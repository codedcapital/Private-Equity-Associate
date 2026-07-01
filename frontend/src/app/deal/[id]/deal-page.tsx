"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Link from "next/link";
import { useToast } from "@/components/toast";
import {
  getDeal,
  getFinancialProfile,
  getLBO,
  getCompetitive,
  getResearch,
  getMemo,
  runPipeline,
  getRunStatus,
  listAgentRuns,
  type DealRead,
  type FinancialProfile,
  type LBOResponse,
  type CompetitiveResponse,
  type ResearchResponse,
  type MemoResponse,
  type AgentRunStatus,
  type AgentRunLog,
} from "@/lib/api";

/* ─── helpers ─── */
function tierColor(t: string) { return t === "green" ? "#10B981" : t === "amber" ? "#F59E0B" : "#EF4444"; }
function tierBg(t: string) { return t === "green" ? "rgba(16,185,129,0.12)" : t === "amber" ? "rgba(245,158,11,0.11)" : "rgba(239,68,68,0.11)"; }
function tierBorder(t: string) { return t === "green" ? "rgba(16,185,129,0.4)" : t === "amber" ? "rgba(245,158,11,0.4)" : "rgba(239,68,68,0.4)"; }
function irrColor(irr: number) { return irr >= 0.25 ? "#10B981" : irr >= 0.18 ? "#F59E0B" : "#EF4444"; }
function irrBg(irr: number) { return irr >= 0.25 ? "rgba(16,185,129,0.14)" : irr >= 0.18 ? "rgba(245,158,11,0.13)" : "rgba(239,68,68,0.13)"; }
function fmtUSD(v: number) { return "$" + (v / 1e6).toFixed(1) + "M"; }
function fmtPct(v: number) { return (v * 100).toFixed(1) + "%"; }

function SkeletonBlock({ lines = 4 }: { lines?: number }) {
  return (
    <div className="flex flex-col gap-[9px] animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-[11px] bg-[#15151f] w-full" style={{ width: i === lines - 1 ? "60%" : "100%" }} />
      ))}
    </div>
  );
}

function TabLoader() {
  return (
    <div className="p-8 flex items-center justify-center">
      <div className="flex items-center gap-3">
        <span className="w-4 h-4 border-2 border-[#2DD4BF] border-t-transparent rounded-full animate-spin" />
        <span className="font-mono text-[11px] text-[#6B7280]">Loading data…</span>
      </div>
    </div>
  );
}

/* ─── LBO engine ─── */
function computeLBO(
  baseEbitda: number,
  baseRev: number,
  p: { entryMult: number; debtPct: number; hold: number; g1: number; g2: number; g3: number; g4: number; g5: number; marginExp: number; exitMult: number },
  entryMultOverride?: number | null,
  exitMultOverride?: number | null
) {
  const entryMult = entryMultOverride != null ? entryMultOverride : p.entryMult;
  const exitMult = exitMultOverride != null ? exitMultOverride : p.exitMult;
  const entryEV = entryMult * baseEbitda;
  const debt = entryEV * p.debtPct / 100;
  const equity = entryEV - debt;
  let rev = baseRev;
  let margin = baseEbitda / baseRev;
  let remaining = debt;
  const growth = [p.g1, p.g2, p.g3, p.g4, p.g5];
  const hold = Math.max(1, Math.round(p.hold));
  for (let y = 0; y < hold; y++) {
    rev = rev * (1 + (growth[Math.min(y, 4)] || 0) / 100);
    margin = margin + p.marginExp / 10000;
    const ebitda = rev * margin;
    const fcf = ebitda * 0.68 - remaining * 0.075;
    remaining = Math.max(0, remaining - Math.max(0, fcf) * 0.8);
  }
  const exitEbitda = rev * margin;
  const exitEV = exitMult * exitEbitda;
  const exitEquity = Math.max(0.01, exitEV - remaining);
  const moic = exitEquity / equity;
  const irr = Math.pow(moic, 1 / hold) - 1;
  return { entryEV, debt, equity, exitEV, exitEquity, exitEbitda, moic, irr, remaining };
}

