import type {
  PipelineColumn, Metric, RiskFlag, AgentRun, FinRow, ChartBar,
  LBOOutput, HeatRow, Competitor, MoatItem, ResearchItem,
  SourcingResult, MemoSection
} from "@/types";

export const pipelineData: PipelineColumn[] = [
  {
    title: "Sourcing",
    key: "sourcing",
    dot: "#6B7280",
    deals: [
      { id: "1", name: "Vantage Freight", sector: "Logistics", revenue: "$142M", margin: "18.0%", irr: "IRR 21%", irrTier: "amber", updated: "2h ago", statusLabel: "NEW", statusColor: "#6B7280", stage: "sourcing", hq: "Dallas, TX" },
      { id: "2", name: "Apex Health Systems", sector: "Healthcare IT", revenue: "$88M", margin: "31.2%", irr: "IRR 28%", irrTier: "green", updated: "5h ago", statusLabel: "NEW", statusColor: "#6B7280", stage: "sourcing", hq: "Boston, MA" },
      { id: "3", name: "Cedar Grove Dental", sector: "Healthcare Svcs", revenue: "$61M", margin: "23.5%", irr: "IRR 24%", irrTier: "green", updated: "8h ago", statusLabel: "NEW", statusColor: "#6B7280", stage: "sourcing", hq: "Nashville, TN" },
    ],
  },
  {
    title: "Diligence",
    key: "diligence",
    dot: "#2DD4BF",
    deals: [
      { id: "4", name: "Northwind Software", sector: "B2B SaaS", revenue: "$210M", margin: "34.1%", irr: "IRR 24%", irrTier: "green", updated: "1h ago", statusLabel: "QofE", statusColor: "#2DD4BF", stage: "diligence", hq: "Seattle, WA" },
      { id: "5", name: "Cobalt Industrial", sector: "Industrials", revenue: "$355M", margin: "22.4%", irr: "IRR 17%", irrTier: "amber", updated: "3h ago", statusLabel: "LEGAL", statusColor: "#2DD4BF", stage: "diligence", hq: "Chicago, IL" },
      { id: "6", name: "Drayton Components", sector: "Industrials", revenue: "$97M", margin: "19.1%", irr: "IRR 12%", irrTier: "red", updated: "1d ago", statusLabel: "COMM DD", statusColor: "#2DD4BF", stage: "diligence", hq: "Detroit, MI" },
    ],
  },
  {
    title: "IC Ready",
    key: "ic",
    dot: "#C8A96E",
    deals: [
      { id: "7", name: "Meridian Logistics", sector: "Logistics", revenue: "$312M", margin: "26.3%", irr: "IRR 27%", irrTier: "green", updated: "22m ago", statusLabel: "IC THU", statusColor: "#C8A96E", stage: "ic_ready", hq: "Atlanta, GA" },
      { id: "8", name: "Stratos Payments", sector: "Fintech Infra", revenue: "$178M", margin: "41.0%", irr: "IRR 31%", irrTier: "green", updated: "4h ago", statusLabel: "IC THU", statusColor: "#C8A96E", stage: "ic_ready", hq: "New York, NY" },
    ],
  },
  {
    title: "Passed / Closed",
    key: "closed",
    dot: "#6B7280",
    deals: [
      { id: "9", name: "Halcyon Foods", sector: "Consumer Staples", revenue: "$480M", margin: "14.2%", irr: "IRR 9%", irrTier: "red", updated: "2d ago", statusLabel: "PASSED", statusColor: "#EF4444", stage: "passed", hq: "Fresno, CA" },
      { id: "10", name: "Tessera Materials", sector: "Specialty Chem", revenue: "$265M", margin: "28.0%", irr: "IRR 19%", irrTier: "amber", updated: "6d ago", statusLabel: "CLOSED", statusColor: "#10B981", stage: "closed", hq: "Houston, TX" },
    ],
  },
];

export const dealDetail = {
  id: "MRD-0142",
  name: "Meridian Logistics",
  sector: "Logistics / 3PL",
  hq: "Atlanta, GA",
  stage: "IC READY",
};

