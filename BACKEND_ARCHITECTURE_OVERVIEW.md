# PE Associate — Complete Backend Architecture Overview

> **Generated from source analysis** of `/Users/aditya/Desktop/PE Associate/PE ASSOCIATE/backend/`

---

## 1. High-Level Architecture

The PE Associate backend is a **Python 3.11+ FastAPI application** built around a **dual-engine architecture**:

1. **Intelligence Hub** — Question-centric evidence collection and management
2. **Decision Engine** — Deterministic, rule-based investment scoring (0-100)

These two engines are fed by a **LangGraph multi-agent pipeline** that runs sourcing, research, competitive analysis, financial modeling, LBO analysis, and IC memo generation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI API LAYER                               │
│  (15 routers, auth, rate limiting, request logging, global exception handler) │
├─────────────────────────────────────────────────────────────────────────────┤
│                           SERVICES & CORE LAYER                              │
│  DecisionEngine │ DataProvider │ IntelligenceHubWriter │ ScoringEngine      │
│  LLMClient │ EmbeddingService │ VectorSearch │ LBOEngine │ RunTracker        │
├─────────────────────────────────────────────────────────────────────────────┤
│                         LANGGRAPH AGENT PIPELINE                             │
│  sourcing → (research + competitive in parallel) → financials → lbo → memo    │
├─────────────────────────────────────────────────────────────────────────────┤
│                           DATA INGESTION LAYER                               │
│  Yahoo Finance │ SEC EDGAR │ Companies House │ Tavily Web Search           │
├─────────────────────────────────────────────────────────────────────────────┤
│                             DATABASE LAYER                                   │
│  PostgreSQL + pgvector │ SQLAlchemy 2.0 (async) │ Alembic migrations        │
│  Redis (Celery broker/backend)                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack & Dependencies

| Category | Technology | Version |
|----------|-----------|---------|
| Web Framework | FastAPI | ≥0.111 |
| Server | Uvicorn (standard) | ≥0.30 |
| ORM | SQLAlchemy (async) | ≥2.0 |
| Migrations | Alembic | ≥1.13 |
| DB Driver | asyncpg | ≥0.29 |
| Sync Driver | psycopg2-binary | ≥2.9 |
| Vector DB | pgvector | ≥0.2 |
| Validation | Pydantic v2 + pydantic-settings | ≥2.7 |
| AI Framework | LangGraph + LangChain | ≥0.0.60 / ≥0.2 |
| LLM | OpenAI (GPT-4o) | ≥1.30 |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim |
| Tokenizer | tiktoken | ≥0.7 |
| Task Queue | Celery + Redis | ≥5.4 |
| Scheduling | APScheduler | ≥3.10 |
| Financial Data | yfinance | ≥0.2.40 |
| SEC Filings | edgar | ≥5.0 |
| Web Search | Tavily | ≥0.3 |
| PDF Generation | WeasyPrint | ≥62.0 |
| HTTP Client | httpx + aiohttp | ≥0.27 / ≥3.9 |
| Dev Tools | pytest, black, isort, mypy, ruff, pre-commit | — |

---

