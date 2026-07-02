"use client";

import { useOpportunityDiscovery } from "@/hooks/use-opportunity-discovery";
import { InvestmentStrategyPanel } from "@/components/opportunity-discovery/investment-strategy-panel";
import { MarketCoveragePanel } from "@/components/opportunity-discovery/market-coverage-panel";
import { OpportunitiesTable } from "@/components/opportunity-discovery/opportunities-table";
import { DailyBriefing } from "@/components/opportunity-discovery/daily-briefing";
import { SignalsPanel } from "@/components/opportunity-discovery/signals-panel";
import { StrategyCoveragePanel } from "@/components/opportunity-discovery/strategy-coverage-panel";
import { SkeletonCard } from "@/components/skeleton";

export default function OpportunityDiscoveryPage() {
  const {
    coverage,
    opportunities,
    signals,
    briefing,
    strategyCoverage,
    loading,
    error,
    refresh,
  } = useOpportunityDiscovery();

  if (loading) {
    return (
      <div className="max-w-[1200px] px-5 pt-6 pb-[60px]">
        <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
          <h1 className="m-0 text-[15px] font-semibold">Opportunity Discovery</h1>
        </div>
        <div className="mt-6 space-y-6">
          <SkeletonCard count={3} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-[1200px] px-5 pt-6 pb-[60px]">
        <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
          <h1 className="m-0 text-[15px] font-semibold">Opportunity Discovery</h1>
        </div>
        <div className="mt-6 p-6 border border-[#EF4444]/30 bg-[#EF4444]/5">
          <div className="text-[#EF4444] text-sm font-medium">Failed to load data</div>
          <div className="text-[#9aa0ad] text-xs mt-1">{error}</div>
          <button
            onClick={refresh}
            className="mt-3 text-xs text-[#C8A96E] hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Top bar */}
      <div className="h-[52px] flex items-center gap-3 px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <h1 className="m-0 text-[15px] font-semibold">Opportunity Discovery</h1>
        <span className="font-mono text-[10px] text-[#6B7280] border border-[#1E1E2E] px-[7px] py-[2px] tracking-[0.05em]">
          CONTINUOUS MONITORING
        </span>
      </div>

      <div className="max-w-[1200px] px-5 pt-6 pb-[60px] space-y-8">
        {/* Section 1: Investment Strategy */}
        <InvestmentStrategyPanel />

        {/* Section 2: Market Coverage */}
        {coverage && <MarketCoveragePanel coverage={coverage} />}

        {/* Section 3: Highest Conviction Opportunities */}
        <OpportunitiesTable opportunities={opportunities} />

        {/* Section 4: Signals */}
        {signals.length > 0 && <SignalsPanel signals={signals} />}

        {/* Section 5: Daily Briefing */}
        {briefing && <DailyBriefing briefing={briefing} />}

        {/* Section 6: Strategy Coverage */}
        {strategyCoverage && <StrategyCoveragePanel coverage={strategyCoverage} />}
      </div>
    </div>
  );
}
