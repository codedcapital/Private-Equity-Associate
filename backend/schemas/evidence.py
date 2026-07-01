"""Pydantic schemas for structured evidence modules.

Phase 3: Intelligence modules produce EvidenceMetric objects instead of flat text.
The Decision Engine consumes EvidenceModules and produces Investment Scores.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceMetric(BaseModel):
    """A single metric finding from an intelligence module.
    
    Every module outputs metrics with this exact shape. The Decision Engine
    scores them and the frontend renders them as question cards.
    """

    name: str = Field(..., description="Metric name, e.g. 'Revenue CAGR', 'Switching Costs'")
    value: str | float | None = Field(None, description="The metric value, e.g. '14.2%' or 0.142")
    direction: str | None = Field(None, description="'improving', 'declining', 'stable', 'elevated'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0.0-1.0 confidence in this metric")
    is_supporting: bool = Field(False, description="Does this metric support the investment thesis?")
    is_contradictory: bool = Field(False, description="Does this metric contradict the thesis?")
    evidence_text: str = Field(..., description="The raw evidence supporting this metric")
    source: str = Field(..., description="Human-readable source name, e.g. 'Yahoo Finance', 'SEC 10-K'")
    source_type: str = Field(..., description="Category: 'filing', 'api', 'web', 'expert_call', 'internal'")
    source_url: str | None = Field(None, description="Link to the raw source if available")
    source_metadata: dict | None = Field(None, description="Additional context: chunk_id, filing_id, ticker, etc.")


class EvidenceModule(BaseModel):
    """Structured output from a single intelligence module.
    
    Every module — Financial, Research, Competitive, Market, Valuation —
    produces exactly this shape. The Decision Engine consumes a list of
    EvidenceModules and computes the Investment Score.
    """

    module_type: str = Field(..., description="'financial', 'research', 'competitive', 'market', 'valuation'")
    company_id: int
    metrics: list[EvidenceMetric] = Field(default_factory=list)
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    key_insights: list[str] = Field(default_factory=list, description="Top 3-5 takeaways")
    warnings: list[str] = Field(default_factory=list, description="Red flags from this module")
    sources: list[str] = Field(default_factory=list, description="All external sources used")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class ModuleScore(BaseModel):
    """A single module's contribution to the Investment Score."""

    module_type: str
    score: int = Field(..., ge=0, le=100, description="0-100 score for this module")
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_count: int
    contradictory_count: int
    warning_count: int


class DecisionOutput(BaseModel):
    """The final investment decision synthesized from all evidence modules.
    
    This is what the investor actually sees. Every number is traceable
    to a specific EvidenceMetric with a source and confidence score.
    """

    investment_score: int = Field(..., ge=0, le=100, description="Overall 0-100 score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Weighted confidence across all evidence")
    recommendation: str = Field(..., description="'PROCEED', 'CONDITIONAL', 'PASS'")
    conviction: str = Field(..., description="'STRONG', 'MODERATE', 'WEAK'")

    # Sub-scores (each 0-100)
    thesis_score: int = Field(0, ge=0, le=100)
    financial_score: int = Field(0, ge=0, le=100)
    competitive_score: int = Field(0, ge=0, le=100)
    market_score: int = Field(0, ge=0, le=100)
    valuation_score: int = Field(0, ge=0, le=100)
    risk_score: int = Field(0, ge=0, le=100, description="Lower is better; measures downside risk")

    # Evidence counts
    supporting_metrics: int
    contradictory_metrics: int
    open_questions: int
    total_metrics: int

    # Module breakdown
    module_scores: list[ModuleScore] = Field(default_factory=list)

    # Key findings
    top_strengths: list[str] = Field(default_factory=list, max_length=5)
    top_concerns: list[str] = Field(default_factory=list, max_length=5)
    critical_gaps: list[str] = Field(default_factory=list, description="Must be resolved before IC")

    # LLM synthesis
    executive_summary: str | None = Field(None, description="One-paragraph investment recommendation with citations")

    # Sources
    evidence_modules: list[str] = Field(default_factory=list, description="Which modules contributed")
    data_sources: list[str] = Field(default_factory=list, description="External data sources used")

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class DecisionRequest(BaseModel):
    """Request to run the Decision Engine for a company."""

    company_id: int
    force_refresh: bool = False
    include_llm_synthesis: bool = True


class DecisionRefreshResponse(BaseModel):
    """Response after triggering a decision refresh."""

    decision: DecisionOutput
    modules_run: list[str]
    duration_ms: int | None = None
