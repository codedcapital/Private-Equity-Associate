# Phase 1 — Data Layer Execution Plan

> **Goal:** Build foundational data infrastructure for the AI-Driven PE Investment Platform. All tables, CRUD operations, data pipelines, and embeddings must be production-ready before any AI agent work begins.
> **Timeline:** 2 weeks (Week 1: Environment + Schema; Week 2: Ingestion + Embeddings)

---

## Stage 1 — Project Scaffolding (Week 1 Day 1)
**Objective:** Create monorepo, Docker Compose, and dependency management.

| Subtask | Deliverable |
|---------|-------------|
| Monorepo structure | `/backend`, `/frontend`, `/agents`, `/data` directories |
| Docker Compose | `postgres` (15+pgvector), `redis` (7), `pgadmin` (optional) |
| Environment config | `.env` template with all API keys; `.env` in `.gitignore` |
| Python deps | `pyproject.toml` with uv/poetry; all core dependencies listed |

**Validation:** `docker compose up` runs clean. All 3 services reachable.

---

## Stage 2 — Database Schema (Week 1 Day 2)
**Objective:** SQLAlchemy ORM models + Alembic migrations.

| Subtask | Deliverable |
|---------|-------------|
| ORM models | 7 tables: `companies`, `financials`, `filings`, `filing_chunks`, `deal_pipeline`, `ic_memos`, `agent_logs` |
| Alembic setup | Initialized, autogenerate from models, `initial_schema` migration |
| pgvector integration | `embedding` columns on `filings` (1536-dim) and `filing_chunks` |

**Validation:** `\dt` in psql shows 7 tables. `\d filings` shows vector column.

---

## Stage 3 — Database Utilities (Week 1 Day 3)
**Objective:** Async session, CRUD, seeding, and tests.

| Subtask | Deliverable |
|---------|-------------|
| Async session | `db/session.py` — `create_async_engine` with `asyncpg` |
| CRUD layer | `db/crud.py` — `create_*`, `get_by_id`, `list_with_filters`, `update`, `delete` for each table |
| Seed script | `db/seed.py` — 4 dummy SaaS companies (BILL, MNDY, DOMO, BAND) |
| Tests | `pytest db/tests/ -v` passes for all 7 tables |

**Validation:** Seeded data queryable. All CRUD tests pass.

---

## Stage 4 — FastAPI Skeleton (Week 1 Day 4)
**Objective:** Router mounting, middleware, health endpoints.

| Subtask | Deliverable |
|---------|-------------|
| App init | `api/main.py` — CORS, exception handler, request logging middleware |
| Routers | Empty router files for all 7 agent routes + pipeline + admin |
| Health checks | `GET /health` on every router returns `{"status": "ok"}` |

**Validation:** `curl` to every `/agents/{name}/health` returns 200. `/docs` shows all routers.

---

## Stage 5 — Pydantic Schemas (Week 1 Day 5)
**Objective:** Typed request/response schemas for FastAPI OpenAPI docs.

| Subtask | Deliverable |
|---------|-------------|
| Company schemas | `CompanyCreate`, `CompanyRead`, `CompanyList` |
| Deal schemas | `DealStage` enum, `DealCreate`, `DealRead` |
| Agent schemas | `AgentStatus` enum, `AgentRunRequest`, `AgentRunResponse` |
| Financial schemas | `FinancialProfile` with all computed ratios |

**Validation:** `/docs` shows all schemas. No `Any` types in critical paths.

---

## Stage 6 — SEC EDGAR Integration (Week 2 Day 1)
**Objective:** Fetch and parse 10-K filings for tickers.

| Subtask | Deliverable |
|---------|-------------|
| SEC fetcher | `ingest/sec_fetcher.py` — `get_company_filings`, `download_filing`, `parse_filing_to_text` |
| Text cleanup | BeautifulSoup-based HTML/XML stripping |
| DB write | Parsed text stored in `filings` table with metadata |
| CLI test | `python -m ingest.sec_fetcher --ticker BILL` creates valid DB row |

**Validation:** Filing text is readable (not raw HTML). Row verified in DB.

---

## Stage 7 — Companies House Integration (Week 2 Day 2)
**Objective:** UK company data ingestion.

| Subtask | Deliverable |
|---------|-------------|
| CH client | `ingest/companies_house.py` — `search_company`, `get_company_profile`, `get_filing_history` |
| Schema mapping | CH fields → `companies` schema with `source = companies_house` |
| Test | UK company data appears in `companies` table |

**Validation:** `source` enum populated correctly. Data matches API response.

---

## Stage 8 — Financial Data Loader (Week 2 Day 3)
**Objective:** yfinance → `financials` table with derived ratios.

| Subtask | Deliverable |
|---------|-------------|
| yfinance loader | `ingest/financial_loader.py` — `load_financials(ticker, company_id)` |
| Derived fields | `net_debt`, `FCF`, `ebitda_margin`, `net_debt_ebitda`, `revenue_growth`, `fcf_yield` |
| Graceful handling | Missing data → `None` + warning log, never crash |
| CLI runner | `python -m ingest.run --ticker BILL --source sec,financials` |

**Validation:** Derived ratios match manual calculation. Both `companies` and `financials` populated.

---

## Stage 9 — Embedding Pipeline (Week 2 Day 4)
**Objective:** OpenAI text-embedding-3-small + pgvector chunking.

| Subtask | Deliverable |
|---------|-------------|
| Embedding generator | `core/embeddings.py` — `generate_embedding(text)` → 1536-dim vector |
| Chunking pipeline | `ingest/embedding_pipeline.py` — 512-token windows, 50-token overlap |
| Vector search | `core/vector_search.py` — `semantic_search(query, top_k)` via cosine similarity |
| Test | `semantic_search("revenue growth SaaS")` returns relevant chunks |

**Validation:** `filing_chunks` has chunks with valid embeddings. Cosine similarity returns relevant results.

---

## Stage 10 — Ingestion Validation + Scheduler (Week 2 Day 5)
**Objective:** Data integrity checks and nightly automation.

| Subtask | Deliverable |
|---------|-------------|
| Validation script | `validate_data.py` — counts + integrity checks (every company has ≥1 filing, every filing has embeddings, no `None` in critical fields) |
| Scheduler | `ingest/scheduler.py` — APScheduler nightly run |
| Admin endpoint | `GET /admin/ingest/status` — JSON with last run timestamp + counts |
| Documentation | `README.md` with Data Layer docs |

**Validation:** Scheduler runs clean. Admin endpoint returns accurate counts. All integrity checks pass.

---

## Execution Strategy

1. **Sequential foundation:** Days 1–5 (scaffolding → schema → utilities → FastAPI → schemas) are inherently sequential. Build these in order.
2. **Parallel ingestion:** Days 6–8 (SEC, Companies House, yfinance) can be developed in parallel once the DB schema is ready.
3. **Integration last:** Days 9–10 (embeddings + validation) depend on all prior work.

**Sub-agent delegation pattern:**
- `coder` agents for implementation (FastAPI, SQLAlchemy, ingestion scripts)
- `plan` agents for review (schema validation, API design review, test coverage)
- `explore` agents for research (SEC EDGAR API docs, Companies House API docs, yfinance quirks)

**Stage-gate validation:** After each stage, run the listed verification checks before proceeding.
