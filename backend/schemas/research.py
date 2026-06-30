"""Pydantic schemas for research agent resources."""

from pydantic import BaseModel


class ResearchAgentResponse(BaseModel):
    """Response schema for the research agent endpoint."""

    run_id: str
    status: str
    message: str
    research: dict | None = None
    errors: list[str] | None = None
