"""Pydantic schemas for Investment View resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InvestmentViewCreate(BaseModel):
    """Schema for creating a new investment view."""

    deal_id: int
    content: dict = Field(default_factory=dict)
    recommendation: str | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=100.0)
    authored_by: str = "system"
    status: str = "draft"


class InvestmentViewUpdate(BaseModel):
    """Schema for updating an investment view."""

    content: dict | None = None
    recommendation: str | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=100.0)
    edited_by: str | None = None
    status: str | None = None


class InvestmentViewRead(BaseModel):
    """Schema for reading an investment view."""

    id: int
    deal_id: int
    version: int
    content: dict
    recommendation: str | None = None
    confidence_score: float | None = None
    authored_by: str
    edited_by: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestmentViewHistoryResponse(BaseModel):
    """Response with all versions of an investment view for a deal."""

    deal_id: int
    views: list[InvestmentViewRead]
    total_versions: int

    model_config = ConfigDict(from_attributes=True)
