# PE Frontend — Phase 1 & 2 Implementation Spec

## User Goal
Implement Phases 1 & 2 of the new frontend roadmap for the PE deal overview page.
- **Phase 1**: Design system + component primitives + page shell
- **Phase 2**: Read-only overview page with 7 sections + API hook + skeletons

## Non-Goals
- No TipTap editor for Phase 1/2 (use plain rendered HTML for read mode; editor comes in Phase 3)
- No actual backend API changes — mock data only for now
- No PDF export, keyboard shortcuts, role-based views (Phase 4+)
- No real-time updates (Phase 5)

## Current Repo Facts
- **Stack**: Next.js 16.2.9, React 19.2.4, Tailwind CSS 4, TypeScript 5
- **Package manager**: npm (package-lock.json exists)
- **Fonts**: Inter (sans), IBM Plex Mono (mono) via next/font/google
- **Existing**: Dark theme at `frontend/src/app/globals.css`, deal page at `frontend/src/app/deal/[id]/deal-page.tsx`
- **Build**: `npm run build` in `frontend/`
- **Path aliases**: `@/*` maps to `frontend/src/*`

## Design System (Single Source of Truth)

### Colors
```ts
const colors = {
  background: '#0a0a0a',
  surface: '#141414',
  surfaceHover: '#1a1a1a',
  border: '#1f1f1f',
  borderHover: '#2a2a2a',
  textPrimary: '#e5e5e5',
  textSecondary: '#737373',
  textMuted: '#525252',
  accent: '#c7a84b',        // desaturated gold
  accentMuted: '#c7a84b33', // 20% opacity
  positive: '#4ade80b3',    // muted green
  warning: '#fbbf24b3',     // muted amber
  negative: '#f87171b3',    // muted red
  unknown: '#525252',
}
```

### Typography
```ts
const typography = {
  mono: '"JetBrains Mono", "SF Mono", monospace',
  sans: '"Inter", "Geist", system-ui, sans-serif',
  serif: '"Tiempos Text", "Chronicle", "Georgia", serif',
}
```

### Spacing
```ts
const spacing = {
  sectionGap: '48px',
  contentGap: '24px',
  textGap: '12px',
  padding: '32px',
}
```

## Shared Interfaces

```ts
// frontend/src/types/overview.ts

export type EvidenceStatus = 'VERIFIED' | 'NEEDS_VALIDATION' | 'CONFLICTING' | 'UNKNOWN';
export type Recommendation = 'PROCEED' | 'CONDITIONAL' | 'DECLINE' | 'HOLD';
export type ViewMode = 'document' | 'data';

export interface DealOverview {
  deal: {
    id: string;
    name: string;
    stage: string;
    sector: string;
    hq: string;
  };
  investmentView: InvestmentView | null;
  score: Score | null;
  evidence: EvidenceModule[];
  diligence: DiligenceItem[];
  readiness: Readiness | null;
  activity: ActivityEvent[];
  nextAction: NextAction | null;
}

export interface InvestmentView {
  id: string;
  content: string; // HTML string
  sources: string[];
  updatedAt: string;
}

export interface Score {
  value: number; // 0-100
  recommendation: Recommendation;
  confidence: number; // 0-100
  breakdown: ScoreBreakdownItem[];
}

export interface ScoreBreakdownItem {
  label: string;
  weight: number;
  score: number;
  contribution: number;
}

export interface EvidenceModule {
  id: string;
  name: string;
  status: EvidenceStatus;
  summary: string;
  sourceReference: string;
  rawData?: string;
}

export interface DiligenceItem {
  id: string;
  title: string;
  category: string;
  owner: string;
  dueDate: string;
  completed: boolean;
}

export interface Readiness {
  score: number; // 0-100
  items: ReadinessItem[];
}

export interface ReadinessItem {
  label: string;
  met: boolean;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  actor: string;
  description: string;
}

export interface NextAction {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
}
```

