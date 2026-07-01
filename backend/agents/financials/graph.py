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
    """Node 1: Fetch financials from live data provider (cache-first)."""
    company_id = state.get("company_id")
    if not company_id:
        state["errors"] = state.get("errors", []) + ["Missing company_id in state"]
        return state

    from services.data_provider import DataProvider

    try:
        profile = await DataProvider.get_financials(company_id)
    except Exception as exc:
        state["errors"] = state.get("errors", []) + [
            f"Data provider failed for company_id={company_id}: {exc}"
        ]
        return state

    if profile.revenue is None and profile.ebitda is None:
        state["errors"] = state.get("errors", []) + [
            f"No financials available for company_id={company_id} (ticker may be missing or YFinance fetch failed)"
        ]
        return state

    state["financials"] = profile
    return state


async def compute_ratios(state: DealState) -> DealState:
    """Node 2: Compute derived ratios (pass-through — DataProvider already computes them)."""
    financials = state.get("financials")
    if not financials:
        state["errors"] = state.get("errors", []) + [
            "No financials available to compute ratios"
        ]
        return state

    # DataProvider returns FinancialProfile with all derived fields already
    # populated (ebitda_margin, net_debt_ebitda, revenue_growth, fcf_yield).
    state["financials"] = financials
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

    # ── Write to Intelligence Hub ───────────────────────────────────────
    try:
        from services.intelligence_hub_writer import HubWriter
        writer = HubWriter(company_id=state.get("company_id"))
        await writer.ensure_hub()
        financials = state.get("financials")
        risk_flags = state.get("risk_flags", [])
        if financials:
            fin_parts = []
            if financials.revenue is not None:
                fin_parts.append(f"Revenue: ${financials.revenue:,.0f}")
            if financials.ebitda is not None:
                fin_parts.append(f"EBITDA: ${financials.ebitda:,.0f}")
            if financials.ebitda_margin is not None:
                fin_parts.append(f"EBITDA Margin: {financials.ebitda_margin:.1%}")
            if financials.net_debt_ebitda is not None:
                fin_parts.append(f"Net Debt / EBITDA: {financials.net_debt_ebitda:.1f}x")
            if financials.fcf_yield is not None:
                fin_parts.append(f"FCF Yield: {financials.fcf_yield:.1%}")
            if financials.revenue_growth is not None:
                fin_parts.append(f"Revenue Growth: {financials.revenue_growth:.1%}")
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
                        source="Yahoo Finance",
                        source_type="api",
                        is_supporting=True,
                        confidence=0.85,
                    )
                await writer.set_source_confidence("Yahoo Finance", "api")
        # Risk flags → Remaining Diligence
        for flag in (risk_flags or [])[:3]:
            await writer.add_remaining_diligence(f"Validate: {flag}")
    except Exception as hub_exc:
        logger.warning("Failed to write financials to Intelligence Hub: %s", hub_exc)

    return state