export const metrics: Metric[] = [
  { label: "Revenue (FY24A)", value: "$312.4M", color: "#C8A96E", delta: "+14.2%", deltaColor: "#10B981", sub: "3yr CAGR" },
  { label: "EBITDA Margin", value: "26.3%", color: "#E8E8F0", delta: "+210 bps", deltaColor: "#10B981", sub: "vs FY22" },
  { label: "Net Debt / EBITDA", value: "4.8x", color: "#F59E0B", delta: "elevated", deltaColor: "#F59E0B", sub: "pre-LBO" },
  { label: "Revenue CAGR", value: "14.2%", color: "#E8E8F0", delta: "3yr", deltaColor: "#6B7280", sub: "organic 9.1%" },
  { label: "FCF Conversion", value: "68%", color: "#E8E8F0", delta: "EBITDA→FCF", deltaColor: "#6B7280", sub: "post-capex" },
  { label: "Entry IRR (base)", value: "27.1%", color: "#10B981", delta: "3.1x MOIC", deltaColor: "#10B981", sub: "5yr hold" },
];

export const riskFlags: RiskFlag[] = [
  { label: "Leverage > 5x at exit (downside)", tier: "red" },
  { label: "Customer concentration — top 3 = 38%", tier: "amber" },
  { label: "Cyclical freight end-market exposure", tier: "amber" },
  { label: "Owner-operator key-man dependency", tier: "amber" },
];

export const agents: AgentRun[] = [
  { name: "Financial Extraction Agent", meta: "CIM + 3yr audited financials", status: "DONE", tier: "done", duration: "12.4s" },
  { name: "LBO Modeling Agent", meta: "Base / upside / downside cases", status: "DONE", tier: "done", duration: "8.1s" },
  { name: "Competitive Mapping Agent", meta: "Scanning 4 comparables…", status: "RUNNING", tier: "running", duration: "—" },
  { name: "Industry Research Agent", meta: "14 sources synthesized", status: "DONE", tier: "done", duration: "41.2s" },
  { name: "Risk Flagging Agent", meta: "4 flags raised", status: "DONE", tier: "done", duration: "3.7s" },
  { name: "Memo Drafting Agent", meta: "Awaiting competitive output", status: "QUEUED", tier: "queued", duration: "—" },
];

export const finYears = ["FY22A", "FY23A", "FY24A", "FY25E"];

export const finRows: FinRow[] = [
  { label: "Revenue", vals: [241.0, 274.8, 312.4, 351.0], weight: 600, accent: true, pct: false, neg: false },
  { label: "Gross Profit", vals: [98.8, 114.0, 131.2, 149.7], weight: 400, accent: false, pct: false, neg: false },
  { label: "EBITDA", vals: [58.0, 69.4, 82.1, 95.1], weight: 600, accent: true, pct: false, neg: false },
  { label: "EBITDA Margin", vals: ["24.1%", "25.3%", "26.3%", "27.1%"], weight: 400, accent: false, pct: true, neg: false },
  { label: "Capex", vals: [-14.5, -16.2, -18.1, -20.4], weight: 400, accent: false, pct: false, neg: true },
  { label: "Unlevered FCF", vals: [38.2, 47.1, 55.8, 64.7], weight: 400, accent: false, pct: false, neg: false },
  { label: "Net Debt", vals: [298.0, 342.0, 394.0, 360.0], weight: 600, accent: false, pct: false, neg: true },
];

export const chartBars: ChartBar[] = [
  { year: "FY22", revH: "69%", ebitdaH: "17%" },
  { year: "FY23", revH: "78%", ebitdaH: "20%" },
  { year: "FY24", revH: "89%", ebitdaH: "23%" },
  { year: "FY25E", revH: "100%", ebitdaH: "27%" },
];

export const competitors: Competitor[] = [
  { name: "Meridian Logistics", tag: "TARGET", target: true, model: "Asset-based 3PL + brokerage", pricing: "Contract + spot blend", segment: "Mid-market shippers", geo: "Southeast US", revenue: "$312M", ownership: "Founder-owned", diff: "Densest SE terminal network" },
  { name: "Continental Freightways", tag: "Public comp", target: false, model: "Asset-heavy LTL", pricing: "Published tariffs", segment: "Enterprise", geo: "National", revenue: "$4.2B", ownership: "Public (NYSE)", diff: "Scale & line-haul density" },
  { name: "Vantage Freight", tag: "Direct comp", target: false, model: "Asset-light brokerage", pricing: "Spot / dynamic", segment: "SMB", geo: "National", revenue: "$142M", ownership: "VC-backed", diff: "Proprietary load-matching" },
  { name: "BlueLane Transport", tag: "Regional", target: false, model: "Dedicated contract", pricing: "Fixed contract", segment: "Mid-market", geo: "Southeast US", revenue: "$208M", ownership: "Sponsor-owned", diff: "Long-term OEM contracts" },
  { name: "NovaShip", tag: "Emerging", target: false, model: "Digital freight platform", pricing: "SaaS + take-rate", segment: "SMB / DTC", geo: "US + Mexico", revenue: "$74M", ownership: "Series C", diff: "API-first tech stack" },
];

