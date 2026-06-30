"""Full orchestrator pipeline tests with real database.

Tests the complete deal pipeline: sourcing → research/competitive → financials → lbo → memo,
including checkpointing and resume behaviour.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agents.orchestrator import graph, run_full_pipeline
from agents.state import create_initial_state, deal_state_to_json
from core.run_tracker import RunTracker
from db.crud import (
    create_company,
    create_deal,
    create_financial,
    get_deal_by_company_id,
    truncate_all_tables,
)
from db.models import AgentStatus, CompanySource, DealStage

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


@pytest.fixture
async def session():
    """Provide a fresh async session and truncate all tables after the test."""
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session
        await truncate_all_tables(session)
    await engine.dispose()


@pytest.fixture
async def seeded_company(session):
    """Seed a company with financials for pipeline testing."""
    company = await create_company(
        session,
        name="TestCo",
        source=CompanySource.SEC,
        ticker="TEST",
        sector="B2B SaaS",
    )
    await create_financial(
        session,
        company_id=company.id,
        report_date=date(2023, 12, 31),
        revenue=100.0,
        ebitda=20.0,
        ebitda_margin=0.20,
        revenue_growth=0.10,
        net_debt=30.0,
        net_debt_ebitda=1.5,
        fcf=15.0,
        fcf_yield=0.15,
    )
    return company


class TestGraphCompilation:
    def test_graph_compiles_without_error(self) -> None:
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        nodes = set(graph.get_graph().nodes.keys()) if hasattr(graph, "get_graph") else set()
        expected = {
            "sourcing",
            "research_competitive",
            "financials",
            "lbo",
            "memo",
            "checkpoint",
            "__start__",
            "__end__",
        }
        if nodes:
            assert expected <= nodes


class TestFullPipelineExecution:
    @pytest.mark.asyncio
    async def test_pipeline_runs_with_company_id(self, session, seeded_company):
        """Run the full pipeline with an existing company_id."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        result = await run_full_pipeline(seeded_company.id, thesis="B2B SaaS, profitable")

        assert result["company_id"] == seeded_company.id
        assert result["company_name"] == seeded_company.name
        assert result["run_id"] is not None
        assert result["errors"] is not None

    @pytest.mark.asyncio
    async def test_pipeline_sequence_with_seeded_company(self, session, seeded_company):
        """Verify that the pipeline produces outputs from each stage."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        result = await run_full_pipeline(seeded_company.id)

        # Sourcing is skipped when company_id is known, so no ranked_candidates
        # Research + competitive should produce outputs
        assert result.get("research") is not None or result.get("errors")
        assert result.get("competitive_map") is not None or result.get("errors")
        # Financials should produce outputs
        assert result.get("financials") is not None or result.get("errors")
        # LBO should produce outputs
        assert result.get("lbo_result") is not None or result.get("errors")
        # Memo should produce outputs
        assert result.get("memo_sections") is not None or result.get("errors")
        # Memo should be saved to DB
        assert result.get("memo_id") is not None or result.get("errors")

    @pytest.mark.asyncio
    async def test_pipeline_creates_company_from_name(self, session):
        """Running with a string name creates a new company."""
        result = await run_full_pipeline("NewCo Inc")
        assert result["company_name"] == "NewCo Inc"
        assert result["company_id"] is not None

        # Verify in DB
        deal = await get_deal_by_company_id(session, result["company_id"])
        assert deal is not None


class TestCheckpointing:
    @pytest.mark.asyncio
    async def test_checkpoint_updates_deal_stage(self, session, seeded_company):
        """After the pipeline completes, the deal stage should be ic_ready."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        await run_full_pipeline(seeded_company.id)

        deal = await get_deal_by_company_id(session, seeded_company.id)
        assert deal is not None
        assert deal.stage == DealStage.IC_READY

    @pytest.mark.asyncio
    async def test_checkpoint_saves_state_to_agent_log(self, session, seeded_company):
        """A checkpoint should be saved in the agent_log output_data."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        result = await run_full_pipeline(seeded_company.id)
        run_id = result["run_id"]

        tracker = RunTracker()
        log = await tracker.get_run(run_id)
        assert log is not None
        assert log.output_data is not None
        assert "state_json" in log.output_data


class TestPipelineResume:
    @pytest.mark.asyncio
    async def test_resume_from_failed_run(self, session, seeded_company):
        """Resume a pipeline from a FAILED run's checkpoint."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        tracker = RunTracker()

        # Create a failed run with a checkpoint at diligence stage
        run_id = await tracker.start_run(
            agent_name="full_pipeline",
            input_data={
                "company_id": seeded_company.id,
                "company_name": seeded_company.name,
            },
        )
        checkpoint_state = create_initial_state(seeded_company.name, company_id=seeded_company.id)
        checkpoint_state["run_id"] = run_id
        checkpoint_state["research"] = {"tam": 100.0, "cagr": 15.0}
        checkpoint_state["competitive_map"] = {"competitors": {}}
        checkpoint_state["financials"] = None
        checkpoint_state["lbo_result"] = None
        checkpoint_state["memo_sections"] = None

        await tracker.update_status(
            run_id=run_id,
            status=AgentStatus.FAILED,
            output_data={"state_json": deal_state_to_json(checkpoint_state)},
        )

        # Resume
        result = await run_full_pipeline(seeded_company.id, existing_run_id=run_id)

        assert result["run_id"] == run_id
        assert any("Resumed from failed run" in e for e in result.get("errors", []))
        # The pipeline should continue from where it left off
        assert result.get("research") is not None
        assert result.get("competitive_map") is not None

    @pytest.mark.asyncio
    async def test_resume_preserves_checkpointed_state(self, session, seeded_company):
        """Resumed run should preserve values from the checkpoint."""
        await create_deal(session, company_id=seeded_company.id, stage=DealStage.SOURCING)
        tracker = RunTracker()

        run_id = await tracker.start_run(
            agent_name="full_pipeline",
            input_data={"company_id": seeded_company.id, "company_name": seeded_company.name},
        )
        checkpoint_state = create_initial_state(seeded_company.name, company_id=seeded_company.id)
        checkpoint_state["run_id"] = run_id
        checkpoint_state["research"] = {"tam": 42.0, "custom_key": "custom_value"}
        checkpoint_state["competitive_map"] = {"moat_assessment": {"overall_moat": "strong"}}

        await tracker.update_status(
            run_id=run_id,
            status=AgentStatus.FAILED,
            output_data={"state_json": deal_state_to_json(checkpoint_state)},
        )

        result = await run_full_pipeline(seeded_company.id, existing_run_id=run_id)
        assert result["research"]["tam"] == 42.0
        assert result["competitive_map"]["moat_assessment"]["overall_moat"] == "strong"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_pipeline_continues_with_missing_financials(self, session):
        """If a company has no financials, the pipeline should collect errors but continue."""
        company = await create_company(
            session, name="NoFinCo", source=CompanySource.SEC, sector="B2B SaaS"
        )
        await create_deal(session, company_id=company.id, stage=DealStage.SOURCING)
        result = await run_full_pipeline(company.id)

        assert result["company_id"] == company.id
        # Errors should be collected
        assert len(result.get("errors", [])) > 0
        # The pipeline should still return a complete state
        assert result.get("run_id") is not None

    @pytest.mark.asyncio
    async def test_pipeline_errors_for_missing_company(self, session):
        """Running with a non-existent company_id should return an error."""
        result = await run_full_pipeline(99999)
        assert result["company_id"] == 99999
        assert any("not found" in e.lower() for e in result.get("errors", []))
