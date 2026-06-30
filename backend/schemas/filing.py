"""Pydantic schemas for Filing resources."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class FilingCreate(BaseModel):
    """Schema for creating a new filing."""

    company_id: int
    filing_type: str
    filing_date: date
    accession_number: str | None = None
    raw_text: str | None = None


class FilingRead(BaseModel):
    """Schema for reading a filing (ORM-compatible)."""

    id: int
    company_id: int
    filing_type: str
    filing_date: date
    accession_number: str | None
    raw_text: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilingList(BaseModel):
    """Schema for paginated filing list responses."""

    filings: list[FilingRead]
    total: int