export const moatData: MoatItem[] = [
  { label: "Switching Costs", rating: "High", tier: 3, note: "Multi-year dedicated contracts with embedded TMS integration. Replacement requires re-bidding lanes and re-routing capacity — high friction for shippers." },
  { label: "Network Effects", rating: "Medium", tier: 2, note: "Terminal density improves load matching within the Southeast, but the effect is regional and does not extend to a national flywheel." },
  { label: "IP / Technology", rating: "Medium", tier: 2, note: "Proprietary routing and a modern TMS provide a margin edge, though no defensible patents. Tech is a fast-follow risk from digital entrants." },
  { label: "Distribution", rating: "High", tier: 3, note: "Entrenched broker relationships and a 40-year reputation drive low-cost, referral-led customer acquisition versus paid-acquisition entrants." },
];

export const researchItems: ResearchItem[] = [
  { type: "Market", typeTier: "teal", title: "US 3PL Market Outlook 2025–2030", source: "Armstrong & Associates", date: "Aug 2025", snippet: "Domestic 3PL gross revenue projected to grow 6.1% CAGR; asset-based regional carriers gaining share from national LTL on service density." },
  { type: "Filing", typeTier: "gold", title: "Continental Freightways 10-K (FY24)", source: "SEC EDGAR", date: "Feb 2025", snippet: "Public comp trades at 9.8x EV/EBITDA; operating ratio of 88.4%. Useful benchmark for Meridian exit-multiple underwriting." },
  { type: "Expert", typeTier: "teal", title: "Expert call — former VP Ops, regional 3PL", source: "GLG Network", date: "Sep 2025", snippet: "Confirmed 300–400 bps margin opportunity from TMS automation and lane optimization; cited 18–24 month implementation timeline." },
  { type: "News", typeTier: "gray", title: "Southeast freight volumes rebound in Q2", source: "FreightWaves", date: "Jul 2025", snippet: "Regional tonnage up 4.2% QoQ as nearshoring lifts cross-border and SE port activity; supportive of Meridian organic ramp." },
  { type: "Data", typeTier: "gold", title: "Customer concentration analysis", source: "Internal — Diligence", date: "Sep 2025", snippet: "Top 3 customers represent 38% of revenue; top 1 (national retailer) at 19%. Contracts run through 2028 with auto-renewal." },
  { type: "Market", typeTier: "teal", title: "M&A multiples in regional logistics", source: "PitchBook", date: "Jun 2025", snippet: "Median platform entry of 8.2x; bolt-ons clearing 5–6x. Supports buy-and-build arbitrage central to the Meridian thesis." },
];

export const sourcingResults: SourcingResult[] = [
  { name: "Apex Health Systems", sector: "Healthcare IT", revenue: "$88M", margin: "31.2%", fit: 94 },
  { name: "Cedar Grove Dental", sector: "Healthcare Svcs", revenue: "$61M", margin: "23.5%", fit: 89 },
  { name: "Northwind Software", sector: "B2B SaaS", revenue: "$210M", margin: "34.1%", fit: 86 },
  { name: "Lattice Robotics", sector: "Industrial Tech", revenue: "$54M", margin: "27.8%", fit: 81 },
  { name: "Pinnacle Facility Svcs", sector: "Business Svcs", revenue: "$133M", margin: "16.4%", fit: 73 },
  { name: "Orchard Labs", sector: "Diagnostics", revenue: "$45M", margin: "21.0%", fit: 68 },
  { name: "Brightway Logistics", sector: "Logistics", revenue: "$119M", margin: "15.2%", fit: 61 },
];

