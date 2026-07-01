"""LBO agent router — LBO model and returns analysis endpoints.

Endpoints:
    POST   /agents/lbo              — Run full LBO analysis for a company
    GET    /agents/lbo/{company_id} — Get latest LBO result for a company
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter

from agents.lbo.graph import run_lbo_analysis
from schemas.agent import AgentRunRequest
from schemas.lbo import LBOAgentResponse
from schemas.reasoning_trace import ReasoningTraceStep

router = APIRouter(prefix="/agents/lbo", tags=["lbo"])


def _build_lbo_trace(final_state: dict) -> list[ReasoningTraceStep]:
    """Build a synthetic reasoning trace from LBO final state."""
    ts = datetime.utcnow().isoformat() + "Z"
    trace: list[ReasoningTraceStep] = []
    trace.append(ReasoningTraceStep(timestamp=ts, text="Loaded company financials (EBITDA and revenue) from database"))

    lbo_result = final_state.get("lbo_result")
    if lbo_result:
        entry_ev = getattr(lbo_result, "entry_equity", None) or lbo_result.get("entry_equity", 0)
        entry_debt = getattr(lbo_result, "entry_debt", None) or lbo_result.get("entry_debt", 0)
        total_ev = entry_ev + entry_debt
        if total_ev > 0:
            trace.append(ReasoningTraceStep(timestamp=ts, text=f"Computed entry EV = ${total_ev:,.0f} (equity ${entry_ev:,.0f} + debt ${entry_debt:,.0f})"))
        debt_pct = total_ev > 0 and (entry_debt / total_ev) or 0
        trace.append(ReasoningTraceStep(timestamp=ts, text=f"Debt financing = {debt_pct:.0%} of entry EV"))

    lbo_results = final_state.get("lbo_results")
    if lbo_results:
        for name, result in lbo_results.items():
            irr = getattr(result, "irr", None) or result.get("irr")
            moic = getattr(result, "moic", None) or result.get("moic")
            if irr is not None and moic is not None:
                trace.append(ReasoningTraceStep(timestamp=ts, text=f"{name} case: IRR = {irr:.1%}, MOIC = {moic:.2f}x"))

    sens = final_state.get("lbo_sensitivity")
    if sens:
        trace.append(ReasoningTraceStep(timestamp=ts, text="Generated IRR sensitivity grid across entry and exit multiples"))

    interp = final_state.get("lbo_interpretation")
    if interp:
        trace.append(ReasoningTraceStep(timestamp=ts, text="Generated associate interpretation from model outputs"))

    return trace


@router.get("/health")
async def health() -> dict:
    """Health check for the LBO agent."""
    return {"status": "ok"}


@router.post("", response_model=LBOAgentResponse)
async def run_lbo(request: AgentRunRequest) -> dict:
    """Run the full LBO analysis for a company.

    Accepts optional overrides for entry multiple, debt percentage,
    hold years, exit multiple, revenue growth, and margin expansion.
    """
    final_state = await run_lbo_analysis(
        company_id=request.company_id,
        overrides=request.overrides,
    )

    errors = final_state.get("errors", [])

    # Build response
    response: dict = {
        "lbo_result": {},
        "scenarios": {},
        "sensitivity_grid": final_state.get("lbo_sensitivity"),
        "interpretation": final_state.get("lbo_interpretation"),
        "errors": errors,
    }

    lbo_result = final_state.get("lbo_result")
    if lbo_result:
        response["lbo_result"] = dict(lbo_result)

    lbo_results = final_state.get("lbo_results")
    if lbo_results:
        for name, result in lbo_results.items():
            # Handle both dict (from graph) and dataclass (legacy)
            def _r(attr: str) -> Any:
                if isinstance(result, dict):
                    return result.get(attr)
                return getattr(result, attr, None)

            response["scenarios"][name] = {
                "entry_equity": _r("entry_equity"),
                "entry_debt": _r("entry_debt"),
                "irr": _r("irr"),
                "moic": _r("moic"),
                "exit_ev": _r("exit_ev"),
                "exit_equity": _r("exit_equity"),
                "debt_schedule": _r("debt_schedule"),
                "ebitda_projection": _r("ebitda_projection"),
            }

    trace = _build_lbo_trace(final_state)
    response["reasoning_trace"] = trace
    return response


@router.get("/{company_id}", response_model=LBOAgentResponse)
async def get_lbo(company_id: int) -> dict:
    """Get the latest LBO result for a company.

    Computes the analysis on the fly using the company's latest financials.
    """
    final_state = await run_lbo_analysis(company_id=company_id)

    response: dict = {
        "lbo_result": {},
        "scenarios": {},
        "sensitivity_grid": final_state.get("lbo_sensitivity"),
        "interpretation": final_state.get("lbo_interpretation"),
        "errors": final_state.get("errors", []),
    }

    lbo_result = final_state.get("lbo_result")
    if lbo_result:
        response["lbo_result"] = dict(lbo_result)

    lbo_results = final_state.get("lbo_results")
    if lbo_results:
        for name, result in lbo_results.items():
            # Handle both dict (from graph) and dataclass (legacy)
            def _r(attr: str) -> Any:
                if isinstance(result, dict):
                    return result.get(attr)
                return getattr(result, attr, None)

            response["scenarios"][name] = {
                "entry_equity": _r("entry_equity"),
                "entry_debt": _r("entry_debt"),
                "irr": _r("irr"),
                "moic": _r("moic"),
                "exit_ev": _r("exit_ev"),
                "exit_equity": _r("exit_equity"),
                "debt_schedule": _r("debt_schedule"),
                "ebitda_projection": _r("ebitda_projection"),
            }

    trace = _build_lbo_trace(final_state)
    response["reasoning_trace"] = trace
    return response
