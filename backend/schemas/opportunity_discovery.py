"""Pydantic schemas for the Opportunity Discovery API.

Defines request/response types for the new Opportunity Discovery page,
which replaces the old Sourcing page with a live, persistent view of
companies that match the investment strategy.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyCriteria(BaseModel):
    """Editable investment strategy criteria."""

    sectors: list[str] = Field(default_factory=list, description="e.g. ['Vertical SaaS', 'Healthcare IT']")
    geographies: list[str] = Field(default_factory=list, description="e.g. ['North America', 'Europe']")
    business_models: list[str] = Field(
        default_factory=list, description="e.g. ['Recurring Revenue', 'Usage-Based']"
    )
    ownership_types: list[str] = Field(
        default_factory=list, description="e.g. ['Founder-Owned', 'Sponsor-Owned', 'PE-Backed']"
    )
    min_revenue: float | None = Field(None, description="Minimum revenue in USD")
    max_revenue: float | None = Field(None, description="Maximum revenue in USD")
    min_ebitda: float | None = Field(None, description="Minimum EBITDA in USD")
    max_ebitda: float | None = Field(None, description="Maximum EBITDA in USD")
    min_ebitda_margin: float | None = Field(None, description="Minimum EBITDA margin (0-1)")
    min_revenue_growth: float | None = Field(None, description="Minimum revenue CAGR (0-1)")
    max_net_debt_ebitda: float | None = Field(None, description="Maximum net debt / EBITDA ratio")
    min_fcf_yield: float | None = Field(None, description="Minimum FCF yield (0-1)")
    customer_concentration: str | None = Field(None, description="e.g. 'Low', 'Medium', 'High'")
    product_type: str | None = Field(None, description="e.g. 'Mission Critical', 'Workflow'")


class InvestmentStrategyRead(BaseModel):
    """Response shape for an investment strategy."""

    id: int
    name: str
    is_active: bool
    is_default: bool
    criteria: StrategyCriteria
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestmentStrategyUpdate(BaseModel):
    """Request shape for updating an investment strategy."""

    name: str | None = None
    criteria: StrategyCriteria | None = None
    is_active: bool | None = None
    is_default: bool | None = None


class CoverageMetrics(BaseModel):
    """Funnel counts: universe → financial match → strategic match → high conviction."""

    universe: int = Field(..., description="Total companies in the universe")
    financial_match: int = Field(..., description="Companies passing financial screen")
    strategic_match: int = Field(..., description="Companies with DealScore + ConfidenceLedger")
    high_conviction: int = Field(..., description="Strategic matches with score ≥ 80 & confidence ≥ 0.80")
    breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Why companies failed: {failed_valuation: 118, ...}",
    )


class FinancialSnapshot(BaseModel):
    """Lightweight financial data for list views."""

    revenue: float | None = None
    ebitda: float | None = None
    ebitda_margin: float | None = None
    revenue_growth: float | None = None
    net_debt_ebitda: float | None = None
    fcf: float | None = None
    fcf_yield: float | None = None


class OpportunityItem(BaseModel):
    """A single company in the Highest Conviction Opportunities table."""

    company_id: int
    company_name: str
    ticker: str | None = None
    sector: str | None = None
    fit_score: int = Field(..., ge=0, le=100, description="Investment fit score (0-100)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the score (0-1)")
    recommendation: str | None = Field(None, description="PROCEED, CONDITIONAL, or PASS")
    trend: int | None = Field(None, description="Score change from last week (+/- points)")
    why: str = Field(..., description="Human-readable reason for surfacing")
    evidence_coverage: int | None = Field(None, ge=0, le=100, description="Evidence completeness (0-100)")
    has_deal: bool = Field(False, description="Whether this company is already in the pipeline")
    deal_id: int | None = None
    financial_snapshot: FinancialSnapshot | None = None


class CriterionMatch(BaseModel):
    """A single criterion match/fail for the discovery summary."""

    criterion: str
    status: str = Field(..., description="pass or fail")
    detail: str | None = None


class DiscoverySummary(BaseModel):
    """Expanded view when clicking a company in the opportunities table."""

    company_id: int
    company_name: str
    ticker: str | None = None
    fit_score: int = Field(..., ge=0, le=100)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    why_surfaced: list[str] = Field(default_factory=list, description="Bullet points of why this company surfaced")
    matches: list[CriterionMatch] = Field(default_factory=list, description="Strategy criteria match/fail breakdown")
    concerns: list[str] = Field(default_factory=list, description="Potential concerns flagged by the engine")
    evidence_coverage: int = Field(..., ge=0, le=100, description="Percent of evidence modules complete")
    recommendation: str = Field(..., description="Worth opening workspace / Monitor / Pass")
    has_deal: bool = False
    deal_id: int | None = None
    financial_snapshot: FinancialSnapshot | None = None


class DailyBriefingItem(BaseModel):
    """A single change in the daily briefing."""

    type: str = Field(..., description="new_opportunity, exited, score_increased, earnings, ma")
    company_id: int
    company_name: str
    description: str
    direction: str | None = Field(None, description="up, down, or neutral")
    delta: int | None = Field(None, description="Score change amount")


class DailyBriefing(BaseModel):
    """Morning briefing: what changed since yesterday."""

    date: str = Field(..., description="ISO date string")
    new_opportunities: int
    exited_opportunities: int
    scores_increased: int
    scores_decreased: int
    earnings_reported: int
    ma_transactions: int
    items: list[DailyBriefingItem] = Field(default_factory=list)


class FailedScreenCompany(BaseModel):
    """A company that failed a specific screen, with details."""

    company_id: int
    company_name: str
    ticker: str | None = None
    sector: str | None = None
    financial_snapshot: FinancialSnapshot | None = None
    failure_reason: str = Field(..., description="The screen that failed: valuation, leverage, growth, market_structure")
    failure_detail: str = Field(..., description="Human-readable detail of why it failed")


class SignalFeedItem(BaseModel):
    """A signal in the Opportunity Discovery feed."""

    id: int
    deal_id: int | None = None
    company_id: int
    company_name: str
    signal_type: str = Field(..., description="earnings, valuation, ma, operational, etc.")
    direction: str | None = Field(None, description="up, down, neutral")
    title: str
    description: str | None = None
    confidence: str
    detected_at: str = Field(..., description="ISO datetime string")


class ThemeItem(BaseModel):
    """An emerging investment theme."""

    name: str
    company_count: int
    avg_score: int = Field(..., ge=0, le=100)
    trend: str = Field(..., description="rising, stable, falling")
    description: str


class StrategyCoverage(BaseModel):
    """Research velocity and coverage completeness for a strategy."""

    strategy_name: str
    universe: int
    financial_match: int
    research_complete: int
    investment_ready: int
    research_velocity: int = Field(..., description="Companies completed research this week")
    investment_ready_velocity: int = Field(..., description="Companies added to investment-ready this month")
    coverage_percent: int = Field(..., ge=0, le=100)
