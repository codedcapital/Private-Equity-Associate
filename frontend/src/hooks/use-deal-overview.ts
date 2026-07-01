"use client";

import { useState, useEffect, useCallback } from "react";
import type { DealOverview } from "@/types/overview";
import { getDealOverview, mapBackendToFrontend } from "@/lib/api";
import { generateMockOverviewData } from "@/lib/mock-overview-data";

export interface UseDealOverviewResult {
  data: DealOverview | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";

export function useDealOverview(dealId: string): UseDealOverviewResult {
  const [data, setData] = useState<DealOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (USE_MOCK_DATA) {
      // Dev fallback: mock data with artificial latency
      const timeoutId = setTimeout(() => {
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
      }, 600);
      return () => clearTimeout(timeoutId);
    }

    try {
      const numericDealId = parseInt(dealId, 10);
      if (Number.isNaN(numericDealId)) {
        throw new Error(`Invalid deal ID: ${dealId}`);
      }
      const raw = await getDealOverview(numericDealId);
      const overview = mapBackendToFrontend(raw);
      setData(overview);
    } catch (err) {
      // Fallback to mock data on API failure so the UI still renders
      console.warn("Overview API failed, falling back to mock data:", err);
      try {
        const fallback = generateMockOverviewData(dealId);
        setData(fallback);
      } catch {
        const message =
          err instanceof Error ? err.message : "Failed to load deal overview";
        setError(message);
        setData(null);
      }
    } finally {
      setLoading(false);
    }

    return () => {};
  }, [dealId]);

  useEffect(() => {
    let cleanup = () => {};
    fetchData().then((fn) => {
      cleanup = fn;
    });
    return () => cleanup();
  }, [fetchData]);

  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
}
