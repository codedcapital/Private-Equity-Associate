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

const REFERENCE_NOW = new Date("2025-07-10T12:00:00.000Z");

function getIsoTimestamp(offsetDays: number = 0): string {
  const d = new Date(REFERENCE_NOW);
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString();
}

function buildInvestmentView(dealId: string): InvestmentView {
  return {
    id: `view-${dealId}`,
    content: `<p><strong>AppFolio, Inc.</strong> represents a compelling mid-market SaaS investment within the PropTech vertical. The company has demonstrated consistent top-line growth, with revenue expanding from $520M in 2022 to $789M in 2024, representing a compound annual growth rate of approximately 23%. This growth is underpinned by strong customer retention (&gt;95% net revenue retention) and increasing average revenue per user as the platform matures.</p>

<p>From a market positioning perspective, AppFolio occupies a defensible niche in property management software for mid-market residential and commercial operators. The total addressable market is estimated at $12 billion, growing at a 15% CAGR, driven by continued digitization of real estate operations and increasing regulatory complexity that favors software-enabled compliance. The company’s integrated ecosystem—spanning property management, leasing, maintenance, and accounting—creates meaningful switching costs and reduces customer churn.</p>

<p>The investment moat is further reinforced by AppFolio’s data network effects. As more properties are managed on the platform, the aggregated data improves pricing algorithms, tenant screening accuracy, and market intelligence offerings, creating a virtuous cycle that benefits existing customers and attracts new ones. Management has demonstrated disciplined capital allocation, prioritizing organic product development over dilutive M&A, which aligns well with our long-term value creation thesis.</p>

<p>However, prospective investors should note the competitive intensity from both legacy incumbents and well-funded vertical SaaS entrants. While AppFolio’s product depth and customer intimacy provide differentiation, sustained R&D investment will be critical to maintaining market leadership. The company’s transition to a AI-enhanced platform represents a key catalyst that could expand margins and deepen customer relationships over the next three to five years.</p>`,
    sources: ["Yahoo Finance", "SEC Filings", "Industry Research"],
    updatedAt: getIsoTimestamp(),
  };
}

function buildScore(): Score {
  return {
    value: 78,
    recommendation: "PROCEED",
    confidence: 82,
    breakdown: [
      { label: "Financials", weight: 0.3, score: 85, contribution: 25.5 },
      { label: "Market", weight: 0.25, score: 72, contribution: 18.0 },
      { label: "Moat", weight: 0.2, score: 80, contribution: 16.0 },
      { label: "Management", weight: 0.15, score: 75, contribution: 11.25 },
      { label: "Risk", weight: 0.1, score: 65, contribution: 6.5 },
    ],
  };
}

function buildEvidence(): EvidenceModule[] {
  return [
    {
      id: "ev-1",
      name: "Revenue Verification",
      status: "VERIFIED",
      summary: "Revenue of $789M confirmed via 10-K filing",
      sourceReference: "SEC EDGAR 10-K 2024",
    },
    {
      id: "ev-2",
      name: "Market Sizing",
      status: "VERIFIED",
      summary: "TAM of $12B with 15% CAGR supported by industry reports",
      sourceReference: "Grand View Research",
    },
    {
      id: "ev-3",
      name: "Competitive Position",
      status: "NEEDS_VALIDATION",
      summary: "Strong moat but new entrant threat emerging",
      sourceReference: "Internal analysis",
    },
    {
      id: "ev-4",
      name: "Margin Analysis",
      status: "VERIFIED",
      summary: "EBITDA margin 18.2% consistent across 3 years",
      sourceReference: "Yahoo Finance",
    },
    {
      id: "ev-5",
      name: "Debt Profile",
      status: "CONFLICTING",
      summary: "Net debt/EBITDA at 4.2x vs management guidance of 3.5x",
      sourceReference: "Credit Suisse report",
    },
    {
      id: "ev-6",
      name: "Management Track",
      status: "UNKNOWN",
      summary: "CEO tenure 8 years, limited info on bench strength",
      sourceReference: "LinkedIn / Proxy",
    },
  ];
}

