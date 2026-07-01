"""Pydantic schemas for research agent resources."""

from pydantic import BaseModel

from schemas.reasoning_trace import ReasoningTraceStep


class ResearchAgentResponse(BaseModel):
    """Response schema for the research agent endpoint."""

    run_id: str
    status: str
    message: str
    research: dict | None = None
    errors: list[str] | None = None
    reasoning_trace: list[ReasoningTraceStep] | None = None