## 3. Directory Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI app factory, router mounting, middleware
│   ├── auth.py              # API-key / header-based auth, UserRole, UserContext
│   ├── dependencies.py      # FastAPI DB session dependency (get_db)
│   ├── middleware.py        # RequestLoggingMiddleware (timing + status logging)
│   ├── rate_limit.py        # RateLimitMiddleware
│   └── routers/             # 15 API route modules
│       ├── admin.py
│       ├── companies.py     # Company CRUD + financial profile
│       ├── competitive.py
│       ├── dashboard.py     # Summary metrics, attention list, score refresh, signals
│       ├── financials.py
│       ├── intelligence.py  # Intelligence Hub endpoints (questions, evidence, decisions)
│       ├── lbo.py
│       ├── market_pulse.py
│       ├── memo.py
│       ├── overview.py
│       ├── pipeline.py      # Pipeline runs, agent dispatch (Celery + BackgroundTasks), deal CRUD
│       ├── research.py
│       └── sourcing.py
├── agents/                  # LangGraph multi-agent pipeline
│   ├── base.py              # BaseAgent ABC (run tracking, status, logging)
│   ├── orchestrator.py      # Master pipeline graph: sourcing → research+competitive → financials → lbo → memo → decision
│   ├── state.py             # DealState TypedDict, LBOResult, serialization helpers
│   ├── competitive/graph.py
│   ├── financials/graph.py  # 5-node graph: load_data → compute_ratios → flag_risks → interpret → produce_evidence_module
│   ├── lbo/graph.py
│   ├── memo/graph.py        # 4-node graph: aggregate_context → write_sections → edit_pass → format_output
│   ├── memo/prompts.py      # 8 section prompts (exec summary, industry, financials, etc.)
│   ├── memo/pdf_renderer.py
│   ├── research/graph.py
│   └── sourcing/graph.py
├── core/                    # Platform infrastructure
│   ├── celery_app.py        # Celery configuration, Redis broker, beat schedule (nightly at 03:00 UTC)
│   ├── config.py            # Pydantic-Settings (DATABASE_URL, OPENAI keys, Redis, Tavily, SEC, etc.)
│   ├── embeddings.py        # OpenAI embedding generation with retry (1536-dim)
│   ├── exceptions.py        # LLMError, LLMBudgetExceeded, LLMRateLimitError
│   ├── lbo_engine.py        # Pure-Python deterministic LBO model (no LLM)
│   ├── llm.py               # LLMClient: async OpenAI with retry, token counting, cost estimation, structured output
│   ├── prompts.py           # System prompts for financial interpretation, etc.
│   ├── retry.py             # Tenacity retry helpers
│   ├── run_tracker.py       # RunTracker: UUID generation, status transitions, error logging
│   ├── tasks.py             # Celery tasks: run_agent_task (with retries), nightly_ingestion_task
│   └── vector_search.py     # pgvector semantic search over filing chunks
├── db/                      # Database layer
│   ├── models.py            # 25 SQLAlchemy 2.0 declarative models (all tables, enums, relationships)
│   ├── crud.py              # 1,689 lines of async CRUD for all models
│   ├── session.py           # Async engine, async_session_factory, session dependency, pgbouncer support
│   └── seed.py              # Database seeding scripts
├── ingest/                  # Data ingestion pipelines
│   ├── companies_house.py   # UK Companies House API integration
│   ├── embedding_pipeline.py
│   ├── financial_loader.py  # Yahoo Finance → Financial model mapping (income, balance, cash flow)
│   ├── run.py               # Unified ingestion runner (bulk + single ticker, SEC + financials)
│   ├── scheduler.py         # APScheduler nightly ingestion at 03:00 UTC (background daemon thread)
│   └── sec_fetcher.py       # SEC EDGAR filing fetcher
├── schemas/                 # Pydantic v2 request/response models
│   ├── evidence.py          # EvidenceMetric, EvidenceModule, ModuleScore, DecisionOutput, DecisionRequest
│   ├── agent.py             # AgentRunRequest, AgentRunResponse, AgentLogRead, PipelineRunRead, etc.
│   ├── company.py           # CompanyCreate, CompanyRead, CompanyList
│   ├── competitor.py
│   ├── confidence_ledger.py
│   ├── dashboard.py         # DashboardSummary, AttentionDeal, AttentionList, ScoreRefreshResponse
│   ├── deal.py              # DealCreate, DealRead, DealUpdate, DealList
│   ├── deal_event.py
│   ├── diligence.py
│   ├── filing.py
│   ├── financials.py        # FinancialProfile (revenue, ebitda, margins, growth, leverage, fcf)
│   ├── intelligence.py      # IntelligenceHubResponse, IntelligenceQuestionSchema, EvidenceItemSchema, SourceConfidenceSchema
│   ├── investment_view.py
│   ├── lbo.py
│   ├── market_pulse.py
│   ├── memo.py
│   ├── overview.py
│   ├── reasoning_trace.py   # ReasoningTraceStep
│   ├── research.py
│   └── signals.py           # SignalBase, SignalCreate, SignalRead, SignalList, SignalDismiss
├── services/                # Business logic services
│   ├── change_summarizer.py
│   ├── confidence_ledger_builder.py
│   ├── data_provider.py     # Cache-first unified data provider (DB → YFinance live fetch)
│   ├── decision_engine.py   # Deterministic scoring: module scoring → weighted average → risk penalty → recommendation
│   ├── decision_readiness.py
│   ├── evidence_status_mapper.py
│   ├── intelligence_hub_writer.py  # HubWriter: clean API for agents to deposit evidence
│   └── investment_view_manager.py
├── alembic/                 # Database migrations
│   ├── env.py
│   └── versions/            # 7 migration files (initial schema, intelligence hub, deal settings, dashboard scoring, etc.)
├── pyproject.toml           # Dependencies, scripts (pe-seed, pe-ingest, pe-validate), tool configs
├── Dockerfile
├── README.md
└── seed_demo.py
```

---

## 4. API Layer (`api/`)

### 4.1 Application Factory (`api/main.py`)
- FastAPI app with title `"AI-Driven PE Investment Platform"`, version `0.1.0`
- CORS middleware (configurable via `ALLOWED_ORIGINS`)
- `RequestLoggingMiddleware` — logs every request with timestamp, method, path, status, duration
- `RateLimitMiddleware` — rate limiting
- Global exception handler: structured JSON, dev mode shows detail, prod hides traceback
- 15 routers mounted at application startup

### 4.2 Routers

| Router | Prefix | Key Endpoints |
|--------|--------|--------------|
| `sourcing` | `/sourcing` | Deal sourcing from thesis |
| `research` | `/research` | Industry research, filing research, web research |
| `financials` | `/financials` | Financial analysis, ratio computation |
| `lbo` | `/lbo` | LBO modeling, sensitivity analysis |
| `competitive` | `/competitive` | Competitive mapping, moat signals |
| `memo` | `/memo` | IC memo generation, PDF export |
| `pipeline` | `/pipeline` | Deal pipeline CRUD, full pipeline execution, resume runs |
| `agents` | `/agents` | Agent dispatch via Celery, run status polling, run logs |
| `intelligence` | `/intelligence` | Hub generation, questions, evidence, source confidence, decision engine, data refresh |
| `admin` | `/admin` | Admin operations |
| `companies` | `/companies` | Company CRUD + latest financials |
| `market_pulse` | `/market_pulse` | Market pulse settings |
| `dashboard` | `/dashboard` | Summary stats, attention list, score refresh, signals, global search |
| `overview` | `/overview` | High-level portfolio overview |

### 4.3 Authentication (`api/auth.py`)
- `HTTPBearer` security scheme
- **Development mode**: reads `X-User-Id` and `X-User-Role` headers
- Roles: `PARTNER`, `VP`, `ASSOCIATE`, `SYSTEM`
- Role-based permission methods (`can_view_raw_data`, `can_edit_views`, `can_finalize_views`, `can_override_weights`)

### 4.4 Middleware (`api/middleware.py`)
- `RequestLoggingMiddleware`: prints timestamp, method, path, status code, duration in ms

---

## 5. Database Layer (`db/`)

### 5.1 Models (`db/models.py`) — 25 Tables

**Core Entities:**
| Model | Table | Description |
|-------|-------|-------------|
| `Company` | `companies` | Investment universe (name, ticker, sector, geography, source) |
| `Financial` | `financials` | Annual snapshots with raw + computed fields (revenue, EBITDA, margins, leverage, FCF) |
| `Filing` | `filings` | SEC filings with pgvector embeddings (1536-dim) |
| `FilingChunk` | `filing_chunks` | Chunked text with per-chunk embeddings |
| `Deal` | `deal_pipeline` | Pipeline stages (sourcing → diligence → ic_ready → passed/rejected/closed) |
| `ICMemo` | `ic_memos` | Generated IC memos (sections JSON, word count, confidence) |
| `AgentLog` | `agent_logs` | Audit trail for every agent run (status, cost, tokens, errors) |
| `CompetitorCompany` | `competitor_companies` | Cached competitor data (Wikidata, GLEIF, Explorium) |

**Intelligence Hub:**
| Model | Table | Description |
|-------|-------|-------------|
| `IntelligenceHub` | `intelligence_hubs` | Per-company hub with status, executive briefing, decision output |
| `IntelligenceQuestion` | `intelligence_questions` | Q&A nodes with category, confidence, status |
| `EvidenceItem` | `evidence_items` | Linked evidence with supporting/contradictory flags, source, confidence |
| `SourceConfidence` | `source_confidence` | Per-source reliability tracking |

**Decision Platform:**
| Model | Table | Description |
|-------|-------|-------------|
| `DealScore` | `deal_scores` | Composite score with 4-dimension breakdown (financials, moat, market, risk) |
| `ScoreHistory` | `score_history` | Historical score changes for audit trail |
| `InvestmentView` | `investment_views` | Versioned, editable investment theses |
| `DiligenceItem` | `diligence_items` | Interactive checklist with priority, status, assignment |
| `ConfidenceLedger` | `confidence_ledgers` | Transparent score computation breakdown |
| `EvidenceConflict` | `evidence_conflicts` | Conflict detection between evidence items |
| `DealSettings` | `deal_settings` | Per-deal user-overridden weights |
| `Signal` | `signals` | Detected signals (earnings surprise, valuation gap, etc.) |
| `MarketPulseSetting` | `market_pulse_settings` | Configurable market indicators |
| `ActivityLog` | `activity_log` | General activity audit log |
| `DealEvent` | `deal_events` | Structured deal event log |

**Enums:** `CompanySource`, `DealStage`, `AgentStatus`, `EvidenceStatus`, `InvestmentViewStatus`, `DiligenceStatus`, `DiligencePriority`, `DealEventType`, `ActorType`, `ResolutionStatus`, `ConfidenceLevel`

### 5.2 CRUD (`db/crud.py`)
- 1,689 lines of comprehensive async CRUD
- Pattern: `create_*`, `get_*_by_id`, `list_*`, `update_*`, `delete_*`
- Special functions: `upsert_source_confidence`, `resolve_intelligence_question`, `truncate_all_tables`
- All operations use `async_session_factory()` context manager

### 5.3 Session (`db/session.py`)
- `create_async_engine` with `pool_pre_ping=True`
- `async_sessionmaker` with `expire_on_commit=False`, `autoflush=False`
- Pgbouncer support: strips `pgbouncer` query param, disables statement cache
- `get_session()` / `get_async_session()` — FastAPI dependency
- `init_db()` — dev helper to create all tables

### 5.4 Alembic Migrations (`alembic/versions/`)
- 7 migration files covering:
  1. Initial schema (`5e88d99b2da6`)
  2. Investment decision platform tables (`46417ac6cab7`)
  3. Intelligence hub schema (`a1b2c3d4e5f6`)
  4. Decision output in intelligence hubs (`b2c3d4e5f6g7`)
  5. Deal settings table (`215b1f04d130`)
  6. Dashboard scoring (`2026_07_01_dashboard_scoring`)
  7. Signals & market pulse (`2026_07_02_signals_market_pulse`)

---

## 6. Core Infrastructure (`core/`)

### 6.1 Configuration (`core/config.py`)
`Settings` class (Pydantic-Settings) reads from `.env`:
- `database_url`: PostgreSQL + asyncpg
- `redis_url`: Redis for Celery
- `openai_api_key`, `openai_chat_model` (gpt-4o), `openai_embedding_model` (text-embedding-3-small)
- `max_llm_tokens_per_run`: 4000
- `tavily_api_key`, `companies_house_api_key`, `explorium_api_key`
- `sec_user_agent`: required for SEC EDGAR
- `nightly_ingest_hour`: 3, `nightly_ingest_minute`: 0

### 6.2 LLM Client (`core/llm.py`)
- `LLMClient`: async OpenAI wrapper
- **Retry**: 3 attempts with exponential backoff for `RateLimitError`
- **Token counting**: tiktoken (o200k_base fallback)
- **Cost estimation**: $5/1M input tokens, $15/1M output tokens (GPT-4o pricing)
- **Budget enforcement**: raises `LLMBudgetExceeded` if response hits `max_tokens`
- **Structured output**: `chat_structured()` parses JSON into Pydantic models
- Temperature default: 0.3 (deterministic for finance)

### 6.3 Embeddings (`core/embeddings.py`)
- OpenAI `text-embedding-3-small` (1536-dim)
- Retry: 3 attempts with exponential backoff for `RateLimitError`
- Lazy client initialization

### 6.4 Vector Search (`core/vector_search.py`)
- `semantic_search(query, top_k=5)` over `filing_chunks`
- Uses pgvector `cosine_distance` operator (`<=>`)
- Returns `ChunkResult` with similarity score (1 - cosine_distance)

### 6.5 LBO Engine (`core/lbo_engine.py`)
- **Pure Python, deterministic, no LLM**
- `LBOInputs` dataclass: entry_ev, entry_ebitda, debt_pct, revenue_growth[], margin_expansion, exit_multiple, hold_years, interest_rate, amortization_rate
- `run_lbo(inputs)` → `LBOResult` with full debt schedule, EBITDA projection, exit equity, IRR, MOIC
- `sensitivity_grid(base_inputs, entry_range, exit_range)` → IRR matrix
- Validates: debt_pct < 0.85, hold_years ∈ {3,4,5,6}, exit_multiple > 0

### 6.6 Celery (`core/celery_app.py`)
- Broker & backend: Redis
- Task time limit: 10 min hard / 5 min soft
- Beat schedule: `nightly-ingestion` at 03:00 UTC (`crontab(hour=3, minute=0)`)
- Includes `core.tasks`

### 6.7 Tasks (`core/tasks.py`)
- `run_agent_task`: Celery task with 3 retries, exponential backoff (2^retry seconds)
- `AGENT_REGISTRY`: maps agent names to wrapper classes (dummy, sourcing, research, competitive, financials, lbo, memo, full)
- `_run_async` helper: handles both no-event-loop (worker) and event-loop-running (test/eager) contexts
- `run_nightly_ingestion_task`: Celery beat wrapper

### 6.8 Run Tracker (`core/run_tracker.py`)
- `start_run()` → UUID, creates `PENDING` AgentLog
- `update_status()` → transitions with optional output_data / duration_ms
- `log_error()` → appends error, sets `FAILED`
- `get_run()` / `list_runs()` → retrieval

### 6.9 Exceptions (`core/exceptions.py`)
- `LLMError` (base), `LLMBudgetExceeded`, `LLMRateLimitError`

---

## 7. Agent Pipeline (`agents/`)

### 7.1 Pipeline Flow (Orchestrator)
```
sourcing
    ↓