async def produce_evidence_module(state: DealState) -> DealState:
    """Node 5: Produce structured EvidenceModule for the Decision Engine."""
    financials = state.get("financials")
    risk_flags = state.get("risk_flags", [])

    if not financials:
        state["errors"] = state.get("errors", []) + [
            "No financials available for evidence module"
        ]
        return state

    from schemas.evidence import EvidenceMetric, EvidenceModule

    metrics: list[EvidenceMetric] = []
    warnings: list[str] = []
    sources: list[str] = ["Yahoo Finance"]

    # Revenue CAGR
    if financials.revenue_growth is not None:
        growth_pct = financials.revenue_growth * 100
        direction = "improving" if growth_pct > 10 else "stable" if growth_pct > 0 else "declining"
        metrics.append(EvidenceMetric(
            name="Revenue CAGR",
            value=f"{growth_pct:.1f}%",
            direction=direction,
            confidence=0.90,
            is_supporting=growth_pct > 5,
            is_contradictory=growth_pct < 0,
            evidence_text=f"Revenue growth of {growth_pct:.1f}% indicates {'strong' if growth_pct > 10 else 'moderate' if growth_pct > 0 else 'negative'} top-line expansion.",
            source="Yahoo Finance",
            source_type="api",
        ))

    # EBITDA Margin
    if financials.ebitda_margin is not None:
        margin_pct = financials.ebitda_margin * 100
        direction = "improving" if margin_pct > 25 else "stable" if margin_pct > 15 else "declining"
        metrics.append(EvidenceMetric(
            name="EBITDA Margin",
            value=f"{margin_pct:.1f}%",
            direction=direction,
            confidence=0.90,
            is_supporting=margin_pct > 20,
            is_contradictory=margin_pct < 10,
            evidence_text=f"EBITDA margin of {margin_pct:.1f}% reflects {'strong' if margin_pct > 25 else 'reasonable' if margin_pct > 15 else 'weak'} profitability.",
            source="Yahoo Finance",
            source_type="api",
        ))

    # Cash Conversion
    if financials.fcf_yield is not None:
        fcf_pct = financials.fcf_yield * 100
        metrics.append(EvidenceMetric(
            name="Cash Conversion",
            value=f"{fcf_pct:.1f}%",
            direction="stable",
            confidence=0.85,
            is_supporting=fcf_pct > 50,
            is_contradictory=fcf_pct < 20,
            evidence_text=f"FCF conversion of {fcf_pct:.1f}% indicates {'strong' if fcf_pct > 50 else 'adequate' if fcf_pct > 20 else 'poor'} cash generation.",
            source="Yahoo Finance",
            source_type="api",
        ))

    # Leverage
    if financials.net_debt_ebitda is not None:
        leverage = financials.net_debt_ebitda
        metrics.append(EvidenceMetric(
            name="Leverage",
            value=f"{leverage:.1f}x",
            direction="stable" if leverage < 5 else "elevated",
            confidence=0.85,
            is_supporting=leverage < 4,
            is_contradictory=leverage > 5,
            evidence_text=f"Net Debt / EBITDA of {leverage:.1f}x is {'conservative' if leverage < 3 else 'manageable' if leverage < 5 else 'elevated'}.",
            source="Yahoo Finance",
            source_type="api",
        ))

    # ROIC (computed from available data)
    if financials.ebitda and financials.net_debt and financials.revenue:
        try:
            capital = financials.net_debt + (financials.revenue * 0.3)  # rough equity proxy
            roic = financials.ebitda / capital if capital > 0 else 0
            metrics.append(EvidenceMetric(
                name="ROIC",
                value=f"{roic * 100:.1f}%",
                direction="stable",
                confidence=0.70,
                is_supporting=roic > 0.15,
                is_contradictory=roic < 0.05,
                evidence_text=f"ROIC of {roic * 100:.1f}% indicates {'strong' if roic > 0.15 else 'adequate' if roic > 0.05 else 'weak'} capital returns.",
                source="Yahoo Finance",
                source_type="api",
            ))
        except Exception:
            pass

    # Forecast (placeholder — in Phase 4 this will be computed from historical trends)
    if financials.revenue_growth is not None and financials.revenue is not None:
        growth = financials.revenue_growth
        forecast_revenue = financials.revenue * (1 + growth) ** 3
        metrics.append(EvidenceMetric(
            name="Forecast Revenue (3yr)",
            value=f"${forecast_revenue:,.0f}",
            direction="improving" if growth > 0.05 else "stable",
            confidence=0.65,
            is_supporting=growth > 0.05,
            is_contradictory=growth < 0,
            evidence_text=f"3-year revenue forecast of ${forecast_revenue:,.0f} assumes {growth * 100:.1f}% CAGR.",
            source="Yahoo Finance",
            source_type="api",
        ))

    # Risk flags → warnings
    for flag in risk_flags or []:
        warnings.append(flag)

    # Overall confidence: average of metric confidences
    avg_confidence = sum(m.confidence for m in metrics) / len(metrics) if metrics else 0.0

    # Key insights
    insights: list[str] = []
    if financials.revenue_growth and financials.revenue_growth > 0.10:
        insights.append(f"Revenue growing at {financials.revenue_growth * 100:.1f}% with stable margins")
    if financials.ebitda_margin and financials.ebitda_margin > 0.20:
        insights.append(f"Strong EBITDA margin of {financials.ebitda_margin * 100:.1f}%")
    if financials.net_debt_ebitda and financials.net_debt_ebitda > 5:
        insights.append(f"Elevated leverage at {financials.net_debt_ebitda:.1f}x")
    if financials.fcf_yield and financials.fcf_yield > 0.50:
        insights.append(f"Healthy FCF conversion of {financials.fcf_yield * 100:.1f}%")

    module = EvidenceModule(
        module_type="financial",
        company_id=state.get("company_id", 0),
        metrics=metrics,
        overall_confidence=round(avg_confidence, 2),
        key_insights=insights[:5],
        warnings=warnings[:5],
        sources=sources,
    )

    state["financial_evidence_module"] = module.model_dump(mode="json")
    return state


# ── Graph wiring ───────────────────────────────────────────────────────────

from langgraph.graph import END, StateGraph

builder = StateGraph(DealState)
builder.add_node("load_data", load_data)
builder.add_node("compute_ratios", compute_ratios)
builder.add_node("flag_risks", flag_risks)
builder.add_node("interpret", interpret)
builder.add_node("produce_evidence_module", produce_evidence_module)

builder.set_entry_point("load_data")
builder.add_edge("load_data", "compute_ratios")
builder.add_edge("compute_ratios", "flag_risks")
builder.add_edge("flag_risks", "interpret")
builder.add_edge("interpret", "produce_evidence_module")
builder.add_edge("produce_evidence_module", END)

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
