# Opportunity Discovery — Complete Implementation Roadmap

> **Status:** Architecture Complete | Ready for Implementation  
> **Scope:** Full-stack rewrite of `/sourcing` → `/opportunity-discovery`  
> **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL + Celery  
> **Frontend:** Next.js 16 + React 19 + Tailwind CSS v4 + ky

---

## 1. Executive Summary

The current `/sourcing` page is a **prompt-driven agent** (textarea → `POST /agents/sourcing` → results table). The backend, however, is already a **continuous portfolio intelligence platform** with:

- Intelligence Hub (`intelligence_hub_writer.py`)
- Decision Engine (`decision_engine.py`)
- Scoring Engine (`scoring_engine.py`)
- Confidence Ledger (`confidence_ledger_builder.py`)
- Change Summarizer (`change_summarizer.py`)
- Decision Readiness (`decision_readiness.py`)
- Investment View Manager (`investment_view_manager.py`)
- Signals engine (`Signal` model + `ScoringEngine`)
- Market Pulse (`market_pulse.py`)

The Opportunity Discovery page will be the **natural frontend expression** of these backend systems — a live, persistent dashboard that continuously monitors the investment universe against a configured strategy.

---

## 2. The Problem We're Solving

| Current | Target |
|---------|--------|
| "Find me companies" (on-demand agent) | "Continuously monitor the market for companies that fit our strategy" |
| Prompt box every time | Living investment mandate (persistent) |
| Black-box AI recommendations | Transparent funnel with evidence |
| Static results table | Dynamic signals + confidence trajectory |
| "Sourcing" | "Opportunity Discovery" |

---

## 3. Feature Selection (Chosen from Brainstorming)

### Tier 1 — Core MVP (Must Ship)
These are the features that make the product category-defining. Every other feature is secondary.

1. **Rename & Navigation Restructure** — `/sourcing` → `/opportunity-discovery`, sidebar update
2. **Living Investment Strategy** — Persistent, editable mandate (not a prompt box)
3. **Market Coverage Funnel** — Universe → Financial Match → Strategic Match → High Conviction (transparent counts)
4. **Highest Conviction Opportunities Table** — Company | Fit | Confidence | Why | Trend
5. **Discovery Summary** — Click a company → see "Why surfaced?" with evidence before opening full workspace
6. **Signals Panel** — New opportunities, revenue acceleration, valuation compression, M&A, etc.
7. **Strategy Coverage Progress Bars** — Research velocity, coverage completeness per strategy
8. **Daily Morning Briefing** — "New Opportunities Today" powered by Change Summarizer + Signals
9. **Transparency Layer** — "Why only 8 passed?" → expandable drill-down with actual company lists

### Tier 2 — High Differentiation (Ship in Phase 2)
10. **Confidence Trajectory** — Sparkline showing score change over time (ScoreHistory)
11. **Evidence Gaps** — "Near misses" with missing data highlighted
12. **Emerging Themes** — AI Infrastructure, Defense Software, etc. powered by Market Pulse

### Tier 3 — Polish (Ship in Phase 3)
13. **Opportunity Watchlist as Strategy Tabs** — Switch entire page context by strategy
14. **Decision Readiness Filter** — Ready for Diligence / Needs Research / Monitor

---

## 4. Backend Architecture

### 4.1 New Data Model: `InvestmentStrategy`

```python
# db/models.py
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
        }
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

**Rationale:** JSON `criteria` allows the strategy to evolve without schema migrations. The UI will define the schema, and the backend will interpret it.

### 4.2 New Service: `UniverseScreenEngine`

```python
# services/universe_screen.py
class UniverseScreenEngine:
    """
    Screens the entire company universe against an InvestmentStrategy.

    Returns structured buckets:
      - universe: all companies
      - financial_match: passes financial criteria (revenue, EBITDA, margin, growth, leverage)
      - strategic_match: has DealScore + ConfidenceLedger (pipeline companies with intelligence)
      - high_conviction: strategic_match with investment_score >= 80 and confidence >= 0.80
      - failed_screen: categorized by why they failed (valuation, leverage, growth, market_structure)

    For companies without deals, computes a "financial fit score" on the fly from Financial data.
    For companies with deals, uses existing DealScore + ConfidenceLedger.
    """
