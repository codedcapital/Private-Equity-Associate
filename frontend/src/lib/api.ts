import ky from "ky";
import type {
  DealOverview,
  InvestmentView,
  Score,
  EvidenceModule,
  DiligenceItem,
  Readiness,
  ActivityEvent,
  NextAction,
} from "@/types/overview";

export interface ReasoningTraceStep {
  timestamp: string;
  text: string;
}

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production"
    ? "https://your-api-domain.com"
    : "http://localhost:8000");

const api = ky.create({ baseUrl: BASE_URL, timeout: 30000 });

export async function apiCall<T>(url: string, opts?: any): Promise<T> {
  const res = await api(url, opts);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ─── Sourcing ─── */
export interface SourcingCandidate {
  name: string;
  company_id?: number | null;
  sector?: string | null;
  revenue?: number | null;
  ebitda_margin?: number | null;
  score?: number | null;
  [key: string]: any;
}

export interface SourcingResponse {
  run_id: string;
  status: string;
  message: string;
  candidates: SourcingCandidate[];
}

export async function runSourcing(thesis: string): Promise<SourcingResponse> {
  return apiCall<SourcingResponse>("/agents/sourcing", {
    method: "POST",
    json: { thesis },
  });
}

export async function createDeal(companyId: number) {
  return apiCall<any>("/pipeline/deals", {
    method: "POST",
    json: { company_id: companyId, stage: "sourcing" },
  });
}

/* ─── Deals ─── */
export async function getDeals() {
  return apiCall<any>("/pipeline/deals");
}

export const listDeals = getDeals;

export interface SourcingResponse {
  run_id: string;
  status: string;
  message: string;
  candidates: SourcingCandidate[];
  reasoning_trace?: ReasoningTraceStep[];
}

export interface FinancialProfile {
  revenue?: number | null;
  ebitda?: number | null;
  ebitda_margin?: number | null;
  revenue_growth?: number | null;
  net_debt?: number | null;
  net_debt_ebitda?: number | null;
  fcf?: number | null;
  fcf_yield?: number | null;
  reasoning_trace?: ReasoningTraceStep[];
}

export interface LBOResponse {
  lbo_result?: any;
  scenarios?: any;
  sensitivity_grid?: any;
  interpretation?: string | null;
  errors?: string[] | null;
  reasoning_trace?: ReasoningTraceStep[];
}

export interface CompetitiveResponse {
  competitive_map?: any;
  reasoning_trace?: ReasoningTraceStep[];
}

export interface ResearchResponse {
  research?: any;
  reasoning_trace?: ReasoningTraceStep[];
}

export interface MemoResponse {
  memo?: any;
  pdf_download_url?: string | null;
  reasoning_trace?: ReasoningTraceStep[];
}

export interface DealRead {
  id: number;
  company_id: number;
  stage: string;
  entry_ev?: number | null;
  entry_ebitda?: number | null;
  lbo_irr?: number | null;
  lbo_moic?: number | null;
  memo_id?: number | null;
  last_updated?: string | null;
  created_at?: string | null;
  company?: any;
  financials?: FinancialProfile | null;
  reasoning_trace?: ReasoningTraceStep[];
}

export async function getDeal(id: number) {
  return apiCall<any>(`/pipeline/deals/${id}`);
}

/* ─── Financials ─── */
export async function getFinancialProfile(companyId: number) {
  return apiCall<any>(`/agents/financials/${companyId}`);
}

/* ─── LBO ─── */
export async function getLBO(companyId: number) {
  return apiCall<any>(`/agents/lbo/${companyId}`);
}

/* ─── Research ─── */
export async function getResearch(companyId: number) {
  return apiCall<any>(`/agents/research/${companyId}`);
}

/* ─── Intelligence Hub ─── */
export interface IntelligenceHubResponse {
  hub_id: number;
  company_id: number;
  deal_id: number | null;
  status: string;
  executive_briefing: string | null;
  questions: any[];
  source_confidence: any[];
  comparable_companies: any[];
  remaining_diligence: string[];
  generated_at: string;
  updated_at: string;
}

export async function getIntelligenceHub(companyId: number): Promise<IntelligenceHubResponse> {
  return apiCall<IntelligenceHubResponse>(`/intelligence/${companyId}`);
}

export async function generateIntelligenceHub(companyId: number): Promise<IntelligenceHubResponse> {
  return apiCall<IntelligenceHubResponse>(`/intelligence/${companyId}/generate`, {
    method: "POST",
  });
}

export async function addHubQuestion(companyId: number, payload: { category: string; question: string; answer?: string; confidence?: number; sort_order?: number }) {
  return apiCall<any>(`/intelligence/${companyId}/questions`, {
    method: "POST",
    json: payload,
  });
}

export async function addHubEvidence(companyId: number, payload: { text: string; source: string; source_type: string; is_supporting?: boolean; is_contradictory?: boolean; confidence?: number; source_url?: string }) {
  return apiCall<any>(`/intelligence/${companyId}/evidence`, {
    method: "POST",
    json: payload,
  });
}

export async function setHubSourceConfidence(companyId: number, payload: { source_name: string; source_type: string; confidence_score: number; rationale: string }) {
  return apiCall<any>(`/intelligence/${companyId}/source-confidence`, {
    method: "POST",
    json: payload,
  });
}

/* ─── Competitive ─── */
export async function getCompetitive(companyId: number) {
  return apiCall<any>(`/agents/competitive/${companyId}`);
}

/* ─── Memo ─── */
export async function getMemo(memoId: number) {
  return apiCall<any>(`/agents/memo/${memoId}`);
}

/* ─── Admin / Settings ─── */
export interface IngestStatus {
  last_run: string | null;
  companies: number;
  filings: number;
  chunks: number;
  financials: number;
}

export async function getIngestStatus(): Promise<IngestStatus> {
  return apiCall<IngestStatus>("/admin/ingest/status");
}

export async function triggerIngest(): Promise<{ message: string; status: string }> {
  return apiCall<{ message: string; status: string }>("/admin/ingest/trigger", { method: "POST" });
}

export interface BulkIngestResult {
  total: number;
  created: number;
  existing: number;
  failed: number;
  results: Record<string, Record<string, string>>;
}

export async function bulkIngest(tickers: string[], sources?: string[]): Promise<BulkIngestResult> {
  return apiCall<BulkIngestResult>("/admin/ingest/bulk", {
    method: "POST",
    json: { tickers, sources: sources ?? ["financials"] },
  });
}

export interface PipelineStatus {
  active_runs: number;
  completed_today: number;
  failed_today: number;
  total_cost_today: number;
  total_tokens_today: number;
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  return apiCall<PipelineStatus>("/admin/pipeline/status");
}

/* ─── Pipeline ─── */
export interface PipelineRunRequest {
  company_name_or_id: string | number;
  thesis?: string | null;
}

export interface PipelineRunResponse {
  run_id: string;
  status: string;
  message: string;
}

export async function runPipeline(request: PipelineRunRequest): Promise<PipelineRunResponse> {
  return apiCall<PipelineRunResponse>("/pipeline/run", {
    method: "POST",
    json: request,
  });
}

/* ─── Agent runs ─── */
export interface AgentRunStatus {
  run_id: string;
  celery_status: string;
  agent_status: string | null;
  output_data: unknown;
  errors: string[] | null;
  duration_ms: number | null;
  created_at: string | null;
}

export interface AgentRunLog {
  id: number;
  run_id: string;
  agent_name: string;
  status: string;
  input_data: unknown;
  output_data: unknown;
  errors: string[] | null;
  duration_ms: number | null;
  created_at: string | null;
}

export interface AgentRunListResponse {
  logs: AgentRunLog[];
  total: number;
}

export async function listAgentRuns(limit: number = 50): Promise<AgentRunLog[]> {
  const res = await apiCall<AgentRunListResponse>(`/agents/runs?limit=${limit}`);
  return res.logs ?? [];
}

export async function getRunStatus(runId: string): Promise<AgentRunStatus> {
  return apiCall<AgentRunStatus>(`/agents/runs/${runId}/status`);
}

export async function getRun(runId: string): Promise<unknown> {
  return apiCall<unknown>(`/agents/runs/${runId}`);
}

/* ─── Dashboard ─── */
export interface DashboardSummary {
  active_deals: number;
  avg_score: number | null;
  ic_ready_count: number;
  attention_count: number;
  stage_breakdown: Record<string, number>;
  last_updated: string;
}

export interface AttentionDeal {
  deal_id: number;
  company_id: number;
  company_name: string;
  ticker: string | null;
  score: number | null;
  score_change: number | null;
  score_change_direction: "up" | "down" | null;
  stage: string;
  stage_label: string;
  why: string;
  confidence: string;
  updated_at: string;
  financials_score: number | null;
  risk_score: number | null;
  moat_score: number | null;
  market_score: number | null;
}

export interface AttentionList {
  deals: AttentionDeal[];
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiCall<DashboardSummary>("/dashboard/summary");
}

export async function getAttentionDeals(): Promise<AttentionList> {
  return apiCall<AttentionList>("/dashboard/attention");
}

/* ─── Market Pulse ─── */
export interface MarketPulseItem {
  key: string;
  value: string;
  label?: string | null;
  direction?: string | null;
}

export interface MarketPulseData {
  items: MarketPulseItem[];
  last_updated: string;
}

export async function getMarketPulse(): Promise<MarketPulseData> {
  return apiCall<MarketPulseData>("/market-pulse");
}

export async function updateMarketPulse(data: MarketPulseData): Promise<MarketPulseData> {
  return apiCall<MarketPulseData>("/market-pulse", { method: "PUT", json: data });
}

/* ─── Signals ─── */
export interface SignalItem {
  id: number;
  deal_id: number;
  company_name?: string | null;
  signal_type: string;
  direction?: string | null;
  title: string;
  description?: string | null;
  evidence_url?: string | null;
  confidence: string;
  detected_at: string;
  resolved_at?: string | null;
  is_dismissed: boolean;
}

export interface SignalList {
  signals: SignalItem[];
}

export async function getSignals(dealId?: number): Promise<SignalList> {
  const url = dealId ? `/dashboard/signals?deal_id=${dealId}` : "/dashboard/signals";
  return apiCall<SignalList>(url);
}

export async function dismissSignal(signalId: number): Promise<{ success: boolean; signal_id: number }> {
  return apiCall<{ success: boolean; signal_id: number }>(`/dashboard/signals/${signalId}/dismiss`, { method: "POST" });
}

/* ─── Recently Updated ─── */
export interface RecentItem {
  deal_id: number;
  company_name: string;
  event_type: string;
  old_value?: string | null;
  new_value?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface RecentlyUpdatedResponse {
  items: RecentItem[];
}

export async function getRecentlyUpdated(): Promise<RecentlyUpdatedResponse> {
  return apiCall<RecentlyUpdatedResponse>("/dashboard/recently-updated");
}

/* ─── Activity Summary ─── */
export interface ActivitySummary {
  financials_refreshed: number;
  research_updated: number;
  news_analyzed: number;
  models_rebuilt: number;
  total_runs: number;
  date: string;
}

export async function getActivitySummary(): Promise<ActivitySummary> {
  return apiCall<ActivitySummary>("/dashboard/activity-summary");
}

/* ─── Industry Watch ─── */
export interface SectorItem {
  sector: string;
  count: number;
}

export interface IndustryWatchResponse {
  sectors: SectorItem[];
}

export async function getIndustryWatch(): Promise<IndustryWatchResponse> {
  return apiCall<IndustryWatchResponse>("/dashboard/industry");
}

/* ─── Search ─── */
export interface SearchResult {
  type: string;
  id: number | string;
  title: string;
  subtitle?: string | null;
  url: string;
}

export interface SearchResponse {
  results: SearchResult[];
}

export async function globalSearch(query: string): Promise<SearchResponse> {
  if (!query || query.length < 2) return { results: [] };
  return apiCall<SearchResponse>(`/dashboard/search?q=${encodeURIComponent(query)}`);
}

/* ─── Outstanding Questions ─── */
export interface QuestionItem {
  id: number;
  deal_id?: number | null;
  company_name: string;
  category: string;
  question: string;
  answer?: string | null;
  status: string;
  created_at: string;
}

export interface QuestionsResponse {
  questions: QuestionItem[];
}

export async function getOutstandingQuestions(status: string = "pending"): Promise<QuestionsResponse> {
  return apiCall<QuestionsResponse>(`/intelligence/questions?status=${status}`);
}

export async function updateQuestionStatus(questionId: number, status: string, answer?: string): Promise<{ success: boolean; question_id: number }> {
  return apiCall<{ success: boolean; question_id: number }>(`/intelligence/questions/${questionId}`, {
    method: "PATCH",
    json: { status, answer },
  });
}

/* ─── Deal Overview (New IC Pack) ─── */

// Raw backend response shape from /deals/{deal_id}/overview
export interface BackendOverviewResponse {
  deal_id: number;
  company: {
    id: number;
    name: string;
    ticker: string | null;
    sector: string | null;
    geography: string | null;
  };
  stage: string;
  investment_view: {
    id: number;
    deal_id: number;
    version: number;
    content: { text?: string; blocks?: any[]; sources?: string[]; generated_at?: string } | null;
    recommendation: string | null;
    confidence_score: number | null;
    authored_by: string;
    edited_by: string | null;
    status: string;
    created_at: string;
    updated_at: string;
  } | null;
  confidence: {
    deal_id: number;
    final_score: number;
    base_score: number;
    factors: Record<string, { weight?: number; contribution?: number; penalty?: number; status?: string }>;
    bottlenecks: string[] | null;
    reduced_because: string[] | null;
  } | null;
  evidence: {
    id: number;
    module_name: string;
    text: string;
    status: string;
    source: string;
    source_type: string;
    confidence: number | null;
    is_supporting: boolean;
    is_contradictory: boolean;
    created_at: string | null;
  }[];
  diligence: {
    items: {
      id: number;
      deal_id: number;
      category: string;
      title: string;
      description: string | null;
      status: string;
      assigned_to: string | null;
      due_date: string | null;
      evidence_id: number | null;
      priority: string;
      created_by: string | null;
      created_at: string;
      completed_at: string | null;
    }[];
    total: number;
    complete: number;
    open: number;
  };
  decision_readiness: {
    score: number;
    current_stage: string;
    met: string[];
    unmet: string[];
    recommended_next_step: string;
    next_stage: string | null;
    diligence_summary: {
      total: number;
      complete: number;
      open: number;
      blockers: number;
    };
  } | null;
  recent_events: {
    id: number;
    event_type: string;
    actor_type: string;
    actor_id: string | null;
    description: string;
    created_at: string;
  }[];
  financial_snapshot: Record<string, any> | null;
  lbo: Record<string, any> | null;
}

export async function getDealOverview(dealId: number): Promise<BackendOverviewResponse> {
  return apiCall<BackendOverviewResponse>(`/deals/${dealId}/overview`);
}

export function mapBackendToFrontend(raw: BackendOverviewResponse): DealOverview {
  // 1. Investment View
  const rawView = raw.investment_view;
  const investmentView: InvestmentView | null = rawView
    ? {
        id: String(rawView.id),
        content: rawView.content?.text ?? "",
        sources: rawView.content?.sources ?? [],
        updatedAt: rawView.updated_at,
      }
    : null;

  // 2. Score (from confidence ledger + investment view recommendation)
  const rawConfidence = raw.confidence;
  const rawRecommendation = rawView?.recommendation ?? "HOLD";
  // Map backend "PASS" to frontend "DECLINE"
  const recommendation: "PROCEED" | "CONDITIONAL" | "DECLINE" | "HOLD" =
    rawRecommendation === "PASS"
      ? "DECLINE"
      : (rawRecommendation as any) === "PROCEED" || rawRecommendation === "CONDITIONAL" || rawRecommendation === "HOLD"
      ? (rawRecommendation as any)
      : "HOLD";

  const score: Score | null = rawConfidence
    ? {
        value: rawConfidence.final_score,
        recommendation,
        confidence: rawView?.confidence_score ?? 0,
        breakdown: Object.entries(rawConfidence.factors ?? {}).map(([label, f]) => ({
          label,
          weight: (f.weight ?? 0) * 100, // backend 0.0–1.0 → frontend 0–100
          score: (f.contribution ?? 0) + (f.penalty ?? 0), // approximate
          contribution: f.contribution ?? 0,
        })),
      }
    : null;

  // 3. Evidence
  const evidence: EvidenceModule[] = raw.evidence.map((e) => ({
    id: String(e.id),
    name: e.module_name || e.source,
    status: (e.status as any) || "UNKNOWN",
    summary: e.text,
    sourceReference: `${e.source}${e.source_type ? ` (${e.source_type})` : ""}`,
  }));

  // 4. Diligence (flatten from { items, total, complete, open })
  const diligence: DiligenceItem[] = raw.diligence.items.map((d) => ({
    id: String(d.id),
    title: d.title,
    category: d.category,
    owner: d.assigned_to ?? "—",
    dueDate: d.due_date ?? "",
    completed: d.status === "complete",
  }));

  // 5. Readiness
  const rawReadiness = raw.decision_readiness;
  const readiness: Readiness | null = rawReadiness
    ? {
        score: rawReadiness.score,
        items: [
          ...rawReadiness.met.map((label) => ({ label, met: true as const })),
          ...rawReadiness.unmet.map((label) => ({ label, met: false as const })),
        ],
      }
    : null;

  // 6. Activity / Recent Events
  const activity: ActivityEvent[] = raw.recent_events.map((e) => ({
    id: String(e.id),
    timestamp: e.created_at,
    actor: e.actor_id ?? e.actor_type ?? "System",
    description: e.description,
  }));

  // 7. Next Action (from recommended_next_step)
  const nextAction: NextAction | null = rawReadiness?.recommended_next_step
    ? {
        id: "next-1",
        title: rawReadiness.recommended_next_step,
        description: rawReadiness.unmet.length > 0
          ? `Outstanding: ${rawReadiness.unmet.slice(0, 3).join("; ")}`
          : "All requirements met.",
        priority: rawReadiness.unmet.length > 0 ? "high" : "medium",
      }
    : null;

  return {
    deal: {
      id: String(raw.deal_id),
      name: raw.company.name,
      stage: raw.stage.toUpperCase(),
      sector: raw.company.sector ?? "—",
      hq: raw.company.geography ?? "—",
    },
    investmentView,
    score,
    evidence,
    diligence,
    readiness,
    activity,
    nextAction,
  };
}


/* ─── Phase 3: Next Actions ─── */

export interface NextActionItem {
  id: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  rationale: string;
}

export interface NextActionsResponse {
  deal_id: number;
  actions: NextActionItem[];
  generated_at: string;
}

export async function getNextActions(dealId: number): Promise<NextActionsResponse> {
  return apiCall<NextActionsResponse>(`/deals/${dealId}/overview/next-actions`);
}

/* ─── Phase 3: Evidence Status Update ─── */

export async function updateEvidenceStatus(
  dealId: number,
  evidenceId: number,
  status: string,
  conflictDescription?: string | null
) {
  return apiCall<any>(`/deals/${dealId}/overview/evidence/${evidenceId}`, {
    method: "PATCH",
    json: { status, conflict_description: conflictDescription },
  });
}

/* ─── Phase 3: Evidence Conflict ─── */

export async function createEvidenceConflict(
  dealId: number,
  evidenceId: number,
  evidenceBId: number,
  conflictDescription: string
) {
  return apiCall<any>(`/deals/${dealId}/overview/evidence/${evidenceId}/conflict`, {
    method: "POST",
    json: { evidence_b_id: evidenceBId, conflict_description: conflictDescription },
  });
}

/* ─── Phase 3: Investment View Diff ─── */

export interface ViewDiffResponse {
  from_version: number;
  to_version: number;
  changes: { path: string; before: any; after: any }[];
  summary: string[];
}

export async function getViewDiff(
  dealId: number,
  fromVersionId: number,
  toVersionId: number
): Promise<ViewDiffResponse> {
  return apiCall<ViewDiffResponse>(
    `/deals/${dealId}/overview/investment-view/diff?from_version_id=${fromVersionId}&to_version_id=${toVersionId}`
  );
}

/* ─── Phase 3: Restore View Version ─── */

export async function restoreViewVersion(dealId: number, versionId: number) {
  return apiCall<any>(`/deals/${dealId}/overview/investment-view/${versionId}/restore`, {
    method: "POST",
  });
}

/* ─── Phase 3: Recent Changes ─── */

export interface RecentChangeItem {
  id: number;
  timestamp: string;
  event_type: string;
  actor: string;
  description: string;
  metadata: any;
}

export interface RecentChangesResponse {
  deal_id: number;
  changes: RecentChangeItem[];
  total: number;
}

export async function getRecentChanges(dealId: number): Promise<RecentChangesResponse> {
  return apiCall<RecentChangesResponse>(`/deals/${dealId}/overview/recent-changes`);
}

/* ─── Phase 3: Deal Settings ─── */

export interface DealSettings {
  deal_id: number;
  confidence_weights: Record<string, number>;
  updated_at: string | null;
}

export async function getDealSettings(dealId: number): Promise<DealSettings> {
  return apiCall<DealSettings>(`/deals/${dealId}/overview/settings`);
}

export async function updateDealSettings(
  dealId: number,
  confidenceWeights: Record<string, number> | null
) {
  return apiCall<DealSettings>(`/deals/${dealId}/overview/settings`, {
    method: "PATCH",
    json: { confidence_weights: confidenceWeights },
  });
}

/* ─── Phase 3: Diligence (already in router from Phase 2) ─── */

export interface DiligenceCreatePayload {
  category: string;
  title: string;
  description?: string | null;
  status?: string;
  assigned_to?: string | null;
  due_date?: string | null;
  evidence_id?: number | null;
  priority?: string;
  created_by?: string | null;
}

export async function createDiligenceItem(dealId: number, payload: DiligenceCreatePayload) {
  return apiCall<any>(`/deals/${dealId}/overview/diligence`, {
    method: "POST",
    json: payload,
  });
}

export async function updateDiligenceItem(
  dealId: number,
  itemId: number,
  payload: Partial<DiligenceCreatePayload>
) {
  return apiCall<any>(`/deals/${dealId}/overview/diligence/${itemId}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function deleteDiligenceItem(dealId: number, itemId: number) {
  return apiCall<any>(`/deals/${dealId}/overview/diligence/${itemId}`, {
    method: "DELETE",
  });
}

/* ─── Phase 3: Investment View (Create/Edit) ─── */

export interface InvestmentViewCreatePayload {
  content?: any;
  recommendation?: string | null;
  confidence_score?: number | null;
  authored_by?: string;
  status?: string;
}

export async function createOrEditInvestmentView(
  dealId: number,
  payload: InvestmentViewCreatePayload
) {
  return apiCall<any>(`/deals/${dealId}/overview/investment-view`, {
    method: "POST",
    json: payload,
  });
}

/* ─── Phase 3: Refresh Overview ─── */

export async function refreshOverview(dealId: number) {
  return apiCall<any>(`/deals/${dealId}/overview/refresh`, { method: "POST" });
}
