"""Research agent router — industry research and analysis endpoints.

Endpoints:
    GET    /agents/research/health     — Health check
    POST   /agents/research            — Run industry research agent
"""

from fastapi import APIRouter

from agents.research import run_research
from agents.state import deal_state_from_json
from db.session import async_session_factory
from schemas.agent import AgentRunRequest
from schemas.research import ResearchAgentResponse

router = APIRouter(prefix="/agents/research", tags=["research"])


@router.get("/health")
async def health() -> dict:
    """Health check for the research agent."""
    return {"status": "ok"}


@router.get("/{company_id}")
async def get_research_for_company(company_id: int) -> ResearchAgentResponse:
    """Get the latest research for a specific company.

    Checks (1) dedicated research agent log, (2) full pipeline checkpoint.
    Falls back to re-running the research graph if no cached data exists.
    """
    from sqlalchemy import desc, select
    from db.models import AgentLog

    async with async_session_factory() as session:
        # 1. Check for dedicated research agent log
        result = await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == "IndustryResearchAgent")
            .where(AgentLog.input_data["company_id"].as_string() == str(company_id))
            .order_by(desc(AgentLog.created_at))
            .limit(1)
        )
        log = result.scalar_one_or_none()

        if log and log.output_data and log.output_data.get("research"):
            return ResearchAgentResponse(
                run_id=log.run_id,
                status="complete",
                message="Research loaded from cache",
                research=log.output_data["research"],
                errors=log.errors,
            )

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
                research = state.get("research")
                if research is not None:
                    return ResearchAgentResponse(
                        run_id=log.run_id,
                        status="complete",
                        message="Research loaded from pipeline checkpoint",
                        research=research,
                        errors=state.get("errors"),
                    )
            except Exception:
                pass  # malformed state_json, fall through to re-run

    # No cache — run fresh
    final_state = await run_research(company_id)
    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    status = "failed" if has_errors else "complete"
    message = (
        "Industry research completed with errors"
        if has_errors
        else "Industry research completed successfully"
    )

    return ResearchAgentResponse(
        run_id=run_id,
        status=status,
        message=message,
        research=final_state.get("research"),
        errors=final_state.get("errors"),
    )


@router.post("", response_model=ResearchAgentResponse)
async def run_research_agent(request: AgentRunRequest) -> ResearchAgentResponse:
    """Run the full industry research graph for a company.

    Executes the classify → retrieve → web → synthesize pipeline
    synchronously and returns the resulting IndustryProfile.
    """
    final_state = await run_research(request.company_id)

    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    status = "failed" if has_errors else "complete"
    message = (
        "Industry research completed with errors"
        if has_errors
        else "Industry research completed successfully"
    )

    research = final_state.get("research")

    return ResearchAgentResponse(
        run_id=run_id,
        status=status,
        message=message,
        research=research,
        errors=final_state.get("errors"),
    )

