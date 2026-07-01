import React from "react";
import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  value: number;
  segments?: number;
  label?: string;
}

export function ConfidenceBar({
  value,
  segments = 10,
  label,
}: ConfidenceBarProps) {
  const filledSegments = Math.round((value / 100) * segments);

  return (
    <div className="flex flex-col gap-2">
      {label && (
        <div className="flex items-center justify-between">
          <span className="font-ov-sans text-xs text-[#525252] uppercase tracking-wider">
            {label}
          </span>
          <span className="font-ov-mono text-sm text-[#e5e5e5]">{value}%</span>
        </div>
      )}
      <div className="flex gap-1">
        {Array.from({ length: segments }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-2 flex-1 rounded-sm transition-colors",
              i < filledSegments ? "bg-[#c7a84b]" : "bg-[#1f1f1f]"
            )}
          />
        ))}
      </div>
    </div>
  );
}
