"""Async CRUD operations for all database models."""

from datetime import date, datetime
from typing import Any, Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AgentLog,
    AgentStatus,
    Company,
    CompanySource,
    CompetitorCompany,
    Deal,
    DealStage,
    EvidenceItem,
    Filing,
    FilingChunk,
    Financial,
    ICMemo,
    IntelligenceHub,
    IntelligenceQuestion,
    SourceConfidence,
)


# ── Company ────────────────────────────────────────────────────────────────

async def create_company(
    session: AsyncSession,
    name: str,
    source: CompanySource | str,
    ticker: str | None = None,
    sector: str | None = None,
    geography: str | None = None,
) -> Company:
    company = Company(
        name=name,
        source=source if isinstance(source, CompanySource) else CompanySource(source),
        ticker=ticker,
        sector=sector,
        geography=geography,
    )
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def get_company_by_id(session: AsyncSession, company_id: int) -> Company | None:
    result = await session.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one_or_none()


async def list_companies(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    sector: str | None = None,
    source: str | None = None,
) -> Sequence[Company]:
    stmt = select(Company).offset(skip).limit(limit)
    if sector:
        stmt = stmt.where(Company.sector == sector)
    if source:
        stmt = stmt.where(Company.source == source)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_company(
    session: AsyncSession, company_id: int, **kwargs: Any
) -> Company | None:
    company = await get_company_by_id(session, company_id)
    if not company:
        return None
    for key, value in kwargs.items():
        if hasattr(company, key):
            setattr(company, key, value)
    await session.commit()
    await session.refresh(company)
    return company


async def delete_company(session: AsyncSession, company_id: int) -> bool:
    company = await get_company_by_id(session, company_id)
    if not company:
        return False
    await session.delete(company)
    await session.commit()
    return True


# ── Financial ──────────────────────────────────────────────────────────────

async def create_financial(
    session: AsyncSession,
    company_id: int,
    report_date: date,
    revenue: float | None = None,
    ebitda: float | None = None,
    net_income: float | None = None,
    total_debt: float | None = None,
    cash: float | None = None,
    total_assets: float | None = None,
    total_equity: float | None = None,
    operating_cf: float | None = None,
    capex: float | None = None,
    net_debt: float | None = None,
    fcf: float | None = None,
    ebitda_margin: float | None = None,
    net_debt_ebitda: float | None = None,
    revenue_growth: float | None = None,
    fcf_yield: float | None = None,
) -> Financial:
    financial = Financial(
        company_id=company_id,
        report_date=report_date,
        revenue=revenue,
        ebitda=ebitda,
        net_income=net_income,
        total_debt=total_debt,
        cash=cash,
        total_assets=total_assets,
        total_equity=total_equity,
        operating_cf=operating_cf,
        capex=capex,
        net_debt=net_debt,
        fcf=fcf,
        ebitda_margin=ebitda_margin,
        net_debt_ebitda=net_debt_ebitda,
        revenue_growth=revenue_growth,
        fcf_yield=fcf_yield,
    )
    session.add(financial)
    await session.commit()
    await session.refresh(financial)
    return financial


async def get_financial_by_id(session: AsyncSession, financial_id: int) -> Financial | None:
    result = await session.execute(select(Financial).where(Financial.id == financial_id))
    return result.scalar_one_or_none()


