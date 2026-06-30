"""Financials agent router — financial modeling and ratio analysis endpoints.

Endpoints:
    GET    /agents/financials/health     — Health check
    POST   /agents/financials            — Run financial analysis agent
    GET    /agents/financials/{company_id} — Retrieve latest financial profile
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from agents.financials import run_financial_analysis
from db.models import Financial
from db.session import async_session_factory
from schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatus
from schemas.financials import FinancialProfile

router = APIRouter(prefix="/agents/financials", tags=["financials"])


@router.get("/health")
async def health() -> dict:
    """Health check for the financials agent."""
    return {"status": "ok"}


@router.post("", response_model=AgentRunResponse)
async def run_financials_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Run the full financial analysis graph for a company.

    Executes synchronously because the graph is fast (DB queries + Python math +
    optional LLM call).  The returned ``run_id`` is the graph state ID so the
    caller can correlate logs later.
    """
    final_state = await run_financial_analysis(request.company_id)
    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    status = AgentStatus.FAILED if has_errors else AgentStatus.COMPLETE
    message = (
        "Financial analysis completed with errors"
        if has_errors
        else "Financial analysis completed successfully"
    )
    return AgentRunResponse(run_id=run_id, status=status, message=message)


@router.get("/{company_id}", response_model=FinancialProfile)
async def get_financial_profile(company_id: int) -> FinancialProfile:
    """Return the latest FinancialProfile for a company (from DB, not agent output)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = result.scalar_one_or_none()

    if not fin:
        raise HTTPException(
            status_code=404,
            detail=f"Financials not found for company_id={company_id}",
        )

    return FinancialProfile(
        revenue=fin.revenue,
        ebitda=fin.ebitda,
        ebitda_margin=fin.ebitda_margin,
        revenue_growth=fin.revenue_growth,
        net_debt=fin.net_debt,
        net_debt_ebitda=fin.net_debt_ebitda,
        fcf=fin.fcf,
        fcf_yield=fin.fcf_yield,
    )
