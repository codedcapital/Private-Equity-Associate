# Phase 3 Plan: Intelligence Layer + Interactivity

## Objective
Make the platform proactive (not reactive) and turn the Overview page into an interactive workspace.

## Stage 1: Backend (Intelligence Layer)

### 1a. Next Actions Engine
- **Rule-based tier**: Fast, deterministic. Check stage, diligence status, evidence conflicts, confidence thresholds.
- **LLM-based tier**: Feed current state to a lightweight model. Cache results. Regenerate on state change.
- **New endpoint**: `GET /deals/{id}/overview/next-actions`

### 1b. ChangeSummarizer / Diff Engine
- **Service**: `ChangeSummarizer` queries `deal_events`, groups by time window, generates human-readable summaries.
- **Event diff storage**: Store `before`/`after` JSON in `event_metadata` for all mutating operations.
- **New endpoint**: `GET /deals/{id}/overview/recent-changes` (enhanced over existing events)

### 1c. Versioned Investment View (Diff + Restore)
- **Diff endpoint**: `GET /deals/{id}/overview/investment-view/diff?from={v1}&to={v2}`
- **Restore endpoint**: `POST /deals/{id}/overview/investment-view/{version_id}/restore`
- **Diff algorithm**: Simple JSON diff for content, recommendation, confidence changes.

### 1d. Confidence Recalculation on Evidence Changes
- **Trigger**: When evidence status changes, rebuild confidence ledger.
- **New endpoint**: `PATCH /deals/{id}/overview/evidence/{evidence_id}` — update status, triggers recalc.
- **Deal settings**: `deal_settings` table for weight overrides.

### 1e. New API endpoints to add to overview router
```
GET    /deals/{id}/overview/next-actions
PATCH  /deals/{id}/overview/evidence/{evidence_id}  (update status)
POST   /deals/{id}/overview/evidence/{evidence_id}/conflict  (create conflict)
GET    /deals/{id}/overview/investment-view/diff
POST   /deals/{id}/overview/investment-view/{version_id}/restore
GET    /deals/{id}/overview/recent-changes
```

## Stage 2: Frontend (Interactivity & Edit Mode)

### 2a. Investment View Editor (TipTap)
- Component: `InvestmentViewEditor`
- Toolbar: bold, italic, bullet list, numbered list
- Save → POST /overview/investment-view (creates new version)
- Cancel → revert to current version
- Version history slide-out panel

### 2b. Evidence Validation Inline Panel
- Click evidence chip → expand panel
- Status toggle: VERIFIED / NEEDS_VALIDATION / CONFLICTING / UNKNOWN
- If CONFLICTING → prompt for conflict description (creates `evidence_conflicts`)
- Status change triggers background recalc

### 2c. Diligence Tracker — Interactive CRUD
- Checkboxes toggle status (PATCH /overview/diligence/{id})
- "Add Item" button → form (title, category, owner, due_date, priority)
- Inline editing of owner and due date
- Delete item with confirmation
- Optimistic UI updates

### 2d. Confidence Override
- In ScoreBreakdown panel: allow weight adjustment
- Save to `deal_settings` table
- Recalculate score on the fly

### 2e. API hooks to add
- `useNextActions(dealId)` → GET /overview/next-actions
- `useEvidenceUpdate(dealId)` → PATCH /overview/evidence/{id}
- `useDiligenceMutations(dealId)` → POST/PATCH/DELETE /overview/diligence
- `useInvestmentViewHistory(dealId)` → GET /overview/investment-view/history
- `useDiff(dealId, fromV, toV)` → GET /overview/investment-view/diff
- `useRestoreVersion(dealId, versionId)` → POST /overview/investment-view/{id}/restore
- `useRecentChanges(dealId)` → GET /overview/recent-changes

## Stage 3: Wiring & Tests
- Wire all frontend hooks to backend endpoints
- TypeScript type-check
- Frontend build
- Backend tests (new services + endpoints)
- End-to-end verification
