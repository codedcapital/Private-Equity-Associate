"""Pydantic schemas for IC Memo resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from schemas.reasoning_trace import ReasoningTraceStep


class ICMemoCreate(BaseModel):
    """Schema for creating a new IC memo."""

    company_id: int
    deal_id: int | None = None
    sections: dict
    word_count: int | None = None
    confidence_score: float | None = None
    pdf_path: str | None = None


class ICMemoRead(BaseModel):
    """Schema for reading an IC memo (ORM-compatible)."""

    id: int
    company_id: int
    deal_id: int | None
    sections: dict
    word_count: int | None
    confidence_score: float | None
    pdf_path: str | None
    created_at: datetime
    reasoning_trace: list[ReasoningTraceStep] | None = None

    model_config = ConfigDict(from_attributes=True)



class ICMemoList(BaseModel):
    """Schema for paginated IC memo list responses."""

    memos: list[ICMemoRead]
    total: int
