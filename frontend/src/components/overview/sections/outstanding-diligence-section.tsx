"use client";

import React from "react";
import { cn } from "@/lib/utils";
import type { DiligenceItem } from "@/types/overview";
import { DiligenceRow } from "@/components/overview/primitives/diligence-row";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface OutstandingDiligenceSectionProps {
  diligence: DiligenceItem[];
  loading?: boolean;
}

export function OutstandingDiligenceSection({
  diligence,
  loading,
}: OutstandingDiligenceSectionProps) {
  const completedCount = diligence.filter((item) => item.completed).length;
  const totalCount = diligence.length;

  if (loading) {
    return (
      <section>
        <SectionHeader title="Outstanding Diligence" />
        <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="px-4 py-3 border-b border-[#1f1f1f] last:border-b-0">
              <SkeletonSection lines={1} hasHeader={false} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (diligence.length === 0) {
    return (
      <section>
        <SectionHeader title="Outstanding Diligence" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <p className="font-ov-sans text-sm text-[#737373]">No diligence items.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Outstanding Diligence"
        right={
          <span className="font-ov-mono text-xs text-[#525252]">
            {completedCount}/{totalCount}
          </span>
        }
      />
      <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm">
        {diligence.map((item) => (
          <DiligenceRow key={item.id} item={item} readOnly />
        ))}
      </div>
    </section>
  );
}
