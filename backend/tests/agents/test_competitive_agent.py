"""Tests for the CompetitiveAgent LangGraph pipeline.

Tests cover:
  - Individual node behaviour (identify_competitors, extract_profiles, build_matrix, assess_moat)
  - End-to-end graph execution
  - API endpoints (POST /agents/competitive)
  - Deterministic fallback competitors (no API keys required)

IMPORTANT: pytest-asyncio 1.4.0 has event-loop bugs with async fixtures.
We avoid async session fixtures and use the global ``async_session_factory``
directly in each test, wrapped in ``try/finally`` for cleanup.
``loop_scope="session"`` keeps all tests on the same event loop.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from agents.competitive import (
    assess_moat,
    build_matrix,
    competitive_graph,
    extract_profiles,
    identify_competitors,
    run_competitive,
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


async def test_identify_competitors_returns_real_competitors() -> None:
    """identify_competitors should return real, verifiable competitors."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Bill.com Holdings",
            source=CompanySource.MANUAL,
            ticker="BILL",
            sector="B2B SaaS",
        )
        company_id = company.id

    try:
        state = create_initial_state("Bill.com Holdings", company_id=company_id)
        state["sector"] = "B2B SaaS"
        result = await identify_competitors(state)

        competitors = result.get("competitors", [])
        assert len(competitors) >= 5, f"Expected >=5 competitors, got {len(competitors)}"
        assert len(competitors) <= 8, f"Expected <=8 competitors, got {len(competitors)}"

        # Every competitor must be a real company with a name
        for c in competitors:
            assert c["name"], "Competitor must have a name"
            assert c["source_db"], "Competitor must have a source_db"

        # All names should correspond to real, known companies (deterministic fallback)
        names = {c["name"].lower() for c in competitors}
        real_companies = {"stripe", "square", "melio", "tipalti", "avidxchange", "mineraltree"}
        assert names & real_companies, f"Expected at least one known competitor in {names}"
    finally:
        await _cleanup_db()