async def list_financials(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    company_id: int | None = None,
) -> Sequence[Financial]:
    stmt = select(Financial).offset(skip).limit(limit)
    if company_id is not None:
        stmt = stmt.where(Financial.company_id == company_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_financial(
    session: AsyncSession, financial_id: int, **kwargs: Any
) -> Financial | None:
    financial = await get_financial_by_id(session, financial_id)
    if not financial:
        return None
    for key, value in kwargs.items():
        if hasattr(financial, key):
            setattr(financial, key, value)
    await session.commit()
    await session.refresh(financial)
    return financial


async def delete_financial(session: AsyncSession, financial_id: int) -> bool:
    financial = await get_financial_by_id(session, financial_id)
    if not financial:
        return False
    await session.delete(financial)
    await session.commit()
    return True


# ── Filing ─────────────────────────────────────────────────────────────────

async def create_filing(
    session: AsyncSession,
    company_id: int,
    filing_type: str,
    filing_date: date,
    accession_number: str | None = None,
    raw_text: str | None = None,
    embedding: list[float] | None = None,
) -> Filing:
    filing = Filing(
        company_id=company_id,
        filing_type=filing_type,
        filing_date=filing_date,
        accession_number=accession_number,
        raw_text=raw_text,
        embedding=embedding,
    )
    session.add(filing)
    await session.commit()
    await session.refresh(filing)
    return filing


async def get_filing_by_id(session: AsyncSession, filing_id: int) -> Filing | None:
    result = await session.execute(select(Filing).where(Filing.id == filing_id))
    return result.scalar_one_or_none()


async def list_filings(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    company_id: int | None = None,
    filing_type: str | None = None,
) -> Sequence[Filing]:
    stmt = select(Filing).offset(skip).limit(limit)
    if company_id is not None:
        stmt = stmt.where(Filing.company_id == company_id)
    if filing_type:
        stmt = stmt.where(Filing.filing_type == filing_type)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_filing(
    session: AsyncSession, filing_id: int, **kwargs: Any
) -> Filing | None:
    filing = await get_filing_by_id(session, filing_id)
    if not filing:
        return None
    for key, value in kwargs.items():
        if hasattr(filing, key):
            setattr(filing, key, value)
    await session.commit()
    await session.refresh(filing)
    return filing


async def delete_filing(session: AsyncSession, filing_id: int) -> bool:
    filing = await get_filing_by_id(session, filing_id)
    if not filing:
        return False
    await session.delete(filing)
    await session.commit()
    return True


# ── FilingChunk ────────────────────────────────────────────────────────────

async def create_filing_chunk(
    session: AsyncSession,
    filing_id: int,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float] | None = None,
) -> FilingChunk:
    chunk = FilingChunk(
        filing_id=filing_id,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        embedding=embedding,
    )
    session.add(chunk)
    await session.commit()
    await session.refresh(chunk)
    return chunk


async def get_filing_chunk_by_id(session: AsyncSession, chunk_id: int) -> FilingChunk | None:
    result = await session.execute(select(FilingChunk).where(FilingChunk.id == chunk_id))
    return result.scalar_one_or_none()


