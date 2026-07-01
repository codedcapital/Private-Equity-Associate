"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useToast } from "@/components/toast";
import { listDeals, type DealRead } from "@/lib/api";
import { MetricWithInfo } from "@/components/info-flyout";

/* ─── Color helpers ─── */
function tierColor(t: string) {
  return t === "green" ? "#10B981" : t === "amber" ? "#F59E0B" : t === "gray" ? "#6B7280" : "#EF4444";
}
function tierBg(t: string) {
  return t === "green" ? "rgba(16,185,129,0.12)" : t === "amber" ? "rgba(245,158,11,0.11)" : t === "gray" ? "rgba(107,114,128,0.10)" : "rgba(239,68,68,0.11)";
}
function tierBorder(t: string) {
  return t === "green" ? "rgba(16,185,129,0.4)" : t === "amber" ? "rgba(245,158,11,0.4)" : t === "gray" ? "rgba(107,114,128,0.3)" : "rgba(239,68,68,0.4)";
}

/* ─── PE number formatting ─── */
function formatRevenue(v: number | null | undefined): string {
  if (v == null || v === 0) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

function formatEV(v: number | null | undefined): string {
  if (v == null || v === 0) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

function formatMargin(v: number | null | undefined): string {
  if (v == null) return "—";
  const pct = v * 100;
  return `${pct.toFixed(1)}%`;
}

function marginTier(v: number | null | undefined): string {
  if (v == null) return "gray";
  const pct = v * 100;
  if (pct < 0) return "red";
  if (pct < 10) return "amber";
  if (pct < 20) return "gray";
  return "green";
}

function irrTier(irr: number | null | undefined): string {
  if (irr == null) return "gray";
  return irr >= 0.25 ? "green" : irr >= 0.18 ? "amber" : "red";
}

function formatIRR(irr: number | null | undefined): string {
  if (irr == null) return "—";
  return `${(irr * 100).toFixed(1)}%`;
}

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

function stageColor(stage: string): string {
  const map: Record<string, string> = {
    sourcing: "#6B7280",
    diligence: "#2DD4BF",
    ic_ready: "#C8A96E",
    passed: "#EF4444",
    rejected: "#EF4444",
    closed: "#10B981",
  };
  return map[stage] ?? "#6B7280";
}

function columnForStage(stage: string): string {
  const map: Record<string, string> = {
    sourcing: "Sourcing",
    diligence: "Diligence",
    ic_ready: "IC Ready",
    passed: "Passed",
    rejected: "Passed",
    closed: "Closed",
  };
  return map[stage] ?? "Sourcing";
}

function dotForColumn(title: string): string {
  const map: Record<string, string> = {
    Sourcing: "#6B7280",
    Diligence: "#2DD4BF",
    "IC Ready": "#C8A96E",
    Passed: "#EF4444",
    Closed: "#10B981",
  };
  return map[title] ?? "#6B7280";
}

function relativeTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  const now = new Date();
  const mins = Math.floor((now.getTime() - d.getTime()) / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  const months = Math.floor(days / 30);
  return `${months}mo`;
}

export default function DashboardPage() {
  const { addToast } = useToast();
  const [search, setSearch] = useState("");
  const [deals, setDeals] = useState<DealRead[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const q = search.trim().toLowerCase();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listDeals()
      .then((data) => {
        if (cancelled) return;
        setDeals(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to fetch deals:", err);
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
        addToast("error", "Backend offline", "Could not load deals. Ensure the API is running.");
      });
    return () => { cancelled = true; };
  }, [addToast]);

  const pipeline = useMemo(() => {
    const columns = ["Sourcing", "Diligence", "IC Ready", "Passed", "Closed"];

    const dealMap = (deals ?? []).map((d) => {
      const col = columnForStage(d.stage);
      const irr = d.lbo_irr;
      const irrT = irrTier(irr);
      const mgn = d.financials?.ebitda_margin;
      const mgnT = marginTier(mgn);
      return {
        id: String(d.id),
        name: d.company?.name ?? `Deal ${d.id}`,
        ticker: d.company?.ticker ?? "",
        sector: d.company?.sector ?? "Unknown",
        revenue: formatRevenue(d.financials?.revenue),
        margin: formatMargin(mgn),
        marginTier: mgnT,
        ev: formatEV(d.entry_ev),
        irr: formatIRR(irr),
        irrTier: irrT,
        updated: relativeTime(d.last_updated),
        statusLabel: stageLabel(d.stage),
        statusColor: stageColor(d.stage),
        stage: d.stage,
        hq: d.company?.geography ?? "",
        _column: col,
      };
    }).filter((d) => !q || d.name.toLowerCase().includes(q) || d.sector.toLowerCase().includes(q) || d.ticker.toLowerCase().includes(q));

    return columns.map((title) => {
      const colDeals = dealMap.filter((d) => d._column === title);
      return { title, count: colDeals.length, dot: dotForColumn(title), deals: colDeals, empty: colDeals.length === 0 };
    });
  }, [deals, q]);

  const totalDeals = useMemo(() => pipeline.reduce((sum, col) => sum + col.count, 0), [pipeline]);
  const activeDeals = useMemo(() =>
    pipeline
      .filter((c) => c.title !== "Passed" && c.title !== "Closed")
      .reduce((sum, col) => sum + col.count, 0),
    [pipeline]
  );
  const closedDeals = useMemo(() => pipeline.find((c) => c.title === "Closed")?.count ?? 0, [pipeline]);
  const passedDeals = useMemo(() => pipeline.find((c) => c.title === "Passed")?.count ?? 0, [pipeline]);

  return (
    <div>
      {/* Top bar */}
      <div className="h-[52px] flex items-center gap-[14px] px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <div className="flex items-center gap-2 flex-1 max-w-[420px] bg-[#111118] border border-[#1E1E2E] px-[10px] py-[6px]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.8">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search companies, sectors, tickers…"
            className="flex-1 bg-transparent border-none outline-none text-[#E8E8F0] text-[13px] font-sans"
          />
          <span className="font-mono text-[10px] text-[#4b5160] border border-[#1E1E2E] px-[5px] py-[1px]">⌘K</span>
        </div>
        <div className="flex-1" />
        <Link
          href="/sourcing"
          className="flex items-center gap-[7px] bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] px-[13px] py-[7px] text-xs font-medium cursor-pointer hover:border-[#2c2c42] transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" strokeWidth="1.8">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          Sourcing
        </Link>
        <button
          onClick={() => addToast("info", "Add Company", "Use the Sourcing page to discover and add new companies.")}
          className="flex items-center gap-[7px] bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-[14px] py-[7px] text-xs font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add Company
        </button>
      </div>

      {/* Page heading */}
      <div className="flex items-baseline gap-[14px] px-5 pt-[18px] pb-[14px]">
        <h1 className="m-0 text-lg font-semibold tracking-[-0.01em]">IC Pipeline</h1>
        <span className="font-mono text-[11px] text-[#6B7280]">
          {activeDeals} active · {closedDeals} closed · {passedDeals} passed · updated live
        </span>
        <div className="flex-1" />
        <div className="flex gap-[14px] font-mono text-[11px] text-[#6B7280]">
          <span>FUND IV · $2.1B AUM</span>
          <span className="text-[#1E1E2E]">|</span>
          <span>Q3 2025 DEPLOYMENT</span>
        </div>
      </div>

      {error && !loading && (
        <div className="px-5 pb-4">
          <div className="border border-dashed border-[#EF4444] p-[30px] text-center">
            <div className="text-sm text-[#EF4444]">Failed to load deals</div>
            <div className="mt-2 font-mono text-[11px] text-[#4b5160]">{error}</div>
          </div>
        </div>
      )}

      {!loading && !error && totalDeals === 0 && (
        <div className="px-5 pb-4">
          <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
            <div className="text-sm text-[#9aa0ad]">No deals in the pipeline</div>
            <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Use the Sourcing page to discover and add companies.</div>
          </div>
        </div>
      )}

      {q && totalDeals === 0 && deals && deals.length > 0 && (
        <div className="px-5 pb-4">
          <div className="border border-dashed border-[#1E1E2E] p-[30px] text-center">
            <div className="text-sm text-[#9aa0ad]">No deals match &quot;{search}&quot;</div>
            <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Try a different company name, sector, or ticker</div>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="px-5 pb-4">
          <div className="grid grid-cols-5 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-[#0A0A0F] p-3 space-y-2">
                <div className="h-3 bg-[#15151f] w-1/2" />
                <div className="h-20 bg-[#15151f] w-full" />
                <div className="h-20 bg-[#15151f] w-full" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Kanban */}
      {!loading && (
        <div className="overflow-x-auto">
          <div className="grid grid-cols-5 gap-px bg-[#1E1E2E] border-t border-b border-[#1E1E2E] min-w-[1350px]">
            {pipeline.map((col) => (
              <div key={col.title} className="bg-[#0A0A0F] min-h-[calc(100vh-132px)]">
                <div className="flex items-center justify-between px-[14px] py-[11px] border-b border-[#1E1E2E] sticky top-[52px] bg-[#0A0A0F] z-[2]">
                  <div className="flex items-center gap-2">
                    <span className="w-[7px] h-[7px]" style={{ background: col.dot }} />
                    <span className="font-mono text-[11px] font-semibold tracking-[0.08em] uppercase text-[#E8E8F0]">
                      {col.title}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#6B7280]">{col.count}</span>
                </div>
                <div className="flex flex-col gap-2 p-3">
                  {col.deals.map((d) => (
                    <Link
                      key={d.id}
                      href={`/deal/${d.id}`}
                      className="bg-[#111118] border border-[#1E1E2E] p-3 cursor-pointer hover:border-[#2c2c42] transition-colors block"
                    >
                      {/* Name row */}
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[15px] font-semibold text-[#E8E8F0] leading-[1.25]">{d.name}</div>
                          <div className="flex items-center gap-1.5 mt-1">
                            {d.ticker && (
                              <span className="font-mono text-[9px] font-semibold tracking-[0.06em] uppercase text-[#C8A96E] border border-[#1E1E2E] px-[5px] py-[1px]">
                                {d.ticker}
                              </span>
                            )}
                            <span className="font-mono text-[9px] tracking-[0.06em] uppercase text-[#6B7280]">
                              {d.sector}
                            </span>
                          </div>
                        </div>
                        {d.irr !== "—" && (
                          <div
                            className="flex-none font-mono text-[10px] font-semibold px-[6px] py-[2px] border whitespace-nowrap"
                            style={{
                              color: tierColor(d.irrTier),
                              background: tierBg(d.irrTier),
                              borderColor: tierBorder(d.irrTier),
                            }}
                          >
                            {d.irr} IRR
                          </div>
                        )}
                      </div>

                      {/* Metrics row */}
                      <div className="mt-[11px] flex gap-0 border-t border-[#1E1E2E] pt-[9px]">
                        <div className="flex-1">
                          <div className="text-[9px] text-[#6B7280] tracking-[0.06em] uppercase">Revenue</div>
                          <div className="font-mono text-[13px] font-semibold text-[#C8A96E] mt-[2px]">
                            <MetricWithInfo
                              value={d.revenue}
                              label="Revenue"
                              formula="Total revenue from the latest reported financial period."
                              source="Yahoo Finance API → financial snapshot"
                              lastUpdated={d.updated ?? null}
                            />
                          </div>
                        </div>
                        <div className="flex-1 border-l border-[#1E1E2E] pl-[11px]">
                          <div className="text-[9px] text-[#6B7280] tracking-[0.06em] uppercase">EBITDA</div>
                          <div className="font-mono text-[13px] font-semibold mt-[2px]" style={{ color: tierColor(d.marginTier) }}>
                            <MetricWithInfo
                              value={d.margin}
                              label="EBITDA Margin"
                              formula="EBITDA / Revenue × 100. Measures operating profitability before interest, taxes, depreciation and amortization."
                              source="Calculated field (financial snapshot)"
                              lastUpdated={d.updated ?? null}
                            />
                          </div>
                        </div>
                        <div className="flex-1 border-l border-[#1E1E2E] pl-[11px]">
                          <div className="text-[9px] text-[#6B7280] tracking-[0.06em] uppercase">Entry EV</div>
                          <div className="font-mono text-[13px] font-semibold text-[#E8E8F0] mt-[2px]">
                            <MetricWithInfo
                              value={d.ev}
                              label="Entry EV"
                              formula="Entry Enterprise Value recorded for this deal. Represents the total value of the company at acquisition."
                              source="Deal record (pipeline database)"
                              lastUpdated={d.updated ?? null}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Footer row */}
                      <div className="mt-[10px] flex items-center justify-between">
                        <span className="font-mono text-[9px] text-[#6B7280]">{d.updated}</span>
                        <span className="flex items-center gap-1 font-mono text-[9px]" style={{ color: d.statusColor }}>
                          <span className="w-[5px] h-[5px]" style={{ background: d.statusColor }} />
                          {d.statusLabel}
                        </span>
                      </div>
                    </Link>
                  ))}
                  {col.empty && (
                    <div className="border border-dashed border-[#1E1E2E] p-[18px] text-center font-mono text-[10px] text-[#4b5160]">
                      No deals
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
