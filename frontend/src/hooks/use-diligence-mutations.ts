"use client";

import { useState, useCallback } from "react";
import {
  createDiligenceItem,
  updateDiligenceItem,
  deleteDiligenceItem,
} from "@/lib/api";

export interface UseDiligenceMutationsResult {
  loading: boolean;
  error: string | null;
  addItem: (payload: {
    category: string;
    title: string;
    description?: string | null;
    assigned_to?: string | null;
    due_date?: string | null;
    priority?: string;
  }) => Promise<void>;
  toggleItem: (itemId: number, completed: boolean) => Promise<void>;
  updateItem: (itemId: number, payload: Record<string, any>) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
}

export function useDiligenceMutations(dealId: string): UseDiligenceMutationsResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const numericDealId = parseInt(dealId, 10);

  const addItem = useCallback(async (payload: {
    category: string;
    title: string;
    description?: string | null;
    assigned_to?: string | null;
    due_date?: string | null;
    priority?: string;
  }) => {
    setLoading(true);
    setError(null);
    try {
      await createDiligenceItem(numericDealId, {
        ...payload,
        status: "not_started",
        created_by: "user",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add diligence item");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [numericDealId]);

  const toggleItem = useCallback(async (itemId: number, completed: boolean) => {
    setLoading(true);
    setError(null);
    try {
      await updateDiligenceItem(numericDealId, itemId, {
        status: completed ? "complete" : "not_started",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update diligence item");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [numericDealId]);

  const updateItem = useCallback(async (itemId: number, payload: Record<string, any>) => {
    setLoading(true);
    setError(null);
    try {
      await updateDiligenceItem(numericDealId, itemId, payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update diligence item");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [numericDealId]);

  const removeItem = useCallback(async (itemId: number) => {
    setLoading(true);
    setError(null);
    try {
      await deleteDiligenceItem(numericDealId, itemId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete diligence item");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [numericDealId]);

  return { loading, error, addItem, toggleItem, updateItem, removeItem };
}
