"""Pydantic schemas for Competitor resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetitorCreate(BaseModel):
    """Schema for creating a new competitor record."""

    target_company_id: int
    name: str
    domain: str | None = None
    source_db: str
    sector: str | None = None
    funding_stage: str | None = None
    hq_location: str | None = None


class CompetitorRead(BaseModel):
    """Schema for reading a competitor record (ORM-compatible)."""

    id: int
    target_company_id: int
    name: str
    domain: str | None
    source_db: str
    sector: str | None
    funding_stage: str | None
    hq_location: str | None
    last_verified: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorList(BaseModel):
    """Schema for paginated competitor list responses."""

    competitors: list[CompetitorRead]
    total: int
