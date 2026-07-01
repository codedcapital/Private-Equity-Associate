"use client";

import { useState, useCallback } from "react";
import { updateEvidenceStatus, createEvidenceConflict } from "@/lib/api";

export interface UseEvidenceUpdateResult {
  updating: boolean;
  error: string | null;
  updateStatus: (evidenceId: number, status: string, conflictDescription?: string) => Promise<void>;
  createConflict: (evidenceId: number, evidenceBId: number, description: string) => Promise<void>;
}

export function useEvidenceUpdate(dealId: string): UseEvidenceUpdateResult {
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const numericDealId = parseInt(dealId, 10);

  const updateStatus = useCallback(async (
    evidenceId: number, status: string, conflictDescription?: string
  ) => {
    setUpdating(true);
    setError(null);
    try {
      await updateEvidenceStatus(numericDealId, evidenceId, status, conflictDescription ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update evidence");
      throw err;
    } finally {
      setUpdating(false);
    }
  }, [numericDealId]);

  const createConflict = useCallback(async (
    evidenceId: number, evidenceBId: number, description: string
  ) => {
    setUpdating(true);
    setError(null);
    try {
      await createEvidenceConflict(numericDealId, evidenceId, evidenceBId, description);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create conflict");
      throw err;
    } finally {
      setUpdating(false);
    }
  }, [numericDealId]);

  return { updating, error, updateStatus, createConflict };
}
