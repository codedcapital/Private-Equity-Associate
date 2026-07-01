from pydantic import BaseModel, Field
from typing import Any

class EvidenceStatusUpdate(BaseModel):
    status: str
    conflict_description: str | None = None

class EvidenceConflictCreate(BaseModel):
    evidence_b_id: int
    conflict_description: str

class InvestmentViewDiffQuery(BaseModel):
    from_version_id: int
    to_version_id: int

class DealSettingsUpdate(BaseModel):
    confidence_weights: dict[str, Any] | None = None

class DealSettingsRead(BaseModel):
    deal_id: int
    confidence_weights: dict[str, Any]
    updated_at: str