async def list_filing_chunks(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filing_id: int | None = None,
) -> Sequence[FilingChunk]:
    stmt = select(FilingChunk).offset(skip).limit(limit)
    if filing_id is not None:
        stmt = stmt.where(FilingChunk.filing_id == filing_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_filing_chunk(
    session: AsyncSession, chunk_id: int, **kwargs: Any
) -> FilingChunk | None:
    chunk = await get_filing_chunk_by_id(session, chunk_id)
    if not chunk:
        return None
    for key, value in kwargs.items():
        if hasattr(chunk, key):
            setattr(chunk, key, value)
    await session.commit()
    await session.refresh(chunk)
    return chunk


async def delete_filing_chunk(session: AsyncSession, chunk_id: int) -> bool:
    chunk = await get_filing_chunk_by_id(session, chunk_id)
    if not chunk:
        return False
    await session.delete(chunk)
    await session.commit()
    return True


# ── Deal ───────────────────────────────────────────────────────────────────

async def create_deal(
    session: AsyncSession,
    company_id: int,
    stage: DealStage | str = DealStage.SOURCING,
    entry_ev: float | None = None,
    entry_ebitda: float | None = None,
    lbo_irr: float | None = None,
    lbo_moic: float | None = None,
    memo_id: int | None = None,
) -> Deal:
    deal = Deal(
        company_id=company_id,
        stage=stage if isinstance(stage, DealStage) else DealStage(stage),
        entry_ev=entry_ev,
        entry_ebitda=entry_ebitda,
        lbo_irr=lbo_irr,
        lbo_moic=lbo_moic,
        memo_id=memo_id,
    )
    session.add(deal)
    await session.commit()
    await session.refresh(deal)
    return deal


async def get_deal_by_company_id(session: AsyncSession, company_id: int) -> Deal | None:
    result = await session.execute(
        select(Deal).where(Deal.company_id == company_id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_deal_by_id(session: AsyncSession, deal_id: int) -> Deal | None:
    result = await session.execute(select(Deal).where(Deal.id == deal_id))
    return result.scalar_one_or_none()


async def list_deals(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    company_id: int | None = None,
    stage: DealStage | str | None = None,
) -> Sequence[Deal]:
    stmt = select(Deal).offset(skip).limit(limit)
    if company_id is not None:
        stmt = stmt.where(Deal.company_id == company_id)
    if stage is not None:
        stmt = stmt.where(Deal.stage == (stage if isinstance(stage, DealStage) else DealStage(stage)))
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_deal(session: AsyncSession, deal_id: int, **kwargs: Any) -> Deal | None:
    deal = await get_deal_by_id(session, deal_id)
    if not deal:
        return None
    for key, value in kwargs.items():
        if hasattr(deal, key):
            setattr(deal, key, value)
    await session.commit()
    await session.refresh(deal)
    return deal


async def delete_deal(session: AsyncSession, deal_id: int) -> bool:
    deal = await get_deal_by_id(session, deal_id)
    if not deal:
        return False
    await session.delete(deal)
    await session.commit()
    return True


# ── ICMemo ─────────────────────────────────────────────────────────────────

async def create_ic_memo(
    session: AsyncSession,
    company_id: int,
    sections: dict,
    deal_id: int | None = None,
    word_count: int | None = None,
    confidence_score: float | None = None,
    pdf_path: str | None = None,
) -> ICMemo:
    memo = ICMemo(
        company_id=company_id,
        sections=sections,
        deal_id=deal_id,
        word_count=word_count,
        confidence_score=confidence_score,
        pdf_path=pdf_path,
    )
    session.add(memo)
    await session.commit()
    await session.refresh(memo)
    return memo


async def get_ic_memo_by_id(session: AsyncSession, memo_id: int) -> ICMemo | None:
    result = await session.execute(select(ICMemo).where(ICMemo.id == memo_id))
    return result.scalar_one_or_none()


async def list_ic_memos(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    company_id: int | None = None,
) -> Sequence[ICMemo]:
    stmt = select(ICMemo).offset(skip).limit(limit)
    if company_id is not None:
        stmt = stmt.where(ICMemo.company_id == company_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_ic_memo(
    session: AsyncSession, memo_id: int, **kwargs: Any
) -> ICMemo | None:
    memo = await get_ic_memo_by_id(session, memo_id)
    if not memo:
        return None
    for key, value in kwargs.items():
        if hasattr(memo, key):
            setattr(memo, key, value)
    await session.commit()
    await session.refresh(memo)
    return memo


async def delete_ic_memo(session: AsyncSession, memo_id: int) -> bool:
    memo = await get_ic_memo_by_id(session, memo_id)
    if not memo:
        return False
    await session.delete(memo)
    await session.commit()
    return True


# ── AgentLog ───────────────────────────────────────────────────────────────

async def create_agent_log(
    session: AsyncSession,
    run_id: str,
    agent_name: str,
    status: AgentStatus | str = AgentStatus.PENDING,
    input_data: dict | None = None,
    output_data: dict | None = None,
    duration_ms: int | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
    errors: list[str] | None = None,
) -> AgentLog:
    log = AgentLog(
        run_id=run_id,
        agent_name=agent_name,
        status=status if isinstance(status, AgentStatus) else AgentStatus(status),
        input_data=input_data,
        output_data=output_data,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        errors=errors,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_agent_log_by_id(session: AsyncSession, log_id: int) -> AgentLog | None:
    result = await session.execute(select(AgentLog).where(AgentLog.id == log_id))
    return result.scalar_one_or_none()


async def list_agent_logs(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    agent_name: str | None = None,
    status: AgentStatus | str | None = None,
) -> Sequence[AgentLog]:
    stmt = select(AgentLog).offset(skip).limit(limit)
    if agent_name:
        stmt = stmt.where(AgentLog.agent_name == agent_name)
    if status is not None:
        stmt = stmt.where(
            AgentLog.status == (status if isinstance(status, AgentStatus) else AgentStatus(status))
        )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_agent_log(
    session: AsyncSession, log_id: int, **kwargs: Any
) -> AgentLog | None:
    log = await get_agent_log_by_id(session, log_id)
    if not log:
        return None
    for key, value in kwargs.items():
        if hasattr(log, key):
            setattr(log, key, value)
    await session.commit()
    await session.refresh(log)
    return log


async def delete_agent_log(session: AsyncSession, log_id: int) -> bool:
    log = await get_agent_log_by_id(session, log_id)
    if not log:
        return False
    await session.delete(log)
    await session.commit()
    return True


# ── CompetitorCompany ────────────────────────────────────────────────────────

async def create_competitor_company(
    session: AsyncSession,
    target_company_id: int,
    name: str,
    source_db: str,
    domain: str | None = None,
    sector: str | None = None,
    funding_stage: str | None = None,
    hq_location: str | None = None,
) -> CompetitorCompany:
    competitor = CompetitorCompany(
        target_company_id=target_company_id,
        name=name,
        source_db=source_db,
        domain=domain,
        sector=sector,
        funding_stage=funding_stage,
        hq_location=hq_location,
    )
    session.add(competitor)
    await session.commit()
    await session.refresh(competitor)
    return competitor


async def get_competitor_company_by_id(
    session: AsyncSession, competitor_id: int
) -> CompetitorCompany | None:
    result = await session.execute(
        select(CompetitorCompany).where(CompetitorCompany.id == competitor_id)
    )
    return result.scalar_one_or_none()


async def list_competitor_companies(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    target_company_id: int | None = None,
    source_db: str | None = None,
) -> Sequence[CompetitorCompany]:
    stmt = select(CompetitorCompany).offset(skip).limit(limit)
    if target_company_id is not None:
        stmt = stmt.where(CompetitorCompany.target_company_id == target_company_id)
    if source_db:
        stmt = stmt.where(CompetitorCompany.source_db == source_db)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_competitor_company(
    session: AsyncSession, competitor_id: int, **kwargs: Any
) -> CompetitorCompany | None:
    competitor = await get_competitor_company_by_id(session, competitor_id)
    if not competitor:
        return None
    for key, value in kwargs.items():
        if hasattr(competitor, key):
            setattr(competitor, key, value)
    await session.commit()
    await session.refresh(competitor)
    return competitor


async def delete_competitor_company(session: AsyncSession, competitor_id: int) -> bool:
    competitor = await get_competitor_company_by_id(session, competitor_id)
    if not competitor:
        return False
    await session.delete(competitor)
    await session.commit()
    return True


# ── Intelligence Hub ────────────────────────────────────────────────────────


async def create_intelligence_hub(
    session: AsyncSession,
    company_id: int,
    deal_id: int | None = None,
    status: str = "draft",
    executive_briefing: str | None = None,
) -> IntelligenceHub:
    hub = IntelligenceHub(
        company_id=company_id,
        deal_id=deal_id,
        status=status,
        executive_briefing=executive_briefing,
    )
    session.add(hub)
    await session.commit()
    await session.refresh(hub)
    return hub


async def get_hub_by_id(session: AsyncSession, hub_id: int) -> IntelligenceHub | None:
    result = await session.execute(
        select(IntelligenceHub).where(IntelligenceHub.id == hub_id)
    )
    return result.scalar_one_or_none()


async def get_hub_by_company(session: AsyncSession, company_id: int) -> IntelligenceHub | None:
    result = await session.execute(
        select(IntelligenceHub)
        .where(IntelligenceHub.company_id == company_id)
        .order_by(IntelligenceHub.generated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_intelligence_hubs(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    company_id: int | None = None,
) -> Sequence[IntelligenceHub]:
    stmt = select(IntelligenceHub).offset(skip).limit(limit)
    if company_id is not None:
        stmt = stmt.where(IntelligenceHub.company_id == company_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_intelligence_hub(
    session: AsyncSession, hub_id: int, **kwargs: Any
) -> IntelligenceHub | None:
    hub = await get_hub_by_id(session, hub_id)
    if not hub:
        return None
    for key, value in kwargs.items():
        if hasattr(hub, key):
            setattr(hub, key, value)
    await session.commit()
    await session.refresh(hub)
    return hub


async def delete_intelligence_hub(session: AsyncSession, hub_id: int) -> bool:
    hub = await get_hub_by_id(session, hub_id)
    if not hub:
        return False
    await session.delete(hub)
    await session.commit()
    return True


# ── Intelligence Question ────────────────────────────────────────────────────


async def create_intelligence_question(
    session: AsyncSession,
    hub_id: int,
    category: str,
    question: str,
    answer: str | None = None,
    confidence: float | None = None,
    sort_order: int = 0,
) -> IntelligenceQuestion:
    q = IntelligenceQuestion(
        hub_id=hub_id,
        category=category,
        question=question,
        answer=answer,
        confidence=confidence,
        sort_order=sort_order,
    )
    session.add(q)
    await session.commit()
    await session.refresh(q)
    return q


async def get_intelligence_question_by_id(
    session: AsyncSession, question_id: int
) -> IntelligenceQuestion | None:
    result = await session.execute(
        select(IntelligenceQuestion).where(IntelligenceQuestion.id == question_id)
    )
    return result.scalar_one_or_none()


async def list_intelligence_questions(
    session: AsyncSession,
    hub_id: int | None = None,
    category: str | None = None,
) -> Sequence[IntelligenceQuestion]:
    stmt = select(IntelligenceQuestion)
    if hub_id is not None:
        stmt = stmt.where(IntelligenceQuestion.hub_id == hub_id)
    if category is not None:
        stmt = stmt.where(IntelligenceQuestion.category == category)
    stmt = stmt.order_by(IntelligenceQuestion.sort_order, IntelligenceQuestion.created_at)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_intelligence_question(
    session: AsyncSession, question_id: int, **kwargs: Any
) -> IntelligenceQuestion | None:
    q = await get_intelligence_question_by_id(session, question_id)
    if not q:
        return None
    for key, value in kwargs.items():
        if hasattr(q, key):
            setattr(q, key, value)
    await session.commit()
    await session.refresh(q)
    return q


async def delete_intelligence_question(session: AsyncSession, question_id: int) -> bool:
    q = await get_intelligence_question_by_id(session, question_id)
    if not q:
        return False
    await session.delete(q)
    await session.commit()
    return True


# ── Evidence Item ───────────────────────────────────────────────────────────


async def create_evidence_item(
    session: AsyncSession,
    hub_id: int,
    text: str,
    source: str,
    source_type: str,
    question_id: int | None = None,
    source_url: str | None = None,
    source_metadata: dict | None = None,
    is_supporting: bool = False,
    is_contradictory: bool = False,
    confidence: float | None = None,
) -> EvidenceItem:
    item = EvidenceItem(
        hub_id=hub_id,
        question_id=question_id,
        text=text,
        source=source,
        source_type=source_type,
        source_url=source_url,
        source_metadata=source_metadata,
        is_supporting=is_supporting,
        is_contradictory=is_contradictory,
        confidence=confidence,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_evidence_item_by_id(session: AsyncSession, evidence_id: int) -> EvidenceItem | None:
    result = await session.execute(
        select(EvidenceItem).where(EvidenceItem.id == evidence_id)
    )
    return result.scalar_one_or_none()


async def list_evidence_items(
    session: AsyncSession,
    hub_id: int | None = None,
    question_id: int | None = None,
    is_supporting: bool | None = None,
    is_contradictory: bool | None = None,
) -> Sequence[EvidenceItem]:
    stmt = select(EvidenceItem)
    if hub_id is not None:
        stmt = stmt.where(EvidenceItem.hub_id == hub_id)
    if question_id is not None:
        stmt = stmt.where(EvidenceItem.question_id == question_id)
    if is_supporting is not None:
        stmt = stmt.where(EvidenceItem.is_supporting == is_supporting)
    if is_contradictory is not None:
        stmt = stmt.where(EvidenceItem.is_contradictory == is_contradictory)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_evidence_item(
    session: AsyncSession, evidence_id: int, **kwargs: Any
) -> EvidenceItem | None:
    item = await get_evidence_item_by_id(session, evidence_id)
    if not item:
        return None
    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_evidence_item(session: AsyncSession, evidence_id: int) -> bool:
    item = await get_evidence_item_by_id(session, evidence_id)
    if not item:
        return False
    await session.delete(item)
    await session.commit()
    return True


# ── Source Confidence ──────────────────────────────────────────────────────


async def create_source_confidence(
    session: AsyncSession,
    hub_id: int,
    source_name: str,
    source_type: str,
    confidence_score: float,
    rationale: str,
) -> SourceConfidence:
    sc = SourceConfidence(
        hub_id=hub_id,
        source_name=source_name,
        source_type=source_type,
        confidence_score=confidence_score,
        rationale=rationale,
    )
    session.add(sc)
    await session.commit()
    await session.refresh(sc)
    return sc


async def get_source_confidence_by_id(
    session: AsyncSession, sc_id: int
) -> SourceConfidence | None:
    result = await session.execute(
        select(SourceConfidence).where(SourceConfidence.id == sc_id)
    )
    return result.scalar_one_or_none()


async def get_source_confidence_by_source(
    session: AsyncSession, hub_id: int, source_name: str
) -> SourceConfidence | None:
    result = await session.execute(
        select(SourceConfidence)
        .where(SourceConfidence.hub_id == hub_id)
        .where(SourceConfidence.source_name == source_name)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_source_confidence(
    session: AsyncSession,
    hub_id: int | None = None,
) -> Sequence[SourceConfidence]:
    stmt = select(SourceConfidence)
    if hub_id is not None:
        stmt = stmt.where(SourceConfidence.hub_id == hub_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_source_confidence(
    session: AsyncSession, sc_id: int, **kwargs: Any
) -> SourceConfidence | None:
    sc = await get_source_confidence_by_id(session, sc_id)
    if not sc:
        return None
    for key, value in kwargs.items():
        if hasattr(sc, key):
            setattr(sc, key, value)
    await session.commit()
    await session.refresh(sc)
    return sc


async def upsert_source_confidence(
    session: AsyncSession,
    hub_id: int,
    source_name: str,
    source_type: str,
    confidence_score: float,
    rationale: str,
) -> SourceConfidence:
    """Create or update source confidence for a given source in a hub."""
    existing = await get_source_confidence_by_source(session, hub_id, source_name)
    if existing:
        existing.confidence_score = confidence_score
        existing.rationale = rationale
        await session.commit()
        await session.refresh(existing)
        return existing
    return await create_source_confidence(
        session, hub_id, source_name, source_type, confidence_score, rationale
    )


async def delete_source_confidence(session: AsyncSession, sc_id: int) -> bool:
    sc = await get_source_confidence_by_id(session, sc_id)
    if not sc:
        return False
    await session.delete(sc)
    await session.commit()
    return True


# ── General utilities ──────────────────────────────────────────────────────

async def truncate_all_tables(session: AsyncSession) -> None:
    """Truncate all tables (useful for test cleanup)."""
    await session.execute(
        text(
            "TRUNCATE TABLE evidence_items, intelligence_questions, source_confidence, "
            "intelligence_hubs, filing_chunks, filings, financials, "
            "competitor_companies, deal_pipeline, ic_memos, agent_logs, companies "
            "RESTART IDENTITY CASCADE"
        )
    )
    await session.commit()
