"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/types";
import { EvidencePill } from "./evidence-pill";

interface QuestionCardProps {
  id: number;
  category: string;
  question: string;
  answer: string | null;
  confidence: number | null;
  evidence: EvidenceItem[];
  sortOrder?: number;
}

const categoryLabels: Record<string, string> = {
  supporting_evidence: "Supporting Evidence",
  contradictory_evidence: "Contradictory Evidence",
  expert_consensus: "Expert Consensus",
  comparable_companies: "Comparable Companies",
  remaining_diligence: "Remaining Diligence",
  executive_briefing: "Executive Briefing",
};

const categoryColors: Record<string, { border: string; badge: string }> = {
  supporting_evidence: {
    border: "border-[#10B981]/20",
    badge: "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30",
  },
  contradictory_evidence: {
    border: "border-[#EF4444]/20",
    badge: "bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30",
  },
  expert_consensus: {
    border: "border-[#2DD4BF]/20",
    badge: "bg-[#2DD4BF]/10 text-[#2DD4BF] border-[#2DD4BF]/30",
  },
  comparable_companies: {
    border: "border-[#C8A96E]/20",
    badge: "bg-[#C8A96E]/10 text-[#C8A96E] border-[#C8A96E]/30",
  },
  remaining_diligence: {
    border: "border-[#F59E0B]/20",
    badge: "bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/30",
  },
  executive_briefing: {
    border: "border-[#C8A96E]/20",
    badge: "bg-[#C8A96E]/10 text-[#C8A96E] border-[#C8A96E]/30",
  },
};

export function QuestionCard({ category, question, answer, confidence, evidence }: QuestionCardProps) {
  const [expanded, setExpanded] = useState(true);
  const styles = categoryColors[category] || { border: "border-[#1E1E2E]", badge: "bg-[#6B7280]/10 text-[#6B7280]" };

  const confValue = confidence ?? 0.5;
  const confColor = confValue >= 0.8 ? "#10B981" : confValue >= 0.6 ? "#F59E0B" : "#EF4444";

  return (
    <div className={`bg-[#111118] border ${styles.border} rounded overflow-hidden`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-[#15151f] transition-colors"
      >
        <span className={`mt-0.5 text-[9px] font-semibold px-1.5 py-0.5 border rounded ${styles.badge} flex-none`}>
          {categoryLabels[category] || category}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-[12.5px] font-medium text-[#E8E8F0]">{question}</h3>
          {answer && (
            <p className="mt-1 text-[11px] text-[#9aa0ad] line-clamp-2">{answer}</p>
          )}
        </div>
        <div className="flex-none flex items-center gap-2">
          {confidence !== null && (
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-1 bg-[#1E1E2E] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${confValue * 100}%`, backgroundColor: confColor }}
                />
              </div>
              <span className="font-mono text-[9px]" style={{ color: confColor }}>
                {confValue.toFixed(2)}
              </span>
            </div>
          )}
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
        </div>
      </button>

      {expanded && answer && (
        <div className="px-4 pb-4 border-t border-[#1E1E2E]">
          <p className="text-[12px] text-[#9aa0ad] leading-[1.7] mt-3 whitespace-pre-wrap">{answer}</p>
          {evidence.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <span className="font-mono text-[9px] text-[#6B7280] uppercase tracking-wider">
                Evidence ({evidence.length})
              </span>
              {evidence.map((e) => (
                <EvidencePill key={e.id} evidence={e} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
