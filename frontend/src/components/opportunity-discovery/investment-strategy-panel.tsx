"use client";

import { useState } from "react";
import { useInvestmentStrategy } from "@/hooks/use-investment-strategy";
import { useToast } from "@/components/toast";
import type { InvestmentStrategy } from "@/lib/api";

export function InvestmentStrategyPanel() {
  const { strategy, loading, saving, save } = useInvestmentStrategy();
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);

  const handleSave = async (updates: Partial<InvestmentStrategy>) => {
    const ok = await save(updates);
    if (ok) {
      addToast("success", "Strategy updated", "Investment strategy has been saved.");
      setEditing(false);
    } else {
      addToast("error", "Save failed", "Could not update strategy.");
    }
  };

  if (loading) {
    return (
      <div className="border border-[#1E1E2E] bg-[#111118] p-5">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-[#1E1E2E] rounded w-1/3" />
          <div className="h-3 bg-[#1E1E2E] rounded w-1/2" />
          <div className="h-3 bg-[#1E1E2E] rounded w-2/3" />
        </div>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="border border-[#1E1E2E] bg-[#111118] p-5">
        <div className="text-sm text-[#9aa0ad]">No active investment strategy configured.</div>
      </div>
    );
  }

  const criteria = strategy.criteria;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-[13px] font-semibold text-[#E8E8F0]">Investment Strategy</h2>
          <p className="text-[11px] text-[#6B7280] mt-0.5">Living investment mandate — continuously screening the universe</p>
        </div>
        <button
          onClick={() => setEditing(!editing)}
          disabled={saving}
          className="text-[11px] font-mono tracking-[0.03em] text-[#C8A96E] border border-[#C8A96E]/30 px-3 py-[6px] hover:bg-[#C8A96E]/10 transition-colors disabled:opacity-50"
        >
          {editing ? "CANCEL" : "EDIT STRATEGY"}
        </button>
      </div>

      {editing ? (
        <StrategyEditor strategy={strategy} onSave={handleSave} onCancel={() => setEditing(false)} saving={saving} />
      ) : (
        <div className="border border-[#1E1E2E] bg-[#111118]">
          {/* Strategy name */}
          <div className="px-5 py-3 border-b border-[#1E1E2E] flex items-center gap-3">
            <span className="text-[15px] font-semibold text-[#E8E8F0]">{strategy.name}</span>
            {strategy.is_default && (
              <span className="font-mono text-[9px] text-[#2DD4BF] border border-[#2DD4BF]/30 px-1.5 py-0.5 tracking-[0.05em]">
                DEFAULT
              </span>
            )}
          </div>

          {/* Criteria grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#1E1E2E]">
            <CriterionCell label="Sectors" value={formatList(criteria.sectors)} />
            <CriterionCell label="Geography" value={formatList(criteria.geographies)} />
            <CriterionCell label="Revenue" value={formatRange(criteria.min_revenue, criteria.max_revenue, "$", "M")} />
            <CriterionCell label="EBITDA" value={formatRange(criteria.min_ebitda, criteria.max_ebitda, "$", "M")} />
            <CriterionCell label="EBITDA Margin" value={criteria.min_ebitda_margin != null ? `${(criteria.min_ebitda_margin * 100).toFixed(0)}%+` : "—"} />
            <CriterionCell label="Revenue Growth" value={criteria.min_revenue_growth != null ? `${(criteria.min_revenue_growth * 100).toFixed(0)}%+` : "—"} />
            <CriterionCell label="Max Leverage" value={criteria.max_net_debt_ebitda != null ? `<${criteria.max_net_debt_ebitda}x` : "—"} />
            <CriterionCell label="Business Model" value={formatList(criteria.business_models)} />
          </div>
        </div>
      )}
    </section>
  );
}

function CriterionCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#111118] px-4 py-3">
      <div className="font-mono text-[9px] tracking-[0.06em] uppercase text-[#6B7280] mb-1">{label}</div>
      <div className="text-[13px] text-[#E8E8F0]">{value}</div>
    </div>
  );
}

function formatList(items: string[] | undefined | null): string {
  if (!items || items.length === 0) return "Any";
  if (items.length <= 2) return items.join(", ");
  return `${items[0]}, ${items[1]} +${items.length - 2}`;
}

function formatRange(min: number | null, max: number | null, prefix: string, suffix: string): string {
  if (min == null && max == null) return "Any";
  const minStr = min != null ? `${prefix}${(min / 1e6).toFixed(0)}${suffix}` : "";
  const maxStr = max != null ? `${prefix}${(max / 1e6).toFixed(0)}${suffix}` : "";
  if (minStr && maxStr) return `${minStr} – ${maxStr}`;
  return minStr || maxStr || "Any";
}

// ── Strategy Editor ─────────────────────────────────────────────────────────

function StrategyEditor({
  strategy,
  onSave,
  onCancel,
  saving,
}: {
  strategy: InvestmentStrategy;
  onSave: (updates: Partial<InvestmentStrategy>) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [name, setName] = useState(strategy.name);
  const [criteria, setCriteria] = useState(strategy.criteria);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ name, criteria });
  };

  const updateCriteria = (key: string, value: any) => {
    setCriteria((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="border border-[#C8A96E]/30 bg-[#111118] p-5">
      <div className="space-y-4">
        <div>
          <label className="font-mono text-[10px] tracking-[0.06em] uppercase text-[#6B7280] block mb-1">
            Strategy Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-[#0A0A0F] border border-[#1E1E2E] px-3 py-2 text-[13px] text-[#E8E8F0] outline-none focus:border-[#C8A96E]"
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <NumberField
            label="Min Revenue ($M)"
            value={criteria.min_revenue != null ? criteria.min_revenue / 1e6 : ""}
            onChange={(v) => updateCriteria("min_revenue", v ? v * 1e6 : null)}
          />
          <NumberField
            label="Max Revenue ($M)"
            value={criteria.max_revenue != null ? criteria.max_revenue / 1e6 : ""}
            onChange={(v) => updateCriteria("max_revenue", v ? v * 1e6 : null)}
          />
          <NumberField
            label="Min EBITDA Margin (%)"
            value={criteria.min_ebitda_margin != null ? criteria.min_ebitda_margin * 100 : ""}
            onChange={(v) => updateCriteria("min_ebitda_margin", v ? v / 100 : null)}
          />
          <NumberField
            label="Min Revenue Growth (%)"
            value={criteria.min_revenue_growth != null ? criteria.min_revenue_growth * 100 : ""}
            onChange={(v) => updateCriteria("min_revenue_growth", v ? v / 100 : null)}
          />
          <NumberField
            label="Max Net Debt / EBITDA"
            value={criteria.max_net_debt_ebitda ?? ""}
            onChange={(v) => updateCriteria("max_net_debt_ebitda", v || null)}
          />
          <NumberField
            label="Min FCF Yield (%)"
            value={criteria.min_fcf_yield != null ? criteria.min_fcf_yield * 100 : ""}
            onChange={(v) => updateCriteria("min_fcf_yield", v ? v / 100 : null)}
          />
        </div>
      </div>

      <div className="flex items-center gap-3 mt-5">
        <button
          type="submit"
          disabled={saving}
          className="bg-[#C8A96E] text-[#0A0A0F] px-4 py-[9px] text-[13px] font-semibold hover:bg-[#d8bd86] transition-colors disabled:opacity-50"
        >
          {saving ? "SAVING..." : "SAVE STRATEGY"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-[#1E1E2E] text-[#9aa0ad] px-4 py-[9px] text-[13px] hover:text-[#E8E8F0] transition-colors"
        >
          CANCEL
        </button>
      </div>
    </form>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | number;
  onChange: (v: number | null) => void;
}) {
  return (
    <div>
      <label className="font-mono text-[9px] tracking-[0.06em] uppercase text-[#6B7280] block mb-1">
        {label}
      </label>
      <input
        type="number"
        step="0.1"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === "" ? null : parseFloat(v));
        }}
        className="w-full bg-[#0A0A0F] border border-[#1E1E2E] px-3 py-2 text-[13px] text-[#E8E8F0] outline-none focus:border-[#C8A96E]"
      />
    </div>
  );
}
