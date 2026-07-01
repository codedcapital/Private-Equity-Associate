"""Intelligence Hub Writer — Service for agents to deposit evidence.

Provides a clean async API that any agent can use to write structured evidence
into the Intelligence Hub without worrying about CRUD details or schema shapes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from db.crud import (
    create_evidence_item,
    create_intelligence_hub,
    create_intelligence_question,
    get_hub_by_company,
    update_intelligence_hub,
    upsert_source_confidence,
)
from db.session import async_session_factory

logger = logging.getLogger(__name__)


# ── Source confidence rules (static baseline) ────────────────────────────────

SOURCE_CONFIDENCE_BASE: dict[str, tuple[float, str]] = {
    "SEC EDGAR": (0.95, "Regulatory filing — high verifiability, audited, publicly disclosed"),
    "Yahoo Finance": (0.90, "Real-time market data from publicly traded companies"),
    "FMP": (0.88, "Financial Modeling Prep — structured financial data"),
    "Expert Call (GLG)": (0.85, "Domain expert with direct industry experience"),
    "Tavily Web Search": (0.60, "Web aggregation — may be promotional or outdated"),
    "Internal Diligence": (0.80, "Internal analysis based on management-provided data"),
    "Research Agent": (0.75, "Synthesized from web research and filing semantic search"),
    "Financial Agent": (0.85, "Derived from audited financials with deterministic ratios"),
    "Competitive Agent": (0.80, "Multi-source enrichment (Wikidata, SEC, Tavily)"),
    "LBO Agent": (0.70, "Model-based projection with explicit assumptions"),
    "Memo Agent": (0.65, "Synthesized prose from multiple agent outputs"),
    "Risk Flagging Agent": (0.75, "Rule-based flags with heuristic thresholds"),
}


# ── Hub Writer ───────────────────────────────────────────────────────────────


class HubWriter:
    """Stateful writer for a single company's Intelligence Hub.

    Usage:
        writer = HubWriter(company_id=7)
        await writer.ensure_hub()
        await writer.add_question(
            category="supporting_evidence",
            question="What evidence supports the growth thesis?",
            answer="Three structural tailwinds...",
            confidence=0.78,
        )
        await writer.add_evidence(
            question_text="What evidence supports the growth thesis?",
            text="Domestic 3PL gross revenue projected to grow 6.1% CAGR...",
            source="Research Agent",
            source_type="api",
            is_supporting=True,
            confidence=0.75,
        )
    """

    def __init__(self, company_id: int, deal_id: int | None = None):
        self.company_id = company_id
        self.deal_id = deal_id
        self.hub_id: int | None = None
        self._question_cache: dict[str, int] = {}  # question_text -> question_id

    async def ensure_hub(self, status: str = "generated") -> int:
        """Get or create the Intelligence Hub for this company."""
        async with async_session_factory() as session:
            hub = await get_hub_by_company(session, self.company_id)
            if hub:
                self.hub_id = hub.id
                if hub.status != status:
                    await update_intelligence_hub(session, hub.id, status=status)
                return hub.id

            new_hub = await create_intelligence_hub(
                session,
                company_id=self.company_id,
                deal_id=self.deal_id,
                status=status,
            )
            self.hub_id = new_hub.id
            logger.info(
                "Created Intelligence Hub id=%s for company_id=%s", self.hub_id, self.company_id
            )
            return self.hub_id

    async def set_executive_briefing(self, briefing: str) -> None:
        """Set the AI-generated executive briefing."""
        if self.hub_id is None:
            await self.ensure_hub()
        async with async_session_factory() as session:
            await update_intelligence_hub(
                session, self.hub_id, executive_briefing=briefing
            )

    async def add_question(
        self,
        category: str,
        question: str,
        answer: str | None = None,
        confidence: float | None = None,
        sort_order: int = 0,
    ) -> int:
        """Add a question to the hub. Returns the question_id."""
        if self.hub_id is None:
            await self.ensure_hub()

        # Cache hit — don't duplicate
        if question in self._question_cache:
            return self._question_cache[question]

        async with async_session_factory() as session:
            q = await create_intelligence_question(
                session,
                hub_id=self.hub_id,
                category=category,
                question=question,
                answer=answer,
                confidence=confidence,
                sort_order=sort_order,
            )
            self._question_cache[question] = q.id
            return q.id

    async def add_evidence(
        self,
        question_text: str | None,
        text: str,
        source: str,
        source_type: str,
        source_url: str | None = None,
        source_metadata: dict | None = None,
        is_supporting: bool = False,
        is_contradictory: bool = False,
        confidence: float | None = None,
    ) -> None:
        """Add evidence to the hub, optionally linked to a question."""
        if self.hub_id is None:
            await self.ensure_hub()

        question_id: int | None = None
        if question_text:
            if question_text not in self._question_cache:
                # Create a minimal question placeholder if not found
                await self.add_question(
                    category="supporting_evidence",
                    question=question_text,
                    confidence=0.5,
                )
            question_id = self._question_cache.get(question_text)

        async with async_session_factory() as session:
            await create_evidence_item(
                session,
                hub_id=self.hub_id,
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

    async def set_source_confidence(self, source_name: str, source_type: str) -> None:
        """Set the confidence score for a source using built-in rules."""
        if self.hub_id is None:
            await self.ensure_hub()

        score, rationale = SOURCE_CONFIDENCE_BASE.get(
            source_name, (0.50, "Default confidence for unknown source")
        )

        async with async_session_factory() as session:
            await upsert_source_confidence(
                session,
                hub_id=self.hub_id,
                source_name=source_name,
                source_type=source_type,
                confidence_score=score,
                rationale=rationale,
            )

    async def add_remaining_diligence(self, question: str, priority: str = "medium") -> None:
        """Add an open diligence question."""
        await self.add_question(
            category="remaining_diligence",
            question=question,
            confidence=0.50,
            sort_order=100,  # Open questions sort last
        )


# ── Convenience: write full hub from DealState ───────────────────────────────


async def write_hub_from_research_state(
    company_id: int,
    research: dict[str, Any] | None,
    financials: Any | None,
    competitive_map: dict | None,
    competitors: list[dict] | None,
    lbo_result: dict | None,
    risk_flags: list[str] | None,
    interpretation: str | None,
) -> int:
    """One-shot hub population from all agent outputs.

    This is what the generate endpoint currently does, but as a reusable
    service so agents can call it directly after they finish.
    """
    writer = HubWriter(company_id=company_id)
    await writer.ensure_hub()

    # 1. Executive briefing (from research interpretation)
    briefing_parts: list[str] = []
    if research:
        if research.get("tam"):
            briefing_parts.append(f"Market TAM: ${research['tam']}B")
        if research.get("cagr"):
            briefing_parts.append(f"CAGR: {research['cagr']}%")
        if research.get("growth_drivers"):
            drivers = research["growth_drivers"]
            if isinstance(drivers, list):
                briefing_parts.append(f"Growth drivers: {', '.join(drivers[:3])}")
    if financials:
        if hasattr(financials, "revenue") and financials.revenue is not None:
            briefing_parts.append(f"Revenue: ${financials.revenue:,.0f}")
        if hasattr(financials, "ebitda") and financials.ebitda is not None:
            briefing_parts.append(f"EBITDA: ${financials.ebitda:,.0f}")
    if lbo_result:
        if lbo_result.get("irr") is not None:
            briefing_parts.append(f"Base IRR: {lbo_result['irr']:.1%}")
        if lbo_result.get("moic") is not None:
            briefing_parts.append(f"Base MOIC: {lbo_result['moic']:.2f}x")

    if briefing_parts:
        await writer.set_executive_briefing("\n".join(briefing_parts))

    # 2. Supporting Evidence — Growth Drivers
    growth_drivers = (research or {}).get("growth_drivers", []) or []
    if growth_drivers and isinstance(growth_drivers, list):
        q_text = "What evidence supports the growth thesis?"
        await writer.add_question(
            category="supporting_evidence",
            question=q_text,
            answer="; ".join(growth_drivers[:5]),
            confidence=0.75,
            sort_order=1,
        )
        for driver in growth_drivers[:5]:
            await writer.add_evidence(
                question_text=q_text,
                text=driver,
                source="Research Agent",
                source_type="api",
                is_supporting=True,
                confidence=0.75,
            )
        await writer.set_source_confidence("Research Agent", "api")

    # 3. Contradictory Evidence — Risks
    risks = (research or {}).get("risks", []) or []
    if risks and isinstance(risks, list):
        q_text = "What evidence contradicts or risks the investment thesis?"
        await writer.add_question(
            category="contradictory_evidence",
            question=q_text,
            answer="; ".join(risks[:5]),
            confidence=0.70,
            sort_order=2,
        )
        for risk in risks[:5]:
            await writer.add_evidence(
                question_text=q_text,
                text=risk,
                source="Research Agent",
                source_type="api",
                is_contradictory=True,
                confidence=0.70,
            )

    # 4. Financial Evidence
    if financials:
        fin_parts = []
        if hasattr(financials, "revenue") and financials.revenue is not None:
            fin_parts.append(f"Revenue: ${financials.revenue:,.0f}")
        if hasattr(financials, "ebitda") and financials.ebitda is not None:
            fin_parts.append(f"EBITDA: ${financials.ebitda:,.0f}")
        if hasattr(financials, "ebitda_margin") and financials.ebitda_margin is not None:
            fin_parts.append(f"EBITDA Margin: {financials.ebitda_margin:.1%}")
        if hasattr(financials, "net_debt_ebitda") and financials.net_debt_ebitda is not None:
            fin_parts.append(f"Net Debt / EBITDA: {financials.net_debt_ebitda:.1f}x")

        if fin_parts:
            q_text = "What does the financial profile look like?"
            await writer.add_question(
                category="supporting_evidence",
                question=q_text,
                answer="\n".join(fin_parts),
                confidence=0.85,
                sort_order=3,
            )
            for part in fin_parts:
                await writer.add_evidence(
                    question_text=q_text,
                    text=part,
                    source="Financial Agent",
                    source_type="api",
                    is_supporting=True,
                    confidence=0.85,
                )
            await writer.set_source_confidence("Financial Agent", "api")

    # 5. Competitive Landscape
    if competitors and isinstance(competitors, list):
        comp_names = [c.get("name", "Unknown") for c in competitors[:5]]
        q_text = "Who are the key competitors?"
        await writer.add_question(
            category="comparable_companies",
            question=q_text,
            answer="Key competitors: " + ", ".join(comp_names),
            confidence=0.80,
            sort_order=4,
        )
        for comp in competitors[:5]:
            name = comp.get("name", "Unknown")
            diff = comp.get("key_differentiators", "")
            text = f"{name}: {diff}" if diff else name
            await writer.add_evidence(
                question_text=q_text,
                text=text,
                source="Competitive Agent",
                source_type="api",
                is_supporting=True,
                confidence=0.80,
            )
        await writer.set_source_confidence("Competitive Agent", "api")

    # 6. LBO Returns
    if lbo_result:
        lbo_parts = []
        if lbo_result.get("irr") is not None:
            lbo_parts.append(f"Base IRR: {lbo_result['irr']:.1%}")
        if lbo_result.get("moic") is not None:
            lbo_parts.append(f"Base MOIC: {lbo_result['moic']:.2f}x")

        if lbo_parts:
            q_text = "What are the projected returns?"
            await writer.add_question(
                category="supporting_evidence",
                question=q_text,
                answer="\n".join(lbo_parts),
                confidence=0.70,
                sort_order=5,
            )
            for part in lbo_parts:
                await writer.add_evidence(
                    question_text=q_text,
                    text=part,
                    source="LBO Agent",
                    source_type="api",
                    is_supporting=True,
                    confidence=0.70,
                )
            await writer.set_source_confidence("LBO Agent", "api")

    # 7. Risk Flags → Remaining Diligence
    if risk_flags and isinstance(risk_flags, list):
        for flag in risk_flags[:3]:
            await writer.add_remaining_diligence(f"Validate: {flag}")

    # 8. Interpretation → Expert Consensus
    if interpretation:
        await writer.add_question(
            category="expert_consensus",
            question="What is the synthesized view from all agents?",
            answer=interpretation,
            confidence=0.65,
            sort_order=6,
        )
        await writer.add_evidence(
            question_text="What is the synthesized view from all agents?",
            text=interpretation,
            source="Memo Agent",
            source_type="api",
            is_supporting=True,
            confidence=0.65,
        )
        await writer.set_source_confidence("Memo Agent", "api")

    return writer.hub_id
