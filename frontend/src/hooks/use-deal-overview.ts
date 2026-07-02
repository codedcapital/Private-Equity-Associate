"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  DealOverview,
  InvestmentView,
  Score,
  EvidenceModule,
  DiligenceItem,
  Readiness,
  ActivityEvent,
  NextAction,
} from "@/types/overview";
import { getOverview, type OverviewResponse } from "@/lib/api";

/* ── helpers: render backend dict-content as HTML ── */

function renderContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (content && typeof content === "object") {
    const c = content as Record<string, unknown>;
    // 1. Try "text" field
    if (typeof c.text === "string" && c.text) {
      return `<p>${escapeHtml(c.text)}</p>`;
    }
    // 2. Try "blocks" array
    if (Array.isArray(c.blocks)) {
      return c.blocks
        .map((b: any) => {
          const text = b?.text ?? b?.content ?? "";
          if (b?.type === "heading" || b?.type === "h2") {
            return `<h2>${escapeHtml(text)}</h2>`;
          }
          return `<p>${escapeHtml(text)}</p>`;
        })
        .join("\n");
    }
    // 3. Fallback: JSON stringify as readable text
    return `<pre style="white-space:pre-wrap">${escapeHtml(JSON.stringify(c, null, 2))}</pre>`;
  }
  return String(content ?? "");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ── helpers: derive recommendation from score ── */

function deriveRecommendation(score: number): Score["recommendation"] {
  if (score >= 75) return "PROCEED";
  if (score >= 55) return "CONDITIONAL";
  if (score >= 35) return "HOLD";
  return "DECLINE";
}

/* ── transform backend → frontend ── */

function transformBackendToOverview(raw: OverviewResponse, dealId: string): DealOverview {
  const company = raw?.company ?? {};

  const investmentView: InvestmentView | null = raw?.investment_view
    ? {
        id: String(raw.investment_view.id ?? `view-${dealId}`),
        content: renderContent(raw.investment_view.content),
        sources: ["Intelligence Engine"],
        updatedAt:
          raw.investment_view.updated_at ?? new Date().toISOString(),
      }
    : null;

  const score: Score | null = raw?.confidence
    ? {
        value: Math.round(raw.confidence.final_score ?? 0),
        recommendation: deriveRecommendation(raw.confidence.final_score ?? 0),
        confidence: Math.round(raw.confidence.base_score ?? 0),
        breakdown: (raw.confidence.factors ?? []).map((f: any) => ({
          label: f.name ?? "Factor",
          weight: f.weight ?? 0,
          score: f.contribution ?? 0,
          contribution: f.contribution ?? 0,
        })),
      }
    : null;

  const evidence: EvidenceModule[] = (raw?.evidence ?? []).map((e: any) => ({
    id: String(e.id ?? `ev-${Math.random().toString(36).slice(2, 7)}`),
    name: e.module_name ?? e.name ?? e.source ?? "Evidence",
    status: ((e.status ?? "UNKNOWN").toUpperCase().replace(/\s+/g, "_") || "UNKNOWN") as EvidenceModule["status"],
    summary: e.text ?? e.summary ?? "",
    sourceReference: e.source ?? e.sourceReference ?? "",
    rawData: e.rawData ?? undefined,
  }));

  const diligence: DiligenceItem[] = (raw?.diligence?.items ?? []).map(
    (d: any) => ({
      id: String(d.id ?? `dd-${Math.random().toString(36).slice(2, 7)}`),
      title: d.title ?? "Diligence item",
      category: d.category ?? "General",
      owner: d.assigned_to ?? d.owner ?? "Unassigned",
      dueDate: d.due_date ? String(d.due_date) : new Date().toISOString(),
      completed: (d.status ?? "") === "complete" || d.completed === true,
    })
  );

  const readiness: Readiness | null = raw?.decision_readiness
    ? {
        score: Math.round(raw.decision_readiness.score ?? 0),
        items: [
          ...(raw.decision_readiness.met ?? []).map((m: string) => ({
            label: m,
            met: true,
          })),
          ...(raw.decision_readiness.unmet ?? []).map((u: string) => ({
            label: u,
            met: false,
          })),
        ],
      }
    : null;

  const activity: ActivityEvent[] = (raw?.recent_events ?? []).map((e: any) => ({
    id: String(e.id ?? `act-${Math.random().toString(36).slice(2, 7)}`),
    timestamp: e.created_at ?? e.timestamp ?? new Date().toISOString(),
    actor: e.actor_type ?? e.actor ?? "System",
    description: e.description ?? "",
  }));

  const nextAction: NextAction | null = null; // Backend has separate endpoint

  return {
    deal: {
      id: dealId,
      name: company.name ?? `Deal ${dealId}`,
      stage: (raw?.stage ?? "—").toUpperCase(),
      sector: company.sector ?? "—",
      hq: company.geography ?? "—",
    },
    investmentView,
    score,
    evidence,
    diligence,
    readiness,
    activity,
    nextAction,
  };
}

/* ── hook ── */

export interface UseDealOverviewResult {
  data: DealOverview | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  rawResponse: OverviewResponse | null;
}

export function useDealOverview(dealId: string): UseDealOverviewResult {
  const [data, setData] = useState<DealOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rawResponse, setRawResponse] = useState<OverviewResponse | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setRawResponse(null);

    try {
      const numericId = parseInt(dealId, 10);

      if (isNaN(numericId)) {
        throw new Error(`Invalid deal ID: "${dealId}"`);
      }

      const backendData = await getOverview(numericId);
      console.log("[useDealOverview] raw response:", JSON.stringify(backendData, null, 2));
      setRawResponse(backendData);
      const result = transformBackendToOverview(backendData, dealId);
      console.log("[useDealOverview] transformed:", result);
      setData(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load deal overview";
      setError(message);
      setData(null);
      console.error("[useDealOverview] error:", err);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const refetch = useCallback(() => {
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch, rawResponse };
}
