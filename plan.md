# PE Dashboard — Phase 3 & 4 Implementation Plan

## Phase 1 & 2 Assessment

### Phase 1: Foundation — Data Infrastructure ✅
| Task | Status | Notes |
|------|--------|-------|
| 1.1 Activity/Audit Log | ✅ | `activity_log` table exists with deal_id, event_type, old_value, new_value, reason, metadata, created_at |
| 1.2 Score Versioning | ✅ | `score_history` table exists with snapshots + methodology_version |
| 1.3 Attention Algorithm | ✅ | Backend rule engine in `/dashboard/attention` and `/dashboard/summary` — score_change > 3, stage == ic_ready, LOW confidence |
| 1.4 Outstanding Questions | ⚠️ | `IntelligenceQuestion` exists but **missing `status` field** — needs `status` enum (pending, resolved, etc.) |
| 1.5 Dashboard Summary Endpoint | ✅ | `GET /dashboard/summary` returns active_deals, avg_score, ic_ready_count, attention_count, stage_breakdown |

### Phase 2: Core Dashboard — Layout & Attention ✅
| Task | Status | Notes |
|------|--------|-------|
| 2.1 New Dashboard Layout | ✅ | `dashboard-page.tsx` has grid layout: KPIs → Attention+Market → Pipeline → Search |
| 2.2 Attention Table | ✅ | `AttentionTable.tsx` with sortable columns: Company, Score, Change, Stage, Why, Updated |
| 2.3 Top KPI Cards | ✅ | `KpiCards.tsx` with Active Deals, Avg Score, IC Ready, Attention Required |
| 2.4 Pipeline Mini-Chart | ✅ | `PipelineMiniChart.tsx` horizontal bar chart |
| 2.5 Recently Updated Feed | ❌ | **NOT IMPLEMENTED** — needs `ActivityLog` API + frontend component |

---

## Phase 3: Intelligence — Signals & Market (Week 5-6)

### 3.1 Signal Taxonomy v1
**Goal:** Define 5-6 signal types, create `signals` table.

**Signal Types:**
- `earnings` — New earnings report, revenue beat/miss
- `insider_trading` — Significant insider buy/sell
- `macro_rate` — Interest rate changes, Fed policy
- `multiple_shift` — Sector multiple expansion/contraction
- `m_a` — M&A activity (acquisition, merger)
- `operational` — Management change, product launch, etc.

**Database Schema:**
```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deal_pipeline(id) ON DELETE CASCADE,
    signal_type VARCHAR(50) NOT NULL,  -- earnings, insider_trading, etc.
    direction VARCHAR(10),             -- up, down, neutral
    title TEXT NOT NULL,
    description TEXT,
    evidence_url TEXT,
    evidence_text TEXT,
    confidence VARCHAR(20) DEFAULT 'MEDIUM',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    metadata JSONB
);
CREATE INDEX idx_signals_deal_time ON signals(deal_id, detected_at DESC);
CREATE INDEX idx_signals_type ON signals(signal_type);
```

**Files:**
- Modify `backend/db/models.py` — add `Signal` model
- Create `backend/alembic/versions/2026_07_02_signals.py` — migration
- Modify `backend/schemas/__init__.py` — export Signal schemas
- Create `backend/schemas/signals.py` — Pydantic schemas
- Modify `backend/db/crud.py` — add Signal CRUD operations

### 3.2 Signal Detection (Rule-based)
**Goal:** v1 uses deterministic rules — no LLM needed.

**Rules:**
- If new `ScoreHistory` entry with `event_type == 'earnings'` → create `earnings` signal
- If `score_change >= 5` in `ScoreHistory` → create `earnings` or `operational` signal
- If `score_change <= -10` → create `earnings` signal (negative)
- If `Deal.stage` changes to `ic_ready` → create `operational` signal
- If new `ActivityLog` with `event_type == 'score_changed'` → create signal

**Implementation:** Hook into `ScoringEngine.compute_score()` after score is computed. If score changed significantly, auto-create signal.

**Files:**
- Modify `backend/services/scoring_engine.py` — add `create_signal()` call after score changes
- Modify `backend/services/signal_detector.py` — new module for signal detection rules
- Modify `backend/api/routers/dashboard.py` — add signal endpoints

### 3.3 Market Pulse Panel (Dynamic)
**Goal:** Replace static market data with admin-configurable API.

