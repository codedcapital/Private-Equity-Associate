"""Pydantic schemas for Signal resources."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SignalBase(BaseModel):
    signal_type: str
    direction: str | None = None
    title: str
    description: str | None = None
    evidence_url: str | None = None
    evidence_text: str | None = None
    confidence: str = "MEDIUM"


class SignalCreate(SignalBase):
    deal_id: int
    metadata: dict | None = None


class SignalRead(SignalBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    deal_id: int
    company_name: str | None = None
    detected_at: str
    resolved_at: str | None = None
    is_dismissed: bool
    metadata: dict | None = None


class SignalList(BaseModel):
    signals: list[SignalRead]


class SignalDismiss(BaseModel):
    is_dismissed: bool = True
