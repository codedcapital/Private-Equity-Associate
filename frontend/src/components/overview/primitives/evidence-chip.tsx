import React from "react";
import { evidenceStatusColors } from "@/lib/theme";
import type { EvidenceStatus } from "@/types/overview";

interface EvidenceChipProps {
  status: EvidenceStatus;
}

const statusLabels: Record<EvidenceStatus, string> = {
  VERIFIED: "VERIFIED",
  NEEDS_VALIDATION: "NEEDS VALIDATION",
  CONFLICTING: "CONFLICTING",
  UNKNOWN: "UNKNOWN",
};

export function EvidenceChip({ status }: EvidenceChipProps) {
  const colors = evidenceStatusColors[status] || evidenceStatusColors.UNKNOWN;

  return (
    <span
      className="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider font-ov-sans border"
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      }}
    >
      [{statusLabels[status]}]
    </span>
  );
}
