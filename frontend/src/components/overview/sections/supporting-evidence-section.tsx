"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EvidenceModule } from "@/types/overview";
import { EvidenceChip } from "@/components/overview/primitives/evidence-chip";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface SupportingEvidenceSectionProps {
  evidence: EvidenceModule[];
  loading?: boolean;
}

export function SupportingEvidenceSection({ evidence, loading }: SupportingEvidenceSectionProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <section>
        <SectionHeader title="Supporting Evidence" />
        <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-4 py-3 border-b border-[#1f1f1f] last:border-b-0">
              <SkeletonSection lines={2} hasHeader={false} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (evidence.length === 0) {
    return (
      <section>
        <SectionHeader title="Supporting Evidence" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <p className="font-ov-sans text-sm text-[#737373]">No evidence modules available.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader title="Supporting Evidence" />
      <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm divide-y divide-[#1f1f1f]">
        {evidence.map((module) => {
          const isExpanded = expandedIds.has(module.id);
          return (
            <div key={module.id} className="px-4 py-3">
              <button
                onClick={() => toggle(module.id)}
                className="w-full flex items-center gap-3 text-left group"
              >
                <EvidenceChip status={module.status} />
                <span className="font-ov-sans text-sm text-[#e5e5e5] flex-1 min-w-0 truncate group-hover:text-[#c7a84b] transition-colors">
                  {module.name}
                </span>
                <span className="font-ov-sans text-xs text-[#737373] truncate max-w-[240px] hidden sm:block">
                  {module.summary}
                </span>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-[#525252] shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-[#525252] shrink-0" />
                )}
              </button>

              <div
                className={cn(
                  "overflow-hidden transition-all duration-200",
                  isExpanded ? "max-h-[300px] mt-3 opacity-100" : "max-h-0 opacity-0"
                )}
              >
                <div className="pl-1 pr-1 pb-1 flex flex-col gap-2">
                  <div className="flex items-start gap-2">
                    <FileText className="w-3.5 h-3.5 text-[#525252] mt-0.5 shrink-0" />
                    <span className="font-ov-sans text-xs text-[#737373]">
                      {module.sourceReference}
                    </span>
                  </div>
                  {module.rawData && (
                    <div className="font-ov-mono text-xs text-[#525252] bg-[#0a0a0a] p-3 rounded border border-[#1f1f1f] overflow-x-auto">
                      {module.rawData}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
