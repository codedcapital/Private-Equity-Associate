"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { colors, recommendationColors } from "@/lib/theme";
import type { Score, Recommendation } from "@/types/overview";
import { NumberDisplay } from "@/components/overview/primitives/number-display";
import { ConfidenceBar } from "@/components/overview/primitives/confidence-bar";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface InvestmentScoreSectionProps {
  score: Score | null;
  loading?: boolean;
}

const recommendationLabels: Record<Recommendation, string> = {
  PROCEED: "Proceed",
  CONDITIONAL: "Conditional",
  DECLINE: "Decline",
  HOLD: "Hold",
};

export function InvestmentScoreSection({ score, loading }: InvestmentScoreSectionProps) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <section>
        <SectionHeader title="Investment Score" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <SkeletonSection lines={4} hasHeader={false} />
        </div>
      </section>
    );
  }

  if (!score) {
    return (
      <section>
        <SectionHeader title="Investment Score" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <p className="font-ov-sans text-sm text-[#737373]">No score available.</p>
        </div>
      </section>
    );
  }

  const recColor = recommendationColors[score.recommendation] || recommendationColors.HOLD;

  return (
    <section>
      <SectionHeader title="Investment Score" />
      <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <span
              className="inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold uppercase tracking-wider font-ov-sans border w-fit"
              style={{
                backgroundColor: recColor.bg,
                color: recColor.text,
                borderColor: recColor.border,
              }}
            >
              {recommendationLabels[score.recommendation]}
            </span>
            <span className="font-ov-sans text-sm text-[#737373]">
              Confidence {score.confidence}%
            </span>
          </div>

          <NumberDisplay
            value={score.value.toString()}
            label="Score"
            color={colors.textPrimary}
          />
        </div>

        {/* Confidence bar */}
        <div className="mt-6">
          <ConfidenceBar value={score.confidence} label="Confidence" />
        </div>

        {/* View Breakdown toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 mt-5 text-xs font-ov-sans font-medium text-[#737373] hover:text-[#e5e5e5] transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              Hide Breakdown
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              View Breakdown
            </>
          )}
        </button>

        {/* Breakdown table */}
        <div
          className={cn(
            "overflow-hidden transition-all duration-200",
            expanded ? "max-h-[500px] mt-4 opacity-100" : "max-h-0 opacity-0"
          )}
        >
          <div className="border border-[#1f1f1f] rounded-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#1f1f1f] bg-[#0a0a0a]">
                  <th className="text-left px-4 py-2 font-ov-sans text-xs text-[#525252] uppercase tracking-wider font-medium">
                    Factor
                  </th>
                  <th className="text-right px-4 py-2 font-ov-sans text-xs text-[#525252] uppercase tracking-wider font-medium">
                    Weight
                  </th>
                  <th className="text-right px-4 py-2 font-ov-sans text-xs text-[#525252] uppercase tracking-wider font-medium">
                    Score
                  </th>
                  <th className="text-right px-4 py-2 font-ov-sans text-xs text-[#525252] uppercase tracking-wider font-medium">
                    Contribution
                  </th>
                </tr>
              </thead>
              <tbody>
                {score.breakdown.map((item) => (
                  <tr key={item.label} className="border-b border-[#1f1f1f] last:border-b-0">
                    <td className="px-4 py-2.5 font-ov-sans text-[#e5e5e5]">{item.label}</td>
                    <td className="px-4 py-2.5 font-ov-mono text-[#737373] text-right">
                      {item.weight}%
                    </td>
                    <td className="px-4 py-2.5 font-ov-mono text-[#e5e5e5] text-right">
                      {item.score}
                    </td>
                    <td className="px-4 py-2.5 font-ov-mono text-[#c7a84b] text-right">
                      +{item.contribution}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