function buildDiligence(): DiligenceItem[] {
  return [
    {
      id: "dd-1",
      title: "Reference checks with 3 customers",
      category: "Commercial",
      owner: "Sarah Chen",
      dueDate: "2025-07-15",
      completed: true,
    },
    {
      id: "dd-2",
      title: "Insurance review",
      category: "Legal",
      owner: "Mike Ross",
      dueDate: "2025-07-20",
      completed: false,
    },
    {
      id: "dd-3",
      title: "Legal review of customer contracts",
      category: "Legal",
      owner: "Legal Team",
      dueDate: "2025-07-18",
      completed: true,
    },
    {
      id: "dd-4",
      title: "Environmental site assessment",
      category: "Technical",
      owner: "External",
      dueDate: "2025-07-25",
      completed: false,
    },
    {
      id: "dd-5",
      title: "Tax structuring review",
      category: "Financial",
      owner: "Deloitte",
      dueDate: "2025-08-01",
      completed: false,
    },
  ];
}

function buildReadiness(): Readiness {
  return {
    score: 72,
    items: [
      { label: "Investment view drafted", met: true },
      { label: "Financial model complete", met: true },
      { label: "Management meeting held", met: true },
      { label: "Legal DD initiated", met: false },
      { label: "Board pre-approval", met: false },
      { label: "Insurance review", met: false },
    ],
  };
}

function buildActivity(): ActivityEvent[] {
  return [
    {
      id: "act-1",
      timestamp: getIsoTimestamp(-0.1),
      actor: "System",
      description: "Overall deal score updated from 76 to 78 based on new financial evidence",
    },
    {
      id: "act-2",
      timestamp: getIsoTimestamp(-0.5),
      actor: "AI Agent",
      description: "Evidence module 'Margin Analysis' verified with 3-year consistency data",
    },
    {
      id: "act-3",
      timestamp: getIsoTimestamp(-1.2),
      actor: "Sarah Chen",
      description: "Completed commercial reference checks with 3 customers",
    },
    {
      id: "act-4",
      timestamp: getIsoTimestamp(-2.0),
      actor: "Partner",
      description: "Investment view edited — added competitive positioning paragraph",
    },
    {
      id: "act-5",
      timestamp: getIsoTimestamp(-2.8),
      actor: "System",
      description: "Debt profile flagged as CONFLICTING after Credit Suisse report upload",
    },
    {
      id: "act-6",
      timestamp: getIsoTimestamp(-3.5),
      actor: "AI Agent",
      description: "Market sizing evidence verified against Grand View Research 2024 report",
    },
    {
      id: "act-7",
      timestamp: getIsoTimestamp(-4.1),
      actor: "Sarah Chen",
      description: "Legal review of customer contracts marked complete",
    },
    {
      id: "act-8",
      timestamp: getIsoTimestamp(-5.0),
      actor: "Partner",
      description: "Management meeting held — CEO and CFO presented 5-year strategic plan",
    },
    {
      id: "act-9",
      timestamp: getIsoTimestamp(-6.2),
      actor: "AI Agent",
      description: "Revenue verification confirmed via SEC EDGAR 10-K filing extraction",
    },
    {
      id: "act-10",
      timestamp: getIsoTimestamp(-6.9),
      actor: "System",
      description: "Deal created and moved to IC_READY stage",
    },
  ];
}

function buildNextAction(): NextAction {
  return {
    id: "next-1",
    title: "Schedule management reference calls",
    description:
      "Contact 3 named references from management package. Focus on leadership transitions and capital allocation decisions.",
    priority: "high",
  };
}

export function generateMockOverviewData(dealId: string): DealOverview {
  return {
    deal: {
      id: dealId,
      name: "AppFolio, Inc.",
      stage: "IC_READY",
      sector: "PropTech / SaaS",
      hq: "Santa Barbara, CA",
    },
    investmentView: buildInvestmentView(dealId),
    score: buildScore(),
    evidence: buildEvidence(),
    diligence: buildDiligence(),
    readiness: buildReadiness(),
    activity: buildActivity(),
    nextAction: buildNextAction(),
  };
}
