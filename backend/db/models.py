"""SQLAlchemy ORM models for the PE Investment Platform.

All tables use async-compatible SQLAlchemy 2.0 declarative style.
pgvector is used for embedding storage (1536-dim, OpenAI text-embedding-3-small).
"""

from datetime import datetime
from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all models."""

    pass


# ── Enums ───────────────────────────────────────────────────────────────────


class CompanySource(str, PyEnum):
    """Where the company record originated."""

    SEC = "sec"
    COMPANIES_HOUSE = "companies_house"
    MANUAL = "manual"


class DealStage(str, PyEnum):
    """Pipeline stage for a deal."""

    SOURCING = "sourcing"
    DILIGENCE = "diligence"
    IC_READY = "ic_ready"
    PASSED = "passed"
    REJECTED = "rejected"
    CLOSED = "closed"


class AgentStatus(str, PyEnum):
    """Execution status of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class EvidenceStatus(str, PyEnum):
    """Lifecycle status of an evidence item."""

    VERIFIED = "verified"
    NEEDS_VALIDATION = "needs_validation"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class InvestmentViewStatus(str, PyEnum):
    """Status of an investment view document."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINAL = "final"


class DiligenceStatus(str, PyEnum):
    """Status of a diligence item."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class DiligencePriority(str, PyEnum):
    """Priority of a diligence item."""

    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DealEventType(str, PyEnum):
    """Types of deal events for the activity log."""

    VIEW_UPDATED = "view_updated"
    EVIDENCE_REFRESHED = "evidence_refreshed"
    DILIGENCE_STATUS_CHANGED = "diligence_status_changed"
    CONFIDENCE_RECALCULATED = "confidence_recalculated"
    RECOMMENDATION_CHANGED = "recommendation_changed"
    STAGE_CHANGED = "stage_changed"


class ActorType(str, PyEnum):
    """Type of actor who triggered an event."""

    SYSTEM = "system"
    USER = "user"


class ResolutionStatus(str, PyEnum):
    """Resolution status for an evidence conflict."""

    OPEN = "open"
    RESOLVED = "resolved"
    OVERRIDDEN = "overridden"


# ── Models ───────────────────────────────────────────────────────────────────


