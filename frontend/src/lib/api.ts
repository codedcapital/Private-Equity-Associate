import ky from "ky";

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

async function apiCall<T>(url: string, opts?: any): Promise<T> {
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
