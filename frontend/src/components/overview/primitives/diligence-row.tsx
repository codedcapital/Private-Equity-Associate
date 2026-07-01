import React from "react";
import type { DiligenceItem } from "@/types/overview";

interface DiligenceRowProps {
  item: DiligenceItem;
  readOnly?: boolean;
}

export function DiligenceRow({ item, readOnly = true }: DiligenceRowProps) {
  const formattedDate = new Date(item.dueDate).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex items-center gap-4 py-3 px-1 border-b border-[#1f1f1f] last:border-b-0">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <input
          type="checkbox"
          id={item.id}
          checked={item.completed}
          disabled={readOnly}
          readOnly={readOnly}
          className="shrink-0 w-4 h-4 rounded border border-[#2a2a2a] bg-[#141414] accent-[#c7a84b] cursor-default"
        />
        <label
          htmlFor={item.id}
          className={`font-ov-sans text-sm truncate cursor-default ${
            item.completed ? "text-[#525252] line-through" : "text-[#e5e5e5]"
          }`}
        >
          {item.title}
        </label>
      </div>
      <span className="font-ov-sans text-xs text-[#737373] shrink-0">
        {item.owner}
      </span>
      <span className="font-ov-mono text-xs text-[#525252] shrink-0">
        {formattedDate}
      </span>
    </div>
  );
}
