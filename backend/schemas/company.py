"""Pydantic schemas for Company resources."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class CompanySource(str, Enum):
    """Where the company record originated."""

    SEC = "sec"
    COMPANIES_HOUSE = "companies_house"
    MANUAL = "manual"


class CompanyCreate(BaseModel):
    """Schema for creating a new company."""

    name: str
    ticker: str | None = None
    sector: str | None = None
    geography: str | None = None
    source: CompanySource


class CompanyRead(BaseModel):
    """Schema for reading a company (ORM-compatible)."""

    id: int
    name: str
    ticker: str | None
    sector: str | None
    geography: str | None
    source: CompanySource
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyList(BaseModel):
    """Schema for paginated company list responses."""

    companies: list[CompanyRead]
    total: int
