"""Pydantic schemas for Diligence Item resources."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DiligenceItemCreate(BaseModel):
    """Schema for creating a new diligence item."""

    deal_id: int
    category: str
    title: str
    description: str | None = None
    status: str = "not_started"
    assigned_to: str | None = None
    due_date: date | None = None
    evidence_id: int | None = None
    priority: str = "medium"
    created_by: str | None = None


class DiligenceItemUpdate(BaseModel):
    """Schema for updating a diligence item."""

    category: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    due_date: date | None = None
    evidence_id: int | None = None
    priority: str | None = None
    completed_at: datetime | None = None


class DiligenceItemRead(BaseModel):
    """Schema for reading a diligence item."""

    id: int
    deal_id: int
    category: str
    title: str
    description: str | None = None
    status: str
    assigned_to: str | None = None
    due_date: date | None = None
    evidence_id: int | None = None
    priority: str
    created_by: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DiligenceListResponse(BaseModel):
    """Response with all diligence items for a deal."""

    deal_id: int
    items: list[DiligenceItemRead]
    total: int
    by_status: dict[str, int]

    model_config = ConfigDict(from_attributes=True)