async def test_identify_competitors_caches_in_db() -> None:
    """identify_competitors should persist competitors to the competitor_companies table."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Monday.com",
            source=CompanySource.MANUAL,
            ticker="MNDY",
            sector="B2B SaaS",
        )
        company_id = company.id

    try:
        state = create_initial_state("Monday.com", company_id=company_id)
        state["sector"] = "B2B SaaS"
        await identify_competitors(state)

        async with async_session_factory() as session:
            from db.crud import list_competitor_companies
            cached = await list_competitor_companies(session, target_company_id=company_id)
            assert len(cached) > 0, "Competitors should be cached in DB"
    finally:
        await _cleanup_db()


async def test_extract_profiles_builds_complete_fields() -> None:
    """extract_profiles should populate all required profile fields."""
    state = create_initial_state("TestCo", company_id=1)
    state["competitors"] = [
        {"name": "Stripe", "domain": "stripe.com", "funding_stage": "Private", "hq_location": "SF", "source_db": "fallback"},
        {"name": "Square", "domain": "squareup.com", "funding_stage": "Public", "hq_location": "SF", "source_db": "fallback"},
    ]

    # Mock LLM so we don't need a real API key
    mock_profile = {
        "business_model": "Subscription + transaction fees",
        "pricing": "2.9% + 30¢ per transaction",
        "segment": "SMB to enterprise",
        "geography": "Global",
        "funding": "VC-backed",
        "key_differentiators": "Developer-first platform",
    }

    with patch("agents.competitive.graph.LLMClient") as MockLLM:
        instance = MockLLM.return_value
        instance.chat_structured = AsyncMock(return_value=type("Obj", (), {"model_dump": lambda self: mock_profile})())
        result = await extract_profiles(state)

    profiles = result.get("competitor_profiles", {})
    assert "Stripe" in profiles
    assert "Square" in profiles

    for name, prof in profiles.items():
        assert prof["business_model"] != "Unknown"
        assert prof["pricing"] != "Unknown"
        assert prof["segment"] != "Unknown"
        assert prof["geography"] != "Unknown"
        assert prof["funding"] != "Unknown"
        assert prof["key_differentiators"] != "Unknown"


async def test_build_matrix_has_complete_fields() -> None:
    """build_matrix should produce a matrix with all required attributes for every competitor."""
    state = create_initial_state("TestCo", company_id=1)
    state["competitor_profiles"] = {
        "Stripe": {
            "business_model": "Usage-based",
            "pricing": "2.9% + 30¢",
            "segment": "SMB, enterprise",
            "geography": "Global",
            "funding": "VC-backed",
            "key_differentiators": "Developer APIs",
        },
        "Square": {
            "business_model": "Hybrid",
            "pricing": "2.6% + 10¢",
            "segment": "SMB",
            "geography": "North America",
            "funding": "Public",
            "key_differentiators": "POS hardware",
        },
    }
    state["competitor_sources"] = ["fallback_sector_map"]

    result = await build_matrix(state)
    matrix = result.get("competitive_map", {}).get("competitors", {})

    assert "Stripe" in matrix
    assert "Square" in matrix

    for name, attrs in matrix.items():
        assert "business_model" in attrs
        assert "pricing" in attrs
        assert "segment" in attrs
        assert "geography" in attrs
        assert "funding" in attrs
        assert "source" in attrs


async def test_assess_moat_cites_specific_competitors() -> None:
    """assess_moat should produce a moat assessment that references competitors by name."""
    state = create_initial_state("Bill.com", company_id=1)
    state["competitors"] = [
        {"name": "Stripe", "domain": "stripe.com", "funding_stage": "Private", "hq_location": "SF", "source_db": "fallback"},
        {"name": "Square", "domain": "squareup.com", "funding_stage": "Public", "hq_location": "SF", "source_db": "fallback"},
    ]
    state["competitor_profiles"] = {
        "Stripe": {
            "business_model": "Usage-based",
            "pricing": "2.9% + 30¢",
            "segment": "SMB, enterprise",
            "geography": "Global",
            "funding": "VC-backed",
            "key_differentiators": "Developer APIs",
        },
        "Square": {
            "business_model": "Hybrid",
            "pricing": "2.6% + 10¢",
            "segment": "SMB",
            "geography": "North America",
            "funding": "Public",
            "key_differentiators": "POS hardware",
        },
    }
    state["competitive_map"] = {
        "competitors": {
            "Stripe": {
                "business_model": "Usage-based",
                "pricing": "2.9% + 30¢",
                "segment": "SMB, enterprise",
                "geography": "Global",
                "funding": "VC-backed",
                "source": "fallback",
            },
            "Square": {
                "business_model": "Hybrid",
                "pricing": "2.6% + 10¢",
                "segment": "SMB",
                "geography": "North America",
                "funding": "Public",
                "source": "fallback",
            },
        }
    }
    state["competitor_sources"] = ["fallback_sector_map"]
    state["structured_competitor_count"] = 0

    # Mock LLM
    mock_moat = {
        "switching_costs": "High — integrated AP workflows",
        "network_effects": "Moderate — network of vendors",
        "ip_proprietary_tech": "Strong — AI-powered invoice extraction",
        "distribution_advantages": "Strong — bank partnerships",
        "brand_reputation": "Strong — trusted by SMBs",
        "overall_moat": "Unlike Stripe, Bill.com focuses on AP/AR automation for mid-market.",
        "confidence_score": 0.5,
        "data_sources": ["fallback_sector_map"],
    }

    with patch("agents.competitive.graph.LLMClient") as MockLLM:
        instance = MockLLM.return_value
        instance.chat_structured = AsyncMock(return_value=type("Obj", (), {"model_dump": lambda self: mock_moat})())
        result = await assess_moat(state)

    moat = result.get("competitive_map", {}).get("moat_assessment", {})
    assert moat, "moat_assessment should be present"
    assert "overall_moat" in moat

    # The overall_moat should cite at least one competitor by name
    overall = moat["overall_moat"].lower()
    assert "stripe" in overall or "square" in overall, (
        f"Moat assessment should cite a specific competitor: {overall}"
    )

    # Confidence score and data sources should be set
    assert "confidence_score" in result["competitive_map"]
    assert "data_sources" in result["competitive_map"]


async def test_assess_moat_graceful_without_llm() -> None:
    """assess_moat should produce a fallback moat assessment when LLM is unavailable."""
    state = create_initial_state("TestCo", company_id=1)
    state["competitors"] = [
        {"name": "Stripe", "domain": "stripe.com", "funding_stage": "Private", "hq_location": "SF", "source_db": "fallback"},
    ]
    state["competitive_map"] = {
        "competitors": {
            "Stripe": {
                "business_model": "Usage-based",
                "pricing": "2.9% + 30¢",
                "segment": "SMB, enterprise",
                "geography": "Global",
                "funding": "VC-backed",
                "source": "fallback",
            }
        }
    }
    state["competitor_sources"] = ["fallback_sector_map"]
    state["structured_competitor_count"] = 0

    with patch("agents.competitive.graph.LLMClient") as MockLLM:
        instance = MockLLM.return_value
        instance.chat_structured = AsyncMock(side_effect=Exception("No API key"))
        result = await assess_moat(state)

    moat = result.get("competitive_map", {}).get("moat_assessment", {})
    assert moat, "Fallback moat assessment should be present"
    assert "Stripe" in moat.get("overall_moat", ""), "Fallback should mention competitor names"


# ── End-to-end graph tests ────────────────────────────────────────────────────


async def test_graph_end_to_end_with_fallback() -> None:
    """The full graph should run with deterministic fallback competitors (no API keys)."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Domo Inc",
            source=CompanySource.MANUAL,
            ticker="DOMO",
            sector="B2B SaaS / Analytics",
        )
        company_id = company.id

    try:
        # Mock LLM so no API key is needed
        mock_profile = {
            "business_model": "Subscription",
            "pricing": "Seat-based",
            "segment": "Enterprise",
            "geography": "Global",
            "funding": "Public",
            "key_differentiators": "BI platform",
        }
        mock_moat = {
            "switching_costs": "High",
            "network_effects": "Low",
            "ip_proprietary_tech": "Medium",
            "distribution_advantages": "Medium",
            "brand_reputation": "Medium",
            "overall_moat": "Unlike Tableau, Domo has a cloud-native architecture.",
            "confidence_score": 0.5,
            "data_sources": ["fallback_sector_map"],
        }

        with patch("agents.competitive.graph.LLMClient") as MockLLM:
            instance = MockLLM.return_value
            instance.chat_structured = AsyncMock(
                side_effect=[
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_moat})(),
                ]
            )
            final_state = await run_competitive(company_id)

        assert final_state.get("competitors")
        assert final_state.get("competitive_map")
        assert "competitors" in final_state["competitive_map"]
        assert "moat_assessment" in final_state["competitive_map"]
        assert "confidence_score" in final_state["competitive_map"]
        assert "data_sources" in final_state["competitive_map"]
    finally:
        await _cleanup_db()


