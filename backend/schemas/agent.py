"""Pydantic schemas for Agent resources."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AgentStatus(str, Enum):
    """Execution status of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRunRequest(BaseModel):
    """Schema for requesting a new agent run."""

    company_id: int | None = None
    thesis: str | None = None
    overrides: dict = {}


class AgentRunResponse(BaseModel):
    """Schema for agent run initiation response."""

    run_id: str
    status: AgentStatus
    message: str


class PipelineRunRequest(BaseModel):
    """Schema for requesting a full pipeline run."""

    company_name_or_id: str | int
    thesis: str | None = None


class BulkIngestRequest(BaseModel):
    """Schema for bulk ingestion of new tickers."""

    tickers: list[str]
    sources: list[str] = ["financials"]  # e.g., ["financials", "sec"] or ["all"]


class BulkIngestResponse(BaseModel):
    """Schema for bulk ingestion response."""

    total: int
    created: int
    existing: int
    failed: int
    results: dict[str, dict]


class AgentLogRead(BaseModel):
    """Schema for reading an agent log entry (ORM-compatible)."""

    id: int
    run_id: str
    agent_name: str
    status: AgentStatus
    input_data: dict | None
    output_data: dict | None
    errors: list[str] | None
    duration_ms: int | None
    tokens_used: int | None
    cost_usd: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentLogList(BaseModel):
    """Schema for paginated agent log list responses."""

    logs: list[AgentLogRead]
    total: int


class PipelineRunRead(BaseModel):
    """Schema for a single pipeline run (aggregated from agent logs)."""

    run_id: str
    company_name: str | None
    status: str
    duration: int | None
    cost_usd: float | None


class PipelineRunList(BaseModel):
    """Schema for the list of pipeline runs."""

    runs: list[PipelineRunRead]


class PipelineStatusRead(BaseModel):
    """Schema for daily pipeline status summary."""

    active_runs: int
    completed_today: int
    failed_today: int
    total_cost_today: float
    total_tokens_today: int
