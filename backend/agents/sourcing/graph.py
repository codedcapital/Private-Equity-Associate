"""LangGraph sourcing pipeline — thesis → DB screen → web enrichment → score & rank.

Four-node async graph:
  parse_thesis → screen_database → enrich_candidates → score_and_rank → END
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy import func, select

from agents.state import DealState
from core.config import settings
from core.llm import LLMClient
from core.run_tracker import RunTracker
from db.models import AgentStatus, Company, Financial
from db.session import async_session_factory

logger = logging.getLogger(__name__)

TAVILY_API_KEY = settings.tavily_api_key


class SourcingFilters(BaseModel):
    """Structured filters extracted from a natural-language investment thesis."""

    sector: str | None = None
    geography: str | None = None
    revenue_min: float | None = None
    revenue_max: float | None = None
    ebitda_margin_min: float | None = None
    growth_rate_min: float | None = None


# ── Node 1: parse_thesis ─────────────────────────────────────────────────────


async def parse_thesis(state: DealState) -> DealState:
    """Convert natural language thesis into structured sourcing filters."""
    thesis = state.get("thesis", "")
    if not thesis:
        state["errors"] = state.get("errors", []) + ["Missing thesis in state"]
        state["sourcing_filters"] = {}
        return state

    llm = LLMClient()
    system_prompt = (
        "You are an expert PE investment analyst. Parse the user's investment thesis "
        "into a structured JSON object with these fields: sector, geography, "
        "revenue_min, revenue_max, ebitda_margin_min, growth_rate_min. "
        "Use null for fields not mentioned. Revenue values should be numeric dollars "
        "(e.g., €10M = 10000000). ebitda_margin_min and growth_rate_min should be "
        "decimal fractions (e.g., 0.15 for 15%)."
    )
    try:
        parsed = await llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=f"Thesis: {thesis}",
            response_model=SourcingFilters,
        )
        state["sourcing_filters"] = parsed.model_dump()
    except Exception as exc:
        logger.warning("LLM thesis parsing failed: %s", exc)
        state["sourcing_filters"] = _heuristic_parse_thesis(thesis)

    return state


def _heuristic_parse_thesis(thesis: str) -> dict[str, Any]:
    """Simple keyword-based thesis parser when LLM is unavailable."""
    thesis_lower = thesis.lower()
    filters: dict[str, Any] = {}

    # Sector matching
    sector_keywords = {
        "b2b saas": "B2B SaaS",
        "saas": "B2B SaaS",
        "software": "B2B SaaS",
        "fintech": "FinTech",
        "healthcare": "Healthcare",
        "telecom": "Telecom",
        "cpaas": "CPaaS",
        "analytics": "Analytics",
    }
    for kw, sector_val in sector_keywords.items():
        if kw in thesis_lower:
            filters["sector"] = sector_val
            break

    # Geography matching
    geo_keywords = {
        "europe": "Europe",
        "european": "Europe",
        "us": "United States",
        "usa": "United States",
        "united states": "United States",
        "north america": "North America",
        "uk": "United Kingdom",
        "asia": "Asia",
    }
    for kw, geo_val in geo_keywords.items():
        if kw in thesis_lower:
            filters["geography"] = geo_val
            break

    # Revenue range extraction
    revenue_patterns = [
        r"€?\$?\s*(\d+(?:\.\d+)?)\s*-\s*€?\$?\s*(\d+(?:\.\d+)?)\s*[Mm]",
        r"€?\$?\s*(\d+(?:\.\d+)?)\s*[Mm]\s*-\s*€?\$?\s*(\d+(?:\.\d+)?)\s*[Mm]",
    ]
    for pattern in revenue_patterns:
        match = re.search(pattern, thesis_lower)
        if match:
            filters["revenue_min"] = float(match.group(1)) * 1e6
            filters["revenue_max"] = float(match.group(2)) * 1e6
            break

    # Single revenue value
    if "revenue_min" not in filters:
        match = re.search(
            r"€?\$?\s*(\d+(?:\.\d+)?)\s*[Mm](?:\s+arr|\s+revenue)?",
            thesis_lower,
        )
        if match:
            filters["revenue_min"] = float(match.group(1)) * 1e6

    # EBITDA margin
    if "profitable" in thesis_lower or "margin" in thesis_lower:
        filters["ebitda_margin_min"] = 0.15

    # Growth rate
    if "growth" in thesis_lower:
        filters["growth_rate_min"] = 0.20

    return filters


# ── Node 2: screen_database ──────────────────────────────────────────────────


async def screen_database(state: DealState) -> DealState:
    """Query the database for candidates matching the sourcing filters."""
    filters = state.get("sourcing_filters", {})
    if not filters:
        state["errors"] = state.get("errors", []) + ["No sourcing filters available"]
        state["candidates"] = []
        return state

    async with async_session_factory() as session:
        # Subquery for latest financial report per company
        subq = (
            select(
                Financial.company_id,
                func.max(Financial.report_date).label("latest_report_date"),
            )
            .group_by(Financial.company_id)
            .subquery()
        )

        stmt = (
            select(
                Company.id,
                Company.name,
                Company.ticker,
                Company.sector,
                Company.geography,
                Financial.revenue,
                Financial.ebitda,
                Financial.ebitda_margin,
                Financial.revenue_growth,
                Financial.net_debt,
                Financial.fcf,
            )
            .join(Financial, Company.id == Financial.company_id)
            .join(
                subq,
                (Financial.company_id == subq.c.company_id)
                & (Financial.report_date == subq.c.latest_report_date),
            )
        )

        # Apply filters dynamically
        sector = filters.get("sector")
        if sector:
            # Use keyword-based matching for sectors since LLM returns arbitrary names
            sector_lower = sector.lower()
            # Map common LLM sector outputs to DB sector keywords
            sector_keywords = []
            if any(k in sector_lower for k in ("saas", "software", "cloud", "b2b")):
                sector_keywords.extend(["saas", "software"])
            if any(k in sector_lower for k in ("fintech", "finance", "financial", "banking", "payment")):
                sector_keywords.extend(["fintech", "finance"])
            if any(k in sector_lower for k in ("healthcare", "health", "medical", "biotech", "pharma")):
                sector_keywords.extend(["healthcare", "health", "medical"])
            if any(k in sector_lower for k in ("telecom", "cpaas", "communication", "network")):
                sector_keywords.extend(["telecom", "cpaas", "communication"])
            if any(k in sector_lower for k in ("analytics", "data", "ai", "machine learning")):
                sector_keywords.extend(["analytics", "data"])
            if any(k in sector_lower for k in ("consumer", "retail", "ecommerce", "e-commerce")):
                sector_keywords.extend(["consumer", "retail"])
            if any(k in sector_lower for k in ("technology", "tech")):
                sector_keywords.extend(["technology", "tech"])
            if not sector_keywords:
                sector_keywords = [sector_lower]

            # Build OR conditions for each keyword
            from sqlalchemy import or_
            conditions = []
            for kw in sector_keywords:
                conditions.append(Company.sector.ilike(f"%{kw}%"))
            stmt = stmt.where(or_(*conditions))

        geography = filters.get("geography")
        if geography:
            stmt = stmt.where(Company.geography.ilike(f"%{geography}%"))

        revenue_min = filters.get("revenue_min")
        revenue_max = filters.get("revenue_max")
        if revenue_min is not None:
            stmt = stmt.where(Financial.revenue >= revenue_min)
        if revenue_max is not None:
            stmt = stmt.where(Financial.revenue <= revenue_max)

        ebitda_margin_min = filters.get("ebitda_margin_min")
        if ebitda_margin_min is not None:
            stmt = stmt.where(Financial.ebitda_margin >= ebitda_margin_min)

        growth_rate_min = filters.get("growth_rate_min")
        if growth_rate_min is not None:
            stmt = stmt.where(Financial.revenue_growth >= growth_rate_min)

        stmt = stmt.order_by(Financial.revenue.desc()).limit(20)

        result = await session.execute(stmt)
        rows = result.all()

        candidates = [
            {
                "company_id": row.id,
                "name": row.name,
                "ticker": row.ticker,
                "sector": row.sector,
                "geography": row.geography,
                "revenue": row.revenue,
                "ebitda": row.ebitda,
                "ebitda_margin": row.ebitda_margin,
                "revenue_growth": row.revenue_growth,
                "net_debt": row.net_debt,
                "fcf": row.fcf,
            }
            for row in rows
        ]

        # Fallback: if sector filter yielded nothing, return all companies
        if not candidates and sector:
            logger.info(
                "Sector filter '%s' yielded no matches; falling back to all companies", sector
            )
            stmt_fallback = (
                select(
                    Company.id,
                    Company.name,
                    Company.ticker,
                    Company.sector,
                    Company.geography,
                    Financial.revenue,
                    Financial.ebitda,
                    Financial.ebitda_margin,
                    Financial.revenue_growth,
                    Financial.net_debt,
                    Financial.fcf,
                )
                .join(Financial, Company.id == Financial.company_id)
                .join(
                    subq,
                    (Financial.company_id == subq.c.company_id)
                    & (Financial.report_date == subq.c.latest_report_date),
                )
                .order_by(Financial.revenue.desc())
                .limit(20)
            )
            result_fb = await session.execute(stmt_fallback)
            rows_fb = result_fb.all()
            candidates = [
                {
                    "company_id": row.id,
                    "name": row.name,
                    "ticker": row.ticker,
                    "sector": row.sector,
                    "geography": row.geography,
                    "revenue": row.revenue,
                    "ebitda": row.ebitda,
                    "ebitda_margin": row.ebitda_margin,
                    "revenue_growth": row.revenue_growth,
                    "net_debt": row.net_debt,
                    "fcf": row.fcf,
                }
                for row in rows_fb
            ]

        state["candidates"] = candidates
    return state


# ── Node 3: enrich_candidates ────────────────────────────────────────────────


async def enrich_candidates(state: DealState) -> DealState:
    """Enrich candidate data from web search using Tavily."""
    candidates = state.get("candidates", [])
    if not candidates:
        return state

    if not TAVILY_API_KEY:
        logger.info("TAVILY_API_KEY not set; skipping enrichment")
        return state

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
    except Exception as exc:
        logger.warning("Failed to initialize Tavily client: %s", exc)
        return state

    enriched_candidates = []
    for candidate in candidates:
        # Enrich revenue if missing
        if candidate.get("revenue") is None:
            try:
                query = f"{candidate['name']} revenue 2024"
                result = await client.search(query, max_results=3, include_answer=True)
                answer = result.get("answer", "")
                rev_match = re.search(
                    r"[\$€]?\s*(\d+(?:\.\d+)?)\s*([BbMm])", answer
                )
                if rev_match:
                    val = float(rev_match.group(1))
                    suffix = rev_match.group(2).upper()
                    if suffix == "B":
                        candidate["revenue"] = val * 1e9
                    else:
                        candidate["revenue"] = val * 1e6
            except Exception as exc:
                logger.debug(
                    "Tavily revenue enrichment failed for %s: %s",
                    candidate["name"],
                    exc,
                )

        # Enrich sector if missing
        if candidate.get("sector") is None:
            try:
                query = f"{candidate['name']} industry"
                result = await client.search(query, max_results=3, include_answer=True)
                answer = result.get("answer", "")
                if "software" in answer.lower() or "saas" in answer.lower():
                    candidate["sector"] = "B2B SaaS"
                elif "healthcare" in answer.lower():
                    candidate["sector"] = "Healthcare"
                elif "fintech" in answer.lower():
                    candidate["sector"] = "FinTech"
                elif "telecom" in answer.lower() or "cpaas" in answer.lower():
                    candidate["sector"] = "Telecom"
                else:
                    candidate["sector"] = answer[:50] if answer else None
            except Exception as exc:
                logger.debug(
                    "Tavily sector enrichment failed for %s: %s",
                    candidate["name"],
                    exc,
                )

        enriched_candidates.append(candidate)

    state["candidates"] = enriched_candidates
    return state


# ── Node 4: score_and_rank ───────────────────────────────────────────────────


async def score_and_rank(state: DealState) -> DealState:
    """Score and rank candidates based on weighted criteria."""
    candidates = state.get("candidates", [])
    filters = state.get("sourcing_filters", {})

    if not candidates:
        state["ranked_candidates"] = []
        return state

    sector_filter = filters.get("sector")
    geo_filter = filters.get("geography")
    revenue_min = filters.get("revenue_min")
    revenue_max = filters.get("revenue_max")
    ebitda_margin_min = filters.get("ebitda_margin_min")
    growth_rate_min = filters.get("growth_rate_min")

    scored = []
    for candidate in candidates:
        # 1. Sector fit (30%)
        sector_score = 0.0
        candidate_sector = (candidate.get("sector") or "").lower()
        if sector_filter:
            filter_sector = sector_filter.lower()
            if filter_sector == candidate_sector:
                sector_score = 1.0
            elif filter_sector in candidate_sector or candidate_sector in filter_sector:
                sector_score = 0.5
        else:
            sector_score = 0.5

        # 2. Financial profile (40%)
        financial_score = 0.0
        revenue = candidate.get("revenue")
        ebitda_margin = candidate.get("ebitda_margin")
        growth = candidate.get("revenue_growth")

        checks = 0
        passed = 0

        # Revenue in range
        if revenue_min is not None or revenue_max is not None:
            checks += 1
            in_range = True
            if revenue_min is not None and (revenue is None or revenue < revenue_min):
                in_range = False
            if revenue_max is not None and (revenue is None or revenue > revenue_max):
                in_range = False
            if in_range:
                passed += 1

        # Margin above threshold
        if ebitda_margin_min is not None:
            checks += 1
            if ebitda_margin is not None and ebitda_margin >= ebitda_margin_min:
                passed += 1

        # Growth above threshold
        if growth_rate_min is not None:
            checks += 1
            if growth is not None and growth >= growth_rate_min:
                passed += 1

        # Also consider raw profitability and growth
        if ebitda_margin is not None and ebitda_margin > 0:
            checks += 1
            passed += 1
        if growth is not None and growth > 0:
            checks += 1
            passed += 1

        if checks > 0:
            financial_score = passed / checks
        else:
            financial_score = 0.5

        # 3. Strategic rationale (30%)
        strategic_score = 0.0
        geo_match = False
        if geo_filter:
            candidate_geo = (candidate.get("geography") or "").lower()
            if geo_filter.lower() in candidate_geo or candidate_geo in geo_filter.lower():
                geo_match = True
        else:
            geo_match = True

        has_financials = bool(
            candidate.get("revenue") is not None
            and candidate.get("ebitda_margin") is not None
        )

        if geo_match and has_financials:
            strategic_score = 1.0
        elif geo_match or has_financials:
            strategic_score = 0.5

        # Weighted total
        total_score = (
            0.30 * sector_score + 0.40 * financial_score + 0.30 * strategic_score
        )

        # Build rationale
        rationale_parts = []
        if sector_score >= 0.5:
            rationale_parts.append(
                f"Sector fit ({candidate.get('sector') or 'unknown'})"
            )
        if financial_score >= 0.5:
            rationale_parts.append("Strong financial profile")
        if strategic_score >= 0.5:
            rationale_parts.append("Strategic match")

        rationale = ", ".join(rationale_parts) if rationale_parts else "Partial match"

        scored.append(
            {
                "company_id": candidate["company_id"],
                "name": candidate["name"],
                "score": round(total_score, 4),
                "rationale": rationale,
                "sector": candidate.get("sector"),
                "geography": candidate.get("geography"),
                "revenue": candidate.get("revenue"),
                "ebitda_margin": candidate.get("ebitda_margin"),
                "revenue_growth": candidate.get("revenue_growth"),
                "weights": {
                    "sector_fit": 0.30,
                    "financial_profile": 0.40,
                    "strategic_rationale": 0.30,
                },
            }
        )

    # Sort by score descending, take top 10
    scored.sort(key=lambda x: x["score"], reverse=True)
    state["ranked_candidates"] = scored[:10]
    return state


# ── Graph wiring ─────────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("parse_thesis", parse_thesis)
builder.add_node("screen_database", screen_database)
builder.add_node("enrich_candidates", enrich_candidates)
builder.add_node("score_and_rank", score_and_rank)

builder.set_entry_point("parse_thesis")
builder.add_edge("parse_thesis", "screen_database")
builder.add_edge("screen_database", "enrich_candidates")
builder.add_edge("enrich_candidates", "score_and_rank")
builder.add_edge("score_and_rank", END)

sourcing_graph = builder.compile()


# ── Helper ──────────────────────────────────────────────────────────────────


async def run_sourcing(thesis: str) -> DealState:
    """Run the full sourcing pipeline for an investment thesis."""
    tracker = RunTracker()
    run_id = await tracker.start_run(
        agent_name="SourcingAgent", input_data={"thesis": thesis}
    )

    state: DealState = {
        "company_name": "",
        "company_id": None,
        "run_id": run_id,
        "errors": [],
        "thesis": thesis,
    }

    try:
        final_state = await sourcing_graph.ainvoke(state)
        ranked = final_state.get("ranked_candidates", [])
        await tracker.update_status(
            run_id=run_id,
            status=AgentStatus.COMPLETE,
            output_data={"ranked_candidates": ranked, "thesis": thesis},
        )
        return final_state  # type: ignore[return-value]
    except Exception as exc:
        logger.exception("Sourcing pipeline failed: %s", exc)
        state["errors"] = state.get("errors", []) + [str(exc)]
        await tracker.log_error(run_id, str(exc))
        return state