async def test_graph_with_missing_company() -> None:
    """run_competitive should gracefully handle a missing company_id."""
    final_state = await run_competitive(99999)
    assert final_state["errors"] != []
    assert "not found" in str(final_state["errors"]).lower()


# ── API endpoint tests ───────────────────────────────────────────────────────


async def test_api_post_competitive_agent() -> None:
    """POST /agents/competitive should run the graph and return AgentRunResponse."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Bandwidth Inc",
            source=CompanySource.MANUAL,
            ticker="BAND",
            sector="CPaaS / Telecom",
        )
        company_id = company.id

    try:
        mock_profile = {
            "business_model": "Usage-based",
            "pricing": "Per-minute / per-message",
            "segment": "Enterprise",
            "geography": "North America",
            "funding": "Public",
            "key_differentiators": "Direct carrier relationships",
        }
        mock_moat = {
            "switching_costs": "High",
            "network_effects": "High",
            "ip_proprietary_tech": "Medium",
            "distribution_advantages": "High",
            "brand_reputation": "Medium",
            "overall_moat": "Unlike Twilio, Bandwidth owns its own network infrastructure.",
            "confidence_score": 0.5,
            "data_sources": ["fallback_sector_map"],
        }

        with patch("agents.competitive.graph.LLMClient") as MockLLM:
            instance = MockLLM.return_value
            instance.chat_structured = AsyncMock(
                side_effect=[
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_profile})(),
                    type("Obj", (), {"model_dump": lambda self: mock_moat})(),
                ]
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/agents/competitive",
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


async def test_api_post_competitive_missing_company() -> None:
    """POST /agents/competitive should return failed status for a missing company."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/agents/competitive",
            json={"company_id": 99999, "overrides": {}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "run_id" in data


async def test_api_health() -> None:
    """GET /agents/competitive/health should return ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/agents/competitive/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Deterministic fallback tests ─────────────────────────────────────────────


async def test_identify_competitors_cpaas_sector() -> None:
    """identify_competitors should use CPaaS fallback map for telecom companies."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Bandwidth Inc",
            source=CompanySource.MANUAL,
            ticker="BAND",
            sector="CPaaS / Telecom",
        )
        company_id = company.id

    try:
        state = create_initial_state("Bandwidth Inc", company_id=company_id)
        state["sector"] = "CPaaS / Telecom"
        result = await identify_competitors(state)

        competitors = result.get("competitors", [])
        names = {c["name"].lower() for c in competitors}
        cpaas_names = {"twilio", "vonage", "messagebird", "sinch", "plivo", "infobip"}
        assert names & cpaas_names, f"Expected CPaaS competitors in {names}"
    finally:
        await _cleanup_db()


async def test_identify_competitors_analytics_sector() -> None:
    """identify_competitors should use analytics fallback map for analytics companies."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name="Domo Inc",
            source=CompanySource.MANUAL,
            ticker="DOMO",
            sector="B2B SaaS / Analytics",
        )
        company_id = company.id

    try:
        state = create_initial_state("Domo Inc", company_id=company_id)
        state["sector"] = "B2B SaaS / Analytics"
        result = await identify_competitors(state)

        competitors = result.get("competitors", [])
        names = {c["name"].lower() for c in competitors}
        analytics_names = {"tableau", "power bi", "looker", "qlik", "sisense", "thoughtspot"}
        assert names & analytics_names, f"Expected analytics competitors in {names}"
    finally:
        await _cleanup_db()