class Company(Base):
    """A company in the investment universe."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[CompanySource] = mapped_column(
        Enum(CompanySource, name="company_source"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    financials: Mapped[list["Financial"]] = relationship(
        "Financial", back_populates="company", cascade="all, delete-orphan"
    )
    filings: Mapped[list["Filing"]] = relationship(
        "Filing", back_populates="company", cascade="all, delete-orphan"
    )
    deals: Mapped[list["Deal"]] = relationship(
        "Deal", back_populates="company", cascade="all, delete-orphan"
    )
    memos: Mapped[list["ICMemo"]] = relationship(
        "ICMemo", back_populates="company", cascade="all, delete-orphan"
    )
    competitors: Mapped[list["CompetitorCompany"]] = relationship(
        "CompetitorCompany", back_populates="company", cascade="all, delete-orphan"
    )
    intelligence_hubs: Mapped[list["IntelligenceHub"]] = relationship(
        "IntelligenceHub", back_populates="company", cascade="all, delete-orphan"
    )


class IntelligenceHub(Base):
    """Central intelligence hub instance per company/deal."""

    __tablename__ = "intelligence_hubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    executive_briefing: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="intelligence_hubs")
    questions: Mapped[list["IntelligenceQuestion"]] = relationship(
        "IntelligenceQuestion", back_populates="hub", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem", back_populates="hub", cascade="all, delete-orphan"
    )
    source_confidence: Mapped[list["SourceConfidence"]] = relationship(
        "SourceConfidence", back_populates="hub", cascade="all, delete-orphan"
    )


class IntelligenceQuestion(Base):
    """A question-answer node in the intelligence hub."""

    __tablename__ = "intelligence_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hub_id: Mapped[int] = mapped_column(
        ForeignKey("intelligence_hubs.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    hub: Mapped["IntelligenceHub"] = relationship("IntelligenceHub", back_populates="questions")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem", back_populates="question", cascade="all, delete-orphan"
    )


class EvidenceItem(Base):
    """A piece of evidence linked to a question."""

    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hub_id: Mapped[int] = mapped_column(
        ForeignKey("intelligence_hubs.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("intelligence_questions.id", ondelete="CASCADE"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_supporting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_contradictory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status"),
        nullable=False,
        default=EvidenceStatus.VERIFIED,
    )
    verified_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    hub: Mapped["IntelligenceHub"] = relationship("IntelligenceHub", back_populates="evidence")
    question: Mapped["IntelligenceQuestion | None"] = relationship(
        "IntelligenceQuestion", back_populates="evidence_items"
    )


class SourceConfidence(Base):
    """Track reliability of each source used in the hub."""

    __tablename__ = "source_confidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hub_id: Mapped[int] = mapped_column(
        ForeignKey("intelligence_hubs.id", ondelete="CASCADE"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    hub: Mapped["IntelligenceHub"] = relationship(
        "IntelligenceHub", back_populates="source_confidence"
    )

class Financial(Base):
    """Financial statement snapshot for a company at a given reporting date."""

    __tablename__ = "financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    report_date: Mapped[Date] = mapped_column(Date, nullable=False)

    # Raw fields (from data sources)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_cf: Mapped[float | None] = mapped_column(Float, nullable=True)
    capex: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Computed fields (derived at ingestion time)
    net_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcf: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_debt_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcf_yield: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="financials")

    __table_args__ = (
        UniqueConstraint(
            "company_id", "report_date", name="uq_financials_company_report_date"
        ),
    )


class Filing(Base):
    """SEC or other regulatory filing stored as plain text with embeddings."""

    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    filing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filing_date: Mapped[Date] = mapped_column(Date, nullable=False)
    accession_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="filings")
    chunks: Mapped[list["FilingChunk"]] = relationship(
        "FilingChunk", back_populates="filing", cascade="all, delete-orphan"
    )


class FilingChunk(Base):
    """Chunked text from a filing, each with its own embedding for semantic search."""

    __tablename__ = "filing_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(
        ForeignKey("filings.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    filing: Mapped["Filing"] = relationship("Filing", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "filing_id", "chunk_index", name="uq_filing_chunks_filing_index"
        ),
    )


class Deal(Base):
    """A deal in the investment pipeline."""

    __tablename__ = "deal_pipeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[DealStage] = mapped_column(
        Enum(DealStage, name="deal_stage"), nullable=False, default=DealStage.SOURCING
    )
    entry_ev: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    lbo_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    lbo_moic: Mapped[float | None] = mapped_column(Float, nullable=True)
    memo_id: Mapped[int | None] = mapped_column(
        ForeignKey("ic_memos.id", ondelete="SET NULL"), nullable=True
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="deals")
    memo: Mapped["ICMemo | None"] = relationship("ICMemo", back_populates="deal")


class ICMemo(Base):
    """Investment Committee memo generated by the AI pipeline."""

    __tablename__ = "ic_memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    # deal_id is stored as a plain integer to avoid circular FK with deal_pipeline.
    # The relationship is one-directional: Deal.memo_id -> ICMemo.id.
    deal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="memos")
    deal: Mapped["Deal | None"] = relationship("Deal", back_populates="memo")


class AgentLog(Base):
    """Audit log for every agent run — status, cost, tokens, errors."""

    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"), nullable=False, default=AgentStatus.PENDING
    )
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CompetitorCompany(Base):
    """Verified competitor data cached from structured sources (Wikidata, GLEIF, Explorium)."""

    __tablename__ = "competitor_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_db: Mapped[str] = mapped_column(String(50), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    funding_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hq_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_verified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="competitors")


class ConfidenceLevel(str, PyEnum):
    """Confidence level for a deal score."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class DealScore(Base):
    """Composite score and dimension breakdown for a deal."""

    __tablename__ = "deal_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financials_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="INSUFFICIENT")
    methodology_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    override_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    deal: Mapped["Deal"] = relationship("Deal")


class ScoreHistory(Base):
    """Historical record of score changes for a deal."""

    __tablename__ = "score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    financials: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_score_history_deal_time", "deal_id", desc("created_at")),
    )


