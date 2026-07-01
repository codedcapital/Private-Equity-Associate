"use client";

import React from "react";
import type { Readiness } from "@/types/overview";
import { ReadinessMeter } from "@/components/overview/primitives/readiness-meter";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface DecisionReadinessSectionProps {
  readiness: Readiness | null;
  loading?: boolean;
}

export function DecisionReadinessSection({ readiness, loading }: DecisionReadinessSectionProps) {
  if (loading) {
    return (
      <section>
        <SectionHeader title="Decision Readiness" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <SkeletonSection lines={5} hasHeader={false} />
        </div>
      </section>
    );
  }

  if (!readiness) {
    return (
      <section>
        <SectionHeader title="Decision Readiness" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <p className="font-ov-sans text-sm text-[#737373]">
            No readiness data available.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader title="Decision Readiness" />
      <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
        <ReadinessMeter readiness={readiness} />
      </div>
    </section>
  );
}
