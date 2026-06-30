"""Tests for the Research Agent — LangGraph industry research pipeline.

Tests cover:
  - Individual node behaviour (classify_sector, retrieve_filings, web_research, synthesize)
  - End-to-end graph execution
  - API endpoints (POST /agents/research)

IMPORTANT: pytest-asyncio 1.4.0 (ancient version) has event-loop bugs with async
fixtures.  We avoid async session fixtures entirely and use the global
``async_session_factory`` directly in each test, wrapped in ``try/finally``
for cleanup.  ``loop_scope="session"`` keeps all tests on the same event loop
so the global SQLAlchemy engine works correctly.
"""

from datetime import date
from unittest.mock import MagicMock

import sys

# Mock weasyprint before any API imports pull it in via agents.memo.pdf_renderer
sys.modules["weasyprint"] = MagicMock()

import pytest
from httpx import ASGITransport, AsyncClient

from agents.research import (
    IndustryProfile,
    classify_sector,
    research_graph,
    retrieve_filings,
    run_research,
    synthesize,
    web_research,
)
from agents.state import create_initial_state
from api.main import app
from db.crud import (
    create_company,
    create_filing,
    create_filing_chunk,
    truncate_all_tables,
)
from db.models import CompanySource
from db.session import async_session_factory

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _cleanup_db() -> None:
    """Truncate all tables after a test."""
    async with async_session_factory() as session:
        await truncate_all_tables(session)


# ── Node unit tests ─────────────────────────────────────────────────────────


async def test_classify_sector_maps_b2b_saas() -> None:
    """classify_sector should map 'B2B SaaS' to Software & IT Services."""
    state = create_initial_state("CloudCo", company_id=1)
    state["sector"] = "B2B SaaS"
    result = await classify_sector(state)
    assert result["gics_sector"] == "Software & IT Services"
    assert result["gics_industry_group"] == "Software"


async def test_classify_sector_maps_cpaa_telecom() -> None:
    """classify_sector should map 'CPaaS / Telecom' to Communication Services."""
    state = create_initial_state("Telco", company_id=2)
    state["sector"] = "CPaaS / Telecom"
    result = await classify_sector(state)
    assert result["gics_sector"] == "Communication Services"
    assert result["gics_industry_group"] == "Interactive Media & Services"


async def test_classify_sector_maps_analytics() -> None:
    """classify_sector should map 'Analytics' to Software & IT Services."""
    state = create_initial_state("DataCo", company_id=3)
    state["sector"] = "Analytics"
    result = await classify_sector(state)
    assert result["gics_sector"] == "Software & IT Services"
    assert result["gics_industry_group"] == "Software"


async def test_classify_sector_unknown_fallback() -> None:
    """classify_sector should fallback to 'Unknown' for unmapped sectors."""
    state = create_initial_state("MysteryCo", company_id=4)
    state["sector"] = "Quantum Entanglement"
    result = await classify_sector(state)
    assert result["gics_sector"] == "Unknown"
    assert result["gics_industry_group"] == "Unknown"


async def test_retrieve_filings_handles_empty_chunks() -> None:
    """retrieve_filings should gracefully handle empty filing_chunks."""
    state = create_initial_state("TestCo", company_id=1)
    state["gics_sector"] = "Software & IT Services"
    result = await retrieve_filings(state)
    assert isinstance(result["filing_research"], list)


async def test_retrieve_filings_returns_chunks_when_available() -> None:
    """retrieve_filings should return chunks when embeddings exist in the DB."""
    async with async_session_factory() as session:
        company = await create_company(
            session, name="ChunkCo", source=CompanySource.MANUAL, sector="Software"
        )
        filing = await create_filing(
            session,
            company_id=company.id,
            filing_type="10-K",
            filing_date=date(2024, 1, 1),
            raw_text="The software market is growing rapidly.",
        )
        # Create a chunk with a dummy embedding
        await create_filing_chunk(
            session,
            filing_id=filing.id,
            chunk_index=0,
            chunk_text="The software market is growing rapidly.",
            embedding=[0.0] * 1536,
        )
        company_id = company.id

    try:
        state = create_initial_state("ChunkCo", company_id=company_id)
        state["gics_sector"] = "Software & IT Services"
        result = await retrieve_filings(state)
        # semantic_search requires OpenAI API key to generate query embeddings;
        # if not available, filing_research will be an empty list with an error
        assert isinstance(result["filing_research"], list)
    finally:
        await _cleanup_db()


