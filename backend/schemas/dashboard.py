"""Pydantic schemas for Dashboard resources."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    """Summary statistics for the dashboard."""

    active_deals: int
    avg_score: int
    ic_ready_count: int
    attention_count: int
    stage_breakdown: dict[str, int]
    last_updated: str


class AttentionDeal(BaseModel):
    """A deal requiring attention on the dashboard."""

    deal_id: int
    company_id: int
    company_name: str
    ticker: str | None
    score: int | None
    score_change: int
    score_change_direction: str
    stage: str
    stage_label: str
    why: str
    confidence: str
    updated_at: str
    financials_score: int | None
    risk_score: int | None
    moat_score: int | None
    market_score: int | None


class AttentionList(BaseModel):
    """List of deals requiring attention."""

    deals: list[AttentionDeal]


class ScoreRefreshResponse(BaseModel):
    """Response after refreshing a deal score."""

    deal_id: int
    score: int
    financials_score: int
    moat_score: int
    market_score: int
    risk_score: int
    confidence: str
    reason: str
