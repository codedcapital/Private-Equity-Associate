"""LangGraph IC memo generation pipeline.

Four-node async graph:
  aggregate_context → write_sections → edit_pass → format_output → END
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy import select

from agents.memo.prompts import (
    PROMPT_MEMO_COMPANY_OVERVIEW,
    PROMPT_MEMO_COMPETITIVE_POSITIONING,
    PROMPT_MEMO_EXECUTIVE_SUMMARY,
    PROMPT_MEMO_FINANCIAL_ANALYSIS,
    PROMPT_MEMO_INDUSTRY_ANALYSIS,
    PROMPT_MEMO_INVESTMENT_RECOMMENDATION,
    PROMPT_MEMO_LBO_MODEL,
    PROMPT_MEMO_RISK_FACTORS,
)
from agents.state import DealState, create_initial_state
from core.llm import LLMClient
from db.crud import create_ic_memo
from db.models import Company, Financial
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)

# Mapping of section keys to their display names and prompts
from agents.memo.prompts import SECTION_CONFIG


# ── Helpers ───────────────────────────────────────────────────────────────────


def _format_context(context: dict) -> str:
    """Flatten the structured context into a key=value string for prompts."""
    lines = []
    for top_key, top_val in context.items():
        if isinstance(top_val, dict):
            for sub_key, sub_val in top_val.items():
                lines.append(f"{top_key}[{sub_key}]={sub_val}")
        else:
            lines.append(f"{top_key}={top_val}")
    return "\n".join(lines)


def _compute_confidence(content: str) -> float:
    """Heuristic confidence score based on content substance."""
    word_count = len(content.split())
    if word_count > 300:
        return 0.90
    if word_count > 200:
        return 0.85
    if word_count > 100:
        return 0.80
    if word_count > 50:
        return 0.70
    if word_count > 20:
        return 0.60
    return 0.50


async def _write_section(
    section_key: str,
    display_name: str,
    system_prompt: str,
    context: dict,
) -> tuple[str, str, int, float]:
    """Call LLM for a single section and return (key, content, word_count, confidence)."""
    llm = LLMClient()
    user_prompt = _format_context(context)

    try:
        content = await llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
    except Exception as exc:
        logger.warning("LLM call failed for section %s: %s", section_key, exc)
        content = f"[{display_name} placeholder — LLM not configured]"

    word_count = len(content.split())
    confidence = _compute_confidence(content)
    return section_key, content, word_count, confidence


# ── Node 1: aggregate_context ───────────────────────────────────────────────


async def aggregate_context(state: DealState) -> DealState:
    """Pull all prior agent outputs into a structured context object."""
    context: dict[str, Any] = {
        "company": {
            "name": state.get("company_name") or "Unknown",
            "sector": state.get("sector") or "Unknown",
        },
        "financials": {},
        "lbo": {},
        "competitive": state.get("competitive_map") or {},
        "research": state.get("research") or {},
    }

    financials = state.get("financials")
    if financials:
        context["financials"] = {
            "revenue": financials.revenue,
            "ebitda": financials.ebitda,
            "ebitda_margin": financials.ebitda_margin,
            "revenue_growth": financials.revenue_growth,
            "net_debt": financials.net_debt,
            "net_debt_ebitda": financials.net_debt_ebitda,
            "fcf": financials.fcf,
            "fcf_yield": financials.fcf_yield,
        }

    lbo = state.get("lbo_result")
    if lbo:
        context["lbo"] = {
            "irr": lbo.get("irr"),
            "moic": lbo.get("moic"),
            "entry_equity": lbo.get("entry_equity"),
            "entry_debt": lbo.get("entry_debt"),
            "exit_ev": lbo.get("exit_ev"),
            "exit_equity": lbo.get("exit_equity"),
        }

    scenarios = state.get("lbo_results")
    if scenarios:
        context["lbo"]["scenarios"] = {
            k: {
                "irr": getattr(v, "irr", None),
                "moic": getattr(v, "moic", None),
            }
            for k, v in scenarios.items()
        }

    sensitivity = state.get("lbo_sensitivity")
    if sensitivity:
        context["lbo"]["sensitivity"] = "Available (see model)"

    state["memo_context"] = context
    return state


# ── Node 2: write_sections ──────────────────────────────────────────────────


async def write_sections(state: DealState) -> DealState:
    """Make 8 LLM calls in parallel to write each memo section."""
    context = state.get("memo_context")
    if not context:
        state["errors"] = state.get("errors", []) + ["No memo context available"]
        return state

    tasks = [
        _write_section(key, display, prompt, context)
        for key, display, prompt in SECTION_CONFIG
    ]

    results = await asyncio.gather(*tasks)

    memo_sections: dict[str, dict] = {}
    for key, content, word_count, confidence in results:
        memo_sections[key] = {
            "content": content,
            "word_count": word_count,
            "confidence_score": confidence,
        }

    state["memo_sections"] = memo_sections
    return state


# ── Node 3: edit_pass ───────────────────────────────────────────────────────


async def edit_pass(state: DealState) -> DealState:
    """Review the full draft for consistency, contradictions, and missing sections."""
    memo_sections = state.get("memo_sections")
    if not memo_sections:
        state["errors"] = state.get("errors", []) + ["No memo sections to edit"]
        state["memo_edit_notes"] = {"needs_revision": False, "notes": []}
        return state

    notes: list[str] = []
    needs_revision = False

    # Check all 8 sections are present
    expected_keys = {key for key, _, _ in SECTION_CONFIG}
    actual_keys = set(memo_sections.keys())
    missing = expected_keys - actual_keys
    if missing:
        notes.append(f"Missing sections: {', '.join(missing)}")
        needs_revision = True

    # Check for placeholder-only sections
    for key, section in memo_sections.items():
        content = section.get("content", "")
        if "placeholder" in content.lower() or "LLM not configured" in content:
            notes.append(f"Section '{key}' contains placeholder text")

    # Check for contradictions between executive summary and recommendation
    exec_summary = memo_sections.get("executive_summary", {}).get("content", "").lower()
    recommendation = memo_sections.get("investment_recommendation", {}).get("content", "").lower()

    if exec_summary and recommendation:
        exec_positive = any(w in exec_summary for w in ("proceed", "strong buy", "attractive", "compelling"))
        exec_negative = any(w in exec_summary for w in ("pass", "reject", "decline", "avoid"))
        rec_positive = any(w in recommendation for w in ("proceed", "approve", "recommend"))
        rec_negative = any(w in recommendation for w in ("pass", "reject", "decline"))

        if exec_positive and rec_negative:
            notes.append("Contradiction: Executive Summary is positive but Recommendation says PASS")
            needs_revision = True
        if exec_negative and rec_positive:
            notes.append("Contradiction: Executive Summary is negative but Recommendation says PROCEED")
            needs_revision = True

    # Check financial consistency between financial_analysis and lbo_model
    financial_analysis = memo_sections.get("financial_analysis", {}).get("content", "").lower()
    lbo_model = memo_sections.get("lbo_model", {}).get("content", "").lower()

    financials = state.get("financials")
    if financials and financials.ebitda is not None:
        ebitda_str = f"{financials.ebitda:.1f}".rstrip("0").rstrip(".")
        if ebitda_str not in financial_analysis:
            notes.append("Financial Analysis section does not cite EBITDA from state")
        if lbo_model and ebitda_str not in lbo_model:
            notes.append("LBO Model section does not cite EBITDA from state")

    state["memo_edit_notes"] = {
        "needs_revision": needs_revision,
        "notes": notes,
    }
    return state


# ── Node 4: format_output ─────────────────────────────────────────────────────


async def format_output(state: DealState) -> DealState:
    """Structure final output, compute totals, and ensure all sections are present."""
    memo_sections = state.get("memo_sections")
    if not memo_sections:
        state["errors"] = state.get("errors", []) + ["No memo sections to format"]
        return state

    total_words = 0
    total_confidence = 0.0
    count = 0

    for key, section in memo_sections.items():
        content = section.get("content", "")
        word_count = len(content.split())
        section["word_count"] = word_count
        total_words += word_count
        total_confidence += section.get("confidence_score", 0.0)
        count += 1

    state["memo_total_words"] = total_words
    state["memo_avg_confidence"] = total_confidence / count if count > 0 else 0.0
    return state


# ── Graph wiring ─────────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("aggregate_context", aggregate_context)
builder.add_node("write_sections", write_sections)
builder.add_node("edit_pass", edit_pass)
builder.add_node("format_output", format_output)

builder.set_entry_point("aggregate_context")
builder.add_edge("aggregate_context", "write_sections")
builder.add_edge("write_sections", "edit_pass")
builder.add_edge("edit_pass", "format_output")
builder.add_edge("format_output", END)

memo_graph = builder.compile()


# ── Helper: run_memo_generation ───────────────────────────────────────────────


async def run_memo_generation(company_id: int) -> DealState:
    """End-to-end memo generation for a given company.

    1. Look up company from DB
    2. Build initial DealState (populate financials, lbo_result from DB if available)
    3. Run memo_graph
    4. Save result to `ic_memos` table
    5. Return final state
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

    # Pull latest financials from DB
    async with async_session_factory() as session:
        fin_result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = fin_result.scalar_one_or_none()
        if fin:
            state["financials"] = FinancialProfile(
                revenue=fin.revenue,
                ebitda=fin.ebitda,
                ebitda_margin=fin.ebitda_margin,
                revenue_growth=fin.revenue_growth,
                net_debt=fin.net_debt,
                net_debt_ebitda=fin.net_debt_ebitda,
                fcf=fin.fcf,
                fcf_yield=fin.fcf_yield,
            )

    # Pull latest deal/LBO data from DB
    from db.models import Deal

    async with async_session_factory() as session:
        deal_result = await session.execute(
            select(Deal)
            .where(Deal.company_id == company_id)
            .order_by(Deal.last_updated.desc())
            .limit(1)
        )
        deal = deal_result.scalar_one_or_none()
        if deal:
            from agents.state import LBOResult

            state["lbo_result"] = LBOResult(
                entry_equity=deal.entry_ev,
                entry_debt=None,
                irr=deal.lbo_irr,
                moic=deal.lbo_moic,
                exit_ev=None,
                exit_equity=None,
            )

    # Run the memo graph
    final_state = await memo_graph.ainvoke(state)

    # Save to DB
    memo_sections = final_state.get("memo_sections") or {}
    total_words = final_state.get("memo_total_words", 0)
    avg_confidence = final_state.get("memo_avg_confidence", 0.0)

    async with async_session_factory() as session:
        memo = await create_ic_memo(
            session,
            company_id=company_id,
            sections=memo_sections,
            word_count=total_words,
            confidence_score=avg_confidence,
        )
        final_state["memo_id"] = memo.id

    return final_state
