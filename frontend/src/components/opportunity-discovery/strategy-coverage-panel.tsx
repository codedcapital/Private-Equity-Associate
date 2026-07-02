"use client";

import type { StrategyCoverage } from "@/lib/api";

export function StrategyCoveragePanel({ coverage }: { coverage: StrategyCoverage }) {
  const bars = [
    {
      label: "Universe",
      count: coverage.universe,
      total: coverage.universe,
      color: "#6B7280",
    },
    {
      label: "Financial Match",
      count: coverage.financial_match,
      total: coverage.universe,
      color: "#2DD4BF",
    },
    {
      label: "Research Complete",
      count: coverage.research_complete,
      total: coverage.universe,
      color: "#C8A96E",
    },
    {
      label: "Investment Ready",
      count: coverage.investment_ready,
      total: coverage.universe,
      color: "#10B981",
    },
  ];

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[#E8E8F0]">Strategy Coverage</h2>
        <p className="text-[11px] text-[#6B7280] mt-0.5">
          {coverage.strategy_name} — {coverage.coverage_percent}% of universe researched
        </p>
      </div>

      <div className="border border-[#1E1E2E] bg-[#111118] p-5">
        <div className="space-y-4">
          {bars.map((bar) => {
            const pct = bar.total > 0 ? (bar.count / bar.total) * 100 : 0;
            return (
              <div key={bar.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] text-[#9aa0ad]">{bar.label}</span>
                  <span className="font-mono text-[11px] text-[#E8E8F0]">
                    {bar.count.toLocaleString()}
                  </span>
                </div>
                <div className="h-[6px] bg-[#1E1E2E] relative">
                  <div
                    className="absolute left-0 top-0 bottom-0 transition-all"
                    style={{ width: `${pct}%`, background: bar.color }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 pt-4 border-t border-[#1E1E2E] flex items-center gap-6">
          <div>
            <div className="text-[9px] font-mono tracking-[0.05em] uppercase text-[#6B7280]">
              Research Velocity
            </div>
            <div className="text-[13px] text-[#E8E8F0] mt-0.5">
              {coverage.research_velocity} <span className="text-[#6B7280]">this week</span>
            </div>
          </div>
          <div>
            <div className="text-[9px] font-mono tracking-[0.05em] uppercase text-[#6B7280]">
              Investment Ready
            </div>
            <div className="text-[13px] text-[#E8E8F0] mt-0.5">
              {coverage.investment_ready_velocity} <span className="text-[#6B7280]">this month</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