export const memoSections: MemoSection[] = [
  {
    id: "exec",
    title: "Executive Summary",
    paras: [
      "We recommend that the Investment Committee approve a platform investment in Meridian Logistics, a founder-owned regional third-party logistics provider headquartered in Atlanta. Meridian generated $312M of revenue and $82M of EBITDA (26.3% margin) in FY2024, with a 14% three-year revenue CAGR underpinned by contract-backed, mid-market shipper relationships.",
      "At an 8.0x entry multiple and 60% leverage, the base case underwrites a 27.1% gross IRR and 3.1x MOIC over a five-year hold, driven by EBITDA growth, 300–400 bps of margin expansion, and a fragmented market that supports a buy-and-build strategy at accretive multiples.",
    ],
  },
  {
    id: "overview",
    title: "Company Overview",
    paras: [
      "Founded in 1984, Meridian operates an asset-based trucking fleet complemented by an asset-light brokerage arm, serving over 600 mid-market shippers across the Southeastern United States. The company has built the densest terminal network in its core geography, enabling superior service levels and lane economics relative to national carriers.",
      "Management is led by the founder-CEO, who intends to roll a meaningful portion of proceeds into the transaction. The investment includes a structured leadership-transition plan to mitigate key-man risk over the first 24 months.",
    ],
  },
  {
    id: "industry",
    title: "Industry & Market",
    paras: [
      "The US 3PL market is projected to grow at a 6.1% CAGR through 2030, with regional asset-based carriers gaining share from national LTL providers on the basis of service density and reliability. Nearshoring trends and Southeast port activity provide a structural tailwind to Meridian's core lanes.",
      "The regional logistics landscape remains highly fragmented, with thousands of sub-scale operators — a backdrop well suited to a disciplined consolidation strategy executed at 5–6x bolt-on multiples.",
    ],
  },
  {
    id: "competitive",
    title: "Competitive Position",
    paras: [
      "Meridian competes against national asset-heavy carriers, asset-light digital brokers, and regional contract specialists. Its defensibility rests on high switching costs from embedded TMS integration and multi-year dedicated contracts, reinforced by entrenched distribution and a four-decade reputation.",
      "The principal competitive risk is the encroachment of API-first digital entrants; we view Meridian's modern TMS and terminal density as adequate near-term defenses, with technology investment a priority of the value-creation plan.",
    ],
  },
  {
    id: "financial",
    title: "Financial Analysis",
    hasTable: true,
    tableRows: [
      { k: "FY24 Revenue", v: "$312.4M", color: "#C8A96E" },
      { k: "FY24 EBITDA", v: "$82.1M", color: "#C8A96E" },
      { k: "EBITDA Margin", v: "26.3%", color: "#E8E8F0" },
      { k: "3yr Revenue CAGR", v: "14.2%", color: "#10B981" },
      { k: "FCF Conversion", v: "68%", color: "#E8E8F0" },
      { k: "Recurring Revenue", v: "71%", color: "#10B981" },
    ],
    paras: [
      "Meridian has compounded revenue at 14% with steady margin expansion of ~210 bps over three years, driven by operating leverage and lane-mix optimization. FCF conversion of 68% post-capex supports the leveraged structure, and quality-of-earnings analysis confirms 71% recurring revenue under contract.",
    ],
  },
  {
    id: "lbo",
    title: "LBO Returns",
    hasTable: true,
    tableRows: [
      { k: "Entry Multiple", v: "8.0x", color: "#E8E8F0" },
      { k: "Exit Multiple", v: "11.0x", color: "#E8E8F0" },
      { k: "Leverage", v: "60% of EV", color: "#E8E8F0" },
      { k: "Base-case IRR", v: "27.1%", color: "#10B981" },
      { k: "Base-case MOIC", v: "3.1x", color: "#C8A96E" },
    ],
    paras: [
      "The return profile is balanced across EBITDA growth, margin expansion, and deleveraging, with limited reliance on multiple arbitrage. Returns hold above the fund's 22% hurdle across most of the sensitivity space; the key vulnerability is exit-multiple compression, where a one-turn contraction erodes approximately 500 bps of IRR.",
    ],
  },
  {
    id: "risks",
    title: "Key Risks",
    paras: [
      "Principal risks include: (i) customer concentration, with the top three customers representing 38% of revenue; (ii) cyclical exposure to freight demand; (iii) leverage exceeding 5x in a downside scenario; and (iv) key-man dependency on the founder-CEO.",
      "Mitigants include multi-year contracts running through 2028 with auto-renewal, a conservative leverage runway with a covenant cushion, and a structured management-transition plan with retention incentives.",
    ],
  },
  {
    id: "recommendation",
    title: "Investment Recommendation",
    paras: [
      "We recommend approval of a platform investment in Meridian Logistics at an 8.0x entry multiple, subject to confirmatory quality-of-earnings, legal, and commercial diligence. The opportunity offers an attractive risk-adjusted return with multiple, controllable value-creation levers and a clear consolidation runway.",
      "Proposed next steps: finalize the QoE bridge, secure debt commitments, and submit a binding LOI ahead of the September 18 Investment Committee meeting.",
    ],
  },
];
