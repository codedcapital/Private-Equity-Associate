"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/toast";
import {
  listDeals,
  getDashboardSummary,
  getAttentionDeals,
  getSignals,
  getRecentlyUpdated,
  getActivitySummary,
  getIndustryWatch,
  getOutstandingQuestions,
  globalSearch,
  type AttentionDeal,
  type DashboardSummary,
  type DealRead,
  type SignalItem,
  type RecentItem,
  type ActivitySummary,
  type SectorItem,
  type QuestionItem,
} from "@/lib/api";
import KpiCards from "@/components/dashboard/KpiCards";
import AttentionTable from "@/components/dashboard/AttentionTable";
import PipelineMiniChart from "@/components/dashboard/PipelineMiniChart";
import MarketPulse from "@/components/dashboard/MarketPulse";
import SignalsFeed from "@/components/dashboard/SignalsFeed";
import RecentlyUpdated from "@/components/dashboard/RecentlyUpdated";
import OutstandingQuestions from "@/components/dashboard/OutstandingQuestions";
import DailyActivity from "@/components/dashboard/DailyActivity";
import GlobalSearch from "@/components/dashboard/GlobalSearch";

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    sourcing: "Sourcing",
    diligence: "Diligence",
    ic_ready: "IC Ready",
    passed: "Passed",
    rejected: "Rejected",
    closed: "Closed",
  };
  return map[stage] ?? stage.toUpperCase();
}

