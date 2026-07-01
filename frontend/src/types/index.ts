export interface Deal {
  id: string;
  name: string;
  sector: string;
  revenue: string;
  margin: string;
  irr: string;
  irrTier: 'green' | 'amber' | 'red';
  updated: string;
  statusLabel: string;
  statusColor: string;
  stage: string;
  hq: string;
}

export interface PipelineColumn {
  title: string;
  key: string;
  dot: string;
  deals: Deal[];
}

export interface Metric {
  label: string;
  value: string;
  color: string;
  delta: string;
  deltaColor: string;
  sub: string;
}

export interface RiskFlag {
  label: string;
  tier: 'green' | 'amber' | 'red';
}

export interface AgentRun {
  name: string;
  meta: string;
  status: string;
  tier: 'done' | 'running' | 'queued';
  duration: string;
}

export interface FinRow {
  label: string;
  weight: 400 | 600;
  accent: boolean;
  pct: boolean;
  neg: boolean;
  vals: (string | number)[];
}

export interface ChartBar {
  year: string;
  revH: string;
  ebitdaH: string;
}

export interface LBOInput {
  entryMult: number;
  debtPct: number;
  hold: number;
  g1: number;
  g2: number;
  g3: number;
  g4: number;
  g5: number;
  marginExp: number;
  exitMult: number;
}

export interface LBOOutput {
  label: string;
  value: string;
  color: string;
  sub: string;
}

export interface HeatCell {
  irr: string;
  fg: string;
  bg: string;
  border: string;
}

export interface HeatRow {
  exit: string;
  cells: HeatCell[];
}

export interface Competitor {
  name: string;
  tag: string;
  target: boolean;
  model: string;
  pricing: string;
  segment: string;
  geo: string;
  revenue: string;
  ownership: string;
  diff: string;
}

export interface MoatItem {
  label: string;
  rating: string;
  tier: 1 | 2 | 3;
  note: string;
}

export interface ReasoningTraceStep {
  timestamp: string;
  text: string;
}

// ── Intelligence Hub ──────────────────────────────────────────────────────

export interface EvidenceItem {
  id: number;
  text: string;
  source: string;
  source_type: string;
  source_url: string | null;
  source_metadata: Record<string, unknown> | null;
  is_supporting: boolean;
  is_contradictory: boolean;
  confidence: number | null;
  created_at: string;
}

export interface IntelligenceQuestion {
  id: number;
  category: string;
  question: string;
  answer: string | null;
  confidence: number | null;
  sort_order: number;
  evidence: EvidenceItem[];
  created_at: string;
}

export interface SourceConfidence {
  id: number;
  source_name: string;
  source_type: string;
  confidence_score: number;
  rationale: string;
  updated_at: string;
}

export interface ComparableCompany {
  name: string;
  ticker: string | null;
  tag: string;
  revenue: string | null;
  ebitda: string | null;
  ebitda_margin: string | null;
  ev_ebitda: string | null;
  revenue_growth: string | null;
  market_cap: string | null;
  ownership: string | null;
  source: string;
}

export interface IntelligenceHub {
  hub_id: number;
  company_id: number;
  deal_id: number | null;
  status: string;
  executive_briefing: string | null;
  questions: IntelligenceQuestion[];
  source_confidence: SourceConfidence[];
  comparable_companies: ComparableCompany[];
  remaining_diligence: string[];
  generated_at: string;
  updated_at: string;
}

export interface ResearchItem {
  type: string;
  typeTier: 'teal' | 'gold' | 'gray';
  title: string;
  source: string;
  date: string;
  snippet: string;
}

export interface SourcingResult {
  name: string;
  sector: string;
  revenue: string;
  margin: string;
  fit: number;
}

export interface MemoSection {
  id: string;
  title: string;
  paras: string[];
  hasTable?: boolean;
  tableRows?: { k: string; v: string; color: string }[];
}

export type DealTab = 'overview' | 'financials' | 'lbo' | 'competitive' | 'research' | 'memo';
