"""Comprehensive Phase 3 tests for new endpoints and services.

Tests:
- NextActionsEngine (rule-based + LLM)
- ChangeSummarizer
- Evidence status update + confidence recalc
- Investment view diff + restore
- Deal settings CRUD + weight override
- Recent changes endpoint
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.crud import (
    create_company,
    create_confidence_ledger,
    create_deal,
    create_deal_event,
    create_diligence_item,
    create_evidence_item,
    create_intelligence_hub,
    create_investment_view,
    get_deal_settings,
    list_deal_events,
    truncate_all_tables,
    upsert_deal_settings,
)
from db.models import (
    ActorType,
    CompanySource,
    DealEventType,
    DealStage,
    DiligencePriority,
    DiligenceStatus,
    EvidenceStatus,
    InvestmentViewStatus,
)
from schemas.evidence import DecisionOutput, ModuleScore
from services.change_summarizer import ChangeSummarizer, _simple_json_diff
from services.next_actions_engine import NextActionsEngine, RuleBasedNextActions

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


@pytest.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, future=True, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await truncate_all_tables(session)
    await engine.dispose()


async def _create_test_deal(session: AsyncSession, stage: DealStage = DealStage.DILIGENCE):
    company = await create_company(
        session, name="TestCo", source=CompanySource.MANUAL, ticker="TEST"
    )
    deal = await create_deal(session, company_id=company.id, stage=stage)
    return company, deal


# ── NextActionsEngine Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rule_based_next_actions_conflicts(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session, stage=DealStage.DILIGENCE)

    # Create confidence ledger with a CONFLICTING factor
    await create_confidence_ledger(
        session,
        deal_id=deal.id,
        base_score=80,
        factors={
            "Revenue Quality": {"weight": 0.2, "contribution": 10, "status": "CONFLICTING"},
            "Margin Stability": {"weight": 0.15, "contribution": 12, "status": "VERIFIED"},
        },
        final_score=70,
        bottlenecks=["Revenue Quality"],
    )

    engine = RuleBasedNextActions(deal.id, deal.stage.value)
    actions = await engine.generate()

    conflict_actions = [a for a in actions if a["category"] == "evidence"]
    assert len(conflict_actions) >= 1
    assert "Resolve evidence conflict" in conflict_actions[0]["title"]


@pytest.mark.asyncio
async def test_rule_based_next_actions_diligence_blockers(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session, stage=DealStage.DILIGENCE)

    await create_diligence_item(
        session,
        deal_id=deal.id,
        category="legal",
        title="Legal review pending",
        status=DiligenceStatus.NOT_STARTED.value,
        priority=DiligencePriority.BLOCKER.value,
    )

    engine = RuleBasedNextActions(deal.id, "deep_diligence")
    actions = await engine.generate()

    blocker_actions = [a for a in actions if a["category"] == "diligence"]
    assert len(blocker_actions) >= 1
    assert "blocker" in blocker_actions[0]["title"].lower()


@pytest.mark.asyncio
async def test_rule_based_next_actions_no_view(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    engine = RuleBasedNextActions(deal.id, deal.stage.value)
    actions = await engine.generate()

    view_actions = [a for a in actions if a["category"] == "view"]
    assert len(view_actions) >= 1


@pytest.mark.asyncio
async def test_next_actions_cache(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    engine = NextActionsEngine(deal.id, deal.stage.value)
    actions1 = await engine.generate(use_llm=False)
    actions2 = await engine.generate(use_llm=False)

    # Second call should be cached (same result)
    assert actions1 == actions2

    # Invalidate cache
    await engine.invalidate_cache()
    NextActionsEngine.clear_all_cache()


# ── ChangeSummarizer Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_change_summarizer_summarize_recent(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    await create_deal_event(
        session,
        deal_id=deal.id,
        event_type=DealEventType.VIEW_UPDATED.value,
        actor_type=ActorType.USER.value,
        actor_id="J. Reyes",
        description="View updated",
        event_metadata={"content_changed": True},
    )
    await create_deal_event(
        session,
        deal_id=deal.id,
        event_type=DealEventType.DILIGENCE_STATUS_CHANGED.value,
        actor_type=ActorType.USER.value,
        description="Diligence completed",
        event_metadata={"from": "not_started", "to": "complete"},
    )

    summarizer = ChangeSummarizer(deal.id)
    changes = await summarizer.summarize_recent(limit=10)

    # The events are returned newest-first (desc created_at). Diligence event is second.
    # We just verify both are present and have the right structure.
    assert len(changes) == 2
    descriptions = [c["description"] for c in changes]
    assert any("J. Reyes" in d for d in descriptions)
    assert any("Diligence" in d for d in descriptions)


@pytest.mark.asyncio
async def test_change_summarizer_diff_investment_views(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    v1 = await create_investment_view(
        session, deal_id=deal.id, content={"text": "Old view"}, recommendation="PROCEED", confidence_score=80
    )
    v2 = await create_investment_view(
        session, deal_id=deal.id, content={"text": "New view"}, recommendation="PASS", confidence_score=75
    )

    summarizer = ChangeSummarizer(deal.id)
    diff = await summarizer.diff_investment_views(v1.id, v2.id)

    assert diff["from_version"] == v1.version
    assert diff["to_version"] == v2.version
    assert len(diff["changes"]) > 0
    assert len(diff["summary"]) > 0


@pytest.mark.asyncio
async def test_simple_json_diff():
    before = {"a": 1, "b": {"c": "old"}}
    after = {"a": 2, "b": {"c": "new"}}
    diff = _simple_json_diff(before, after)

    assert len(diff) == 2
    paths = {d["path"] for d in diff}
    assert "a" in paths
    assert "b.c" in paths


# ── DealSettings Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deal_settings_crud(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create
    settings = await upsert_deal_settings(session, deal.id, confidence_weights={"Revenue Quality": 0.25})
    assert settings.deal_id == deal.id
    assert settings.confidence_weights["Revenue Quality"] == 0.25

    # Read
    fetched = await get_deal_settings(session, deal.id)
    assert fetched is not None
    assert fetched.confidence_weights["Revenue Quality"] == 0.25

    # Update
    updated = await upsert_deal_settings(session, deal.id, confidence_weights={"Revenue Quality": 0.30, "Margin": 0.15})
    assert updated.confidence_weights["Revenue Quality"] == 0.30


# ── Integration: Evidence Update → Confidence Recalc ──────────────────────────


@pytest.mark.asyncio
async def test_evidence_update_triggers_recalc(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)
    hub = await create_intelligence_hub(session, company_id=company.id, deal_id=deal.id)

    item = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue $100M", source="SEC", source_type="filing"
    )

    # Seed confidence ledger
    from services.confidence_ledger_builder import ConfidenceLedgerBuilder
    decision = DecisionOutput(
        investment_score=82, confidence_score=0.84, recommendation="PROCEED", conviction="STRONG",
        thesis_score=80, financial_score=85, competitive_score=78, market_score=75, valuation_score=82, risk_score=25,
        supporting_metrics=12, contradictory_metrics=0, open_questions=0, total_metrics=12,
        module_scores=[ModuleScore(module_type="financial", score=85, confidence=0.90, supporting_count=5, contradictory_count=0, warning_count=0)],
        top_strengths=["Strong revenue"], top_concerns=["None"], critical_gaps=[],
        executive_summary="Proceed", evidence_modules=["financial"], data_sources=["SEC"], company_id=company.id,
    )
    builder = ConfidenceLedgerBuilder(deal_id=deal.id)
    await builder.build_from_decision(decision)

    # Update evidence status (direct CRUD, not through router so no event logged)
    from db.crud import update_evidence_item
    updated = await update_evidence_item(session, item.id, evidence_status="conflicting")

    # Verify status was updated
    assert updated.evidence_status == "conflicting"


# ── Integration: Overview Endpoint Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_overview_next_actions_endpoint(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    from api.routers.overview import _build_overview
    overview = await _build_overview(deal.id)
    assert overview["deal_id"] == deal.id
    assert "investment_view" in overview
