"use client";

import React, { useState } from "react";
import { Pencil } from "lucide-react";
import { cn } from "@/lib/utils";
import type { InvestmentView } from "@/types/overview";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface InvestmentViewSectionProps {
  view: InvestmentView | null;
  loading?: boolean;
  editing?: boolean;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
  onSaveEdit?: () => void;
}

export function InvestmentViewSection({ view, loading, editing, onStartEdit, onCancelEdit, onSaveEdit }: InvestmentViewSectionProps) {
  const [editContent, setEditContent] = useState(view?.content ?? "");

  if (loading) {
    return (
      <section className="py-10 px-8 border border-[#1f1f1f] bg-[#141414] rounded-sm">
        <SkeletonSection lines={8} hasHeader={false} />
      </section>
    );
  }

  if (!view) {
    return (
      <section className="py-10 px-8 border border-[#1f1f1f] bg-[#141414] rounded-sm">
        <div className="font-ov-sans text-sm text-[#737373]">
          No investment view available.
        </div>
      </section>
    );
  }

  const lastUpdated = new Date(view.updatedAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <section className="relative py-10 px-8 border border-[#1f1f1f] bg-[#141414] rounded-sm">
      {/* Edit / Save / Cancel buttons */}
      <div className="absolute top-6 right-6 flex items-center gap-2">
        {editing ? (
          <>
            <button
              onClick={onSaveEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#c7a84b] bg-[#c7a84b]/10 text-[#c7a84b] text-xs font-ov-sans font-medium hover:bg-[#c7a84b]/20 transition-colors"
            >
              Save
            </button>
            <button
              onClick={onCancelEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#1f1f1f] bg-[#0a0a0a] text-[#525252] text-xs font-ov-sans font-medium hover:text-[#e5e5e5] transition-colors"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={onStartEdit}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#1f1f1f] bg-[#0a0a0a] text-[#a3a3a3] text-xs font-ov-sans font-medium hover:text-[#e5e5e5] hover:border-[#c7a84b] transition-colors"
          >
            <Pencil className="w-3.5 h-3.5" />
            Edit
          </button>
        )}
      </div>

      {/* Content */}
      {editing ? (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full min-h-[200px] bg-[#0a0a0a] border border-[#1f1f1f] text-[#e5e5e5] font-ov-serif text-[16px] leading-[1.75] p-4 rounded-sm focus:outline-none focus:border-[#c7a84b]"
        />
      ) : (
        <div
          className={cn(
            "font-ov-serif text-[#e5e5e5] leading-[1.75]",
            "prose prose-invert max-w-none prose-p:my-4 prose-headings:font-ov-sans prose-headings:text-[#e5e5e5]"
          )}
          style={{ fontSize: "16px" }}
          dangerouslySetInnerHTML={{ __html: view.content }}
        />
      )}

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-[#1f1f1f]">
        <p className="font-ov-sans text-xs text-[#525252]">
          Generated from {view.sources.join(", ")} · Last updated {lastUpdated}
        </p>
      </div>
    </section>
  );
}