**Database:** Add `market_pulse_settings` table or reuse a simple config approach.
**Simpler approach:** Store in `market_data` JSON config table, updated manually via API.

Actually, for MVP: Store in a simple `market_pulse` table with key-value pairs. Admin can update via settings page.

**Files:**
- Modify `backend/db/models.py` — add `MarketPulseSetting` model
- Create `backend/api/routers/market.py` — GET/PUT market pulse data
- Modify `frontend/src/components/dashboard/MarketPulse.tsx` — fetch from API
- Modify `frontend/src/lib/api.ts` — add `getMarketPulse()`, `updateMarketPulse()`

### 3.4 Latest Signals Feed
**Goal:** Query signals table, display with icon + text + evidence link + timestamp.

**API Endpoint:** `GET /dashboard/signals` — returns latest signals for all deals, paginated

**Frontend Component:** `frontend/src/components/dashboard/SignalsFeed.tsx`

**Layout:** Goes in the bottom-left of the two-column split (below Market Pulse or beside it).

### 3.5 Industry Watch
**Goal:** Group pipeline companies by sector, compute median EV/Revenue, EV/EBITDA from own data.

**API Endpoint:** `GET /dashboard/industry` — returns sector breakdown with median metrics

**Frontend Component:** `frontend/src/components/dashboard/IndustryWatch.tsx`

**Layout:** Could be a small panel in the dashboard or part of the signals section.

---

## Phase 4: Workflow — Questions & Actions (Week 7-8)

### 4.1 Outstanding Questions Widget
**Goal:** Checkboxes, add/remove, assign to deal, mark complete. Syncs with `IntelligenceQuestion`.

**Database Changes:**
- Add `status` field to `IntelligenceQuestion` (VARCHAR(20), default 'pending')
- Values: `pending`, `in_progress`, `resolved`, `blocked`
- Add `resolved_at` timestamp

**API Endpoints:**
- `GET /dashboard/questions?status=pending` — get outstanding questions across all deals
- `PATCH /intelligence/questions/{question_id}` — update status, answer

**Frontend Component:** `frontend/src/components/dashboard/OutstandingQuestions.tsx`

### 4.2 Daily Activity Summary
**Goal:** "Today: Financials refreshed 14, Research updated 8, News analyzed 124, Models rebuilt 6"

**API Endpoint:** `GET /dashboard/activity-summary` — aggregates from `agent_logs` last 24h

**Implementation:** Count `agent_logs` by `agent_name` where `created_at >= today - 1 day`

**Frontend Component:** `frontend/src/components/dashboard/DailyActivity.tsx`

### 4.3 Recently Updated Feed (Phase 2 Missing Piece)
**Goal:** Query `activity_log` for last 24h, show deal name + what changed + link.

**API Endpoint:** `GET /dashboard/recently-updated` — returns last 24h activity logs with deal names

**Frontend Component:** `frontend/src/components/dashboard/RecentlyUpdated.tsx`

### 4.4 Global Search (Command-K Style)
**Goal:** Search across companies, deals, research notes, memos.

**API Endpoint:** `GET /dashboard/search?q={query}` — returns mixed results

**Frontend Component:** `frontend/src/components/dashboard/GlobalSearch.tsx` — modal with Command-K shortcut

### 4.5 "What's Changed" Notification Badge
**Goal:** Badge or toast when new signals arrive for watched deals.

**Implementation:** In `dashboard-page.tsx`, poll `/dashboard/signals?since={lastCheck}` every 30s. If new signals exist, show toast badge.

---

## Execution Order

### Stage 1: Backend Foundation (Parallel)
- **Agent A:** Signal model + migration + CRUD + schema
- **Agent B:** Question status field + migration + CRUD update
- **Agent C:** Market Pulse settings model + API + migration

### Stage 2: Backend API (Sequential on Stage 1)
- **Agent D:** Dashboard router additions (signals, recently-updated, activity-summary, industry, search)
- **Agent E:** Signal detection engine (hook into scoring)

### Stage 3: Frontend Components (Parallel on Stage 2)
- **Agent F:** SignalsFeed + MarketPulse dynamic + IndustryWatch
- **Agent G:** OutstandingQuestions + DailyActivity + RecentlyUpdated
- **Agent H:** GlobalSearch + dashboard layout update + notification badge

