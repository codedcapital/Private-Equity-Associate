"""Pydantic schemas for Deal Pipeline resources."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class DealStage(str, Enum):
    """Pipeline stage for a deal."""

    SOURCING = "sourcing"
    DILIGENCE = "diligence"
    IC_READY = "ic_ready"
    PASSED = "passed"
    REJECTED = "rejected"
    CLOSED = "closed"


class DealCreate(BaseModel):
    """Schema for creating a new deal."""

    company_id: int
    stage: DealStage
    entry_ev: float | None = None
    entry_ebitda: float | None = None
    lbo_irr: float | None = None
    lbo_moic: float | None = None
    memo_id: int | None = None


class DealRead(BaseModel):
    """Schema for reading a deal (ORM-compatible)."""

    id: int
    company_id: int
    stage: DealStage
    entry_ev: float | None
    entry_ebitda: float | None
    lbo_irr: float | None
    lbo_moic: float | None
    memo_id: int | None
    last_updated: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealUpdate(BaseModel):
    """Schema for partial deal updates."""

    stage: DealStage | None = None
    entry_ev: float | None = None
    entry_ebitda: float | None = None
    lbo_irr: float | None = None
    lbo_moic: float | None = None
    memo_id: int | None = None


class DealList(BaseModel):
    """Schema for paginated deal list responses."""

    deals: list[DealRead]
    total: int
