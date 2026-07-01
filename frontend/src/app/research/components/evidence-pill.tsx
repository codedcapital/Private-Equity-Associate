"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/types";

interface EvidencePillProps {
  evidence: EvidenceItem;
}

export function EvidencePill({ evidence }: EvidencePillProps) {
  const [expanded, setExpanded] = useState(false);

  const confidence = evidence.confidence ?? 0.5;
  const confidenceColor =
    confidence >= 0.8 ? "#10B981" : confidence >= 0.6 ? "#F59E0B" : "#EF4444";

  const badgeColor = evidence.is_supporting
    ? "border-[#10B981]/30 text-[#10B981] bg-[#10B981]/5"
    : evidence.is_contradictory
      ? "border-[#EF4444]/30 text-[#EF4444] bg-[#EF4444]/5"
      : "border-[#6B7280]/30 text-[#6B7280] bg-[#6B7280]/5";

  const badgeLabel = evidence.is_supporting
    ? "Supporting"
    : evidence.is_contradictory
      ? "Contradictory"
      : "Neutral";

  return (
    <div className="border border-[#1E1E2E] rounded bg-[#0A0A0F] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[#15151f] transition-colors"
      >
        <span className={`text-[9px] font-semibold px-1.5 py-0.5 border rounded ${badgeColor}`}>
          {badgeLabel}
        </span>
        <span className="text-[11px] text-[#9aa0ad] flex-1 truncate">
          {evidence.text}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#6B7280"
          strokeWidth="2"
          className={`transition-transform flex-none ${expanded ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-[#1E1E2E]">
          <p className="text-[11px] text-[#9aa0ad] leading-[1.6] mt-2">
            {evidence.text}
          </p>
          <div className="mt-2 flex items-center gap-3 flex-wrap">
            <span className="font-mono text-[9px] text-[#6B7280]">
              Source: {evidence.source}
            </span>
            {evidence.source_url && (
              <a
                href={evidence.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[9px] text-[#2DD4BF] hover:underline"
              >
                View source →
              </a>
            )}
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[9px] text-[#6B7280]">Confidence</span>
              <div className="w-12 h-1 bg-[#1E1E2E] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${confidence * 100}%`, backgroundColor: confidenceColor }}
                />
              </div>
              <span className="font-mono text-[9px]" style={{ color: confidenceColor }}>
                {confidence.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
