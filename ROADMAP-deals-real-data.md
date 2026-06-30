# Roadmap — Real Data on Deals Page & Pipeline Board

**Goal:** Remove all mock/fallback data from the deal detail page (`/deal/[id]`) and the
dashboard pipeline board, and back them with real data ingested for free from SEC EDGAR
(plus yfinance financials). No paid API keys required for the core data path.

---

## Current state (as of audit)

**Frontend**
- `frontend/src/lib/api.ts` — typed client; already calls the real FastAPI backend.
- `frontend/src/lib/data.ts` — hardcoded mock data (Meridian Logistics, etc.).
- `frontend/src/app/deal/[id]/deal-page.tsx` — fetches real data but **silently falls back
  to `lib/data.ts`** when the API returns empty/errors. Toasts "Showing mock data."
- `frontend/src/app/dashboard/dashboard-page.tsx` — same pattern via a `useFallback` flag;
  header even shows "demo data" vs "updated live."
- `generateStaticParams` in `deal/[id]/page.tsx` hardcodes ids `7` and `MRD-0142`.

**Backend**
- `/pipeline/deals` and `/pipeline/deals/{id}` are real, DB-backed (Postgres + pgvector).
- Agent endpoints exist for financials, LBO, competitive, research, memo.
- `backend/db/seed.py` inserts ~4 dummy **companies** but **no deals and no financials**.
- `backend/ingest/run.py` — real ingestion runner: `--ticker TICKER --source sec,financials,all`.
  Note: it **looks up an existing company by ticker** and fails if it isn't already in the DB.
- `backend/db/crud.py` has `create_deal()` (line ~312) but nothing currently calls it for
  real ingested companies.

**Key gaps**
1. No script creates real companies + deals from a ticker list (seed = dummy, no deals).
2. `ingest.run` requires the company row to pre-exist before it will ingest.
3. Frontend masks all of the above by falling back to mock data.

---

## Phase 1 — Real data into the backend

- [ ] Decide an initial ticker universe (e.g. real public small/mid-caps the fund would track).
- [ ] Add a script `backend/ingest/bootstrap_deals.py` that, for each ticker:
  - [ ] Upserts a `Company` (name, ticker, sector, geography, source=SEC) via `create_company`.
  - [ ] Runs `ingest_company_financials(ticker)` (yfinance) and `ingest_ticker(ticker, company_id)` (SEC).
  - [ ] Creates a `Deal` via `create_deal()` with a starting `stage` (e.g. `sourcing`).
- [ ] Confirm `financial_loader` populates revenue / ebitda / margins / net_debt for the metrics row.
- [ ] (Optional, needs OpenAI key) run `embedding_pipeline` so research/competitive tabs have content.

**Run commands (on your machine, backend env active):**
```bash
cd ~/Desktop/PE\ Associate/PE\ ASSOCIATE
docker compose up -d                      # Postgres + Redis
cd backend
alembic upgrade head
python -m ingest.bootstrap_deals          # new script (Phase 1)
# or per-ticker once company exists:
python -m ingest.run --ticker BILL --source all
```

---

## Phase 2 — De-mock the deal detail page

- [ ] In `deal-page.tsx`, remove the `lib/data.ts` fallback imports and every `?? fallback*`.
- [ ] Replace the "Backend unavailable → showing mock data" toast with a real error state.
- [ ] Per tab, render explicit states: **loading** (spinner already exists), **empty**
      ("No financials ingested yet"), **error** (retry button). Never silently substitute.
- [ ] Handle non-numeric ids (`MRD-0142`) properly instead of "showing mock data."
- [ ] Fix `generateStaticParams` to derive ids from real deals (or switch route to dynamic).

## Phase 3 — De-mock the pipeline board (dashboard)

- [ ] Remove `fallbackPipeline` import and the `useFallback` flag in `dashboard-page.tsx`.
- [ ] Map real `listDeals()` results into the kanban columns by `stage`.
- [ ] Empty board state ("No deals in pipeline — run ingestion to add companies").
- [ ] Update header line to drop the "demo data" wording.

## Phase 4 — Verify

- [ ] Backend up + ingestion run; `GET /pipeline/deals` returns real rows.
- [ ] `npm run build` / dev server: deal page and board show real companies, no mock names.
- [ ] Grep that `lib/data.ts` is no longer imported by deal/dashboard pages.
- [ ] Spot-check one deal end-to-end (metrics, financials tab) against the SEC/yfinance source.
- [ ] Decide whether to delete `lib/data.ts` or keep it only for Storybook/tests.

---

## Risks & notes
- SEC EDGAR is free but rate-limited and requires a descriptive `User-Agent` (already noted in
  `.env.example`); be gentle on bulk ingestion.
- Research / competitive / memo tabs depend on agents that need OpenAI + Tavily keys. Without
  them those tabs should show an honest empty state, not mock content.
- yfinance data quality varies; validate the financials mapping before trusting the metrics row.
- The frontend currently "fails open" to mock data — after this work it will "fail honest,"
  so a down backend will be visible. That's intended.
