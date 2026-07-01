"use client";

import { useState, useEffect, useCallback } from "react";
import { getDealSettings, updateDealSettings } from "@/lib/api";
import type { DealSettings } from "@/lib/api";

export interface UseDealSettingsResult {
  settings: DealSettings | null;
  loading: boolean;
  error: string | null;
  updateWeights: (weights: Record<string, number> | null) => Promise<void>;
  refetch: () => void;
}

export function useDealSettings(dealId: string): UseDealSettingsResult {
  const [settings, setSettings] = useState<DealSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const numericDealId = parseInt(dealId, 10);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (Number.isNaN(numericDealId)) throw new Error(`Invalid deal ID: ${dealId}`);
      const res = await getDealSettings(numericDealId);
      setSettings(res);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load settings";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  const updateWeights = useCallback(async (weights: Record<string, number> | null) => {
    setLoading(true);
    setError(null);
    try {
      const res = await updateDealSettings(numericDealId, weights);
      setSettings(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update settings");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [numericDealId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { settings, loading, error, updateWeights, refetch: fetchData };
}
