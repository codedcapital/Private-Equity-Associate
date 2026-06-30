"""SQLAlchemy ORM models for the PE Investment Platform.

All tables use async-compatible SQLAlchemy 2.0 declarative style.
pgvector is used for embedding storage (1536-dim, OpenAI text-embedding-3-small).
"""

from datetime import datetime
from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