/* ─── main ─── */
export default function DealPage({ id }: { id: string }) {
  const { addToast } = useToast();
  const [tab, setTab] = useState<"overview" | "financials" | "lbo" | "competitive" | "research" | "memo">("overview");

  /* Backend data */
  const [dealData, setDealData] = useState<DealRead | null>(null);
  const [financialsData, setFinancialsData] = useState<FinancialProfile | null>(null);
  const [lboData, setLboData] = useState<LBOResponse | null>(null);
  const [competitiveData, setCompetitiveData] = useState<CompetitiveResponse | null>(null);
  const [researchData, setResearchData] = useState<ResearchResponse | null>(null);
  const [memoData, setMemoData] = useState<MemoResponse | null>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({
    deal: false,
    financials: false,
    lbo: false,
    competitive: false,
    research: false,
    memo: false,
  });
  const [pipelineRun, setPipelineRun] = useState<{
    runId: string | null;
    status: string | null;
    polling: boolean;
  }>({ runId: null, status: null, polling: false });
  const [agentRuns, setAgentRuns] = useState<AgentRunLog[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);

  /* Compute pipeline completion based on loaded data */
  const pipelineProgress = useMemo(() => {
    const steps = [
      !!financialsData,
      !!researchData,
      !!competitiveData,
      !!lboData,
      !!memoData,
    ];
    const done = steps.filter(Boolean).length;
    return { done, total: steps.length, pct: Math.round((done / steps.length) * 100) };
  }, [financialsData, researchData, competitiveData, lboData, memoData]);

  /* Fetch agent runs for this deal */
  const fetchAgentRuns = useCallback(async () => {
    setRunsLoading(true);
    try {
      const runs = await listAgentRuns(20);
      setAgentRuns(runs);
    } catch {
      // silently fail
    } finally {
      setRunsLoading(false);
    }
  }, []);

  /* Reusable data refresh */
  const refreshData = useCallback(async (companyId: number, memoId?: number | null) => {
    setLoading((l) => ({
      ...l,
      financials: true,
      lbo: true,
      competitive: true,
      research: true,
      memo: !!memoId,
    }));
    const promises: Promise<void>[] = [
      getFinancialProfile(companyId)
        .then((d) => setFinancialsData(d))
        .catch(() => {}),
      getLBO(companyId)
        .then((d) => setLboData(d))
        .catch(() => {}),
      getCompetitive(companyId)
        .then((d) => setCompetitiveData(d))
        .catch(() => {}),
      getResearch(companyId)
        .then((d) => setResearchData(d))
        .catch(() => {}),
    ];
    if (memoId) {
      promises.push(
        getMemo(memoId)
          .then((d) => setMemoData(d))
          .catch(() => {})
      );
    }
    await Promise.all(promises);
    setLoading((l) => ({
      ...l,
      financials: false,
      lbo: false,
      competitive: false,
      research: false,
      memo: false,
    }));
  }, []);

  /* Sync pipeline run status with data availability — stop polling when all data is loaded */
  useEffect(() => {
    if (pipelineProgress.pct === 100 && pipelineRun.polling && pipelineRun.runId) {
      setPipelineRun((prev) => ({ ...prev, status: "complete", polling: false }));
      fetchAgentRuns();
    }
  }, [pipelineProgress.pct, pipelineRun.polling, pipelineRun.runId, fetchAgentRuns]);

  /* Run full pipeline */
  const handleRunPipeline = async () => {
    const companyId = dealData?.company_id;
    const companyName = dealData?.company?.name ?? id;
    if (!companyId) {
      addToast("warning", "No company", "Cannot run pipeline without a company ID.");
      return;
    }
    setPipelineRun({ runId: null, status: "running", polling: true });
    try {
      const res = await runPipeline({ company_name_or_id: companyId });
      setPipelineRun({ runId: res.run_id, status: "running", polling: true });
      addToast("info", "Pipeline started", `Run ${res.run_id} in progress…`);

      // Poll for completion
      let attempts = 0;
      const maxAttempts = 120; // ~2 minutes at 1s intervals
      const poll = async () => {
        if (attempts >= maxAttempts) {
          setPipelineRun({ runId: res.run_id, status: "timeout", polling: false });
          addToast("warning", "Pipeline timeout", "The pipeline is still running. Check back later.");
          fetchAgentRuns();
          return;
        }
        attempts++;
        try {
          const status = await getRunStatus(res.run_id);
          const agentStatus = status.agent_status?.toLowerCase() ?? status.celery_status?.toLowerCase() ?? "running";
          if (agentStatus === "complete" || agentStatus === "completed") {
            setPipelineRun({ runId: res.run_id, status: "complete", polling: false });
            addToast("success", "Pipeline complete", "All agents finished. Refreshing data…");
            // Refresh all data
            await refreshData(companyId, dealData?.memo_id);
            fetchAgentRuns();
            return;
          }
          if (agentStatus === "failed" || agentStatus === "failure") {
            setPipelineRun({ runId: res.run_id, status: "failed", polling: false });
            addToast("error", "Pipeline failed", status.errors?.[0] ?? "Check agent logs for details.");
            fetchAgentRuns();
            return;
          }
          setPipelineRun({ runId: res.run_id, status: agentStatus, polling: true });
          setTimeout(poll, 1500);
        } catch {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch (err) {
      console.error("Pipeline run failed:", err);
      setPipelineRun({ runId: null, status: "failed", polling: false });
      addToast("error", "Pipeline failed", err instanceof Error ? err.message : "Could not start pipeline.");
    }
  };

  /* Fetch on mount / id change */
  useEffect(() => {
    const numericId = parseInt(id, 10);
    if (isNaN(numericId)) {
      addToast("warning", "Invalid deal ID", `Cannot parse "${id}" as a numeric deal ID. Showing mock data.`);
      return;
    }

    async function load() {
      setLoading((l) => ({ ...l, deal: true }));
      try {
        const deal = await getDeal(numericId);
        setDealData(deal);
        const companyId = deal.company_id;
        const memoId = deal.memo_id;

        setLoading((l) => ({
          ...l,
          deal: false,
          financials: true,
          lbo: true,
          competitive: true,
          research: true,
          memo: !!memoId,
        }));

        const promises: Promise<void>[] = [
          getFinancialProfile(companyId)
            .then((d) => setFinancialsData(d))
            .catch(() => {}),
          getLBO(companyId)
            .then((d) => setLboData(d))
            .catch(() => {}),
          getCompetitive(companyId)
            .then((d) => setCompetitiveData(d))
            .catch(() => {}),
          getResearch(companyId)
            .then((d) => setResearchData(d))
            .catch(() => {}),
        ];

        if (memoId) {
          promises.push(
            getMemo(memoId)
              .then((d) => setMemoData(d))
              .catch(() => {})
          );
        }

        await Promise.all(promises);
        fetchAgentRuns();
      } catch (err) {
        console.error("Failed to fetch deal data", err);
        addToast("warning", "Backend unavailable", "Showing mock data for this deal.");
      } finally {
        setLoading((l) => ({
          ...l,
          deal: false,
          financials: false,
          lbo: false,
          competitive: false,
          research: false,
          memo: false,
        }));
      }
    }

    load();
  }, [id, addToast, refreshData]);

  /* Derived active deal */
  const activeDeal = useMemo(() => {
    if (!dealData) {
      return {
        id: id,
        name: "Loading…",
        sector: "",
        hq: "",
        stage: "",
      };
    }
    return {
      id: String(dealData.id),
      name: dealData.company?.name ?? `Deal ${dealData.id}`,
      sector: dealData.company?.sector ?? "",
      hq: dealData.company?.geography ?? "",
      stage: dealData.stage?.toUpperCase() ?? "",
    };
  }, [dealData, id]);

  /* Extract company name from a run's input_data for display */
  const getRunCompanyName = useCallback((run: AgentRunLog): string => {
    const input = (run.input_data || {}) as Record<string, unknown>;
    const cname = input.company_name_or_id;
    if (typeof cname === "string" && isNaN(Number(cname))) {
      return cname;
    }
    const cid = input.company_id || input.company_name_or_id;
    if (String(cid) === String(dealData?.company_id) && activeDeal.name && activeDeal.name !== "Loading…") {
      return activeDeal.name;
    }
    return `Company ${cid}`;
  }, [dealData?.company_id, activeDeal.name]);

  /* Derived metrics from real financials */
  const metrics = useMemo(() => {
    const fp = financialsData;
    const deal = dealData;
    if (!fp && !deal?.lbo_irr) {
      return [];
    }
    const out: { label: string; value: string; color: string; delta: string; deltaColor: string; sub: string }[] = [];
    if (fp?.revenue != null) {
      out.push({
        label: "Revenue (latest)",
        value: `$${(fp.revenue / 1e6).toFixed(1)}M`,
        color: "#C8A96E",
        delta: fp.revenue_growth ? `${(fp.revenue_growth * 100).toFixed(1)}%` : "—",
        deltaColor: fp.revenue_growth && fp.revenue_growth > 0 ? "#10B981" : "#6B7280",
        sub: "YoY growth",
      });
    }
    if (fp?.ebitda_margin != null) {
      out.push({
        label: "EBITDA Margin",
        value: `${(fp.ebitda_margin * 100).toFixed(1)}%`,
        color: "#E8E8F0",
        delta: "",
        deltaColor: "#6B7280",
        sub: "latest period",
      });
    }
    if (fp?.net_debt_ebitda != null) {
      out.push({
        label: "Net Debt / EBITDA",
        value: `${fp.net_debt_ebitda.toFixed(1)}x`,
        color: fp.net_debt_ebitda > 5 ? "#F59E0B" : "#E8E8F0",
        delta: "",
        deltaColor: "#6B7280",
        sub: "leverage",
      });
    }
    if (fp?.fcf_yield != null) {
      out.push({
        label: "FCF Yield",
        value: `${(fp.fcf_yield * 100).toFixed(0)}%`,
        color: "#E8E8F0",
        delta: "",
        deltaColor: "#6B7280",
        sub: "revenue basis",
      });
    }
    if (deal?.lbo_irr != null) {
      out.push({
        label: "Entry IRR (base)",
        value: `${(deal.lbo_irr * 100).toFixed(1)}%`,
        color: "#10B981",
        delta: deal.lbo_moic ? `${deal.lbo_moic.toFixed(1)}x MOIC` : "",
        deltaColor: "#10B981",
        sub: "modeled",
      });
    }
    return out;
  }, [financialsData, dealData]);

  /* Derived research items */
  const researchItems = useMemo(() => {
    if (!researchData?.research) return [];
    const r = researchData.research;
    // Array format (legacy / direct)
    if (Array.isArray(r)) {
      return r.map((item: any, i: number) => ({
        type: item?.type ?? "Data",
        typeTier: item?.typeTier ?? "gray",
        title: item?.title ?? `Research ${i + 1}`,
        source: item?.source ?? "Agent",
        date: item?.date ?? "2025",
        snippet: item?.snippet ?? item?.summary ?? "",
      }));
    }
    // Object format from API: { tam, cagr, growth_drivers, risks, sources, ... }
    if (typeof r === "object") {
      const items: any[] = [];
      const tam = r?.tam ? `$${r.tam}B` : "";
      const cagr = r?.cagr ? `${r.cagr}%` : "";
      const drivers = Array.isArray(r?.growth_drivers) ? r.growth_drivers.join("; ") : "";
      const risks = Array.isArray(r?.risks) ? r.risks.join("; ") : "";
      const summary = `Market TAM: ${tam}, CAGR: ${cagr}. Growth drivers: ${drivers}. Key risks: ${risks}.`;
      const now = new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" });
      items.push({
        type: "Market",
        typeTier: "teal",
        title: "Industry Research Report",
        source: "Industry Research Agent",
        date: now,
        snippet: summary,
      });
      if (Array.isArray(r?.sources)) {
        r.sources.forEach((url: string, i: number) => {
          let host = url;
          try { host = new URL(url).hostname.replace(/^www\./, ""); } catch (_) {}
          items.push({
            type: "Source",
            typeTier: "gray",
            title: `Source ${i + 1}`,
            source: host,
            date: now,
            snippet: url,
          });
        });
      }
      return items;
    }
    return [];
  }, [researchData]);

  /* Derived memo sections */
  const memoSections = useMemo(() => {
    if (!memoData?.memo?.sections) return [];
    const sections = memoData.memo.sections;
    if (typeof sections === "object" && !Array.isArray(sections)) {
      const mapped = Object.entries(sections).map(([id, sec]) => {
        const s = sec as any;
        return {
          id,
          title: s?.title ?? id,
          paras: Array.isArray(s?.paras) ? s.paras : typeof s?.content === "string" ? [s.content] : [],
          hasTable: s?.hasTable ?? false,
          tableRows: s?.tableRows ?? undefined,
        };
      });
      if (mapped.length > 0 && mapped.some((m) => m.paras.length > 0)) return mapped;
    }
    return [];
  }, [memoData]);

  /* Derived competitive items */
  const competitors = useMemo(() => {
    if (!competitiveData?.competitive_map) return [];
    const c = competitiveData.competitive_map;
    // Array format (legacy / direct)
    if (Array.isArray(c)) {
      return c.map((item: any) => ({
        name: item?.name ?? "Unknown",
        tag: item?.tag ?? "Comp",
        target: item?.target ?? false,
        model: item?.model ?? "",
        pricing: item?.pricing ?? "",
        segment: item?.segment ?? "",
        geo: item?.geo ?? "",
        revenue: item?.revenue ?? "",
        ownership: item?.ownership ?? "",
        diff: item?.diff ?? item?.differentiator ?? "",
      }));
    }
    // Object format from API: { competitors: { "Name": { business_model, pricing, ... } } }
    if (typeof c === "object" && c?.competitors) {
      const comps = c.competitors as Record<string, any>;
      return Object.entries(comps).map(([name, item]) => ({
        name: name ?? "Unknown",
        tag: "Comp",
        target: false,
        model: item?.business_model ?? item?.model ?? "",
        pricing: item?.pricing ?? "",
        segment: item?.segment ?? item?.company_size ?? "",
        geo: item?.geography ?? item?.geo ?? "",
        revenue: item?.revenue ?? "",
        ownership: item?.funding ?? item?.ownership ?? "",
        diff: item?.key_differentiators ?? item?.industry ?? item?.diff ?? "",
      }));
    }
    return [];
  }, [competitiveData]);

  /* Derived moat data */
  const moatData = useMemo(() => {
    if (!competitiveData?.competitive_map) return [];
    const c = competitiveData.competitive_map;
    if (typeof c === "object" && !Array.isArray(c) && c?.moat_assessment) {
      const m = c.moat_assessment as any;
      const labels: Record<string, string> = {
        switching_costs: "Switching Costs",
        network_effects: "Network Effects",
        ip_proprietary_tech: "IP / Proprietary Tech",
        distribution_advantages: "Distribution Advantages",
        brand_reputation: "Brand / Reputation",
        overall_moat: "Overall Moat",
      };
      const entries = Object.entries(m)
        .filter(([k]) => k !== "confidence_score" && k !== "data_sources")
        .map(([k, v]) => ({
          label: labels[k] || k.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
          rating: typeof v === "string" ? v.slice(0, 80) : String(v).slice(0, 80),
          tier: 2 as 1 | 2 | 3,
          note: typeof v === "string" ? v : "",
        }));
      return entries;
    }
    return [];
  }, [competitiveData]);

  /* LBO state — initialize from backend data when available */
  const base = { entryMult: 8, debtPct: 60, hold: 5, g1: 9, g2: 8, g3: 7, g4: 6, g5: 5, marginExp: 75, exitMult: 11 };
  const [lbo, setLbo] = useState({ ...base });
  useEffect(() => {
    if (lboData?.scenarios?.base && financialsData?.ebitda) {
      const b = lboData.scenarios.base;
      const entryEv = b.entry_ev ?? (b.entry_equity + b.entry_debt);
      const ebitda = financialsData.ebitda;
      const entryMult = ebitda > 0 ? Math.round(entryEv / ebitda * 10) / 10 : base.entryMult;
      const debtPct = entryEv > 0 ? Math.round((b.entry_debt / entryEv) * 100) : base.debtPct;
      const hold = b.debt_schedule?.length ?? base.hold;
      const exitMult = b.exit_ev && b.ebitda_projection?.length
        ? Math.round((b.exit_ev / b.ebitda_projection[b.ebitda_projection.length - 1]) * 10) / 10
        : base.exitMult;
      const revGrowth = financialsData.revenue_growth ?? 0;
      const g1 = Math.round((revGrowth + 2) * 10) / 10;
      setLbo({
        entryMult, debtPct, hold,
        g1: Math.max(1, g1), g2: Math.max(1, g1 - 1), g3: Math.max(1, g1 - 2),
        g4: Math.max(1, g1 - 3), g5: Math.max(1, g1 - 4),
        marginExp: Math.round((financialsData.ebitda_margin ?? 0.75) * 100),
        exitMult,
      });
    }
  }, [lboData, financialsData]);
  const [analysisOpen, setAnalysisOpen] = useState(true);
  const setLboKey = (key: string, val: string) => {
    const n = parseFloat(val);
    setLbo((s) => ({ ...s, [key]: isNaN(n) ? 0 : n }));
  };

  type MemoStatus = "done" | "pending" | "streaming";
  /* memo generation */
  const [memoStatuses, setMemoStatuses] = useState<Record<string, MemoStatus>>({
    exec: "done", overview: "done", industry: "done", competitive: "done",
    financial: "done", lbo: "done", risks: "done", recommendation: "done",
  });
  const [memoGenerating, setMemoGenerating] = useState(false);
  const [memoEditing, setMemoEditing] = useState<Record<string, boolean>>({});
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const memoRef = useRef<HTMLDivElement>(null);

  const generateMemo = useCallback(() => {
    const ids = ["exec", "overview", "industry", "competitive", "financial", "lbo", "risks", "recommendation"];
    const pending: Record<string, "pending"> = {};
    ids.forEach((id) => (pending[id] = "pending"));
    setMemoStatuses(pending as Record<string, MemoStatus>);
    setMemoGenerating(true);
    addToast("info", "Generating memo", "8 sections will be drafted sequentially…");
    let i = 0;
    const step = () => {
      if (i >= ids.length) {
        setMemoGenerating(false);
        addToast("success", "Memo generated", "All 8 sections are ready for review.");
        return;
      }
      const id = ids[i];
      setMemoStatuses((s) => ({ ...s, [id]: "streaming" }));
      setTimeout(() => {
        setMemoStatuses((s) => ({ ...s, [id]: "done" }));
        i++;
        setTimeout(step, 220);
      }, 520);
    };
    step();
  }, [addToast]);

  const toggleEdit = (secId: string) => {
    setMemoEditing((prev) => ({ ...prev, [secId]: !prev[secId] }));
  };

  const saveEdit = (secId: string) => {
    setMemoEditing((prev) => ({ ...prev, [secId]: false }));
    addToast("success", "Section saved", "Your edits have been applied to the memo.");
  };

  const onEditChange = (secId: string, val: string) => {
    setEditedContent((prev) => ({ ...prev, [secId]: val }));
  };

  const jumpTo = (id: string) => {
    if (!memoRef.current) return;
    const el = memoRef.current.querySelector(`[data-sec="${id}"]`);
    if (el) memoRef.current.scrollTo({ top: (el as HTMLElement).offsetTop - 16, behavior: "smooth" });
  };

  /* Risk flags — computed from financials and research data */
  const riskFlags = useMemo(() => {
    const flags: { label: string; severity: "high" | "medium" | "low"; detail: string }[] = [];
    if (financialsData) {
      if (financialsData.net_debt_ebitda != null && financialsData.net_debt_ebitda > 5) {
        flags.push({ label: "High Leverage", severity: "high", detail: `Net debt / EBITDA at ${financialsData.net_debt_ebitda.toFixed(1)}x` });
      }
      if (financialsData.ebitda_margin != null && financialsData.ebitda_margin < 0.10) {
        flags.push({ label: "Low Margin", severity: "medium", detail: `EBITDA margin ${(financialsData.ebitda_margin * 100).toFixed(1)}%` });
      }
      if (financialsData.revenue_growth != null && financialsData.revenue_growth < 0) {
        flags.push({ label: "Declining Revenue", severity: "high", detail: `Revenue growth ${(financialsData.revenue_growth * 100).toFixed(1)}%` });
      }
      if (financialsData.fcf_yield != null && financialsData.fcf_yield < 0.03) {
        flags.push({ label: "Low FCF Yield", severity: "medium", detail: `FCF yield ${(financialsData.fcf_yield * 100).toFixed(1)}%` });
      }
    }
    if (researchData?.research?.risks) {
      const risks = researchData.research.risks;
      if (typeof risks === "string") {
        flags.push({ label: "Market Risk", severity: "medium", detail: risks.slice(0, 120) });
      } else if (Array.isArray(risks)) {
        risks.slice(0, 3).forEach((r: any) => {
          flags.push({ label: r?.category || "Risk", severity: r?.severity || "medium", detail: String(r?.description || r).slice(0, 120) });
        });
      }
    }
    return flags;
  }, [financialsData, researchData]);

  const tabs = [
    { id: "overview" as const, label: "Overview" },
    { id: "financials" as const, label: "Financials" },
    { id: "lbo" as const, label: "LBO" },
    { id: "competitive" as const, label: "Competitive" },
    { id: "research" as const, label: "Research" },
    { id: "memo" as const, label: "Memo" },
  ];

  /* LBO outputs — use real financials when available */
  const baseEbitda = useMemo(() => {
    const ebitda = financialsData?.ebitda;
    return ebitda && ebitda > 0 ? ebitda : 1.0;
  }, [financialsData]);
  const baseRev = useMemo(() => {
    const rev = financialsData?.revenue;
    return rev && rev > 0 ? rev : 1.0;
  }, [financialsData]);

/* LBO outputs — use backend data when available, else fall back to local computation */
  const lboOutputs = useMemo(() => {
    if (lboData?.lbo_result) {
      const r = lboData.lbo_result;
      const entryEv = r.entry_equity + r.entry_debt;
      return [
        { label: "IRR", value: fmtPct(r.irr), color: irrColor(r.irr), sub: "gross, base case" },
        { label: "MOIC", value: `${r.moic.toFixed(2)}x`, color: "#C8A96E", sub: "multiple of capital" },
        { label: "Entry EV", value: fmtUSD(entryEv), color: "#E8E8F0", sub: `${fmtUSD(r.entry_equity)} equity / ${fmtUSD(r.entry_debt)} debt` },
        { label: "Exit EV", value: fmtUSD(r.exit_ev), color: "#E8E8F0", sub: `exit valuation` },
        { label: "Exit Equity", value: fmtUSD(r.exit_equity), color: "#C8A96E", sub: `${fmtUSD(r.exit_ev - r.exit_equity)} net debt at exit` },
      ];
    }
    const o = computeLBO(baseEbitda, baseRev, lbo);
    return [
      { label: "IRR", value: fmtPct(o.irr), color: irrColor(o.irr), sub: "gross, 5yr" },
      { label: "MOIC", value: o.moic.toFixed(2) + "x", color: "#C8A96E", sub: "multiple of capital" },
      { label: "Entry EV", value: fmtUSD(o.entryEV), color: "#E8E8F0", sub: fmtUSD(o.equity) + " equity" },
      { label: "Exit EV", value: fmtUSD(o.exitEV), color: "#E8E8F0", sub: fmtUSD(o.exitEbitda) + " EBITDA" },
      { label: "Exit Equity", value: fmtUSD(o.exitEquity), color: "#C8A96E", sub: fmtUSD(o.remaining) + " net debt" },
    ];
  }, [lboData, baseEbitda, baseRev, lbo]);

  /* Sensitivity grid — use backend data when available */
  const heatRows = useMemo(() => {
    if (lboData?.sensitivity_grid) {
      const sg = lboData.sensitivity_grid;
      const entryMultiples = sg.entry_multiples || [];
      const exitMultiples = sg.exit_multiples || [];
      const grid = sg.grid || [];
      if (!entryMultiples.length || !exitMultiples.length) return [];
      return exitMultiples.map((ex: number, ri: number) => ({
        exit: ex + "x",
        cells: entryMultiples.map((en: number, ci: number) => {
          const irr = grid[ri]?.[ci] ?? 0;
          const isBase = Math.abs(en - lbo.entryMult) < 0.5 && Math.abs(ex - lbo.exitMult) < 0.5;
          return {
            irr: fmtPct(irr),
            fg: irrColor(irr),
            bg: irrBg(irr),
            border: isBase ? "2px solid #C8A96E" : "1px solid #1E1E2E",
          };
        }),
      }));
    }
    const entryAxis = [7, 8, 9, 10, 11];
    const exitAxis = [13, 12, 11, 10, 9];
    return exitAxis.map((ex) => ({
      exit: ex + "x",
      cells: entryAxis.map((en) => {
        const r = computeLBO(baseEbitda, baseRev, lbo, en, ex);
        const isBase = Math.abs(en - lbo.entryMult) < 0.01 && Math.abs(ex - lbo.exitMult) < 0.01;
        return {
          irr: fmtPct(r.irr), fg: irrColor(r.irr), bg: irrBg(r.irr),
          border: isBase ? "2px solid #C8A96E" : "1px solid #1E1E2E",
        };
      }),
    }));
  }, [lboData, baseEbitda, baseRev, lbo]);

  const growthInputs = [
    { label: "Y1", key: "g1" }, { label: "Y2", key: "g2" }, { label: "Y3", key: "g3" },
    { label: "Y4", key: "g4" }, { label: "Y5", key: "g5" },
  ];

  const doneCount = memoSections.filter((s) => (memoStatuses[s.id] || "done") === "done").length;
  const memoProgress = doneCount + "/" + memoSections.length;
  const memoProgressWidth = (doneCount / memoSections.length * 100) + "%";

  const resTypeColor = { teal: "#2DD4BF", gold: "#C8A96E", gray: "#6B7280" };
  const moatColor: Record<number, string> = { 1: "#EF4444", 2: "#F59E0B", 3: "#10B981" };

  /* Sensitivity grid headers — use backend data when available */
  const sensitivityHeaders = useMemo(() => {
    if (lboData?.sensitivity_grid?.entry_multiples) {
      return lboData.sensitivity_grid.entry_multiples as number[];
    }
    return [7, 8, 9, 10, 11];
  }, [lboData]);

  return (
    <div>
      {/* Deal header */}
      <div className="border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <div className="flex items-center gap-[14px] px-5 py-[14px] pb-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-[6px] bg-transparent border border-[#1E1E2E] text-[#6B7280] px-[9px] py-[6px] text-[11px] cursor-pointer font-mono hover:text-[#E8E8F0] hover:border-[#2c2c42] transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            PIPELINE
          </Link>
          <div>
            <div className="flex items-center gap-[10px]">
              <h1 className="m-0 text-xl font-semibold tracking-[-0.01em]">{activeDeal.name}</h1>
              <span className="font-mono text-[10px] text-[#0A0A0F] bg-[#2DD4BF] px-[7px] py-[2px] font-semibold tracking-[0.05em]">
                {activeDeal.stage}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-[10px] font-mono text-[11px] text-[#6B7280]">
              <span>{activeDeal.sector}</span>
              <span className="text-[#1E1E2E]">|</span>
              <span>{activeDeal.hq}</span>
              <span className="text-[#1E1E2E]">|</span>
              <span>Deal ID {activeDeal.id}</span>
            </div>
          </div>
          <div className="flex-1" />
          <button
            onClick={() => setTab("lbo")}
            className="bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] px-[13px] py-2 text-xs font-medium cursor-pointer hover:border-[#2c2c42] transition-colors"
          >
            Open LBO Model
          </button>
          <button
            onClick={handleRunPipeline}
            disabled={pipelineRun.polling}
            className="flex items-center gap-2 bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-[15px] py-2 text-xs font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 3l14 9-14 9V3z" />
            </svg>
            {pipelineRun.polling ? "RUNNING…" : "Run Full Pipeline"}
          </button>
          {pipelineRun.polling && pipelineRun.status && (
            <span className="flex items-center gap-2 font-mono text-xs text-[#2DD4BF]">
              <span className="w-[7px] h-[7px] bg-[#2DD4BF] rounded-full animate-pulse" />
              Pipeline {pipelineRun.status}…
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-0 px-5">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="px-4 py-[10px] text-[13px] font-medium cursor-pointer transition-colors relative"
              style={{
                color: tab === t.id ? "#E8E8F0" : "#6B7280",
                borderBottom: tab === t.id ? "2px solid #C8A96E" : "2px solid transparent",
              }}
            >
              {t.label}
              {loading[t.id] && (
                <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-[#2DD4BF] rounded-full animate-pulse" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ===== OVERVIEW ===== */}
      {tab === "overview" && (
        <div className="grid grid-cols-[1fr_332px] gap-px bg-[#1E1E2E]">
          <div className="bg-[#0A0A0F] p-5">
            {loading.deal || loading.financials ? (
              <div className="mb-4">
                <SkeletonBlock lines={3} />
              </div>
            ) : null}
            <div className="flex items-center justify-between mb-[13px]">
              <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Key Metrics</h2>
              <span className="font-mono text-[10px] text-[#4b5160]">Live · from Yahoo Finance</span>
            </div>
            <div className="grid grid-cols-3 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
              {metrics.map((m) => (
                <div key={m.label} className="bg-[#111118] px-4 py-[15px]">
                  <div className="text-[10px] text-[#6B7280] tracking-[0.05em] uppercase">{m.label}</div>
                  <div className="font-mono text-[25px] font-semibold mt-[7px] tracking-[-0.01em]" style={{ color: m.color }}>
                    {m.value}
                  </div>
                  <div className="font-mono text-[10px] text-[#6B7280] mt-[5px] flex items-center gap-[5px]">
                    <span style={{ color: m.deltaColor }}>{m.delta}</span>
                    {m.sub}
                  </div>
                </div>
              ))}
            </div>

            <h2 className="mt-6 mb-[11px] font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Risk Flags</h2>
            {riskFlags.length > 0 ? (
              <div className="flex flex-col gap-2">
                {riskFlags.map((f, i) => {
                  const severityColor = f.severity === "high" ? "#EF4444" : f.severity === "medium" ? "#F59E0B" : "#10B981";
                  return (
                    <div key={i} className="flex items-start gap-3 bg-[#111118] border border-[#1E1E2E] px-4 py-3">
                      <span className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: severityColor }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-[13px] text-[#E8E8F0]">{f.label}</span>
                          <span className="font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded" style={{ backgroundColor: severityColor + "20", color: severityColor }}>
                            {f.severity}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#6B7280] mt-1">{f.detail}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="border border-dashed border-[#1E1E2E] p-[18px] text-center font-mono text-[10px] text-[#4b5160]">
                No risk flags generated yet. Run the pipeline to populate.
              </div>
            )}

            <h2 className="mt-6 mb-[11px] font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Thesis Snapshot</h2>
            {financialsData?.revenue ? (
              <div className="bg-[#111118] border border-[#1E1E2E] px-[18px] py-4 text-[13.5px] leading-[1.65] text-[#c4c6d0]">
                {activeDeal.name} generated <span className="text-[#C8A96E]">${(financialsData.revenue / 1e6).toFixed(0)}M in revenue</span>{" "}
                {financialsData.ebitda_margin != null && (
                  <>with an EBITDA margin of <span className="text-[#C8A96E]">{(financialsData.ebitda_margin * 100).toFixed(1)}%</span></>
                )}
                {financialsData.fcf_yield != null && (
                  <>. FCF yield is <span className="text-[#E8E8F0]">{(financialsData.fcf_yield * 100).toFixed(0)}%</span></>
                )}
                {financialsData.net_debt_ebitda != null && (
                  <> with net debt / EBITDA at <span className="text-[#E8E8F0]">{financialsData.net_debt_ebitda.toFixed(1)}x</span></>
                )}. Run the full pipeline to generate a detailed investment thesis, competitive analysis, and LBO model.
              </div>
            ) : (
              <div className="border border-dashed border-[#1E1E2E] p-[18px] text-center font-mono text-[10px] text-[#4b5160]">
                No thesis generated yet. Run the pipeline to populate.
              </div>
            )}
          </div>

          {/* Agent run history */}
          <div className="bg-[#0A0A0F] p-5">
            <div className="flex items-center justify-between mb-[13px]">
              <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Agent Run History</h2>
              <div className="flex items-center gap-3">
                {pipelineRun.polling && (
                  <span className="flex items-center gap-1.5 font-mono text-[10px] text-[#2DD4BF]">
                    <span className="w-[6px] h-[6px] rounded-full bg-[#2DD4BF] animate-pulse" />
                    Live
                  </span>
                )}
                <button
                  onClick={fetchAgentRuns}
                  className="font-mono text-[10px] text-[#6B7280] hover:text-[#E8E8F0] transition-colors cursor-pointer"
                  disabled={runsLoading}
                >
                  {runsLoading ? "Loading…" : "Refresh"}
                </button>
              </div>
            </div>

            {/* Active run */}
            {pipelineRun.runId && (
              <div className="border border-[#1E1E2E] p-[12px] mb-[10px]">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-[10px] text-[#E8E8F0]">
                    Run <span className="text-[#C8A96E]">{pipelineRun.runId.slice(0, 8)}</span>
                  </div>
                  <span
                    className="font-mono text-[9px] uppercase px-[6px] py-[2px] border"
                    style={{
                      color: pipelineRun.status === "complete" ? "#10B981" : pipelineRun.status === "failed" ? "#EF4444" : "#2DD4BF",
                      borderColor: pipelineRun.status === "complete" ? "#10B981" : pipelineRun.status === "failed" ? "#EF4444" : "#2DD4BF",
                      background: pipelineRun.status === "complete" ? "rgba(16,185,129,0.10)" : pipelineRun.status === "failed" ? "rgba(239,68,68,0.10)" : "rgba(45,212,191,0.10)",
                    }}
                  >
                    {pipelineRun.status ?? "running"}
                  </span>
                </div>
                {pipelineRun.polling && (
                  <div className="mt-[8px] font-mono text-[10px] text-[#6B7280]">Polling for status…</div>
                )}
              </div>
            )}

            {/* Run list */}
            {agentRuns.length === 0 && !pipelineRun.runId ? (
              <div className="border border-dashed border-[#1E1E2E] p-[18px] text-center font-mono text-[10px] text-[#4b5160]">
                No agent runs yet. Run the pipeline to populate.
              </div>
            ) : (
              <div className="space-y-[8px]">
                {agentRuns.slice(0, 8).map((run) => (
                  <div key={run.run_id} className="border border-[#1E1E2E] p-[10px] flex items-center justify-between">
                    <div>
                      <div className="font-mono text-[10px] text-[#E8E8F0]">
                        {run.agent_name} <span className="text-[#4b5160]">·</span>{" "}
                        <span className="text-[#C8A96E]">{getRunCompanyName(run)}</span>
                      </div>
                      <div className="font-mono text-[9px] text-[#6B7280] mt-[2px]">
                        {run.run_id.slice(0, 8)} · {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                      </div>
                    </div>
                    <span
                      className="font-mono text-[9px] uppercase px-[5px] py-[1px] border"
                      style={{
                        color: (run.status?.toLowerCase() === "complete" || run.status?.toLowerCase() === "completed") ? "#10B981" : (run.status?.toLowerCase() === "failed" || run.status?.toLowerCase() === "failure") ? "#EF4444" : "#2DD4BF",
                        borderColor: (run.status?.toLowerCase() === "complete" || run.status?.toLowerCase() === "completed") ? "#10B981" : (run.status?.toLowerCase() === "failed" || run.status?.toLowerCase() === "failure") ? "#EF4444" : "#2DD4BF",
                      }}
                    >
                      {run.status ?? "unknown"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Pipeline progress */}
            <div className="mt-[14px] bg-[#111118] border border-[#1E1E2E] p-[14px]">
              <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280]">Pipeline Status</div>
              <div className="mt-[10px] h-2 bg-[#1E1E2E] relative">
                <div
                  className="absolute left-0 top-0 bottom-0 bg-[#C8A96E] transition-all duration-500"
                  style={{ width: `${pipelineProgress.pct}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between font-mono text-[11px]">
                <span className="text-[#6B7280]">
                  {pipelineProgress.done} of {pipelineProgress.total} agents complete
                </span>
                <span className="text-[#C8A96E]">{pipelineProgress.pct}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===== FINANCIALS ===== */}
      {tab === "financials" && (
        <div className="p-5">
          {loading.financials ? (
            <TabLoader />
          ) : (
            <div className="grid grid-cols-[1.4fr_1fr] gap-5">
              <div>
                <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">
                  Financial Snapshot <span className="text-[#4b5160]">($M)</span>
                </h2>
                {financialsData?.revenue ? (
                  <div className="border border-[#1E1E2E]">
                    <div className="grid grid-cols-[1.6fr_1fr] bg-[#0A0A0F] border-b border-[#1E1E2E]">
                      <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Line Item</div>
                      <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] text-right">Latest</div>
                    </div>
                    {[
                      { label: "Revenue", val: financialsData.revenue ? (financialsData.revenue / 1e6).toFixed(1) : "—", accent: true },
                      { label: "EBITDA", val: financialsData.ebitda ? (financialsData.ebitda / 1e6).toFixed(1) : "—", accent: true },
                      { label: "EBITDA Margin", val: financialsData.ebitda_margin ? `${(financialsData.ebitda_margin * 100).toFixed(1)}%` : "—", accent: false },
                      { label: "Net Debt", val: financialsData.net_debt ? (financialsData.net_debt / 1e6).toFixed(1) : "—", accent: false, neg: financialsData.net_debt != null && financialsData.net_debt > 0 },
                      { label: "Net Debt / EBITDA", val: financialsData.net_debt_ebitda ? `${financialsData.net_debt_ebitda.toFixed(1)}x` : "—", accent: false },
                      { label: "FCF", val: financialsData.fcf ? (financialsData.fcf / 1e6).toFixed(1) : "—", accent: false },
                      { label: "FCF Yield", val: financialsData.fcf_yield ? `${(financialsData.fcf_yield * 100).toFixed(1)}%` : "—", accent: false },
                      { label: "Revenue Growth", val: financialsData.revenue_growth ? `${(financialsData.revenue_growth * 100).toFixed(1)}%` : "—", accent: false },
                    ].map((row) => (
                      <div key={row.label} className="grid grid-cols-[1.6fr_1fr] border-b border-[#1E1E2E] hover:bg-[#111118] transition-colors">
                        <div className="px-3 py-[10px] text-[12.5px]" style={{ fontWeight: row.accent ? 600 : 400, color: row.accent ? "#E8E8F0" : "#9aa0ad" }}>
                          {row.label}
                        </div>
                        <div className="px-3 py-[10px] font-mono text-[12.5px] text-right" style={{ fontWeight: row.accent ? 600 : 400, color: row.accent ? "#C8A96E" : row.neg ? "#EF4444" : "#E8E8F0" }}>
                          {row.val}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
                    <div className="text-sm text-[#9aa0ad]">No financial data available</div>
                    <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Run the financials agent to populate historical statements.</div>
                  </div>
                )}
              </div>
              <div>
                <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Revenue & EBITDA Trend</h2>
                <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
                  <div className="text-sm text-[#9aa0ad]">No trend data available</div>
                  <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Multi-year data will appear after running the financials agent.</div>
                </div>
                <div className="mt-4 border border-[#1E1E2E] bg-[#111118] p-4">
                  <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280]">Quality of Earnings</div>
                  <div className="mt-[10px] flex flex-col gap-[9px]">
                    {(() => {
                      const qoeItems = [];
                      if (financialsData?.revenue_growth != null) {
                        qoeItems.push({ label: "Revenue growth trend", value: `${(financialsData.revenue_growth * 100).toFixed(1)}%`, color: financialsData.revenue_growth >= 0 ? "#10B981" : "#EF4444" });
                      }
                      if (financialsData?.ebitda_margin != null) {
                        qoeItems.push({ label: "EBITDA margin", value: `${(financialsData.ebitda_margin * 100).toFixed(1)}%`, color: financialsData.ebitda_margin >= 0.2 ? "#10B981" : "#F59E0B" });
                      }
                      if (financialsData?.fcf_yield != null) {
                        qoeItems.push({ label: "FCF yield", value: `${(financialsData.fcf_yield * 100).toFixed(1)}%`, color: financialsData.fcf_yield >= 0.05 ? "#10B981" : "#C8A96E" });
                      }
                      if (financialsData?.net_debt_ebitda != null) {
                        qoeItems.push({ label: "Net debt / EBITDA", value: `${financialsData.net_debt_ebitda.toFixed(1)}x`, color: financialsData.net_debt_ebitda <= 3 ? "#10B981" : financialsData.net_debt_ebitda <= 5 ? "#F59E0B" : "#EF4444" });
                      }
                      if (qoeItems.length === 0) {
                        return (
                          <div className="text-[11px] text-[#4b5160] font-mono">No quality of earnings data available. Run the pipeline to populate.</div>
                        );
                      }
                      return qoeItems.map((q) => (
                        <div key={q.label} className="flex justify-between text-[12.5px]">
                          <span className="text-[#9aa0ad]">{q.label}</span>
                          <span className="font-mono" style={{ color: q.color }}>{q.value}</span>
                        </div>
                      ));
                    })()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== LBO ===== */}
      {tab === "lbo" && (
        <div className="grid grid-cols-[300px_1fr] gap-px bg-[#1E1E2E]">
          {/* Assumptions */}
          <div className="bg-[#0A0A0F] p-[18px]">
            <h2 className="m-0 mb-[14px] font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Assumptions</h2>
            <div className="flex flex-col gap-[13px]">
              {/* Entry Multiple */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[5px]">
                  Entry Multiple <span className="text-[#6B7280]">(EV/EBITDA)</span>
                </label>
                <div className="flex items-center bg-[#111118] border border-[#1E1E2E]">
                  <input
                    type="number"
                    step="0.5"
                    value={lbo.entryMult}
                    onChange={(e) => setLboKey("entryMult", e.target.value)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-[#C8A96E] font-mono text-sm px-[11px] py-[9px]"
                  />
                  <span className="px-[11px] font-mono text-xs text-[#6B7280]">x</span>
                </div>
              </div>
              {/* Debt % */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[5px]">Debt % of EV</label>
                <div className="flex items-center bg-[#111118] border border-[#1E1E2E]">
                  <input
                    type="number"
                    step="5"
                    value={lbo.debtPct}
                    onChange={(e) => setLboKey("debtPct", e.target.value)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-[#E8E8F0] font-mono text-sm px-[11px] py-[9px]"
                  />
                  <span className="px-[11px] font-mono text-xs text-[#6B7280]">%</span>
                </div>
              </div>
              {/* Hold Period */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[5px]">Hold Period</label>
                <div className="flex items-center bg-[#111118] border border-[#1E1E2E]">
                  <input
                    type="number"
                    step="1"
                    value={lbo.hold}
                    onChange={(e) => setLboKey("hold", e.target.value)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-[#E8E8F0] font-mono text-sm px-[11px] py-[9px]"
                  />
                  <span className="px-[11px] font-mono text-xs text-[#6B7280]">yrs</span>
                </div>
              </div>
              {/* Revenue Growth */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[6px]">Revenue Growth by Year</label>
                <div className="grid grid-cols-5 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
                  {growthInputs.map((g) => (
                    <div key={g.key} className="bg-[#111118]">
                      <div className="font-mono text-[9px] text-[#6B7280] text-center pt-[6px]">{g.label}</div>
                      <input
                        type="number"
                        step="1"
                        value={lbo[g.key as keyof typeof lbo]}
                        onChange={(e) => setLboKey(g.key, e.target.value)}
                        className="w-full bg-transparent border-none outline-none text-[#E8E8F0] font-mono text-xs py-1 pb-2 text-center"
                      />
                    </div>
                  ))}
                </div>
                <div className="text-right font-mono text-[9px] text-[#6B7280] mt-1">% per year</div>
              </div>
              {/* Margin Expansion */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[5px]">EBITDA Margin Expansion</label>
                <div className="flex items-center bg-[#111118] border border-[#1E1E2E]">
                  <input
                    type="number"
                    step="25"
                    value={lbo.marginExp}
                    onChange={(e) => setLboKey("marginExp", e.target.value)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-[#E8E8F0] font-mono text-sm px-[11px] py-[9px]"
                  />
                  <span className="px-[11px] font-mono text-xs text-[#6B7280]">bps/yr</span>
                </div>
              </div>
              {/* Exit Multiple */}
              <div>
                <label className="text-[11px] text-[#9aa0ad] block mb-[5px]">
                  Exit Multiple <span className="text-[#6B7280]">(EV/EBITDA)</span>
                </label>
                <div className="flex items-center bg-[#111118] border border-[#1E1E2E]">
                  <input
                    type="number"
                    step="0.5"
                    value={lbo.exitMult}
                    onChange={(e) => setLboKey("exitMult", e.target.value)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-[#C8A96E] font-mono text-sm px-[11px] py-[9px]"
                  />
                  <span className="px-[11px] font-mono text-xs text-[#6B7280]">x</span>
                </div>
              </div>
              <button
                onClick={() => setLbo({ ...base })}
                className="mt-1 bg-transparent border border-[#1E1E2E] text-[#6B7280] px-2 py-[8px] text-[11px] cursor-pointer font-mono tracking-[0.04em] hover:text-[#E8E8F0] hover:border-[#2c2c42] transition-colors"
              >
                RESET TO BASE CASE
              </button>
            </div>
          </div>

          {/* Outputs + Heatmap + Analysis */}
          <div className="bg-[#0A0A0F] p-5">
            <h2 className="m-0 mb-[13px] font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Returns Summary</h2>
            <div className="grid grid-cols-5 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
              {lboOutputs.map((o) => (
                <div key={o.label} className="bg-[#111118] px-[15px] py-4">
                  <div className="text-[10px] text-[#6B7280] tracking-[0.05em] uppercase">{o.label}</div>
                  <div className="font-mono text-[27px] font-semibold mt-2 tracking-[-0.02em]" style={{ color: o.color }}>
                    {o.value}
                  </div>
                  <div className="font-mono text-[10px] text-[#6B7280] mt-1">{o.sub}</div>
                </div>
              ))}
            </div>

            {/* Sensitivity */}
            <div className="mt-6 flex items-baseline justify-between">
              <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">IRR Sensitivity</h2>
              <span className="font-mono text-[10px] text-[#4b5160]">Entry × Exit multiple · current cell ringed</span>
            </div>
            <div className="mt-[11px] flex gap-0">
              <div className="flex items-center font-mono text-[10px] tracking-[0.1em] uppercase text-[#6B7280] pr-2" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
                Exit Multiple →
              </div>
              <div className="flex-1">
                <table className="w-full border-collapse font-mono">
                  <thead>
                    <tr>
                      <th className="border border-[#1E1E2E] bg-[#0A0A0F] p-[7px] text-[9px] text-[#6B7280] font-medium">IRR</th>
                      {sensitivityHeaders.map((h) => (
                        <th key={h} className="border border-[#1E1E2E] bg-[#0A0A0F] p-[7px_10px] text-[11px] text-[#9aa0ad] font-medium text-center">
                          {h}x
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatRows.map((hr: { exit: string; cells: { irr: string; fg: string; bg: string; border: string }[] }) => (
                      <tr key={hr.exit}>
                        <td className="border border-[#1E1E2E] bg-[#0A0A0F] p-[7px_10px] text-[11px] text-[#9aa0ad] text-center font-medium">{hr.exit}</td>
                        {hr.cells.map((c: { irr: string; fg: string; bg: string; border: string }, ci: number) => (
                          <td
                            key={ci}
                            className="p-[11px_10px] text-[12.5px] text-center font-semibold"
                            style={{ border: c.border, background: c.bg, color: c.fg }}
                          >
                            {c.irr}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="text-center font-mono text-[10px] tracking-[0.1em] uppercase text-[#6B7280] pt-2">
                  ← Entry Multiple →
                </div>
              </div>
            </div>

            {/* Associate Analysis */}
            <div className="mt-6 border border-[#1E1E2E] bg-[#111118]">
              <button
                onClick={() => setAnalysisOpen(!analysisOpen)}
                className="flex items-center gap-[10px] px-4 py-[13px] cursor-pointer w-full text-left hover:bg-[#15151f] transition-colors"
                style={{ borderBottom: analysisOpen ? "1px solid #1E1E2E" : "none" }}
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#2DD4BF"
                  strokeWidth="2"
                  className="transition-transform duration-150"
                  style={{ transform: analysisOpen ? "rotate(90deg)" : "rotate(0deg)" }}
                >
                  <path d="M9 18l6-6-6-6" />
                </svg>
                <span className="font-mono text-[11px] tracking-[0.08em] uppercase text-[#2DD4BF]">Associate Analysis</span>
                <span className="font-mono text-[10px] text-[#6B7280]">· LLM-generated · {lboOutputs[0].value} base case</span>
              </button>
              {analysisOpen && (
                <div className="px-[22px] py-[18px] pl-10">
                  {lboData?.interpretation ? (
                    <p className="m-0 font-serif text-[14.5px] italic leading-[1.72] text-[#c4c6d0]">
                      {lboData.interpretation}
                    </p>
                  ) : (
                    <>
                      <p className="m-0 mb-[13px] font-serif text-[14.5px] italic leading-[1.72] text-[#c4c6d0]">
                        At the current base case, the model returns a <span className="text-[#C8A96E] not-italic">{lboOutputs[0].value} IRR</span> and <span className="text-[#C8A96E] not-italic">{lboOutputs[1].value} MOIC</span> over a {lbo.hold}-year hold. The return is driven by EBITDA growth, margin expansion, and deleveraging. Review the sensitivity grid below to understand how returns shift under different entry and exit multiple assumptions.
                      </p>
                      <p className="m-0 font-serif text-[14.5px] italic leading-[1.72] text-[#c4c6d0]">
                        The sensitivity grid shows returns vary significantly across entry/exit multiples. Key risks to monitor: exit-multiple compression, revenue growth shortfalls, and margin expansion delays. Run the full pipeline to generate a detailed associate analysis with company-specific risks and recommendations.
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== COMPETITIVE ===== */}
      {tab === "competitive" && (
        <div className="p-5">
          {loading.competitive ? (
            <TabLoader />
          ) : competitors.length === 0 ? (
            <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
              <div className="text-sm text-[#9aa0ad]">No competitive data available</div>
              <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Run the competitive agent to map the landscape.</div>
            </div>
          ) : (
            <>
              <div className="flex items-baseline justify-between mb-[13px]">
                <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Competitive Landscape</h2>
                <span className="font-mono text-[10px] text-[#4b5160]">{competitors.length} companies · click column headers to sort</span>
              </div>
              <div className="border border-[#1E1E2E] overflow-x-auto">
                <table className="w-full border-collapse min-w-[980px]">
                  <thead>
                    <tr className="bg-[#0A0A0F]">
                      <th className="border-b border-r border-[#1E1E2E] p-[10px_13px] text-left font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] sticky left-0 bg-[#0A0A0F] min-w-[160px]">
                        Company
                      </th>
                      {["Business Model", "Pricing", "Customer Segment", "Geographies", "Est. Revenue", "Ownership", "Key Differentiator"].map((cc) => (
                        <th
                          key={cc}
                          className="border-b border-[#1E1E2E] p-[10px_13px] text-left font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] cursor-pointer whitespace-nowrap hover:text-[#E8E8F0]"
                        >
                          {cc}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {competitors.map((c) => (
                      <tr
                        key={c.name}
                        className="hover:bg-[#15151f] transition-colors"
                        style={{ background: c.target ? "rgba(200,169,110,0.06)" : "transparent" }}
                      >
                        <td className="border-b border-r border-[#1E1E2E] p-[13px] sticky left-0" style={{ background: c.target ? "#15130d" : "#0A0A0F" }}>
                          <div className="text-[13px] font-semibold" style={{ color: c.target ? "#C8A96E" : "#E8E8F0" }}>{c.name}</div>
                          <div className="font-mono text-[10px] mt-[2px]" style={{ color: c.target ? "#C8A96E" : "#6B7280" }}>{c.tag}</div>
                        </td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.model || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.pricing || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.segment || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.geo || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] font-mono text-[12.5px] text-[#C8A96E] text-right whitespace-nowrap">{c.revenue || <span className="text-[#4b5160] italic text-xs font-sans">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.ownership || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                        <td className="border-b border-[#1E1E2E] p-[13px] text-xs text-[#c4c6d0]">{c.diff || <span className="text-[#4b5160] italic">Not disclosed</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h2 className="mt-[26px] mb-[13px] font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Moat Assessment</h2>
              <div className="grid grid-cols-4 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
                {moatData.map((m) => (
                  <div key={m.label} className="bg-[#111118] p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-[12.5px] font-semibold text-[#E8E8F0]">{m.label}</span>
                      <span className="flex items-center gap-[6px] font-mono text-[10px] font-semibold tracking-[0.05em] uppercase" style={{ color: moatColor[m.tier] }}>
                        <span className="w-[7px] h-[7px]" style={{ background: moatColor[m.tier] }} />
                        {m.rating}
                      </span>
                    </div>
                    <div className="mt-[9px] flex gap-[3px]">
                      <div className="flex-1 h-[3px]" style={{ background: m.tier >= 1 ? moatColor[m.tier] : "#1E1E2E" }} />
                      <div className="flex-1 h-[3px]" style={{ background: m.tier >= 2 ? moatColor[m.tier] : "#1E1E2E" }} />
                      <div className="flex-1 h-[3px]" style={{ background: m.tier >= 3 ? moatColor[m.tier] : "#1E1E2E" }} />
                    </div>
                    <p className="mt-[11px] m-0 text-xs leading-[1.6] text-[#9aa0ad]">{m.note}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ===== RESEARCH ===== */}
      {tab === "research" && (
        <div className="p-5 max-w-[1000px]">
          {loading.research ? (
            <TabLoader />
          ) : researchItems.length === 0 ? (
            <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
              <div className="text-sm text-[#9aa0ad]">No research available</div>
              <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Run the research agent to gather market intelligence.</div>
            </div>
          ) : (
            <>
              <div className="flex items-baseline justify-between mb-[13px]">
                <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Research Library</h2>
                <span className="font-mono text-[10px] text-[#4b5160]">{researchItems.length} sources · gathered by Industry Research Agent</span>
              </div>
              <div className="flex flex-col gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
                {researchItems.map((rs, i) => (
                  <div key={rs.title} className="bg-[#111118] p-[15px_16px] flex gap-[14px] hover:bg-[#15151f] transition-colors">
                    <div className="flex-none w-[40px] font-mono text-[10px] text-[#6B7280] pt-[2px]">{String(i + 1).padStart(2, "0")}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-[9px]">
                        <span
                          className="font-mono text-[9px] font-semibold tracking-[0.05em] uppercase px-[6px] py-[2px] border"
                          style={{
                            color: resTypeColor[rs.typeTier as keyof typeof resTypeColor],
                            borderColor: resTypeColor[rs.typeTier as keyof typeof resTypeColor] === "#6B7280" ? "#1E1E2E" : resTypeColor[rs.typeTier as keyof typeof resTypeColor],
                          }}
                        >
                          {rs.type}
                        </span>
                        <span className="text-[13.5px] font-semibold text-[#E8E8F0]">{rs.title}</span>
                      </div>
                      <p className="m-0 mt-2 text-[12.5px] leading-[1.6] text-[#9aa0ad]">{rs.snippet}</p>
                      <div className="mt-2 flex items-center gap-[10px] font-mono text-[10px] text-[#6B7280]">
                        <span>{rs.source}</span>
                        <span className="text-[#1E1E2E]">|</span>
                        <span>{rs.date}</span>
                      </div>
                    </div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.7" className="flex-none mt-[3px]">
                      <path d="M7 17L17 7M17 7H8M17 7v9" />
                    </svg>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ===== MEMO ===== */}
      {tab === "memo" && (
        <div className="grid grid-cols-[248px_1fr] gap-px bg-[#1E1E2E]">
          {/* Jump nav */}
          <div className="bg-[#0A0A0F] py-[18px] sticky top-[115px] self-start h-[calc(100vh-115px)] overflow-y-auto">
            <div className="flex items-center justify-between px-[18px] pb-3">
              <h2 className="m-0 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">Contents</h2>
              {memoGenerating && (
                <span className="font-mono text-[10px] text-[#2DD4BF]">{memoProgress}</span>
              )}
            </div>
            <div className="flex flex-col">
              {memoSections.map((s, i) => {
                const status = memoStatuses[s.id] || "done";
                const dot = status === "done" ? "#10B981" : status === "streaming" ? "#2DD4BF" : "#1E1E2E";
                return (
                  <button
                    key={s.id}
                    onClick={() => jumpTo(s.id)}
                    className="flex items-center gap-[10px] px-[18px] py-2 cursor-pointer text-[12.5px] hover:bg-[#111118] hover:text-[#E8E8F0] transition-colors text-left"
                    style={{ color: status === "streaming" ? "#E8E8F0" : "#9aa0ad" }}
                  >
                    <span
                      className="w-[7px] h-[7px] flex-none"
                      style={{ background: dot, ...(status === "streaming" ? { animation: "pePulse 1s infinite" } : {}) }}
                    />
                    <span className="font-mono text-[10px] text-[#4b5160] w-4">{String(i + 1).padStart(2, "0")}</span>
                    <span className="flex-1">{s.title}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Memo body */}
          <div className="bg-[#0A0A0F]">
            <div className="flex items-center gap-3 px-8 py-[14px] border-b border-[#1E1E2E] sticky top-[115px] bg-[#0A0A0F] z-[3]">
              <button
                onClick={generateMemo}
                className="flex items-center gap-2 bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-[14px] py-2 text-xs font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v6m0 0l3-3m-3 3L9 5M5 13l1.5 7h11L19 13" />
                </svg>
                {memoGenerating ? "Generating…" : "Generate Memo"}
              </button>
              {memoGenerating && (
                <span className="flex-1 flex items-center gap-[10px]">
                  <span className="flex-1 max-w-[280px] h-[5px] bg-[#1E1E2E] relative">
                    <span
                      className="absolute left-0 top-0 bottom-0 bg-[#2DD4BF] transition-[width] duration-300"
                      style={{ width: memoProgressWidth }}
                    />
                  </span>
                  <span className="font-mono text-[11px] text-[#2DD4BF]">{memoProgress} sections</span>
                </span>
              )}
              <div className="flex-1" />
              <span className="font-mono text-[10px] text-[#6B7280]">CONFIDENTIAL · IC MEMORANDUM</span>
              <button className="flex items-center gap-[7px] bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] px-[13px] py-2 text-xs cursor-pointer hover:border-[#2c2c42] transition-colors">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M12 3v12m0 0l4-4m-4 4l-4-4M5 21h14" />
                </svg>
                Download PDF
              </button>
            </div>

            {loading.memo ? (
              <div className="p-8">
                <TabLoader />
              </div>
            ) : (
              <div ref={memoRef} className="h-[calc(100vh-168px)] overflow-y-auto relative">
                <div className="max-w-[760px] mx-auto px-[48px] pt-10 pb-20">
                  <div className="border-b border-[#1E1E2E] pb-6 mb-2">
                    <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-[#C8A96E]">Investment Committee Memorandum</div>
                    <h1 className="mt-[14px] mb-2 font-serif text-[34px] font-semibold text-[#E8E8F0] tracking-[-0.01em]">{activeDeal.name}</h1>
                    <div className="font-serif text-[15px] text-[#9aa0ad] italic">Project {activeDeal.name.split(" ")[0]} · {activeDeal.sector}</div>
                    <div className="mt-4 flex gap-6 font-mono text-[11px] text-[#6B7280]">
                      <span>PREPARED BY: AI Pipeline</span>
                      <span>DATE: {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                      <span>FUND IV</span>
                    </div>
                  </div>

                  {memoSections.length === 0 ? (
                    <div className="pt-[30px] border border-dashed border-[#1E1E2E] p-[30px] text-center">
                      <div className="text-sm text-[#9aa0ad]">No memo generated yet</div>
                      <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Click "Generate Memo" to draft an IC memorandum.</div>
                    </div>
                  ) : (
                    memoSections.map((sec, si) => {
                    const status = memoStatuses[sec.id] || "done";
                    const isEditing = memoEditing[sec.id];
                    const edited = editedContent[sec.id];
                    return (
                      <div key={sec.id} data-sec={sec.id} className="pt-[30px] group">
                        <div className="flex items-baseline gap-3 justify-between">
                          <div className="flex items-baseline gap-3">
                            <span className="font-mono text-xs text-[#6B7280]">{String(si + 1).padStart(2, "0")}.</span>
                            <h2 className="m-0 font-serif text-[21px] font-semibold text-[#C8A96E] tracking-[-0.005em]">{sec.title}</h2>
                          </div>
                          {status === "done" && !memoGenerating && (
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                              {isEditing ? (
                                <button
                                  onClick={() => saveEdit(sec.id)}
                                  className="flex items-center gap-1 bg-[#10B981] text-[#0A0A0F] px-2 py-[4px] text-[10px] font-semibold cursor-pointer"
                                >
                                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                    <path d="M5 13l4 4L19 7" />
                                  </svg>
                                  Save
                                </button>
                              ) : (
                                <button
                                  onClick={() => toggleEdit(sec.id)}
                                  className="flex items-center gap-1 bg-[#111118] border border-[#1E1E2E] text-[#6B7280] px-2 py-[4px] text-[10px] cursor-pointer hover:text-[#E8E8F0] hover:border-[#2c2c42] transition-colors"
                                >
                                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                                  </svg>
                                  Edit
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                        {status === "pending" && (
                          <div className="mt-4 flex flex-col gap-[9px]">
                            <div className="h-[11px] bg-[#15151f] w-full" />
                            <div className="h-[11px] bg-[#15151f] w-[92%]" />
                            <div className="h-[11px] bg-[#15151f] w-[96%]" />
                            <div className="h-[11px] bg-[#15151f] w-[60%]" />
                          </div>
                        )}
                        {status !== "pending" && (
                          <div className="mt-[13px]">
                            {isEditing ? (
                              <textarea
                                className="w-full min-h-[200px] bg-[#111118] border border-[#1E1E2E] text-[#d4d6de] font-serif text-[15.5px] leading-[1.78] px-4 py-3 outline-none focus:border-[#C8A96E] transition-colors resize-y"
                                defaultValue={edited || sec.paras.join("\n\n")}
                                onChange={(e) => onEditChange(sec.id, e.target.value)}
                              />
                            ) : (
                              <>
                                {sec.paras.map((p: string, pi: number) => (
                                  <p key={pi} className="m-0 mb-[15px] font-serif text-[15.5px] leading-[1.78] text-[#d4d6de]">
                                    {edited ? edited.split("\n\n")[pi] || p : p}
                                  </p>
                                ))}
                                {sec.hasTable && sec.tableRows && (
                                  <div className="my-[18px] border border-[#1E1E2E]">
                                    {sec.tableRows.map((tr: { k: string; v: string; color: string }, tri: number) => (
                                      <div
                                        key={tri}
                                        className="flex justify-between px-[14px] py-[10px] border-b border-[#1E1E2E]"
                                        style={{ background: tri % 2 === 0 ? "transparent" : "#111118" }}
                                      >
                                        <span className="text-[13px] text-[#9aa0ad]">{tr.k}</span>
                                        <span className="font-mono text-[13px]" style={{ color: tr.color }}>{tr.v}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {status === "streaming" && (
                                  <span className="inline-block w-2 h-4 bg-[#2DD4BF] animate-peBlink align-middle" />
                                )}
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                  )}

                  <div className="mt-12 pt-5 border-t border-[#1E1E2E] font-mono text-[10px] text-[#4b5160] leading-[1.7]">
                    This memorandum is strictly confidential and intended solely for members of the Investment Committee. It contains forward-looking projections that are inherently uncertain. Figures derived from agent-extracted data; review source documents before reliance.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
