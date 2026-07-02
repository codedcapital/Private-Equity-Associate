"use client";

import { useState, useCallback } from "react";
import { getDiscoverySummary, type DiscoverySummary } from "@/lib/api";

export function useDiscoverySummary() {
  const [summary, setSummary] = useState<DiscoverySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async (companyId: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDiscoverySummary(companyId);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load discovery summary");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setSummary(null);
    setError(null);
  }, []);

  return {
    summary,
    loading,
    error,
    fetch: fetchSummary,
    clear,
  };
}
