"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import type { ViewMode } from "@/types/overview";
import { useDealOverview } from "@/hooks/use-deal-overview";
import { useViewMode } from "@/hooks/use-view-mode";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { useOverviewPoll } from "@/hooks/use-overview-poll";
import { useThemeMode } from "@/hooks/use-theme-mode";
import { useUser, canViewSection } from "@/contexts/user-context";
import { PageShell } from "@/components/overview/page-shell";
import { InvestmentViewSection } from "@/components/overview/sections/investment-view-section";
import { InvestmentScoreSection } from "@/components/overview/sections/investment-score-section";
import { SupportingEvidenceSection } from "@/components/overview/sections/supporting-evidence-section";
import { OutstandingDiligenceSection } from "@/components/overview/sections/outstanding-diligence-section";
import { DecisionReadinessSection } from "@/components/overview/sections/decision-readiness-section";
import { RecentChangesSection } from "@/components/overview/sections/recent-changes-section";
import { RecommendedActionsSection } from "@/components/overview/sections/recommended-actions-section";

interface OverviewPageProps {
  dealId: string;
}

function HelpModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  const shortcuts = [
    { key: "E", action: "Edit Investment View" },
    { key: "Esc", action: "Cancel Edit / Close Modal" },
    { key: "Cmd+S / Ctrl+S", action: "Save View" },
    { key: "D", action: "Toggle Document / Data View" },
    { key: "?", action: "Show this help" },
    { key: "↑ / ↓", action: "Navigate between sections" },
    { key: "J / K", action: "Navigate between sections (vim-style)" },
  ];
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0a0a0f]/80" onClick={onClose}>
      <div className="bg-[#111118] border border-[#1E1E2E] p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-ov-sans text-sm font-semibold text-[#c7a84b] mb-4">Keyboard Shortcuts</h3>
        <div className="flex flex-col gap-2">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex justify-between items-center text-sm">
              <span className="font-ov-mono text-[10px] text-[#a3a3a3] bg-[#0a0a0f] px-2 py-1 border border-[#1E1E2E]">{s.key}</span>
              <span className="font-ov-sans text-xs text-[#d5d5d5]">{s.action}</span>
            </div>
          ))}
        </div>
        <button onClick={onClose} className="mt-4 w-full bg-[#c7a84b] text-[#0a0a0f] font-ov-sans text-xs font-semibold py-2">Close</button>
      </div>
    </div>
  );
}

