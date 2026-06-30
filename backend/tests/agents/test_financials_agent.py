"""Tests for the FinancialsAgent LangGraph pipeline.

Tests cover:
  - Individual node behaviour (load_data, compute_ratios, flag_risks)
  - End-to-end graph execution
  - API endpoints (GET /agents/financials/{id}, POST /agents/financials)

IMPORTANT: pytest-asyncio 1.4.0 (ancient version) has event-loop bugs with async
fixtures.  We avoid async session fixtures entirely and use the global
``async_session_factory`` directly in each test, wrapped in ``try/finally``
for cleanup.  ``loop_scope="session"`` keeps all tests on the same event loop
so the global SQLAlchemy engine works correctly.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from agents.financials import (
    compute_ratios,
    flag_risks,
    load_data,
    run_financial_analysis,
)
from agents.state import create_initial_state
from api.main import app
from db.crud import create_company, create_financial, truncate_all_tables
from db.models import CompanySource
from db.session import async_session_factory
from schemas.financials import FinancialProfile

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _cleanup_db() -> None:
    """Truncate all tables after a test."""
    async with async_session_factory() as session:
        await truncate_all_tables(session)


# ── Node unit tests ─────────────────────────────────────────────────────────


async def test_load_data_fetches_financials() -> None:
    """load_data should populate state['financials'] from the latest DB row."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="LoadCo", source=CompanySource.MANUAL, ticker="LOAD"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=1000.0,
            ebitda=200.0,
            net_income=50.0,
            total_debt=300.0,
            cash=100.0,
            total_assets=800.0,
            total_equity=400.0,
            operating_cf=150.0,
            capex=50.0,
            net_debt=200.0,
            fcf=100.0,
            ebitda_margin=0.20,
            net_debt_ebitda=1.0,
            revenue_growth=0.15,
            fcf_yield=0.10,
        )
        # Older period to ensure load_data picks the latest
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2023, 12, 31),
            revenue=800.0,
            ebitda=150.0,
            ebitda_margin=0.1875,
            net_debt=250.0,
            net_debt_ebitda=1.6667,
            revenue_growth=0.10,
            fcf_yield=0.08,
        )
        company_id = company.id

    try:
        state = create_initial_state("LoadCo", company_id=company_id)
        result = await load_data(state)

        assert result["financials"] is not None
        assert result["financials"].revenue == pytest.approx(1000.0)
        assert result["financials"].ebitda == pytest.approx(200.0)
        assert result["financials"].ebitda_margin == pytest.approx(0.20)
        assert result["financials"].net_debt_ebitda == pytest.approx(1.0)
        assert result["financials"].revenue_growth == pytest.approx(0.15)
        assert result["financials"].fcf_yield == pytest.approx(0.10)
        assert result["errors"] == []
    finally:
        await _cleanup_db()


async def test_compute_ratios_recomputes_missing_values() -> None:
    """compute_ratios should derive missing ratios from raw DB fields."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="RatioCo", source=CompanySource.MANUAL, ticker="RATIO"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=1000.0,
            ebitda=200.0,
            total_debt=300.0,
            cash=100.0,
            operating_cf=150.0,
            capex=50.0,
            # No computed ratios provided
        )
        company_id = company.id

    try:
        state = create_initial_state("RatioCo", company_id=company_id)
        state = await load_data(state)
        assert state["financials"].ebitda_margin is None

        result = await compute_ratios(state)
        financials = result["financials"]
        assert financials is not None
        assert financials.ebitda_margin == pytest.approx(0.20)
        assert financials.net_debt == pytest.approx(200.0)
        assert financials.net_debt_ebitda == pytest.approx(1.0)
        assert financials.fcf == pytest.approx(100.0)
        assert financials.fcf_yield == pytest.approx(0.10)
    finally:
        await _cleanup_db()


async def test_flag_risks_triggers_all_thresholds() -> None:
    """flag_risks should append the correct flags for risky metrics."""
    state = create_initial_state("RiskCo", company_id=999)
    state["financials"] = FinancialProfile(
        revenue=100.0,
        ebitda=5.0,
        ebitda_margin=0.05,
        revenue_growth=-0.05,
        net_debt=500.0,
        net_debt_ebitda=10.0,
        fcf=1.0,
        fcf_yield=0.01,
    )

    result = await flag_risks(state)
    flags = result.get("risk_flags", [])

    assert "leverage concern" in flags
    assert "declining revenue" in flags
    assert "low profitability" in flags
    assert "poor cash conversion" in flags
    assert len(flags) == 4


async def test_flag_risks_no_flags_for_healthy_metrics() -> None:
    """flag_risks should return an empty list for healthy metrics."""
    state = create_initial_state("HealthyCo", company_id=998)
    state["financials"] = FinancialProfile(
        revenue=1000.0,
        ebitda=200.0,
        ebitda_margin=0.20,
        revenue_growth=0.15,
        net_debt=200.0,
        net_debt_ebitda=1.0,
        fcf=100.0,
        fcf_yield=0.10,
    )

    result = await flag_risks(state)
    flags = result.get("risk_flags", [])
    assert flags == []


# ── End-to-end graph test ───────────────────────────────────────────────────


async def test_graph_end_to_end() -> None:
    """The full graph should run load_data → compute_ratios → flag_risks → interpret."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="E2ECo", source=CompanySource.MANUAL, ticker="E2E"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=1000.0,
            ebitda=200.0,
            total_debt=300.0,
            cash=100.0,
            operating_cf=150.0,
            capex=50.0,
            net_debt=200.0,
            fcf=100.0,
            ebitda_margin=0.20,
            net_debt_ebitda=1.0,
            revenue_growth=0.15,
            fcf_yield=0.10,
        )
        company_id = company.id

    try:
        final_state = await run_financial_analysis(company_id)

        assert final_state["financials"] is not None
        assert final_state["financials"].revenue == pytest.approx(1000.0)
        assert final_state.get("risk_flags") == []
        assert "interpretation" in final_state
        # Graph should complete without critical errors
        assert "not found" not in str(final_state.get("errors", [])).lower()
    finally:
        await _cleanup_db()


