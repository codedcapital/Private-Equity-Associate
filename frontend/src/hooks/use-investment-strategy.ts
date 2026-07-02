"use client";

import { useState, useEffect, useCallback } from "react";
import { getActiveStrategy, updateStrategy, type InvestmentStrategy } from "@/lib/api";

export function useInvestmentStrategy() {
  const [strategy, setStrategy] = useState<InvestmentStrategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchStrategy = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getActiveStrategy();
      setStrategy(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load strategy");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  const saveStrategy = useCallback(async (updates: Partial<InvestmentStrategy>) => {
    setSaving(true);
    setError(null);
    try {
      const data = await updateStrategy(updates);
      setStrategy(data);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save strategy");
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  return {
    strategy,
    loading,
    error,
    saving,
    refresh: fetchStrategy,
    save: saveStrategy,
  };
}
