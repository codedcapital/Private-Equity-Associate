"use client";

import type { DailyBriefing } from "@/lib/api";

export function DailyBriefing({ briefing }: { briefing: DailyBriefing }) {
  const counts = [
    { label: "New Opportunities", value: briefing.new_opportunities, color: "#10B981" },
    { label: "Exited", value: briefing.exited_opportunities, color: "#EF4444" },
    { label: "Scores ↑", value: briefing.scores_increased, color: "#2DD4BF" },
    { label: "Scores ↓", value: briefing.scores_decreased, color: "#F59E0B" },
    { label: "Earnings", value: briefing.earnings_reported, color: "#C8A96E" },
    { label: "M&A", value: briefing.ma_transactions, color: "#6B7280" },
  ];

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[#E8E8F0]">New Opportunities Today</h2>
        <p className="text-[11px] text-[#6B7280] mt-0.5">
          What changed since yesterday
        </p>
      </div>

      <div className="border border-[#1E1E2E] bg-[#111118]">
        {/* Summary counts */}
        <div className="grid grid-cols-3 md:grid-cols-6 divide-x divide-[#1E1E2E]">
          {counts.map((c) => (
            <div key={c.label} className="px-3 py-3 text-center">
              <div className="text-[18px] font-mono font-semibold" style={{ color: c.color }}>
                {c.value}
              </div>
              <div className="text-[9px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mt-0.5">
                {c.label}
              </div>
            </div>
          ))}
        </div>

        {/* Detail items */}
        {briefing.items.length > 0 && (
          <div className="border-t border-[#1E1E2E] divide-y divide-[#1E1E2E]">
            {briefing.items.slice(0, 10).map((item, i) => (
              <div key={i} className="px-4 py-2 flex items-center gap-3">
                <span
                  className={`text-[10px] font-mono ${
                    item.direction === "up"
                      ? "text-[#10B981]"
                      : item.direction === "down"
                      ? "text-[#EF4444]"
                      : "text-[#6B7280]"
                  }`}
                >
                  {item.direction === "up" ? "↑" : item.direction === "down" ? "↓" : "→"}
                </span>
                <span className="text-[11px] text-[#E8E8F0]">{item.company_name}</span>
                <span className="text-[11px] text-[#9aa0ad]">{item.description}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
