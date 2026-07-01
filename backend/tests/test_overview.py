"""Comprehensive tests for the new Overview / Investment Decision Platform backend.

Tests all new models, CRUD, services, and the overview builder.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.routers.overview import _build_overview
from db.crud import (
    create_company,
    create_confidence_ledger,
    create_deal,
    create_deal_event,
    create_diligence_item,
    create_evidence_conflict,
    create_evidence_item,
    create_intelligence_hub,
    create_investment_view,
    delete_deal_event,
    delete_diligence_item,
    delete_evidence_conflict,
    delete_investment_view,
    get_confidence_ledger_by_id,
    get_diligence_item_by_id,
    get_evidence_conflict_by_id,
    get_investment_view_by_id,
    get_latest_confidence_ledger,
    get_latest_investment_view,
    list_confidence_ledgers,
    list_deal_events,
    list_diligence_items,
    list_evidence_conflicts,
    list_investment_views,
    truncate_all_tables,
    update_diligence_item,
    update_evidence_conflict,
    update_investment_view,
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
    ResolutionStatus,
)
from schemas.evidence import DecisionOutput, ModuleScore
from services.confidence_ledger_builder import ConfidenceLedgerBuilder
from services.decision_readiness import DecisionReadiness
from services.evidence_status_mapper import EvidenceStatusMapper
from services.investment_view_manager import InvestmentViewManager

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_session():
    """Create a fresh async session for each test, then clean up."""
    engine = create_async_engine(TEST_DATABASE_URL, future=True, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        # Clean up after test
        await truncate_all_tables(session)
    await engine.dispose()


# ── Helper: create minimal deal ───────────────────────────────────────────────


async def _create_test_deal(session: AsyncSession):
    """Create a company and deal for testing."""
    company = await create_company(
        session, name=f"TestCo-{uuid4().hex[:6]}", source=CompanySource.MANUAL, ticker="TEST"
    )
    deal = await create_deal(session, company_id=company.id, stage=DealStage.DILIGENCE)
    return company, deal


# ── Model / CRUD Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_investment_view_crud(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create
    view = await create_investment_view(
        session,
        deal_id=deal.id,
        content={"text": "Initial view", "blocks": []},
        recommendation="PROCEED",
        confidence_score=82.0,
        authored_by="system",
        status=InvestmentViewStatus.DRAFT.value,
    )
    assert view.id is not None
    assert view.version == 1
    assert view.deal_id == deal.id

    # Read
    fetched = await get_investment_view_by_id(session, view.id)
    assert fetched is not None
    assert fetched.recommendation == "PROCEED"

    # List
    views = await list_investment_views(session, deal.id)
    assert len(views) == 1

    # Update
    updated = await update_investment_view(session, view.id, recommendation="PASS")
    assert updated is not None
    assert updated.recommendation == "PASS"

    # Create version 2
    view2 = await create_investment_view(
        session,
        deal_id=deal.id,
        content={"text": "Updated view"},
        recommendation="CONDITIONAL",
        confidence_score=75.0,
        authored_by="system",
    )
    assert view2.version == 2

    latest = await get_latest_investment_view(session, deal.id)
    assert latest is not None
    assert latest.version == 2

    # Delete
    success = await delete_investment_view(session, view.id)
    assert success is True


@pytest.mark.asyncio
async def test_diligence_item_crud(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create
    item = await create_diligence_item(
        session,
        deal_id=deal.id,
        category="commercial",
        title="Customer reference calls",
        description="Call 3 customers",
        status=DiligenceStatus.NOT_STARTED.value,
        assigned_to="J. Reyes",
        due_date=date(2026, 3, 15),
        priority=DiligencePriority.HIGH.value,
    )
    assert item.id is not None
    assert item.title == "Customer reference calls"

    # Read
    fetched = await get_diligence_item_by_id(session, item.id)
    assert fetched is not None
    assert fetched.status == DiligenceStatus.NOT_STARTED.value

    # Update
    updated = await update_diligence_item(
        session, item.id, status=DiligenceStatus.IN_PROGRESS.value
    )
    assert updated is not None
    assert updated.status == DiligenceStatus.IN_PROGRESS.value

    # List
    items = await list_diligence_items(session, deal_id=deal.id)
    assert len(items) == 1

    # Delete
    success = await delete_diligence_item(session, item.id)
    assert success is True


@pytest.mark.asyncio
async def test_deal_event_crud(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create
    event = await create_deal_event(
        session,
        deal_id=deal.id,
        event_type=DealEventType.VIEW_UPDATED.value,
        actor_type=ActorType.SYSTEM.value,
        description="Initial view created",
        event_metadata={"version": 1},
    )
    assert event.id is not None

    # List
    events = await list_deal_events(session, deal_id=deal.id, limit=10)
    assert len(events) == 1
    assert events[0].description == "Initial view created"

    # Delete
    success = await delete_deal_event(session, event.id)
    assert success is True


@pytest.mark.asyncio
async def test_confidence_ledger_crud(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create
    ledger = await create_confidence_ledger(
        session,
        deal_id=deal.id,
        base_score=92,
        factors={
            "Revenue Quality": {"weight": 0.2, "contribution": 18, "status": "VERIFIED"},
            "Margin Stability": {"weight": 0.15, "contribution": 14, "status": "VERIFIED"},
        },
        final_score=82,
        bottlenecks=["Customer Concentration"],
    )
    assert ledger.id is not None
    assert ledger.base_score == 92
    assert ledger.final_score == 82

    # Read
    fetched = await get_confidence_ledger_by_id(session, ledger.id)
    assert fetched is not None

    latest = await get_latest_confidence_ledger(session, deal.id)
    assert latest is not None
    assert latest.final_score == 82

    # List
    ledgers = await list_confidence_ledgers(session, deal.id)
    assert len(ledgers) == 1


@pytest.mark.asyncio
async def test_evidence_conflict_crud(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)
    # Create intelligence hub first (required FK)
    hub = await create_intelligence_hub(session, company_id=company.id, deal_id=deal.id)

    item_a = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue is $100M", source="SEC", source_type="filing"
    )
    item_b = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue is $90M", source="Research", source_type="api"
    )

    conflict = await create_evidence_conflict(
        session,
        evidence_a_id=item_a.id,
        evidence_b_id=item_b.id,
        conflict_description="Revenue figures differ by $10M",
        resolution_status=ResolutionStatus.OPEN.value,
    )
    assert conflict.id is not None

    # Read
    fetched = await get_evidence_conflict_by_id(session, conflict.id)
    assert fetched is not None

    # Update
    updated = await update_evidence_conflict(
        session, conflict.id, resolution_status=ResolutionStatus.RESOLVED.value, resolved_by="admin"
    )
    assert updated is not None
    assert updated.resolution_status == ResolutionStatus.RESOLVED.value

    # List
    conflicts = await list_evidence_conflicts(session, resolution_status=ResolutionStatus.RESOLVED.value)
    assert len(conflicts) == 1

    # Delete
    success = await delete_evidence_conflict(session, conflict.id)
    assert success is True


# ── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evidence_status_mapper(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)
    hub = await create_intelligence_hub(session, company_id=company.id, deal_id=deal.id)

    item_sec = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue $100M", source="SEC EDGAR", source_type="filing"
    )
    item_web = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue $100M", source="Tavily Web Search", source_type="web"
    )
    item_model = await create_evidence_item(
        session, hub_id=hub.id, text="Revenue $100M", source="LBO Agent", source_type="api"
    )

    mapper = EvidenceStatusMapper()
    assert mapper.classify_evidence_item(item_sec) == EvidenceStatus.VERIFIED
    assert mapper.classify_evidence_item(item_web) == EvidenceStatus.NEEDS_VALIDATION
    assert mapper.classify_evidence_item(item_model) == EvidenceStatus.NEEDS_VALIDATION


@pytest.mark.asyncio
async def test_confidence_ledger_builder(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # Create a mock DecisionOutput
    decision = DecisionOutput(
        investment_score=82,
        confidence_score=0.84,
        recommendation="PROCEED",
        conviction="STRONG",
        thesis_score=80,
        financial_score=85,
        competitive_score=78,
        market_score=75,
        valuation_score=82,
        risk_score=25,
        supporting_metrics=12,
        contradictory_metrics=2,
        open_questions=0,
        total_metrics=14,
        module_scores=[
            ModuleScore(module_type="financial", score=85, confidence=0.90, supporting_count=5, contradictory_count=0, warning_count=0),
            ModuleScore(module_type="research", score=80, confidence=0.80, supporting_count=4, contradictory_count=1, warning_count=0),
        ],
        top_strengths=["Strong revenue growth"],
        top_concerns=["Customer concentration"],
        critical_gaps=[],
        executive_summary="We recommend PROCEED because of strong fundamentals.",
        evidence_modules=["financial", "research"],
        data_sources=["SEC", "Yahoo"],
        company_id=deal.company_id,
    )

    builder = ConfidenceLedgerBuilder(deal_id=deal.id)
    ledger = await builder.build_from_decision(decision)

    assert ledger is not None
    assert ledger.deal_id == deal.id
    assert ledger.base_score == 84  # 0.84 * 100
    assert 0 <= ledger.final_score <= 100
    assert ledger.bottlenecks is not None

    breakdown = ConfidenceLedgerBuilder.to_breakdown(ledger)
    assert breakdown["deal_id"] == deal.id
    assert "factors" in breakdown
    assert "reduced_because" in breakdown


@pytest.mark.asyncio
async def test_decision_readiness(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)
    deal.stage = DealStage.DILIGENCE

    readiness = DecisionReadiness(deal.id, "diligence")
    result = await readiness.compute()

    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "met" in result
    assert "unmet" in result
    assert "recommended_next_step" in result
    assert "diligence_summary" in result


@pytest.mark.asyncio
async def test_investment_view_manager(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    manager = InvestmentViewManager(deal_id=deal.id)

    # Seed from decision
    from schemas.evidence import DecisionOutput
    decision = DecisionOutput(
        investment_score=82,
        confidence_score=0.84,
        recommendation="PROCEED",
        conviction="STRONG",
        thesis_score=80,
        financial_score=85,
        competitive_score=78,
        market_score=75,
        valuation_score=82,
        risk_score=25,
        supporting_metrics=12,
        contradictory_metrics=2,
        open_questions=0,
        total_metrics=14,
        module_scores=[
            ModuleScore(module_type="financial", score=85, confidence=0.90, supporting_count=5, contradictory_count=0, warning_count=0),
        ],
        top_strengths=["Strong revenue growth"],
        top_concerns=["Customer concentration"],
        critical_gaps=[],
        executive_summary="We recommend PROCEED because of strong fundamentals.",
        evidence_modules=["financial"],
        data_sources=["SEC"],
        company_id=deal.company_id,
    )

    view = await manager.seed_from_decision(decision)
    assert view is not None
    assert view.version == 1
    assert view.recommendation == "PROCEED"

    # Edit
    v2 = await manager.edit(
        view.id,
        content={"text": "Updated view", "blocks": [{"type": "paragraph", "text": "Updated"}]},
        recommendation="CONDITIONAL",
        edited_by="J. Reyes",
    )
    assert v2 is not None
    assert v2.version == 2
    assert v2.recommendation == "CONDITIONAL"
    assert v2.edited_by == "J. Reyes"

    # History
    history = await manager.get_history()
    assert len(history) == 2


# ── Overview Builder Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_overview(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)

    # Create a hub and evidence
    hub = await create_intelligence_hub(session, company_id=company.id, deal_id=deal.id)
    await create_evidence_item(
        session, hub_id=hub.id, text="Revenue $100M", source="SEC", source_type="filing",
        is_supporting=True, confidence=0.95
    )
    await create_evidence_item(
        session, hub_id=hub.id, text="Margin 30%", source="Financial Agent", source_type="api",
        is_supporting=True, confidence=0.85
    )

    # Seed investment view
    await create_investment_view(
        session, deal_id=deal.id, content={"text": "Proceed"}, recommendation="PROCEED", confidence_score=82
    )

    # Create diligence items
    await create_diligence_item(
        session, deal_id=deal.id, category="commercial", title="Customer calls", status="not_started"
    )
    await create_diligence_item(
        session, deal_id=deal.id, category="management", title="Management interview", status="complete"
    )

    # Create event
    await create_deal_event(
        session, deal_id=deal.id, event_type=DealEventType.VIEW_UPDATED.value, description="View created"
    )

    # Build overview
    overview = await _build_overview(deal.id)

    assert overview["deal_id"] == deal.id
    assert overview["company"]["name"] == company.name
    assert overview["investment_view"] is not None
    assert overview["investment_view"]["recommendation"] == "PROCEED"
    assert len(overview["evidence"]) == 2
    assert overview["diligence"]["total"] == 2
    assert overview["diligence"]["complete"] == 1
    assert overview["diligence"]["open"] == 1
    assert "decision_readiness" in overview
    assert "score" in overview["decision_readiness"]
    assert len(overview["recent_events"]) == 1


@pytest.mark.asyncio
async def test_build_overview_empty_deal(test_session: AsyncSession):
    session = test_session
    _, deal = await _create_test_deal(session)

    # No data at all - should still return structure
    overview = await _build_overview(deal.id)
    assert overview["deal_id"] == deal.id
    assert overview["investment_view"] is None
    assert overview["confidence"] is None
    assert len(overview["evidence"]) == 0
    assert overview["diligence"]["total"] == 0
    assert len(overview["recent_events"]) == 0
