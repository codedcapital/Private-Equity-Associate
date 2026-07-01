"""LangGraph industry research pipeline.

Four-node async graph:
  classify_sector → retrieve_filings → web_research → synthesize → END
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy import select

from agents.state import DealState, create_initial_state
from core.config import settings
from core.llm import LLMClient
from core.vector_search import ChunkResult, semantic_search
from db.models import Company
from db.session import async_session_factory

logger = logging.getLogger(__name__)

# ── GICS keyword mapping ────────────────────────────────────────────────────

GICS_SECTOR_MAP: dict[str, str] = {
    "b2b saas": "Software & IT Services",
    "saas": "Software & IT Services",
    "software": "Software & IT Services",
    "analytics": "Software & IT Services",
    "data analytics": "Software & IT Services",
    "business intelligence": "Software & IT Services",
    "cloud": "Software & IT Services",
    "enterprise software": "Software & IT Services",
    "cpaas": "Communication Services",
    "telecom": "Communication Services",
    "telecommunications": "Communication Services",
    "communication": "Communication Services",
    "wireless": "Communication Services",
    "5g": "Communication Services",
    "media": "Communication Services",
    "healthcare": "Health Care",
    "biotech": "Health Care",
    "pharma": "Health Care",
    "medical": "Health Care",
    "fintech": "Financials",
    "banking": "Financials",
    "insurance": "Financials",
    "financial": "Financials",
    "energy": "Energy",
    "oil": "Energy",
    "gas": "Energy",
    "renewable": "Utilities",
    "retail": "Consumer Discretionary",
    "ecommerce": "Consumer Discretionary",
    "consumer": "Consumer Discretionary",
    "food": "Consumer Staples",
    "beverage": "Consumer Staples",
    "manufacturing": "Industrials",
    "industrial": "Industrials",
    "aerospace": "Industrials",
    "defense": "Industrials",
    "logistics": "Industrials",
    "transportation": "Industrials",
    "semiconductor": "Information Technology",
    "hardware": "Information Technology",
    "electronics": "Information Technology",
    "real estate": "Real Estate",
    "reit": "Real Estate",
    "materials": "Materials",
    "chemicals": "Materials",
    "mining": "Materials",
    "utilities": "Utilities",
}

GICS_INDUSTRY_GROUP_MAP: dict[str, str] = {
    "b2b saas": "Software",
    "saas": "Software",
    "software": "Software",
    "analytics": "Software",
    "data analytics": "Software",
    "business intelligence": "Software",
    "cloud": "Internet Services & Infrastructure",
    "enterprise software": "Software",
    "cpaas": "Interactive Media & Services",
    "telecom": "Telecommunication Services",
    "telecommunications": "Telecommunication Services",
    "communication": "Telecommunication Services",
    "wireless": "Wireless Telecommunication Services",
    "5g": "Wireless Telecommunication Services",
    "media": "Media",
    "healthcare": "Health Care Equipment & Services",
    "biotech": "Biotechnology",
    "pharma": "Pharmaceuticals",
    "medical": "Health Care Equipment & Services",
    "fintech": "Financial Services",
    "banking": "Banks",
    "insurance": "Insurance",
    "financial": "Financial Services",
    "energy": "Energy Equipment & Services",
    "oil": "Oil, Gas & Consumable Fuels",
    "gas": "Oil, Gas & Consumable Fuels",
    "renewable": "Independent Power and Renewable Electricity Producers",
    "retail": "Retailing",
    "ecommerce": "Internet & Direct Marketing Retail",
    "consumer": "Automobiles & Components",
    "food": "Food, Beverage & Tobacco",
    "beverage": "Food, Beverage & Tobacco",
    "manufacturing": "Capital Goods",
    "industrial": "Capital Goods",
    "aerospace": "Aerospace & Defense",
    "defense": "Aerospace & Defense",
    "logistics": "Transportation",
    "transportation": "Transportation",
    "semiconductor": "Semiconductors & Semiconductor Equipment",
    "hardware": "Technology Hardware, Storage & Peripherals",
    "electronics": "Technology Hardware, Storage & Peripherals",
    "real estate": "Real Estate",
    "reit": "Real Estate",
    "materials": "Materials",
    "chemicals": "Chemicals",
    "mining": "Metals & Mining",
    "utilities": "Utilities",
}


# ── IndustryProfile schema ──────────────────────────────────────────────────


class IndustryProfile(BaseModel):
    """Structured output from the industry research synthesis step."""

    tam: float | None = None  # Total Addressable Market in USD billions
    cagr: float | None = None  # Compound Annual Growth Rate (percentage)
    growth_drivers: list[str] = []
    risks: list[str] = []
    regulatory_notes: str = ""
    key_players: list[str] = []
    sources: list[str] = []


# ── Node 1: classify_sector ───────────────────────────────────────────────


async def classify_sector(state: DealState) -> DealState:
    """Map company name/sector to GICS taxonomy.

    Uses a keyword-based lookup first; if no match is found, attempts an LLM
    call.  Falls back to "Unknown" if the LLM is unavailable.
    """
    sector = (state.get("sector") or "").lower()
    company_name = (state.get("company_name") or "").lower()

    gics_sector: str | None = None
    gics_industry_group: str | None = None

    search_text = f"{sector} {company_name}"
    for keyword, mapped_sector in GICS_SECTOR_MAP.items():
        if keyword in search_text:
            gics_sector = mapped_sector
            gics_industry_group = GICS_INDUSTRY_GROUP_MAP.get(keyword)
            break

    # Fallback to LLM if available and no keyword match
    if not gics_sector:
        llm = LLMClient()
        try:
            prompt = (
                f"Map this company to GICS taxonomy. Company: '{company_name}', "
                f"Sector: '{sector}'. Return ONLY a JSON object with keys "
                f"'gics_sector' and 'gics_industry_group'."
            )
            response = await llm.chat(
                system_prompt="You are a GICS taxonomy expert. Respond with valid JSON only.",
                user_prompt=prompt,
                temperature=0.0,
            )
            try:
                parsed = json.loads(response)
                gics_sector = parsed.get("gics_sector")
                gics_industry_group = parsed.get("gics_industry_group")
            except json.JSONDecodeError:
                pass
        except Exception as exc:
            logger.warning("LLM sector classification failed: %s", exc)

    state["gics_sector"] = gics_sector or "Unknown"
    state["gics_industry_group"] = gics_industry_group or "Unknown"
    return state


# ── Node 2: retrieve_filings ──────────────────────────────────────────────


async def retrieve_filings(state: DealState) -> DealState:
    """Semantic search on filing_chunks for sector-relevant content.

    Runs three queries (market size, competitive landscape, trends/risks) and
    deduplicates by chunk_id.  Stores results in state["filing_research"].
    """
    sector = state.get("gics_sector") or state.get("sector") or "industry"

    queries = [
        f"{sector} market size and growth",
        f"{sector} competitive landscape",
        f"{sector} industry trends and risks",
    ]

    chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[int] = set()

    for query in queries:
        try:
            results = await semantic_search(query, top_k=5)
            for result in results:
                if result.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(result.chunk_id)
                    chunks.append(
                        {
                            "chunk_id": result.chunk_id,
                            "filing_id": result.filing_id,
                            "text": result.chunk_text,
                            "similarity_score": result.similarity_score,
                            "source": f"filing_chunk:{result.chunk_id}",
                        }
                    )
        except Exception as exc:
            logger.warning("Semantic search failed for query '%s': %s", query, exc)

    state["filing_research"] = chunks
    return state


# ── Node 3: web_research ──────────────────────────────────────────────────


async def web_research(state: DealState) -> DealState:
    """Use Tavily API to search for recent news, market reports, and competitors.

    If TAVILY_API_KEY is not set or the client fails to initialise, the node
    skips gracefully and stores an empty list.
    """
    sector = state.get("gics_sector") or state.get("sector") or ""
    company_name = state.get("company_name") or ""

    tavily_api_key = settings.tavily_api_key
    if not tavily_api_key:
        logger.info("TAVILY_API_KEY not set; skipping web research")
        state["web_research"] = []
        return state

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=tavily_api_key)
    except Exception as exc:
        logger.warning("Failed to initialise Tavily client: %s", exc)
        state["web_research"] = []
        return state

    queries = [
        f"{sector} market size TAM 2024 2025",
        f"{sector} industry growth drivers trends",
        f"{company_name} competitors market share",
    ]

    web_results: list[dict[str, Any]] = []

    for query in queries:
        try:
            response = await client.search(query, max_results=3)
            results = response.get("results", [])
            for item in results:
                web_results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")
                        or item.get("snippet", ""),
                        "source": item.get("url", ""),
                    }
                )
        except Exception as exc:
            logger.warning("Tavily search failed for query '%s': %s", query, exc)

    state["web_research"] = web_results
    return state


# ── Node 4: synthesize ────────────────────────────────────────────────────


async def synthesize(state: DealState) -> DealState:
    """Use LLM to produce structured industry profile.

    Builds a context string from filing_research + web_research and asks the
    LLM to return an IndustryProfile.  Falls back to a placeholder if the LLM
    is unavailable.
    """
    filing_research = state.get("filing_research", []) or []
    web_research = state.get("web_research", []) or []

    parts: list[str] = []

    if filing_research:
        parts.append("=== FILING RESEARCH ===")
        for item in filing_research:
            parts.append(f"Source: {item['source']}")
            parts.append(f"Text: {item['text'][:500]}")
            parts.append("")

    if web_research:
        parts.append("=== WEB RESEARCH ===")
        for item in web_research:
            parts.append(f"Title: {item['title']}")
            parts.append(f"URL: {item['url']}")
            parts.append(f"Snippet: {item['snippet'][:500]}")
            parts.append("")

    context = "\n".join(parts)
    if not context.strip():
        context = "No research data available. Provide a generic industry analysis."

    llm = LLMClient()
    try:
        system_prompt = (
            "You are a PE industry analyst. Given the research context below, "
            "produce a structured industry profile. Return valid JSON only."
        )
        user_prompt = (
            f"{context}\n\n"
            "Return JSON with keys: tam (float, USD billions), cagr (float, percentage), "
            "growth_drivers (list of strings), risks (list of strings), "
            "regulatory_notes (string), key_players (list of strings), "
            "sources (list of strings, citing chunk IDs or URLs)."
        )

        parsed = await llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=IndustryProfile,
        )
        state["research"] = parsed.model_dump(mode="json")
    except Exception as exc:
        logger.warning("LLM synthesis failed: %s", exc)
        # Build a placeholder with sources from whatever research we have
        sources: list[str] = []
        for item in filing_research:
            sources.append(item["source"])
        for item in web_research:
            sources.append(item["url"])

        placeholder = IndustryProfile(
            tam=None,
            cagr=None,
            growth_drivers=[
                "[LLM unavailable] Cloud migration and AI adoption",
                "[LLM unavailable] Enterprise digital transformation",
            ],
            risks=[
                "[LLM unavailable] Regulatory uncertainty and macroeconomic headwinds",
                "[LLM unavailable] Intensifying competition and margin pressure",
            ],
            regulatory_notes="[LLM unavailable] Pending regulation may impact market dynamics.",
            key_players=[
                "[LLM unavailable] Key players unavailable",
            ],
            sources=sources if sources else ["placeholder"],
        )
        state["research"] = placeholder.model_dump(mode="json")

    # ── Write to Intelligence Hub ───────────────────────────────────────
    try:
        from services.intelligence_hub_writer import HubWriter
        writer = HubWriter(
            company_id=state.get("company_id"),
            deal_id=state.get("deal_id"),
        )
        await writer.ensure_hub()
        research_data = state.get("research", {})
        if research_data:
            # Growth drivers → Supporting Evidence
            drivers = research_data.get("growth_drivers", [])
            if drivers and isinstance(drivers, list):
                q_text = "What evidence supports the growth thesis?"
                await writer.add_question(
                    category="supporting_evidence",
                    question=q_text,
                    answer="; ".join(drivers[:5]),
                    confidence=0.75,
                    sort_order=1,
                )
                for driver in drivers[:5]:
                    await writer.add_evidence(
                        question_text=q_text,
                        text=driver,
                        source="Research Agent",
                        source_type="api",
                        is_supporting=True,
                        confidence=0.75,
                    )
                await writer.set_source_confidence("Research Agent", "api")
            # Risks → Contradictory Evidence
            risks = research_data.get("risks", [])
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
            # TAM/CAGR → Executive Briefing building blocks
            briefing_parts = []
            if research_data.get("tam"):
                briefing_parts.append(f"Market TAM: ${research_data['tam']}B")
            if research_data.get("cagr"):
                briefing_parts.append(f"CAGR: {research_data['cagr']}%")
            if briefing_parts:
                await writer.set_executive_briefing("\n".join(briefing_parts))
    except Exception as hub_exc:
        logger.warning("Failed to write research to Intelligence Hub: %s", hub_exc)

    return state


async def produce_research_evidence(state: DealState) -> DealState:
    """Node 5: Produce structured EvidenceModule for the Decision Engine."""
    research_data = state.get("research", {})
    if not research_data:
        state["errors"] = state.get("errors", []) + [
            "No research data available for evidence module"
        ]
        return state

    from schemas.evidence import EvidenceMetric, EvidenceModule

    metrics: list[EvidenceMetric] = []
    warnings: list[str] = []
    insights: list[str] = []
    sources: list[str] = ["Research Agent"]

    # TAM
    tam = research_data.get("tam")
    if tam is not None:
        metrics.append(EvidenceMetric(
            name="Market TAM",
            value=f"${tam:.1f}B",
            direction="stable",
            confidence=0.75,
            is_supporting=tam > 10,
            is_contradictory=False,
            evidence_text=f"Total addressable market of ${tam:.1f}B provides {'significant' if tam > 50 else 'adequate'} runway for growth.",
            source="Research Agent",
            source_type="api",
        ))
        insights.append(f"Market TAM of ${tam:.1f}B")

    # CAGR
    cagr = research_data.get("cagr")
    if cagr is not None:
        metrics.append(EvidenceMetric(
            name="Industry CAGR",
            value=f"{cagr:.1f}%",
            direction="improving" if cagr > 5 else "stable",
            confidence=0.70,
            is_supporting=cagr > 3,
            is_contradictory=cagr < 0,
            evidence_text=f"Industry growing at {cagr:.1f}% CAGR indicates {'strong' if cagr > 5 else 'moderate' if cagr > 0 else 'negative'} tailwinds.",
            source="Research Agent",
            source_type="api",
        ))
        insights.append(f"Industry CAGR of {cagr:.1f}%")

    # Growth Drivers
    drivers = research_data.get("growth_drivers", [])
    if drivers and isinstance(drivers, list):
        for i, driver in enumerate(drivers[:3]):
            metrics.append(EvidenceMetric(
                name=f"Growth Driver {i+1}",
                value="Present",
                direction="improving",
                confidence=0.75,
                is_supporting=True,
                is_contradictory=False,
                evidence_text=driver,
                source="Research Agent",
                source_type="api",
            ))
        insights.append(f"{len(drivers)} growth drivers identified")

    # Risks
    risks = research_data.get("risks", [])
    if risks and isinstance(risks, list):
        for i, risk in enumerate(risks[:3]):
            metrics.append(EvidenceMetric(
                name=f"Risk Factor {i+1}",
                value="Present",
                direction="elevated",
                confidence=0.70,
                is_supporting=False,
                is_contradictory=True,
                evidence_text=risk,
                source="Research Agent",
                source_type="api",
            ))
            warnings.append(risk)
        insights.append(f"{len(risks)} risk factors identified")

    # Key Players
    key_players = research_data.get("key_players", [])
    if key_players and isinstance(key_players, list):
        insights.append(f"Key players: {', '.join(key_players[:3])}")

    # Regulatory
    regulatory = research_data.get("regulatory_notes", "")
    if regulatory and not regulatory.startswith("[LLM unavailable]"):
        warnings.append(f"Regulatory: {regulatory[:100]}")

    # Overall confidence
    avg_confidence = sum(m.confidence for m in metrics) / len(metrics) if metrics else 0.0

    module = EvidenceModule(
        module_type="research",
        company_id=state.get("company_id", 0),
        metrics=metrics,
        overall_confidence=round(avg_confidence, 2),
        key_insights=insights[:5],
        warnings=warnings[:5],
        sources=sources,
    )

    state["research_evidence_module"] = module.model_dump(mode="json")
    return state


# ── Graph wiring ───────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("classify_sector", classify_sector)
builder.add_node("retrieve_filings", retrieve_filings)
builder.add_node("web_research", web_research)
builder.add_node("synthesize", synthesize)
builder.add_node("produce_research_evidence", produce_research_evidence)

builder.set_entry_point("classify_sector")
builder.add_edge("classify_sector", "retrieve_filings")
builder.add_edge("retrieve_filings", "web_research")
builder.add_edge("web_research", "synthesize")
builder.add_edge("synthesize", "produce_research_evidence")
builder.add_edge("produce_research_evidence", END)

research_graph = builder.compile()


# ── Helper ─────────────────────────────────────────────────────────────────


async def run_research(company_id: int) -> DealState:
    """Run the full research graph for a company.

    Looks up the company from the DB, seeds the initial state with the
    company name and sector, and invokes the graph.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

    if not company:
        state = create_initial_state("Unknown", company_id=company_id)
        state["errors"] = [f"Company with id={company_id} not found"]
        return state

    state = create_initial_state(company.name, company_id=company_id)
    state["sector"] = company.sector

    final_state = await research_graph.ainvoke(state)
    return final_state  # type: ignore[return-value]