async def test_graph_with_missing_company() -> None:
    """run_financial_analysis should gracefully handle a missing company_id."""
    final_state = await run_financial_analysis(99999)
    assert final_state["errors"] != []
    assert "not found" in str(final_state["errors"]).lower()


# ── API endpoint tests ─────────────────────────────────────────────────────


async def test_api_get_financial_profile() -> None:
    """GET /agents/financials/{company_id} should return the latest FinancialProfile."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="APICo", source=CompanySource.MANUAL, ticker="API"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=500.0,
            ebitda=100.0,
            total_debt=200.0,
            cash=50.0,
            operating_cf=80.0,
            capex=20.0,
            net_debt=150.0,
            fcf=60.0,
            ebitda_margin=0.20,
            net_debt_ebitda=1.5,
            revenue_growth=0.10,
            fcf_yield=0.12,
        )
        company_id = company.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/agents/financials/{company_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["revenue"] == pytest.approx(500.0)
        assert data["ebitda"] == pytest.approx(100.0)
        assert data["ebitda_margin"] == pytest.approx(0.20)
        assert data["net_debt_ebitda"] == pytest.approx(1.5)
    finally:
        await _cleanup_db()


async def test_api_get_financial_profile_not_found() -> None:
    """GET /agents/financials/{company_id} should 404 when no financials exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/agents/financials/99999")
    assert response.status_code == 404


async def test_api_post_agents_financials() -> None:
    """POST /agents/financials should run the graph and return AgentRunResponse."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="POSTCo", source=CompanySource.MANUAL, ticker="POST"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=800.0,
            ebitda=160.0,
            total_debt=250.0,
            cash=50.0,
            operating_cf=120.0,
            capex=40.0,
            net_debt=200.0,
            fcf=80.0,
            ebitda_margin=0.20,
            net_debt_ebitda=1.25,
            revenue_growth=0.12,
            fcf_yield=0.10,
        )
        company_id = company.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/financials",
                json={"company_id": company_id, "overrides": {}},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "run_id" in data
        assert len(data["run_id"]) == 36
        assert "message" in data
    finally:
        await _cleanup_db()


async def test_api_post_agents_financials_missing_company() -> None:
    """POST /agents/financials should return a failed status for a missing company."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/agents/financials",
            json={"company_id": 99999, "overrides": {}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "run_id" in data


async def test_graph_with_seeded_data_bill() -> None:
    """Run the graph against a freshly-created company to simulate seeded data."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="BILL", source=CompanySource.MANUAL, ticker="BILL"
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=1200.0,
            ebitda=240.0,
            total_debt=360.0,
            cash=120.0,
            operating_cf=180.0,
            capex=60.0,
            net_debt=240.0,
            fcf=120.0,
            ebitda_margin=0.20,
            net_debt_ebitda=1.0,
            revenue_growth=0.15,
            fcf_yield=0.10,
        )
        company_id = company.id

    try:
        final_state = await run_financial_analysis(company_id)
        assert final_state["financials"] is not None
        assert final_state["financials"].revenue is not None
        assert "interpretation" in final_state
        assert "risk_flags" in final_state
    finally:
        await _cleanup_db()
