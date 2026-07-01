"""LangGraph LBO analysis pipeline.

Four-node async graph:
  prepare_inputs → run_model → generate_sensitivity → interpret → END
"""

from __future__ import annotations

import dataclasses
import logging

from langgraph.graph import END, StateGraph
from sqlalchemy import select

from agents.state import DealState, LBOResult as StateLBOResult, create_initial_state
from core.config import settings
from core.lbo_engine import LBOInputs, run_lbo, sensitivity_grid
from core.llm import LLMClient
from core.prompts import PROMPT_LBO_INTERPRET
from db.models import Company, Financial
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)


# ── Scenario builders ───────────────────────────────────────────────────────────


def _build_scenario_inputs(
    entry_ebitda: float,
    entry_multiple: float,
    overrides: dict,
    scenario_defaults: dict,
) -> LBOInputs:
    debt_pct = overrides.get("debt_pct", scenario_defaults.get("debt_pct", 0.60))
    exit_multiple = overrides.get("exit_multiple", scenario_defaults.get("exit_multiple", 12.0))
    hold_years = overrides.get("hold_years", scenario_defaults.get("hold_years", 5))
    revenue_growth = overrides.get(
        "revenue_growth",
        scenario_defaults.get("revenue_growth", [0.10] * hold_years),
    )
    margin_expansion = overrides.get(
        "margin_expansion",
        scenario_defaults.get("margin_expansion", 0.005),
    )

    # Ensure revenue_growth length matches hold_years
    if len(revenue_growth) != hold_years:
        revenue_growth = [revenue_growth[0] if revenue_growth else 0.10] * hold_years

    entry_ev = entry_ebitda * entry_multiple

    return LBOInputs(
        entry_ev=entry_ev,
        entry_ebitda=entry_ebitda,
        debt_pct=debt_pct,
        revenue_growth=revenue_growth,
        margin_expansion=margin_expansion,
        exit_multiple=exit_multiple,
        hold_years=hold_years,
    )


# ── Node 1: prepare_inputs ──────────────────────────────────────────────────


async def prepare_inputs(state: DealState) -> DealState:
    financials = state.get("financials")
    if not financials:
        # Try to fetch from DB if company_id is present
        company_id = state.get("company_id")
        if company_id:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Financial)
                    .where(Financial.company_id == company_id)
                    .order_by(Financial.report_date.desc())
                    .limit(1)
                )
                fin = result.scalar_one_or_none()
                if fin:
                    financials = FinancialProfile(
                        revenue=fin.revenue,
                        ebitda=fin.ebitda,
                        ebitda_margin=fin.ebitda_margin,
                        revenue_growth=fin.revenue_growth,
                        net_debt=fin.net_debt,
                        net_debt_ebitda=fin.net_debt_ebitda,
                        fcf=fin.fcf,
                        fcf_yield=fin.fcf_yield,
                    )
                    state["financials"] = financials

        if not financials:
            state["errors"] = state.get("errors", []) + [
                "No financials available for LBO analysis"
            ]
            return state

    entry_ebitda = financials.ebitda
    if entry_ebitda is None or entry_ebitda <= 0:
        state["errors"] = state.get("errors", []) + [
            "EBITDA is missing or invalid for LBO analysis"
        ]
        return state

    overrides = state.get("overrides") or {}

    entry_multiple = overrides.get("entry_multiple", 12.0)
    entry_ev = entry_ebitda * entry_multiple

    # Scenario defaults
    base_defaults = {
        "debt_pct": 0.60,
        "exit_multiple": 12.0,
        "hold_years": 5,
        "revenue_growth": [0.10] * 5,
        "margin_expansion": 0.005,
    }
    bull_defaults = {
        "debt_pct": 0.65,
        "exit_multiple": 14.0,
        "hold_years": 5,
        "revenue_growth": [0.15] * 5,
        "margin_expansion": 0.010,
    }
    bear_defaults = {
        "debt_pct": 0.55,
        "exit_multiple": 10.0,
        "hold_years": 5,
        "revenue_growth": [0.05] * 5,
        "margin_expansion": 0.000,
    }

    # Apply overrides to each scenario
    base_inputs = _build_scenario_inputs(entry_ebitda, entry_multiple, overrides, base_defaults)
    bull_inputs = _build_scenario_inputs(entry_ebitda, entry_multiple, overrides, bull_defaults)
    bear_inputs = _build_scenario_inputs(entry_ebitda, entry_multiple, overrides, bear_defaults)

    state["lbo_scenarios"] = {
        "base": dataclasses.asdict(base_inputs),
        "bull": dataclasses.asdict(bull_inputs),
        "bear": dataclasses.asdict(bear_inputs),
    }

    return state


