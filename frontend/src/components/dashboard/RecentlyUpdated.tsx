"use client";

interface RecentItem {
  deal_id: number;
  company_name: string;
  event_type: string;
  old_value?: string | null;
  new_value?: string | null;
  reason?: string | null;
  created_at: string;
}

interface RecentlyUpdatedProps {
  items: RecentItem[];
  onItemClick?: (dealId: number) => void;
}

function eventDescription(item: RecentItem): string {
  switch (item.event_type) {
    case "score_changed":
      return `Score ${item.old_value ?? "—"} → ${item.new_value ?? "—"}`;
    case "stage_changed":
      return `Moved to ${item.new_value ?? "—"}`;
    case "financials_updated":
      return "Financials refreshed";
    case "research_added":
      return "Research added";
    default:
      return item.reason || item.event_type;
  }
}

function relativeTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const mins = Math.floor((now.getTime() - d.getTime()) / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

export default function RecentlyUpdated({ items, onItemClick }: RecentlyUpdatedProps) {
  return (
    <div className="bg-[#111118] border border-[#1E1E2E]">
      <div className="px-4 py-3 border-b border-[#1E1E2E] flex items-center justify-between">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">📝 Recently Updated</div>
        <div className="font-mono text-[11px] text-[#6B7280]">Last 24h</div>
      </div>

      <div className="p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 text-center py-8">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <div className="text-[13px] text-[#9aa0ad]">No updates in the last 24 hours.</div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {items.map((item) => (
              <div
                key={`${item.deal_id}-${item.event_type}-${item.created_at}`}
                onClick={onItemClick ? () => onItemClick(item.deal_id) : undefined}
                className={`bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex items-center justify-between gap-3 ${
                  onItemClick ? "cursor-pointer hover:bg-[#111118] transition-colors" : ""
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-medium text-[#E8E8F0] truncate">
                    {item.company_name}
                  </div>
                  <div className="text-[11px] text-[#9aa0ad] mt-0.5">
                    {eventDescription(item)}
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <span className="text-[10px] text-[#6B7280] font-mono">
                    {relativeTime(item.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
