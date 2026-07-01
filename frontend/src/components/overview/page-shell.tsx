import React from "react";
import { FileDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ViewMode } from "@/types/overview";

interface PageShellProps {
  deal: {
    name: string;
    stage: string;
    sector: string;
    hq: string;
    id: string;
  };
  viewMode: ViewMode;
  onToggleView: () => void;
  children: React.ReactNode;
}

export function PageShell({
  deal,
  viewMode,
  onToggleView,
  children,
}: PageShellProps) {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 bg-[#0a0a0a]/95 backdrop-blur-sm border-b border-[#1f1f1f]">
        <div className="max-w-[960px] mx-auto px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <h1 className="font-ov-sans text-lg font-semibold text-[#e5e5e5] leading-tight">
                  {deal.name}
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="font-ov-sans text-xs text-[#737373]">
                    {deal.stage}
                  </span>
                  <span className="text-[#1f1f1f]">·</span>
                  <span className="font-ov-sans text-xs text-[#525252]">
                    {deal.sector}
                  </span>
                  <span className="text-[#1f1f1f]">·</span>
                  <span className="font-ov-sans text-xs text-[#525252]">
                    {deal.hq}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Export PDF Button */}
              <button
                disabled
                className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[#1f1f1f] bg-[#141414] text-[#525252] text-xs font-ov-sans font-medium cursor-not-allowed opacity-60"
              >
                <FileDown className="w-3.5 h-3.5" />
                Export PDF
              </button>

              {/* View Mode Toggle */}
              <div className="flex items-center rounded-md border border-[#1f1f1f] bg-[#141414] p-0.5">
                <button
                  onClick={onToggleView}
                  className={cn(
                    "px-3 py-1.5 rounded text-xs font-ov-sans font-medium transition-colors",
                    viewMode === "document"
                      ? "bg-[#c7a84b] text-[#0a0a0a]"
                      : "text-[#737373] hover:text-[#e5e5e5]"
                  )}
                >
                  Document View
                </button>
                <button
                  onClick={onToggleView}
                  className={cn(
                    "px-3 py-1.5 rounded text-xs font-ov-sans font-medium transition-colors",
                    viewMode === "data"
                      ? "bg-[#c7a84b] text-[#0a0a0a]"
                      : "text-[#737373] hover:text-[#e5e5e5]"
                  )}
                >
                  Data View
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Page Content */}
      <main className="max-w-[960px] mx-auto px-8 py-8">
        {children}
      </main>
    </div>
  );
}
