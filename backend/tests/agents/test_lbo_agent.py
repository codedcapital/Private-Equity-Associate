"""Tests for LBO Agent — LangGraph pipeline with LBO engine."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agents.lbo.graph import (
    generate_sensitivity,
    interpret,
    lbo_graph,
    prepare_inputs,
    run_lbo_analysis,
    run_model,
)
from api.main import app
from db.crud import create_company, create_financial, truncate_all_tables
from db.models import CompanySource
from schemas.financials import FinancialProfile

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


@pytest.fixture
async def seeded_db():
    """Seed the DB with a company and financials for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        company = await create_company(
            session,
            name="Test LBO Corp",
            source=CompanySource.MANUAL,
            ticker="TEST",
            sector="Technology",
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 1, 1),
            revenue=1000.0,
            ebitda=200.0,
            total_debt=500.0,
            cash=100.0,
            operating_cf=150.0,
            capex=30.0,
        )
        yield company.id
        await truncate_all_tables(session)
    await engine.dispose()


async def test_prepare_inputs_produces_scenarios():
    """Node 1: prepare_inputs should build base, bull, and bear scenarios."""
    state = {
        "company_name": "Test",
        "company_id": 1,
        "financials": FinancialProfile(
            revenue=1000.0,
            ebitda=100.0,
            ebitda_margin=0.10,
            revenue_growth=0.05,
            net_debt=400.0,
            net_debt_ebitda=4.0,
            fcf=50.0,
            fcf_yield=0.05,
        ),
        "errors": [],
    }
    result = await prepare_inputs(state)
    scenarios = result["lbo_scenarios"]
    assert "base" in scenarios
    assert "bull" in scenarios
    assert "bear" in scenarios
    assert scenarios["base"].debt_pct == 0.60
    assert scenarios["bull"].debt_pct == 0.65
    assert scenarios["bear"].debt_pct == 0.55
    assert scenarios["base"].exit_multiple == 12.0
    assert scenarios["bull"].exit_multiple == 14.0
    assert scenarios["bear"].exit_multiple == 10.0
    assert scenarios["base"].hold_years == 5
    assert scenarios["base"].entry_ev == 1200.0


async def test_run_model_executes_all_scenarios():
    """Node 2: run_model should execute run_lbo for all 3 scenarios."""
    state = {
        "company_name": "Test",
        "company_id": 1,
        "financials": FinancialProfile(
            revenue=1000.0,
            ebitda=100.0,
            ebitda_margin=0.10,
            revenue_growth=0.05,
            net_debt=400.0,
            net_debt_ebitda=4.0,
            fcf=50.0,
            fcf_yield=0.05,
        ),
        "errors": [],
    }
    state = await prepare_inputs(state)
    result = await run_model(state)
    lbo_results = result["lbo_results"]
    assert "base" in lbo_results
    assert "bull" in lbo_results
    assert "bear" in lbo_results
    assert result["lbo_result"]["irr"] == lbo_results["base"].irr
    assert result["lbo_result"]["moic"] == lbo_results["base"].moic


async def test_generate_sensitivity_dimensions():
    """Node 3: generate_sensitivity should produce a 9x9 grid."""
    state = {
        "company_name": "Test",
        "company_id": 1,
        "financials": FinancialProfile(
            revenue=1000.0,
            ebitda=100.0,
            ebitda_margin=0.10,
            revenue_growth=0.05,
            net_debt=400.0,
            net_debt_ebitda=4.0,
            fcf=50.0,
            fcf_yield=0.05,
        ),
        "errors": [],
    }
    state = await prepare_inputs(state)
    state = await run_model(state)
    result = await generate_sensitivity(state)
    grid = result["lbo_sensitivity"]
    assert grid["entry_multiples"] == [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    assert grid["exit_multiples"] == [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    assert len(grid["grid"]) == 9
    assert len(grid["grid"][0]) == 9


async def test_full_graph_end_to_end():
    """Full graph should run all nodes and populate all expected keys."""
    state = {
        "company_name": "Test",
        "company_id": 1,
        "financials": FinancialProfile(
            revenue=1000.0,
            ebitda=100.0,
            ebitda_margin=0.10,
            revenue_growth=0.05,
            net_debt=400.0,
            net_debt_ebitda=4.0,
            fcf=50.0,
            fcf_yield=0.05,
        ),
        "errors": [],
    }
    final = await lbo_graph.ainvoke(state)
    assert "lbo_result" in final
    assert "lbo_results" in final
    assert "lbo_sensitivity" in final
    assert "lbo_interpretation" in final
    assert "base" in final["lbo_results"]
    assert "bull" in final["lbo_results"]
    assert "bear" in final["lbo_results"]


async def test_with_real_company_id(seeded_db):
    """run_lbo_analysis should work with a real company from the DB."""
    company_id = seeded_db
    final = await run_lbo_analysis(company_id=company_id)
    assert "lbo_result" in final
    assert "lbo_results" in final
    assert "base" in final["lbo_results"]


async def test_api_post_lbo(seeded_db):
    """POST /agents/lbo should return full LBO analysis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/agents/lbo",
            json={"company_id": seeded_db, "overrides": {"entry_multiple": 12.0}},
        )
    assert response.status_code == 200
    data = response.json()
    assert "lbo_result" in data
    assert "scenarios" in data
    assert "base" in data["scenarios"]
    assert "bull" in data["scenarios"]
    assert "bear" in data["scenarios"]
    assert "sensitivity_grid" in data


async def test_api_get_lbo(seeded_db):
    """GET /agents/lbo/{company_id} should return LBO analysis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/agents/lbo/{seeded_db}")
    assert response.status_code == 200
    data = response.json()
    assert "lbo_result" in data
    assert "scenarios" in data
    assert "sensitivity_grid" in data
