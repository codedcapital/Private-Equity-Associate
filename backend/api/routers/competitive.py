"""Competitive agent router — competitor mapping and market intelligence endpoints.

Endpoints:
    GET    /agents/competitive/health     — Health check
    POST   /agents/competitive            — Run competitive analysis agent
"""

from fastapi import APIRouter

from agents.competitive import run_competitive
from agents.state import deal_state_from_json
from db.session import async_session_factory
from schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatus

router = APIRouter(prefix="/agents/competitive", tags=["competitive"])


@router.get("/health")
async def health() -> dict:
    """Health check for the competitive agent."""
    return {"status": "ok"}


@router.get("/{company_id}")
async def get_competitive_for_company(company_id: int) -> dict:
    """Get the latest competitive analysis for a specific company.

    Checks (1) dedicated competitive agent log, (2) full pipeline checkpoint.
    Falls back to re-running the competitive graph if no cached data exists.
    """
    from sqlalchemy import desc, select
    from db.models import AgentLog

    async with async_session_factory() as session:
        # 1. Check for dedicated competitive agent log
        result = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "CompetitiveMappingAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        log = result.scalar_one_or_none()

        if log and log.output_data and log.output_data.get("competitive_map"):
            return {
                "run_id": log.run_id,
                "status": "complete",
                "message": "Competitive analysis loaded from cache",
                "competitive_map": log.output_data["competitive_map"],
                "errors": log.errors,
            }

        # 2. Check full pipeline checkpoint
        result = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "full_pipeline")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        log = result.scalar_one_or_none()

        if log and log.output_data and log.output_data.get("state_json"):
            try:
                state = deal_state_from_json(log.output_data["state_json"])
                competitive_map = state.get("competitive_map")
                if competitive_map is not None:
                    return {
                        "run_id": log.run_id,
                        "status": "complete",
                        "message": "Competitive analysis loaded from pipeline checkpoint",
                        "competitive_map": competitive_map,
                        "errors": state.get("errors"),
                    }
            except Exception:
                pass  # malformed state_json, fall through to re-run

    # No cache — run fresh
    final_state = await run_competitive(company_id)
    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    status = "failed" if has_errors else "complete"
    message = (
        "Competitive analysis completed with errors"
        if has_errors
        else "Competitive analysis completed successfully"
    )

    return {
        "run_id": run_id,
        "status": status,
        "message": message,
        "competitive_map": final_state.get("competitive_map"),
        "errors": final_state.get("errors"),
    }


@router.post("", response_model=AgentRunResponse)
async def run_competitive_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Run the full competitive analysis graph for a company.

    Executes synchronously. Returns a run_id and status. The caller can
    inspect the full competitive map via the agent log or future GET endpoints.
    """
    final_state = await run_competitive(request.company_id)
    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    status = AgentStatus.FAILED if has_errors else AgentStatus.COMPLETE
    message = (
        "Competitive analysis completed with errors"
        if has_errors
        else "Competitive analysis completed successfully"
    )
    return AgentRunResponse(run_id=run_id, status=status, message=message)

