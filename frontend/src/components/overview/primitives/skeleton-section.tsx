import React from "react";
import { cn } from "@/lib/utils";

interface SkeletonSectionProps {
  lines?: number;
  hasHeader?: boolean;
}

export function SkeletonSection({ lines = 3, hasHeader = true }: SkeletonSectionProps) {
  return (
    <div className="flex flex-col gap-4">
      {hasHeader && (
        <div className="ov-skeleton h-4 w-32 rounded" />
      )}
      <div className="flex flex-col gap-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "ov-skeleton h-3 rounded",
              i === 0 ? "w-full" : i === lines - 1 ? "w-3/4" : "w-5/6"
            )}
          />
        ))}
      </div>
    </div>
  );
}
