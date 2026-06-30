"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/components/toast";
import { getResearch } from "@/lib/api";
import { researchItems as fallbackItems } from "@/lib/data";

interface ResearchItem {
  type: string;
  typeTier: string;
  title: string;
  source: string;
  date: string;
  snippet: string;
}

const resTypeColor: Record<string, string> = { teal: "#2DD4BF", gold: "#C8A96E", gray: "#6B7280" };

export default function ResearchPage() {
  const { addToast } = useToast();
  const [filter, setFilter] = useState<string>("All");
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(false);
  const filters = ["All", "Market", "Filing", "Expert", "News", "Data"];

  useEffect(() => {
    let cancelled = false;
    // Fetch research for a default company (id=1) as a demo
    getResearch(1)
      .then((data) => {
        if (cancelled) return;
        if (data.research && typeof data.research === "object") {
          // Map research output to display items if available
          const raw = data.research as Record<string, unknown>;
          const mapped: ResearchItem[] = [];
          if (raw["growth_drivers"]) {
            mapped.push({
              type: "Market",
              typeTier: "teal",
              title: "Industry Growth Drivers",
              source: "Research Agent",
              date: new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
              snippet: Array.isArray(raw["growth_drivers"]) ? raw["growth_drivers"].join("; ") : String(raw["growth_drivers"]),
            });
          }
          if (raw["risks"]) {
            mapped.push({
              type: "Data",
              typeTier: "gold",
              title: "Risk Factors",
              source: "Research Agent",
              date: new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
              snippet: Array.isArray(raw["risks"]) ? raw["risks"].join("; ") : String(raw["risks"]),
            });
          }
          if (mapped.length > 0) {
            setItems(mapped);
            setUseFallback(false);
          } else {
            setUseFallback(true);
            setItems(fallbackItems);
          }
        } else {
          setUseFallback(true);
          setItems(fallbackItems);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Research fetch failed:", err);
        setUseFallback(true);
        setItems(fallbackItems);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const displayItems = filter === "All" ? items : items.filter((r) => r.type === filter);

  return (
    <div>
      <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <h1 className="m-0 text-[15px] font-semibold">Research Library</h1>
        <span className="font-mono text-[10px] text-[#6B7280] border border-[#1E1E2E] px-[7px] py-[2px] tracking-[0.05em]">
          {useFallback ? "DEMO DATA" : "AGGREGATED INTELLIGENCE"}
        </span>
      </div>

      <div className="max-w-[1000px] px-5 pt-6 pb-[60px]">
        <div className="flex flex-wrap gap-2 items-center pb-3 border-b border-[#1E1E2E]">
          <span className="font-mono text-[10px] tracking-[0.06em] uppercase text-[#6B7280] mr-[2px]">
            Filter
          </span>
          {filters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="px-[10px] py-[6px] text-[11px] font-medium cursor-pointer transition-colors"
              style={{
                background: filter === f ? "#111118" : "transparent",
                border: filter === f ? "1px solid #C8A96E" : "1px solid #1E1E2E",
                color: filter === f ? "#C8A96E" : "#6B7280",
              }}
            >
              {f}
            </button>
          ))}
          <div className="flex-1" />
          <span className="font-mono text-[10px] text-[#4b5160]">{displayItems.length} sources</span>
        </div>

        {loading && (
          <div className="mt-4 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-[#111118] p-4 space-y-2">
                <div className="h-3 bg-[#15151f] w-1/3" />
                <div className="h-3 bg-[#15151f] w-3/4" />
              </div>
            ))}
          </div>
        )}

        {!loading && (
          <div className="flex flex-col gap-px bg-[#1E1E2E] border border-[#1E1E2E] mt-0">
            {displayItems.length === 0 && (
              <div className="bg-[#111118] p-[30px] text-center">
                <div className="text-sm text-[#9aa0ad]">No research matches the "{filter}" filter</div>
                <div className="mt-2 font-mono text-[11px] text-[#4b5160]">Select "All" to view every source</div>
              </div>
            )}
            {displayItems.map((rs, i) => (
              <div
                key={rs.title}
                className="bg-[#111118] p-[15px_16px] flex gap-[14px] hover:bg-[#15151f] transition-colors"
              >
                <div className="flex-none w-[40px] font-mono text-[10px] text-[#6B7280] pt-[2px]">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-[9px]">
                    <span
                      className="font-mono text-[9px] font-semibold tracking-[0.05em] uppercase px-[6px] py-[2px] border"
                      style={{
                        color: resTypeColor[rs.typeTier],
                        borderColor: rs.typeTier === "gray" ? "#1E1E2E" : resTypeColor[rs.typeTier],
                      }}
                    >
                      {rs.type}
                    </span>
                    <span className="text-[13.5px] font-semibold text-[#E8E8F0]">{rs.title}</span>
                  </div>
                  <p className="m-0 mt-2 text-[12.5px] leading-[1.6] text-[#9aa0ad]">{rs.snippet}</p>
                  <div className="mt-2 flex items-center gap-[10px] font-mono text-[10px] text-[#6B7280]">
                    <span>{rs.source}</span>
                    <span className="text-[#1E1E2E]">|</span>
                    <span>{rs.date}</span>
                  </div>
                </div>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#6B7280"
                  strokeWidth="1.7"
                  className="flex-none mt-[3px]"
                >
                  <path d="M7 17L17 7M17 7H8M17 7v9" />
                </svg>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