research + competitive  (parallel via asyncio.gather)
    ↓
financials
    ↓
lbo
    ↓
memo
    ↓
decision
    ↓
END
```

### 7.2 State Management (`agents/state.py`)
`DealState` is a `TypedDict` (total=False) carrying:
- `company_name`, `company_id`, `sector`, `gics_sector`, `gics_industry_group`
- `financials` (FinancialProfile), `competitive_map`, `competitors`, `competitor_profiles`
- `lbo_result`, `lbo_scenarios`, `lbo_results`, `lbo_sensitivity`, `lbo_interpretation`
- `memo_sections`, `memo_total_words`, `memo_avg_confidence`, `memo_id`
- `research`, `filing_research`, `web_research`, `risk_flags`, `interpretation`
- `thesis`, `sourcing_filters`, `candidates`, `ranked_candidates`
- `run_id`, `errors`
- Evidence modules: `financial_evidence_module`, `research_evidence_module`, etc.

Serialization: `deal_state_to_json()` / `deal_state_from_json()` with custom encoder for `FinancialProfile` and dataclasses.

### 7.3 Orchestrator (`agents/orchestrator.py`)
- 6-node LangGraph: `sourcing` → `research_competitive` → `financials` → `lbo` → `memo` → `decision`
- **Idempotency**: each node skips if its output already exists in state
- **Checkpointing**: after each node, updates deal stage and serializes state to `agent_log.output_data`
- **Resume**: `existing_run_id` loads checkpointed state, resumes from failed run
- **Stage mapping**: `sourcing` → `SOURCING`, `research_competitive` → `DILIGENCE`, `financials` → `DILIGENCE`, `lbo`/`memo` → `IC_READY`
- `run_full_pipeline(company_name_or_id, thesis, existing_run_id)` → final `DealState`

### 7.4 Financials Agent (`agents/financials/graph.py`)
5-node graph:
1. `load_data` → `DataProvider.get_financials(company_id)` (cache-first, YFinance fallback)
2. `compute_ratios` → pass-through (DataProvider already computes derived fields)
3. `flag_risks` → rule-based flags: leverage > 5x, declining revenue, margin < 10%, FCF yield < 2%
4. `interpret` → LLM narrates financial picture, writes to Intelligence Hub
5. `produce_evidence_module` → creates `EvidenceModule` with metrics: Revenue CAGR, EBITDA Margin, Cash Conversion, Leverage, ROIC, Forecast Revenue

### 7.5 Memo Agent (`agents/memo/graph.py`)
4-node graph:
1. `aggregate_context` → pulls all prior agent outputs into structured context dict
2. `write_sections` → 8 parallel LLM calls for: executive_summary, company_overview, industry_analysis, competitive_positioning, financial_analysis, lbo_model, risk_factors, investment_recommendation
3. `edit_pass` → checks for missing sections, placeholders, contradictions between exec summary and recommendation, financial consistency
4. `format_output` → computes total words, average confidence

Each section has a dedicated prompt in `agents/memo/prompts.py`.

### 7.6 Base Agent (`agents/base.py`)
- Abstract `BaseAgent` with `run()`, `start_run()`, `score_confidence()`, `log_run()`, `get_status()`
- All domain agents inherit from this

---

## 8. Services Layer (`services/`)

### 8.1 Decision Engine (`services/decision_engine.py`)
**Deterministic scoring — no LLM calls.**

**Module Weights:**
| Module | Weight |
|--------|--------|
| financial | 0.25 |
| research | 0.20 |
| competitive | 0.20 |
| market | 0.15 |
| valuation | 0.20 |

**Scoring Steps:**
1. Score each module 0-100 based on: confidence × 100, contradictory ratio penalty, warning penalty
2. Weighted investment score: Σ(module_score × weight)
3. Confidence score: weighted average of module confidences
4. Risk score: 20-80 based on contradictory evidence confidence
5. Recommendation logic:
   - Score ≥ 80 + Confidence ≥ 0.80 → **PROCEED** (Strong)
   - Score ≥ 65 + Confidence ≥ 0.70 → **CONDITIONAL** (Moderate)
   - Score ≥ 50 + Confidence ≥ 0.60 → **CONDITIONAL** (Weak)
   - Else → **PASS** (Weak)
6. Downgrade: critical gaps or high risk → downgrades one level
7. Optional LLM synthesis: one-paragraph executive summary with citations

**Output:** `DecisionOutput` with 10 sub-scores, evidence counts, strengths, concerns, critical gaps, sources

### 8.2 Data Provider (`services/data_provider.py`)
- **Cache-first strategy**: checks PostgreSQL for latest `Financial` record
- If stale/missing → fetches from YFinance via `ingest_company_financials()` → persists → re-queries cache
- Returns `FinancialProfile` regardless of source availability
- `force_refresh=True` bypasses cache

### 8.3 Intelligence Hub Writer (`services/intelligence_hub_writer.py`)
`HubWriter` class — clean API for agents to deposit evidence:
- `ensure_hub()` → get or create hub for company
- `add_question(category, question, answer, confidence)` → returns question_id
- `add_evidence(question_text, text, source, source_type, ...)` → linked to question
- `set_source_confidence(source_name, source_type)` → uses built-in confidence rules
- `add_remaining_diligence(question)` → open diligence items
- `write_hub_from_research_state()` → one-shot population from all agent outputs

**Source Confidence Baselines:**
| Source | Confidence | Rationale |
|--------|-----------|-----------|
| SEC EDGAR | 0.95 | Regulatory, audited |
| Yahoo Finance | 0.90 | Real-time market data |
| FMP | 0.88 | Structured financial data |
| Expert Call (GLG) | 0.85 | Domain expert |
| Internal Diligence | 0.80 | Management data |
| Competitive Agent | 0.80 | Multi-source enrichment |
| Financial Agent | 0.85 | Audited financials + deterministic ratios |
| Research Agent | 0.75 | Synthesized web + filings |
| LBO Agent | 0.70 | Model-based projection |
| Memo Agent | 0.65 | Synthesized prose |
| Tavily Web Search | 0.60 | May be promotional/outdated |

### 8.4 Other Services
- `confidence_ledger_builder.py` — transparent score breakdown
- `change_summarizer.py` — diff-based change detection
- `decision_readiness.py` — readiness checks before IC
- `evidence_status_mapper.py` — status mapping logic
- `investment_view_manager.py` — versioned thesis management

---

## 9. Data Ingestion (`ingest/`)

### 9.1 Financial Loader (`ingest/financial_loader.py`)
- Fetches annual income statement, balance sheet, cash flow from **yfinance**
- Maps row labels: `Total Revenue`, `EBITDA`, `Net Income`, `Total Debt`, `Cash`, `Operating Cash Flow`, `Capital Expenditure`
- Computes derived fields: `net_debt`, `fcf`, `ebitda_margin`, `net_debt_ebitda`, `revenue_growth`, `fcf_yield`
- Handles missing data: treats NaN, Inf, exact zero as `None`
- Persists each period to `financials` table
- Returns `FinancialProfile` for latest period
- CLI: `python -m ingest.financial_loader --ticker AAPL`

### 9.2 Unified Runner (`ingest/run.py`)
- `_run_ingestion(ticker, sources, create_if_missing)` → runs selected pipelines
- `run_bulk_ingestion(tickers)` → batch ingestion with summary stats
- Sources: `"sec"`, `"financials"`, `"all"`
- CLI: `python -m ingest.run --ticker AAPL --source all`

### 9.3 Scheduler (`ingest/scheduler.py`)
- APScheduler `AsyncIOScheduler` running in a **background daemon thread**
- Trigger: `CronTrigger(hour=3, minute=0)` (03:00 UTC nightly)
- Iterates all companies with tickers, runs `_run_ingestion(ticker, ["all"])`
- CLI: `python -m ingest.scheduler` (foreground blocking)

### 9.4 SEC Fetcher (`ingest/sec_fetcher.py`)
- Fetches SEC EDGAR filings
- Uses `sec_user_agent` from config (required by SEC)

### 9.5 Companies House (`ingest/companies_house.py`)
- UK Companies House API integration
- Requires `companies_house_api_key`

---

## 10. Two-Engine Architecture

### 10.1 Intelligence Hub (Question-Based)
Organizes evidence around **questions**, not documents.

**Per-company structure:**
- `IntelligenceHub` (status, executive_briefing, decision_output)
- `IntelligenceQuestion` (category, question, answer, confidence, status, sort_order)
- `EvidenceItem` (text, source, source_type, is_supporting, is_contradictory, confidence)
- `SourceConfidence` (source_name, source_type, confidence_score, rationale)

**Categories:** `financial`, `competitive`, `market`, `management`, `thesis`, `risk`, `valuation`, `supporting_evidence`, `contradictory_evidence`, `comparable_companies`, `remaining_diligence`, `expert_consensus`, `decision`

### 10.2 Decision Engine (Deterministic Scoring)
Synthesizes `EvidenceModule` objects into:
- **Investment Score**: 0-100 (weighted average of module scores minus risk penalties)
- **Confidence Score**: 0.0-1.0 (weighted average of module confidences)
- **Recommendation**: `PROCEED` / `CONDITIONAL` / `PASS`
- **Conviction**: `STRONG` / `MODERATE` / `WEAK`

**Score is N/A when confidence is `INSUFFICIENT`.**

---

## 11. Key Design Patterns

### 11.1 Async-First
- Every layer uses `async/await`
- SQLAlchemy 2.0 async ORM with `asyncpg`
- FastAPI async endpoints
- LangGraph `ainvoke()` for agent graphs

### 11.2 Idempotent Agents
- Each pipeline node checks if its output already exists in `DealState`
- If present, skips execution — safe to retry/resume

### 11.3 Checkpoint & Resume
- After each pipeline node, full state serialized to `agent_log.output_data`
- `existing_run_id` parameter loads checkpoint and resumes
- Deal stage updated automatically based on state contents

### 11.4 Cache-First Data
- `DataProvider` always checks PostgreSQL cache first
- Only fetches live data when cache is stale or missing
- `force_refresh` bypasses cache for explicit refreshes

### 11.5 Structured Evidence
- Every agent produces `EvidenceModule` with `EvidenceMetric` objects
- Each metric has: name, value, direction, confidence, is_supporting, is_contradictory, evidence_text, source, source_type
- Decision Engine consumes these structured objects — no free-text parsing

### 11.6 Source Attribution
- Every number traces back to a source ("Yahoo Finance", "SEC 10-K", "Research Agent")
- `source_type` enum: `filing`, `api`, `web`, `expert_call`, `internal`
- `source_url` links to raw source when available

---

## 12. Configuration & Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker/backend |
| `OPENAI_API_KEY` | `None` | LLM + embeddings |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | Primary LLM |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings |
| `MAX_LLM_TOKENS_PER_RUN` | `4000` | Token budget per LLM call |
| `TAVILY_API_KEY` | `None` | Web search |
| `COMPANIES_HOUSE_API_KEY` | `None` | UK company data |
| `EXPLORIUM_API_KEY` | `None` | Business firmographics (optional) |
| `SEC_USER_AGENT` | `PE Platform Bot (contact@peplatform.local)` | SEC EDGAR compliance |
| `ENVIRONMENT` | `dev` | dev/prod/test |
| `ALLOWED_ORIGINS` | `*` (dev) | CORS origins |
| `NIGHTLY_INGEST_HOUR` | `3` | Ingestion schedule hour |
| `NIGHTLY_INGEST_MINUTE` | `0` | Ingestion schedule minute |

---

## 13. Deployment

| Component | Target Platform |
|-----------|-----------------|
| Frontend | Vercel |
| Backend | Render / Railway / Fly |
| Database | PostgreSQL with pgvector extension |
| Task Queue | Redis (Celery broker) |
| Scheduled Tasks | Celery Beat (nightly ingestion) |

---

## 14. File Reference

| Key File | Path | Lines | Description |
|----------|------|-------|-------------|
| App Factory | `backend/api/main.py` | 111 | FastAPI entry point, router mounting |
| Models | `backend/db/models.py` | 797 | 25 SQLAlchemy models, all enums |
| CRUD | `backend/db/crud.py` | 1,689 | Async CRUD for all tables |
| Orchestrator | `backend/agents/orchestrator.py` | 603 | Master LangGraph pipeline |
| Decision Engine | `backend/services/decision_engine.py` | 312 | Deterministic scoring |
| Intelligence Hub | `backend/api/routers/intelligence.py` | 885 | Hub + decision endpoints |
| Pipeline Router | `backend/api/routers/pipeline.py` | 444 | Pipeline execution, agent dispatch |
| Financials Agent | `backend/agents/financials/graph.py` | 359 | 5-node financial analysis graph |
| Memo Agent | `backend/agents/memo/graph.py` | 405 | 4-node IC memo generation |
| Data Provider | `backend/services/data_provider.py` | 124 | Cache-first unified data fetcher |
| Hub Writer | `backend/services/intelligence_hub_writer.py` | 404 | Agent evidence deposit API |
| Financial Loader | `backend/ingest/financial_loader.py` | 329 | YFinance → DB ingestion |
| LLM Client | `backend/core/llm.py` | 165 | OpenAI wrapper with retry, cost tracking |
| LBO Engine | `backend/core/lbo_engine.py` | 219 | Pure-Python LBO model |
| Schemas | `backend/schemas/evidence.py` | 123 | EvidenceMetric, EvidenceModule, DecisionOutput |
| Config | `backend/core/config.py` | 56 | Pydantic-Settings |
| Tasks | `backend/core/tasks.py` | 253 | Celery agent tasks + registry |
| Session | `backend/db/session.py` | 76 | Async engine + session factory |

---

*End of Backend Architecture Overview*
