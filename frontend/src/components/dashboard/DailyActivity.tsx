"use client";

interface ActivitySummary {
  financials_refreshed: number;
  research_updated: number;
  news_analyzed: number;
  models_rebuilt: number;
  total_runs: number;
  date: string;
}

interface DailyActivityProps {
  summary: ActivitySummary;
}

const ACTIVITY_ITEMS = [
  { key: "financials_refreshed" as const, label: "Financials", color: "#2DD4BF" },
  { key: "research_updated" as const, label: "Research", color: "#C8A96E" },
  { key: "news_analyzed" as const, label: "News", color: "#6B7280" },
  { key: "models_rebuilt" as const, label: "Models", color: "#10B981" },
  { key: "total_runs" as const, label: "Total", color: "#E8E8F0" },
];

export default function DailyActivity({ summary }: DailyActivityProps) {
  if (!summary) {
    return null;
  }

  return (
    <div className="bg-[#111118] border border-[#1E1E2E] p-3">
      <div className="text-[10px] text-[#6B7280] uppercase tracking-[0.06em] mb-2">
        Today&apos;s Activity — {summary.date}
      </div>
      <div className="flex items-center justify-between">
        {ACTIVITY_ITEMS.map((item) => (
          <div key={item.key} className="flex items-center gap-2">
            <span className="text-[14px] leading-none" style={{ color: item.color }}>
              ●
            </span>
            <div className="flex flex-col">
              <span className="text-[10px] text-[#6B7280] uppercase tracking-[0.06em]">
                {item.label}
              </span>
              <span className="font-mono text-[13px] font-semibold" style={{ color: item.color }}>
                {summary[item.key]}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
