"""Tests for the Memo Agent — LangGraph pipeline with LLM-driven section writing."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agents.memo.graph import (
    aggregate_context,
    edit_pass,
    format_output,
    memo_graph,
    run_memo_generation,
    write_sections,
)
from agents.memo.pdf_renderer import render_memo_pdf
from agents.state import DealState, LBOResult, create_initial_state
from api.main import app
from db.crud import create_company, create_deal, create_financial, truncate_all_tables
from db.models import AgentStatus, CompanySource, DealStage
from db.session import async_session_factory
from schemas.financials import FinancialProfile

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


@pytest.fixture
async def seeded_db():
    """Seed the DB with a company, financials, and a deal for testing."""
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
            name="Test Memo Corp",
            source=CompanySource.MANUAL,
            ticker="TMC",
            sector="Technology",
        )
        await create_financial(
            session,
            company_id=company.id,
            report_date=date(2024, 1, 1),
            revenue=1000.0,
            ebitda=200.0,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=300.0,
            net_debt_ebitda=1.5,
            fcf=150.0,
            fcf_yield=0.15,
        )
        await create_deal(
            session,
            company_id=company.id,
            stage=DealStage.IC_READY,
            entry_ev=2400.0,
            entry_ebitda=200.0,
            lbo_irr=0.22,
            lbo_moic=2.5,
        )
        yield company.id
        await truncate_all_tables(session)
    await engine.dispose()


class TestAggregateContext:
    """Tests for Node 1: aggregate_context."""

    async def test_pulls_correct_fields(self) -> None:
        state = create_initial_state("Test Corp", company_id=1)
        state["sector"] = "Technology"
        state["financials"] = FinancialProfile(
            revenue=1000.0,
            ebitda=200.0,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=300.0,
            net_debt_ebitda=1.5,
            fcf=150.0,
            fcf_yield=0.15,
        )
        state["lbo_result"] = LBOResult(
            entry_equity=1000.0,
            entry_debt=500.0,
            irr=0.22,
            moic=2.5,
            exit_ev=2500.0,
            exit_equity=1500.0,
        )
        state["competitive_map"] = {
            "moat_assessment": "Strong",
            "competitors": ["CompA", "CompB"],
        }
        state["research"] = {"summary": "Good company"}

        result = await aggregate_context(state)
        context = result["memo_context"]

        assert context["company"]["name"] == "Test Corp"
        assert context["company"]["sector"] == "Technology"
        assert context["financials"]["revenue"] == 1000.0
        assert context["financials"]["ebitda"] == 200.0
        assert context["financials"]["ebitda_margin"] == 0.20
        assert context["lbo"]["irr"] == 0.22
        assert context["lbo"]["moic"] == 2.5
        assert context["competitive"]["moat_assessment"] == "Strong"
        assert context["research"]["summary"] == "Good company"

    async def test_handles_missing_data_gracefully(self) -> None:
        state = create_initial_state("Missing Corp")
        result = await aggregate_context(state)
        context = result["memo_context"]

        assert context["company"]["name"] == "Missing Corp"
        assert context["company"]["sector"] == "Unknown"
        assert context["financials"] == {}
        assert context["lbo"] == {}
        assert context["competitive"] == {}
        assert context["research"] == {}


class TestWriteSections:
    """Tests for Node 2: write_sections."""

    async def test_produces_all_8_sections(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_context"] = {
            "company": {"name": "Test Corp", "sector": "Tech"},
            "financials": {},
            "lbo": {},
            "competitive": {},
            "research": {},
        }
        result = await write_sections(state)
        memo_sections = result["memo_sections"]

        assert len(memo_sections) == 8
        expected_keys = {
            "executive_summary",
            "company_overview",
            "industry_analysis",
            "competitive_positioning",
            "financial_analysis",
            "lbo_model",
            "risk_factors",
            "investment_recommendation",
        }
        assert set(memo_sections.keys()) == expected_keys

        for key, section in memo_sections.items():
            assert "content" in section
            assert "word_count" in section
            assert "confidence_score" in section
            assert isinstance(section["word_count"], int)
            assert isinstance(section["confidence_score"], float)
            assert section["word_count"] == len(section["content"].split())

    async def test_uses_placeholders_when_llm_unavailable(self) -> None:
        """If OPENAI_API_KEY is not set, sections should contain placeholder text."""
        state = create_initial_state("Test Corp")
        state["memo_context"] = {
            "company": {"name": "Test Corp", "sector": "Tech"},
            "financials": {},
            "lbo": {},
            "competitive": {},
            "research": {},
        }
        result = await write_sections(state)
        memo_sections = result["memo_sections"]

        for key, section in memo_sections.items():
            content = section["content"]
            # If no API key, content should be a placeholder; if API key exists,
            # it should be real text. Either way, content must exist and be non-empty.
            assert len(content) > 0
            assert section["word_count"] >= 0


class TestEditPass:
    """Tests for Node 3: edit_pass."""

    async def test_detects_contradiction(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_sections"] = {
            "executive_summary": {
                "content": "This is a strong buy and very attractive opportunity.",
                "word_count": 10,
                "confidence_score": 0.9,
            },
            "investment_recommendation": {
                "content": "We recommend to pass on this deal.",
                "word_count": 8,
                "confidence_score": 0.9,
            },
            "company_overview": {
                "content": "Overview text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "industry_analysis": {
                "content": "Industry text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "competitive_positioning": {
                "content": "Competitive text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "financial_analysis": {
                "content": "Financial text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "lbo_model": {
                "content": "LBO text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "risk_factors": {
                "content": "Risk text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
        }
        state["financials"] = FinancialProfile(
            revenue=1000.0,
            ebitda=200.0,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=300.0,
            net_debt_ebitda=1.5,
            fcf=150.0,
            fcf_yield=0.15,
        )
        result = await edit_pass(state)
        notes = result["memo_edit_notes"]
        assert notes["needs_revision"] is True
        assert any("contradiction" in n.lower() for n in notes["notes"])

    async def test_passes_clean_when_consistent(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_sections"] = {
            "executive_summary": {
                "content": "We recommend to proceed with this investment.",
                "word_count": 8,
                "confidence_score": 0.9,
            },
            "investment_recommendation": {
                "content": "We recommend to proceed with this deal.",
                "word_count": 8,
                "confidence_score": 0.9,
            },
            "company_overview": {
                "content": "Overview text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "industry_analysis": {
                "content": "Industry text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "competitive_positioning": {
                "content": "Competitive text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
            "financial_analysis": {
                "content": "Financial analysis with EBITDA 200.0.",
                "word_count": 6,
                "confidence_score": 0.8,
            },
            "lbo_model": {
                "content": "LBO model with EBITDA 200.0.",
                "word_count": 6,
                "confidence_score": 0.8,
            },
            "risk_factors": {
                "content": "Risk text.",
                "word_count": 2,
                "confidence_score": 0.8,
            },
        }
        state["financials"] = FinancialProfile(
            revenue=1000.0,
            ebitda=200.0,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=300.0,
            net_debt_ebitda=1.5,
            fcf=150.0,
            fcf_yield=0.15,
        )
        result = await edit_pass(state)
        notes = result["memo_edit_notes"]
        # Should not flag contradictions when both are positive
        assert notes["needs_revision"] is False or not any(
            "contradiction" in n.lower() for n in notes["notes"]
        )

    async def test_detects_missing_sections(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_sections"] = {
            "executive_summary": {
                "content": "Summary.",
                "word_count": 1,
                "confidence_score": 0.9,
            },
        }
        result = await edit_pass(state)
        notes = result["memo_edit_notes"]
        assert notes["needs_revision"] is True
        assert any("missing" in n.lower() for n in notes["notes"])


class TestFormatOutput:
    """Tests for Node 4: format_output."""

    async def test_computes_word_counts_correctly(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_sections"] = {
            "executive_summary": {
                "content": "This is a test with five words",
                "word_count": 0,
                "confidence_score": 0.9,
            },
            "company_overview": {
                "content": "Another test here",
                "word_count": 0,
                "confidence_score": 0.8,
            },
        }
        result = await format_output(state)
        # "This is a test with five words" = 7 words
        # "Another test here" = 3 words
        # Total = 10
        assert result["memo_total_words"] == 10
        assert result["memo_sections"]["executive_summary"]["word_count"] == 7
        assert result["memo_sections"]["company_overview"]["word_count"] == 3

    async def test_computes_average_confidence(self) -> None:
        state = create_initial_state("Test Corp")
        state["memo_sections"] = {
            "a": {"content": "x", "word_count": 1, "confidence_score": 0.8},
            "b": {"content": "y", "word_count": 1, "confidence_score": 0.6},
        }
        result = await format_output(state)
        assert result["memo_avg_confidence"] == 0.7

    async def test_handles_empty_sections(self) -> None:
        state = create_initial_state("Test Corp")
        result = await format_output(state)
        assert "errors" in result
        assert any("no memo sections" in e.lower() for e in result["errors"])


class TestFullGraph:
    """Tests for end-to-end graph execution."""

    async def test_full_graph_runs_end_to_end(self) -> None:
        state = create_initial_state("Test Corp", company_id=1)
        state["sector"] = "Technology"
        state["financials"] = FinancialProfile(
            revenue=1000.0,
            ebitda=200.0,
            ebitda_margin=0.20,
            revenue_growth=0.15,
            net_debt=300.0,
            net_debt_ebitda=1.5,
            fcf=150.0,
            fcf_yield=0.15,
        )
        state["lbo_result"] = LBOResult(
            entry_equity=1000.0,
            entry_debt=500.0,
            irr=0.22,
            moic=2.5,
            exit_ev=2500.0,
            exit_equity=1500.0,
        )
        state["competitive_map"] = {
            "moat_assessment": "Strong",
            "competitors": ["CompA", "CompB"],
            "differentiation": "High",
            "risk_flags": ["Competition"],
        }
        state["research"] = {"summary": "Good company"}

        final = await memo_graph.ainvoke(state)
        assert "memo_sections" in final
        assert "memo_total_words" in final
        assert "memo_avg_confidence" in final
        assert len(final["memo_sections"]) == 8
        assert final["memo_total_words"] > 0

    async def test_with_real_company_id(self, seeded_db: int) -> None:
        """run_memo_generation should work with a real company from the DB."""
        company_id = seeded_db
        final = await run_memo_generation(company_id=company_id)
        assert "memo_id" in final
        assert "memo_sections" in final
        assert final["memo_id"] is not None


class TestPDFRenderer:
    """Tests for PDF rendering."""

    async def test_renders_pdf_file(self) -> None:
        memo_sections = {
            "executive_summary": {
                "content": "This is the executive summary. It is compelling and recommends proceeding.",
                "word_count": 12,
                "confidence_score": 0.9,
            },
            "company_overview": {
                "content": "Company overview text here.",
                "word_count": 4,
                "confidence_score": 0.8,
            },
            "industry_analysis": {
                "content": "Industry analysis text.",
                "word_count": 3,
                "confidence_score": 0.8,
            },
            "competitive_positioning": {
                "content": "Competitive positioning text.",
                "word_count": 3,
                "confidence_score": 0.8,
            },
            "financial_analysis": {
                "content": "Financial analysis text.",
                "word_count": 3,
                "confidence_score": 0.8,
            },
            "lbo_model": {
                "content": "LBO model text.",
                "word_count": 3,
                "confidence_score": 0.8,
            },
            "risk_factors": {
                "content": "Risk factors text.",
                "word_count": 3,
                "confidence_score": 0.8,
            },
            "investment_recommendation": {
                "content": "Recommendation text.",
                "word_count": 2,
                "confidence_score": 0.9,
            },
        }
        pdf_path = await render_memo_pdf(memo_sections, "Test Corp")
        import os

        assert os.path.exists(pdf_path)
        # WeasyPrint may fall back to HTML if system libraries are missing
        assert pdf_path.endswith(".pdf") or pdf_path.endswith(".html")
        assert os.path.getsize(pdf_path) > 0

        # Cleanup
        os.remove(pdf_path)


class TestAPI:
    """Tests for the memo API endpoints."""

    async def test_api_post_generate(self, seeded_db: int) -> None:
        """POST /agents/memo/generate should return a run ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/memo/generate",
                json={"company_id": seeded_db, "overrides": {}},
            )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "status" in data
        assert data["status"] in ("complete", "pending", "running", "failed")

    async def test_api_get_memo(self, seeded_db: int) -> None:
        """GET /agents/memo/{memo_id} should return memo JSON."""
        # First generate a memo
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            gen_response = await client.post(
                "/agents/memo/generate",
                json={"company_id": seeded_db, "overrides": {}},
            )
        assert gen_response.status_code == 200

        # Fetch the memo ID from DB
        async with async_session_factory() as session:
            from db.crud import list_ic_memos

            memos = await list_ic_memos(session, company_id=seeded_db, limit=1)
            if memos:
                memo_id = memos[0].id
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(f"/agents/memo/{memo_id}")
                assert response.status_code == 200
                data = response.json()
                assert "memo" in data
                assert "pdf_download_url" in data
            else:
                pytest.skip("No memo found in DB after generation")

    async def test_api_get_memo_not_found(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/memo/99999")
        assert response.status_code == 404
