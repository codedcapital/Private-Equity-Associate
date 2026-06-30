import ky from "ky";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production"
    ? "https://your-api-domain.com"
    : "http://localhost:8000");

const api = ky.create({ prefixUrl: BASE_URL, timeout: 30000 });

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

export type DealRead = any;
export type FinancialProfile = any;
export type LBOResponse = any;
export type CompetitiveResponse = any;
export type ResearchResponse = any;
export type MemoResponse = any;

export async function getDeal(id: number) {
  return apiCall<any>(`/pipeline/deals/${id}`);
}

/* ─── Financials ─── */
export async function getFinancialProfile(companyId: number) {
  return apiCall<any>(`/financials/${companyId}`);
}

/* ─── LBO ─── */
export async function getLBO(companyId: number) {
  return apiCall<any>(`/lbo/${companyId}`);
}

/* ─── Research ─── */
export async function getResearch(companyId: number) {
  return apiCall<any>(`/agents/research/${companyId}`);
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

export async function getRunStatus(runId: string): Promise<AgentRunStatus> {
  return apiCall<AgentRunStatus>(`/agents/runs/${runId}/status`);
}

export async function getRun(runId: string): Promise<unknown> {
  return apiCall<unknown>(`/agents/runs/${runId}`);
}