# ── Node 2: run_model ─────────────────────────────────────────────────────────


async def run_model(state: DealState) -> DealState:
    scenarios = state.get("lbo_scenarios")
    if not scenarios:
        state["errors"] = state.get("errors", []) + ["No LBO scenarios prepared"]
        return state

    lbo_results: dict[str, dict] = {}

    for name, inputs_data in scenarios.items():
        # Reconstruct LBOInputs if it's a dict (from resumed state)
        if isinstance(inputs_data, dict):
            inputs = LBOInputs(**inputs_data)
        else:
            inputs = inputs_data
        try:
            result = run_lbo(inputs)
            lbo_results[name] = dataclasses.asdict(result)
        except Exception as exc:
            state["errors"] = state.get("errors", []) + [
                f"LBO run failed for {name}: {exc}"
            ]
            continue

    state["lbo_results"] = lbo_results

    # Set base as the main lbo_result
    base_result = lbo_results.get("base")
    if base_result:
        from agents.state import LBOResult as StateLBOResult

        state["lbo_result"] = StateLBOResult(
            entry_equity=base_result.get("entry_equity"),
            entry_debt=base_result.get("entry_debt"),
            irr=base_result.get("irr"),
            moic=base_result.get("moic"),
            exit_ev=base_result.get("exit_ev"),
            exit_equity=base_result.get("exit_equity"),
        )

    return state


# ── Node 3: generate_sensitivity ──────────────────────────────────────────────


async def generate_sensitivity(state: DealState) -> DealState:
    scenarios = state.get("lbo_scenarios")
    if not scenarios or "base" not in scenarios:
        state["errors"] = state.get("errors", []) + [
            "No base scenario for sensitivity"
        ]
        return state

    base_inputs = scenarios["base"]
    if isinstance(base_inputs, dict):
        base_inputs = LBOInputs(**base_inputs)

    try:
        grid = sensitivity_grid(
            base_inputs=base_inputs,
            entry_range=(8.0, 16.0, 1.0),
            exit_range=(8.0, 16.0, 1.0),
        )
        state["lbo_sensitivity"] = grid
    except Exception as exc:
        state["errors"] = state.get("errors", []) + [
            f"Sensitivity grid failed: {exc}"
        ]

    return state


# ── Node 4: interpret ─────────────────────────────────────────────────────────


async def interpret(state: DealState) -> DealState:
    lbo_results = state.get("lbo_results")
    sensitivity = state.get("lbo_sensitivity")

    if not lbo_results:
        state["errors"] = state.get("errors", []) + [
            "No LBO results to interpret"
        ]
        return state

    base = lbo_results.get("base")
    bull = lbo_results.get("bull")
    bear = lbo_results.get("bear")

    # Normalise dict / dataclass access
    def _get(attr: str, obj: Any) -> Any:
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)

    if not base:
        state["errors"] = state.get("errors", []) + [
            "No base LBO result to interpret"
        ]
        return state

    parts = []
    parts.append(
        f"Base scenario: Entry equity ${_get('entry_equity', base)/1e6:.1f}M, "
        f"Exit equity ${_get('exit_equity', base)/1e6:.1f}M, IRR {_get('irr', base):.1%}, MOIC {_get('moic', base):.2f}x"
    )

    if bull:
        parts.append(f"Bull scenario: IRR {_get('irr', bull):.1%}, MOIC {_get('moic', bull):.2f}x")
    if bear:
        parts.append(f"Bear scenario: IRR {_get('irr', bear):.1%}, MOIC {_get('moic', bear):.2f}x")

    if sensitivity:
        grid = sensitivity["grid"]
        flat_irrs = [irr for row in grid for irr in row]
        if flat_irrs:
            parts.append(
                f"Sensitivity grid: Best IRR {max(flat_irrs):.1%}, "
                f"Worst IRR {min(flat_irrs):.1%}"
            )

    context = "\n".join(parts)

    llm = LLMClient()
    try:
        response = await llm.chat(
            system_prompt=PROMPT_LBO_INTERPRET,
            user_prompt=context,
            temperature=0.3,
        )
        state["lbo_interpretation"] = response
    except Exception as exc:
        logger.warning("LLM interpretation failed: %s", exc)
        state["lbo_interpretation"] = (
            "[LLM interpretation unavailable — API key not configured]"
        )

    return state