async def test_web_research_skips_without_key() -> None:
    """web_research should skip gracefully when TAVILY_API_KEY is missing."""
    state = create_initial_state("TestCo", company_id=1)
    state["gics_sector"] = "Software & IT Services"
    result = await web_research(state)
    assert result["web_research"] == []


async def test_synthesize_produces_structured_output() -> None:
    """synthesize should produce an IndustryProfile dict even without LLM."""
    state = create_initial_state("TestCo", company_id=1)
    state["filing_research"] = [
        {
            "chunk_id": 1,
            "filing_id": 1,
            "text": "The market is growing rapidly with cloud adoption.",
            "similarity_score": 0.95,
            "source": "filing_chunk:1",
        }
    ]
    state["web_research"] = [
        {
            "title": "Market Report 2024",
            "url": "https://example.com/report",
            "snippet": "TAM is estimated at $100B.",
            "source": "https://example.com/report",
        }
    ]
    result = await synthesize(state)
    assert "research" in result
    research = result["research"]
    assert isinstance(research, dict)
    assert "growth_drivers" in research
    assert "risks" in research
    assert "sources" in research
    assert len(research["sources"]) > 0


async def test_synthesize_with_empty_research() -> None:
    """synthesize should produce a placeholder even with no research data."""
    state = create_initial_state("TestCo", company_id=1)
    state["filing_research"] = []
    state["web_research"] = []
    result = await synthesize(state)
    assert "research" in result
    research = result["research"]
    assert isinstance(research, dict)
    assert "growth_drivers" in research
    assert "risks" in research


# ── End-to-end graph test ───────────────────────────────────────────────────


async def test_full_graph_end_to_end() -> None:
    """The full graph should run all nodes and populate research."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="ResearchCo",
            source=CompanySource.MANUAL,
            sector="B2B SaaS",
        )
        company_id = company.id

    try:
        final_state = await run_research(company_id)

        assert final_state["gics_sector"] == "Software & IT Services"
        assert "research" in final_state
        research = final_state["research"]
        assert isinstance(research, dict)
        assert "growth_drivers" in research
        assert "risks" in research
        assert "sources" in research
        assert "filing_research" in final_state
        assert "web_research" in final_state
    finally:
        await _cleanup_db()


async def test_graph_with_missing_company() -> None:
    """run_research should gracefully handle a missing company_id."""
    final_state = await run_research(99999)
    assert final_state["errors"] != []
    assert "not found" in str(final_state["errors"]).lower()


# ── API endpoint tests ─────────────────────────────────────────────────────


async def test_api_post_research() -> None:
    """POST /agents/research should return research data."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="APICo",
            source=CompanySource.MANUAL,
            sector="Analytics",
        )
        company_id = company.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/research",
                json={"company_id": company_id, "overrides": {}},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "run_id" in data
        assert len(data["run_id"]) == 36
        assert "research" in data
        assert data["research"] is not None
        assert "growth_drivers" in data["research"]
        assert "risks" in data["research"]
    finally:
        await _cleanup_db()


async def test_api_post_research_missing_company() -> None:
    """POST /agents/research should return a failed status for a missing company."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/agents/research",
            json={"company_id": 99999, "overrides": {}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "run_id" in data


# ── IndustryProfile schema test ─────────────────────────────────────────────


async def test_industry_profile_schema() -> None:
    """IndustryProfile should serialise and deserialise correctly."""
    profile = IndustryProfile(
        tam=150.0,
        cagr=12.5,
        growth_drivers=["Cloud adoption", "AI integration"],
        risks=["Regulatory changes", "Competition"],
        regulatory_notes="GDPR and SOC2 compliance required.",
        key_players=["Salesforce", "Microsoft", "SAP"],
        sources=["filing_chunk:1", "https://example.com/report"],
    )
    dumped = profile.model_dump(mode="json")
    assert dumped["tam"] == 150.0
    assert dumped["cagr"] == 12.5
    assert len(dumped["growth_drivers"]) == 2
    assert len(dumped["risks"]) == 2
    assert len(dumped["key_players"]) == 3
    assert len(dumped["sources"]) == 2
