"""LBO (Leveraged Buyout) financial model engine.

Pure Python, deterministic, mathematically verifiable.
No LLM involved — all formulas are explicit and unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LBOInputs:
    """Inputs for a single LBO model run."""

    entry_ev: float
    entry_ebitda: float
    debt_pct: float
    revenue_growth: list[float]
    margin_expansion: float
    exit_multiple: float
    hold_years: int
    interest_rate: float = 0.08
    amortization_rate: float = 0.10


@dataclass
class LBOResult:
    """Output of a single LBO model run."""

    entry_equity: float
    entry_debt: float
    debt_schedule: list[dict]
    ebitda_projection: list[float]
    exit_ev: float
    exit_equity: float
    irr: float
    moic: float


def _validate_inputs(inputs: LBOInputs) -> None:
    """Validate LBO inputs and raise ValueError on violations."""
    if inputs.entry_ev <= 0:
        raise ValueError(f"entry_ev must be > 0, got {inputs.entry_ev}")
    if inputs.entry_ebitda <= 0:
        raise ValueError(f"entry_ebitda must be > 0, got {inputs.entry_ebitda}")
    if not (0.0 < inputs.debt_pct < 0.85):
        raise ValueError(
            f"debt_pct must be > 0 and < 0.85, got {inputs.debt_pct}"
        )
    if inputs.exit_multiple <= 0:
        raise ValueError(f"exit_multiple must be > 0, got {inputs.exit_multiple}")
    if inputs.hold_years not in {3, 4, 5, 6}:
        raise ValueError(
            f"hold_years must be 3, 4, 5, or 6, got {inputs.hold_years}"
        )
    if len(inputs.revenue_growth) != inputs.hold_years:
        raise ValueError(
            f"len(revenue_growth) must equal hold_years ({inputs.hold_years}), "
            f"got {len(inputs.revenue_growth)}"
        )


def run_lbo(inputs: LBOInputs) -> LBOResult:
    """Run the LBO model and return an LBOResult.

    Formulas (from ROADMAP):
      Entry:
        entry_equity = EV * (1 - debt_pct)
        entry_debt   = EV * debt_pct

      Debt schedule (each year):
        interest       = beginning_balance * interest_rate
        amortization   = beginning_balance * amortization_rate
        ending_balance = beginning_balance - amortization

      EBITDA projection:
        base = entry_ebitda
        year 1: base * (1 + revenue_growth[0]) * (1 + margin_expansion)
        year 2: year_1_ebitda * (1 + revenue_growth[1]) * (1 + margin_expansion)
        ... etc

      Exit:
        exit_ebitda = final year EBITDA
        exit_ev     = exit_ebitda * exit_multiple
        exit_equity = exit_ev - ending_debt (debt remaining at end)

      Returns:
        irr  = (exit_equity / entry_equity)^(1 / hold_years) - 1
        moic = exit_equity / entry_equity
    """
    _validate_inputs(inputs)

    # ── Entry ────────────────────────────────────────────────────────────────
    entry_equity = inputs.entry_ev * (1.0 - inputs.debt_pct)
    entry_debt = inputs.entry_ev * inputs.debt_pct

    # ── Debt schedule ──────────────────────────────────────────────────────────
    debt_schedule: list[dict] = []
    balance = entry_debt
    for _year in range(1, inputs.hold_years + 1):
        interest = balance * inputs.interest_rate
        amortization = balance * inputs.amortization_rate
        ending_balance = balance - amortization
        debt_schedule.append(
            {
                "year": _year,
                "interest": interest,
                "amortization": amortization,
                "ending_balance": ending_balance,
            }
        )
        balance = ending_balance

    ending_debt = debt_schedule[-1]["ending_balance"] if debt_schedule else 0.0

    # ── EBITDA projection ────────────────────────────────────────────────────
    ebitda_projection: list[float] = []
    current_ebitda = inputs.entry_ebitda
    for g in inputs.revenue_growth:
        current_ebitda = current_ebitda * (1.0 + g) * (1.0 + inputs.margin_expansion)
        ebitda_projection.append(current_ebitda)

    exit_ebitda = ebitda_projection[-1] if ebitda_projection else inputs.entry_ebitda

    # ── Exit ─────────────────────────────────────────────────────────────────
    exit_ev = exit_ebitda * inputs.exit_multiple
    exit_equity = exit_ev - ending_debt

    # ── Returns ──────────────────────────────────────────────────────────────
    if entry_equity <= 0:
        # Should not happen because entry_ev > 0 and debt_pct < 1, but guard anyway.
        irr = float("-inf")
        moic = float("-inf")
    else:
        irr = (exit_equity / entry_equity) ** (1.0 / inputs.hold_years) - 1.0
        moic = exit_equity / entry_equity

    return LBOResult(
        entry_equity=entry_equity,
        entry_debt=entry_debt,
        debt_schedule=debt_schedule,
        ebitda_projection=ebitda_projection,
        exit_ev=exit_ev,
        exit_equity=exit_equity,
        irr=irr,
        moic=moic,
    )


def sensitivity_grid(
    base_inputs: LBOInputs,
    entry_range: tuple[float, float, float],  # min, max, step for entry multiple
    exit_range: tuple[float, float, float],  # min, max, step for exit multiple
) -> dict:
    """Generate an IRR sensitivity grid by varying entry and exit multiples.

    The entry multiple is derived from entry_ev / entry_ebitda.  We vary the
    entry_ev proportionally while keeping entry_ebitda fixed, so the entry
    multiple changes.  All other assumptions (debt_pct, revenue_growth, etc.)
    remain constant.

    Returns:
        {
            "entry_multiples": [12.0, 13.0, 14.0],
            "exit_multiples":  [10.0, 11.0, 12.0],
            "grid": [
                [0.15, 0.18, 0.21],  # row for entry=12.0
                [0.12, 0.15, 0.18],  # row for entry=13.0
                [0.09, 0.12, 0.15],  # row for entry=14.0
            ]
        }
    """
    entry_min, entry_max, entry_step = entry_range
    exit_min, exit_max, exit_step = exit_range

    # Build entry-multiple list
    entry_multiples: list[float] = []
    em = entry_min
    while em <= entry_max + 1e-9:
        entry_multiples.append(round(em, 6))
        em += entry_step

    # Build exit-multiple list
    exit_multiples: list[float] = []
    xm = exit_min
    while xm <= exit_max + 1e-9:
        exit_multiples.append(round(xm, 6))
        xm += exit_step

    # Base entry multiple derived from current inputs
    base_entry_multiple = base_inputs.entry_ev / base_inputs.entry_ebitda

    grid: list[list[float]] = []
    for em in entry_multiples:
        # Scale entry_ev to match the target entry multiple
        scaled_entry_ev = base_inputs.entry_ebitda * em
        row: list[float] = []
        for xm in exit_multiples:
            inputs = LBOInputs(
                entry_ev=scaled_entry_ev,
                entry_ebitda=base_inputs.entry_ebitda,
                debt_pct=base_inputs.debt_pct,
                revenue_growth=list(base_inputs.revenue_growth),
                margin_expansion=base_inputs.margin_expansion,
                exit_multiple=xm,
                hold_years=base_inputs.hold_years,
                interest_rate=base_inputs.interest_rate,
                amortization_rate=base_inputs.amortization_rate,
            )
            result = run_lbo(inputs)
            row.append(result.irr)
        grid.append(row)

    return {
        "entry_multiples": entry_multiples,
        "exit_multiples": exit_multiples,
        "grid": grid,
    }
