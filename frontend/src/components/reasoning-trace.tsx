"use client";

import React, { useState } from "react";

export interface ReasoningTraceStep {
  timestamp: string;
  text: string;
}

export interface ReasoningTraceProps {
  steps: ReasoningTraceStep[];
}

export function ReasoningTrace({ steps }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="inline-flex items-center gap-[6px] text-[11px] text-[#6B7280] hover:text-[#9aa0ad] transition-colors cursor-pointer font-mono"
      >
        <span>{expanded ? "Hide reasoning trace" : "Show reasoning trace"}</span>
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="transition-transform duration-200"
          style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      <div
        className="overflow-hidden transition-all duration-300 ease-out"
        style={{
          maxHeight: expanded ? "600px" : "0px",
          opacity: expanded ? 1 : 0,
        }}
      >
        <div className="mt-2 pl-3 border-l-2 border-[#1E1E2E] space-y-[6px]">
          {steps.map((step, i) => {
            const date = new Date(step.timestamp);
            const timeStr = isNaN(date.getTime())
              ? step.timestamp
              : date.toLocaleTimeString("en-US", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hour12: false,
                });
            return (
              <div key={i} className="flex items-start gap-[10px]">
                <span className="font-mono text-[9px] text-[#4b5160] pt-[2px] flex-shrink-0 w-[50px] text-right">
                  {timeStr}
                </span>
                <span className="font-mono text-[11px] text-[#6B7280] leading-[1.5]">
                  {step.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
