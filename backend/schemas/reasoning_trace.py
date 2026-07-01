"""Pydantic schemas for reasoning trace resources."""

from pydantic import BaseModel


class ReasoningTraceStep(BaseModel):
    """A single step in an agent's reasoning trace."""

    timestamp: str
    text: str
