"use client";

import { useState } from "react";

interface ExecutiveBriefingProps {
  briefing: string | null;
  onRegenerate?: () => void;
  isLoading?: boolean;
}

export function ExecutiveBriefing({ briefing, onRegenerate, isLoading }: ExecutiveBriefingProps) {
  const [expanded, setExpanded] = useState(true);

  if (!briefing && !isLoading) {
    return (
      <div className="bg-[#111118] border border-[#1E1E2E] rounded p-5">
        <div className="flex items-center gap-3">
          <span className="text-[#C8A96E] text-lg">●</span>
          <h2 className="text-[14px] font-semibold text-[#E8E8F0]">Executive Briefing</h2>
          <span className="font-mono text-[9px] text-[#6B7280] uppercase tracking-wider">What did we learn?</span>
        </div>
        <p className="mt-3 text-[12.5px] text-[#9aa0ad]">
          No executive briefing available. Generate the Intelligence Hub to synthesize findings.
        </p>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="mt-3 px-4 py-2 text-[11px] font-medium bg-[#C8A96E]/10 text-[#C8A96E] border border-[#C8A96E]/30 rounded hover:bg-[#C8A96E]/20 transition-colors"
          >
            Generate Briefing
          </button>
        )}
      </div>
    );
  }

  const paragraphs = briefing?.split("\n").filter((p) => p.trim()) || [];

  return (
    <div className="bg-[#111118] border border-[#1E1E2E] rounded overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[#15151f] transition-colors"
      >
        <span className="text-[#C8A96E] text-lg">●</span>
        <h2 className="text-[14px] font-semibold text-[#E8E8F0]">Executive Briefing</h2>
        <span className="font-mono text-[9px] text-[#6B7280] uppercase tracking-wider">
          What did we learn?
        </span>
        <div className="flex-1" />
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#6B7280"
          strokeWidth="2"
          className={`transition-transform ${expanded ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          {isLoading ? (
            <div className="space-y-3">
              <div className="h-3 bg-[#1E1E2E] rounded w-3/4 animate-pulse" />
              <div className="h-3 bg-[#1E1E2E] rounded w-full animate-pulse" />
              <div className="h-3 bg-[#1E1E2E] rounded w-5/6 animate-pulse" />
            </div>
          ) : (
            <>
              <div className="space-y-2.5">
                {paragraphs.map((para, i) => (
                  <p key={i} className="text-[12.5px] leading-[1.7] text-[#9aa0ad]">
                    {para}
                  </p>
                ))}
              </div>
              {onRegenerate && (
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={onRegenerate}
                    className="px-3 py-1.5 text-[10px] font-medium bg-[#C8A96E]/10 text-[#C8A96E] border border-[#C8A96E]/30 rounded hover:bg-[#C8A96E]/20 transition-colors"
                  >
                    Regenerate
                  </button>
                  <span className="px-3 py-1.5 text-[10px] text-[#4b5160] font-mono">
                    AI-generated · May contain errors
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
