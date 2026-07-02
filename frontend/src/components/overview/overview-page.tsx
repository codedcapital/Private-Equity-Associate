"use client";

import React, { useState, useEffect } from "react";
import type { ViewMode } from "@/types/overview";
import { useDealOverview } from "@/hooks/use-deal-overview";
import { InvestmentViewSection } from "@/components/overview/sections/investment-view-section";
import { InvestmentScoreSection } from "@/components/overview/sections/investment-score-section";
import { SupportingEvidenceSection } from "@/components/overview/sections/supporting-evidence-section";
import { OutstandingDiligenceSection } from "@/components/overview/sections/outstanding-diligence-section";
import { DecisionReadinessSection } from "@/components/overview/sections/decision-readiness-section";
import { RecentChangesSection } from "@/components/overview/sections/recent-changes-section";
import { RecommendedActionsSection } from "@/components/overview/sections/recommended-actions-section";

interface OverviewPageProps {
  dealId: string;
  refreshKey?: number;
}

export function OverviewPage({ dealId, refreshKey }: OverviewPageProps) {
  const { data, loading, error, refetch, rawResponse } = useDealOverview(dealId);
  const [viewMode] = useState<ViewMode>("document");
  const [showDebug, setShowDebug] = useState(false);

  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      refetch();
    }
  }, [refreshKey, refetch]);

  return (
    <div className="max-w-[960px] mx-auto px-8 py-8 flex flex-col" style={{ gap: "48px" }}>
      {error && (
        <div className="p-4 border border-[#f87171b3] bg-[#f87171b3]/10 rounded-sm">
          <p className="font-ov-sans text-sm text-[#f87171b3]">
            Error loading overview: {error}
          </p>
          <button
            onClick={refetch}
            className="mt-2 text-xs font-ov-sans text-[#c7a84b] hover:underline"
          >
            Retry
          </button>
        </div>
      )}
      {viewMode === "data" ? (
        <div className="flex items-center justify-center h-[400px]">
          <p className="font-ov-sans text-sm text-[#525252]">
            Data View coming in Phase 4.
          </p>
        </div>
      ) : (
        <>
          <InvestmentViewSection
            view={data?.investmentView ?? null}
            loading={loading}
          />
          <InvestmentScoreSection
            score={data?.score ?? null}
            loading={loading}
          />
          <SupportingEvidenceSection
            evidence={data?.evidence ?? []}
            loading={loading}
          />
          <OutstandingDiligenceSection
            diligence={data?.diligence ?? []}
            loading={loading}
          />
          <DecisionReadinessSection
            readiness={data?.readiness ?? null}
            loading={loading}
          />
          <RecentChangesSection
            activity={data?.activity ?? []}
            loading={loading}
          />
          <RecommendedActionsSection
            nextAction={data?.nextAction ?? null}
            loading={loading}
          />
        </>
      )}

      {/* Debug panel */}
      <div className="mt-8 border-t border-dashed border-[#d4d4d4] pt-4">
        <button
          onClick={() => setShowDebug(!showDebug)}
          className="text-xs font-ov-mono text-[#737373] hover:text-[#171717] transition-colors"
        >
          {showDebug ? "Hide Debug" : "Show Debug"}
        </button>
        {showDebug && (
          <div className="mt-2 p-3 bg-[#fafafa] border border-[#d4d4d4] rounded-sm overflow-auto max-h-[400px]">
            <p className="text-xs font-ov-mono text-[#737373] mb-2">
              Deal ID: {dealId} | Status: {loading ? "loading" : error ? "error" : "ok"}
            </p>
            {error && (
              <div className="mb-2 p-2 bg-[#fef2f2] border border-[#f87171b3] rounded-sm">
                <p className="text-xs font-ov-mono text-[#f87171b3]">Error: {error}</p>
              </div>
            )}
            {rawResponse && (
              <pre className="text-[10px] font-ov-mono text-[#525252] whitespace-pre-wrap break-all">
                {JSON.stringify(rawResponse, null, 2)}
              </pre>
            )}
            {!rawResponse && !error && (
              <p className="text-xs font-ov-mono text-[#737373]">No response yet</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
