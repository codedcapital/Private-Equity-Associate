"use client";

import { useState, useEffect, useCallback } from "react";
import type { NextActionsResponse, NextActionItem } from "@/lib/api";
import { getNextActions } from "@/lib/api";

export interface UseNextActionsResult {
  actions: NextActionItem[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useNextActions(dealId: string): UseNextActionsResult {
  const [actions, setActions] = useState<NextActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const numericDealId = parseInt(dealId, 10);
      if (Number.isNaN(numericDealId)) throw new Error(`Invalid deal ID: ${dealId}`);
      const res = await getNextActions(numericDealId);
      setActions(res.actions ?? []);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load next actions";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { actions, loading, error, refetch: fetchData };
}
