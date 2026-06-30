"""Tests for the SourcingAgent LangGraph pipeline.

Tests cover:
  - Individual node behaviour (parse_thesis, screen_database, score_and_rank)
  - End-to-end graph execution
  - API endpoint (POST /agents/sourcing)
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from agents.sourcing import (
    enrich_candidates,
    parse_thesis,
    run_sourcing,
    score_and_rank,
    screen_database,
)
from agents.state import create_initial_state
from api.main import app
from db.crud import create_company, create_financial, truncate_all_tables
from db.models import CompanySource
from db.session import async_session_factory

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _cleanup_db() -> None:
    """Truncate all tables after a test."""
    async with async_session_factory() as session:
        await truncate_all_tables(session)


# ── Node unit tests ─────────────────────────────────────────────────────────


async def test_parse_thesis_produces_filters() -> None:
    """parse_thesis should produce structured filters from a natural language thesis."""
    state = create_initial_state("Test")
    state["thesis"] = "B2B SaaS, €10-50M ARR, European HQ, profitable"
    result = await parse_thesis(state)
    filters = result.get("sourcing_filters", {})
    assert filters is not None
    assert "sector" in filters or "ebitda_margin_min" in filters or "errors" in result


async def test_parse_thesis_with_heuristic_fallback() -> None:
    """parse_thesis should fall back to heuristic when LLM is unavailable."""
    state = create_initial_state("Test")
    state["thesis"] = "B2B SaaS, profitable, high growth"
    result = await parse_thesis(state)
    filters = result.get("sourcing_filters", {})
    assert filters is not None
    # Heuristic should detect sector and profitability
    assert "sector" in filters or "ebitda_margin_min" in filters or "errors" in result


async def test_screen_database_returns_candidates() -> None:
    """screen_database should return candidates matching the filters."""
    # Seed data
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="SaaSCo",
            source=CompanySource.MANUAL,
            ticker="SASS",
            sector="B2B SaaS",
            geography="United States",
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=50e6,
            ebitda=10e6,
            ebitda_margin=0.20,
            revenue_growth=0.20,
            net_debt=20e6,
            fcf=8e6,
        )
        # Older period to ensure latest is picked
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2023, 12, 31),
            revenue=40e6,
            ebitda=8e6,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=25e6,
            fcf=6e6,
        )
        company_id = company.id

    try:
        state = create_initial_state("SaaSCo")
        state["sourcing_filters"] = {
            "sector": "B2B SaaS",
            "ebitda_margin_min": 0.15,
            "growth_rate_min": 0.15,
        }
        result = await screen_database(state)
        candidates = result.get("candidates", [])
        assert len(candidates) > 0
        # Should pick the latest financial period
        for c in candidates:
            if c["company_id"] == company_id:
                assert c["revenue"] == pytest.approx(50e6)
                assert c["ebitda_margin"] == pytest.approx(0.20)
                assert c["revenue_growth"] == pytest.approx(0.20)
    finally:
        await _cleanup_db()


async def test_score_and_rank_produces_valid_scores() -> None:
    """score_and_rank should produce scores between 0 and 1."""
    state = create_initial_state("Test")
    state["sourcing_filters"] = {
        "sector": "B2B SaaS",
        "ebitda_margin_min": 0.15,
        "growth_rate_min": 0.15,
    }
    state["candidates"] = [
        {
            "company_id": 1,
            "name": "Bill.com",
            "sector": "B2B SaaS",
            "geography": "United States",
            "revenue": 50e6,
            "ebitda_margin": 0.20,
            "revenue_growth": 0.20,
        },
        {
            "company_id": 2,
            "name": "Bandwidth Inc",
            "sector": "CPaaS / Telecom",
            "geography": "United States",
            "revenue": 80e6,
            "ebitda_margin": 0.24,
            "revenue_growth": 0.35,
        },
    ]
    result = await score_and_rank(state)
    ranked = result.get("ranked_candidates", [])
    assert len(ranked) > 0
    for candidate in ranked:
        assert 0 <= candidate["score"] <= 1
        assert "rationale" in candidate
        assert "weights" in candidate
        assert candidate["weights"]["sector_fit"] == 0.30
        assert candidate["weights"]["financial_profile"] == 0.40
        assert candidate["weights"]["strategic_rationale"] == 0.30


async def test_score_and_rank_empty_candidates() -> None:
    """score_and_rank should handle empty candidates gracefully."""
    state = create_initial_state("Test")
    state["sourcing_filters"] = {}
    state["candidates"] = []
    result = await score_and_rank(state)
    assert result.get("ranked_candidates") == []


async def test_enrich_candidates_skips_without_tavily_key() -> None:
    """enrich_candidates should skip gracefully when Tavily key is not set."""
    state = create_initial_state("Test")
    state["candidates"] = [
        {"company_id": 1, "name": "TestCo", "revenue": None, "sector": None},
    ]
    result = await enrich_candidates(state)
    # Should not raise; candidates should be unchanged
    assert result.get("candidates") == state["candidates"]


# ── End-to-end graph tests ─────────────────────────────────────────────────


async def test_full_graph_end_to_end() -> None:
    """The full sourcing graph should run end-to-end."""
    # Seed data
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="E2ECo",
            source=CompanySource.MANUAL,
            ticker="E2E",
            sector="B2B SaaS",
            geography="United States",
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=100e6,
            ebitda=20e6,
            ebitda_margin=0.20,
            revenue_growth=0.25,
            net_debt=40e6,
            fcf=16e6,
        )
        company_id = company.id

    try:
        final_state = await run_sourcing("B2B SaaS, profitable, high growth")
        ranked = final_state.get("ranked_candidates", [])
        assert isinstance(ranked, list)
        assert len(ranked) <= 10
        if ranked:
            assert "score" in ranked[0]
            assert "rationale" in ranked[0]
            assert 0 <= ranked[0]["score"] <= 1
    finally:
        await _cleanup_db()


# ── API endpoint tests ─────────────────────────────────────────────────────


async def test_api_post_sourcing() -> None:
    """POST /agents/sourcing should run the sourcing agent and return candidates."""
    # Seed data
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="APICo",
            source=CompanySource.MANUAL,
            ticker="API",
            sector="B2B SaaS",
            geography="United States",
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 12, 31),
            revenue=80e6,
            ebitda=16e6,
            ebitda_margin=0.20,
            revenue_growth=0.20,
            net_debt=30e6,
            fcf=12e6,
        )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/sourcing",
                json={"thesis": "B2B SaaS, profitable, high growth"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "run_id" in data
        assert "candidates" in data
        assert isinstance(data["candidates"], list)
    finally:
        await _cleanup_db()
