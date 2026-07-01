"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/components/toast";
import { ExecutiveBriefing } from "./components/executive-briefing";
import { QuestionCard } from "./components/question-card";
import { SourceConfidenceMatrix } from "./components/source-confidence-matrix";
import { getIntelligenceHub, generateIntelligenceHub } from "@/lib/api";
import type { IntelligenceHub, IntelligenceQuestion, SourceConfidence } from "@/types";

// ── Demo data for the Intelligence Hub ──────────────────────────────────────

const demoHub: IntelligenceHub = {
  hub_id: 1,
  company_id: 1,
  deal_id: 7,
  status: "generated",
  executive_briefing:
    "Meridian Logistics is a founder-owned regional third-party logistics provider with $312M revenue and $82M EBITDA (26.3% margin) in FY2024. The investment thesis rests on three pillars: (1) the densest Southeast terminal network creating high switching costs for mid-market shippers, (2) a fragmented regional logistics market supporting buy-and-build at 5-6x bolt-on multiples, and (3) 300-400 bps of margin expansion from TMS automation and lane optimization. The base-case LBO underwrites a 27.1% IRR and 3.1x MOIC over five years at an 8.0x entry multiple.\n\nKey risks include customer concentration (top 3 = 38% of revenue), cyclical freight demand exposure, and key-man dependency on the founder-CEO. Mitigants include multi-year contracts through 2028 with auto-renewal and a structured management transition plan. The public comp (Continental Freightways) trades at 9.8x EV/EBITDA, suggesting reasonable exit-multiple headroom.",
  questions: [
    {
      id: 1,
      category: "supporting_evidence",
      question: "What evidence supports the growth thesis?",
      answer:
        "Three structural tailwinds support Meridian's growth: (1) the US 3PL market is projected to grow at 6.1% CAGR through 2030, with regional asset-based carriers gaining share from national LTL on service density; (2) nearshoring trends and Southeast port activity provide a structural volume uplift to Meridian's core lanes; (3) the regional logistics landscape remains highly fragmented with thousands of sub-scale operators, creating a disciplined consolidation opportunity at 5-6x bolt-on multiples.",
      confidence: 0.78,
      sort_order: 1,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 1,
          text: "Domestic 3PL gross revenue projected to grow 6.1% CAGR; asset-based regional carriers gaining share from national LTL on service density.",
          source: "Armstrong & Associates",
          source_type: "web",
          source_url: null,
          source_metadata: { report: "US 3PL Market Outlook 2025-2030" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.75,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 2,
          text: "Regional tonnage up 4.2% QoQ as nearshoring lifts cross-border and SE port activity; supportive of Meridian organic ramp.",
          source: "FreightWaves",
          source_type: "web",
          source_url: null,
          source_metadata: { article: "Southeast freight volumes rebound in Q2" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.70,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 3,
          text: "Median platform entry of 8.2x; bolt-ons clearing 5-6x. Supports buy-and-build arbitrage central to the Meridian thesis.",
          source: "PitchBook",
          source_type: "web",
          source_url: null,
          source_metadata: { report: "M&A multiples in regional logistics" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.80,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 2,
      category: "contradictory_evidence",
      question: "What evidence contradicts or risks the investment thesis?",
      answer:
        "Four principal risks challenge the thesis: (1) customer concentration with the top 3 customers representing 38% of revenue creates renewal risk and pricing pressure; (2) cyclical exposure to freight demand means downturns could compress both volume and margin simultaneously; (3) leverage exceeding 5x in a downside scenario strains covenant headroom and could trigger equity impairment; (4) key-man dependency on the founder-CEO creates execution risk during the first 24 months of the hold period.",
      confidence: 0.72,
      sort_order: 2,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 4,
          text: "Top 3 customers represent 38% of revenue; top 1 (national retailer) at 19%. Contracts run through 2028 with auto-renewal.",
          source: "Internal — Diligence",
          source_type: "internal",
          source_url: null,
          source_metadata: { analysis: "Customer concentration analysis" },
          is_supporting: false,
          is_contradictory: true,
          confidence: 0.85,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 5,
          text: "Leverage > 5x at exit in downside scenario. Covenant cushion is thin if EBITDA declines 15%.",
          source: "LBO Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { scenario: "bear" },
          is_supporting: false,
          is_contradictory: true,
          confidence: 0.70,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 6,
          text: "Owner-operator key-man dependency on founder-CEO. Structured transition plan exists but retention incentives are not yet negotiated.",
          source: "Risk Flagging Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { flag: "key_man_dependency" },
          is_supporting: false,
          is_contradictory: true,
          confidence: 0.75,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 3,
      category: "supporting_evidence",
      question: "What does the financial profile look like?",
      answer:
        "Revenue: $312,400,000\nEBITDA: $82,100,000\nEBITDA Margin: 26.3%\nNet Debt / EBITDA: 4.8x\nFCF Conversion: 68% post-capex\nRevenue CAGR: 14.2% (3-year)\nEBITDA margin expanded ~210 bps over three years, driven by operating leverage and lane-mix optimization.",
      confidence: 0.88,
      sort_order: 3,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 7,
          text: "Revenue: $312,400,000 (FY24A). 3-year CAGR of 14.2%.",
          source: "Financial Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { metric: "revenue", period: "FY24" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.90,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 8,
          text: "EBITDA: $82,100,000. Margin: 26.3%. Margin expanded 210 bps vs FY22.",
          source: "Financial Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { metric: "ebitda_margin", period: "FY24" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.90,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 9,
          text: "FCF conversion of 68% post-capex supports leveraged structure.",
          source: "Financial Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { metric: "fcf_conversion" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.85,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 4,
      category: "comparable_companies",
      question: "Who are the key competitors and how do they trade?",
      answer:
        "Meridian competes against national asset-heavy carriers (Continental Freightways), asset-light digital brokers (Vantage Freight), and regional contract specialists (BlueLane Transport). Continental Freightways trades at 9.8x EV/EBITDA with an 88.4% operating ratio. M&A multiples in the sector: median platform entry 8.2x, bolt-ons clearing 5-6x. This supports the buy-and-build arbitrage thesis.",
      confidence: 0.80,
      sort_order: 4,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 10,
          text: "Continental Freightways trades at 9.8x EV/EBITDA; operating ratio of 88.4%. Useful benchmark for Meridian exit-multiple underwriting.",
          source: "SEC EDGAR",
          source_type: "filing",
          source_url: "https://sec.gov/...",
          source_metadata: { filing: "10-K", period: "FY24" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.95,
          created_at: "2025-06-28T10:00:00Z",
        },
        {
          id: 11,
          text: "Median platform entry of 8.2x; bolt-ons clearing 5-6x. Supports buy-and-build arbitrage central to the Meridian thesis.",
          source: "PitchBook",
          source_type: "web",
          source_url: null,
          source_metadata: { report: "M&A multiples in regional logistics" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.80,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 5,
      category: "supporting_evidence",
      question: "What are the projected returns?",
      answer:
        "Base-case IRR: 27.1%\nBase-case MOIC: 3.1x\nEntry multiple: 8.0x\nExit multiple: 11.0x\nLeverage: 60% of EV\nReturns are driven by EBITDA growth, 300-400 bps margin expansion, and deleveraging. The return profile holds above the fund's 22% hurdle across most of the sensitivity space. Key vulnerability is exit-multiple compression — a one-turn contraction erodes approximately 500 bps of IRR.",
      confidence: 0.72,
      sort_order: 5,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 12,
          text: "Base-case IRR: 27.1%, MOIC: 3.1x. Entry: 8.0x, Exit: 11.0x.",
          source: "LBO Agent",
          source_type: "api",
          source_url: null,
          source_metadata: { scenario: "base" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.70,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 6,
      category: "expert_consensus",
      question: "What do industry experts say about the outlook?",
      answer:
        "A former VP of Operations at a regional 3PL confirmed that 300-400 bps of margin expansion is achievable through TMS automation and lane optimization, citing an 18-24 month implementation timeline. This aligns with management's value-creation plan and supports the margin expansion assumption in the LBO model.",
      confidence: 0.82,
      sort_order: 6,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [
        {
          id: 13,
          text: "Confirmed 300-400 bps margin opportunity from TMS automation and lane optimization; cited 18-24 month implementation timeline.",
          source: "GLG Network",
          source_type: "expert_call",
          source_url: null,
          source_metadata: { expert: "former VP Ops, regional 3PL" },
          is_supporting: true,
          is_contradictory: false,
          confidence: 0.85,
          created_at: "2025-06-28T10:00:00Z",
        },
      ],
    },
    {
      id: 7,
      category: "remaining_diligence",
      question: "Validate: Quality of Earnings bridge and revenue recognition",
      answer: null,
      confidence: 0.50,
      sort_order: 10,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [],
    },
    {
      id: 8,
      category: "remaining_diligence",
      question: "Validate: Customer contract renewal terms and pricing escalators",
      answer: null,
      confidence: 0.50,
      sort_order: 11,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [],
    },
    {
      id: 9,
      category: "remaining_diligence",
      question: "Validate: Management transition plan and retention incentives",
      answer: null,
      confidence: 0.50,
      sort_order: 12,
      created_at: "2025-06-28T10:00:00Z",
      evidence: [],
    },
  ],
  source_confidence: [
    {
      id: 1,
      source_name: "SEC EDGAR",
      source_type: "filing",
      confidence_score: 0.95,
      rationale: "Regulatory filing — high verifiability, audited, publicly disclosed",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 2,
      source_name: "Financial Agent",
      source_type: "api",
      confidence_score: 0.85,
      rationale: "Derived from audited financials with deterministic ratio computation",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 3,
      source_name: "Competitive Agent",
      source_type: "api",
      confidence_score: 0.80,
      rationale: "Multi-source enrichment (Wikidata, SEC, Tavily) with cross-validation",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 4,
      source_name: "Research Agent",
      source_type: "api",
      confidence_score: 0.75,
      rationale: "Synthesized from web research and filing semantic search",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 5,
      source_name: "LBO Agent",
      source_type: "api",
      confidence_score: 0.70,
      rationale: "Model-based projection with explicit assumptions and sensitivity",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 6,
      source_name: "GLG Network",
      source_type: "expert_call",
      confidence_score: 0.85,
      rationale: "Expert interview with domain expertise; single source but high credibility",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 7,
      source_name: "PitchBook",
      source_type: "web",
      confidence_score: 0.80,
      rationale: "Proprietary M&A data; reliable for transaction multiples",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 8,
      source_name: "FreightWaves",
      source_type: "web",
      confidence_score: 0.65,
      rationale: "Industry news source; timely but may have editorial bias",
      updated_at: "2025-06-28T10:00:00Z",
    },
    {
      id: 9,
      source_name: "Internal — Diligence",
      source_type: "internal",
      confidence_score: 0.80,
      rationale: "Internal analysis based on management-provided data",
      updated_at: "2025-06-28T10:00:00Z",
    },
  ],
  comparable_companies: [],
  remaining_diligence: [
    "Validate: Quality of Earnings bridge and revenue recognition",
    "Validate: Customer contract renewal terms and pricing escalators",
    "Validate: Management transition plan and retention incentives",
  ],
  generated_at: "2025-06-28T10:00:00Z",
  updated_at: "2025-06-28T10:00:00Z",
};

// ── Main page ───────────────────────────────────────────────────────────────

export default function ResearchPage() {
  const { addToast } = useToast();
  const [hub, setHub] = useState<IntelligenceHub | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [useDemo, setUseDemo] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const filters = [
    { key: "all", label: "All" },
    { key: "supporting_evidence", label: "Supporting" },
    { key: "contradictory_evidence", label: "Contradictory" },
    { key: "expert_consensus", label: "Expert" },
    { key: "comparable_companies", label: "Comps" },
    { key: "remaining_diligence", label: "Open" },
  ];

  useEffect(() => {
    let cancelled = false;

    async function loadHub() {
      try {
        const data = await getIntelligenceHub(1);
        if (!cancelled) {
          setHub(data);
          setUseDemo(false);
        }
      } catch (err) {
        console.log("Hub not found, using demo data:", err);
        if (!cancelled) {
          setHub(demoHub);
          setUseDemo(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadHub();
    return () => { cancelled = true; };
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const data = await generateIntelligenceHub(1);
      setHub(data);
      setUseDemo(false);
      addToast({ message: "Intelligence Hub generated successfully", type: "success" });
    } catch (err) {
      console.error("Generate failed:", err);
      addToast({ message: "Failed to generate hub. Showing demo data.", type: "error" });
      setHub(demoHub);
      setUseDemo(true);
    } finally {
      setGenerating(false);
    }
  };

  const filteredQuestions = hub?.questions.filter((q) => {
    if (activeFilter === "all") return true;
    return q.category === activeFilter;
  }) || [];

  const supportingQuestions = filteredQuestions.filter(
    (q) => q.category === "supporting_evidence"
  );
  const contradictoryQuestions = filteredQuestions.filter(
    (q) => q.category === "contradictory_evidence"
  );
  const otherQuestions = filteredQuestions.filter(
    (q) => !["supporting_evidence", "contradictory_evidence", "remaining_diligence"].includes(q.category)
  );
  const openQuestions = filteredQuestions.filter(
    (q) => q.category === "remaining_diligence"
  );

  return (
    <div>
      {/* Header */}
      <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <h1 className="m-0 text-[15px] font-semibold">Investment Intelligence Hub</h1>
        <span
          className={`font-mono text-[10px] border px-[7px] py-[2px] tracking-[0.05em] ${
            useDemo
              ? "text-[#6B7280] border-[#1E1E2E]"
              : "text-[#C8A96E] border-[#C8A96E]/30"
          }`}
        >
          {useDemo ? "DEMO DATA" : "LIVE INTELLIGENCE"}
        </span>
        <div className="flex-1" />
        {useDemo && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-3 py-1.5 text-[10px] font-medium bg-[#C8A96E]/10 text-[#C8A96E] border border-[#C8A96E]/30 rounded hover:bg-[#C8A96E]/20 transition-colors disabled:opacity-50"
          >
            {generating ? "Generating..." : "Generate from Agents"}
          </button>
        )}
      </div>

      <div className="max-w-[1200px] px-5 pt-5 pb-[60px] space-y-5">
        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-4">
            <div className="bg-[#111118] border border-[#1E1E2E] rounded p-5 space-y-3">
              <div className="h-4 bg-[#1E1E2E] rounded w-1/3" />
              <div className="h-3 bg-[#1E1E2E] rounded w-full" />
              <div className="h-3 bg-[#1E1E2E] rounded w-5/6" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#111118] border border-[#1E1E2E] rounded p-4 space-y-2">
                <div className="h-3 bg-[#1E1E2E] rounded w-3/4" />
                <div className="h-3 bg-[#1E1E2E] rounded w-full" />
              </div>
              <div className="bg-[#111118] border border-[#1E1E2E] rounded p-4 space-y-2">
                <div className="h-3 bg-[#1E1E2E] rounded w-3/4" />
                <div className="h-3 bg-[#1E1E2E] rounded w-full" />
              </div>
            </div>
          </div>
        )}

        {!loading && hub && (
          <>
            {/* Executive Briefing */}
            <ExecutiveBriefing
              briefing={hub.executive_briefing}
              onRegenerate={useDemo ? handleGenerate : undefined}
              isLoading={generating}
            />

            {/* Key assumptions bar */}
            <div className="bg-[#111118] border border-[#1E1E2E] rounded p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="font-mono text-[9px] text-[#6B7280] uppercase tracking-wider">
                  Key Assumptions
                </span>
              </div>
              <div className="flex flex-wrap gap-3">
                {[
                  { label: "Revenue growth", value: "14.2%", conf: 0.78, color: "#10B981" },
                  { label: "Margin expansion", value: "300-400 bps", conf: 0.82, color: "#10B981" },
                  { label: "Exit multiple", value: "11.0x", conf: 0.65, color: "#F59E0B" },
                  { label: "Base IRR", value: "27.1%", conf: 0.72, color: "#10B981" },
                ].map((ass) => (
                  <div
                    key={ass.label}
                    className="flex items-center gap-2 px-3 py-2 border border-[#1E1E2E] rounded bg-[#0A0A0F]"
                  >
                    <span className="text-[11px] text-[#9aa0ad]">{ass.label}</span>
                    <span className="text-[11px] font-medium" style={{ color: ass.color }}>
                      {ass.value}
                    </span>
                    <div className="w-6 h-1 bg-[#1E1E2E] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${ass.conf * 100}%`, backgroundColor: ass.conf >= 0.7 ? "#10B981" : "#F59E0B" }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Filter tabs */}
            <div className="flex flex-wrap gap-2 items-center">
              <span className="font-mono text-[10px] tracking-[0.06em] uppercase text-[#6B7280] mr-1">
                Filter
              </span>
              {filters.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setActiveFilter(f.key)}
                  className="px-[10px] py-[6px] text-[11px] font-medium cursor-pointer transition-colors rounded"
                  style={{
                    background: activeFilter === f.key ? "#111118" : "transparent",
                    border:
                      activeFilter === f.key
                        ? "1px solid #C8A96E"
                        : "1px solid #1E1E2E",
                    color: activeFilter === f.key ? "#C8A96E" : "#6B7280",
                  }}
                >
                  {f.label}
                </button>
              ))}
              <div className="flex-1" />
              <span className="font-mono text-[10px] text-[#4b5160]">
                {filteredQuestions.length} questions
              </span>
            </div>

            {/* Supporting / Contradictory columns */}
            {(activeFilter === "all" || activeFilter === "supporting_evidence" || activeFilter === "contradictory_evidence") && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {(activeFilter === "all" || activeFilter === "supporting_evidence") && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                      <span className="text-[11px] font-medium text-[#10B981]">
                        Supporting Evidence ({supportingQuestions.length})
                      </span>
                    </div>
                    {supportingQuestions.map((q) => (
                      <QuestionCard key={q.id} {...q} />
                    ))}
                  </div>
                )}
                {(activeFilter === "all" || activeFilter === "contradictory_evidence") && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#EF4444]" />
                      <span className="text-[11px] font-medium text-[#EF4444]">
                        Contradictory Evidence ({contradictoryQuestions.length})
                      </span>
                    </div>
                    {contradictoryQuestions.map((q) => (
                      <QuestionCard key={q.id} {...q} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Other categories (Expert, Comps, etc.) */}
            {otherQuestions.length > 0 && (
              <div className="space-y-3">
                {otherQuestions.map((q) => (
                  <QuestionCard key={q.id} {...q} />
                ))}
              </div>
            )}

            {/* Remaining Diligence */}
            {openQuestions.length > 0 && (
              <div className="bg-[#111118] border border-[#1E1E2E] rounded overflow-hidden">
                <div className="px-4 py-3 border-b border-[#1E1E2E]">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#F59E0B]" />
                    <span className="text-[12px] font-semibold text-[#E8E8F0]">
                      Remaining Diligence Questions
                    </span>
                    <span className="font-mono text-[9px] text-[#F59E0B] px-1.5 py-0.5 border border-[#F59E0B]/30 rounded bg-[#F59E0B]/5">
                      {openQuestions.length} open
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-[#1E1E2E]">
                  {openQuestions.map((q, i) => (
                    <div key={q.id} className="px-4 py-3 flex items-start gap-3 hover:bg-[#15151f] transition-colors">
                      <span className="font-mono text-[10px] text-[#6B7280] pt-0.5 flex-none">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="flex-1">
                        <p className="text-[12px] text-[#9aa0ad]">{q.question}</p>
                      </div>
                      <span className="text-[9px] font-medium px-2 py-0.5 rounded border border-[#F59E0B]/30 text-[#F59E0B] bg-[#F59E0B]/5 flex-none">
                        OPEN
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Confidence Matrix */}
            <SourceConfidenceMatrix sources={hub.source_confidence} />

            {/* Footer info */}
            <div className="flex items-center gap-3 pt-2 border-t border-[#1E1E2E]">
              <span className="font-mono text-[9px] text-[#4b5160]">
                Generated: {new Date(hub.generated_at).toLocaleString()}
              </span>
              <span className="text-[#1E1E2E]">|</span>
              <span className="font-mono text-[9px] text-[#4b5160]">
                Status: {hub.status}
              </span>
              <span className="text-[#1E1E2E]">|</span>
              <span className="font-mono text-[9px] text-[#4b5160]">
                Hub ID: {hub.hub_id}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
