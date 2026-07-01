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
  const { data, loading, refetch } = useDealOverview(dealId);
  const [viewMode] = useState<ViewMode>("document");

  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      refetch();
    }
  }, [refreshKey, refetch]);

  return (
    <div className="max-w-[960px] mx-auto px-8 py-8 flex flex-col" style={{ gap: "48px" }}>
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
    </div>
  );
}