```

**Key insight:** The existing `ScoringEngine`, `ConfidenceLedgerBuilder`, and `DecisionEngine` all operate on **deals** (companies already in the pipeline). The `UniverseScreenEngine` extends this to the **entire universe** by:
1. Running SQL-based financial screening (fast, no LLM)
2. For companies already in the pipeline, surfacing their existing scores
3. For new companies, computing a deterministic financial fit score (same logic as `ScoringEngine` but without requiring a Deal)

### 4.3 New Service: `OpportunityDiscoveryService`

```python
# services/opportunity_discovery.py
class OpportunityDiscoveryService:
    """
    Orchestrates all data needed for the Opportunity Discovery page.
    Combines:
      - UniverseScreenEngine (funnel counts)
      - Signal model (recent signals)
      - ScoreHistory (confidence trajectories)
      - ChangeSummarizer (daily briefing)
      - MarketPulseSetting (emerging themes)
    """
```

### 4.4 New Pydantic Schemas

```python
# schemas/opportunity_discovery.py

class StrategyCriteria(BaseModel):
    sectors: list[str] = []
    geographies: list[str] = []
    business_models: list[str] = []
    ownership_types: list[str] = []
    min_revenue: float | None = None
    max_revenue: float | None = None
    min_ebitda: float | None = None
    max_ebitda: float | None = None
    min_ebitda_margin: float | None = None
    min_revenue_growth: float | None = None
    max_net_debt_ebitda: float | None = None
    min_fcf_yield: float | None = None
    customer_concentration: str | None = None
    product_type: str | None = None

class InvestmentStrategyRead(BaseModel):
    id: int
    name: str
    is_active: bool
    is_default: bool
    criteria: StrategyCriteria
    created_at: datetime
    updated_at: datetime

class InvestmentStrategyUpdate(BaseModel):
    name: str | None = None
    criteria: StrategyCriteria | None = None
    is_active: bool | None = None
    is_default: bool | None = None

class CoverageMetrics(BaseModel):
    universe: int
    financial_match: int
    strategic_match: int
    high_conviction: int
    breakdown: dict[str, int]  # {"failed_valuation": 118, ...}

class OpportunityItem(BaseModel):
    company_id: int
    company_name: str
    ticker: str | None
    sector: str | None
    fit_score: int  # 0-100
    confidence_score: float  # 0-1
    recommendation: str | None  # PROCEED, CONDITIONAL, PASS
    trend: int | None  # Change from last week
    why: str  # Human-readable reason
    evidence_coverage: int | None  # 0-100
    has_deal: bool
    deal_id: int | None
    financial_snapshot: dict | None

class DiscoverySummary(BaseModel):
    company_id: int
    company_name: str
    ticker: str | None
    fit_score: int
    confidence_score: float
    why_surfaced: list[str]  # ["Revenue CAGR 18%", "EBITDA 28%", ...]
    matches: list[dict]  # [{"criterion": "Vertical SaaS", "status": "pass"}, ...]
    concerns: list[str]
    evidence_coverage: int
    recommendation: str
    has_deal: bool
    deal_id: int | None

class DailyBriefingItem(BaseModel):
    type: str  # "new_opportunity", "exited", "score_increased", "earnings", "ma"
    company_id: int
    company_name: str
    description: str
    direction: str | None  # "up", "down"
    delta: int | None

class DailyBriefing(BaseModel):
    date: str
    new_opportunities: int
    exited_opportunities: int
    scores_increased: int
    scores_decreased: int
    earnings_reported: int
    ma_transactions: int
    items: list[DailyBriefingItem]

class FailedScreenCompany(BaseModel):
    company_id: int
    company_name: str
    ticker: str | None
    sector: str | None
    financial_snapshot: dict | None
    failure_reason: str
    failure_detail: str

class SignalFeedItem(BaseModel):
    id: int
    deal_id: int | None
    company_id: int
    company_name: str
    signal_type: str
    direction: str | None
    title: str
    description: str | None
    confidence: str
    detected_at: str

class ThemeItem(BaseModel):
    name: str
    company_count: int
    avg_score: int
    trend: str  # "rising", "stable", "falling"
    description: str
```

### 4.5 New API Router: `/opportunity-discovery`

```python
# api/routers/opportunity_discovery.py
router = APIRouter(prefix="/opportunity-discovery", tags=["opportunity-discovery"])

@router.get("/strategy", response_model=InvestmentStrategyRead)
async def get_active_strategy() -> InvestmentStrategyRead:
    """Get the currently active investment strategy."""

@router.put("/strategy", response_model=InvestmentStrategyRead)
async def update_strategy(request: InvestmentStrategyUpdate) -> InvestmentStrategyRead:
    """Update the active investment strategy."""

