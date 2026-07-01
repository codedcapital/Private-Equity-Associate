"""Deterministic scoring engine for PE deal evaluation.

MVP implementation: only Financials and Risk dimensions are computed from real data.
Moat and Market return a baseline 50 until dedicated intelligence modules are built.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select

from db.crud import (
    create_activity_log,
    create_deal_score,
    create_score_history,
    create_signal,
    get_deal_by_id,
    get_deal_score,
    update_deal_score,
)
from db.models import Financial
from db.session import async_session_factory


# ── Scoring sub-functions (pure Python, no LLM) ────────────────────────────


def score_revenue_growth(growth_pct: float | None) -> int:
    if growth_pct is None:
        return 0
    if growth_pct > 0.30:
        return 100
    if growth_pct > 0.20:
        return 85
    if growth_pct > 0.10:
        return 70
    if growth_pct > 0.05:
        return 50
    if growth_pct > 0:
        return 30
    if growth_pct > -0.10:
        return 15
    return 0


def score_margin_quality(ebitda_margin: float | None, fcf_margin: float | None) -> int:
    if ebitda_margin is None:
        return 0
    fcf = fcf_margin or 0
    base = (ebitda_margin * 0.6) + (fcf * 0.4)
    if base > 0.35:
        return 100
    if base > 0.25:
        return 85
    if base > 0.15:
        return 70
    if base > 0.10:
        return 50
    if base > 0.05:
        return 30
    return 15


def score_cash_conversion(fcf_ebitda_ratio: float | None) -> int:
    if fcf_ebitda_ratio is None:
        return 0
    if fcf_ebitda_ratio > 0.80:
        return 100
    if fcf_ebitda_ratio > 0.60:
        return 85
    if fcf_ebitda_ratio > 0.40:
        return 70
    if fcf_ebitda_ratio > 0.20:
        return 50
    if fcf_ebitda_ratio > 0:
        return 30
    return 0


def score_capital_efficiency(roic: float | None, capex_revenue_ratio: float | None) -> int:
    if roic is None:
        return 0
    roic_score = min(100, max(0, roic * 5))
    capex_score = max(0, 100 - ((capex_revenue_ratio or 0) * 20))
    return int(roic_score * 0.7 + capex_score * 0.3)


def score_customer_concentration(
    top1_pct: float | None, top3_pct: float | None, top5_pct: float | None
) -> int:
    penalty = 0
    if top1_pct is not None:
        if top1_pct > 0.50:
            penalty += 40
        elif top1_pct > 0.30:
            penalty += 25
        elif top1_pct > 0.15:
            penalty += 10
    if top3_pct is not None:
        if top3_pct > 0.70:
            penalty += 20
        elif top3_pct > 0.50:
            penalty += 10
    if top5_pct is not None:
        if top5_pct > 0.80:
            penalty += 10
    return max(0, 100 - penalty)


def score_leverage(
    net_debt_ebitda: float | None,
    interest_coverage: float | None,
    cash_runway_months: float | None,
) -> int:
    penalty = 0
    if net_debt_ebitda is not None:
        if net_debt_ebitda > 6:
            penalty += 35
        elif net_debt_ebitda > 4:
            penalty += 25
        elif net_debt_ebitda > 3:
            penalty += 15
        elif net_debt_ebitda > 2:
            penalty += 5
    if interest_coverage is not None:
        if interest_coverage < 2:
            penalty += 25
        elif interest_coverage < 3:
            penalty += 15
        elif interest_coverage < 5:
            penalty += 5
    if cash_runway_months is not None:
        if cash_runway_months < 6:
            penalty += 25
        elif cash_runway_months < 12:
            penalty += 15
    return max(0, 100 - penalty)


# ── ScoringEngine ──────────────────────────────────────────────────────────


class ScoringEngine:
    """Deterministic deal scorer.

    Computes a 0-100 composite score from Financials, Moat, Market, and Risk
    dimensions. Only Financials and Risk use real data in the MVP; Moat and
    Market are baselined at 50.
    """

    def __init__(self, deal_id: int, company_id: int):
        self.deal_id = deal_id
        self.company_id = company_id

    async def compute_score(self) -> dict:
        """Compute and persist the deal score.

        Returns a dict with all dimension scores, composite, confidence, and reason.
        """
        async with async_session_factory() as session:
            # Fetch deal for stage checks
            deal = await get_deal_by_id(session, self.deal_id)

            # 1. Fetch latest financials
            result = await session.execute(
                select(Financial)
                .where(Financial.company_id == self.company_id)
                .order_by(Financial.report_date.desc())
                .limit(1)
            )
            fin = result.scalar_one_or_none()

            # Count total periods for confidence assessment
            period_count = 0
            if fin is not None:
                count_result = await session.execute(
                    select(func.count(Financial.id)).where(
                        Financial.company_id == self.company_id
                    )
                )
                period_count = count_result.scalar_one()

            # 2. Compute Financials dimension score
            if fin is not None:
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
                if (
                    fin.net_income is not None
                    and fin.total_assets is not None
                    and fin.total_assets != 0
                ):
                    roic = fin.net_income / fin.total_assets

                capex_revenue_ratio = (
                    fin.capex / fin.revenue
                    if fin.revenue and fin.revenue != 0 and fin.capex is not None
                    else None
                )
                capital_efficiency_score = score_capital_efficiency(
                    roic, capex_revenue_ratio
                )

                financials_score = round(
                    revenue_growth_score * 0.25
                    + margin_score * 0.25
                    + cash_conversion_score * 0.25
                    + capital_efficiency_score * 0.25
                )
            else:
                financials_score = 0

            # 3. Compute Risk dimension score
            # Customer concentration: MVP placeholder (all None) => 0
            customer_concentration_score = score_customer_concentration(
                None, None, None
            )

            if fin is not None:
                net_debt_ebitda = fin.net_debt_ebitda

                interest_coverage = None
                if (
                    fin.total_debt is not None
                    and fin.total_debt > 0
                    and fin.ebitda is not None
                ):
                    interest_expense = fin.total_debt * 0.05
                    interest_coverage = fin.ebitda / interest_expense

                cash_runway_months = None
                if (
                    fin.cash is not None
                    and fin.operating_cf is not None
                    and fin.operating_cf < 0
                ):
                    cash_runway_months = (
                        fin.cash / abs(fin.operating_cf)
                    ) * 12

                leverage_score = score_leverage(
                    net_debt_ebitda, interest_coverage, cash_runway_months
                )
            else:
                leverage_score = 0

            risk_score = round(
                customer_concentration_score * 0.50 + leverage_score * 0.50
            )

            # 4. Moat and Market baseline
            moat_score = 50
            market_score = 50

            # 5. Composite score
            composite = round(
                financials_score * 0.30
                + moat_score * 0.25
                + market_score * 0.25
                + risk_score * 0.20
            )

            # 6. Confidence assessment
            if fin is None:
                confidence = "INSUFFICIENT"
            elif period_count < 2 or fin.revenue is None or fin.ebitda is None:
                confidence = "LOW"
            else:
                confidence = "HIGH"

            # 7. Upsert DealScore
            existing_score = await get_deal_score(session, self.deal_id)
            old_score = existing_score.score if existing_score else None

            if existing_score is None:
                await create_deal_score(
                    session,
                    deal_id=self.deal_id,
                    score=composite,
                    financials_score=financials_score,
                    moat_score=moat_score,
                    market_score=market_score,
                    risk_score=risk_score,
                    confidence=confidence,
                    methodology_version="1.0.0",
                )
                reason = "Initial score computed"
                score_changed = True
            else:
                await update_deal_score(
                    session,
                    self.deal_id,
                    score=composite,
                    financials_score=financials_score,
                    moat_score=moat_score,
                    market_score=market_score,
                    risk_score=risk_score,
                    confidence=confidence,
                    methodology_version="1.0.0",
                )
                score_changed = old_score is None or abs(composite - old_score) >= 3
                reason = "Score recalculated"

            # 8. Create history and activity log if score changed by >= 3
            if score_changed:
                await create_score_history(
                    session,
                    deal_id=self.deal_id,
                    score=composite,
                    financials=financials_score,
                    moat=moat_score,
                    market=market_score,
                    risk=risk_score,
                    confidence=confidence,
                    methodology_version="1.0.0",
                    reason=reason,
                    event_type="manual" if existing_score is None else "earnings",
                )
                await create_activity_log(
                    session,
                    deal_id=self.deal_id,
                    event_type="score_changed",
                    old_value=str(old_score) if old_score is not None else None,
                    new_value=str(composite),
                    reason=reason,
                    event_metadata={
                        "financials_score": financials_score,
                        "moat_score": moat_score,
                        "market_score": market_score,
                        "risk_score": risk_score,
                        "confidence": confidence,
                    },
                )

                # Signal creation on meaningful score changes
                if old_score is not None and composite - old_score >= 5:
                    await create_signal(
                        session,
                        deal_id=self.deal_id,
                        signal_type="earnings",
                        direction="up",
                        title=f"Score increased by {composite - old_score} points",
                        description=f"Deal score moved from {old_score} to {composite}. Key driver: Financials={financials_score}, Risk={risk_score}.",
                        confidence=confidence,
                    )
                elif old_score is not None and old_score - composite >= 5:
                    await create_signal(
                        session,
                        deal_id=self.deal_id,
                        signal_type="earnings",
                        direction="down",
                        title=f"Score decreased by {old_score - composite} points",
                        description=f"Deal score moved from {old_score} to {composite}. Key driver: Financials={financials_score}, Risk={risk_score}.",
                        confidence=confidence,
                    )
                elif deal and deal.stage.value == "ic_ready":
                    await create_signal(
                        session,
                        deal_id=self.deal_id,
                        signal_type="operational",
                        direction="up",
                        title="Deal moved to IC Ready",
                        description=f"Deal is now ready for Investment Committee review. Score: {composite}.",
                        confidence="HIGH",
                    )

            return {
                "deal_id": self.deal_id,
                "company_id": self.company_id,
                "score": composite,
                "financials_score": financials_score,
                "moat_score": moat_score,
                "market_score": market_score,
                "risk_score": risk_score,
                "confidence": confidence,
                "reason": reason,
            }
