"""Unit tests for core/lbo_engine.py — LBO financial model engine.

All tests are deterministic, mathematically verifiable, and run without LLM calls.
"""

import math

import pytest

from core.lbo_engine import LBOInputs, LBOResult, run_lbo, sensitivity_grid


# ── Basic functional tests ─────────────────────────────────────────────────


def test_zero_debt_case():
    """Zero debt: debt_schedule should be empty or all zeros."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.01,  # minimum allowed (>0)
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    result = run_lbo(inputs)
    # With near-zero debt, the debt schedule should have tiny balances
    assert result.entry_debt == pytest.approx(10.0, abs=0.01)
    assert result.entry_equity == pytest.approx(990.0, abs=0.01)
    assert len(result.debt_schedule) == 3


def test_high_debt_84_percent():
    """84% debt should work (just under the 85% cap)."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.84,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    result = run_lbo(inputs)
    assert result.entry_debt == pytest.approx(840.0, abs=0.01)
    assert result.entry_equity == pytest.approx(160.0, abs=0.01)
    assert result.irr is not None
    assert result.moic is not None


def test_hundred_percent_debt_raises():
    """100% debt (debt_pct = 1.0) must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=1.0,
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="debt_pct"):
        run_lbo(inputs)


def test_negative_irr_scenario():
    """A case where exit_equity < entry_equity should produce negative IRR."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.0, 0.0, 0.0],  # no growth
        margin_expansion=0.0,
        exit_multiple=5.0,  # compressed multiple → exit EV below entry
        hold_years=3,
    )
    result = run_lbo(inputs)
    assert result.irr < 0
    assert result.moic < 1.0


def test_five_year_vs_three_year_hold():
    """Different hold periods produce different IRRs and debt schedules."""
    three = run_lbo(
        LBOInputs(
            entry_ev=1000,
            entry_ebitda=100,
            debt_pct=0.60,
            revenue_growth=[0.10, 0.10, 0.10],
            margin_expansion=0.005,
            exit_multiple=12.0,
            hold_years=3,
        )
    )
    five = run_lbo(
        LBOInputs(
            entry_ev=1000,
            entry_ebitda=100,
            debt_pct=0.60,
            revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
            margin_expansion=0.005,
            exit_multiple=12.0,
            hold_years=5,
        )
    )
    assert len(three.debt_schedule) == 3
    assert len(five.debt_schedule) == 5
    assert len(three.ebitda_projection) == 3
    assert len(five.ebitda_projection) == 5
    # Same entry equity / debt
    assert three.entry_equity == five.entry_equity
    assert three.entry_debt == five.entry_debt


def test_margin_expansion_grows_ebitda_more_than_revenue():
    """EBITDA should grow faster than pure revenue growth due to margin expansion."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.10, 0.10, 0.10],
        margin_expansion=0.01,  # 100 bps per year
        exit_multiple=10.0,
        hold_years=3,
    )
    result = run_lbo(inputs)
    # Pure revenue growth would give:
    #   y1 = 100 * 1.10 = 110
    #   y2 = 110 * 1.10 = 121
    #   y3 = 121 * 1.10 = 133.1
    # With margin expansion, each year gets an extra (1 + 0.01) multiplier.
    assert result.ebitda_projection[0] == pytest.approx(100 * 1.10 * 1.01, abs=0.001)
    assert result.ebitda_projection[1] == pytest.approx(
        100 * 1.10 * 1.01 * 1.10 * 1.01, abs=0.001
    )
    assert result.ebitda_projection[2] == pytest.approx(
        100 * (1.10 * 1.01) ** 3, abs=0.001
    )


def test_sensitivity_grid_dimensions():
    """Grid size must match the requested entry and exit multiple ranges."""
    base_inputs = LBOInputs(
        entry_ev=1200,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    grid = sensitivity_grid(
        base_inputs=base_inputs,
        entry_range=(10.0, 14.0, 1.0),
        exit_range=(8.0, 12.0, 2.0),
    )
    entry_multiples = grid["entry_multiples"]
    exit_multiples = grid["exit_multiples"]
    grid_data = grid["grid"]

    assert entry_multiples == [10.0, 11.0, 12.0, 13.0, 14.0]
    assert exit_multiples == [8.0, 10.0, 12.0]
    assert len(grid_data) == len(entry_multiples)
    for row in grid_data:
        assert len(row) == len(exit_multiples)


def test_revenue_growth_length_mismatch_raises():
    """Mismatch between revenue_growth length and hold_years must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.05, 0.05],  # only 2, but hold_years=3
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="revenue_growth"):
        run_lbo(inputs)


def test_negative_entry_ev_raises():
    """Negative entry_ev must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=-100,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="entry_ev"):
        run_lbo(inputs)


def test_moic_irr_identity():
    """MOIC should equal (1 + IRR)^hold_years within a small tolerance."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    result = run_lbo(inputs)
    expected_moic = (1.0 + result.irr) ** inputs.hold_years
    assert result.moic == pytest.approx(expected_moic, abs=0.001)


def test_exit_equity_equals_exit_ev_minus_ending_debt():
    """exit_equity must equal exit_ev minus the final ending debt balance."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    result = run_lbo(inputs)
    ending_debt = result.debt_schedule[-1]["ending_balance"]
    assert result.exit_equity == pytest.approx(result.exit_ev - ending_debt, abs=0.001)


def test_entry_equity_plus_debt_equals_entry_ev():
    """entry_equity + entry_debt must exactly equal entry_ev."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    result = run_lbo(inputs)
    assert result.entry_equity + result.entry_debt == pytest.approx(inputs.entry_ev, abs=0.001)


# ── Edge-case / boundary tests ─────────────────────────────────────────────