async def produce_lbo_evidence(state: DealState) -> DealState:
    """Node 5: Produce structured EvidenceModule for the Decision Engine."""
    from schemas.evidence import EvidenceMetric, EvidenceModule

    lbo_results = state.get("lbo_results")
    metrics: list[EvidenceMetric] = []
    warnings: list[str] = []
    insights: list[str] = []
    sources: list[str] = ["LBO Agent"]

    if not lbo_results or not isinstance(lbo_results, dict):
        warnings.append("No LBO results available for evidence production")
        module = EvidenceModule(
            module_type="valuation",
            company_id=state.get("company_id", 0),
            metrics=metrics,
            overall_confidence=0.0,
            key_insights=insights,
            warnings=warnings,
            sources=sources,
        )
        state["lbo_evidence_module"] = module.model_dump(mode="json")
        return state

    for scenario_name in ["base", "bull", "bear"]:
        scenario = lbo_results.get(scenario_name)
        if not scenario or not isinstance(scenario, dict):
            continue
        irr = scenario.get("irr")
        moic = scenario.get("moic")
        if irr is not None:
            is_supporting = irr > 0.20 if isinstance(irr, (int, float)) else False
            metrics.append(EvidenceMetric(
                name=f"{scenario_name.capitalize()} IRR",
                value=round(irr, 4) if isinstance(irr, (int, float)) else str(irr),
                direction="positive" if is_supporting else "negative",
                confidence=0.75,
                is_supporting=is_supporting,
                is_contradictory=not is_supporting,
                evidence_text=f"{scenario_name.capitalize()} scenario IRR: {irr:.1%}" if isinstance(irr, (int, float)) else str(irr),
                source="LBO Agent",
                source_type="api",
            ))
        if moic is not None:
            is_supporting = moic > 2.0 if isinstance(moic, (int, float)) else False
            metrics.append(EvidenceMetric(
                name=f"{scenario_name.capitalize()} MOIC",
                value=round(moic, 2) if isinstance(moic, (int, float)) else str(moic),
                direction="positive" if is_supporting else "negative",
                confidence=0.75,
                is_supporting=is_supporting,
                is_contradictory=not is_supporting,
                evidence_text=f"{scenario_name.capitalize()} scenario MOIC: {moic:.2f}x" if isinstance(moic, (int, float)) else str(moic),
                source="LBO Agent",
                source_type="api",
            ))
        insights.append(f"{scenario_name.capitalize()}: IRR={irr:.1%}, MOIC={moic:.2f}x" if isinstance(irr, (int, float)) and isinstance(moic, (int, float)) else f"{scenario_name.capitalize()} scenario available")

    # Entry multiple check
    entry_multiple = None
    scenarios = state.get("lbo_scenarios", {})
    if isinstance(scenarios, dict):
        base = scenarios.get("base", {})
        if isinstance(base, dict):
            entry_multiple = base.get("entry_multiple")
    if entry_multiple is not None:
        is_supporting = entry_multiple < 12.0 if isinstance(entry_multiple, (int, float)) else False
        metrics.append(EvidenceMetric(
            name="Entry Multiple",
            value=round(entry_multiple, 1) if isinstance(entry_multiple, (int, float)) else str(entry_multiple),
            direction="positive" if is_supporting else "negative",
            confidence=0.70,
            is_supporting=is_supporting,
            is_contradictory=not is_supporting,
            evidence_text=f"Entry multiple: {entry_multiple:.1f}x" if isinstance(entry_multiple, (int, float)) else str(entry_multiple),
            source="LBO Agent",
            source_type="api",
        ))

    avg_confidence = sum(m.confidence for m in metrics) / len(metrics) if metrics else 0.0

    module = EvidenceModule(
        module_type="valuation",
        company_id=state.get("company_id", 0),
        metrics=metrics,
        overall_confidence=round(avg_confidence, 2),
        key_insights=insights[:5],
        warnings=warnings[:5],
        sources=sources,
    )

    state["lbo_evidence_module"] = module.model_dump(mode="json")
    return state


# ── Graph wiring ───────────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("prepare_inputs", prepare_inputs)
builder.add_node("run_model", run_model)
builder.add_node("generate_sensitivity", generate_sensitivity)
builder.add_node("interpret", interpret)
builder.add_node("produce_lbo_evidence", produce_lbo_evidence)

builder.set_entry_point("prepare_inputs")
builder.add_edge("prepare_inputs", "run_model")
builder.add_edge("run_model", "generate_sensitivity")
builder.add_edge("generate_sensitivity", "interpret")
builder.add_edge("interpret", "produce_lbo_evidence")
builder.add_edge("produce_lbo_evidence", END)

lbo_graph = builder.compile()


# ── Helper ─────────────────────────────────────────────────────────────────────


async def run_lbo_analysis(company_id: int, overrides: dict | None = None) -> DealState:
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
    if overrides:
        state["overrides"] = overrides

    final_state = await lbo_graph.ainvoke(state)
    return final_state  # type: ignore[return-value]