## Component Inventory (Phase 1)
All components go in `frontend/src/components/overview/`:

| Component | File | Description |
|-----------|------|-------------|
| SectionHeader | `primitives/section-header.tsx` | All-caps, tracked, muted color |
| NumberDisplay | `primitives/number-display.tsx` | Large mono, right-aligned, optional delta |
| EvidenceChip | `primitives/evidence-chip.tsx` | [VERIFIED], [NEEDS VALIDATION], etc. |
| DiligenceRow | `primitives/diligence-row.tsx` | Checkbox + title + owner + due date |
| ConfidenceBar | `primitives/confidence-bar.tsx` | Segmented horizontal bar or big number |
| ReadinessMeter | `primitives/readiness-meter.tsx` | Checklist of met/unmet items |
| ActivityFeedItem | `primitives/activity-feed-item.tsx` | Timestamp + actor + description |
| SkeletonSection | `primitives/skeleton-section.tsx` | Skeleton matching section structure |

## Overview Sections (Phase 2)
All sections go in `frontend/src/components/overview/sections/`:

| Section | File | Description |
|---------|------|-------------|
| InvestmentViewSection | `sections/investment-view-section.tsx` | Hero: serif, generous line height, footer |
| InvestmentScoreSection | `sections/investment-score-section.tsx` | Big number + rec + confidence, expand breakdown |
| SupportingEvidenceSection | `sections/supporting-evidence-section.tsx` | Evidence module list, expandable |
| OutstandingDiligenceSection | `sections/outstanding-diligence-section.tsx` | Diligence item list, read-only checkboxes |
| DecisionReadinessSection | `sections/decision-readiness-section.tsx` | Score + checklist |
| RecentChangesSection | `sections/recent-changes-section.tsx` | Activity feed, last 10 |
| RecommendedActionsSection | `sections/recommended-actions-section.tsx` | Top rec card |

## Page Shell
- `frontend/src/components/overview/page-shell.tsx` — Sticky header, Document/Data toggle, centered 960px max-width

## API Hook
- `frontend/src/hooks/use-deal-overview.ts` — Returns DealOverview with loading state, uses mock data

## Integration Point
- The new overview components render inside the existing `deal-page.tsx` when `tab === "overview"`.
- Replace the existing overview tab content with the new `<OverviewPage dealId={id} />` component.

## Worker Assignments

### Worker A: Primitives + Shell
- Implement all 8 primitives in `frontend/src/components/overview/primitives/`
- Implement `page-shell.tsx`
- Read: `frontend/src/lib/utils.ts`, `frontend/src/app/globals.css`
- Allowed write: `frontend/src/components/overview/primitives/*`, `frontend/src/components/overview/page-shell.tsx`
- Do not edit: existing deal-page.tsx, existing globals.css (only new files)

### Worker B: Overview Sections
- Implement all 7 section components in `frontend/src/components/overview/sections/`
- Implement `overview-page.tsx` (the assembled page)
- Read: `frontend/src/types/overview.ts` (will be created by main agent), existing primitives
- Allowed write: `frontend/src/components/overview/sections/*`, `frontend/src/components/overview/overview-page.tsx`
- Do not edit: anything outside `frontend/src/components/overview/`

### Worker C: API Hook + Types + Mock Data
- Write `frontend/src/types/overview.ts`
- Write `frontend/src/hooks/use-deal-overview.ts`
- Create mock data generator
- Allowed write: `frontend/src/types/overview.ts`, `frontend/src/hooks/use-deal-overview.ts`
- Do not edit: anything outside these two files

## Merge Order
1. Main agent creates design system + types (blocking)
2. Worker A (primitives) + Worker C (hook + types) in parallel
3. Worker B (sections) after Worker A completes
4. Main agent integrates into deal-page.tsx and verifies

## Validation
- `cd frontend && npm run build` must pass with zero errors
- No TypeScript errors in created files
- Components render without runtime errors
