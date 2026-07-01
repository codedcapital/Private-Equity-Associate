"use client";

import { useState, useEffect, useCallback } from "react";
import { getRecentChanges } from "@/lib/api";
import type { RecentChangeItem } from "@/lib/api";

export interface UseRecentChangesResult {
  changes: RecentChangeItem[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRecentChanges(dealId: string): UseRecentChangesResult {
  const [changes, setChanges] = useState<RecentChangeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const numericDealId = parseInt(dealId, 10);
      if (Number.isNaN(numericDealId)) throw new Error(`Invalid deal ID: ${dealId}`);
      const res = await getRecentChanges(numericDealId);
      setChanges(res.changes ?? []);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load recent changes";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { changes, loading, error, refetch: fetchData };
}
