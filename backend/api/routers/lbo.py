"""LBO agent router — LBO model and returns analysis endpoints.

Endpoints:
    POST   /agents/lbo              — Run full LBO analysis for a company
    GET    /agents/lbo/{company_id} — Get latest LBO result for a company
"""

from fastapi import APIRouter

from agents.lbo.graph import run_lbo_analysis
from schemas.agent import AgentRunRequest
from schemas.lbo import LBOAgentResponse

router = APIRouter(prefix="/agents/lbo", tags=["lbo"])


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
            response["scenarios"][name] = {
                "entry_equity": result.entry_equity,
                "entry_debt": result.entry_debt,
                "irr": result.irr,
                "moic": result.moic,
                "exit_ev": result.exit_ev,
                "exit_equity": result.exit_equity,
                "debt_schedule": result.debt_schedule,
                "ebitda_projection": result.ebitda_projection,
            }

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
            response["scenarios"][name] = {
                "entry_equity": result.entry_equity,
                "entry_debt": result.entry_debt,
                "irr": result.irr,
                "moic": result.moic,
                "exit_ev": result.exit_ev,
                "exit_equity": result.exit_equity,
                "debt_schedule": result.debt_schedule,
                "ebitda_projection": result.ebitda_projection,
            }

    return response
