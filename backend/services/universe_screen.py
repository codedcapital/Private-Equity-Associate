"""UniverseScreenEngine — Screens the entire company universe against an InvestmentStrategy.

This is the core engine behind the Opportunity Discovery page. It takes a
strategy's criteria and categorizes every company into buckets:

  - universe: all companies
  - financial_match: passes financial criteria (revenue, EBITDA, margin, growth, leverage)
  - strategic_match: has a DealScore (pipeline company with intelligence)
  - high_conviction: strategic_match with score ≥ 80 and confidence ≥ 0.80
  - failed_screen: categorized by why they failed (valuation, leverage, growth, market_structure)

For companies without pipeline deals, a financial fit score is computed on-the-fly
from the latest Financial snapshot. No LLM calls — pure SQL + deterministic scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Company, Deal, DealScore, Financial
from db.crud import get_active_investment_strategy, get_deal_score
from db.session import async_session_factory
from services.scoring_engine import (
    score_capital_efficiency,
    score_cash_conversion,
    score_leverage,
    score_margin_quality,
    score_revenue_growth,
)

logger = logging.getLogger(__name__)


# ── Financial fit scoring (deterministic, no LLM) ────────────────────────────


def _compute_financial_fit_score(fin: Financial | None) -> int:
    """Compute a 0-100 financial fit score from a Financial snapshot.

    Uses the same deterministic functions as ScoringEngine but adapted
    for companies that don't have a Deal yet.
    """
    if fin is None:
        return 0

    revenue_growth_score = score_revenue_growth(fin.revenue_growth)

    fcf_margin = (
        fin.fcf / fin.revenue
        if fin.revenue and fin.revenue != 0 and fin.fcf is not None
        else None
    )
    margin_score = score_margin_quality(fin.ebitda_margin, fcf_margin)

    fcf_ebitda_ratio = (
        fin.fcf / fin.ebitda
        if fin.ebitda and fin.ebitda != 0 and fin.fcf is not None
        else None
    )
    cash_conversion_score = score_cash_conversion(fcf_ebitda_ratio)

    roic = None
    if fin.net_income is not None and fin.total_assets is not None and fin.total_assets != 0:
        roic = fin.net_income / fin.total_assets

    capex_revenue_ratio = (
        fin.capex / fin.revenue
        if fin.revenue and fin.revenue != 0 and fin.capex is not None
        else None
    )
    capital_efficiency_score = score_capital_efficiency(roic, capex_revenue_ratio)

    financials_score = round(
        revenue_growth_score * 0.25
        + margin_score * 0.25
        + cash_conversion_score * 0.25
        + capital_efficiency_score * 0.25
    )

    # Risk dimension
    net_debt_ebitda = fin.net_debt_ebitda
    interest_coverage = None
    if fin.total_debt is not None and fin.total_debt > 0 and fin.ebitda is not None:
        interest_expense = fin.total_debt * 0.05
        interest_coverage = fin.ebitda / interest_expense

    cash_runway_months = None
    if fin.cash is not None and fin.operating_cf is not None and fin.operating_cf < 0:
        cash_runway_months = (fin.cash / abs(fin.operating_cf)) * 12

    leverage_score = score_leverage(net_debt_ebitda, interest_coverage, cash_runway_months)
    risk_score = round(50 * 0.50 + leverage_score * 0.50)  # customer conc baseline = 50

    # Composite (same weights as ScoringEngine)
    moat_score = 50
    market_score = 50
    composite = round(
        financials_score * 0.30
        + moat_score * 0.25
        + market_score * 0.25
        + risk_score * 0.20
    )
    return composite


# ── Screen logic ─────────────────────────────────────────────────────────────


def _passes_financial_screen(fin: Financial | None, criteria: dict) -> tuple[bool, str]:
    """Check if a company's financials pass the strategy criteria.

    Returns (passes, failure_reason).
    """
    if fin is None:
        return False, "no_financial_data"

    min_rev = criteria.get("min_revenue")
    if min_rev is not None and (fin.revenue is None or fin.revenue < min_rev):
        return False, "failed_revenue"

    max_rev = criteria.get("max_revenue")
    if max_rev is not None and (fin.revenue is None or fin.revenue > max_rev):
        return False, "failed_revenue"

    min_ebitda = criteria.get("min_ebitda")
    if min_ebitda is not None and (fin.ebitda is None or fin.ebitda < min_ebitda):
        return False, "failed_valuation"

    max_ebitda = criteria.get("max_ebitda")
    if max_ebitda is not None and (fin.ebitda is None or fin.ebitda > max_ebitda):
        return False, "failed_valuation"

    min_margin = criteria.get("min_ebitda_margin")
    if min_margin is not None and (fin.ebitda_margin is None or fin.ebitda_margin < min_margin):
        return False, "failed_growth"

    min_growth = criteria.get("min_revenue_growth")
    if min_growth is not None and (fin.revenue_growth is None or fin.revenue_growth < min_growth):
        return False, "failed_growth"

    max_leverage = criteria.get("max_net_debt_ebitda")
    if max_leverage is not None and (fin.net_debt_ebitda is None or fin.net_debt_ebitda > max_leverage):
        return False, "failed_leverage"

    min_fcf = criteria.get("min_fcf_yield")
    if min_fcf is not None and (fin.fcf_yield is None or fin.fcf_yield < min_fcf):
        return False, "failed_valuation"

    return True, ""


def _passes_strategic_screen(company: Company, criteria: dict) -> tuple[bool, str]:
    """Check if a company passes non-financial strategic criteria.

    Returns (passes, failure_reason).
    """
    sectors = criteria.get("sectors", [])
    if sectors and company.sector not in sectors:
        return False, "failed_market_structure"

    geographies = criteria.get("geographies", [])
    if geographies and company.geography not in geographies:
        return False, "failed_market_structure"

    return True, ""


# ── UniverseScreenEngine ─────────────────────────────────────────────────────


class UniverseScreenEngine:
    """Screens the entire company universe against an InvestmentStrategy.

    For companies already in the pipeline (with a Deal), the engine uses
    existing DealScore + ConfidenceLedger data. For new companies, it
    computes a financial fit score on-the-fly from the latest Financial snapshot.

    All operations are SQL-based — no LLM calls. Results are real-time.
    """

    def __init__(self, strategy_id: int | None = None):
        self.strategy_id = strategy_id

    async def screen(self) -> dict[str, Any]:
        """Run the full screen and return all buckets.

        Returns:
            {
                "universe": int,
                "financial_match": int,
                "strategic_match": int,
                "high_conviction": int,
                "breakdown": {"failed_valuation": int, "failed_leverage": int, ...},
                "opportunities": [OpportunityItem ...],
                "failed_companies": [FailedScreenCompany ...],
            }
        """
        async with async_session_factory() as session:
            # 1. Get the strategy
            if self.strategy_id:
                from db.crud import get_investment_strategy_by_id
                strategy = await get_investment_strategy_by_id(session, self.strategy_id)
            else:
                strategy = await get_active_investment_strategy(session)

            criteria = strategy.criteria if strategy else {}

            # 2. Count universe
            universe_result = await session.execute(select(func.count(Company.id)))
            universe = universe_result.scalar_one() or 0

            # 3. Fetch all companies with their latest financials
            # Use a CTE to get the latest financial per company
            subq = (
                select(
                    Financial.company_id,
                    func.max(Financial.report_date).label("latest_date"),
                )
                .group_by(Financial.company_id)
                .subquery()
            )

            stmt = (
                select(Company, Financial)
                .join(Financial, Company.id == Financial.company_id)
                .join(subq, and_(
                    Financial.company_id == subq.c.company_id,
                    Financial.report_date == subq.c.latest_date,
                ))
            )
            result = await session.execute(stmt)
            company_financials = result.all()  # list of (Company, Financial) tuples

            # 4. Also fetch all deals and deal scores for quick lookup
            deals_result = await session.execute(
                select(Deal).options(selectinload(Deal.company))
            )
            all_deals = deals_result.scalars().all()
            deals_by_company = {d.company_id: d for d in all_deals}

            deal_scores_result = await session.execute(select(DealScore))
            all_scores = deal_scores_result.scalars().all()
            scores_by_deal = {s.deal_id: s for s in all_scores}

            # 5. Screen each company
            financial_matches = 0
            strategic_matches = 0
            high_conviction = 0
            breakdown = {
                "failed_valuation": 0,
                "failed_leverage": 0,
                "failed_growth": 0,
                "failed_market_structure": 0,
                "no_financial_data": 0,
            }
            opportunities = []
            failed_companies = []

            for company, fin in company_financials:
                # Financial screen
                fin_passes, fin_fail_reason = _passes_financial_screen(fin, criteria)

                # Strategic screen (non-financial)
                strat_passes, strat_fail_reason = _passes_strategic_screen(company, criteria)

                if not fin_passes:
                    breakdown[fin_fail_reason] = breakdown.get(fin_fail_reason, 0) + 1
                    failed_companies.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "sector": company.sector,
                        "financial_snapshot": self._snapshot(fin),
                        "failure_reason": fin_fail_reason,
                        "failure_detail": self._fail_detail(fin, fin_fail_reason, criteria),
                    })
                    continue

                if not strat_passes:
                    breakdown[strat_fail_reason] = breakdown.get(strat_fail_reason, 0) + 1
                    failed_companies.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "sector": company.sector,
                        "financial_snapshot": self._snapshot(fin),
                        "failure_reason": strat_fail_reason,
                        "failure_detail": self._fail_detail_strategic(company, strat_fail_reason, criteria),
                    })
                    continue

                financial_matches += 1

                # Check if this company has a deal + score
                deal = deals_by_company.get(company.id)
                score = None
                if deal:
                    score = scores_by_deal.get(deal.id)

                if deal and score:
                    strategic_matches += 1
                    is_high_conviction = score.score is not None and score.score >= 80 and score.confidence in ("HIGH", "MEDIUM")
                    if is_high_conviction:
                        high_conviction += 1

                    opportunities.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "sector": company.sector,
                        "fit_score": score.score or 0,
                        "confidence_score": 0.85 if score.confidence == "HIGH" else 0.70 if score.confidence == "MEDIUM" else 0.50,
                        "recommendation": "PROCEED" if (score.score or 0) >= 80 else "CONDITIONAL" if (score.score or 0) >= 65 else "PASS",
                        "trend": None,  # Will be populated by OpportunityDiscoveryService
                        "why": self._why_surfaced_pipeline(company, score, fin),
                        "evidence_coverage": 85 if score.confidence == "HIGH" else 60 if score.confidence == "MEDIUM" else 30,
                        "has_deal": True,
                        "deal_id": deal.id,
                        "financial_snapshot": self._snapshot(fin),
                    })
                else:
                    # No deal yet — compute financial fit score on the fly
                    fit_score = _compute_financial_fit_score(fin)
                    opportunities.append({
                        "company_id": company.id,
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "sector": company.sector,
                        "fit_score": fit_score,
                        "confidence_score": 0.50,  # Lower confidence without full intelligence
                        "recommendation": "CONDITIONAL" if fit_score >= 65 else "PASS",
                        "trend": None,
                        "why": self._why_surfaced_new(company, fin, criteria),
                        "evidence_coverage": 25,  # Only financials available
                        "has_deal": False,
                        "deal_id": None,
                        "financial_snapshot": self._snapshot(fin),
                    })

            # Also count companies with no financial data at all
            companies_with_fin = {c.id for c, _ in company_financials}
            all_companies_result = await session.execute(select(Company.id))
            all_company_ids = {r[0] for r in all_companies_result.all()}
            no_fin_count = len(all_company_ids - companies_with_fin)
            breakdown["no_financial_data"] = breakdown.get("no_financial_data", 0) + no_fin_count

            # Sort opportunities by fit_score descending
            opportunities.sort(key=lambda x: x["fit_score"], reverse=True)

            return {
                "universe": universe,
                "financial_match": financial_matches,
                "strategic_match": strategic_matches,
                "high_conviction": high_conviction,
                "breakdown": breakdown,
                "opportunities": opportunities,
                "failed_companies": failed_companies,
            }

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _snapshot(fin: Financial | None) -> dict:
        """Build a lightweight financial snapshot."""
        if fin is None:
            return {}
        return {
            "revenue": fin.revenue,
            "ebitda": fin.ebitda,
            "ebitda_margin": fin.ebitda_margin,
            "revenue_growth": fin.revenue_growth,
            "net_debt_ebitda": fin.net_debt_ebitda,
            "fcf": fin.fcf,
            "fcf_yield": fin.fcf_yield,
        }

    @staticmethod
    def _fail_detail(fin: Financial, reason: str, criteria: dict) -> str:
        """Human-readable detail of why a company failed a financial screen."""
        if reason == "no_financial_data":
            return "No financial data available in the database."
        if reason == "failed_revenue":
            min_r = criteria.get("min_revenue")
            max_r = criteria.get("max_revenue")
            rev = fin.revenue
            if rev is None:
                return "Revenue data is missing."
            if min_r and rev < min_r:
                return f"Revenue ${rev/1e6:.1f}M is below the ${min_r/1e6:.0f}M minimum."
            if max_r and rev > max_r:
                return f"Revenue ${rev/1e6:.1f}M exceeds the ${max_r/1e6:.0f}M maximum."
        if reason == "failed_valuation":
            min_e = criteria.get("min_ebitda")
            max_e = criteria.get("max_ebitda")
            ebitda = fin.ebitda
            if ebitda is None:
                return "EBITDA data is missing."
            if min_e and ebitda < min_e:
                return f"EBITDA ${ebitda/1e6:.1f}M is below the ${min_e/1e6:.0f}M minimum."
            if max_e and ebitda > max_e:
                return f"EBITDA ${ebitda/1e6:.1f}M exceeds the ${max_e/1e6:.0f}M maximum."
            min_m = criteria.get("min_ebitda_margin")
            if min_m and (fin.ebitda_margin is None or fin.ebitda_margin < min_m):
                return f"EBITDA margin {(fin.ebitda_margin or 0)*100:.1f}% is below the {min_m*100:.0f}% minimum."
            min_f = criteria.get("min_fcf_yield")
            if min_f and (fin.fcf_yield is None or fin.fcf_yield < min_f):
                return f"FCF yield {(fin.fcf_yield or 0)*100:.1f}% is below the {min_f*100:.0f}% minimum."
            return "Failed valuation criteria."
        if reason == "failed_growth":
            min_g = criteria.get("min_revenue_growth")
            if fin.revenue_growth is None:
                return "Revenue growth data is missing."
            return f"Revenue growth {fin.revenue_growth*100:.1f}% is below the {min_g*100:.0f}% minimum."
        if reason == "failed_leverage":
            max_lev = criteria.get("max_net_debt_ebitda")
            if fin.net_debt_ebitda is None:
                return "Leverage data is missing."
            return f"Net debt / EBITDA {fin.net_debt_ebitda:.1f}x exceeds the {max_lev:.1f}x maximum."
        return "Did not pass the screen."

    @staticmethod
    def _fail_detail_strategic(company: Company, reason: str, criteria: dict) -> str:
        """Human-readable detail of why a company failed a strategic screen."""
        if reason == "failed_market_structure":
            sectors = criteria.get("sectors", [])
            geos = criteria.get("geographies", [])
            parts = []
            if sectors and company.sector not in sectors:
                parts.append(f"Sector '{company.sector}' is not in the target sectors: {', '.join(sectors)}")
            if geos and company.geography not in geos:
                parts.append(f"Geography '{company.geography}' is not in the target regions: {', '.join(geos)}")
            return " ".join(parts) if parts else "Did not match strategic criteria."
        return "Did not pass strategic screen."

    @staticmethod
    def _why_surfaced_pipeline(company: Company, score: DealScore, fin: Financial) -> str:
        """Human-readable reason why a pipeline company surfaced."""
        parts = []
        if fin.ebitda_margin is not None and fin.ebitda_margin > 0.20:
            parts.append(f"EBITDA margin {fin.ebitda_margin*100:.0f}%")
        if fin.revenue_growth is not None and fin.revenue_growth > 0.10:
            parts.append(f"Revenue growth {fin.revenue_growth*100:.0f}%")
        if score.score is not None and score.score >= 80:
            parts.append(f"High investment score ({score.score})")
        if not parts:
            parts.append(f"Pipeline company with score {score.score or 0}")
        return ", ".join(parts)

    @staticmethod
    def _why_surfaced_new(company: Company, fin: Financial, criteria: dict) -> str:
        """Human-readable reason why a new company surfaced."""
        parts = []
        if fin.ebitda_margin is not None and fin.ebitda_margin > 0.20:
            parts.append(f"EBITDA margin {fin.ebitda_margin*100:.0f}%")
        if fin.revenue_growth is not None and fin.revenue_growth > 0.10:
            parts.append(f"Revenue growth {fin.revenue_growth*100:.0f}%")
        if fin.net_debt_ebitda is not None and fin.net_debt_ebitda < 3:
            parts.append("Low leverage")
        if not parts:
            parts.append("Passes financial screen")
        return ", ".join(parts)
