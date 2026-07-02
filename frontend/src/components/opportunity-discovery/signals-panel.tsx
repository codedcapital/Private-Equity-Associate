"use client";

import type { SignalFeedItem } from "@/lib/api";

export function SignalsPanel({ signals }: { signals: SignalFeedItem[] }) {
  // Group by signal type
  const grouped = signals.reduce((acc, signal) => {
    const type = signal.signal_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(signal);
    return acc;
  }, {} as Record<string, SignalFeedItem[]>);

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[#E8E8F0]">New Opportunities</h2>
        <p className="text-[11px] text-[#6B7280] mt-0.5">
          Recent signals across the investment universe
        </p>
      </div>

      <div className="border border-[#1E1E2E] bg-[#111118]">
        <div className="divide-y divide-[#1E1E2E]">
          {signals.slice(0, 8).map((signal) => (
            <div
              key={signal.id}
              className="px-4 py-3 flex items-center gap-3 hover:bg-[#0A0A0F] transition-colors"
            >
              <span
                className={`text-[10px] font-mono flex-none ${
                  signal.direction === "up"
                    ? "text-[#10B981]"
                    : signal.direction === "down"
                    ? "text-[#EF4444]"
                    : "text-[#6B7280]"
                }`}
              >
                {signal.direction === "up" ? "↑" : signal.direction === "down" ? "↓" : "→"}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[12px] text-[#E8E8F0] truncate">{signal.title}</div>
                <div className="text-[10px] text-[#6B7280] mt-0.5">
                  {signal.company_name}
                  {signal.description && (
                    <span className="ml-1">— {signal.description}</span>
                  )}
                </div>
              </div>
              <span className="text-[9px] font-mono text-[#4b5160] flex-none">
                {new Date(signal.detected_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
