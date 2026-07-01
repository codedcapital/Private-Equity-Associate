"use client";

import React from "react";
import { Play, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { colors } from "@/lib/theme";
import type { NextAction } from "@/types/overview";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface RecommendedActionsSectionProps {
  nextAction: NextAction | null;
  loading?: boolean;
}

const priorityConfig = {
  high: {
    bg: "rgba(248,113,113,0.12)",
    text: "#f87171b3",
    border: "rgba(248,113,113,0.25)",
    label: "HIGH",
  },
  medium: {
    bg: "rgba(251,191,36,0.12)",
    text: "#fbbf24b3",
    border: "rgba(251,191,36,0.25)",
    label: "MEDIUM",
  },
  low: {
    bg: "rgba(74,222,128,0.12)",
    text: "#4ade80b3",
    border: "rgba(74,222,128,0.25)",
    label: "LOW",
  },
};

export function RecommendedActionsSection({ nextAction, loading }: RecommendedActionsSectionProps) {
  if (loading) {
    return (
      <section>
        <SectionHeader title="Recommended Next Action" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <SkeletonSection lines={3} hasHeader={false} />
        </div>
      </section>
    );
  }

  if (!nextAction) {
    return (
      <section>
        <SectionHeader title="Recommended Next Action" />
        <div className="p-8 border border-[#1f1f1f] bg-[#141414] rounded-sm text-center">
          <p className="font-ov-sans text-sm text-[#737373]">
            No recommended actions at this time.
          </p>
        </div>
      </section>
    );
  }

  const priority = priorityConfig[nextAction.priority];

  return (
    <section>
      <SectionHeader title="Recommended Next Action" />
      <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <span
              className="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider font-ov-sans border w-fit"
              style={{
                backgroundColor: priority.bg,
                color: priority.text,
                borderColor: priority.border,
              }}
            >
              {priority.label}
            </span>
            <h3 className="font-ov-sans text-base font-medium text-[#e5e5e5]">
              {nextAction.title}
            </h3>
            <p className="font-ov-sans text-sm text-[#737373] leading-relaxed">
              {nextAction.description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-5">
          <button
            disabled
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#1f1f1f] bg-[#0a0a0a] text-[#525252] text-xs font-ov-sans font-medium cursor-not-allowed opacity-60 hover:opacity-80 transition-opacity"
          >
            <Play className="w-3.5 h-3.5" />
            Mark as Started
          </button>
          <button
            disabled
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#1f1f1f] bg-[#0a0a0a] text-[#525252] text-xs font-ov-sans font-medium cursor-not-allowed opacity-60 hover:opacity-80 transition-opacity"
          >
            <X className="w-3.5 h-3.5" />
            Dismiss
          </button>
        </div>
      </div>
    </section>
  );
}
