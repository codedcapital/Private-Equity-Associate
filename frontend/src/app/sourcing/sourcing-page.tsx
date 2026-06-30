"use client";

import { useState } from "react";
import { useToast } from "@/components/toast";
import { runSourcing, createDeal, type SourcingCandidate } from "@/lib/api";

const sourceFilters = [
  { label: "Sector", value: "All" },
  { label: "Geography", value: "North America" },
  { label: "Revenue", value: "$50–300M" },
];

function tierColor(t: string) {
  return t === "green" ? "#10B981" : t === "amber" ? "#F59E0B" : "#EF4444";
}

export default function SourcingPage() {
  const { addToast } = useToast();
  const [thesis, setThesis] = useState("");
  const [thesisFocus, setThesisFocus] = useState(false);
  const [sourcing, setSourcing] = useState<"empty" | "running" | "done">("empty");
  const [results, setResults] = useState<SourcingCandidate[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [adding, setAdding] = useState<Set<string>>(new Set());

  const runSourcingAgent = async () => {
    if (!thesis.trim()) {
      addToast("warning", "Empty thesis", "Enter an investment thesis before running the sourcing agent.");
      return;
    }
    setSourcing("running");
    setResults([]);
    const start = Date.now();

    try {
      const data = await runSourcing(thesis.trim());
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      setElapsed(Number(elapsed));
      setResults(data.candidates ?? []);
      setSourcing("done");
      if (data.candidates && data.candidates.length > 0) {
        addToast("success", "Sourcing complete", `${data.candidates.length} candidates ranked in ${elapsed}s`);
      } else {
        addToast("info", "No matches", "No companies in the database match your thesis. Try broadening your criteria.");
      }
    } catch (err) {
      console.error("Sourcing failed:", err);
      setSourcing("done");
      addToast("error", "Sourcing failed", err instanceof Error ? err.message : "Backend error.");
    }
  };

  const addToPipeline = async (candidate: SourcingCandidate) => {
    if (!candidate.company_id) {
      addToast("warning", "Cannot add", "This candidate has no company ID.");
      return;
    }
    setAdding((prev) => new Set(prev).add(candidate.name));
    try {
      await createDeal(candidate.company_id);
      addToast("success", "Added to pipeline", `${candidate.name} added to the deal pipeline.`);
    } catch (err) {
      console.error("Failed to add to pipeline:", err);
      addToast("error", "Failed to add", err instanceof Error ? err.message : "Backend error.");
    } finally {
      setAdding((prev) => {
        const next = new Set(prev);
        next.delete(candidate.name);
        return next;
      });
    }
  };

  return (
    <div>
      {/* Top bar */}
      <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <h1 className="m-0 text-[15px] font-semibold">Deal Sourcing Agent</h1>
        <span className="font-mono text-[10px] text-[#6B7280] border border-[#1E1E2E] px-[7px] py-[2px] tracking-[0.05em]">
          THESIS-DRIVEN DISCOVERY
        </span>
      </div>

      <div className="max-w-[1080px] px-5 pt-6 pb-[60px]">
        {/* Thesis input */}
        <label className="font-mono text-[11px] tracking-[0.08em] uppercase text-[#6B7280]">
          Investment Thesis
        </label>
        <textarea
          value={thesis}
          onChange={(e) => setThesis(e.target.value)}
          onFocus={() => setThesisFocus(true)}
          onBlur={() => setThesisFocus(false)}
          placeholder="Describe your investment thesis… e.g. Founder-owned, asset-light logistics tech in North America, $50–300M revenue, 20%+ EBITDA margins, fragmented end-market ripe for consolidation."
          className="mt-2 w-full h-24 resize-y bg-[#111118] border outline-none text-[#E8E8F0] text-sm leading-[1.55] px-[15px] py-[13px] transition-colors font-sans"
          style={{ borderColor: thesisFocus ? "#C8A96E" : "#1E1E2E" }}
        />

        {/* Action row */}
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={runSourcingAgent}
            className="flex items-center gap-2 bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-4 py-[9px] text-[13px] font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 3l14 9-14 9V3z" />
            </svg>
            Run Sourcing Agent
          </button>

          {sourcing === "running" && (
            <span className="flex items-center gap-2 font-mono text-xs text-[#2DD4BF]">
              <span className="w-[7px] h-[7px] bg-[#2DD4BF] rounded-full animate-pePulse" />
              Scanning database…
            </span>
          )}

          {sourcing === "done" && (
            <span className="font-mono text-xs text-[#6B7280]">
              {results.length} candidates ranked · {elapsed}s
            </span>
          )}
        </div>

        {/* Results */}
        {sourcing === "done" && results.length > 0 && (
          <div className="mt-7">
            {/* Filter bar */}
            <div className="flex flex-wrap gap-2 items-center pb-3 border-b border-[#1E1E2E]">
              <span className="font-mono text-[10px] tracking-[0.06em] uppercase text-[#6B7280] mr-[2px]">
                Filters
              </span>
              {sourceFilters.map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-[7px] bg-[#111118] border border-[#1E1E2E] px-[10px] py-[6px] text-xs text-[#E8E8F0] cursor-pointer hover:border-[#2c2c42] transition-colors"
                >
                  <span className="text-[#6B7280]">{f.label}:</span>
                  <span>{f.value}</span>
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
              ))}
            </div>

            {/* Results table */}
            <div className="mt-0 border border-[#1E1E2E] border-t-0">
              {/* Header */}
              <div className="grid grid-cols-[46px_1.6fr_1fr_110px_110px_200px_130px] bg-[#0A0A0F] border-b border-[#1E1E2E]">
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">#</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Company</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Sector</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] text-right">Revenue</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] text-right">EBITDA %</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Fit Score</div>
                <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]"></div>
              </div>

              {/* Rows */}
              {results.map((r, i) => {
                const fit = Math.round((r.score ?? 0) * 100);
                const tier = fit >= 85 ? "green" : fit >= 70 ? "amber" : "red";
                const isAdding = adding.has(r.name);
                const revenueStr = r.revenue != null
                  ? r.revenue >= 1e9 ? `$${(r.revenue / 1e9).toFixed(1)}B` : `$${(r.revenue / 1e6).toFixed(0)}M`
                  : "—";
                const marginStr = r.ebitda_margin != null ? `${(r.ebitda_margin * 100).toFixed(1)}%` : "—";
                return (
                  <div
                    key={r.name}
                    className="grid grid-cols-[46px_1.6fr_1fr_110px_110px_200px_130px] border-b border-[#1E1E2E] items-center hover:bg-[#111118] transition-colors"
                  >
                    <div className="px-3 py-[11px] font-mono text-[13px] text-[#6B7280]">
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <div className="px-3 py-[11px] text-[13px] font-semibold text-[#E8E8F0]">{r.name}</div>
                    <div className="px-3 py-[11px] text-xs text-[#9aa0ad]">{r.sector ?? "—"}</div>
                    <div className="px-3 py-[11px] font-mono text-[13px] text-[#C8A96E] text-right">{revenueStr}</div>
                    <div className="px-3 py-[11px] font-mono text-[13px] text-[#E8E8F0] text-right">{marginStr}</div>
                    <div className="px-3 py-[11px] flex items-center gap-[9px]">
                      <div className="flex-1 h-[6px] bg-[#1E1E2E] relative">
                        <div
                          className="absolute left-0 top-0 bottom-0"
                          style={{ width: fit + "%", background: tierColor(tier) }}
                        />
                      </div>
                      <span className="font-mono text-xs w-6 text-right" style={{ color: tierColor(tier) }}>
                        {fit}
                      </span>
                    </div>
                    <div className="px-3 py-2">
                      <button
                        onClick={() => addToPipeline(r)}
                        disabled={isAdding}
                        className="w-full bg-[#111118] border border-[#2c2c42] text-[#2DD4BF] px-2 py-[6px] text-[11px] font-semibold cursor-pointer font-mono tracking-[0.03em] hover:border-[#2DD4BF] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isAdding ? "ADDING…" : "+ PIPELINE"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* No results state */}
        {sourcing === "done" && results.length === 0 && (
          <div className="mt-7 border border-dashed border-[#1E1E2E] p-[30px] text-center">
            <div className="text-sm text-[#9aa0ad]">No candidates found</div>
            <div className="mt-2 font-mono text-[11px] text-[#4b5160]">
              No companies in the database match your thesis. Try broadening your criteria or add more companies via the ingest pipeline.
            </div>
          </div>
        )}

        {/* Empty state */}
        {sourcing === "empty" && (
          <div className="mt-[60px] flex flex-col items-center justify-center gap-[18px] px-5 py-[60px] border border-dashed border-[#1E1E2E]">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <div className="absolute inset-0 border border-[#1E1E2E] rounded-full" />
              <div className="absolute inset-3 border border-[#1E1E2E] rounded-full animate-pePulse" />
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#C8A96E" strokeWidth="1.6">
                <circle cx="11" cy="11" r="7" />
                <path d="M21 21l-4.3-4.3" />
              </svg>
            </div>
            <div className="text-center">
              <div className="text-sm text-[#9aa0ad]">Enter a thesis above to surface candidates</div>
              <div className="mt-[6px] font-mono text-[11px] text-[#4b5160]">
                The agent screens the database against your criteria
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
