"use client";

import { useState } from "react";
import type { CoverageMetrics } from "@/lib/api";

export function MarketCoveragePanel({ coverage }: { coverage: CoverageMetrics }) {
  const [expandedReason, setExpandedReason] = useState<string | null>(null);

  const funnel = [
    { label: "Universe", count: coverage.universe, color: "#6B7280" },
    { label: "Financial Match", count: coverage.financial_match, color: "#2DD4BF" },
    { label: "Strategic Match", count: coverage.strategic_match, color: "#C8A96E" },
    { label: "High Conviction", count: coverage.high_conviction, color: "#10B981" },
  ];

  const breakdownKeys = Object.keys(coverage.breakdown).filter(
    (k) => coverage.breakdown[k] > 0
  );

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[#E8E8F0]">Market Coverage</h2>
        <p className="text-[11px] text-[#6B7280] mt-0.5">
          How the universe filters down to investable opportunities
        </p>
      </div>

      <div className="border border-[#1E1E2E] bg-[#111118]">
        {/* Funnel counts */}
        <div className="grid grid-cols-4 divide-x divide-[#1E1E2E]">
          {funnel.map((step) => (
            <div key={step.label} className="px-4 py-4 text-center">
              <div
                className="text-[22px] font-mono font-semibold"
                style={{ color: step.color }}
              >
                {step.count.toLocaleString()}
              </div>
              <div className="text-[10px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mt-1">
                {step.label}
              </div>
            </div>
          ))}
        </div>

        {/* Why only X passed? */}
        {breakdownKeys.length > 0 && (
          <div className="border-t border-[#1E1E2E] px-5 py-4">
            <div className="text-[11px] text-[#9aa0ad] mb-2">
              Why only {coverage.high_conviction} passed?
            </div>
            <div className="flex flex-wrap gap-2">
              {breakdownKeys.map((reason) => {
                const count = coverage.breakdown[reason];
                const label = reason
                  .replace("failed_", "")
                  .replace("no_", "No ")
                  .replace(/_/g, " ");
                return (
                  <button
                    key={reason}
                    onClick={() =>
                      setExpandedReason(expandedReason === reason ? null : reason)
                    }
                    className="flex items-center gap-2 bg-[#0A0A0F] border border-[#1E1E2E] px-3 py-[6px] text-xs text-[#E8E8F0] hover:border-[#EF4444]/50 transition-colors"
                  >
                    <span className="text-[#EF4444]">{count}</span>
                    <span className="text-[#9aa0ad]">failed</span>
                    <span className="capitalize">{label}</span>
                  </button>
                );
              })}
            </div>

            {expandedReason && (
              <div className="mt-3 p-3 border border-[#1E1E2E] bg-[#0A0A0F]">
                <div className="text-[11px] text-[#6B7280] mb-2">
                  Companies that failed{" "}
                  <span className="text-[#EF4444]">
                    {expandedReason.replace("failed_", "").replace(/_/g, " ")}
                  </span>
                </div>
                <div className="text-xs text-[#9aa0ad]">
                  Click to load failed companies (API integration pending)
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
