import React from "react";
import { cn } from "@/lib/utils";

interface NumberDisplayProps {
  value: string;
  label?: string;
  delta?: string;
  deltaColor?: string;
  color?: string;
}

export function NumberDisplay({
  value,
  label,
  delta,
  deltaColor,
  color,
}: NumberDisplayProps) {
  return (
    <div className="flex flex-col items-end gap-1">
      {label && (
        <span className="font-ov-sans text-xs text-[#525252] uppercase tracking-wider">
          {label}
        </span>
      )}
      <div className="flex items-center gap-3">
        {delta && (
          <span
            className="font-ov-mono text-sm"
            style={{ color: deltaColor || "#525252" }}
          >
            {delta}
          </span>
        )}
        <span
          className={cn(
            "font-ov-mono text-4xl font-medium tabular-nums tracking-tight",
            color ? "" : "text-[#e5e5e5]"
          )}
          style={color ? { color } : undefined}
        >
          {value}
        </span>
      </div>
    </div>
  );
}
