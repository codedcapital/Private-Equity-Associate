import React from "react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  right?: React.ReactNode;
}

export function SectionHeader({ title, right }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h2 className="font-ov-sans text-xs font-semibold uppercase tracking-widest text-[#525252]">
        {title}
      </h2>
      {right && <div className="flex items-center">{right}</div>}
    </div>
  );
}
