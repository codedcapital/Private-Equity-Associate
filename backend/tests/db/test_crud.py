"""Tests for async CRUD operations."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.crud import (
    create_agent_log,
    create_company,
    create_competitor_company,
    create_deal,
    create_filing,
    create_filing_chunk,
    create_financial,
    create_ic_memo,
    delete_agent_log,
    delete_company,
    delete_competitor_company,
    delete_deal,
    delete_filing,
    delete_filing_chunk,
    delete_financial,
    delete_ic_memo,
    get_agent_log_by_id,
    get_company_by_id,
    get_competitor_company_by_id,
    get_deal_by_id,
    get_filing_by_id,
    get_filing_chunk_by_id,
    get_financial_by_id,
    get_ic_memo_by_id,
    list_agent_logs,
    list_companies,
    list_competitor_companies,
    list_deals,
    list_filing_chunks,
    list_filings,
    list_financials,
    list_ic_memos,
    truncate_all_tables,
    update_company,
    update_deal,
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


# ── Company tests ──────────────────────────────────────────────────────────

async def test_create_and_get_company(session: AsyncSession) -> None:
    company = await create_company(
        session, name="Acme Corp", source=CompanySource.SEC, ticker="ACME", sector="Tech"
    )
    assert company.id is not None
    fetched = await get_company_by_id(session, company.id)
    assert fetched is not None
    assert fetched.name == "Acme Corp"
    assert fetched.ticker == "ACME"
    assert fetched.source == CompanySource.SEC


async def test_list_companies_with_filters(session: AsyncSession) -> None:
    await create_company(session, name="A", source=CompanySource.SEC, sector="Tech")
    await create_company(session, name="B", source=CompanySource.MANUAL, sector="Health")
    all_companies = await list_companies(session)
    assert len(all_companies) == 2
    tech_companies = await list_companies(session, sector="Tech")
    assert len(tech_companies) == 1
    assert tech_companies[0].name == "A"


async def test_update_company(session: AsyncSession) -> None:
    company = await create_company(session, name="Old", source=CompanySource.SEC)
    updated = await update_company(session, company.id, name="New")
    assert updated is not None
    assert updated.name == "New"


async def test_delete_company(session: AsyncSession) -> None:
    company = await create_company(session, name="DeleteMe", source=CompanySource.SEC)
    deleted = await delete_company(session, company.id)
    assert deleted is True
    assert await get_company_by_id(session, company.id) is None


# ── Financial tests ──────────────────────────────────────────────────────────

async def test_create_and_get_financial(session: AsyncSession) -> None:
    company = await create_company(session, name="FinCo", source=CompanySource.SEC)
    financial = await create_financial(
        session,
        company_id=company.id,
        report_date=date(2023, 12, 31),
        revenue=100.0,
        ebitda=20.0,
    )
    assert financial.id is not None
    fetched = await get_financial_by_id(session, financial.id)
    assert fetched is not None
    assert fetched.revenue == 100.0
    assert fetched.company_id == company.id


async def test_list_financials_by_company(session: AsyncSession) -> None:
    company = await create_company(session, name="FinCo", source=CompanySource.SEC)
    await create_financial(session, company_id=company.id, report_date=date(2023, 12, 31))
    await create_financial(session, company_id=company.id, report_date=date(2022, 12, 31))
    results = await list_financials(session, company_id=company.id)
    assert len(results) == 2


async def test_delete_financial(session: AsyncSession) -> None:
    company = await create_company(session, name="FinCo", source=CompanySource.SEC)
    financial = await create_financial(
        session, company_id=company.id, report_date=date(2023, 12, 31)
    )
    deleted = await delete_financial(session, financial.id)
    assert deleted is True
    assert await get_financial_by_id(session, financial.id) is None


# ── Filing tests ───────────────────────────────────────────────────────────

async def test_create_and_get_filing(session: AsyncSession) -> None:
    company = await create_company(session, name="FileCo", source=CompanySource.SEC)
    filing = await create_filing(
        session,
        company_id=company.id,
        filing_type="10-K",
        filing_date=date(2023, 12, 31),
        accession_number="0001234567-23-000001",
    )
    assert filing.id is not None
    fetched = await get_filing_by_id(session, filing.id)
    assert fetched is not None
    assert fetched.filing_type == "10-K"


async def test_list_filings_with_filters(session: AsyncSession) -> None:
    company = await create_company(session, name="FileCo", source=CompanySource.SEC)
    await create_filing(
        session, company_id=company.id, filing_type="10-K", filing_date=date(2023, 1, 1)
    )
    await create_filing(
        session, company_id=company.id, filing_type="10-Q", filing_date=date(2023, 4, 1)
    )
    all_filings = await list_filings(session)
    assert len(all_filings) == 2
    k_filings = await list_filings(session, filing_type="10-K")
    assert len(k_filings) == 1


async def test_delete_filing(session: AsyncSession) -> None:
    company = await create_company(session, name="FileCo", source=CompanySource.SEC)
    filing = await create_filing(
        session, company_id=company.id, filing_type="10-K", filing_date=date(2023, 1, 1)
    )
    deleted = await delete_filing(session, filing.id)
    assert deleted is True
    assert await get_filing_by_id(session, filing.id) is None


# ── FilingChunk tests ──────────────────────────────────────────────────────

async def test_create_and_get_filing_chunk(session: AsyncSession) -> None:
    company = await create_company(session, name="ChunkCo", source=CompanySource.SEC)
    filing = await create_filing(
        session, company_id=company.id, filing_type="10-K", filing_date=date(2023, 1, 1)
    )
    chunk = await create_filing_chunk(
        session, filing_id=filing.id, chunk_index=0, chunk_text="Hello world"
    )
    assert chunk.id is not None
    fetched = await get_filing_chunk_by_id(session, chunk.id)
    assert fetched is not None
    assert fetched.chunk_text == "Hello world"


async def test_list_filing_chunks_by_filing(session: AsyncSession) -> None:
    company = await create_company(session, name="ChunkCo", source=CompanySource.SEC)
    filing = await create_filing(
        session, company_id=company.id, filing_type="10-K", filing_date=date(2023, 1, 1)
    )
    await create_filing_chunk(session, filing_id=filing.id, chunk_index=0, chunk_text="A")
    await create_filing_chunk(session, filing_id=filing.id, chunk_index=1, chunk_text="B")
    chunks = await list_filing_chunks(session, filing_id=filing.id)
    assert len(chunks) == 2


async def test_delete_filing_chunk(session: AsyncSession) -> None:
    company = await create_company(session, name="ChunkCo", source=CompanySource.SEC)
    filing = await create_filing(
        session, company_id=company.id, filing_type="10-K", filing_date=date(2023, 1, 1)
    )
    chunk = await create_filing_chunk(
        session, filing_id=filing.id, chunk_index=0, chunk_text="Delete me"
    )
    deleted = await delete_filing_chunk(session, chunk.id)
    assert deleted is True
    assert await get_filing_chunk_by_id(session, chunk.id) is None


# ── Deal tests ─────────────────────────────────────────────────────────────

async def test_create_and_get_deal(session: AsyncSession) -> None:
    company = await create_company(session, name="DealCo", source=CompanySource.SEC)
    deal = await create_deal(
        session, company_id=company.id, stage=DealStage.DILIGENCE, entry_ev=500.0
    )
    assert deal.id is not None
    fetched = await get_deal_by_id(session, deal.id)
    assert fetched is not None
    assert fetched.stage == DealStage.DILIGENCE
    assert fetched.entry_ev == 500.0


async def test_list_deals_with_filters(session: AsyncSession) -> None:
    company = await create_company(session, name="DealCo", source=CompanySource.SEC)
    await create_deal(session, company_id=company.id, stage=DealStage.SOURCING)
    await create_deal(session, company_id=company.id, stage=DealStage.DILIGENCE)
    all_deals = await list_deals(session)
    assert len(all_deals) == 2
    sourcing = await list_deals(session, stage=DealStage.SOURCING)
    assert len(sourcing) == 1


async def test_update_deal(session: AsyncSession) -> None:
    company = await create_company(session, name="DealCo", source=CompanySource.SEC)
    deal = await create_deal(session, company_id=company.id, stage=DealStage.SOURCING)
    updated = await update_deal(session, deal.id, stage=DealStage.IC_READY)
    assert updated is not None
    assert updated.stage == DealStage.IC_READY


async def test_delete_deal(session: AsyncSession) -> None:
    company = await create_company(session, name="DealCo", source=CompanySource.SEC)
    deal = await create_deal(session, company_id=company.id)
    deleted = await delete_deal(session, deal.id)
    assert deleted is True
    assert await get_deal_by_id(session, deal.id) is None


# ── ICMemo tests ───────────────────────────────────────────────────────────

async def test_create_and_get_ic_memo(session: AsyncSession) -> None:
    company = await create_company(session, name="MemoCo", source=CompanySource.SEC)
    memo = await create_ic_memo(
        session,
        company_id=company.id,
        sections={"summary": "Good investment"},
        word_count=1200,
        confidence_score=0.85,
    )
    assert memo.id is not None
    fetched = await get_ic_memo_by_id(session, memo.id)
    assert fetched is not None
    assert fetched.sections == {"summary": "Good investment"}
    assert fetched.word_count == 1200


async def test_list_ic_memos_by_company(session: AsyncSession) -> None:
    company = await create_company(session, name="MemoCo", source=CompanySource.SEC)
    await create_ic_memo(session, company_id=company.id, sections={"a": 1})
    await create_ic_memo(session, company_id=company.id, sections={"b": 2})
    memos = await list_ic_memos(session, company_id=company.id)
    assert len(memos) == 2


async def test_delete_ic_memo(session: AsyncSession) -> None:
    company = await create_company(session, name="MemoCo", source=CompanySource.SEC)
    memo = await create_ic_memo(session, company_id=company.id, sections={"a": 1})
    deleted = await delete_ic_memo(session, memo.id)
    assert deleted is True
    assert await get_ic_memo_by_id(session, memo.id) is None


# ── AgentLog tests ─────────────────────────────────────────────────────────

async def test_create_and_get_agent_log(session: AsyncSession) -> None:
    log = await create_agent_log(
        session,
        run_id=str(uuid4()),
        agent_name="sourcing_agent",
        status=AgentStatus.COMPLETE,
        tokens_used=1500,
        cost_usd=0.05,
    )
    assert log.id is not None
    fetched = await get_agent_log_by_id(session, log.id)
    assert fetched is not None
    assert fetched.agent_name == "sourcing_agent"
    assert fetched.status == AgentStatus.COMPLETE


async def test_list_agent_logs_with_filters(session: AsyncSession) -> None:
    await create_agent_log(session, run_id=str(uuid4()), agent_name="agent_a")
    await create_agent_log(session, run_id=str(uuid4()), agent_name="agent_a")
    await create_agent_log(session, run_id=str(uuid4()), agent_name="agent_b")
    all_logs = await list_agent_logs(session)
    assert len(all_logs) == 3
    a_logs = await list_agent_logs(session, agent_name="agent_a")
    assert len(a_logs) == 2


async def test_delete_agent_log(session: AsyncSession) -> None:
    log = await create_agent_log(session, run_id=str(uuid4()), agent_name="temp_agent")
    deleted = await delete_agent_log(session, log.id)
    assert deleted is True
    assert await get_agent_log_by_id(session, log.id) is None


# ── CompetitorCompany tests ────────────────────────────────────────────────

async def test_create_and_get_competitor_company(session: AsyncSession) -> None:
    company = await create_company(session, name="Target", source=CompanySource.SEC)
    competitor = await create_competitor_company(
        session,
        target_company_id=company.id,
        name="Competitor A",
        source_db="crunchbase",
        domain="competitor-a.com",
        sector="SaaS",
    )
    assert competitor.id is not None
    fetched = await get_competitor_company_by_id(session, competitor.id)
    assert fetched is not None
    assert fetched.name == "Competitor A"
    assert fetched.source_db == "crunchbase"


async def test_list_competitor_companies_with_filters(session: AsyncSession) -> None:
    company = await create_company(session, name="Target", source=CompanySource.SEC)
    await create_competitor_company(
        session, target_company_id=company.id, name="C1", source_db="crunchbase"
    )
    await create_competitor_company(
        session, target_company_id=company.id, name="C2", source_db="pitchbook"
    )
    all_competitors = await list_competitor_companies(session)
    assert len(all_competitors) == 2
    cb = await list_competitor_companies(session, source_db="crunchbase")
    assert len(cb) == 1


async def test_delete_competitor_company(session: AsyncSession) -> None:
    company = await create_company(session, name="Target", source=CompanySource.SEC)
    competitor = await create_competitor_company(
        session, target_company_id=company.id, name="RemoveMe", source_db="crunchbase"
    )
    deleted = await delete_competitor_company(session, competitor.id)
    assert deleted is True
    assert await get_competitor_company_by_id(session, competitor.id) is None