export default function DashboardPage() {
  const { addToast } = useToast();
  const router = useRouter();
  const [deals, setDeals] = useState<DealRead[] | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [attentionDeals, setAttentionDeals] = useState<AttentionDeal[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signals, setSignals] = useState<SignalItem[] | null>(null);
  const [recentlyUpdated, setRecentlyUpdated] = useState<RecentItem[] | null>(null);
  const [activitySummary, setActivitySummary] = useState<ActivitySummary | null>(null);
  const [industryWatch, setIndustryWatch] = useState<SectorItem[] | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[] | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    async function fetchData() {
      let summaryData: DashboardSummary | null = null;
      let attentionData: AttentionDeal[] | null = null;
      let dealsData: DealRead[] | null = null;

      // Try new endpoints first; gracefully fall back on 404
      try {
        summaryData = await getDashboardSummary();
      } catch (e: any) {
        if (e?.response?.status !== 404) {
          console.warn("Dashboard summary endpoint not available:", e?.message);
        }
      }

      try {
        const attentionList = await getAttentionDeals();
        attentionData = attentionList.deals ?? [];
      } catch (e: any) {
        if (e?.response?.status !== 404) {
          console.warn("Attention deals endpoint not available:", e?.message);
        }
      }

      // Always fetch base deal data as fallback
      try {
        dealsData = await listDeals();
      } catch (e: any) {
        console.error("Failed to fetch deals:", e);
        setError(e instanceof Error ? e.message : String(e));
        addToast("error", "Backend offline", "Could not load deals. Ensure the API is running.");
        if (!cancelled) setLoading(false);
        return;
      }

      if (cancelled) return;
      setDeals(dealsData);
      if (summaryData) setSummary(summaryData);
      if (attentionData) setAttentionDeals(attentionData);
      setLoading(false);

      // Parallel fetches for new Phase 3 & 4 endpoints (non-blocking)
      try {
        const [signalsRes, recentRes, activityRes, industryRes, questionsRes] = await Promise.all([
          getSignals().catch(() => null),
          getRecentlyUpdated().catch(() => null),
          getActivitySummary().catch(() => null),
          getIndustryWatch().catch(() => null),
          getOutstandingQuestions().catch(() => null),
        ]);
        if (signalsRes) setSignals(signalsRes.signals);
        if (recentRes) setRecentlyUpdated(recentRes.items);
        if (activityRes) setActivitySummary(activityRes);
        if (industryRes) setIndustryWatch(industryRes.sectors);
        if (questionsRes) setQuestions(questionsRes.questions);
      } catch (e) {
        console.warn("Some dashboard extensions failed to load", e);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, [addToast]);

  // Keyboard shortcut: Cmd/Ctrl + K to open global search
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchModalOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);


  // Fallback KPIs computed from deals
  const kpis = useMemo(() => {
    const d = deals ?? [];
    const active = d.filter((deal) => deal.stage !== "passed" && deal.stage !== "closed");
    const icReady = d.filter((deal) => deal.stage === "ic_ready");
    const highIrr = d.filter((deal) => deal.lbo_irr != null && deal.lbo_irr >= 0.25);
    const attention = icReady.length + highIrr.length;

    return {
      activeDeals: summary?.active_deals ?? active.length,
      avgScore: summary?.avg_score ?? 75,
      icReadyCount: summary?.ic_ready_count ?? icReady.length,
      attentionCount: summary?.attention_count ?? attention,
      stageBreakdown:
        summary?.stage_breakdown ??
        d.reduce((acc, deal) => {
          acc[deal.stage] = (acc[deal.stage] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
    };
  }, [deals, summary]);

  // Fallback attention deals computed from deals
  const computedAttentionDeals = useMemo(() => {
    if (attentionDeals != null) return attentionDeals;
    const d = deals ?? [];
    const active = d.filter((deal) => deal.stage !== "passed" && deal.stage !== "closed");

    const sorted = [...active].sort((a, b) => {
      if (a.stage === "ic_ready" && b.stage !== "ic_ready") return -1;
      if (b.stage === "ic_ready" && a.stage !== "ic_ready") return 1;
      return (b.lbo_irr ?? 0) - (a.lbo_irr ?? 0);
    });

    const top = sorted.slice(0, 5);
    const mockChanges = [4, -2, 6, 0, -3];
    const mockDirections: ("up" | "down" | null)[] = ["up", "down", "up", null, "down"];

    return top.map((deal, i) => {
      const score =
        deal.lbo_irr != null ? Math.min(95, Math.round(deal.lbo_irr * 100 * 2.5)) : null;
      const why =
        deal.stage === "ic_ready"
          ? "IC Ready — strong IRR and clean diligence"
          : deal.lbo_irr != null && deal.lbo_irr >= 0.25
            ? "High IRR potential"
            : "Above threshold metrics";

      return {
        deal_id: deal.id,
        company_id: deal.company_id,
        company_name: deal.company?.name ?? `Deal ${deal.id}`,
        ticker: deal.company?.ticker ?? null,
        score,
        score_change: mockChanges[i] ?? 0,
        score_change_direction: mockDirections[i] ?? null,
        stage: deal.stage,
        stage_label: stageLabel(deal.stage),
        why,
        confidence: "LOW",
        updated_at: deal.last_updated ?? deal.created_at ?? new Date().toISOString(),
        financials_score: null,
        risk_score: null,
        moat_score: null,
        market_score: null,
      } as AttentionDeal;
    });
  }, [deals, attentionDeals]);

  const pipelineStages = useMemo(() => {
    const stages = [
      { name: "Sourcing", stage: "sourcing", color: "#6B7280" },
      { name: "Diligence", stage: "diligence", color: "#2DD4BF" },
      { name: "IC Ready", stage: "ic_ready", color: "#C8A96E" },
      { name: "Closed", stage: "closed", color: "#10B981" },
    ];
    return stages.map((s) => ({
      name: s.name,
      count: kpis.stageBreakdown[s.stage] ?? 0,
      color: s.color,
    }));
  }, [kpis.stageBreakdown]);

  if (loading) {
    return (
      <div className="flex flex-col gap-5 p-5">
        <div className="h-8 bg-[#111118] w-[200px]" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-[#111118] border border-[#1E1E2E] p-4 h-[80px]" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 bg-[#111118] border border-[#1E1E2E] h-[200px]" />
          <div className="lg:col-span-1 bg-[#111118] border border-[#1E1E2E] h-[200px]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-5">
        <div className="border border-dashed border-[#EF4444] p-[30px] text-center">
          <div className="text-sm text-[#EF4444]">Failed to load dashboard</div>
          <div className="mt-2 font-mono text-[11px] text-[#4b5160]">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 p-5">
      {/* Greeting */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-[#E8E8F0] tracking-[-0.01em]">
          Good Morning, Aditya
        </h1>
        <div className="font-mono text-[11px] text-[#6B7280]">
          {kpis.activeDeals} active deals · {kpis.attentionCount} require attention · {kpis.icReadyCount} IC-ready this week
        </div>
      </div>

      {/* Portfolio KPIs + Market Pulse */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <KpiCards
            activeDeals={kpis.activeDeals}
            avgScore={kpis.avgScore}
            icReadyCount={kpis.icReadyCount}
            attentionCount={kpis.attentionCount}
          />
        </div>
        <div className="lg:col-span-1">
          <MarketPulse />
        </div>
      </div>

      {/* Attention Table */}
      <div>
        <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">🔥 Deals Requiring Attention</div>
        <AttentionTable
          deals={computedAttentionDeals}
          onDealClick={(id) => router.push(`/deal/${id}`)}
        />
      </div>

      {/* Signals + Recently Updated */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div>
          <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">📡 Latest Signals</div>
          {signals ? (
            <SignalsFeed signals={signals} />
          ) : (
            <div className="bg-[#111118] border border-[#1E1E2E] p-4 text-[11px] text-[#6B7280]">
              Loading signals…
            </div>
          )}
        </div>
        <div>
          <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">📝 Recently Updated</div>
          {recentlyUpdated ? (
            <RecentlyUpdated items={recentlyUpdated} />
          ) : (
            <div className="bg-[#111118] border border-[#1E1E2E] p-4 text-[11px] text-[#6B7280]">
              Loading recent updates…
            </div>
          )}
        </div>
      </div>

      {/* Outstanding Questions + Pipeline Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div>
          <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">✅ Outstanding Questions</div>
          {questions ? (
            <OutstandingQuestions questions={questions} />
          ) : (
            <div className="bg-[#111118] border border-[#1E1E2E] p-4 text-[11px] text-[#6B7280]">
              Loading questions…
            </div>
          )}
        </div>
        <div>
          <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">📊 Pipeline Funnel</div>
          <PipelineMiniChart stages={pipelineStages} />
        </div>
      </div>

      {/* Daily Activity Summary */}
      <div>
        <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">📊 Daily Activity Summary</div>
        {activitySummary ? (
          <DailyActivity summary={activitySummary} />
        ) : (
          <div className="bg-[#111118] border border-[#1E1E2E] p-4 text-[11px] text-[#6B7280]">
            Loading activity summary…
          </div>
        )}
      </div>

      {/* Global Search Trigger */}
      <div className="bg-[#111118] border border-[#1E1E2E] p-4">
        <div className="flex items-center gap-2 bg-[#0A0A0F] border border-[#1E1E2E] px-[10px] py-[8px] cursor-pointer"
             onClick={() => setSearchModalOpen(true)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.8">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <span className="flex-1 text-[#6B7280] text-[13px] font-sans select-none">
            Search across deals, research, and memos…
          </span>
          <span className="text-[10px] text-[#4b5160] bg-[#1E1E2E] px-[6px] py-[2px] rounded font-mono">
            ⌘K
          </span>
        </div>
      </div>

      {/* Global Search Modal */}
      <GlobalSearch
        isOpen={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
        onSearch={globalSearch}
        onResultSelect={(url: string) => {
          setSearchModalOpen(false);
          router.push(url);
        }}
      />
    </div>
  );
}
