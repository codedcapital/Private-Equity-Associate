"use client";

interface SignalItem {
  id: number;
  deal_id: number;
  company_name?: string | null;
  signal_type: string;
  direction?: string | null;
  title: string;
  description?: string | null;
  evidence_url?: string | null;
  confidence: string;
  detected_at: string;
}

interface SignalsFeedProps {
  signals: SignalItem[];
  onDismiss?: (signalId: number) => void;
}

const signalTypeColors: Record<string, string> = {
  earnings: "#10B981",
  insider_trading: "#C8A96E",
  macro_rate: "#2DD4BF",
  multiple_shift: "#EF4444",
  m_a: "#F59E0B",
  operational: "#6B7280",
};

function SignalIcon({ type }: { type: string }) {
  const color = signalTypeColors[type] ?? "#6B7280";
  switch (type) {
    case "earnings":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
      );
    case "insider_trading":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      );
    case "macro_rate":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      );
    case "multiple_shift":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
          <polyline points="17 6 23 6 23 12" />
        </svg>
      );
    case "m_a":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "operational":
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      );
    default:
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill={color}>
          <circle cx="12" cy="12" r="6" />
        </svg>
      );
  }
}

function DirectionArrow({ direction }: { direction?: string | null }) {
  if (direction === "up" || direction === "positive") {
    return <span className="text-[#10B981]">▲</span>;
  }
  if (direction === "down" || direction === "negative") {
    return <span className="text-[#EF4444]">▼</span>;
  }
  return <span className="text-[#6B7280]">—</span>;
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

export default function SignalsFeed({ signals, onDismiss }: SignalsFeedProps) {
  const displaySignals = signals.slice(0, 10);

  return (
    <div className="bg-[#111118] border border-[#1E1E2E]">
      <div className="px-4 py-3 border-b border-[#1E1E2E] flex items-center justify-between">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">📡 Latest Signals</div>
        <div className="font-mono text-[11px] text-[#6B7280]">{signals.length} signals</div>
      </div>

      <div className="p-4">
        {displaySignals.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 text-center py-8">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="text-[13px] text-[#9aa0ad]">No signals detected. Pipeline is quiet.</div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {displaySignals.map((signal) => (
              <div
                key={signal.id}
                className="bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex items-start gap-3"
              >
                <div className="mt-0.5 flex-shrink-0">
                  <SignalIcon type={signal.signal_type} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[13px] text-[#E8E8F0] truncate">{signal.title}</span>
                    <DirectionArrow direction={signal.direction} />
                  </div>
                  {signal.company_name && (
                    <div className="text-[11px] font-mono text-[#C8A96E] mb-1">{signal.company_name}</div>
                  )}
                  {signal.description && (
                    <div className="text-[11px] text-[#9aa0ad] leading-relaxed mb-1">{signal.description}</div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#6B7280] font-mono">{relativeTime(signal.detected_at)}</span>
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5 border border-[#1E1E2E]"
                      style={{ color: signalTypeColors[signal.signal_type] ?? "#6B7280" }}
                    >
                      {signal.confidence}
                    </span>
                  </div>
                </div>
                {onDismiss && (
                  <button
                    onClick={() => onDismiss(signal.id)}
                    className="flex-shrink-0 text-[#6B7280] hover:text-[#E8E8F0] transition-colors text-[16px] leading-none mt-0.5"
                    aria-label="Dismiss signal"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
