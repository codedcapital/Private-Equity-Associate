"""LangGraph financial analysis pipeline.

Four-node async graph:
  load_data → compute_ratios → flag_risks → interpret → END
"""

import logging
from datetime import datetime

from sqlalchemy import select

from agents.state import DealState, create_initial_state
from core.llm import LLMClient
from core.prompts import PROMPT_FINANCIAL_INTERPRET
from db.models import Company, Financial
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)


async def load_data(state: DealState) -> DealState:
    """Node 1: Fetch financials from DB for company_id."""
    company_id = state.get("company_id")
    if not company_id:
        state["errors"] = state.get("errors", []) + ["Missing company_id in state"]
        return state

    async with async_session_factory() as session:
        result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = result.scalar_one_or_none()

        if not fin:
            state["errors"] = state.get("errors", []) + [
                f"No financials found for company_id={company_id}"
            ]
            return state

        profile = FinancialProfile(
            revenue=fin.revenue,
            ebitda=fin.ebitda,
            ebitda_margin=fin.ebitda_margin,
            revenue_growth=fin.revenue_growth,
            net_debt=fin.net_debt,
            net_debt_ebitda=fin.net_debt_ebitda,
            fcf=fin.fcf,
            fcf_yield=fin.fcf_yield,
        )

        state["financials"] = profile
    return state


async def compute_ratios(state: DealState) -> DealState:
    """Node 2: Pure Python ratio calculation.

    Re-verifies / re-computes: ebitda_margin, net_debt_ebitda, revenue_growth, fcf_yield.
    """
    financials = state.get("financials")
    if not financials:
        state["errors"] = state.get("errors", []) + [
            "No financials available to compute ratios"
        ]
        return state

    company_id = state.get("company_id")
    if not company_id:
        state["errors"] = state.get("errors", []) + [
            "Missing company_id for ratio computation"
        ]
        return state

    async with async_session_factory() as session:
        result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = result.scalar_one_or_none()

        if not fin:
            state["errors"] = state.get("errors", []) + [
                f"No financials found for company_id={company_id}"
            ]
            return state

        revenue = fin.revenue
        ebitda = fin.ebitda
        total_debt = fin.total_debt
        cash = fin.cash
        operating_cf = fin.operating_cf
        capex = fin.capex

        # Use existing ratios if present, otherwise compute from raw fields
        ebitda_margin = financials.ebitda_margin
        if ebitda_margin is None and revenue and ebitda is not None:
            ebitda_margin = ebitda / revenue

        net_debt = financials.net_debt
        if net_debt is None and total_debt is not None and cash is not None:
            net_debt = total_debt - cash

        net_debt_ebitda = financials.net_debt_ebitda
        if net_debt_ebitda is None and net_debt is not None and ebitda is not None and ebitda != 0:
            net_debt_ebitda = net_debt / ebitda

        fcf = financials.fcf
        if fcf is None and operating_cf is not None and capex is not None:
            fcf = operating_cf - capex

        fcf_yield = financials.fcf_yield
        if fcf_yield is None and fcf is not None and revenue and revenue != 0:
            fcf_yield = fcf / revenue

        revenue_growth = financials.revenue_growth

        updated = FinancialProfile(
            revenue=revenue,
            ebitda=ebitda,
            ebitda_margin=ebitda_margin,
            revenue_growth=revenue_growth,
            net_debt=net_debt,
            net_debt_ebitda=net_debt_ebitda,
            fcf=fcf,
            fcf_yield=fcf_yield,
        )

        state["financials"] = updated
    return state


async def flag_risks(state: DealState) -> DealState:
    """Node 3: Rule-based risk flags."""
    financials = state.get("financials")
    if not financials:
        state["errors"] = state.get("errors", []) + [
            "No financials available for risk flagging"
        ]
        return state

    flags: list[str] = []

    if financials.net_debt_ebitda is not None and financials.net_debt_ebitda > 5.0:
        flags.append("leverage concern")
    if financials.revenue_growth is not None and financials.revenue_growth < 0:
        flags.append("declining revenue")
    if financials.ebitda_margin is not None and financials.ebitda_margin < 0.10:
        flags.append("low profitability")
    if financials.fcf_yield is not None and financials.fcf_yield < 0.02:
        flags.append("poor cash conversion")

    state["risk_flags"] = flags
    return state


async def interpret(state: DealState) -> DealState:
    """Node 4: LLM call to narrate financial picture."""
    financials = state.get("financials")
    if not financials:
        state["errors"] = state.get("errors", []) + [
            "No financials available for interpretation"
        ]
        return state

    # Build context string from the FinancialProfile
    parts: list[str] = []
    if financials.revenue is not None:
        parts.append(f"Revenue: ${financials.revenue:.2f}M")
    if financials.ebitda is not None:
        parts.append(f"EBITDA: ${financials.ebitda:.2f}M")
    if financials.ebitda_margin is not None:
        parts.append(f"EBITDA margin: {financials.ebitda_margin * 100:.1f}%")
    if financials.net_debt_ebitda is not None:
        parts.append(f"Net debt/EBITDA: {financials.net_debt_ebitda:.1f}x")
    if financials.fcf_yield is not None:
        parts.append(f"FCF yield: {financials.fcf_yield * 100:.1f}%")
    if financials.revenue_growth is not None:
        parts.append(f"Revenue growth: {financials.revenue_growth * 100:.1f}%")

    context = ", ".join(parts)

    llm = LLMClient()
    try:
        response = await llm.chat(
            system_prompt=PROMPT_FINANCIAL_INTERPRET,
            user_prompt=context,
            temperature=0.3,
        )
        state["interpretation"] = response
    except Exception as exc:
        logger.warning("LLM interpretation failed: %s", exc)
        state["interpretation"] = (
            "[LLM interpretation unavailable — API key not configured]"
        )

    return state


# ── Graph wiring ───────────────────────────────────────────────────────────

from langgraph.graph import END, StateGraph

builder = StateGraph(DealState)
builder.add_node("load_data", load_data)
builder.add_node("compute_ratios", compute_ratios)
builder.add_node("flag_risks", flag_risks)
builder.add_node("interpret", interpret)

builder.set_entry_point("load_data")
builder.add_edge("load_data", "compute_ratios")
builder.add_edge("compute_ratios", "flag_risks")
builder.add_edge("flag_risks", "interpret")
builder.add_edge("interpret", END)

financials_graph = builder.compile()


# ── Helper ─────────────────────────────────────────────────────────────────

async def run_financial_analysis(company_id: int) -> DealState:
    """Run the full financial analysis graph for a company."""
    async with async_session_factory() as session:
        result = await session.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()

    if not company:
        state = create_initial_state("Unknown", company_id=company_id)
        state["errors"] = [f"Company with id={company_id} not found"]
        return state

    state = create_initial_state(company.name, company_id=company_id)
    final_state = await financials_graph.ainvoke(state)
    return final_state  # type: ignore[return-value]