class ActivityLog(Base):
    """Audit log of activities for a deal."""

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Signal(Base):
    """A signal detected for a deal (earnings surprise, valuation gap, etc.)."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # up, down, neutral
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    deal: Mapped["Deal"] = relationship("Deal")

    __table_args__ = (
        Index("idx_signals_deal_time", "deal_id", desc("detected_at")),
        Index("idx_signals_type", "signal_type"),
    )


class MarketPulseSetting(Base):
    """Configurable market pulse setting (e.g., recession probability, sector sentiment)."""

    __tablename__ = "market_pulse_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # up, down
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── NEW: Investment Decision Platform Models ─────────────────────────────────


class InvestmentView(Base):
    """A versioned, editable investment view (the narrative thesis) for a deal."""

    __tablename__ = "investment_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    authored_by: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    edited_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[InvestmentViewStatus] = mapped_column(
        Enum(InvestmentViewStatus, name="investment_view_status"),
        nullable=False,
        default=InvestmentViewStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("deal_id", "version", name="uq_investment_view_deal_version"),
    )


class DiligenceItem(Base):
    """An interactive diligence checklist item for a deal."""

    __tablename__ = "diligence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DiligenceStatus] = mapped_column(
        Enum(DiligenceStatus, name="diligence_status"),
        nullable=False,
        default=DiligenceStatus.NOT_STARTED,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True
    )
    priority: Mapped[DiligencePriority] = mapped_column(
        Enum(DiligencePriority, name="diligence_priority"),
        nullable=False,
        default=DiligencePriority.MEDIUM,
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deal: Mapped["Deal"] = relationship("Deal")
    evidence: Mapped["EvidenceItem | None"] = relationship("EvidenceItem")


class DealEvent(Base):
    """Structured event log for deal activity and audit trail."""

    __tablename__ = "deal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[DealEventType] = mapped_column(
        Enum(DealEventType, name="deal_event_type"), nullable=False
    )
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type"), nullable=False, default=ActorType.SYSTEM
    )
    actor_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deal: Mapped["Deal"] = relationship("Deal")

    __table_args__ = (
        Index("idx_deal_events_deal_time", "deal_id", desc("created_at")),
    )


class ConfidenceLedger(Base):
    """Transparent breakdown of how the investment confidence score was computed."""

    __tablename__ = "confidence_ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_score: Mapped[int] = mapped_column(Integer, nullable=False)
    factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bottlenecks: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deal: Mapped["Deal"] = relationship("Deal")

    __table_args__ = (
        Index("idx_confidence_ledger_deal_version", "deal_id", desc("version")),
    )


class EvidenceConflict(Base):
    """A conflict between two evidence items from different sources."""

    __tablename__ = "evidence_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_a_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False
    )
    evidence_b_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False
    )
    conflict_description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus, name="resolution_status"),
        nullable=False,
        default=ResolutionStatus.OPEN,
    )
    resolved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence_a: Mapped["EvidenceItem"] = relationship(
        "EvidenceItem", foreign_keys=[evidence_a_id]
    )
    evidence_b: Mapped["EvidenceItem"] = relationship(
        "EvidenceItem", foreign_keys=[evidence_b_id]
    )


class DealSettings(Base):
    """Per-deal user-overridden settings (confidence weights, etc.)."""

    __tablename__ = "deal_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal_pipeline.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    confidence_weights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    deal: Mapped["Deal"] = relationship("Deal")

    __table_args__ = (
        Index("idx_deal_settings_deal_id", "deal_id"),
    )


class InvestmentStrategy(Base):
    """A persistent, configurable investment mandate that filters the universe."""

    __tablename__ = "investment_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Criteria stored as JSON for flexibility (can evolve without migrations)
    criteria: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "sectors": [],
            "geographies": [],
            "business_models": [],
            "ownership_types": [],
            "min_revenue": None,
            "max_revenue": None,
            "min_ebitda": None,
            "max_ebitda": None,
            "min_ebitda_margin": None,
            "min_revenue_growth": None,
            "max_net_debt_ebitda": None,
            "min_fcf_yield": None,
            "customer_concentration": None,
            "product_type": None,
        },
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
