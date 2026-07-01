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