@router.get("/coverage", response_model=CoverageMetrics)
async def get_coverage_metrics(strategy_id: int | None = None) -> CoverageMetrics:
    """Get funnel counts: universe → financial → strategic → high conviction."""

@router.get("/opportunities", response_model=list[OpportunityItem])
async def list_opportunities(
    strategy_id: int | None = None,
    min_score: int = 70,
    limit: int = 50,
    offset: int = 0,
) -> list[OpportunityItem]:
    """List highest conviction opportunities."""

@router.get("/opportunities/{company_id}", response_model=DiscoverySummary)
async def get_discovery_summary(company_id: int) -> DiscoverySummary:
    """Get discovery summary for a specific company (before opening workspace)."""

@router.get("/signals", response_model=list[SignalFeedItem])
async def get_signal_feed(
    strategy_id: int | None = None,
    limit: int = 20,
    signal_type: str | None = None,
) -> list[SignalFeedItem]:
    """Get recent signals across the universe or strategy."""

@router.get("/daily-briefing", response_model=DailyBriefing)
async def get_daily_briefing(strategy_id: int | None = None) -> DailyBriefing:
    """Get morning briefing: what changed since yesterday."""

@router.get("/failed-screen/{reason}", response_model=list[FailedScreenCompany])
async def get_failed_screen_companies(
    reason: str,  # "valuation", "leverage", "growth", "market_structure"
    strategy_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FailedScreenCompany]:
    """Get companies that failed a specific screen, with details."""

@router.get("/themes", response_model=list[ThemeItem])
async def get_emerging_themes() -> list[ThemeItem]:
    """Get emerging investment themes from Market Pulse + universe data."""

@router.get("/strategy-coverage", response_model=dict)
async def get_strategy_coverage(strategy_id: int | None = None) -> dict:
    """Get research velocity and coverage completeness for the active strategy."""
```

### 4.6 Backend File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `db/models.py` | **Add** | `InvestmentStrategy` model |
| `db/crud.py` | **Add** | CRUD operations for `InvestmentStrategy` |
| `alembic/versions/` | **Add** | Migration for `investment_strategies` table |
| `services/universe_screen.py` | **Create** | SQL-based universe screening engine |
| `services/opportunity_discovery.py` | **Create** | Orchestration service for page data |
| `schemas/opportunity_discovery.py` | **Create** | All Pydantic request/response schemas |
| `api/routers/opportunity_discovery.py` | **Create** | New FastAPI router with 8 endpoints |
| `api/main.py` | **Edit** | Register new router |
| `db/seed.py` | **Edit** | Seed default strategy on first run |

---

## 5. Frontend Architecture

### 5.1 New Route Structure

```
frontend/src/app/
├── opportunity-discovery/
│   ├── page.tsx                    # Server Component (redirects /sourcing)
│   └── opportunity-discovery-page.tsx  # Client Component (main page)
├── sourcing/                        # Keep for backward compatibility
│   ├── page.tsx                     # Redirect → /opportunity-discovery
│   └── sourcing-page.tsx            # Keep as archive (or delete)
```

### 5.2 New Component Directory

```
frontend/src/components/opportunity-discovery/
├── index.tsx                        # Re-exports
├── investment-strategy-panel.tsx    # Section 1: Living mandate
├── market-coverage-panel.tsx        # Section 2: Funnel counts
├── opportunities-table.tsx          # Section 3: Highest conviction table
├── opportunity-row.tsx              # Individual row with expand
├── discovery-summary-card.tsx       # Expanded row content
├── signals-panel.tsx                # Section 4: Signal feed
├── signal-item.tsx                  # Individual signal
├── strategy-coverage-panel.tsx      # Section 6: Progress bars
├── daily-briefing.tsx               # Section 8: Morning briefing
├── themes-panel.tsx                 # Section 7: Emerging themes
├── failed-screen-drawer.tsx         # Transparency layer drill-down
├── confidence-sparkline.tsx         # Tiny trend chart
├── strategy-editor-modal.tsx        # Edit Strategy modal
└── empty-strategy-state.tsx         # Before strategy is configured
```

### 5.3 New Hooks

```
frontend/src/hooks/
├── use-opportunity-discovery.ts     # Main data fetch for the page
├── use-investment-strategy.ts       # Strategy CRUD + editing
├── use-signals-feed.ts              # Signal feed with polling
├── use-daily-briefing.ts            # Morning briefing
├── use-failed-screen.ts             # Failed screen drill-down
└── use-discovery-summary.ts         # Discovery summary for a company
```

### 5.4 API Layer Updates

```typescript
// frontend/src/lib/api.ts

