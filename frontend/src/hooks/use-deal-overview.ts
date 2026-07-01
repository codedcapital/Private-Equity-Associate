"use client";

import { useState, useEffect, useCallback } from "react";
import type { DealOverview } from "@/types/overview";
import { generateMockOverviewData } from "@/lib/mock-overview-data";

export interface UseDealOverviewResult {
  data: DealOverview | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDealOverview(dealId: string): UseDealOverviewResult {
  const [data, setData] = useState<DealOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    try {
      const result = generateMockOverviewData(dealId);
      setData(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load deal overview";
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const refetch = useCallback(() => {
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch };
}
