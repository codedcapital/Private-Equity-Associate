"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getCoverageMetrics,
  getOpportunities,
  getSignalFeed,
  getDailyBriefing,
  getStrategyCoverage,
  type CoverageMetrics,
  type OpportunityItem,
  type SignalFeedItem,
  type DailyBriefing,
  type StrategyCoverage,
} from "@/lib/api";

export function useOpportunityDiscovery() {
  const [coverage, setCoverage] = useState<CoverageMetrics | null>(null);
  const [opportunities, setOpportunities] = useState<OpportunityItem[]>([]);
  const [signals, setSignals] = useState<SignalFeedItem[]>([]);
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [strategyCoverage, setStrategyCoverage] = useState<StrategyCoverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [coverageData, oppData, signalData, briefingData, coverageStratData] = await Promise.all([
        getCoverageMetrics(),
        getOpportunities({ min_score: 70, limit: 50 }),
        getSignalFeed({ limit: 20 }),
        getDailyBriefing(),
        getStrategyCoverage(),
      ]);
      setCoverage(coverageData);
      setOpportunities(oppData);
      setSignals(signalData);
      setBriefing(briefingData);
      setStrategyCoverage(coverageStratData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load opportunity discovery data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const refreshOpportunities = useCallback(async () => {
    try {
      const data = await getOpportunities({ min_score: 70, limit: 50 });
      setOpportunities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh opportunities");
    }
  }, []);

  return {
    coverage,
    opportunities,
    signals,
    briefing,
    strategyCoverage,
    loading,
    error,
    refresh: fetchAll,
    refreshOpportunities,
  };
}