// Add to existing api.ts:
export interface InvestmentStrategy {
  id: number;
  name: string;
  is_active: boolean;
  is_default: boolean;
  criteria: StrategyCriteria;
  created_at: string;
  updated_at: string;
}

export interface StrategyCriteria {
  sectors: string[];
  geographies: string[];
  business_models: string[];
  ownership_types: string[];
  min_revenue: number | null;
  max_revenue: number | null;
  min_ebitda: number | null;
  max_ebitda: number | null;
  min_ebitda_margin: number | null;
  min_revenue_growth: number | null;
  max_net_debt_ebitda: number | null;
  min_fcf_yield: number | null;
  customer_concentration: string | null;
  product_type: string | null;
}

export interface CoverageMetrics {
  universe: number;
  financial_match: number;
  strategic_match: number;
  high_conviction: number;
  breakdown: Record<string, number>;
}

export interface OpportunityItem {
  company_id: number;
  company_name: string;
  ticker: string | null;
  sector: string | null;
  fit_score: number;
  confidence_score: number;
  recommendation: string | null;
  trend: number | null;
  why: string;
  evidence_coverage: number | null;
  has_deal: boolean;
  deal_id: number | null;
  financial_snapshot: Record<string, any> | null;
}

export interface DiscoverySummary {
  company_id: number;
  company_name: string;
  ticker: string | null;
  fit_score: number;
  confidence_score: number;
  why_surfaced: string[];
  matches: { criterion: string; status: string }[];
  concerns: string[];
  evidence_coverage: number;
  recommendation: string;
  has_deal: boolean;
  deal_id: number | null;
}

export interface DailyBriefing {
  date: string;
  new_opportunities: number;
  exited_opportunities: number;
  scores_increased: number;
  scores_decreased: number;
  earnings_reported: number;
  ma_transactions: number;
  items: DailyBriefingItem[];
}

export interface DailyBriefingItem {
  type: string;
  company_id: number;
  company_name: string;
  description: string;
  direction: string | null;
  delta: number | null;
}

export interface FailedScreenCompany {
  company_id: number;
  company_name: string;
  ticker: string | null;
  sector: string | null;
  financial_snapshot: Record<string, any> | null;
  failure_reason: string;
  failure_detail: string;
}

export interface SignalFeedItem {
  id: number;
  deal_id: number | null;
  company_id: number;
  company_name: string;
  signal_type: string;
  direction: string | null;
  title: string;
  description: string | null;
  confidence: string;
  detected_at: string;
}

export interface ThemeItem {
  name: string;
  company_count: number;
  avg_score: number;
  trend: string;
  description: string;
}

// API functions:
export async function getActiveStrategy(): Promise<InvestmentStrategy> {
  return apiCall<InvestmentStrategy>("/opportunity-discovery/strategy");
}

export async function updateStrategy(payload: Partial<InvestmentStrategy>): Promise<InvestmentStrategy> {
  return apiCall<InvestmentStrategy>("/opportunity-discovery/strategy", { method: "PUT", json: payload });
}

export async function getCoverageMetrics(): Promise<CoverageMetrics> {
  return apiCall<CoverageMetrics>("/opportunity-discovery/coverage");
}

export async function getOpportunities(params?: { min_score?: number; limit?: number; offset?: number }): Promise<OpportunityItem[]> {
  return apiCall<OpportunityItem[]>(`/opportunity-discovery/opportunities?${new URLSearchParams(params as any)}`);
}

export async function getDiscoverySummary(companyId: number): Promise<DiscoverySummary> {
  return apiCall<DiscoverySummary>(`/opportunity-discovery/opportunities/${companyId}`);
}

export async function getSignalFeed(params?: { limit?: number; signal_type?: string }): Promise<SignalFeedItem[]> {
  return apiCall<SignalFeedItem[]>(`/opportunity-discovery/signals?${new URLSearchParams(params as any)}`);
}

export async function getDailyBriefing(): Promise<DailyBriefing> {
  return apiCall<DailyBriefing>("/opportunity-discovery/daily-briefing");
}

export async function getFailedScreenCompanies(reason: string, params?: { limit?: number; offset?: number }): Promise<FailedScreenCompany[]> {
  return apiCall<FailedScreenCompany[]>(`/opportunity-discovery/failed-screen/${reason}?${new URLSearchParams(params as any)}`);
}

