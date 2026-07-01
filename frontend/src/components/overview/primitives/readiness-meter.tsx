import React from "react";
import { Check, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Readiness } from "@/types/overview";

interface ReadinessMeterProps {
  readiness: Readiness;
}

export function ReadinessMeter({ readiness }: ReadinessMeterProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between mb-1">
        <span className="font-ov-sans text-xs text-[#525252] uppercase tracking-wider">
          Readiness
        </span>
        <span className="font-ov-mono text-2xl font-medium text-[#e5e5e5]">
          {readiness.score}
          <span className="text-sm text-[#525252] ml-0.5">/100</span>
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {readiness.items.map((item) => (
          <div key={item.label} className="flex items-center gap-3">
            {item.met ? (
              <Check className="w-4 h-4 text-[#525252] shrink-0" strokeWidth={2} />
            ) : (
              <AlertTriangle className="w-4 h-4 text-[#525252] shrink-0" strokeWidth={2} />
            )}
            <span
              className={cn(
                "font-ov-sans text-sm",
                item.met ? "text-[#737373]" : "text-[#e5e5e5]"
              )}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
