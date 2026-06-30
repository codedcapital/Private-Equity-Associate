"""Master orchestrator graph for the deal pipeline.

Runs the full pipeline linearly:
    sourcing → research_competitive → financials → lbo → memo

Each node is idempotent: if its outputs already exist in state, it skips.
Each node checkpoints state to PostgreSQL after completing its work.
The pipeline supports resume from failed runs via checkpointed state in agent_logs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy import select

from agents.competitive.graph import run_competitive
from agents.financials.graph import run_financial_analysis
from agents.lbo.graph import run_lbo_analysis
from agents.memo.graph import memo_graph
from agents.research.graph import run_research
from agents.sourcing.graph import run_sourcing
from agents.state import DealState, LBOResult, create_initial_state, deal_state_from_json, deal_state_to_json
from core.run_tracker import RunTracker
from db.crud import create_company, create_deal, create_ic_memo, get_company_by_id, get_deal_by_company_id, update_deal
from db.models import AgentStatus, Company, CompanySource, Deal, DealStage
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)

# ── Stage mapping ─────────────────────────────────────────────────────────────

_NODE_TO_STAGE: dict[str, DealStage] = {
    "sourcing": DealStage.SOURCING,
    "research_competitive": DealStage.DILIGENCE,
    "financials": DealStage.DILIGENCE,
    "lbo": DealStage.IC_READY,
    "memo": DealStage.IC_READY,
}


def _stage_for_node(state: DealState) -> DealStage:
    """Determine the appropriate deal stage based on current state contents."""
    if state.get("memo_sections"):
        return DealStage.IC_READY
    if state.get("lbo_result"):
        return DealStage.IC_READY
    if state.get("financials") and state.get("research") and state.get("competitive_map"):
        return DealStage.DILIGENCE
    if state.get("ranked_candidates") is not None:
        return DealStage.SOURCING
    return DealStage.SOURCING


# ── Checkpoint ────────────────────────────────────────────────────────────────


async def _checkpoint(state: DealState) -> None:
    """Persist DealState after a node completes.

    1. Updates the deal_pipeline stage for the current company.
    2. Serialises the full state into the agent_log output_data for resume.
    """
    company_id = state.get("company_id")
    run_id = state.get("run_id")
    if not company_id:
        return

    # Update deal stage
    async with async_session_factory() as session:
        deal = await get_deal_by_company_id(session, company_id)
        if deal:
            deal.stage = _stage_for_node(state)
            await session.commit()

    # Save checkpoint to agent_log
    if run_id:
        tracker = RunTracker()
        try:
            state_json = deal_state_to_json(state)
            await tracker.update_status(
                run_id=run_id,
                status=AgentStatus.RUNNING,
                output_data={"state_json": state_json},
            )
        except Exception as exc:
            logger.warning("Checkpoint failed for run %s: %s", run_id, exc)


async def checkpoint_node(state: DealState) -> dict[str, Any]:
    """Graph node wrapper for _checkpoint — no state mutation."""
    await _checkpoint(state)
    return {}


async def _checkpoint_after_node(state: DealState, updates: dict[str, Any] | None = None) -> None:
    """Apply node updates to state and checkpoint."""
    if updates:
        for key, value in updates.items():
            if value is not None:
                state[key] = value  # type: ignore[literal-required]
    await _checkpoint(state)


# ── Node 1: sourcing ──────────────────────────────────────────────────────────


async def sourcing_node(state: DealState) -> dict[str, Any]:
    """Run sourcing if thesis is provided; skip if company_id is already known."""
    # Idempotent: if we already have ranked candidates, skip
    if state.get("ranked_candidates") is not None:
        await _checkpoint_after_node(state)
        return {}

    # If company_id is present, skip sourcing and proceed to research
    if state.get("company_id") is not None:
        await _checkpoint_after_node(state)
        return {}

    thesis = state.get("thesis")
    if not thesis:
        await _checkpoint_after_node(state)
        return {
            "errors": state.get("errors", []) + ["Missing thesis for sourcing; no company_id provided"]
        }

    try:
        result = await run_sourcing(thesis)
        updates: dict[str, Any] = {
            "ranked_candidates": result.get("ranked_candidates"),
            "candidates": result.get("candidates"),
            "sourcing_filters": result.get("sourcing_filters"),
        }
        # Merge errors from sourcing
        if result.get("errors"):
            updates["errors"] = state.get("errors", []) + result["errors"]
        await _checkpoint_after_node(state, updates)
        return updates
    except Exception as exc:
        logger.exception("Sourcing node failed: %s", exc)
        await _checkpoint_after_node(state)
        return {"errors": state.get("errors", []) + [f"Sourcing failed: {exc}"]}


# ── Node 2: research + competitive (parallel) ─────────────────────────────────


async def research_competitive_node(state: DealState) -> dict[str, Any]:
    """Run research and competitive analysis in parallel via asyncio.gather()."""
    company_id = state.get("company_id")
    if not company_id:
        await _checkpoint_after_node(state)
        return {
            "errors": state.get("errors", []) + ["Missing company_id for research/competitive"]
        }

    # Idempotent: skip if both outputs already present
    if state.get("research") is not None and state.get("competitive_map") is not None:
        await _checkpoint_after_node(state)
        return {}

    try:
        research_task = run_research(company_id)
        competitive_task = run_competitive(company_id)
        research_result, competitive_result = await asyncio.gather(research_task, competitive_task)

        updates: dict[str, Any] = {
            "research": research_result.get("research"),
            "filing_research": research_result.get("filing_research"),
            "web_research": research_result.get("web_research"),
            "gics_sector": research_result.get("gics_sector"),
            "gics_industry_group": research_result.get("gics_industry_group"),
            "competitive_map": competitive_result.get("competitive_map"),
            "competitors": competitive_result.get("competitors"),
            "competitor_profiles": competitive_result.get("competitor_profiles"),
            "competitor_sources": competitive_result.get("competitor_sources"),
            "structured_competitor_count": competitive_result.get("structured_competitor_count"),
        }

        # Preserve company name / sector from competitive if they were resolved
        if competitive_result.get("company_name"):
            updates["company_name"] = competitive_result["company_name"]
        if competitive_result.get("sector"):
            updates["sector"] = competitive_result["sector"]

        # Merge errors
        errors = state.get("errors", [])[:]
        if research_result.get("errors"):
            errors.extend(research_result["errors"])
        if competitive_result.get("errors"):
            errors.extend(competitive_result["errors"])
        updates["errors"] = errors

        await _checkpoint_after_node(state, updates)
        return updates
    except Exception as exc:
        logger.exception("Research/competitive node failed: %s", exc)
        await _checkpoint_after_node(state)
        return {"errors": state.get("errors", []) + [f"Research/competitive failed: {exc}"]}


# ── Node 3: financials ───────────────────────────────────────────────────────


async def financials_node(state: DealState) -> dict[str, Any]:
    """Run financial analysis for the target company."""
    company_id = state.get("company_id")
    if not company_id:
        await _checkpoint_after_node(state)
        return {
            "errors": state.get("errors", []) + ["Missing company_id for financials"]
        }

    # Idempotent: skip if already present
    if state.get("financials") is not None:
        await _checkpoint_after_node(state)
        return {}

    try:
        result = await run_financial_analysis(company_id)
        updates: dict[str, Any] = {
            "financials": result.get("financials"),
            "risk_flags": result.get("risk_flags"),
            "interpretation": result.get("interpretation"),
        }
        if result.get("errors"):
            updates["errors"] = state.get("errors", []) + result["errors"]
        await _checkpoint_after_node(state, updates)
        return updates
    except Exception as exc:
        logger.exception("Financials node failed: %s", exc)
        await _checkpoint_after_node(state)
        return {"errors": state.get("errors", []) + [f"Financials failed: {exc}"]}


# ── Node 4: lbo ───────────────────────────────────────────────────────────────


async def lbo_node(state: DealState) -> dict[str, Any]:
    """Run LBO modelling for the target company."""
    company_id = state.get("company_id")
    if not company_id:
        await _checkpoint_after_node(state)
        return {
            "errors": state.get("errors", []) + ["Missing company_id for LBO"]
        }

    # Idempotent: skip if already present
    if state.get("lbo_result") is not None:
        await _checkpoint_after_node(state)
        return {}

    overrides = state.get("overrides") or {}
    try:
        result = await run_lbo_analysis(company_id, overrides=overrides)
        updates: dict[str, Any] = {
            "lbo_result": result.get("lbo_result"),
            "lbo_scenarios": result.get("lbo_scenarios"),
            "lbo_results": result.get("lbo_results"),
            "lbo_sensitivity": result.get("lbo_sensitivity"),
            "lbo_interpretation": result.get("lbo_interpretation"),
        }
        if result.get("errors"):
            updates["errors"] = state.get("errors", []) + result["errors"]

        # Also write LBO result to the deal table so downstream DB readers see it
        if result.get("lbo_result"):
            lbo = result["lbo_result"]
            async with async_session_factory() as session:
                deal = await get_deal_by_company_id(session, company_id)
                if deal:
                    await update_deal(
                        session,
                        deal.id,
                        lbo_irr=lbo.get("irr"),
                        lbo_moic=lbo.get("moic"),
                        entry_ev=lbo.get("exit_ev"),
                    )

        await _checkpoint_after_node(state, updates)
        return updates
    except Exception as exc:
        logger.exception("LBO node failed: %s", exc)
        await _checkpoint_after_node(state)
        return {"errors": state.get("errors", []) + [f"LBO failed: {exc}"]}


# ── Node 5: memo ───────────────────────────────────────────────────────────────


async def memo_node(state: DealState) -> dict[str, Any]:
    """Generate IC memo and save to the database.

    Uses the orchestrator's accumulated state so that research, competitive,
    financials and LBO outputs are all available to the memo graph.
    """
    company_id = state.get("company_id")
    if not company_id:
        await _checkpoint_after_node(state)
        return {
            "errors": state.get("errors", []) + ["Missing company_id for memo"]
        }

    # Idempotent: skip if memo already generated
    if state.get("memo_sections") is not None and state.get("memo_id") is not None:
        await _checkpoint_after_node(state)
        return {}

    try:
        # Run the memo graph directly with the orchestrator's accumulated state
        final_state = await memo_graph.ainvoke(state)

        # Extract memo outputs
        updates: dict[str, Any] = {
            "memo_sections": final_state.get("memo_sections"),
            "memo_total_words": final_state.get("memo_total_words"),
            "memo_avg_confidence": final_state.get("memo_avg_confidence"),
            "memo_context": final_state.get("memo_context"),
            "memo_edit_notes": final_state.get("memo_edit_notes"),
        }

        if final_state.get("errors"):
            updates["errors"] = state.get("errors", []) + list(final_state["errors"])

        # Save memo to ic_memos table
        memo_sections = final_state.get("memo_sections") or {}
        total_words = final_state.get("memo_total_words", 0)
        avg_confidence = final_state.get("memo_avg_confidence", 0.0)

        if memo_sections:
            async with async_session_factory() as session:
                memo = await create_ic_memo(
                    session,
                    company_id=company_id,
                    sections=memo_sections,
                    word_count=total_words,
                    confidence_score=avg_confidence,
                )
                updates["memo_id"] = memo.id

                # Link memo to deal
                deal = await get_deal_by_company_id(session, company_id)
                if deal:
                    await update_deal(session, deal.id, memo_id=memo.id)

        await _checkpoint_after_node(state, updates)
        return updates
    except Exception as exc:
        logger.exception("Memo node failed: %s", exc)
        await _checkpoint_after_node(state)
        return {"errors": state.get("errors", []) + [f"Memo generation failed: {exc}"]}


# ── Graph wiring ──────────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("sourcing", sourcing_node)
builder.add_node("research_competitive", research_competitive_node)
builder.add_node("financials", financials_node)
builder.add_node("lbo", lbo_node)
builder.add_node("memo", memo_node)

builder.set_entry_point("sourcing")
builder.add_edge("sourcing", "research_competitive")
builder.add_edge("research_competitive", "financials")
builder.add_edge("financials", "lbo")
builder.add_edge("lbo", "memo")
builder.add_edge("memo", END)

graph = builder.compile()


# ── Helper: run_full_pipeline ─────────────────────────────────────────────────


async def _resolve_company(company_name_or_id: str | int) -> tuple[int, str]:
    """Resolve a company identifier into (company_id, company_name).

    If int: look up in DB.
    If str: look up by name (case-insensitive) or create a new company.
    """
    if isinstance(company_name_or_id, int):
        async with async_session_factory() as session:
            company = await get_company_by_id(session, company_name_or_id)
            if not company:
                raise ValueError(f"Company with id={company_name_or_id} not found")
            return company.id, company.name

    # str: try to find existing, else create
    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.name.ilike(f"%{company_name_or_id}%"))
        )
        company = result.scalar_one_or_none()
        if company:
            return company.id, company.name

        # Create new company
        company = await create_company(
            session,
            name=company_name_or_id,
            source=CompanySource.MANUAL,
        )
        return company.id, company.name


async def run_full_pipeline(
    company_name_or_id: str | int,
    thesis: str | None = None,
    existing_run_id: str | None = None,
) -> DealState:
    """Run the full pipeline from sourcing through memo generation.

    Args:
        company_name_or_id: If int, treated as company_id. If str, treated as company name.
        thesis: Natural language investment thesis (used for sourcing step).
        existing_run_id: If provided, resume from a failed run using its checkpoint.

    Returns:
        Final DealState with all agent outputs.
    """
    # 1. Resolve company
    try:
        company_id, company_name = await _resolve_company(company_name_or_id)
    except ValueError as exc:
        initial_state = create_initial_state(str(company_name_or_id), company_id=None if isinstance(company_name_or_id, str) else company_name_or_id)
        initial_state["thesis"] = thesis
        initial_state["errors"] = [str(exc)]
        return initial_state

    # 2. Get or create deal
    async with async_session_factory() as session:
        deal = await get_deal_by_company_id(session, company_id)
        if not deal:
            deal = await create_deal(session, company_id=company_id, stage=DealStage.SOURCING)

    # 3. Build initial state
    initial_state = create_initial_state(company_name, company_id=company_id)
    initial_state["thesis"] = thesis

    # 4. Resume logic
    tracker = RunTracker()
    run_id = existing_run_id

    if run_id:
        log = await tracker.get_run(run_id)
        if log and log.output_data and isinstance(log.output_data, dict):
            state_json = log.output_data.get("state_json")
            if state_json:
                try:
                    checkpointed = deal_state_from_json(state_json)
                    for key, value in checkpointed.items():
                        if value is not None:
                            initial_state[key] = value  # type: ignore[literal-required]
                    initial_state["errors"] = initial_state.get("errors", []) + ["Resumed from failed run"]
                    logger.info("Resumed pipeline for company_id=%s from run_id=%s", company_id, run_id)
                except Exception as exc:
                    logger.warning("Failed to resume checkpoint for run %s: %s", run_id, exc)
        # Mark existing run as RUNNING again
        try:
            await tracker.update_status(run_id=run_id, status=AgentStatus.RUNNING)
        except Exception as exc:
            logger.warning("Failed to update run status for %s: %s", run_id, exc)
    else:
        run_id = await tracker.start_run(
            agent_name="full_pipeline",
            input_data={
                "company_id": company_id,
                "company_name": company_name,
                "thesis": thesis,
            },
        )

    initial_state["run_id"] = run_id

    # 5. Run the graph
    try:
        final_state = await graph.ainvoke(initial_state)

        # Mark as complete
        await tracker.update_status(
            run_id=run_id,
            status=AgentStatus.COMPLETE,
            output_data={"state_json": deal_state_to_json(final_state)},
        )

        return final_state  # type: ignore[return-value]
    except Exception as exc:
        logger.exception("Pipeline failed for run %s: %s", run_id, exc)
        initial_state["errors"] = initial_state.get("errors", []) + [str(exc)]
        await tracker.log_error(run_id, str(exc))
        return initial_state


__all__ = [
    "graph",
    "builder",
    "sourcing_node",
    "research_competitive_node",
    "financials_node",
    "lbo_node",
    "memo_node",
    "checkpoint_node",
    "_checkpoint_after_node",
    "run_full_pipeline",
]