export async function getEmergingThemes(): Promise<ThemeItem[]> {
  return apiCall<ThemeItem[]>("/opportunity-discovery/themes");
}

export async function getStrategyCoverage(): Promise<any> {
  return apiCall<any>("/opportunity-discovery/strategy-coverage");
}
```

### 5.5 Sidebar & Navigation Update

```typescript
// frontend/src/components/sidebar.tsx
const navItems = [
  { id: "dashboard", label: "Dashboard", href: "/dashboard" },
  { id: "pipeline", label: "Pipeline", href: "/pipeline" },
  { id: "deals", label: "Deals", href: "/dashboard" },
  { id: "opportunity-discovery", label: "Opportunity Discovery", href: "/opportunity-discovery" },
  // OLD: { id: "sourcing", label: "Sourcing", href: "/sourcing" },
  { id: "research", label: "Research", href: "/research" },
  { id: "settings", label: "Settings", href: "/settings" },
];
```

Add redirect in `/sourcing/page.tsx`:
```typescript
import { redirect } from "next/navigation";
export default function SourcingRedirectPage() {
  redirect("/opportunity-discovery");
}
```

### 5.6 Page Layout: 7 Sections

```tsx
// opportunity-discovery-page.tsx
export default function OpportunityDiscoveryPage() {
  return (
    <div className="max-w-[1200px] px-5 pt-6 pb-[60px]">
      {/* Section 1: Investment Strategy */}
      <InvestmentStrategyPanel />

      {/* Section 2: Market Coverage */}
      <MarketCoveragePanel />

      {/* Section 3: Highest Conviction Opportunities */}
      <OpportunitiesTable />

      {/* Section 4: New Opportunities (Signals) */}
      <SignalsPanel />

      {/* Section 5: Daily Briefing */}
      <DailyBriefing />

      {/* Section 6: Strategy Coverage */}
      <StrategyCoveragePanel />

      {/* Section 7: Emerging Themes */}
      <ThemesPanel />
    </div>
  );
}
```

---

## 6. Implementation Phases

### Phase 1: Backend Foundation (No Frontend)
**Goal:** Build the data layer and API endpoints with zero frontend changes.

| Step | Task | Files | Est. Time |
|------|------|-------|-----------|
| 1.1 | Add `InvestmentStrategy` model to `db/models.py` | `db/models.py` | 30 min |
| 1.2 | Add CRUD operations in `db/crud.py` | `db/crud.py` | 30 min |
| 1.3 | Create Alembic migration | `alembic/versions/` | 15 min |
| 1.4 | Create `schemas/opportunity_discovery.py` | New file | 45 min |
| 1.5 | Build `UniverseScreenEngine` | `services/universe_screen.py` | 3 hours |
| 1.6 | Build `OpportunityDiscoveryService` | `services/opportunity_discovery.py` | 2 hours |
| 1.7 | Create FastAPI router with all 8 endpoints | `api/routers/opportunity_discovery.py` | 2 hours |
| 1.8 | Register router in `api/main.py` | `api/main.py` | 10 min |
| 1.9 | Seed default strategy on startup | `db/seed.py` | 30 min |
| 1.10 | Run migration & test endpoints with curl/httpie | Terminal | 30 min |

**Total: ~10 hours**

**Acceptance Criteria:**
- `GET /opportunity-discovery/strategy` returns default strategy
- `GET /opportunity-discovery/coverage` returns correct funnel counts
- `GET /opportunity-discovery/opportunities` returns paginated opportunities with fit/confidence
- `GET /opportunity-discovery/daily-briefing` returns structured briefing
- `GET /opportunity-discovery/failed-screen/valuation` returns companies with failure details

---

### Phase 2: Frontend Page Structure & Navigation
**Goal:** Build the new page shell, routing, and navigation. No data yet.

| Step | Task | Files | Est. Time |
|------|------|-------|-----------|
| 2.1 | Create `/opportunity-discovery` route + page wrapper | `app/opportunity-discovery/` | 30 min |
| 2.2 | Create `/sourcing` redirect | `app/sourcing/page.tsx` | 10 min |
| 2.3 | Update sidebar navigation | `components/sidebar.tsx` | 15 min |
| 2.4 | Create page layout with 7 section placeholders | `opportunity-discovery-page.tsx` | 30 min |
| 2.5 | Add new API functions to `lib/api.ts` | `lib/api.ts` | 45 min |
| 2.6 | Create `useInvestmentStrategy` hook | `hooks/use-investment-strategy.ts` | 30 min |
| 2.7 | Create `useOpportunityDiscovery` hook | `hooks/use-opportunity-discovery.ts` | 45 min |

**Total: ~3 hours**

**Acceptance Criteria:**
- `/opportunity-discovery` loads without errors
- Sidebar shows "Opportunity Discovery" instead of "Sourcing"
- `/sourcing` redirects to `/opportunity-discovery`
- Page shows 7 empty section placeholders with correct headings

---

### Phase 3: Section-by-Section Implementation
**Goal:** Build each of the 7 sections, wiring them to the backend.

#### Section 1: Investment Strategy Panel
| Step | Task | Est. Time |
|------|------|-----------|
| 3.1.1 | Build `InvestmentStrategyPanel` component with display mode | 1 hour |
| 3.1.2 | Build `StrategyEditorModal` for editing criteria | 1.5 hours |
| 3.1.3 | Wire to `useInvestmentStrategy` hook | 30 min |

**Total: ~3 hours**

#### Section 2: Market Coverage Panel
| Step | Task | Est. Time |
|------|------|-----------|
| 3.2.1 | Build `MarketCoveragePanel` with funnel visualization | 1 hour |
| 3.2.2 | Add clickable breakdown ("Why only 8?") → `FailedScreenDrawer` | 1.5 hours |
| 3.2.3 | Wire to `getCoverageMetrics()` | 30 min |

**Total: ~3 hours**

#### Section 3: Highest Conviction Opportunities Table
| Step | Task | Est. Time |
|------|------|-----------|
| 3.3.1 | Build `OpportunitiesTable` with columns: Company, Fit, Confidence, Why | 1.5 hours |
| 3.3.2 | Add tier colors (green/amber/red) for fit scores | 30 min |
| 3.3.3 | Add expandable row → `DiscoverySummaryCard` | 1.5 hours |
| 3.3.4 | Add "Add to Pipeline" action | 30 min |
| 3.3.5 | Add confidence sparkline (Phase 2) | 1 hour |
| 3.3.6 | Wire to `getOpportunities()` | 30 min |

**Total: ~5 hours**

#### Section 4: Signals Panel
| Step | Task | Est. Time |
|------|------|-----------|
| 3.4.1 | Build `SignalsPanel` with categorized signal list | 1 hour |
| 3.4.2 | Build `SignalItem` with direction icons and company link | 45 min |
| 3.4.3 | Wire to `getSignalFeed()` | 30 min |

**Total: ~2 hours**

#### Section 5: Daily Briefing
| Step | Task | Est. Time |
|------|------|-----------|
| 3.5.1 | Build `DailyBriefing` component with summary counts | 1 hour |
| 3.5.2 | Add detail list with expandable items | 45 min |
| 3.5.3 | Wire to `getDailyBriefing()` | 30 min |

**Total: ~2 hours**

#### Section 6: Strategy Coverage Panel
| Step | Task | Est. Time |
|------|------|-----------|
| 3.6.1 | Build `StrategyCoveragePanel` with progress bars | 1 hour |
| 3.6.2 | Add velocity metrics ("8 completed this week") | 30 min |
| 3.6.3 | Wire to `getStrategyCoverage()` | 30 min |

**Total: ~2 hours**

#### Section 7: Emerging Themes
| Step | Task | Est. Time |
|------|------|-----------|
| 3.7.1 | Build `ThemesPanel` with theme cards | 45 min |
| 3.7.2 | Wire to `getEmergingThemes()` | 30 min |

**Total: ~1 hour**

**Phase 3 Total: ~18 hours**

**Acceptance Criteria:**
- All 7 sections render with real data from the backend
- Investment Strategy is editable and persists
- Market Coverage shows correct funnel counts
- Opportunities table shows companies with Fit/Confidence/Why
- Clicking a company expands Discovery Summary with evidence
- Signals panel shows recent signals
- Daily Briefing shows "what changed since yesterday"
- Strategy Coverage shows progress bars
- Themes panel shows emerging themes

---

### Phase 4: Advanced Features & Polish
**Goal:** Add confidence trajectories, evidence gaps, and watchlist strategies.

| Step | Task | Est. Time |
|------|------|-----------|
| 4.1 | Add confidence trajectory sparklines to opportunities table | 2 hours |
| 4.2 | Add "Near Misses" section (companies that almost passed) | 1.5 hours |
| 4.3 | Add strategy tabs (watchlist) to switch entire page context | 2 hours |
| 4.4 | Add Decision Readiness filter layer (Ready/Needs Research/Monitor) | 1.5 hours |
| 4.5 | Add keyboard shortcuts (e.g., `/` to search, `e` to edit strategy) | 1 hour |
| 4.6 | Add empty states and loading skeletons for all sections | 1.5 hours |
| 4.7 | Add error boundaries and retry logic | 1 hour |
| 4.8 | Responsive design (mobile-friendly) | 2 hours |

**Phase 4 Total: ~13 hours**

---

### Phase 5: Testing
**Goal:** Comprehensive backend API tests, frontend component tests, and integration tests.

#### Backend Tests
| Step | Task | Files | Est. Time |
|------|------|-------|-----------|
| 5.1 | Unit tests for `UniverseScreenEngine` | `tests/services/test_universe_screen.py` | 2 hours |
| 5.2 | Unit tests for `OpportunityDiscoveryService` | `tests/services/test_opportunity_discovery.py` | 1.5 hours |
| 5.3 | API tests for all 8 router endpoints | `tests/api/test_opportunity_discovery.py` | 2 hours |
| 5.4 | Integration test: strategy → screen → opportunities → daily briefing | `tests/integration/test_discovery_flow.py` | 1.5 hours |
| 5.5 | Database fixture with seed data | `tests/conftest.py` | 1 hour |

**Backend Tests Total: ~8 hours**

#### Frontend Tests
| Step | Task | Files | Est. Time |
|------|------|-------|-----------|
| 5.6 | Component tests for `InvestmentStrategyPanel` | `__tests__/investment-strategy-panel.test.tsx` | 1.5 hours |
| 5.7 | Component tests for `OpportunitiesTable` | `__tests__/opportunities-table.test.tsx` | 1.5 hours |
| 5.8 | Component tests for `DiscoverySummaryCard` | `__tests__/discovery-summary-card.test.tsx` | 1 hour |
| 5.9 | Hook tests for `useInvestmentStrategy` | `__tests__/use-investment-strategy.test.ts` | 1 hour |
| 5.10 | Hook tests for `useOpportunityDiscovery` | `__tests__/use-opportunity-discovery.test.ts` | 1 hour |
| 5.11 | Integration test: full page render with MSW | `__tests__/opportunity-discovery-page.test.tsx` | 2 hours |

**Frontend Tests Total: ~8 hours**

#### End-to-End Tests
| Step | Task | Est. Time |
|------|------|-----------|
| 5.12 | E2E: Load page → edit strategy → see coverage update | 2 hours |
| 5.13 | E2E: Click company → expand discovery summary → add to pipeline | 2 hours |
| 5.14 | E2E: Click "Why only 8?" → see failed companies → click back | 1.5 hours |

**E2E Tests Total: ~5.5 hours**

**Phase 5 Total: ~21.5 hours**

---

## 7. Total Time Estimate

| Phase | Hours | Days (6h/day) |
|-------|-------|---------------|
| Phase 1: Backend Foundation | 10 | 1.7 |
| Phase 2: Frontend Shell | 3 | 0.5 |
| Phase 3: Section Implementation | 18 | 3 |
| Phase 4: Advanced Features | 13 | 2.2 |
| Phase 5: Testing | 21.5 | 3.6 |
| **Total** | **65.5** | **~11 days** |

**Realistic timeline (with reviews, fixes, iteration): 3–4 weeks**

---

## 8. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Opportunity     │  │ useInvestment   │  │ useOpportunityDiscovery     │  │
│  │ Discovery Page  │  │ Strategy Hook   │  │ Hook (main data fetch)      │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘  │
│           │                    │                         │                  │
│           └────────────────────┴─────────────────────────┘                  │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        ky (REST API)                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              FastAPI Router: /opportunity-discovery                  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ /strategy│ │ /coverage│ │ /opportun│ │ /signals │ │ /daily-b │  │    │
│  │  │          │ │          │ │ ities    │ │          │ │ riefing  │  │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │    │
│  │       └─────────────┴─────────────┴─────────────┴─────────────┘     │    │
│  │                              │                                      │    │
│  │                              ▼                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │         OpportunityDiscoveryService (orchestrator)            │   │    │
│  │  └─────────────────────────────┬───────────────────────────────┘   │    │
│  │                                │                                    │    │
│  │        ┌───────────────────────┼───────────────────────┐            │    │
│  │        ▼                       ▼                       ▼            │    │
│  │  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐     │    │
│  │  │ Universe    │        │ Change      │        │ Market      │     │    │
│  │  │ ScreenEngine│        │ Summarizer  │        │ Pulse       │     │    │
│  │  └──────┬──────┘        └─────────────┘        └─────────────┘     │    │
│  │         │                                                          │    │
│  │         ▼                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                    SQLAlchemy + PostgreSQL                    │   │    │
│  │  │  ┌────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │    │
│  │  │  │Company │ │Financial│ │ Deal    │ │DealScore│ │ Signal  │ │   │    │
│  │  │  │        │ │        │ │         │ │         │ │         │ │   │    │
│  │  │  └────────┘ └────────┘ └─────────┘ └─────────┘ └─────────┘ │   │    │
│  │  │  ┌─────────┐ ┌─────────────┐ ┌─────────────────────────────┐ │   │    │
│  │  │  │Confidence│ │Investment   │ │ IntelligenceHub             │ │   │    │
│  │  │  │Ledger    │ │View         │ │                             │ │   │    │
│  │  │  └─────────┘ └─────────────┘ └─────────────────────────────┘ │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Key Design Decisions

### 9.1 Why JSON `criteria` instead of typed columns?

- **Flexibility:** The strategy criteria will evolve (new fields, new filters). JSON avoids schema migrations.
- **Validation:** Pydantic schemas (`StrategyCriteria`) validate the JSON shape at the API boundary.
- **Querying:** Financial criteria are extracted from JSON and used in SQL queries. Non-financial criteria (sectors, geographies) use `JSONB` containment operators (`@>`, `?|`) which are indexed and fast.

### 9.2 Why compute on-the-fly instead of pre-computing `ScreenResult`?

- **Universe size:** 5,842 companies is small enough for a SQL query to run in <100ms.
- **Simplicity:** No need for background jobs, cache invalidation, or stale data.
- **Real-time:** When the strategy changes, results update immediately.
- **Future:** If the universe grows to 100k+, we can add a `ScreenResult` cache table and a nightly recomputation job without changing the API contract.

### 9.3 Why separate `UniverseScreenEngine` from `OpportunityDiscoveryService`?

- **Single Responsibility:** `UniverseScreenEngine` does one thing: screen companies against criteria.
- **Reusability:** The screening engine can be reused by other features (e.g., a "Compare Strategies" tool).
- **Testability:** The screen engine can be unit-tested with mock data without spinning up the full orchestrator.

### 9.4 Why keep the old `/agents/sourcing` endpoint?

- **Backward compatibility:** Existing users or API clients might depend on it.
- **Different use case:** The old endpoint is useful for ad-hoc research ("What if I searched for healthcare companies?"). The new page is for continuous monitoring.
- **Cost:** Zero cost to keep it. The new page doesn't call it.

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Database query performance** with 5,842 companies | Use `EXPLAIN ANALYZE` on all new queries. Add composite indexes on `(company_id, report_date)` for financials. The existing schema already has these. |
| **No deals exist for most companies** → empty strategic_match | The `UniverseScreenEngine` computes a financial fit score for all companies. Only companies with existing deals get the full strategic score. This is documented behavior. |
| **Strategy criteria JSON is too flexible** | Pydantic validation at the API layer. Frontend uses a typed form. Backend uses explicit field extraction for SQL queries. |
| **Frontend data fetching is manual** | Keep the same pattern (`useState` + `useEffect` + `ky`). Consider migrating to TanStack Query in Phase 4 if the page becomes complex. |
| **No existing test infrastructure** | The project already has `pytest` + `pytest-asyncio`. For frontend, add `vitest` + `@testing-library/react` + `msw` (Mock Service Worker). |

---

## 11. Success Metrics

After shipping, we measure:

| Metric | Target | How |
|--------|--------|-----|
| Page load time | < 2s | Lighthouse / browser devtools |
| API response time | < 500ms | Backend logging / monitoring |
| Time to first opportunity | < 1s | User timing API |
| Strategy edit → results update | < 2s | Manual testing |
| Daily briefing generation | < 1s | Backend logging |
| Test coverage | > 80% | `pytest --cov` / `vitest --coverage` |

---

## 12. Next Steps

1. **Review this plan** — confirm scope and priorities
2. **Start Phase 1** — I'll implement the backend foundation
3. **Parallel: Phase 2 prep** — While backend is being built, scaffold the frontend page structure
4. **Phase 3** — Wire frontend sections to backend endpoints one by one
5. **Phase 4** — Advanced features
6. **Phase 5** — Testing

**Ready to start?** I can begin with Phase 1 (Backend Foundation) immediately.
