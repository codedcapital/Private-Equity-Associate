"""Pydantic schemas for Confidence Ledger resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceFactor(BaseModel):
    """A single factor contributing to or reducing confidence."""

    name: str
    weight: float = Field(..., ge=0.0, le=1.0)
    contribution: float | None = None
    penalty: float | None = None
    status: str


class ConfidenceLedgerCreate(BaseModel):
    """Schema for creating a confidence ledger."""

    deal_id: int
    version: int = 1
    base_score: int = Field(..., ge=0, le=100)
    factors: list[ConfidenceFactor] = Field(default_factory=list)
    final_score: int = Field(..., ge=0, le=100)
    bottlenecks: list[str] = Field(default_factory=list)


class ConfidenceLedgerRead(BaseModel):
    """Schema for reading a confidence ledger."""

    id: int
    deal_id: int
    version: int
    base_score: int
    factors: dict
    final_score: int
    bottlenecks: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfidenceLedgerBreakdown(BaseModel):
    """Human-readable confidence breakdown for the frontend."""

    deal_id: int
    final_score: int
    base_score: int
    factors: list[ConfidenceFactor]
    bottlenecks: list[str]
    reduced_because: list[str]

    model_config = ConfigDict(from_attributes=True)
