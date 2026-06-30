"""Pydantic schemas for LBO engine inputs, outputs, and sensitivity grids."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LBOInputsSchema(BaseModel):
    """Pydantic schema for LBO model inputs."""

    entry_ev: float = Field(..., gt=0, description="Entry Enterprise Value")
    entry_ebitda: float = Field(..., gt=0, description="Entry EBITDA")
    debt_pct: float = Field(..., gt=0, lt=0.85, description="Debt as % of EV")
    revenue_growth: list[float] = Field(
        ..., description="Per-year revenue growth rates, length = hold_years"
    )
    margin_expansion: float = Field(
        0.0, description="Annual EBITDA margin expansion in bps (e.g. 0.005 = 50bps)"
    )
    exit_multiple: float = Field(..., gt=0, description="Exit EV/EBITDA multiple")
    hold_years: int = Field(..., ge=3, le=6, description="Hold period in years (3-6)")
    interest_rate: float = Field(0.08, ge=0, description="Annual interest rate on debt")
    amortization_rate: float = Field(0.10, ge=0, description="Annual debt amortization rate")

    @field_validator("hold_years")
    @classmethod
    def _check_hold_years(cls, v: int) -> int:
        if v not in {3, 4, 5, 6}:
            raise ValueError("hold_years must be 3, 4, 5, or 6")
        return v

    @field_validator("revenue_growth")
    @classmethod
    def _check_revenue_growth_length(cls, v: list[float], info) -> list[float]:
        hold_years = info.data.get("hold_years")
        if hold_years is not None and len(v) != hold_years:
            raise ValueError(
                f"len(revenue_growth) must equal hold_years ({hold_years}), got {len(v)}"
            )
        return v


class DebtScheduleItem(BaseModel):
    """A single year in the debt schedule."""

    year: int
    interest: float
    amortization: float
    ending_balance: float


class LBOResultSchema(BaseModel):
    """Pydantic schema for LBO model results."""

    entry_equity: float
    entry_debt: float
    debt_schedule: list[DebtScheduleItem]
    ebitda_projection: list[float]
    exit_ev: float
    exit_equity: float
    irr: float
    moic: float

    model_config = ConfigDict(from_attributes=True)


class SensitivityGridSchema(BaseModel):
    """Pydantic schema for IRR sensitivity grid output."""

    entry_multiples: list[float]
    exit_multiples: list[float]
    grid: list[list[float]]


class LBOAgentResponse(BaseModel):
    """Response schema for the LBO agent analysis endpoint."""

    lbo_result: dict | None = None
    scenarios: dict[str, dict] | None = None
    sensitivity_grid: dict | None = None
    interpretation: str | None = None
    errors: list[str] | None = None


class LBOScenario(BaseModel):
    """A named LBO scenario (e.g. base, bull, bear)."""

    name: str
    inputs: LBOInputsSchema
    result: LBOResultSchema
