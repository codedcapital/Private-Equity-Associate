"""Pydantic schemas for Financial resources."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class FinancialCreate(BaseModel):
    """Schema for creating a new financial snapshot."""

    company_id: int
    report_date: date

    # Raw fields
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    total_debt: float | None = None
    cash: float | None = None
    total_assets: float | None = None
    total_equity: float | None = None
    operating_cf: float | None = None
    capex: float | None = None

    # Computed fields
    net_debt: float | None = None
    fcf: float | None = None
    ebitda_margin: float | None = None
    net_debt_ebitda: float | None = None
    revenue_growth: float | None = None
    fcf_yield: float | None = None


class FinancialRead(BaseModel):
    """Schema for reading a financial snapshot (ORM-compatible)."""

    id: int
    company_id: int
    report_date: date

    # Raw fields
    revenue: float | None
    ebitda: float | None
    net_income: float | None
    total_debt: float | None
    cash: float | None
    total_assets: float | None
    total_equity: float | None
    operating_cf: float | None
    capex: float | None

    # Computed fields
    net_debt: float | None
    fcf: float | None
    ebitda_margin: float | None
    net_debt_ebitda: float | None
    revenue_growth: float | None
    fcf_yield: float | None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialProfile(BaseModel):
    """A focused view of the most commonly-used financial metrics."""

    revenue: float | None
    ebitda: float | None
    ebitda_margin: float | None
    revenue_growth: float | None
    net_debt: float | None
    net_debt_ebitda: float | None
    fcf: float | None
    fcf_yield: float | None


class FinancialList(BaseModel):
    """Schema for paginated financial list responses."""

    financials: list[FinancialRead]
    total: int
