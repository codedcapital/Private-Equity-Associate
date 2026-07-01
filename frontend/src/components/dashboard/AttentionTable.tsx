"use client";

import { type AttentionDeal } from "@/lib/api";

interface AttentionTableProps {
  deals: AttentionDeal[];
  onDealClick: (dealId: number) => void;
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

export default function AttentionTable({ deals, onDealClick }: AttentionTableProps) {
  if (deals.length === 0) {
    return (
      <div className="bg-[#111118] border border-[#1E1E2E] p-6 flex flex-col items-center justify-center gap-3 text-center min-h-[200px]">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 6L9 17l-5-5" />
        </svg>
        <div className="text-sm text-[#9aa0ad]">
          No deals require attention right now. All clear.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#111118] border border-[#1E1E2E]">
      <div className="px-4 py-3 border-b border-[#1E1E2E] flex items-center justify-between">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">Attention Required</div>
        <div className="font-mono text-[11px] text-[#6B7280]">{deals.length} deals</div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#111118]">
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Company</th>
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Score</th>
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Change</th>
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Stage</th>
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Why</th>
              <th className="px-4 py-2 text-[10px] text-[#6B7280] tracking-[0.06em] uppercase font-medium border-b border-[#1E1E2E]">Updated</th>
            </tr>
          </thead>
          <tbody>
            {deals.map((deal) => (
              <tr
                key={deal.deal_id}
                onClick={() => onDealClick(deal.deal_id)}
                className="bg-[#0A0A0F] cursor-pointer hover:bg-[#111118] transition-colors"
              >
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  <div className="text-[13px] font-medium text-[#E8E8F0]">{deal.company_name}</div>
                  {deal.ticker && (
                    <span className="inline-block mt-1 font-mono text-[9px] font-semibold tracking-[0.06em] uppercase text-[#C8A96E] border border-[#1E1E2E] px-[5px] py-[1px]">
                      {deal.ticker}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  {deal.confidence === "INSUFFICIENT" ? (
                    <span className="text-[13px] font-semibold text-[#6B7280]">N/A</span>
                  ) : (
                    <span className={`text-[13px] font-semibold ${deal.confidence === "LOW" ? "text-[#6B7280]" : "text-[#E8E8F0]"}`}>
                      {deal.score ?? "—"}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  {deal.score_change != null && deal.score_change_direction != null ? (
                    <span className={`text-[13px] font-medium ${deal.score_change_direction === "up" ? "text-[#10B981]" : "text-[#EF4444]"}`}>
                      {deal.score_change_direction === "up" ? "▲" : "▼"} {deal.score_change > 0 ? "+" : ""}{deal.score_change}
                    </span>
                  ) : (
                    <span className="text-[13px] text-[#6B7280]">—</span>
                  )}
                </td>
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  <div className="flex items-center gap-2">
                    <span className="w-[7px] h-[7px]" style={{ background: stageColor(deal.stage) }} />
                    <span className="text-[12px] text-[#E8E8F0]">{deal.stage_label}</span>
                  </div>
                </td>
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  <span className="text-[12px] text-[#9aa0ad]">{deal.why}</span>
                </td>
                <td className="px-4 py-3 border-b border-[#1E1E2E]">
                  <span className="font-mono text-[11px] text-[#6B7280]">{relativeTime(deal.updated_at)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
