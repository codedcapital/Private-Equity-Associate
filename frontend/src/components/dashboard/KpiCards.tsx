"use client";

interface KpiCardsProps {
  activeDeals: number;
  avgScore: number | null;
  icReadyCount: number;
  attentionCount: number;
}

function scoreColor(score: number | null): string {
  if (score == null) return "#6B7280";
  if (score > 75) return "#10B981";
  if (score > 50) return "#F59E0B";
  return "#6B7280";
}

export default function KpiCards({ activeDeals, avgScore, icReadyCount, attentionCount }: KpiCardsProps) {
  const cards = [
    { label: "Active Deals", value: activeDeals, color: "#E8E8F0", suffix: "" },
    { label: "Avg Score", value: avgScore ?? "—", color: scoreColor(avgScore), suffix: avgScore != null ? "/100" : "" },
    { label: "IC Ready", value: icReadyCount, color: "#C8A96E", suffix: "" },
    { label: "Attention Required", value: attentionCount, color: attentionCount > 0 ? "#EF4444" : "#6B7280", suffix: "" },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-[#111118] border border-[#1E1E2E] p-4 flex flex-col gap-1"
        >
          <div className="text-[11px] text-[#6B7280] tracking-[0.06em] uppercase font-medium">
            {card.label}
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-semibold" style={{ color: card.color }}>
              {card.value}
            </span>
            {card.suffix && (
              <span className="text-sm text-[#6B7280] font-medium">{card.suffix}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