### Stage 4: Integration & Polish
- Main agent: Wire everything together, test, fix issues

---

## API Contract Summary

### New Endpoints

```
GET  /dashboard/signals              → { signals: SignalRead[] }
GET  /dashboard/signals?deal_id=1   → { signals: SignalRead[] }
POST /dashboard/signals/{id}/dismiss → { success: true }

GET  /dashboard/recently-updated     → { items: ActivityLogRead[] }
GET  /dashboard/activity-summary    → { counts: { financials: 14, research: 8, ... } }
GET  /dashboard/industry             → { sectors: SectorSummary[] }
GET  /dashboard/search?q=appfolio   → { results: SearchResult[] }

GET  /market-pulse                   → { treasuryYield, softwareEvRevenue, sp500Change, fedOutlook, lastUpdated }
PUT  /market-pulse                   → { ... } (admin)

GET  /dashboard/questions?status=pending → { questions: QuestionWithDeal[] }
PATCH /intelligence/questions/{id}   → { ... } (update status)
```

### New Schemas

```python
class SignalBase(BaseModel):
    signal_type: str  # earnings, insider_trading, macro_rate, multiple_shift, m_a, operational
    direction: str | None  # up, down, neutral
    title: str
    description: str | None
    evidence_url: str | None
    confidence: str = "MEDIUM"

class SignalRead(SignalBase):
    id: int
    deal_id: int
    company_name: str
    detected_at: str
    resolved_at: str | None
    is_dismissed: bool

class MarketPulseData(BaseModel):
    treasury_yield: str
    treasury_direction: str
    software_ev_revenue: str
    sp500_change: str
    fed_outlook: str
    last_updated: str

class ActivitySummary(BaseModel):
    financials_refreshed: int
    research_updated: int
    news_analyzed: int
    models_rebuilt: int
    total_runs: int

class RecentlyUpdatedItem(BaseModel):
    deal_id: int
    company_name: str
    event_type: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    created_at: str

class OutstandingQuestion(BaseModel):
    id: int
    deal_id: int
    company_name: str
    category: str
    question: str
    answer: str | None
    status: str  # pending, in_progress, resolved, blocked
    created_at: str

class SearchResult(BaseModel):
    type: str  # company, deal, memo, research
    id: int | str
    title: str
    subtitle: str | None
    url: str
```

---

## File Checklist

### Backend Files to Create/Modify
- [ ] `backend/db/models.py` — add Signal, MarketPulseSetting models; add status to IntelligenceQuestion
- [ ] `backend/alembic/versions/2026_07_02_signals_and_market_pulse.py` — migration
- [ ] `backend/db/crud.py` — add Signal CRUD, MarketPulse CRUD, update Question CRUD
- [ ] `backend/schemas/signals.py` — new schema file
- [ ] `backend/schemas/market_pulse.py` — new schema file
- [ ] `backend/schemas/__init__.py` — export new schemas
- [ ] `backend/services/signal_detector.py` — new signal detection engine
- [ ] `backend/services/scoring_engine.py` — hook signal creation after score changes
- [ ] `backend/api/routers/dashboard.py` — add new endpoints (signals, recently-updated, activity-summary, industry, search)
- [ ] `backend/api/routers/market.py` — new router for market pulse (or add to dashboard)
- [ ] `backend/api/routers/intelligence.py` — add question status update endpoint
- [ ] `backend/api/main.py` — register new routers

### Frontend Files to Create/Modify
- [ ] `frontend/src/lib/api.ts` — add new API functions
- [ ] `frontend/src/components/dashboard/SignalsFeed.tsx` — new
- [ ] `frontend/src/components/dashboard/IndustryWatch.tsx` — new
- [ ] `frontend/src/components/dashboard/RecentlyUpdated.tsx` — new
- [ ] `frontend/src/components/dashboard/OutstandingQuestions.tsx` — new
- [ ] `frontend/src/components/dashboard/DailyActivity.tsx` — new
- [ ] `frontend/src/components/dashboard/GlobalSearch.tsx` — new
- [ ] `frontend/src/components/dashboard/MarketPulse.tsx` — modify to fetch from API
- [ ] `frontend/src/app/dashboard/dashboard-page.tsx` — update layout with all new components
- [ ] `frontend/src/app/layout.tsx` — add Command-K listener if needed
