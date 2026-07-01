"""Intelligence Hub router — question-centric diligence and evidence management.

Endpoints:
    GET    /intelligence/{company_id}              — Get full hub for a company
    POST   /intelligence/{company_id}/generate     — Populate hub from agent outputs
    POST   /intelligence/{company_id}/questions    — Add a question
    PATCH  /intelligence/questions/{question_id}   — Update a question
    DELETE /intelligence/questions/{question_id} — Delete a question
    POST   /intelligence/{company_id}/evidence     — Add evidence
    PATCH  /intelligence/evidence/{evidence_id}    — Update evidence
    DELETE /intelligence/evidence/{evidence_id}   — Remove evidence
    POST   /intelligence/{company_id}/source-confidence — Set source confidence
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.crud import (
    create_evidence_item,
    create_intelligence_hub,
    create_intelligence_question,
    create_source_confidence,
    delete_evidence_item,
    delete_intelligence_question,
    get_evidence_item_by_id,
    get_hub_by_company,
    get_hub_by_id,
    get_intelligence_question_by_id,
    get_source_confidence_by_id,
    list_evidence_items,
    list_intelligence_questions,
    list_source_confidence,
    update_evidence_item,
    update_intelligence_hub,
    update_intelligence_question,
    update_source_confidence,
    upsert_source_confidence,
)
from db.session import async_session_factory
from schemas.intelligence import (
    EvidenceItemCreate,
    EvidenceItemSchema,
    EvidenceItemUpdate,
    IntelligenceHubResponse,
    IntelligenceQuestionCreate,
    IntelligenceQuestionSchema,
    IntelligenceQuestionUpdate,
    SourceConfidenceCreate,
    SourceConfidenceSchema,
    SourceConfidenceUpdate,
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Helper: build full hub response with nested relationships ──────────────────


async def _build_hub_response(hub_id: int) -> IntelligenceHubResponse:
    """Fetch a hub with all nested relationships and build the response schema."""
    async with async_session_factory() as session:
        from db.models import (
            EvidenceItem,
            IntelligenceHub,
            IntelligenceQuestion,
            SourceConfidence,
        )

        hub_result = await session.execute(
            select(IntelligenceHub)
            .where(IntelligenceHub.id == hub_id)
            .options(
                selectinload(IntelligenceHub.questions).selectinload(
                    IntelligenceQuestion.evidence_items
                ),
                selectinload(IntelligenceHub.source_confidence),
            )
        )
        hub = hub_result.scalar_one_or_none()

        if not hub:
            raise HTTPException(status_code=404, detail="Intelligence hub not found")

        # Build questions with evidence
        questions: list[IntelligenceQuestionSchema] = []
        for q in hub.questions:
            evidence = [
                EvidenceItemSchema.model_validate(e) for e in q.evidence_items
            ]
            questions.append(
                IntelligenceQuestionSchema(
                    id=q.id,
                    category=q.category,
                    question=q.question,
                    answer=q.answer,
                    confidence=q.confidence,
                    sort_order=q.sort_order,
                    evidence=evidence,
                    created_at=q.created_at,
                )
            )

        # Build source confidence
        source_conf = [
            SourceConfidenceSchema.model_validate(sc) for sc in hub.source_confidence
        ]

        # Build comparable companies (placeholder — populated from competitive agent later)
        comparable_companies: list[dict] = []

        # Build remaining diligence (from questions with category remaining_diligence)
        remaining_diligence = [
            q.question for q in hub.questions if q.category == "remaining_diligence"
        ]

        return IntelligenceHubResponse(
            hub_id=hub.id,
            company_id=hub.company_id,
            deal_id=hub.deal_id,
            status=hub.status,
            executive_briefing=hub.executive_briefing,
            questions=questions,
            source_confidence=source_conf,
            comparable_companies=comparable_companies,
            remaining_diligence=remaining_diligence,
            generated_at=hub.generated_at,
            updated_at=hub.updated_at,
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/health")
async def health() -> dict:
    """Health check for the intelligence hub service."""
    return {"status": "ok"}


@router.get("/{company_id}", response_model=IntelligenceHubResponse)
async def get_intelligence_hub(company_id: int) -> IntelligenceHubResponse:
    """Get the latest Intelligence Hub for a company.

    If no hub exists, returns a 404. Use POST /generate to create one.
    """
    async with async_session_factory() as session:
        hub = await get_hub_by_company(session, company_id)

    if not hub:
        raise HTTPException(
            status_code=404,
            detail=f"No intelligence hub found for company_id={company_id}. Generate one first.",
        )

    return await _build_hub_response(hub.id)


@router.post("/{company_id}/generate", response_model=IntelligenceHubResponse)
async def generate_intelligence_hub(company_id: int) -> IntelligenceHubResponse:
    """Generate or regenerate the Intelligence Hub for a company.

    Creates a new hub with default structure, then attempts to populate
    from the latest agent outputs (research, financials, competitive, LBO).
    """
    async with async_session_factory() as session:
        from db.models import Company

        # Verify company exists
        company_result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=404, detail=f"Company with id={company_id} not found"
            )

        # Check for existing hub
        hub = await get_hub_by_company(session, company_id)
        if hub:
            # Clear existing questions and evidence for regeneration
            for q in hub.questions:
                await session.delete(q)
            for e in hub.evidence:
                await session.delete(e)
            for sc in hub.source_confidence:
                await session.delete(sc)
            await session.commit()
            hub_id = hub.id
            # Update status
            await update_intelligence_hub(
                session, hub_id, status="generated", executive_briefing=None
            )
        else:
            new_hub = await create_intelligence_hub(
                session, company_id=company_id, status="generated"
            )
            hub_id = new_hub.id

    # ── Populate from agent outputs ──────────────────────────────────────────
    # Step 1: Check agent logs for latest outputs
    from sqlalchemy import desc
    from db.models import AgentLog

    async with async_session_factory() as session:
        # Research agent
        research_log = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "IndustryResearchAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        research = research_log.scalar_one_or_none()

        # Competitive agent
        competitive_log = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "CompetitiveMappingAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        competitive = competitive_log.scalar_one_or_none()

        # Financials agent
        financials_log = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "FinancialExtractionAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        financials = financials_log.scalar_one_or_none()

        # LBO agent
        lbo_log = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "LBOModelingAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        lbo = lbo_log.scalar_one_or_none()

        # Pipeline checkpoint
        pipeline_log = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "full_pipeline")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        pipeline = pipeline_log.scalar_one_or_none()

        # Use pipeline checkpoint as fallback if individual agents are missing
        state_data: dict[str, Any] = {}
        if pipeline and pipeline.output_data and pipeline.output_data.get("state_json"):
            from agents.state import deal_state_from_json
            try:
                state_data = deal_state_from_json(pipeline.output_data["state_json"])
            except Exception:
                pass

        # ── Build questions and evidence ─────────────────────────────────────
        questions_created: list[IntelligenceQuestionSchema] = []

        # 1. Executive Briefing (from memo or research)
        exec_briefing = None
        if state_data.get("memo_sections") and isinstance(state_data["memo_sections"], dict):
            exec_section = state_data["memo_sections"].get("executive_summary", {})
            if isinstance(exec_section, dict):
                exec_briefing = exec_section.get("content", "")
        elif research and research.output_data and research.output_data.get("research"):
            r = research.output_data["research"]
            if isinstance(r, dict):
                parts = []
                if r.get("tam"):
                    parts.append(f"Market TAM: ${r['tam']}B")
                if r.get("cagr"):
                    parts.append(f"CAGR: {r['cagr']}%")
                if r.get("growth_drivers"):
                    parts.append(f"Growth drivers: {', '.join(r['growth_drivers'][:3])}")
                exec_briefing = "\n".join(parts) if parts else None

        if exec_briefing:
            await update_intelligence_hub(
                session, hub_id, executive_briefing=exec_briefing
            )

        # 2. Supporting Evidence — Growth Drivers
        growth_drivers: list[str] = []
        if state_data.get("research") and isinstance(state_data["research"], dict):
            growth_drivers = state_data["research"].get("growth_drivers", []) or []
        elif research and research.output_data and research.output_data.get("research"):
            r = research.output_data["research"]
            if isinstance(r, dict):
                growth_drivers = r.get("growth_drivers", []) or []

        if growth_drivers:
            q = await create_intelligence_question(
                session,
                hub_id=hub_id,
                category="supporting_evidence",
                question="What evidence supports the growth thesis?",
                answer="; ".join(growth_drivers[:5]),
                confidence=0.75,
                sort_order=1,
            )
            for driver in growth_drivers[:5]:
                await create_evidence_item(
                    session,
                    hub_id=hub_id,
                    question_id=q.id,
                    text=driver,
                    source="Research Agent",
                    source_type="api",
                    is_supporting=True,
                    confidence=0.75,
                )

        # 3. Contradictory Evidence — Risks
        risks: list[str] = []
        if state_data.get("research") and isinstance(state_data["research"], dict):
            risks = state_data["research"].get("risks", []) or []
        elif research and research.output_data and research.output_data.get("research"):
            r = research.output_data["research"]
            if isinstance(r, dict):
                risks = r.get("risks", []) or []

        if risks:
            q = await create_intelligence_question(
                session,
                hub_id=hub_id,
                category="contradictory_evidence",
                question="What evidence contradicts or risks the investment thesis?",
                answer="; ".join(risks[:5]),
                confidence=0.70,
                sort_order=2,
            )
            for risk in risks[:5]:
                await create_evidence_item(
                    session,
                    hub_id=hub_id,
                    question_id=q.id,
                    text=risk,
                    source="Research Agent",
                    source_type="api",
                    is_contradictory=True,
                    confidence=0.70,
                )

        # 4. Financial Evidence
        fin_profile = None
        if state_data.get("financials"):
            fin_profile = state_data["financials"]
        if financials and financials.output_data:
            # Try to parse financials from output
            pass  # Financial agent output is typically state-based

        if fin_profile:
            fin_parts = []
            if hasattr(fin_profile, "revenue") and fin_profile.revenue is not None:
                fin_parts.append(f"Revenue: ${fin_profile.revenue:,.0f}M")
            if hasattr(fin_profile, "ebitda") and fin_profile.ebitda is not None:
                fin_parts.append(f"EBITDA: ${fin_profile.ebitda:,.0f}M")
            if hasattr(fin_profile, "ebitda_margin") and fin_profile.ebitda_margin is not None:
                fin_parts.append(f"EBITDA Margin: {fin_profile.ebitda_margin:.1%}")
            if hasattr(fin_profile, "net_debt_ebitda") and fin_profile.net_debt_ebitda is not None:
                fin_parts.append(f"Net Debt / EBITDA: {fin_profile.net_debt_ebitda:.1f}x")

            if fin_parts:
                q = await create_intelligence_question(
                    session,
                    hub_id=hub_id,
                    category="supporting_evidence",
                    question="What does the financial profile look like?",
                    answer="\n".join(fin_parts),
                    confidence=0.85,
                    sort_order=3,
                )
                for part in fin_parts:
                    await create_evidence_item(
                        session,
                        hub_id=hub_id,
                        question_id=q.id,
                        text=part,
                        source="Financial Agent",
                        source_type="api",
                        is_supporting=True,
                        confidence=0.85,
                    )

        # 5. Competitive Landscape
        competitors_data: list[dict] = []
        if state_data.get("competitors"):
            competitors_data = state_data["competitors"]
        elif competitive and competitive.output_data and competitive.output_data.get("competitive_map"):
            cmap = competitive.output_data["competitive_map"]
            if isinstance(cmap, dict):
                competitors_data = cmap.get("competitors", []) or []

        if competitors_data:
            comp_names = [c.get("name", "Unknown") for c in competitors_data[:5]]
            q = await create_intelligence_question(
                session,
                hub_id=hub_id,
                category="comparable_companies",
                question="Who are the key competitors?",
                answer="Key competitors: " + ", ".join(comp_names),
                confidence=0.80,
                sort_order=4,
            )
            for comp in competitors_data[:5]:
                name = comp.get("name", "Unknown")
                diff = comp.get("key_differentiators", "")
                text = f"{name}: {diff}" if diff else name
                await create_evidence_item(
                    session,
                    hub_id=hub_id,
                    question_id=q.id,
                    text=text,
                    source="Competitive Agent",
                    source_type="api",
                    is_supporting=True,
                    confidence=0.80,
                )

        # 6. LBO Returns
        lbo_result = None
        if state_data.get("lbo_result"):
            lbo_result = state_data["lbo_result"]
        elif lbo and lbo.output_data and lbo.output_data.get("lbo_result"):
            lbo_result = lbo.output_data["lbo_result"]

        if lbo_result:
            lbo_parts = []
            if isinstance(lbo_result, dict):
                if lbo_result.get("irr") is not None:
                    lbo_parts.append(f"Base IRR: {lbo_result['irr']:.1%}")
                if lbo_result.get("moic") is not None:
                    lbo_parts.append(f"Base MOIC: {lbo_result['moic']:.2f}x")
            else:
                if hasattr(lbo_result, "irr") and lbo_result.irr is not None:
                    lbo_parts.append(f"Base IRR: {lbo_result.irr:.1%}")
                if hasattr(lbo_result, "moic") and lbo_result.moic is not None:
                    lbo_parts.append(f"Base MOIC: {lbo_result.moic:.2f}x")

            if lbo_parts:
                q = await create_intelligence_question(
                    session,
                    hub_id=hub_id,
                    category="supporting_evidence",
                    question="What are the projected returns?",
                    answer="\n".join(lbo_parts),
                    confidence=0.70,
                    sort_order=5,
                )
                for part in lbo_parts:
                    await create_evidence_item(
                        session,
                        hub_id=hub_id,
                        question_id=q.id,
                        text=part,
                        source="LBO Agent",
                        source_type="api",
                        is_supporting=True,
                        confidence=0.70,
                    )

        # 7. Remaining Diligence (placeholder from risk flags)
        risk_flags: list[str] = []
        if state_data.get("risk_flags"):
            risk_flags = state_data["risk_flags"]
        if financials and financials.output_data and financials.output_data.get("risk_flags"):
            risk_flags = financials.output_data["risk_flags"]

        for flag in risk_flags[:3]:
            await create_intelligence_question(
                session,
                hub_id=hub_id,
                category="remaining_diligence",
                question=f"Validate: {flag}",
                answer=None,
                confidence=0.50,
                sort_order=10,
            )

        # 8. Source Confidence defaults
        default_sources = [
            ("Research Agent", "api", 0.75, "Synthesized from web research and filings"),
            ("Financial Agent", "api", 0.85, "Derived from audited financials"),
            ("Competitive Agent", "api", 0.80, "Multi-source enrichment (Wikidata, SEC, Tavily)"),
            ("LBO Agent", "api", 0.70, "Model-based projection with assumptions"),
        ]
        for source_name, source_type, score, rationale in default_sources:
            await create_source_confidence(
                session, hub_id, source_name, source_type, score, rationale
            )

    return await _build_hub_response(hub_id)


# ── Questions ─────────────────────────────────────────────────────────────────


@router.post("/{company_id}/questions", response_model=IntelligenceQuestionSchema)
async def add_question(
    company_id: int, payload: IntelligenceQuestionCreate
) -> IntelligenceQuestionSchema:
    """Add a new question to the hub."""
    async with async_session_factory() as session:
        hub = await get_hub_by_company(session, company_id)
        if not hub:
            raise HTTPException(
                status_code=404,
                detail=f"No intelligence hub for company_id={company_id}. Generate one first.",
            )

        q = await create_intelligence_question(
            session,
            hub_id=hub.id,
            category=payload.category,
            question=payload.question,
            answer=payload.answer,
            confidence=payload.confidence,
            sort_order=payload.sort_order,
        )

        return IntelligenceQuestionSchema(
            id=q.id,
            category=q.category,
            question=q.question,
            answer=q.answer,
            confidence=q.confidence,
            sort_order=q.sort_order,
            evidence=[],
            created_at=q.created_at,
        )


@router.patch("/questions/{question_id}", response_model=IntelligenceQuestionSchema)
async def update_question(
    question_id: int, payload: IntelligenceQuestionUpdate
) -> IntelligenceQuestionSchema:
    """Update an existing question."""
    async with async_session_factory() as session:
        q = await get_intelligence_question_by_id(session, question_id)
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")

        update_data = payload.model_dump(exclude_unset=True)
        if update_data:
            await update_intelligence_question(session, question_id, **update_data)

        # Re-fetch with evidence
        q = await get_intelligence_question_by_id(session, question_id)
        evidence = [
            EvidenceItemSchema.model_validate(e) for e in q.evidence_items
        ] if hasattr(q, "evidence_items") else []

        return IntelligenceQuestionSchema(
            id=q.id,
            category=q.category,
            question=q.question,
            answer=q.answer,
            confidence=q.confidence,
            sort_order=q.sort_order,
            evidence=evidence,
            created_at=q.created_at,
        )


@router.delete("/questions/{question_id}")
async def delete_question(question_id: int) -> dict:
    """Delete a question and its associated evidence."""
    async with async_session_factory() as session:
        success = await delete_intelligence_question(session, question_id)
        if not success:
            raise HTTPException(status_code=404, detail="Question not found")
    return {"deleted": True, "question_id": question_id}


# ── Evidence ──────────────────────────────────────────────────────────────────


@router.post("/{company_id}/evidence", response_model=EvidenceItemSchema)
async def add_evidence(company_id: int, payload: EvidenceItemCreate) -> EvidenceItemSchema:
    """Add evidence to the hub (optionally linked to a question)."""
    async with async_session_factory() as session:
        hub = await get_hub_by_company(session, company_id)
        if not hub:
            raise HTTPException(
                status_code=404,
                detail=f"No intelligence hub for company_id={company_id}. Generate one first.",
            )

        item = await create_evidence_item(
            session,
            hub_id=hub.id,
            text=payload.text,
            source=payload.source,
            source_type=payload.source_type,
            source_url=payload.source_url,
            source_metadata=payload.source_metadata,
            is_supporting=payload.is_supporting,
            is_contradictory=payload.is_contradictory,
            confidence=payload.confidence,
        )

        return EvidenceItemSchema.model_validate(item)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceItemSchema)
async def update_evidence(evidence_id: int, payload: EvidenceItemUpdate) -> EvidenceItemSchema:
    """Update an evidence item."""
    async with async_session_factory() as session:
        item = await get_evidence_item_by_id(session, evidence_id)
        if not item:
            raise HTTPException(status_code=404, detail="Evidence item not found")

        update_data = payload.model_dump(exclude_unset=True)
        if update_data:
            await update_evidence_item(session, evidence_id, **update_data)

        item = await get_evidence_item_by_id(session, evidence_id)
        return EvidenceItemSchema.model_validate(item)


@router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id: int) -> dict:
    """Remove an evidence item."""
    async with async_session_factory() as session:
        success = await delete_evidence_item(session, evidence_id)
        if not success:
            raise HTTPException(status_code=404, detail="Evidence item not found")
    return {"deleted": True, "evidence_id": evidence_id}


# ── Source Confidence ─────────────────────────────────────────────────────────


@router.post("/{company_id}/source-confidence", response_model=SourceConfidenceSchema)
async def set_source_confidence(
    company_id: int, payload: SourceConfidenceCreate
) -> SourceConfidenceSchema:
    """Set or update confidence for a source."""
    async with async_session_factory() as session:
        hub = await get_hub_by_company(session, company_id)
        if not hub:
            raise HTTPException(
                status_code=404,
                detail=f"No intelligence hub for company_id={company_id}. Generate one first.",
            )

        sc = await upsert_source_confidence(
            session,
            hub_id=hub.id,
            source_name=payload.source_name,
            source_type=payload.source_type,
            confidence_score=payload.confidence_score,
            rationale=payload.rationale,
        )

        return SourceConfidenceSchema.model_validate(sc)


@router.patch("/source-confidence/{sc_id}", response_model=SourceConfidenceSchema)
async def update_source_confidence_endpoint(
    sc_id: int, payload: SourceConfidenceUpdate
) -> SourceConfidenceSchema:
    """Update an existing source confidence entry."""
    async with async_session_factory() as session:
        sc = await get_source_confidence_by_id(session, sc_id)
        if not sc:
            raise HTTPException(status_code=404, detail="Source confidence entry not found")

        update_data = payload.model_dump(exclude_unset=True)
        if update_data:
            await update_source_confidence(session, sc_id, **update_data)

        sc = await get_source_confidence_by_id(session, sc_id)
        return SourceConfidenceSchema.model_validate(sc)


@router.get("/{company_id}/source-confidence")
async def list_source_confidence_endpoint(company_id: int) -> list[SourceConfidenceSchema]:
    """List all source confidence scores for a hub."""
    async with async_session_factory() as session:
        hub = await get_hub_by_company(session, company_id)
        if not hub:
            raise HTTPException(
                status_code=404,
                detail=f"No intelligence hub for company_id={company_id}",
            )

        items = await list_source_confidence(session, hub_id=hub.id)
        return [SourceConfidenceSchema.model_validate(sc) for sc in items]
