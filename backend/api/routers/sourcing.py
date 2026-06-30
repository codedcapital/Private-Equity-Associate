"""Sourcing agent router — company discovery and deal origination endpoints.

Endpoints:
    GET    /agents/sourcing/health     — Health check
    POST   /agents/sourcing            — Run sourcing agent for a thesis
"""

from fastapi import APIRouter
from pydantic import BaseModel

from agents.sourcing import run_sourcing

router = APIRouter(prefix="/agents/sourcing", tags=["sourcing"])


class SourcingAgentRequest(BaseModel):
    """Request schema for the sourcing agent.

    Accepts either a direct ``thesis`` string or an ``overrides`` dict
    containing a ``thesis`` key (compatible with ``AgentRunRequest``).
    """

    thesis: str | None = None
    company_id: int | None = None
    overrides: dict | None = None


class SourcingAgentResponse(BaseModel):
    """Response schema for the sourcing agent."""

    run_id: str
    status: str
    message: str
    candidates: list[dict]


@router.get("/health")
async def health() -> dict:
    """Health check for the sourcing agent."""
    return {"status": "ok"}


@router.post("", response_model=SourcingAgentResponse)
async def run_sourcing_agent(request: SourcingAgentRequest) -> SourcingAgentResponse:
    """Run the sourcing agent for an investment thesis.

    Extracts structured filters from the thesis, screens the database,
    optionally enriches via web search, and returns scored candidates.
    """
    thesis = request.thesis or ""
    if not thesis and request.overrides:
        thesis = request.overrides.get("thesis", "")

    if not thesis:
        return SourcingAgentResponse(
            run_id="",
            status="failed",
            message="Missing thesis in request",
            candidates=[],
        )

    final_state = await run_sourcing(thesis=thesis)

    run_id = final_state.get("run_id", "")
    has_errors = bool(final_state.get("errors"))
    ranked = final_state.get("ranked_candidates", [])

    status = "failed" if has_errors else "complete"
    message = (
        f"Failed: {final_state['errors'][0]}"
        if has_errors
        else f"Found {len(ranked)} candidates"
    )

    return SourcingAgentResponse(
        run_id=run_id,
        status=status,
        message=message,
        candidates=ranked,
    )
