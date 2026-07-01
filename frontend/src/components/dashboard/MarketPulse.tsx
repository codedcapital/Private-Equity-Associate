"use client";

import { useState, useEffect } from "react";
import { getMarketPulse, type MarketPulseData, type MarketPulseItem } from "@/lib/api";

export default function MarketPulse() {
  const [data, setData] = useState<MarketPulseData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMarketPulse()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const defaults: MarketPulseItem[] = [
    { key: "treasury_yield", value: "4.18%", label: "10Y Treasury", direction: "up" },
    { key: "software_ev_revenue", value: "7.8x", label: "Software EV/Revenue", direction: null },
    { key: "sp500_change", value: "+0.7%", label: "S&P 500", direction: null },
    { key: "fed_outlook", value: "1 Cut Expected", label: "Fed Outlook", direction: null },
  ];

  const items = data?.items ?? defaults;

  const cardMap: Record<string, string> = {
    treasury_yield: "10Y Treasury",
    software_ev_revenue: "Software EV/Revenue",
    sp500_change: "S&P 500",
    fed_outlook: "Fed Outlook",
  };

  const cards = defaults.map((def) => {
    const found = items.find((i) => i.key === def.key);
    return {
      label: found?.label ?? cardMap[def.key] ?? def.label,
      value: found?.value ?? def.value,
      direction: found?.direction ?? def.direction,
    };
  });

  return (
    <div className="bg-[#111118] border border-[#1E1E2E] p-4">
      <div className="text-[13px] font-semibold text-[#E8E8F0] mb-3">Market Pulse</div>
      <div className="grid grid-cols-2 gap-3">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex flex-col gap-1 animate-pulse"
              >
                <div className="h-[10px] bg-[#1E1E2E] rounded w-[60%]" />
                <div className="h-[15px] bg-[#1E1E2E] rounded w-[40%] mt-1" />
              </div>
            ))
          : cards.map((card) => (
              <div
                key={card.label}
                className="bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex flex-col gap-1"
              >
                <div className="text-[10px] text-[#6B7280] tracking-[0.06em] uppercase">
                  {card.label}
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[15px] font-semibold text-[#E8E8F0]">
                    {card.value}
                  </span>
                  {card.direction === "up" && (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#EF4444"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M18 15l-6-6-6 6" />
                    </svg>
                  )}
                  {card.direction === "down" && (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#10B981"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  )}
                </div>
              </div>
            ))}
      </div>
      <div className="mt-3 text-[10px] text-[#6B7280] font-mono">
        {data
          ? `Market data · Last updated: ${data.last_updated}`
          : "Market data updated manually"}
      </div>
    </div>
  );
}
