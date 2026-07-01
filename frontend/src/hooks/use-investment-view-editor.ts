"use client";

import { useState, useEffect, useCallback } from "react";
import { createOrEditInvestmentView, getDealOverview } from "@/lib/api";
import { mapBackendToFrontend } from "@/lib/api";
import type { DealOverview } from "@/types/overview";

export interface UseInvestmentViewEditorResult {
  saving: boolean;
  error: string | null;
  saveView: (content: string, recommendation?: string, confidenceScore?: number) => Promise<void>;
}

export function useInvestmentViewEditor(dealId: string): UseInvestmentViewEditorResult {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const numericDealId = parseInt(dealId, 10);

  const saveView = useCallback(async (
    content: string, recommendation?: string, confidenceScore?: number
  ) => {
    setSaving(true);
    setError(null);
    try {
      await createOrEditInvestmentView(numericDealId, {
        content: { text: content, blocks: [{ type: "paragraph", text: content }] },
        recommendation: recommendation ?? null,
        confidence_score: confidenceScore ?? null,
        authored_by: "user",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save investment view");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [numericDealId]);

  return { saving, error, saveView };
}
