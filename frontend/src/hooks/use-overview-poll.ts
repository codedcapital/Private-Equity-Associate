"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiCall } from "@/lib/api";

export interface SectionStatus {
  last_updated: string | null;
  count?: number;
}

export interface OverviewStatus {
  deal_id: number;
  sections: {
    investment_view: SectionStatus;
    confidence: SectionStatus;
    diligence: SectionStatus;
    evidence: SectionStatus;
    events: SectionStatus;
  };
  running_modules: string[];
  poll_again_in_seconds: number;
}

export interface UseOverviewPollResult {
  status: OverviewStatus | null;
  hasChanged: (section: keyof OverviewStatus["sections"], since: string | null) => boolean;
  isRunning: (section: string) => boolean;
  lastPolled: Date | null;
}

export function useOverviewPoll(dealId: string): UseOverviewPollResult {
  const [status, setStatus] = useState<OverviewStatus | null>(null);
  const [lastPolled, setLastPolled] = useState<Date | null>(null);
  const previousRef = useRef<OverviewStatus | null>(null);

  const numericDealId = parseInt(dealId, 10);

  const poll = useCallback(async () => {
    if (Number.isNaN(numericDealId)) return;
    try {
      const res = await apiCall<OverviewStatus>(`/deals/${numericDealId}/overview/status`);
      previousRef.current = status;
      setStatus(res);
      setLastPolled(new Date());
    } catch {
      // Silently fail — don't break the UI on polling errors
    }
  }, [numericDealId, status]);

  useEffect(() => {
    // Initial poll
    poll();

    // Set up interval
    const interval = setInterval(poll, 10_000); // 10 seconds
    return () => clearInterval(interval);
  }, [poll]);

  const hasChanged = useCallback(
    (section: keyof OverviewStatus["sections"], since: string | null): boolean => {
      if (!status) return false;
      const current = status.sections[section]?.last_updated;
      if (!current) return false;
      if (!since) return true;
      return new Date(current) > new Date(since);
    },
    [status]
  );

  const isRunning = useCallback(
    (section: string): boolean => {
      if (!status) return false;
      const moduleMap: Record<string, string[]> = {
        evidence: ["evidence_refreshed"],
        confidence: ["confidence_recalculated"],
      };
      const eventTypes = moduleMap[section] ?? [];
      return status.running_modules.some((r) => eventTypes.includes(r));
    },
    [status]
  );

  return { status, hasChanged, isRunning, lastPolled };
}
