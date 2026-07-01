"""Pydantic schemas for Intelligence Hub resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItemSchema(BaseModel):
    """A single piece of evidence linked to a question."""

    id: int
    text: str
    source: str
    source_type: str  # filing, web, expert_call, internal, api
    source_url: str | None = None
    source_metadata: dict | None = None
    is_supporting: bool = False
    is_contradictory: bool = False
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemCreate(BaseModel):
    """Schema for creating new evidence."""

    text: str
    source: str
    source_type: str
    source_url: str | None = None
    source_metadata: dict | None = None
    is_supporting: bool = False
    is_contradictory: bool = False
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class EvidenceItemUpdate(BaseModel):
    """Schema for updating evidence."""

    text: str | None = None
    source: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_metadata: dict | None = None
    is_supporting: bool | None = None
    is_contradictory: bool | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class IntelligenceQuestionSchema(BaseModel):
    """A question-answer node in the intelligence hub."""

    id: int
    category: str  # executive_briefing, supporting_evidence, contradictory_evidence, expert_consensus, comparable_companies, remaining_diligence
    question: str
    answer: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    sort_order: int = 0
    evidence: list[EvidenceItemSchema] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntelligenceQuestionCreate(BaseModel):
    """Schema for creating a new question."""

    category: str
    question: str
    answer: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    sort_order: int = 0


class IntelligenceQuestionUpdate(BaseModel):
    """Schema for updating a question."""

    category: str | None = None
    question: str | None = None
    answer: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    sort_order: int | None = None


class SourceConfidenceSchema(BaseModel):
    """Source reliability tracking."""

    id: int
    source_name: str
    source_type: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceConfidenceCreate(BaseModel):
    """Schema for creating source confidence."""

    source_name: str
    source_type: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class SourceConfidenceUpdate(BaseModel):
    """Schema for updating source confidence."""

    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    rationale: str | None = None


class ComparableCompanySchema(BaseModel):
    """Simplified comparable company for the hub."""

    name: str
    ticker: str | None = None
    tag: str = "Peer"
    revenue: str | None = None
    ebitda: str | None = None
    ebitda_margin: str | None = None
    ev_ebitda: str | None = None
    revenue_growth: str | None = None
    market_cap: str | None = None
    ownership: str | None = None
    source: str = "Internal"


class IntelligenceHubResponse(BaseModel):
    """Full Intelligence Hub response."""

    hub_id: int
    company_id: int
    deal_id: int | None = None
    status: str  # draft, generated, reviewed
    executive_briefing: str | None = None
    questions: list[IntelligenceQuestionSchema] = []
    source_confidence: list[SourceConfidenceSchema] = []
    comparable_companies: list[ComparableCompanySchema] = []
    remaining_diligence: list[str] = []
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntelligenceHubGenerateRequest(BaseModel):
    """Request to generate/populate the hub from agent outputs."""

    company_id: int
    include_market_data: bool = False
    include_analyst_consensus: bool = False


class HubStatusUpdate(BaseModel):
    """Update hub status."""

    status: str  # draft, generated, reviewed
    executive_briefing: str | None = None


class DiligenceQuestionSchema(BaseModel):
    """An open diligence question."""

    id: int
    question: str
    category: str  # financial, legal, commercial, operational
    owner: str | None = None
    status: str = "open"  # open, in_progress, resolved, blocked
    priority: str = "medium"  # high, medium, low
    due_date: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiligenceQuestionCreate(BaseModel):
    """Create an open diligence question."""

    question: str
    category: str
    owner: str | None = None
    priority: str = "medium"
    due_date: str | None = None


class DiligenceQuestionUpdate(BaseModel):
    """Update an open diligence question."""

    status: str | None = None
    owner: str | None = None
    priority: str | None = None
    due_date: str | None = None


class IntelligenceHubListResponse(BaseModel):
    """Paginated list of intelligence hubs."""

    hubs: list[IntelligenceHubResponse]
    total: int
