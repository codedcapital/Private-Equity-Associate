"""Phase 5 tests: Polling endpoint, status tracking, and real-time features."""

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
    truncate_all_tables,
)
from db.models import CompanySource, DealStage, DiligencePriority, DiligenceStatus

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


@pytest.mark.asyncio
async def test_overview_status_endpoint(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)
    hub = await create_intelligence_hub(session, company_id=company.id, deal_id=deal.id)

    # Seed data
    await create_investment_view(session, deal_id=deal.id, content={"text": "View"}, recommendation="PROCEED", confidence_score=80)
    await create_confidence_ledger(session, deal_id=deal.id, base_score=80, factors={}, final_score=80)
    await create_diligence_item(session, deal_id=deal.id, category="test", title="Item", status=DiligenceStatus.NOT_STARTED.value, priority=DiligencePriority.HIGH.value)
    await create_evidence_item(session, hub_id=hub.id, text="Evidence", source="SEC", source_type="filing")
    await create_deal_event(session, deal_id=deal.id, event_type="view_updated", description="Test event")

    # Test the status endpoint via _build_overview helper
    from api.routers.overview import _build_overview
    overview = await _build_overview(deal.id)
    assert overview["deal_id"] == deal.id
    assert overview["investment_view"] is not None
    assert overview["confidence"] is not None


@pytest.mark.asyncio
async def test_polling_returns_sections(test_session: AsyncSession):
    session = test_session
    company, deal = await _create_test_deal(session)

    # Create a view
    view = await create_investment_view(session, deal_id=deal.id, content={"text": "Test"}, recommendation="PROCEED", confidence_score=75)

    # Get status via direct DB query (simulating what the endpoint does)
    from db.crud import get_latest_investment_view, get_latest_confidence_ledger, list_diligence_items, list_deal_events

    latest_view = await get_latest_investment_view(session, deal.id)
    assert latest_view is not None
    assert latest_view.updated_at is not None

    latest_ledger = await get_latest_confidence_ledger(session, deal.id)
    # No ledger yet, should be None
    assert latest_ledger is None

    diligence = await list_diligence_items(session, deal_id=deal.id)
    assert len(diligence) == 0

    events = await list_deal_events(session, deal_id=deal.id, limit=1)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_rate_limit_middleware_exists():
    from api.rate_limit import RateLimitMiddleware, _SlidingWindow

    limiter = _SlidingWindow(max_requests=3, window_seconds=60)
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is False  # Exceeded limit


@pytest.mark.asyncio
async def test_auth_user_context():
    from api.auth import UserContext, UserRole

    user = UserContext(user_id="test", role=UserRole.ASSOCIATE)
    assert user.can_edit_views() is True
    assert user.can_finalize_views() is False
    assert user.can_override_weights() is False

    partner = UserContext(user_id="partner", role=UserRole.PARTNER)
    assert partner.can_finalize_views() is True
    assert partner.can_view_raw_data() is False
