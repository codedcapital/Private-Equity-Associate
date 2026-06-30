# AI-Driven PE Investment Platform — Master Roadmap

> **Project Start Date:** June 23, 2026
> **Estimated Duration:** 9 weeks
> **Current Status:** 🟡 Planning / Not Started

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1 — Data Layer (Weeks 1–2)](#phase-1--data-layer-weeks-12)
4. [Phase 2 — Intelligence Layer (Weeks 3–6)](#phase-2--intelligence-layer-weeks-36)
5. [Phase 3 — Analytics Layer (Weeks 7–9)](#phase-3--analytics-layer-weeks-79)
6. [Risk Register](#risk-register)
7. [Success Metrics](#success-metrics)
8. [Post-Launch Roadmap (Beyond Week 9)](#post-launch-roadmap)

---

## Executive Summary

This project builds an end-to-end AI-driven Private Equity (PE) deal platform that automates the investment analysis workflow from sourcing through Investment Committee (IC) memo generation. The system comprises:

- **Backend:** Python FastAPI with LangGraph orchestration, PostgreSQL + pgvector, Redis, Celery
- **Frontend:** Next.js (App Router) with Tailwind CSS, Recharts, Zustand
- **Data Sources:** SEC EDGAR, Companies House UK, Yahoo Finance, Tavily web search, **Crunchbase, PitchBook** (structured competitor data)
- **AI Stack:** OpenAI GPT-4 + text-embedding-3-small, LangGraph state machines
- **7 Specialized Agents:** Sourcing, Research, Competitive, Financials, LBO, Memo Generator, Orchestrator

### Target Output
A production-grade platform that can:
1. Accept a natural-language investment thesis and return ranked deal candidates
2. Automatically ingest financial data, SEC filings, and web research
3. Run full LBO (Leveraged Buyout) financial models with sensitivity analysis
4. Generate 10-page IC-quality investment memos with PDF export
5. Render interactive dashboards for pipeline management and deal analysis

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                     │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Dashboard│ │ Deal Detail│ │ LBO UI   │ │ Memo Viewer  │  │
│  │ (Kanban) │ │ (Tabbed)   │ │ (Heatmap)│ │ (PDF)        │  │
│  └──────────┘ └────────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST + WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Router Layer                                        │  │
│  │  /agents/sourcing   /agents/research   /agents/lbo  │  │
│  │  /agents/memo       /pipeline/run      /admin/*     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Framework (LangGraph)                         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │Sourcing  │ │Research  │ │Financials│ │ LBO     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────────────┐  │  │
│  │  │Competitive│ │ Memo Gen │ │ Master Orchestrator │  │  │
│  │  └──────────┘ └──────────┘ └─────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Services                                       │  │
│  │  LLM Wrapper │ LBO Engine │ Embeddings │ Vector Search│  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Async Job Queue (Celery + Redis)                     │  │
│  │  run_agent_task → instant dispatch → polling via API │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ SQL + Vector queries
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ PostgreSQL │  │   Redis    │  │  pgvector  │            │
│  │ (6 tables) │  │ (Celery)   │  │ (embeddings)│           │
│  └────────────┐  └────────────┘  └────────────┘            │
│  companies │ financials │ filings │ deal_pipeline │         │
│  ic_memos  │ filing_chunks│ agent_logs              │         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Data ingestion
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL DATA SOURCES                        │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐     │
│  │ SEC EDGAR│ │ Companies  │ │ Yahoo    │ │  Tavily  │     │
│  │ (10-K)   │ │ House UK   │ │ Finance  │ │ (Web)    │     │
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌────────────┐                                │
│  │Crunchbase│ │ PitchBook  │  ← structured competitor data │
│  │ (API)    │ │ (API)      │                                │
│  └──────────┘ └────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack Matrix

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind | Dashboard, deal views, LBO interactive UI |
| Frontend State | Zustand | Global state management |
| Frontend Data | TanStack Query | API calls, caching, polling |
| Frontend Charts | Recharts | Financial charts, sensitivity heatmaps |
| Frontend Icons | Lucide React | Consistent iconography |
| Backend | FastAPI + Uvicorn | API framework, async request handling |
| Backend ORM | SQLAlchemy 2.0 + Alembic | Database models, migrations |
| Backend DB | PostgreSQL 15 + pgvector | Relational data, vector search |
| Backend Queue | Celery + Redis | Async agent job processing |
| Backend AI | LangGraph + OpenAI | Agent orchestration, LLM calls |
| Backend PDF | WeasyPrint | IC memo PDF generation |
| Backend Testing | pytest | Unit + integration tests |
| Backend Packaging | uv (or Poetry) | Python dependency management |
| Infra | Docker Compose | Local dev environment |
| Deployment | Railway (backend) + Vercel (frontend) | Production hosting |
| Version Control | GitHub + GitHub Actions | CI/CD |

---

## Phase 1 — Data Layer (Weeks 1–2)

> **Goal:** Build the foundational data infrastructure. Every table, every CRUD operation, every data pipeline must be rock-solid before any AI work begins.
> **Golden Rule:** "If a senior associate at Apollo saw this output, would they trust the number?"

### Week 1 — Environment, Schema, Migrations

#### Day 1 — Project Scaffolding (Monorepo + Docker)
**Owner:** Backend Engineer (You)
**Deliverables:**
- [ ] GitHub repo created with monorepo structure: `/backend`, `/frontend`, `/agents`, `/data`
- [ ] `docker-compose.yml` with 3 services:
  - `postgres` (PostgreSQL 15 + pgvector extension)
  - `redis` (Redis 7 for Celery job queue)
  - `pgadmin` (optional, for DB inspection)
- [ ] `.env` file created with all secrets:
  - `DATABASE_URL`, `REDIS_URL`
  - `OPENAI_API_KEY`, `SEC_API_KEY`
  - `CRUNCHBASE_API_KEY`, `PITCHBOOK_API_KEY` (structured competitor data — optional but strongly recommended)
  - `COMPANIES_HOUSE_API_KEY`, `TAVILY_API_KEY`
- [ ] `.env` added to `.gitignore` immediately
- [ ] `pyproject.toml` initialized (use `uv` or `poetry` — **not** plain pip)
- [ ] Core dependencies installed:
  ```
  fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pgvector, pydantic, pydantic-settings, langchain, langgraph, openai, tenacity, celery, redis, yfinance, tavily-python, weasyprint, apscheduler, pytest, pytest-asyncio, httpx
  ```

**Verification:** `docker compose up` runs without errors. All three services are reachable.

---

#### Day 2 — Database Schema (SQLAlchemy + Alembic)
**Owner:** Backend Engineer
**Deliverables:**
- [ ] SQLAlchemy ORM models for all 6 tables:

```python
# companies
class Company(Base):
    id: int (PK)
    name: str
    ticker: str (nullable)
    sector: str
    geography: str
    source: enum(sec, companies_house, manual)
    created_at: datetime

# financials
class Financial(Base):
    id: int (PK)
    company_id: int (FK)
    report_date: date
    revenue: float
    ebitda: float
    net_income: float
    total_debt: float
    cash: float
    total_assets: float
    total_equity: float
    operating_cf: float
    capex: float
    # computed fields
    net_debt: float
    fcf: float
    ebitda_margin: float
    net_debt_ebitda: float
    revenue_growth: float
    created_at: datetime

# filings
class Filing(Base):
    id: int (PK)
    company_id: int (FK)
    filing_type: str (10-K, 10-Q, etc.)
    filing_date: date
    accession_number: str
    raw_text: text
    embedding: Vector(1536)  # pgvector, OpenAI text-embedding-3-small
    created_at: datetime

# filing_chunks (Day 4 of Week 2)
class FilingChunk(Base):
    id: int (PK)
    filing_id: int (FK)
    chunk_index: int
    chunk_text: text
    embedding: Vector(1536)
    created_at: datetime

# deal_pipeline
class Deal(Base):
    id: int (PK)
    company_id: int (FK)
    stage: enum(sourcing, diligence, ic_ready, passed, rejected, closed)
    entry_ev: float (nullable)
    entry_ebitda: float (nullable)
    lbo_irr: float (nullable)
    lbo_moic: float (nullable)
    memo_id: int (nullable, FK to ic_memos)
    last_updated: datetime
    created_at: datetime

# ic_memos
class ICMemo(Base):
    id: int (PK)
    company_id: int (FK)
    deal_id: int (FK)
    sections: JSON  # {section_name: content, ...}
    word_count: int
    confidence_score: float
    pdf_path: str
    created_at: datetime

# agent_logs
class AgentLog(Base):
    id: int (PK)
    run_id: str (UUID)
    agent_name: str
    status: enum(pending, running, complete, failed)
    input: JSON
    output: JSON
    duration_ms: int
    tokens_used: int
    cost_usd: float
    errors: list[str]
    created_at: datetime
```

- [ ] Alembic initialized and configured to autogenerate from models
- [ ] First migration generated: `alembic revision --autogenerate -m "initial_schema"`
- [ ] Migration applied: `alembic upgrade head`
- [ ] Tables verified in pgadmin or via `psql`

**Verification:** `\dt` in psql shows all 6 tables. `\d filings` shows the `embedding` vector column.

---

#### Day 3 — Database Utilities
**Owner:** Backend Engineer
**Deliverables:**
- [ ] `db/session.py` — SQLAlchemy **async** session factory:
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
  # Use asyncpg driver: postgresql+asyncpg://...
  ```
- [ ] `db/crud.py` — basic CRUD for each table:
  - `create_*`, `get_by_id`, `list_with_filters`, `update`, `delete`
  - Use async/await throughout
- [ ] `db/seed.py` — inserts 3-5 dummy companies:
  ```python
  seed_companies = [
      {"name": "Bill.com Holdings", "ticker": "BILL", "sector": "B2B SaaS", "source": "sec"},
      {"name": "Monday.com", "ticker": "MNDY", "sector": "B2B SaaS", "source": "sec"},
      {"name": "Domo Inc", "ticker": "DOMO", "sector": "B2B SaaS / Analytics", "source": "sec"},
      {"name": "Bandwidth Inc", "ticker": "BAND", "sector": "CPaaS / Telecom", "source": "sec"},
  ]
  ```
- [ ] `pytest` tests for all CRUD functions (at least 1 test per table)

**Verification:** `pytest db/tests/ -v` passes all tests. Seeded data is queryable.

---

#### Day 4 — FastAPI Skeleton
**Owner:** Backend Engineer
**Deliverables:**
- [ ] `api/main.py` — FastAPI app initialization:
  - CORS middleware configured (allow Vercel domain in production)
  - Router mounting: `/agents/sourcing`, `/agents/research`, `/agents/financials`, `/agents/lbo`, `/agents/competitive`, `/agents/memo`, `/pipeline`, `/admin`
  - Global exception handler → structured JSON (never leak raw tracebacks)
  - Request logging middleware: `timestamp | METHOD path | status_code | duration_ms`
- [ ] Empty router files for each agent with `GET /health` → `{"status": "ok"}`
- [ ] `uvicorn api.main:app --reload` verified — all health endpoints return 200

**Verification:** `curl http://localhost:8000/agents/sourcing/health` returns `{"status":"ok"}`. OpenAPI docs at `/docs` show all routers.

---

#### Day 5 — Pydantic Schemas
**Owner:** Backend Engineer
**Deliverables:**
- [ ] `schemas/company.py`:
  ```python
  class CompanyCreate(BaseModel): ...
  class CompanyRead(BaseModel): ...
  class CompanyList(BaseModel): companies: list[CompanyRead]; total: int
  ```
- [ ] `schemas/deal.py`:
  ```python
  class DealStage(str, Enum): sourcing = "sourcing"; diligence = "diligence"; ic_ready = "ic_ready"; passed = "passed"; rejected = "rejected"; closed = "closed"
  class DealCreate(BaseModel): ...
  class DealRead(BaseModel): ...
  ```
- [ ] `schemas/agent.py`:
  ```python
  class AgentStatus(str, Enum): pending = "pending"; running = "running"; complete = "complete"; failed = "failed"
  class AgentRunRequest(BaseModel): company_id: int; overrides: dict = {}
  class AgentRunResponse(BaseModel): run_id: str; status: AgentStatus; message: str
  ```
- [ ] `schemas/financials.py`:
  ```python
  class FinancialProfile(BaseModel):
      revenue: float
      ebitda: float
      ebitda_margin: float
      revenue_growth: float
      net_debt: float
      net_debt_ebitda: float
      fcf: float
      fcf_yield: float
      # ... all computed ratios as typed fields
  ```
- [ ] All schemas wired into routers so FastAPI generates correct OpenAPI docs

**Verification:** `/docs` shows all request/response schemas. No `Any` types in critical paths.

---

### Week 2 — Data Ingestion

#### Day 1 — SEC EDGAR Integration
**Owner:** Backend Engineer
**Deliverables:**
- [ ] Install `edgar` library: `uv pip install edgar`
- [ ] Test fetch 10-K for known ticker (BILL, MNDY, DOMO)
- [ ] `ingest/sec_fetcher.py` with 3 functions:
  ```python
  def get_company_filings(ticker: str) -> list[dict]: ...
  def download_filing(accession_number: str) -> str: ...  # raw HTML/XML
  def parse_filing_to_text(filing_html: str) -> str: ...  # strip tags, normalize whitespace
  ```
- [ ] Clean raw HTML/XML into plain text (use BeautifulSoup or html.parser)
- [ ] Write parsed text to `filings` table with `company_id`, `filing_type`, `filing_date`, `raw_text`
- [ ] End-to-end test: run script for one company, verify row in DB

**Verification:** `python -m ingest.sec_fetcher --ticker BILL` creates a row in `filings`. Text is readable (not raw HTML).

---

#### Day 2 — Companies House Integration
**Owner:** Backend Engineer
**Deliverables:**
- [ ] Register for free Companies House API key at [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk)
- [ ] `ingest/companies_house.py` with functions:
  ```python
  def search_company(name: str) -> list[dict]: ...
  def get_company_profile(company_number: str) -> dict: ...
  def get_filing_history(company_number: str) -> list[dict]: ...
  ```
- [ ] Map Companies House fields to `companies` schema:
  - `registered_name`, `incorporation_date`, `sic_code` → `sector`
- [ ] Add `source` enum to `companies` table: `sec`, `companies_house`, `manual`
- [ ] Test with a known UK PE-backed SaaS company

**Verification:** UK company data appears in `companies` table with `source = companies_house`.

---

#### Day 3 — Financial Data Loader
**Owner:** Backend Engineer
**Deliverables:**
- [ ] Install `yfinance`: `uv pip install yfinance`
- [ ] Test pulling income statement, balance sheet, cash flow for a ticker
- [ ] `ingest/financial_loader.py` — maps raw yfinance to `financials` schema:
  ```python
  def load_financials(ticker: str, company_id: int) -> FinancialProfile: ...
  ```
- [ ] Compute derived fields at ingestion:
  - `EBITDA` (if not direct from yfinance)
  - `net_debt = total_debt - cash`
  - `FCF = operating_cf - capex`
- [ ] Handle missing data gracefully: log warning, store `None`, never crash
- [ ] CLI script: `python -m ingest.run --ticker BILL --source sec,financials`

**Verification:** `python -m ingest.run --ticker BILL` populates both `companies` and `financials`. Derived ratios match manual calculation.

---

#### Day 4 — Embedding Pipeline
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `core/embeddings.py`:
  ```python
  def generate_embedding(text: str) -> list[float]: ...  # OpenAI text-embedding-3-small, 1536-dim
  ```
- [ ] `ingest/embedding_pipeline.py`:
  1. Read all `filings` rows without embeddings
  2. Chunk text into 512-token windows with 50-token overlap
  3. Generate embedding per chunk
  4. Store each chunk in new `filing_chunks` table: `filing_id`, `chunk_index`, `chunk_text`, `embedding`
- [ ] `core/vector_search.py`:
  ```python
  def semantic_search(query: str, top_k: int = 5) -> list[ChunkResult]: ...  # pgvector cosine similarity
  ```
- [ ] Test: `semantic_search("revenue growth SaaS")` returns relevant chunks

**Verification:** `SELECT * FROM filing_chunks` shows chunks with valid vector embeddings. Cosine similarity search returns relevant results.

---

#### Day 5 — Ingestion Validation + Scheduler
**Owner:** Backend Engineer
**Deliverables:**
- [ ] `validate_data.py` script:
  ```
  ✓ 5 companies | ✓ 23 filings | ✓ 847 chunks | ✗ 2 companies missing financials
  ```
  - Every company has ≥1 filing
  - Every filing has embeddings
  - No `None` in critical financial fields
- [ ] `ingest/scheduler.py` — APScheduler to run full ingestion pipeline nightly
- [ ] `GET /admin/ingest/status` endpoint:
  ```json
  {"last_run": "2026-06-22T03:00:00Z", "companies": 5, "filings": 23, "chunks": 847}
  ```
- [ ] Commit, push to GitHub
- [ ] Update README with Data Layer documentation

**Verification:** Scheduler runs without errors. `/admin/ingest/status` returns accurate counts. All validation checks pass.

**Week 1-2 Milestone:** 🎯 Data infrastructure is complete. All tables exist, CRUD is tested, ingestion pipelines work, embeddings are searchable.

---

## Phase 2 — Intelligence Layer (Weeks 3–6)

> **Goal:** Build the AI agent framework and all 6 specialized agents. Financial logic must be deterministic and testable before any LLM narration is added.

### Week 3 — FastAPI Foundation + Agent Framework

#### Day 1 — Agent Base Class
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/base.py` — abstract `BaseAgent` class:
  ```python
  class BaseAgent(ABC):
      @abstractmethod
      async def run(self, input: dict) -> dict: ...
      
      async def log_run(self, run_id: str, input: dict, output: dict) -> None: ...
      async def get_status(self, run_id: str) -> AgentStatus: ...
  ```
- [ ] `core/run_tracker.py` — UUID assignment, status tracking, write to `agent_logs`:
  ```python
  class RunTracker:
      async def start_run(self, agent_name: str, input: dict) -> str: ...  # returns run_id
      async def update_status(self, run_id: str, status: AgentStatus, output: dict = None): ...
      async def log_error(self, run_id: str, error: str): ...
  ```
- [ ] `GET /agents/runs/{run_id}` endpoint — returns full log entry
- [ ] `DummyAgent` for testing — inherits `BaseAgent`, returns `{"result": "ok"}`
- [ ] Test: verify `DummyAgent` logs correctly via API

**Verification:** `POST /agents/dummy/run` → `{"run_id": "...", "status": "pending"}`. `GET /agents/runs/{run_id}` shows complete log with input, output, duration.

---

#### Day 2 — Async Job Queue (Celery + Redis)
**Owner:** Backend Engineer
**Deliverables:**
- [ ] Install Celery + Redis: `uv pip install celery redis`
- [ ] `core/tasks.py`:
  ```python
  @celery_app.task(bind=True)
  def run_agent_task(self, agent_name: str, input_data: dict, run_id: str) -> dict: ...
  ```
- [ ] `POST /agents/{agent_name}/run` endpoint:
  - Dispatches Celery task immediately
  - Returns `{"run_id": "...", "status": "pending"}`
- [ ] Client polling pattern: `GET /agents/runs/{run_id}` until status is `complete`
- [ ] Test full async loop with `DummyAgent`

**Verification:** `POST /agents/dummy/run` → `run_id`. Celery worker processes task. `GET /agents/runs/{run_id}` transitions from `pending` → `running` → `complete`.

---

#### Days 3-4 — LangGraph Setup
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] Install `langgraph`: `uv pip install langgraph`
- [ ] Read LangGraph docs for `StateGraph`, conditional edges, compilation
- [ ] Minimal working graph: `node_a → node_b → node_c` with shared state dict
- [ ] `agents/state.py` — `DealState` TypedDict:
  ```python
  class DealState(TypedDict):
      company_name: str
      company_id: Optional[int]
      sector: Optional[str]
      financials: Optional[FinancialProfile]
      competitive_map: Optional[dict]
      lbo_result: Optional[LBOResult]
      memo_sections: Optional[dict]
      run_id: str
      errors: list[str]
  ```
- [ ] Verify JSON serialization/deserialization of `DealState`
- [ ] Verify `DealState` can be stored in PostgreSQL (as JSONB) for run resumability

**Verification:** `DealState` round-trips through JSON and PostgreSQL without data loss. Type hints are preserved on deserialization.

---

#### Day 5 — OpenAI Integration Layer
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `core/llm.py` — OpenAI wrapper:
  ```python
  class LLMClient:
      async def chat(self, system: str, user: str, model: str = "gpt-4o", temperature: float = 0.3) -> str: ...
      # Automatic retry on rate limit (tenacity)
      # Token counting per call
      # Spend tracking
  ```
- [ ] `core/prompts.py` — all system prompts as constants (never hardcode in agent logic):
  ```python
  PROMPT_FINANCIAL_INTERPRET = "You are a PE associate..."
  PROMPT_LBO_INTERPRET = "You are analyzing an LBO model..."
  # etc.
  ```
- [ ] Test `llm.chat()` with simple prompt, verify response and token count
- [ ] Spend tracking: write `tokens_used` and `cost_usd` to `agent_logs`
- [ ] Hard max_tokens budget per agent run (e.g., 4000 tokens), raise exception if exceeded

**Verification:** `LLMClient` returns valid responses. Token counts are accurate. Budget enforcement works. Cost is logged.

---

### Week 4 — Financial Analysis Agent + LBO Engine

> **Critical:** Build the LBO engine as pure Python first. No LLM. It must be deterministic, mathematically verifiable, and fully unit-tested.

#### Days 1-2 — LBO Engine (Pure Python, No LLM)
**Owner:** Backend Engineer (Quantitative)
**Deliverables:**
- [ ] `core/lbo_engine.py`:
  ```python
  @dataclass
  class LBOResult:
      entry_equity: float
      entry_debt: float
      debt_schedule: list[dict]  # year, interest, amortization, ending_balance
      ebitda_projection: list[float]
      exit_ev: float
      exit_equity: float
      irr: float
      moic: float
      
  def run_lbo(
      entry_ev: float,
      entry_ebitda: float,
      debt_pct: float,
      revenue_growth: list[float],
      margin_expansion: float,  # bps per year
      exit_multiple: float,
      hold_years: int,
  ) -> LBOResult: ...
  ```
  Model computes:
  - Entry equity = EV × (1 - debt_pct)
  - Entry debt = EV × debt_pct
  - Debt schedule: interest + amortization each year
  - EBITDA projection: base × growth × margin expansion
  - Exit EV = exit_ebitda × exit_multiple
  - Exit equity = exit_ev - ending_debt
  - IRR = (exit_equity / entry_equity)^(1/hold_years) - 1
  - MOIC = exit_equity / entry_equity
- [ ] Sensitivity table generator:
  ```python
  def sensitivity_grid(
      base_inputs: dict,
      entry_range: tuple[float, float, float],  # min, max, step
      exit_range: tuple[float, float, float]
  ) -> dict: ...  # grid of IRR values
  ```
- [ ] 15+ unit tests in `agents/lbo/tests/`:
  - Zero-debt case
  - 100% debt (should error)
  - Negative IRR scenario
  - 5-year vs 3-year hold
  - Edge cases
- [ ] Run all tests: `pytest agents/lbo/tests/ -v`

**Verification:** All 15+ tests pass. IRR calculations match Excel/manual verification. Sensitivity grid has correct dimensions.

---

#### Day 3 — Financial Analysis Agent
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/financials/graph.py` — LangGraph with 4 nodes:
  1. `load_data` — fetches from `financials` table for `company_id`
  2. `compute_ratios` — pure Python, calculates all ratios
  3. `flag_risks` — rule-based flags:
     - `net_debt_ebitda > 5.0` → "leverage concern"
     - `revenue_growth < 0` → "declining revenue"
     - `ebitda_margin < 0.10` → "low profitability"
     - `fcf_yield < 0.02` → "poor cash conversion"
  4. `interpret` — single LLM call to narrate financial picture in 3 paragraphs
- [ ] Nodes 1-3 are deterministic and independently testable
- [ ] `POST /agents/financials` endpoint
- [ ] Test with real `company_id` from seeded data
- [ ] Verify output matches `FinancialProfile` schema exactly

**Verification:** `POST /agents/financials` returns valid `FinancialProfile`. Risk flags are accurate. LLM interpretation is coherent. Test with real data.

---

#### Days 4-5 — LBO Agent (LLM Interpretation Layer)
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/lbo/graph.py` — 4 nodes:
  1. `prepare_inputs` — extracts from `DealState.financials` (entry EBITDA, implied EV from comps)
  2. `run_model` — calls `lbo_engine.run_lbo()` with base/bull/bear assumptions
  3. `generate_sensitivity` — calls `lbo_engine.sensitivity_grid()`
  4. `interpret` — LLM call: "Given these returns, what are the key value creation levers? What would kill this deal?"
- [ ] `POST /agents/lbo` endpoint — accepts overrides:
  ```json
  {"company_id": 1, "entry_multiple": 12.0, "debt_pct": 0.60, "hold_years": 5}
  ```
  Uses defaults from financial profile if not provided.
- [ ] Test on target company: verify IRR/MOIC numbers are mathematically correct
- [ ] Add sensitivity grid to response (for frontend heatmap rendering)

**Verification:** LBO numbers match Excel model. Sensitivity grid renders correctly. LLM interpretation is insightful, not generic. Base/bull/bear scenarios are distinct.

**Week 4 Milestone:** 🎯 Financial backbone is complete. LBO engine is mathematically verified. Financial agent produces structured, accurate output.

---

### Week 5 — Memo Generator + Orchestrator

#### Days 1-2 — Investment Memo Generator
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/memo/prompts.py` — 8 system prompts, one per section:
  1. Executive Summary
  2. Company Overview
  3. Industry Analysis
  4. Competitive Positioning
  5. Financial Analysis
  6. LBO Model & Returns
  7. Risk Factors
  8. Investment Recommendation
  - Each prompt references specific `DealState` fields (not the entire state)
- [ ] `agents/memo/graph.py` — 4 nodes:
  1. `aggregate_context` — pulls all prior agent outputs from `DealState`, structures into context object
  2. `write_sections` — 8 LLM calls in parallel using `asyncio.gather()`
  3. `edit_pass` — single LLM call reviewing full draft for consistency/contradictions
  4. `format_output` — structures final JSON:
     ```json
     {"sections": {"executive_summary": {"content": "...", "word_count": 450, "confidence_score": 0.85}}, ...}
     ```
- [ ] PDF renderer using WeasyPrint:
  - Styled HTML template for IC memo
  - Store in `/outputs/memos/{memo_id}.pdf`
- [ ] `POST /agents/memo/generate` → dispatches async job, returns `memo_id`
- [ ] `GET /agents/memo/{memo_id}` → returns memo JSON + PDF download URL

**Verification:** Memo has all 8 sections. No contradictions between sections. PDF is professionally formatted. Word count is accurate.

---

#### Days 3-4 — Master Orchestrator
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/orchestrator.py` — top-level LangGraph graph:
  ```
  sourcing → research (parallel with competitive) → financials → lbo → memo
  ```
  - Each node calls the corresponding agent's `.run()` and merges result into `DealState`
- [ ] Checkpointing after each agent: save `DealState` to PostgreSQL
  - If run fails at LBO stage, resume from financial analysis without re-running everything
- [ ] `POST /pipeline/run` — takes company name or ID, runs full pipeline end-to-end
- [ ] Test full pipeline on one company
- [ ] Expected: first run takes 2-3 minutes, costs ~$0.50 in API calls

**Verification:** Pipeline completes successfully. All agent outputs are in `DealState`. Checkpointing works: killing the process mid-run and resuming picks up where it left off.

---

#### Day 5 — Error Handling + Observability
**Owner:** Backend Engineer
**Deliverables:**
- [ ] Retry logic on every LLM node:
  - If malformed JSON, retry once with stricter prompt before failing
- [ ] `confidence_score` on every agent output:
  - Ask LLM to self-rate 0-1 based on data quality
- [ ] `GET /pipeline/runs` endpoint:
  ```json
  {"runs": [{"run_id": "...", "company_name": "...", "status": "complete", "duration": 180, "cost_usd": 0.47}], ...}
  ```
- [ ] Test failure scenarios:
  - Missing SEC data → clear error in `agent_logs`, structured response (not 500)
  - Bad LBO inputs → validation error, graceful degradation
  - LLM timeout → retry, then fail with meaningful message

**Verification:** Every failure writes a clear error to `agent_logs` and returns structured error response. No raw 500s. Confidence scores are populated.

**Week 5 Milestone:** 🎯 Full pipeline works end-to-end. Memo generator produces 8-section documents. Orchestrator handles failures gracefully.

---

### Week 6 — Sourcing, Research, Competitive Agents

#### Days 1-2 — Deal Sourcing Agent
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/sourcing/graph.py` — 4 nodes:
  1. `parse_thesis` — LLM converts natural language to structured filters:
     ```json
     {"sector": "B2B SaaS", "geography": "Europe", "revenue_min": 10e6, "revenue_max": 50e6, "ebitda_margin_min": 0.15, "growth_rate_min": 0.20}
     ```
  2. `screen_database` — SQL query against `companies` + `financials` using extracted filters
  3. `enrich_candidates` — for each candidate, pull missing data from web using Tavily API
  4. `score_and_rank` — weighted scoring:
     - Sector fit: 30%
     - Financial profile: 40%
     - Strategic rationale: 30%
- [ ] Output: top 10 candidates with scores and rationale
- [ ] `POST /agents/sourcing` — input: `{"thesis": "B2B SaaS, €10-50M ARR, European HQ, profitable"}`
- [ ] Test with 3 different thesis statements, verify ranking feels logical

**Verification:** Sourcing returns ranked candidates. Scoring is transparent (weights visible). Tavily enrichment adds real data. Ranking passes sanity check.

---

#### Day 3 — Industry Research Agent
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `agents/research/graph.py` — 4 nodes:
  1. `classify_sector` — maps company to GICS taxonomy
  2. `retrieve_filings` — semantic search on `filing_chunks` for sector-relevant content
  3. `web_research` — Tavily search for recent news, market reports, competitor announcements
  4. `synthesize` — LLM produces structured output:
     ```json
     {"tam": 45e9, "cagr": 0.12, "growth_drivers": [...], "risks": [...], "regulatory_notes": "...", "key_players": [...]}
     ```
- [ ] Each field cites its source (filing chunk ID or web URL)
- [ ] `POST /agents/research` — input: `{"company_id": 1}` → returns `IndustryProfile`

**Verification:** Research output includes citations. TAM/CAGR are reasonable. Growth drivers and risks are specific, not generic. Sources are verifiable.

---

#### Day 4 — Competitive Positioning Agent
**Owner:** Backend Engineer (AI/ML)
**Deliverables:**
- [ ] `ingest/competitor_data.py` — structured competitor source layer:
  ```python
  def fetch_crunchbase_competitors(company_name: str, sector: str) -> list[dict]: ...
  def fetch_pitchbook_competitors(company_name: str, sector: str) -> list[dict]: ...
  ```
  - **Primary:** Query Crunchbase API for companies in same sector + funding stage
  - **Fallback:** Query PitchBook API (or free tier) for peer companies
  - **Last resort:** Tavily web search with query `"competitors of {company_name} in {sector}"`
  - Every competitor returned must include: `name`, `domain`, `funding_stage`, `hq_location`, `source_db`
- [ ] `agents/competitive/graph.py` — 4 nodes, **deterministic competitor discovery first**:
  1. **`identify_competitors`** — structured DB query (NOT LLM):
     - Call `fetch_crunchbase_competitors()` → get up to 10 candidates
     - Filter by: same sector, similar revenue range (±50%), same geography (if relevant)
     - Deduplicate by domain/name
     - Select top 5-8 verified competitors
     - **Why this matters:** LLMs hallucinate competitors (e.g., naming companies that don't exist or aren't actually competitors). Structured databases return real companies with verified funding, revenue, and sector tags. The LLM should only *profile* competitors, not *discover* them.
  2. **`extract_profiles`** — for each verified competitor, use **LLM + Tavily web search** to build profile:
     - Business model (subscription, usage-based, enterprise, etc.)
     - Pricing (public plans, seat-based, API-based)
     - Customer segment (SMB, mid-market, enterprise)
     - Geographic presence
     - Funding/ownership (VC-backed, PE-backed, public, bootstrapped)
     - Key differentiators vs. target
  3. **`build_matrix`** — structured competitive matrix:
     ```json
     {"competitors": {"Competitor A": {"business_model": "...", "pricing": "...", "segment": "...", "geography": "...", "funding": "...", "source": "crunchbase"}}}
     ```
  4. **`assess_moat`** — LLM analysis of target's differentiation:
     - Switching costs
     - Network effects
     - IP / proprietary technology
     - Distribution advantages
     - Brand / reputation
     - **Output must cite specific competitors from the matrix** (not generic statements)
- [ ] `POST /agents/competitive` → returns `CompetitiveMap`:
  ```json
  {
    "competitors": [...],          // verified competitor list with source attribution
    "matrix": {...},               // structured competitive matrix
    "moat_assessment": "...",    // LLM analysis with citations
    "data_sources": ["crunchbase", "pitchbook", "tavily"],  // which sources were used
    "confidence_score": 0.85       // based on % of competitors from structured DB vs. web search
  }
  ```
- [ ] Matrix output renders directly as HTML table (columns = attributes, rows = competitors)
- [ ] Add `competitor_companies` table for caching:
  ```python
  class CompetitorCompany(Base):
      id: int (PK)
      target_company_id: int (FK)
      name: str
      domain: str
      source_db: str  # crunchbase, pitchbook, tavily
      sector: str
      funding_stage: str
      hq_location: str
      last_verified: datetime
  ```

**Verification:**
- All 5-8 competitors are real, verifiable companies (check domains exist)
- At least 70% of competitors come from structured DB (Crunchbase/PitchBook), not web search
- Moat assessment cites specific competitors by name (e.g., "Unlike Competitor X, the target has...")
- Competitive matrix is complete — no missing fields for any competitor
- If Crunchbase API is unavailable, graceful fallback to Tavily with clear source attribution

---

#### Day 5 — Integration Testing
**Owner:** QA / Backend Engineer
**Deliverables:**
- [ ] Run full pipeline on chosen target company — all 6 agents in sequence
- [ ] Manual review of every output:
  - Financials correct? Ratios match source data?
  - LBO math checks out? Sensitivity grid is smooth?
  - **Competitive matrix: are competitors from structured DB (Crunchbase/PitchBook) or web search?** Verify ≥70% from structured sources.
  - **Competitor domains exist?** Spot-check 2-3 competitor websites to confirm they are real companies.
  - Moat assessment cites specific competitors by name?
  - Memo has no contradictions? Sections flow logically?
- [ ] Fix data quality issues — tighten prompts where needed
- [ ] Document full API in `README.md`:
  - Every endpoint
  - Request/response schemas
  - Example cURL commands

**Verification:** Full pipeline run succeeds. Manual review finds no factual errors. API documentation is complete and accurate.

**Week 6 Milestone:** 🎯 All 6 agents are built and tested. Full pipeline runs end-to-end. API is documented.

---

## Phase 3 — Analytics Layer (Weeks 7–9)

> **Goal:** Build a professional frontend that makes the AI output feel like a real PE platform, not a demo.

### Week 7 — Next.js Setup + Core Components

#### Day 1 — Next.js Project
**Owner:** Frontend Engineer (You)
**Deliverables:**
- [ ] `npx create-next-app@latest frontend --typescript --tailwind --app` (App Router)
- [ ] Install dependencies:
  ```bash
  npm install recharts @tanstack/react-query zustand lucide-react clsx tailwind-merge
  ```
- [ ] Design tokens in `tailwind.config.ts`:
  ```typescript
  colors: {
    background: "#0A0A0F",      // near-black
    accent: "#C8A96E",          // gold
    muted: "#6B7280",           // muted text
    danger: "#EF4444",          // danger red
    success: "#10B981",         // success green
    surface: "#111118",         // card background
    border: "#1F1F2E",          // subtle borders
  }
  ```
- [ ] IBM Plex Mono as primary font (Google Fonts)
- [ ] `lib/api.ts` — typed API client for all FastAPI endpoints:
  ```typescript
  async function apiCall<T>(endpoint: string, options?: RequestInit): Promise<T>
  ```
  - Error handling
  - Automatic JSON parsing
  - Authentication header (if needed)

**Verification:** `npm run dev` starts without errors. Tailwind classes work. API client can call backend health endpoints.

---

#### Days 2-3 — Shared Components
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] `StatusBadge` — renders agent status with color:
  - `pending` → amber dot
  - `running` → blue animated pulse
  - `complete` → green check
  - `failed` → red X
- [ ] `MetricCard` — financial metric display:
  - Label, value, trend arrow (▲ ▼), optional flag indicator
- [ ] `AgentRunLog` — scrollable terminal-style log:
  - Timestamps, step names, status, duration
  - Monospace font, dark background
- [ ] `SectionLoader` — skeleton loader for pending data
- [ ] `ErrorBoundary` — catches render errors, shows clean fallback

**Verification:** All components render in Storybook (or simple test page). StatusBadge colors are correct. MetricCard handles large numbers (e.g., "$1.2B").

---

#### Days 4-5 — Pipeline View (Dashboard)
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] `/dashboard` page — pipeline Kanban:
  - Columns: Sourcing → Diligence → IC Ready → Passed → Rejected → Closed
  - Drag-and-drop between columns (optional, can be click-to-move)
- [ ] Deal cards show:
  - Company name, sector
  - Revenue, EBITDA margin
  - LBO IRR (if run), MOIC
  - Last updated timestamp
- [ ] `POST /deals` from UI — form to add company manually:
  - Name, ticker, sector, geography
- [ ] Click deal card → navigate to `/deal/[id]`
- [ ] Real-time polling: every 30 seconds, refresh deal statuses
  - Use `react-query` `refetchInterval: 30000`

**Verification:** Dashboard shows deals in correct columns. Adding a deal updates the UI. Polling works without flicker. Navigation to deal detail works.

**Week 7 Milestone:** 🎯 Frontend scaffold is complete. Dashboard shows pipeline. Components are reusable.

---

### Week 8 — Deal View + LBO UI

#### Days 1-2 — Deal Detail Page
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] `/deal/[id]` — tabbed layout:
  - Tabs: Overview, Financials, LBO, Competitive, Research, Memo
- [ ] **Overview tab:**
  - Company summary
  - Key metrics in 2×3 grid (revenue, EBITDA, margin, growth, net debt, FCF)
  - Agent run history (list of past runs with status)
  - "Run Full Pipeline" button
- [ ] **Financials tab:**
  - Revenue/EBITDA chart (Recharts AreaChart)
  - Ratio table (all computed ratios)
  - Risk flags as colored badges
- [ ] "Run Agent" buttons wired to `POST /agents/{name}`
- [ ] Real-time status via polling

**Verification:** All tabs render. Charts show real data. Risk flags are colored correctly. Running an agent updates status in real-time.

---

#### Day 3 — LBO Interactive UI
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] LBO tab with editable inputs:
  - Entry multiple (slider + number input)
  - Debt % (slider)
  - Hold period (dropdown: 3, 4, 5, 6 years)
  - Revenue growth per year (array of inputs)
  - Exit multiple (slider + number input)
- [ ] On any input change: debounced `POST /agents/lbo` with new assumptions
- [ ] Results display:
  - Entry equity, entry debt
  - Exit EV, exit equity
  - IRR (large, colored: red < 15%, amber 15-25%, green > 25%)
  - MOIC
- [ ] Sensitivity heatmap:
  - Table with entry multiple on X-axis, exit multiple on Y-axis
  - Cell color = IRR range (red/amber/green)
- [ ] LLM interpretation displayed below model outputs
- [ ] "Download Model" button → exports LBO assumptions + outputs as CSV

**Verification:** Changing inputs recalculates LBO instantly. Sensitivity heatmap colors are correct. CSV download contains all assumptions and results.

---

#### Days 4-5 — Memo Viewer + Competitive Matrix
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] `/deal/[id]/memo` — paginated memo viewer:
  - Section jump nav on left
  - Content on right
  - Serif font (Georgia) for readability
- [ ] "Generate Memo" button:
  - Triggers full memo pipeline
  - Progress indicator by section (sections appear as they complete)
- [ ] **Competitive tab:**
  - Sortable HTML table for competitive matrix
  - Moat assessment below
- [ ] PDF download button → `GET /agents/memo/{id}` → downloads PDF

**Verification:** Memo looks professional (like a real IC document). Competitive table is sortable. PDF download works and matches the rendered memo.

**Week 8 Milestone:** 🎯 All deal views are complete. LBO UI is interactive. Memo viewer is professional.

---

### Week 9 — Real Target Run + Polish

#### Day 1 — Choose and Run Real Target
**Owner:** Full Stack (You)
**Deliverables:**
- [ ] **Pick target company:**
  - Good candidates: Domo (DOMO), Bandwidth (BAND), or a smaller public SaaS
  - Must have public SEC filings and financial data
- [ ] Ingest all available data:
  - SEC filings (10-K, 10-Q)
  - Financials via yfinance
  - Web research via Tavily
- [ ] Run full pipeline end-to-end
- [ ] Review every output section by section
- [ ] **Manual editing pass:** correct factual errors in the memo
- [ ] Export final 10-page PDF

**Verification:** Pipeline completes on real target. Final memo is factually accurate. PDF is 10 pages, professionally formatted.

---

#### Days 2-3 — Frontend Polish
**Owner:** Frontend Engineer
**Deliverables:**
- [ ] Responsive design check:
  - Works at 1280px and 1440px (no mobile needed for this project)
- [ ] Loading states everywhere:
  - No blank screens while agents are running
  - Skeleton loaders for all data-fetching sections
- [ ] Empty states:
  - If no filings: "No filings found. Ingest Data →"
  - If no LBO run: "Run LBO Model →"
- [ ] Global notification system (toast):
  - Agent completed ✓
  - Agent failed ✗
  - Memo ready for download 📄
- [ ] Final typography pass:
  - Consistent font sizes, weights, spacing
  - IBM Plex Mono for data, Georgia for prose

**Verification:** No blank screens. Toasts appear for all major events. Typography is consistent. Layout works at target resolutions.

---

#### Day 4 — Deployment
**Owner:** DevOps / Full Stack
**Deliverables:**
- [ ] **Backend deployment on Railway:**
  - Connect PostgreSQL instance
  - Set all environment variables
  - Verify all endpoints are live (`curl` each `/health`)
- [ ] **Frontend deployment on Vercel:**
  - Set `NEXT_PUBLIC_API_URL` to Railway backend URL
  - Build succeeds
- [ ] Final end-to-end test on live deployment:
  - Sourcing → Memo → PDF download
- [ ] Fix CORS issues:
  - Add Vercel URL to FastAPI `allow_origins`
- [ ] Verify `/docs` OpenAPI page is accessible (part of demo)

**Verification:** Live deployment is fully functional. No CORS errors. OpenAPI docs are public. Sourcing → memo → PDF works end-to-end.

---

#### Day 5 — Documentation + GitHub Cleanup
**Owner:** Full Stack (You)
**Deliverables:**
- [ ] Thorough `README.md`:
  - What the project does
  - Architecture diagram (ASCII is fine)
  - Setup instructions (step-by-step)
  - Environment variables table
  - Example API calls (cURL)
  - Screenshots of key UI views
- [ ] Inline docstrings on all agent files:
  - Explain what each LangGraph node does
  - Document expected inputs/outputs
- [ ] Tag first release:
  ```bash
  git tag v1.0.0 && git push --tags
  ```
- [ ] Record Loom walkthrough (8-10 min max):
  - Show UI
  - Run sourcing agent live
  - Generate a memo
  - Download PDF
- [ ] Draft LinkedIn article:
  - Lead with the architecture decision that surprised you most
  - Not: "I built an AI tool"
  - Instead: "What I learned building an AI associate for PE diligence"

**Verification:** README is complete. All agent files have docstrings. Git tag is pushed. Loom is recorded. LinkedIn draft is written.

**Week 9 Milestone:** 🎯 Project is deployed, documented, and demo-ready. Real target company has been analyzed. Platform is production-grade.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **SEC EDGAR API rate limits** | Medium | High | Implement caching, batch requests, and exponential backoff. Use `tenacity` for retries. |
| **OpenAI API costs spiral** | Medium | High | Hard token budget per run (4000 tokens). Track spend per run. Use `text-embedding-3-small` (cheapest). Cache embeddings. |
| **LLM hallucinates financial data** | High | High | Never let LLM generate raw numbers. All financial data comes from deterministic pipelines (yfinance, SEC). LLM only narrates and interprets. |
| **LLM hallucinates competitors** | Medium | High | **Mitigated by design:** Competitor discovery uses structured DBs (Crunchbase/PitchBook), not LLM. LLM only profiles verified competitors. Fallback to Tavily with clear source attribution. |
| **Structured competitor APIs unavailable** | Medium | Medium | Crunchbase has free tier; PitchBook has paid tier. If both fail, Tavily web search is fallback. Cache competitor data in `competitor_companies` table to reduce API dependency. |
| **pgvector performance at scale** | Medium | Medium | Index embeddings with `ivfflat` or `hnsw`. Monitor query times. Shard if needed. |
| **Celery/Redis queue failures** | Low | Medium | Monitor Redis memory. Use Celery's `ack_late` for durability. Implement dead-letter queues. |
| **Yfinance data quality issues** | Medium | Medium | Validate all yfinance data against SEC filings. Flag discrepancies. Never use unverified data. |
| **Companies House API complexity** | Medium | Low | Start with SEC-only companies. Add UK companies as stretch goal. |
| **Frontend build size on Vercel** | Low | Low | Code-split routes. Lazy load heavy components. Monitor build output. |
| **Memo generation takes too long** | Medium | Medium | Parallelize section generation. Use `asyncio.gather()`. Consider streaming response. |
| **Real target company has no/missing data** | Medium | High | Have 2-3 backup targets ready. Verify data availability before Day 1 of Week 9. |

---

## Success Metrics

### Technical Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| LBO engine unit test coverage | ≥90% | `pytest --cov` |
| All API endpoints return <500ms | 95th percentile | Load testing with `locust` or `k6` |
| Full pipeline runtime | <3 minutes | Timer on `/pipeline/run` |
| API cost per full run | <$1.00 | `agent_logs.cost_usd` sum |
| Embedding search latency | <200ms | `EXPLAIN ANALYZE` on pgvector query |
| Frontend Lighthouse score | >80 | Chrome DevTools |

### Business Metrics (Quality)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Financial ratios match source data | 100% | Manual spot-check against SEC filings |
| LBO IRR accuracy vs Excel | ±0.1% | Compare 5 scenarios |
| Memo factual errors | 0 | Manual review of final memo |
| Sensitivity grid smoothness | No artifacts | Visual inspection |
| Competitive matrix accuracy | ≥80% | Manual review of competitor list |
| **Competitors from structured DB** | **≥70%** | Check `data_sources` field in `CompetitiveMap` output — count % from Crunchbase/PitchBook vs. Tavily |
| User can run full pipeline without help | Yes | Fresh user test |

---

## Post-Launch Roadmap (Beyond Week 9)

### Immediate (Week 10-12)
- [ ] Add user authentication (OAuth 2.0 / JWT)
- [ ] Multi-user support with deal sharing and permissions
- [ ] **Enhance competitor data sources:** add LinkedIn Sales Navigator, G2, Capterra for competitor profiling
- [ ] Implement deal comparison mode (side-by-side LBO models)
- [ ] Add real-time competitor alerts (notify when competitor raises funding, changes pricing, etc.)

### Short-term (Months 4-6)
- [ ] Real-time data streaming (WebSocket for agent progress)
- [ ] Advanced LBO features: PIK toggle, dividend recap, add-on modeling
- [ ] Historical deal tracking (track portfolio company performance post-close)
- [ ] Integration with actual deal management tools (Salesforce, Affinity)

### Long-term (Months 6-12)
- [ ] Fine-tuned LLM on PE-specific language (reduce API costs, improve accuracy)
- [ ] Automated deal alert system (notify when new companies match thesis)
- [ ] Multi-currency support (EUR, GBP, JPY deals)
- [ ] Mobile app (React Native) for deal review on the go
- [ ] AI-powered negotiation support (term sheet analysis)

---

## The One Rule

> **Every time you finish a day's work, ask yourself one question:**
> **"If a senior associate at Apollo saw this output right now, would they trust the number?"**
> **If the answer is no, don't move forward.**
> The financial logic has to be airtight before the AI narration matters at all — that's what separates this project from a chatbot with a finance prompt.

---

*Document Version: 1.0*
*Last Updated: June 23, 2026*
