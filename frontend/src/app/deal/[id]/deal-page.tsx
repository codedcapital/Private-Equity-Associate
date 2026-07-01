"use client";

import Link from "next/link";
import { useToast } from "@/components/toast";
import { getDeal, refreshOverview, type DealRead } from "@/lib/api";
import { OverviewPage } from "@/components/overview/overview-page";
import { useState, useEffect, useCallback } from "react";

export default function DealPage({ id }: { id: string }) {
  const { addToast } = useToast();
  const [dealData, setDealData] = useState<DealRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const numericId = parseInt(id, 10);

  const fetchDeal = useCallback(async () => {
    if (isNaN(numericId)) {
      addToast("warning", "Invalid deal ID", `Cannot parse "${id}" as a number.`);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const deal = await getDeal(numericId);
      setDealData(deal);
    } catch (err) {
      addToast("error", "Failed to load deal", err instanceof Error ? err.message : "Backend unavailable");
    } finally {
      setLoading(false);
    }
  }, [numericId, id, addToast]);

  useEffect(() => {
    fetchDeal();
  }, [fetchDeal]);

  const handleRefresh = useCallback(async () => {
    if (isNaN(numericId)) return;
    setRefreshing(true);
    try {
      await refreshOverview(numericId);
      addToast("success", "Overview refreshed", "Data has been regenerated from the intelligence engine.");
    } catch (err) {
      addToast("warning", "Refresh failed", err instanceof Error ? err.message : "Could not refresh overview.");
    } finally {
      setRefreshing(false);
    }
  }, [numericId, addToast]);

  const activeDeal = {
    id: String(dealData?.id ?? id),
    name: dealData?.company?.name ?? `Deal ${id}`,
    stage: (dealData?.stage ?? "—").toUpperCase(),
    sector: dealData?.company?.sector ?? "—",
    hq: dealData?.company?.geography ?? "—",
  };

  return (
    <div>
      {/* Clean header */}
      <div className="border-b border-[#1a1a1a] bg-[#0a0a0f] sticky top-0 z-[5]">
        <div className="flex items-center gap-[14px] px-5 py-[14px] pb-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-[6px] bg-transparent border border-[#1a1a1a] text-[#6B7280] px-[9px] py-[6px] text-[11px] cursor-pointer font-mono hover:text-[#E8E8F0] hover:border-[#2c2c42] transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            PIPELINE
          </Link>
          <div>
            <div className="flex items-center gap-[10px]">
              <h1 className="m-0 text-xl font-semibold tracking-[-0.01em]">{activeDeal.name}</h1>
              <span className="font-mono text-[10px] text-[#0a0a0f] bg-[#2DD4BF] px-[7px] py-[2px] font-semibold tracking-[0.05em]">
                {activeDeal.stage}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-[10px] font-mono text-[11px] text-[#6B7280]">
              <span>{activeDeal.sector}</span>
              <span className="text-[#1E1E2E]">|</span>
              <span>{activeDeal.hq}</span>
              <span className="text-[#1E1E2E]">|</span>
              <span>Deal ID {activeDeal.id}</span>
            </div>
          </div>
          <div className="flex-1" />
          <button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="flex items-center gap-2 bg-[#111118] border border-[#1a1a1a] text-[#E8E8F0] px-[13px] py-2 text-xs font-medium cursor-pointer hover:border-[#2c2c42] transition-colors disabled:opacity-50"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={refreshing ? "animate-spin" : ""}>
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            {refreshing ? "Refreshing…" : "Refresh Overview"}
          </button>
        </div>
      </div>

      {/* Overview page */}
      <OverviewPage dealId={id} />
    </div>
  );
}
