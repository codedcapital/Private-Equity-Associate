"use client";

import type { SourceConfidence } from "@/types";

interface SourceConfidenceMatrixProps {
  sources: SourceConfidence[];
}

export function SourceConfidenceMatrix({ sources }: SourceConfidenceMatrixProps) {
  if (sources.length === 0) {
    return (
      <div className="bg-[#111118] border border-[#1E1E2E] rounded p-4">
        <h3 className="text-[12px] font-semibold text-[#E8E8F0]">Source Confidence</h3>
        <p className="mt-2 text-[11px] text-[#9aa0ad]">No sources rated yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-[#111118] border border-[#1E1E2E] rounded overflow-hidden">
      <div className="px-4 py-3 border-b border-[#1E1E2E]">
        <h3 className="text-[12px] font-semibold text-[#E8E8F0]">Source Confidence Matrix</h3>
        <p className="text-[10px] text-[#6B7280] mt-0.5">Reliability of each data source used in this hub</p>
      </div>
      <div className="divide-y divide-[#1E1E2E]">
        {sources.map((source) => {
          const score = source.confidence_score;
          const color = score >= 0.8 ? "#10B981" : score >= 0.6 ? "#F59E0B" : "#EF4444";
          const label = score >= 0.8 ? "High" : score >= 0.6 ? "Medium" : "Low";

          return (
            <div key={source.id} className="px-4 py-3 flex items-center gap-4 hover:bg-[#15151f] transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium text-[#E8E8F0]">{source.source_name}</span>
                  <span className="font-mono text-[9px] text-[#6B7280] px-1.5 py-0.5 border border-[#1E1E2E] rounded">
                    {source.source_type}
                  </span>
                </div>
                <p className="text-[10px] text-[#9aa0ad] mt-0.5 truncate">{source.rationale}</p>
              </div>
              <div className="flex-none flex items-center gap-2.5">
                <div className="flex items-center gap-1.5">
                  <div className="w-16 h-1.5 bg-[#1E1E2E] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${score * 100}%`, backgroundColor: color }}
                    />
                  </div>
                  <span className="font-mono text-[10px] w-6 text-right" style={{ color }}>
                    {score.toFixed(2)}
                  </span>
                </div>
                <span
                  className="text-[9px] font-medium px-2 py-0.5 rounded border"
                  style={{ color, borderColor: `${color}40`, backgroundColor: `${color}10` }}
                >
                  {label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
