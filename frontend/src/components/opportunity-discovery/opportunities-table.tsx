"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/components/toast";
import { useDiscoverySummary } from "@/hooks/use-discovery-summary";
import { createDeal } from "@/lib/api";
import type { OpportunityItem } from "@/lib/api";

export function OpportunitiesTable({ opportunities }: { opportunities: OpportunityItem[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [adding, setAdding] = useState<Set<number>>(new Set());
  const { addToast } = useToast();

  const handleAddToPipeline = async (opp: OpportunityItem) => {
    if (!opp.company_id) return;
    setAdding((prev) => new Set(prev).add(opp.company_id));
    try {
      await createDeal(opp.company_id);
      addToast("success", "Added to pipeline", `${opp.company_name} added to the deal pipeline.`);
    } catch (err) {
      addToast("error", "Failed to add", err instanceof Error ? err.message : "Backend error.");
    } finally {
      setAdding((prev) => {
        const next = new Set(prev);
        next.delete(opp.company_id);
        return next;
      });
    }
  };

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[#E8E8F0]">Highest Conviction Opportunities</h2>
        <p className="text-[11px] text-[#6B7280] mt-0.5">
          Companies that best match your investment strategy
        </p>
      </div>

      {opportunities.length === 0 ? (
        <div className="border border-dashed border-[#1E1E2E] p-8 text-center">
          <div className="text-sm text-[#9aa0ad]">No opportunities match your current strategy</div>
          <div className="mt-1 font-mono text-[11px] text-[#4b5160]">
            Try broadening your criteria or wait for new data
          </div>
        </div>
      ) : (
        <div className="border border-[#1E1E2E]">
          {/* Header */}
          <div className="grid grid-cols-[1.5fr_80px_80px_1fr_100px_130px] bg-[#0A0A0F] border-b border-[#1E1E2E]">
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Company</div>
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] text-right">Fit</div>
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280] text-right">Conf</div>
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Why</div>
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]">Trend</div>
            <div className="px-3 py-[9px] font-mono text-[10px] tracking-[0.05em] uppercase text-[#6B7280]"></div>
          </div>

          {/* Rows */}
          {opportunities.map((opp) => (
            <OpportunityRow
              key={opp.company_id}
              opp={opp}
              isExpanded={expandedId === opp.company_id}
              onToggle={() => setExpandedId(expandedId === opp.company_id ? null : opp.company_id)}
              onAddToPipeline={() => handleAddToPipeline(opp)}
              isAdding={adding.has(opp.company_id)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function OpportunityRow({
  opp,
  isExpanded,
  onToggle,
  onAddToPipeline,
  isAdding,
}: {
  opp: OpportunityItem;
  isExpanded: boolean;
  onToggle: () => void;
  onAddToPipeline: () => void;
  isAdding: boolean;
}) {
  const tier = opp.fit_score >= 85 ? "green" : opp.fit_score >= 70 ? "amber" : "red";
  const tierColor = tier === "green" ? "#10B981" : tier === "amber" ? "#F59E0B" : "#EF4444";

  return (
    <div className="border-b border-[#1E1E2E] last:border-b-0">
      <div
        className="grid grid-cols-[1.5fr_80px_80px_1fr_100px_130px] items-center hover:bg-[#111118] transition-colors cursor-pointer"
        onClick={onToggle}
      >
        <div className="px-3 py-[11px]">
          <div className="text-[13px] font-semibold text-[#E8E8F0]">{opp.company_name}</div>
          <div className="text-[10px] text-[#6B7280] mt-0.5">
            {opp.ticker && <span className="font-mono text-[#C8A96E]">{opp.ticker}</span>}
            {opp.ticker && opp.sector && <span className="mx-1">·</span>}
            {opp.sector && <span>{opp.sector}</span>}
          </div>
        </div>

        <div className="px-3 py-[11px] text-right">
          <span className="font-mono text-[13px] font-semibold" style={{ color: tierColor }}>
            {opp.fit_score}
          </span>
        </div>

        <div className="px-3 py-[11px] text-right">
          <span className="font-mono text-[13px] text-[#E8E8F0]">
            {Math.round((opp.confidence_score || 0) * 100)}
          </span>
        </div>

        <div className="px-3 py-[11px] text-[11px] text-[#9aa0ad] truncate">
          {opp.why}
        </div>

        <div className="px-3 py-[11px]">
          {opp.trend != null ? (
            <span
              className={`font-mono text-[11px] ${
                opp.trend > 0 ? "text-[#10B981]" : opp.trend < 0 ? "text-[#EF4444]" : "text-[#6B7280]"
              }`}
            >
              {opp.trend > 0 ? "↑" : opp.trend < 0 ? "↓" : "→"} {Math.abs(opp.trend)}
            </span>
          ) : (
            <span className="font-mono text-[11px] text-[#4b5160]">—</span>
          )}
        </div>

        <div className="px-3 py-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddToPipeline();
            }}
            disabled={isAdding || opp.has_deal}
            className="w-full bg-[#111118] border border-[#2c2c42] text-[#2DD4BF] px-2 py-[6px] text-[11px] font-semibold font-mono tracking-[0.03em] hover:border-[#2DD4BF] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {opp.has_deal ? "IN PIPELINE" : isAdding ? "ADDING…" : "+ PIPELINE"}
          </button>
        </div>
      </div>

      {isExpanded && (
        <DiscoverySummaryRow companyId={opp.company_id} />
      )}
    </div>
  );
}

function DiscoverySummaryRow({ companyId }: { companyId: number }) {
  const { summary, loading, error, fetch } = useDiscoverySummary();

  useEffect(() => {
    fetch(companyId);
  }, [companyId, fetch]);

  if (loading) {
    return (
      <div className="px-5 py-4 bg-[#0A0A0F] border-t border-[#1E1E2E]">
        <div className="animate-pulse space-y-2">
          <div className="h-3 bg-[#1E1E2E] rounded w-1/4" />
          <div className="h-3 bg-[#1E1E2E] rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="px-5 py-4 bg-[#0A0A0F] border-t border-[#1E1E2E]">
        <div className="text-[11px] text-[#EF4444]">{error || "Failed to load summary"}</div>
      </div>
    );
  }

  return (
    <div className="px-5 py-4 bg-[#0A0A0F] border-t border-[#1E1E2E]">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Why surfaced + Matches */}
        <div>
          <div className="text-[11px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mb-2">
            Why Surfaced?
          </div>
          <ul className="space-y-1">
            {summary.why_surfaced.map((reason, i) => (
              <li key={i} className="text-[12px] text-[#E8E8F0] flex items-start gap-2">
                <span className="text-[#10B981] mt-0.5">✓</span>
                {reason}
              </li>
            ))}
          </ul>

          <div className="mt-4 text-[11px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mb-2">
            Matches
          </div>
          <ul className="space-y-1">
            {summary.matches.map((match, i) => (
              <li key={i} className="text-[12px] text-[#E8E8F0] flex items-start gap-2">
                <span className={match.status === "pass" ? "text-[#10B981]" : "text-[#EF4444]"}>
                  {match.status === "pass" ? "✓" : "✗"}
                </span>
                {match.criterion}
                {match.detail && <span className="text-[#6B7280] ml-1">— {match.detail}</span>}
              </li>
            ))}
          </ul>
        </div>

        {/* Right: Concerns + Evidence + Decision */}
        <div>
          {summary.concerns.length > 0 && (
            <>
              <div className="text-[11px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mb-2">
                Potential Concerns
              </div>
              <ul className="space-y-1">
                {summary.concerns.map((concern, i) => (
                  <li key={i} className="text-[12px] text-[#E8E8F0] flex items-start gap-2">
                    <span className="text-[#EF4444] mt-0.5">•</span>
                    {concern}
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="mt-4">
            <div className="text-[11px] font-mono tracking-[0.05em] uppercase text-[#6B7280] mb-2">
              Evidence Coverage
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-[6px] bg-[#1E1E2E] relative">
                <div
                  className="absolute left-0 top-0 bottom-0 bg-[#C8A96E]"
                  style={{ width: `${summary.evidence_coverage}%` }}
                />
              </div>
              <span className="font-mono text-[11px] text-[#E8E8F0]">{summary.evidence_coverage}%</span>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <div className="text-[11px] font-mono tracking-[0.05em] uppercase text-[#6B7280]">
              Decision
            </div>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 border ${
                summary.recommendation === "PROCEED"
                  ? "text-[#10B981] border-[#10B981]/30"
                  : summary.recommendation === "CONDITIONAL"
                  ? "text-[#F59E0B] border-[#F59E0B]/30"
                  : "text-[#EF4444] border-[#EF4444]/30"
              }`}
            >
              {summary.recommendation}
            </span>
          </div>

          {summary.has_deal && (
            <div className="mt-4">
              <a
                href={`/deal/${summary.deal_id}`}
                className="inline-flex items-center gap-2 text-[11px] font-semibold text-[#C8A96E] hover:underline"
              >
                Open Investment Workspace
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M7 17L17 7M17 7H7M17 7V17" />
                </svg>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
