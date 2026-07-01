"""Pydantic schemas for Deal Event resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DealEventCreate(BaseModel):
    """Schema for creating a deal event."""

    deal_id: int
    event_type: str
    actor_type: str = "system"
    actor_id: str | None = None
    description: str
    event_metadata: dict | None = None


class DealEventRead(BaseModel):
    """Schema for reading a deal event."""

    id: int
    deal_id: int
    event_type: str
    actor_type: str
    actor_id: str | None = None
    description: str
    event_metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealEventFeedResponse(BaseModel):
    """Response with recent deal events."""

    deal_id: int
    events: list[DealEventRead]
    total: int

    model_config = ConfigDict(from_attributes=True)