def test_debt_pct_exactly_85_raises():
    """debt_pct == 0.85 is an error (must be strictly < 0.85)."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.85,
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="debt_pct"):
        run_lbo(inputs)


def test_zero_entry_ebitda_raises():
    """Zero entry_ebitda must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=0,
        debt_pct=0.50,
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="entry_ebitda"):
        run_lbo(inputs)


def test_zero_exit_multiple_raises():
    """Zero exit_multiple must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.05, 0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=0.0,
        hold_years=3,
    )
    with pytest.raises(ValueError, match="exit_multiple"):
        run_lbo(inputs)


def test_invalid_hold_years_raises():
    """hold_years outside {3,4,5,6} must raise ValueError."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.50,
        revenue_growth=[0.05, 0.05],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=2,
    )
    with pytest.raises(ValueError, match="hold_years"):
        run_lbo(inputs)


# ── Manual-verification regression test ────────────────────────────────────


def test_manual_verification_regression():
    """Reproduce the exact manual verification case from the spec."""
    inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    result = run_lbo(inputs)

    # Entry
    assert result.entry_equity == pytest.approx(400.0, abs=0.01)
    assert result.entry_debt == pytest.approx(600.0, abs=0.01)

    # Debt schedule (10% amortization, 8% interest)
    # y1: bal=600, int=48, amort=60, end=540
    # y2: bal=540, int=43.2, amort=54, end=486
    # y3: bal=486, int=38.88, amort=48.6, end=437.4
    # y4: bal=437.4, int=34.992, amort=43.74, end=393.66
    # y5: bal=393.66, int=31.4928, amort=39.366, end=354.294
    assert result.debt_schedule[0]["interest"] == pytest.approx(48.0, abs=0.01)
    assert result.debt_schedule[0]["amortization"] == pytest.approx(60.0, abs=0.01)
    assert result.debt_schedule[0]["ending_balance"] == pytest.approx(540.0, abs=0.01)
    assert result.debt_schedule[-1]["ending_balance"] == pytest.approx(354.294, abs=0.01)

    # EBITDA projection
    # y1: 100 * 1.10 * 1.005 = 110.55
    # y2: 110.55 * 1.10 * 1.005 = 122.163525
    # y3: 122.163525 * 1.10 * 1.005 = 134.99478...
    # y4: 134.99478 * 1.10 * 1.005 = 149.23973...
    # y5: 149.23973 * 1.10 * 1.005 = 164.98352...
    assert result.ebitda_projection[0] == pytest.approx(110.55, abs=0.001)
    assert result.ebitda_projection[-1] == pytest.approx(165.1177395675376, abs=0.001)

    # Exit
    exit_ebitda = result.ebitda_projection[-1]
    exit_ev = exit_ebitda * 12.0
    assert result.exit_ev == pytest.approx(exit_ev, abs=0.001)
    assert result.exit_equity == pytest.approx(exit_ev - 354.294, abs=0.001)

    # IRR & MOIC
    # irr = (exit_equity / 400)^(1/5) - 1
    # moic = exit_equity / 400
    assert result.irr > 0
    assert result.moic > 1.0


# ── Sensitivity-grid specific tests ──────────────────────────────────────────


def test_sensitivity_grid_monotonicity():
    """Higher exit multiples should produce higher IRRs for the same entry."""
    base_inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    grid = sensitivity_grid(
        base_inputs=base_inputs,
        entry_range=(10.0, 14.0, 1.0),
        exit_range=(8.0, 14.0, 2.0),
    )
    for row in grid["grid"]:
        # Each row corresponds to a fixed entry multiple; as exit multiple rises,
        # IRR should rise (or at least not decrease).
        for i in range(1, len(row)):
            assert row[i] >= row[i - 1] - 1e-9


def test_sensitivity_grid_decreasing_with_entry():
    """Higher entry multiples should generally produce lower IRRs for the same exit."""
    base_inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    grid = sensitivity_grid(
        base_inputs=base_inputs,
        entry_range=(10.0, 14.0, 1.0),
        exit_range=(8.0, 14.0, 2.0),
    )
    for col_idx in range(len(grid["exit_multiples"])):
        column = [row[col_idx] for row in grid["grid"]]
        for i in range(1, len(column)):
            # Higher entry multiple → more equity at risk → lower IRR
            assert column[i] <= column[i - 1] + 1e-9


def test_sensitivity_grid_empty_range():
    """A single-point range should produce a 1x1 grid."""
    base_inputs = LBOInputs(
        entry_ev=1000,
        entry_ebitda=100,
        debt_pct=0.60,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        margin_expansion=0.005,
        exit_multiple=12.0,
        hold_years=5,
    )
    grid = sensitivity_grid(
        base_inputs=base_inputs,
        entry_range=(12.0, 12.0, 1.0),
        exit_range=(12.0, 12.0, 1.0),
    )
    assert grid["entry_multiples"] == [12.0]
    assert grid["exit_multiples"] == [12.0]
    assert len(grid["grid"]) == 1
    assert len(grid["grid"][0]) == 1


# ── Floating-point tolerance helpers ───────────────────────────────────────


def test_floating_point_tolerance_on_small_numbers():
    """Model should handle very small EV/EBITDA without crashing."""
    inputs = LBOInputs(
        entry_ev=1.0,
        entry_ebitda=0.1,
        debt_pct=0.50,
        revenue_growth=[0.0, 0.0, 0.0],
        margin_expansion=0.0,
        exit_multiple=10.0,
        hold_years=3,
    )
    result = run_lbo(inputs)
    assert result.entry_equity == pytest.approx(0.5, abs=0.0001)
    assert result.entry_debt == pytest.approx(0.5, abs=0.0001)
