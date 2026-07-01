"""OpportunityDiscoveryService — Orchestrates all data for the Opportunity Discovery page.

Combines:
  - UniverseScreenEngine (funnel counts + opportunities)
  - Signal model (recent signals)
  - ScoreHistory (confidence trajectories)
  - ChangeSummarizer (daily briefing)
  - MarketPulseSetting (emerging themes)

This is the single service the Opportunity Discovery router calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_active_investment_strategy,
    get_investment_strategy_by_id,
    list_signals,
    list_score_history,
    list_deal_events,
)
from db.models import (
    Company,
    Deal,
    DealScore,
    Financial,
    Signal,
    ScoreHistory,
    DealEvent,
)
from db.session import async_session_factory
from services.universe_screen import UniverseScreenEngine
from services.change_summarizer import ChangeSummarizer
from schemas.opportunity_discovery import (
    CoverageMetrics,
    OpportunityItem,
    DiscoverySummary,
    DailyBriefing,
    DailyBriefingItem,
    FailedScreenCompany,
    SignalFeedItem,
    ThemeItem,
    StrategyCoverage,
    FinancialSnapshot,
    CriterionMatch,
)

logger = logging.getLogger(__name__)


class OpportunityDiscoveryService:
    """Orchestrates all data needed for the Opportunity Discovery page."""

    def __init__(self, strategy_id: int | None = None):
        self.strategy_id = strategy_id

    # ── Core: Coverage Metrics ─────────────────────────────────────────────────

    async def get_coverage_metrics(self) -> CoverageMetrics:
        """Get funnel counts for the Market Coverage panel."""
        engine = UniverseScreenEngine(strategy_id=self.strategy_id)
        result = await engine.screen()
        return CoverageMetrics(
            universe=result["universe"],
            financial_match=result["financial_match"],
            strategic_match=result["strategic_match"],
            high_conviction=result["high_conviction"],
            breakdown=result["breakdown"],
        )

    # ── Core: Opportunities List ──────────────────────────────────────────────

    async def get_opportunities(
        self, min_score: int = 70, limit: int = 50, offset: int = 0
    ) -> list[OpportunityItem]:
        """Get highest conviction opportunities, sorted by fit score."""
        engine = UniverseScreenEngine(strategy_id=self.strategy_id)
        result = await engine.screen()

        opportunities = result["opportunities"]

        # Filter by min_score
        opportunities = [o for o in opportunities if o["fit_score"] >= min_score]

        # Add trend data (score change from last week) for companies with deals
        async with async_session_factory() as session:
            for opp in opportunities:
                if opp.get("deal_id"):
                    trend = await self._compute_trend(session, opp["deal_id"])
                    opp["trend"] = trend

        # Paginate
        opportunities = opportunities[offset:offset + limit]

        return [OpportunityItem(**o) for o in opportunities]

    # ── Core: Discovery Summary ───────────────────────────────────────────────

    async def get_discovery_summary(self, company_id: int) -> DiscoverySummary:
        """Get detailed discovery summary for a specific company."""
        async with async_session_factory() as session:
            # Get company + financials
            company = await session.get(Company, company_id)
            if not company:
                raise ValueError(f"Company {company_id} not found")

            # Get latest financials
            fin_result = await session.execute(
                select(Financial)
                .where(Financial.company_id == company_id)
                .order_by(Financial.report_date.desc())
                .limit(1)
            )
            fin = fin_result.scalar_one_or_none()

            # Get strategy
            if self.strategy_id:
                strategy = await get_investment_strategy_by_id(session, self.strategy_id)
            else:
                strategy = await get_active_investment_strategy(session)
            criteria = strategy.criteria if strategy else {}

            # Get deal + score if exists
            deal_result = await session.execute(
                select(Deal).where(Deal.company_id == company_id)
            )
            deal = deal_result.scalar_one_or_none()

            score = None
            if deal:
                score_result = await session.execute(
                    select(DealScore).where(DealScore.deal_id == deal.id)
                )
                score = score_result.scalar_one_or_none()

            # Compute fit score
            if score:
                fit_score = score.score or 0
                confidence = 0.85 if score.confidence == "HIGH" else 0.70 if score.confidence == "MEDIUM" else 0.50
                evidence_coverage = 85 if score.confidence == "HIGH" else 60 if score.confidence == "MEDIUM" else 30
                recommendation = (
                    "PROCEED" if fit_score >= 80 else "CONDITIONAL" if fit_score >= 65 else "PASS"
                )
            else:
                from services.universe_screen import _compute_financial_fit_score
                fit_score = _compute_financial_fit_score(fin)
                confidence = 0.50
                evidence_coverage = 25
                recommendation = "CONDITIONAL" if fit_score >= 65 else "PASS"

            # Build "why surfaced" bullets
            why_surfaced = []
            if fin:
                if fin.revenue_growth is not None and fin.revenue_growth > 0.15:
                    why_surfaced.append(f"Revenue CAGR {fin.revenue_growth*100:.0f}%")
                if fin.ebitda_margin is not None and fin.ebitda_margin > 0.20:
                    why_surfaced.append(f"EBITDA {fin.ebitda_margin*100:.0f}%")
                if fin.net_debt_ebitda is not None and fin.net_debt_ebitda < 3:
                    why_surfaced.append("Low leverage")

            # Build matches
            matches = []
            sectors = criteria.get("sectors", [])
            if sectors:
                match = company.sector in sectors
                matches.append(CriterionMatch(
                    criterion="Sector",
                    status="pass" if match else "fail",
                    detail=f"{company.sector} {'matches' if match else 'does not match'} target sectors"
                ))

            geos = criteria.get("geographies", [])
            if geos:
                match = company.geography in geos
                matches.append(CriterionMatch(
                    criterion="Geography",
                    status="pass" if match else "fail",
                    detail=f"{company.geography} {'matches' if match else 'does not match'} target regions"
                ))

            if fin:
                min_rev = criteria.get("min_revenue")
                if min_rev is not None:
                    match = fin.revenue is not None and fin.revenue >= min_rev
                    matches.append(CriterionMatch(
                        criterion="Revenue",
                        status="pass" if match else "fail",
                        detail=f"${(fin.revenue or 0)/1e6:.1f}M {'meets' if match else 'below'} ${min_rev/1e6:.0f}M minimum"
                    ))

                min_margin = criteria.get("min_ebitda_margin")
                if min_margin is not None:
                    match = fin.ebitda_margin is not None and fin.ebitda_margin >= min_margin
                    matches.append(CriterionMatch(
                        criterion="EBITDA Margin",
                        status="pass" if match else "fail",
                        detail=f"{(fin.ebitda_margin or 0)*100:.1f}% {'meets' if match else 'below'} {min_margin*100:.0f}% minimum"
                    ))

                min_growth = criteria.get("min_revenue_growth")
                if min_growth is not None:
                    match = fin.revenue_growth is not None and fin.revenue_growth >= min_growth
                    matches.append(CriterionMatch(
                        criterion="Revenue Growth",
                        status="pass" if match else "fail",
                        detail=f"{fin.revenue_growth*100:.1f}% {'meets' if match else 'below'} {min_growth*100:.0f}% minimum"
                    ))

            # Build concerns
            concerns = []
            if fin:
                if fin.net_debt_ebitda is not None and fin.net_debt_ebitda > 4:
                    concerns.append(f"High leverage: {fin.net_debt_ebitda:.1f}x Net Debt / EBITDA")
                if fin.revenue_growth is not None and fin.revenue_growth < 0.05:
                    concerns.append(f"Low growth: {fin.revenue_growth*100:.1f}% revenue CAGR")
                if fin.ebitda_margin is not None and fin.ebitda_margin < 0.15:
                    concerns.append(f"Thin margins: {fin.ebitda_margin*100:.1f}% EBITDA margin")

            return DiscoverySummary(
                company_id=company.id,
                company_name=company.name,
                ticker=company.ticker,
                fit_score=fit_score,
                confidence_score=confidence,
                why_surfaced=why_surfaced,
                matches=matches,
                concerns=concerns,
                evidence_coverage=evidence_coverage,
                recommendation=recommendation,
                has_deal=deal is not None,
                deal_id=deal.id if deal else None,
                financial_snapshot=FinancialSnapshot(
                    revenue=fin.revenue if fin else None,
                    ebitda=fin.ebitda if fin else None,
                    ebitda_margin=fin.ebitda_margin if fin else None,
                    revenue_growth=fin.revenue_growth if fin else None,
                    net_debt_ebitda=fin.net_debt_ebitda if fin else None,
                    fcf=fin.fcf if fin else None,
                    fcf_yield=fin.fcf_yield if fin else None,
                ) if fin else None,
            )

    # ── Signals Feed ───────────────────────────────────────────────────────────

    async def get_signals(
        self, limit: int = 20, signal_type: str | None = None
    ) -> list[SignalFeedItem]:
        """Get recent signals across the universe or strategy."""
        async with async_session_factory() as session:
            # Get all signals (or filtered by type)
            signals = await list_signals(
                session, signal_type=signal_type, is_dismissed=False, limit=limit
            )

            # Enrich with company names
            result = []
            for sig in signals:
                company_name = "Unknown"
                if sig.deal:
                    company_name = sig.deal.company.name if sig.deal.company else "Unknown"
                result.append(SignalFeedItem(
                    id=sig.id,
                    deal_id=sig.deal_id,
                    company_id=sig.deal.company_id if sig.deal else 0,
                    company_name=company_name,
                    signal_type=sig.signal_type,
                    direction=sig.direction,
                    title=sig.title,
                    description=sig.description,
                    confidence=sig.confidence,
                    detected_at=sig.detected_at.isoformat() if sig.detected_at else None,
                ))
            return result

    # ── Daily Briefing ─────────────────────────────────────────────────────────

    async def get_daily_briefing(self) -> DailyBriefing:
        """Generate morning briefing: what changed since yesterday."""
        async with async_session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)

            # Count new opportunities (companies that entered the screen in the last 24h)
            # This is an approximation: count score history entries with "manual" or "earnings" type
            # For MVP, we use signals as the source of change
            signals = await list_signals(session, is_dismissed=False, limit=100)
            recent_signals = [s for s in signals if s.detected_at and s.detected_at >= cutoff]

            new_opps = 0
            exited = 0
            scores_up = 0
            scores_down = 0
            earnings = 0
            ma_count = 0
            items = []

            for sig in recent_signals:
                if sig.signal_type == "earnings":
                    earnings += 1
                    items.append(DailyBriefingItem(
                        type="earnings",
                        company_id=sig.deal.company_id if sig.deal else 0,
                        company_name=sig.deal.company.name if sig.deal and sig.deal.company else "Unknown",
                        description=sig.description or sig.title,
                        direction=sig.direction,
                        delta=None,
                    ))
                elif sig.signal_type == "operational":
                    if sig.direction == "up":
                        scores_up += 1
                    elif sig.direction == "down":
                        scores_down += 1
                    items.append(DailyBriefingItem(
                        type="score_increased" if sig.direction == "up" else "score_decreased",
                        company_id=sig.deal.company_id if sig.deal else 0,
                        company_name=sig.deal.company.name if sig.deal and sig.deal.company else "Unknown",
                        description=sig.description or sig.title,
                        direction=sig.direction,
                        delta=None,
                    ))
                elif sig.signal_type == "ma":
                    ma_count += 1
                    items.append(DailyBriefingItem(
                        type="ma",
                        company_id=sig.deal.company_id if sig.deal else 0,
                        company_name=sig.deal.company.name if sig.deal and sig.deal.company else "Unknown",
                        description=sig.description or sig.title,
                        direction=sig.direction,
                        delta=None,
                    ))

            # Also check for new companies that entered the financial screen
            # For MVP, use deal events as a proxy
            # Get all deal events in last 24h
            all_events = await session.execute(
                select(DealEvent).where(DealEvent.created_at >= cutoff).limit(50)
            )
            events = all_events.scalars().all()
            for evt in events:
                if evt.event_type == "score_changed":
                    items.append(DailyBriefingItem(
                        type="score_increased" if "increased" in evt.description else "score_decreased",
                        company_id=evt.deal_id,
                        company_name="Unknown",
                        description=evt.description,
                        direction="up" if "increased" in evt.description else "down",
                        delta=None,
                    ))

            # For MVP, new_opps and exited are approximated from the engine run
            engine = UniverseScreenEngine(strategy_id=self.strategy_id)
            screen_result = await engine.screen()
            new_opps = min(3, screen_result["high_conviction"])  # Placeholder
            exited = min(2, screen_result["breakdown"].get("failed_valuation", 0) // 10)

            return DailyBriefing(
                date=datetime.now(timezone.utc).isoformat(),
                new_opportunities=new_opps,
                exited_opportunities=exited,
                scores_increased=scores_up,
                scores_decreased=scores_down,
                earnings_reported=earnings,
                ma_transactions=ma_count,
                items=items[:20],  # Limit items
            )

    # ── Failed Screen Drill-Down ─────────────────────────────────────────────────

    async def get_failed_screen_companies(
        self, reason: str, limit: int = 100, offset: int = 0
    ) -> list[FailedScreenCompany]:
        """Get companies that failed a specific screen, with details."""
        engine = UniverseScreenEngine(strategy_id=self.strategy_id)
        result = await engine.screen()

        failed = [f for f in result["failed_companies"] if f["failure_reason"] == reason]
        failed = failed[offset:offset + limit]

        return [FailedScreenCompany(**f) for f in failed]

    # ── Emerging Themes ────────────────────────────────────────────────────────

    async def get_emerging_themes(self) -> list[ThemeItem]:
        """Get emerging investment themes from universe data.

        For MVP, derive themes from sector distribution of high-scoring companies.
        """
        async with async_session_factory() as session:
            engine = UniverseScreenEngine(strategy_id=self.strategy_id)
            screen_result = await engine.screen()
            opportunities = screen_result["opportunities"]

            # Group by sector
            sector_data = {}
            for opp in opportunities:
                sector = opp.get("sector", "Unknown")
                if sector not in sector_data:
                    sector_data[sector] = {"count": 0, "total_score": 0}
                sector_data[sector]["count"] += 1
                sector_data[sector]["total_score"] += opp.get("fit_score", 0)

            themes = []
            for sector, data in sector_data.items():
                if data["count"] >= 2:  # Only sectors with 2+ companies
                    avg_score = round(data["total_score"] / data["count"])
                    trend = "rising" if avg_score > 75 else "stable" if avg_score > 60 else "falling"
                    themes.append(ThemeItem(
                        name=sector,
                        company_count=data["count"],
                        avg_score=avg_score,
                        trend=trend,
                        description=f"{data['count']} companies with avg fit score {avg_score}",
                    ))

            # Sort by avg score descending
            themes.sort(key=lambda t: t.avg_score, reverse=True)
            return themes[:10]

    # ── Strategy Coverage ──────────────────────────────────────────────────────

    async def get_strategy_coverage(self) -> StrategyCoverage:
        """Get research velocity and coverage completeness."""
        engine = UniverseScreenEngine(strategy_id=self.strategy_id)
        result = await engine.screen()

        async with async_session_factory() as session:
            # Count how many companies have DealScores (research complete)
            deals_count = await session.execute(select(func.count(Deal.id)))
            total_deals = deals_count.scalar_one() or 0

            scores_count = await session.execute(select(func.count(DealScore.id)))
            total_scores = scores_count.scalar_one() or 0

            # Investment-ready = deals with score >= 80
            investment_ready_result = await session.execute(
                select(func.count(DealScore.id)).where(DealScore.score >= 80)
            )
            investment_ready = investment_ready_result.scalar_one() or 0

            universe = result["universe"]
            coverage_percent = round((total_scores / universe * 100)) if universe > 0 else 0

            return StrategyCoverage(
                strategy_name="Active Strategy",
                universe=universe,
                financial_match=result["financial_match"],
                research_complete=total_scores,
                investment_ready=investment_ready,
                research_velocity=total_scores,  # For MVP, use total as proxy for weekly
                investment_ready_velocity=investment_ready,
                coverage_percent=coverage_percent,
            )

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _compute_trend(self, session: AsyncSession, deal_id: int) -> int | None:
        """Compute score change from last week for a deal."""
        history = await list_score_history(session, deal_id, limit=2)
        if len(history) >= 2:
            latest = history[0].score
            previous = history[1].score
            return latest - previous
        return None
