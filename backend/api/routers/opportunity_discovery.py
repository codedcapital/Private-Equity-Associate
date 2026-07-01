"""Opportunity Discovery API Router.

Replaces the old Sourcing page with a live, persistent view of companies
that match the investment strategy. All endpoints are read-only (except
strategy updates) and fast — no LLM calls, pure SQL + deterministic scoring.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from schemas.opportunity_discovery import (
    CoverageMetrics,
    DailyBriefing,
    DiscoverySummary,
    FailedScreenCompany,
    InvestmentStrategyRead,
    InvestmentStrategyUpdate,
    OpportunityItem,
    SignalFeedItem,
    StrategyCoverage,
    ThemeItem,
)
from services.opportunity_discovery import OpportunityDiscoveryService
from db.session import async_session_factory
from db.crud import (
    get_active_investment_strategy,
    update_investment_strategy,
)

router = APIRouter(prefix="/opportunity-discovery", tags=["opportunity-discovery"])


# ── Strategy ─────────────────────────────────────────────────────────────────


@router.get("/strategy", response_model=InvestmentStrategyRead)
async def get_active_strategy() -> InvestmentStrategyRead:
    """Get the currently active investment strategy."""
    async with async_session_factory() as session:
        strategy = await get_active_investment_strategy(session)
        if not strategy:
            # Return empty default if no strategy exists
            return InvestmentStrategyRead(
                id=0,
                name="Default Strategy",
                is_active=True,
                is_default=True,
                criteria={
                    "sectors": [],
                    "geographies": [],
                    "business_models": [],
                    "ownership_types": [],
                    "min_revenue": None,
                    "max_revenue": None,
                    "min_ebitda": None,
                    "max_ebitda": None,
                    "min_ebitda_margin": None,
                    "min_revenue_growth": None,
                    "max_net_debt_ebitda": None,
                    "min_fcf_yield": None,
                    "customer_concentration": None,
                    "product_type": None,
                },
                created_at="",
                updated_at="",
            )
        return InvestmentStrategyRead.model_validate(strategy)


@router.put("/strategy", response_model=InvestmentStrategyRead)
async def update_strategy(request: InvestmentStrategyUpdate) -> InvestmentStrategyRead:
    """Update the active investment strategy."""
    async with async_session_factory() as session:
        strategy = await get_active_investment_strategy(session)
        if not strategy:
            raise ValueError("No active strategy found")
        
        update_data = request.model_dump(exclude_unset=True)
        updated = await update_investment_strategy(session, strategy.id, **update_data)
        if not updated:
            raise ValueError("Failed to update strategy")
        return InvestmentStrategyRead.model_validate(updated)


# ── Coverage Metrics ───────────────────────────────────────────────────────


@router.get("/coverage", response_model=CoverageMetrics)
async def get_coverage_metrics() -> CoverageMetrics:
    """Get funnel counts: universe → financial match → strategic match → high conviction."""
    service = OpportunityDiscoveryService()
    return await service.get_coverage_metrics()


# ── Opportunities ──────────────────────────────────────────────────────────────


@router.get("/opportunities", response_model=list[OpportunityItem])
async def list_opportunities(
    min_score: int = Query(70, ge=0, le=100, description="Minimum fit score to include"),
    limit: int = Query(50, ge=1, le=200, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[OpportunityItem]:
    """List highest conviction opportunities sorted by fit score."""
    service = OpportunityDiscoveryService()
    return await service.get_opportunities(min_score=min_score, limit=limit, offset=offset)


@router.get("/opportunities/{company_id}", response_model=DiscoverySummary)
async def get_discovery_summary(company_id: int) -> DiscoverySummary:
    """Get discovery summary for a specific company (before opening workspace)."""
    service = OpportunityDiscoveryService()
    return await service.get_discovery_summary(company_id)


# ── Signals ──────────────────────────────────────────────────────────────────


@router.get("/signals", response_model=list[SignalFeedItem])
async def get_signal_feed(
    limit: int = Query(20, ge=1, le=100),
    signal_type: str | None = Query(None, description="Filter by signal type"),
) -> list[SignalFeedItem]:
    """Get recent signals across the universe or strategy."""
    service = OpportunityDiscoveryService()
    return await service.get_signals(limit=limit, signal_type=signal_type)


# ── Daily Briefing ───────────────────────────────────────────────────────────


@router.get("/daily-briefing", response_model=DailyBriefing)
async def get_daily_briefing() -> DailyBriefing:
    """Get morning briefing: what changed since yesterday."""
    service = OpportunityDiscoveryService()
    return await service.get_daily_briefing()


# ── Failed Screen Drill-Down ─────────────────────────────────────────────────


@router.get("/failed-screen/{reason}", response_model=list[FailedScreenCompany])
async def get_failed_screen_companies(
    reason: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[FailedScreenCompany]:
    """Get companies that failed a specific screen, with details.

    Reasons: valuation, leverage, growth, market_structure, no_financial_data
    """
    service = OpportunityDiscoveryService()
    return await service.get_failed_screen_companies(reason=reason, limit=limit, offset=offset)


# ── Themes ───────────────────────────────────────────────────────────────────


@router.get("/themes", response_model=list[ThemeItem])
async def get_emerging_themes() -> list[ThemeItem]:
    """Get emerging investment themes from Market Pulse + universe data."""
    service = OpportunityDiscoveryService()
    return await service.get_emerging_themes()


# ── Strategy Coverage ────────────────────────────────────────────────────────


@router.get("/strategy-coverage", response_model=StrategyCoverage)
async def get_strategy_coverage() -> StrategyCoverage:
    """Get research velocity and coverage completeness for the active strategy."""
    service = OpportunityDiscoveryService()
    return await service.get_strategy_coverage()