function RoleSelector() {
  const { role, setRole } = useUser();
  const roles: Array<{ value: typeof role; label: string }> = [
    { value: "associate", label: "Associate" },
    { value: "vp", label: "VP" },
    { value: "partner", label: "Partner" },
  ];
  return (
    <div className="flex items-center gap-2">
      <span className="font-ov-mono text-[10px] text-[#737373] uppercase tracking-wider">View as</span>
      <div className="flex bg-[#0a0a0f] border border-[#1a1a1a]">
        {roles.map((r) => (
          <button
            key={r.value}
            onClick={() => setRole(r.value)}
            className="font-ov-sans text-[10px] px-2.5 py-1 transition-colors"
            style={{
              color: role === r.value ? "#c7a84b" : "#525252",
              backgroundColor: role === r.value ? "rgba(199,168,75,0.08)" : "transparent",
            }}
          >
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function DataView({ data }: { data: any }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="border border-[#1a1a1a] bg-[#0a0a0f] p-4">
        <h3 className="font-ov-mono text-[10px] uppercase tracking-wider text-[#737373] mb-3">Raw Evidence</h3>
        <pre className="font-ov-mono text-[11px] text-[#525252] overflow-auto max-h-[300px]">
          {JSON.stringify(data?.evidence ?? [], null, 2)}
        </pre>
      </div>
      <div className="border border-[#1a1a1a] bg-[#0a0a0f] p-4">
        <h3 className="font-ov-mono text-[10px] uppercase tracking-wider text-[#737373] mb-3">Confidence Breakdown</h3>
        <pre className="font-ov-mono text-[11px] text-[#525252] overflow-auto max-h-[300px]">
          {JSON.stringify(data?.score ?? null, null, 2)}
        </pre>
      </div>
      <div className="border border-[#1a1a1a] bg-[#0a0a0f] p-4">
        <h3 className="font-ov-mono text-[10px] uppercase tracking-wider text-[#737373] mb-3">Diligence Items</h3>
        <pre className="font-ov-mono text-[11px] text-[#525252] overflow-auto max-h-[300px]">
          {JSON.stringify(data?.diligence ?? [], null, 2)}
        </pre>
      </div>
    </div>
  );
}

function StaleDataBanner({ lastPolled }: { lastPolled: Date | null }) {
  if (!lastPolled) return null;
  const age = Date.now() - lastPolled.getTime();
  const ageSec = Math.round(age / 1000);
  if (ageSec < 30) return null; // Fresh enough
  const text = ageSec < 60 ? `${ageSec}s ago` : `${Math.round(ageSec / 60)}m ago`;
  return (
    <div className="px-5 py-1.5 bg-[#c7a84b]/10 border-b border-[#c7a84b]/20" role="status" aria-live="polite">
      <span className="font-ov-sans text-[10px] text-[#c7a84b]">
        Data as of {lastPolled.toLocaleTimeString()} ({text}). Refresh for latest.
      </span>
    </div>
  );
}

function ProgressIndicator({ running }: { running: boolean }) {
  if (!running) return null;
  return (
    <span className="inline-flex items-center gap-1.5 ml-2" aria-label="Processing">
      <span className="w-1.5 h-1.5 bg-[#2DD4BF] rounded-full animate-pulse" />
      <span className="font-ov-mono text-[9px] text-[#2DD4BF] uppercase tracking-wider">Processing</span>
    </span>
  );
}

function HighContrastToggle({ isHighContrast, toggle }: { isHighContrast: boolean; toggle: () => void }) {
  return (
    <button
      onClick={toggle}
      className="font-ov-sans text-[10px] px-2.5 py-1 border border-[#1a1a1a] text-[#a3a3a3] hover:text-[#e5e5e5] transition-colors"
      aria-label={isHighContrast ? "Switch to default theme" : "Switch to high contrast theme"}
      aria-pressed={isHighContrast}
    >
      {isHighContrast ? "Default Theme" : "High Contrast"}
    </button>
  );
}

export function OverviewPage({ dealId }: OverviewPageProps) {
  const { data, loading, refetch } = useDealOverview(dealId);
  const { viewMode, toggleViewMode } = useViewMode();
  const { role } = useUser();
  const { status, hasChanged, isRunning, lastPolled } = useOverviewPoll(dealId);
  const { isHighContrast, toggleTheme } = useThemeMode();
  const [helpOpen, setHelpOpen] = useState(false);
  const [editingView, setEditingView] = useState(false);
  const [activeSection, setActiveSection] = useState(0);
  const pageRef = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<(HTMLElement | null)[]>([]);

  const handleEdit = useCallback(() => setEditingView(true), []);
  const handleCancel = useCallback(() => setEditingView(false), []);
  const handleSave = useCallback(() => {
    setEditingView(false);
  }, []);

  // Keyboard section navigation
  const navigateSection = useCallback((direction: "next" | "prev") => {
    const sections = sectionRefs.current.filter(Boolean);
    if (sections.length === 0) return;
    const nextIndex = direction === "next"
      ? Math.min(activeSection + 1, sections.length - 1)
      : Math.max(activeSection - 1, 0);
    setActiveSection(nextIndex);
    sections[nextIndex]?.scrollIntoView({ behavior: "smooth", block: "start" });
    sections[nextIndex]?.focus();
  }, [activeSection]);

  useKeyboardShortcuts({
    onEdit: handleEdit,
    onSave: handleSave,
    onCancel: handleCancel,
    onToggleDataView: toggleViewMode,
    onHelp: () => setHelpOpen(true),
    onEscape: () => setHelpOpen(false),
  });

  // Add arrow key navigation for sections
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable)) {
        return;
      }
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        navigateSection("next");
      }
      if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        navigateSection("prev");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigateSection]);

  // Auto-refresh when sections change
  useEffect(() => {
    if (status && !loading) {
      const sections: Array<keyof typeof status.sections> = ["investment_view", "confidence", "diligence", "evidence"];
      const anyChanged = sections.some((s) => hasChanged(s, data?.deal?.id ? null : null));
      if (anyChanged) {
        refetch();
      }
    }
  }, [status, loading, hasChanged, refetch, data?.deal?.id]);

  const handleExportPDF = useCallback(() => {
    if (typeof window === "undefined") return;
    window.print();
  }, []);

  const deal = data?.deal ?? {
    id: dealId,
    name: "Loading…",
    stage: "—",
    sector: "—",
    hq: "—",
  };

  const registerSectionRef = (index: number) => (el: HTMLElement | null) => {
    sectionRefs.current[index] = el;
  };

  return (
    <div ref={pageRef}>
      <StaleDataBanner lastPolled={lastPolled} />

      <div className="flex items-center justify-between px-5 py-2 border-b border-[#1a1a1a] bg-[#0a0a0f]">
        <div className="flex items-center gap-3">
          <RoleSelector />
          <span className="font-ov-mono text-[10px] text-[#525252]">|</span>
          <button
            onClick={toggleViewMode}
            className="font-ov-sans text-[10px] px-2.5 py-1 border border-[#1a1a1a] text-[#a3a3a3] hover:text-[#e5e5e5] transition-colors"
          >
            {viewMode === "document" ? "Data View (D)" : "Document View (D)"}
          </button>
          <button
            onClick={handleExportPDF}
            className="font-ov-sans text-[10px] px-2.5 py-1 border border-[#1a1a1a] text-[#a3a3a3] hover:text-[#e5e5e5] transition-colors"
          >
            Export PDF
          </button>
          <HighContrastToggle isHighContrast={isHighContrast} toggle={toggleTheme} />
        </div>
        <div className="flex items-center gap-2">
          {status && (
            <span className="font-ov-mono text-[10px] text-[#525252]">
              Last sync: {lastPolled?.toLocaleTimeString() ?? "—"}
            </span>
          )}
          <span className="font-ov-mono text-[10px] text-[#525252]">Press ? for shortcuts</span>
        </div>
      </div>

      <PageShell deal={deal} viewMode={viewMode} onToggleView={toggleViewMode}>
        {viewMode === "data" ? (
          <DataView data={data} />
        ) : (
          <div className="flex flex-col" style={{ gap: "48px" }}>
            <section ref={registerSectionRef(0)} tabIndex={-1} aria-label="Investment View">
              <InvestmentViewSection
                view={data?.investmentView ?? null}
                loading={loading}
                editing={editingView}
                onStartEdit={handleEdit}
                onCancelEdit={handleCancel}
                onSaveEdit={handleSave}
              />
              <ProgressIndicator running={isRunning("evidence")} />
            </section>
            <section ref={registerSectionRef(1)} tabIndex={-1} aria-label="Investment Score">
              <InvestmentScoreSection
                score={data?.score ?? null}
                loading={loading}
              />
              <ProgressIndicator running={isRunning("confidence")} />
            </section>
            {canViewSection(role, "evidence") && (
              <section ref={registerSectionRef(2)} tabIndex={-1} aria-label="Supporting Evidence">
                <SupportingEvidenceSection
                  evidence={data?.evidence ?? []}
                  loading={loading}
                />
                <ProgressIndicator running={isRunning("evidence")} />
              </section>
            )}
            {canViewSection(role, "diligence") && (
              <section ref={registerSectionRef(3)} tabIndex={-1} aria-label="Outstanding Diligence">
                <OutstandingDiligenceSection
                  diligence={data?.diligence ?? []}
                  loading={loading}
                />
              </section>
            )}
            <section ref={registerSectionRef(4)} tabIndex={-1} aria-label="Decision Readiness">
              <DecisionReadinessSection
                readiness={data?.readiness ?? null}
                loading={loading}
              />
            </section>
            <section ref={registerSectionRef(5)} tabIndex={-1} aria-label="Recent Changes">
              <RecentChangesSection
                activity={data?.activity ?? []}
                loading={loading}
              />
            </section>
            <section ref={registerSectionRef(6)} tabIndex={-1} aria-label="Recommended Actions">
              <RecommendedActionsSection
                nextAction={data?.nextAction ?? null}
                loading={loading}
              />
            </section>
          </div>
        )}
      </PageShell>

      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
