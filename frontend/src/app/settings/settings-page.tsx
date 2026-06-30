"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/components/toast";
import { getIngestStatus, getPipelineStatus, bulkIngest, type IngestStatus, type PipelineStatus, type BulkIngestResult } from "@/lib/api";

interface SectionItem {
  label: string;
  value: string | boolean;
  type: "text" | "number" | "toggle" | "readonly";
  suffix?: string;
}

export default function SettingsPage() {
  const { addToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [ingest, setIngest] = useState<IngestStatus | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);

  /* Bulk ingestion state */
  const [tickersInput, setTickersInput] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<BulkIngestResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getIngestStatus(), getPipelineStatus()])
      .then(([ingestData, pipelineData]) => {
        if (cancelled) return;
        setIngest(ingestData);
        setPipeline(pipelineData);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Settings fetch failed:", err);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      addToast("success", "Settings saved", "Your configuration has been updated.");
      setTimeout(() => setSaved(false), 3000);
    }, 800);
  };

  const handleBulkIngest = async () => {
    const raw = tickersInput
      .split(/[,\n]/)
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0);

    if (raw.length === 0) {
      addToast("warning", "No tickers", "Paste at least one ticker symbol.");
      return;
    }

    setIngesting(true);
    setIngestResult(null);
    try {
      const res = await bulkIngest(raw, ["financials"]);
      setIngestResult(res);
      addToast(
        "success",
        "Ingestion complete",
        `${res.created} created, ${res.existing} existing, ${res.failed} failed out of ${res.total} tickers.`
      );
      // Refresh ingest status
      const status = await getIngestStatus();
      setIngest(status);
    } catch (err) {
      console.error("Bulk ingest failed:", err);
      addToast("error", "Ingestion failed", err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIngesting(false);
    }
  };

  const platformItems: SectionItem[] = [
    { label: "API Base URL", value: "http://localhost:8000", type: "text" },
    { label: "Polling Interval", value: "30", type: "number", suffix: "seconds" },
    { label: "Auto-refresh Dashboard", value: true, type: "toggle" },
    { label: "Dark Mode", value: true, type: "toggle" },
  ];

  const agentItems: SectionItem[] = [
    { label: "Max Tokens per Run", value: "4000", type: "number" },
    { label: "Temperature", value: "0.3", type: "number" },
    { label: "Enable Competitive Agent", value: true, type: "toggle" },
    { label: "Enable Research Agent", value: true, type: "toggle" },
  ];

  const notificationItems: SectionItem[] = [
    { label: "Agent Completed", value: true, type: "toggle" },
    { label: "Agent Failed", value: true, type: "toggle" },
    { label: "Memo Ready", value: true, type: "toggle" },
    { label: "Pipeline Status Updates", value: false, type: "toggle" },
  ];

  const ingestionItems: SectionItem[] = [
    {
      label: "Last Run",
      value: ingest?.last_run
        ? new Date(ingest.last_run).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) + " at 03:00 UTC"
        : "Never",
      type: "readonly",
    },
    { label: "Companies", value: String(ingest?.companies ?? 0), type: "readonly" },
    { label: "Filings", value: String(ingest?.filings ?? 0), type: "readonly" },
    { label: "Chunks", value: String(ingest?.chunks ?? 0), type: "readonly" },
    { label: "Scheduled Ingestion", value: true, type: "toggle" },
  ];

  const renderSection = (title: string, items: SectionItem[]) => (
    <div className="mb-8">
      <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">
        {title}
      </h2>
      <div className="border border-[#1E1E2E]">
        {items.map((item, i) => (
          <div
            key={item.label}
            className="flex items-center justify-between px-4 py-[13px]"
            style={{ borderBottom: i < items.length - 1 ? "1px solid #1E1E2E" : "none" }}
          >
            <span className="text-[13px] text-[#E8E8F0]">{item.label}</span>
            {item.type === "toggle" && (
              <button
                className="relative w-9 h-5 cursor-pointer transition-colors"
                style={{ background: item.value ? "#C8A96E" : "#1E1E2E" }}
                onClick={() => {}}
              >
                <span
                  className="absolute top-[2px] w-4 h-4 bg-[#E8E8F0] transition-transform"
                  style={{ left: item.value ? "18px" : "2px" }}
                />
              </button>
            )}
            {item.type === "text" && (
              <input
                defaultValue={item.value as string}
                className="bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] text-xs px-3 py-[7px] w-[240px] outline-none focus:border-[#C8A96E] transition-colors"
              />
            )}
            {item.type === "number" && (
              <div className="flex items-center gap-2">
                <input
                  defaultValue={item.value as string}
                  className="bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] text-xs px-3 py-[7px] w-[80px] outline-none focus:border-[#C8A96E] transition-colors text-right"
                />
                {item.suffix && (
                  <span className="font-mono text-[10px] text-[#6B7280]">{item.suffix}</span>
                )}
              </div>
            )}
            {item.type === "readonly" && (
              <span className="font-mono text-[12.5px] text-[#6B7280]">{item.value as string}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <div className="h-[52px] flex items-center justify-between px-5 border-b border-[#1E1E2E] bg-[#0A0A0F] sticky top-0 z-[5]">
        <h1 className="m-0 text-[15px] font-semibold">Settings</h1>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="font-mono text-[11px] text-[#10B981]">Settings saved</span>
          )}
          <button
            onClick={handleSave}
            className="flex items-center gap-2 bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-[14px] py-2 text-xs font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors"
          >
            {saving ? (
              <>
                <span className="w-[12px] h-[12px] border-2 border-[#0A0A0F] border-t-transparent rounded-full animate-spin" />
                Saving…
              </>
            ) : (
              "Save Changes"
            )}
          </button>
        </div>
      </div>

      <div className="max-w-[720px] px-5 pt-6 pb-[60px]">
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-[#111118] border border-[#1E1E2E] p-4">
                <div className="h-3 bg-[#15151f] w-1/4 mb-3" />
                <div className="h-3 bg-[#15151f] w-3/4" />
              </div>
            ))}
          </div>
        )}

        {!loading && (
          <>
            {renderSection("Platform", platformItems)}
            {renderSection("Agents", agentItems)}
            {renderSection("Notifications", notificationItems)}
            {renderSection("Ingestion", ingestionItems)}

            {/* Bulk Ingestion */}
            <div className="mb-8">
              <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">
                Bulk Ingestion
              </h2>
              <div className="border border-[#1E1E2E] p-4">
                <p className="text-[12px] text-[#9aa0ad] mb-3">
                  Paste a comma-separated or newline-separated list of ticker symbols to add new companies to the universe.
                  The system will look up each ticker via Yahoo Finance, create the company record, and pull financial data.
                </p>
                <textarea
                  value={tickersInput}
                  onChange={(e) => setTickersInput(e.target.value)}
                  placeholder="e.g., CRM, ADBE, ZS, CRWD, DDOG, PLTR, GTLB, NET, SNOW, TWLO..."
                  className="w-full h-[100px] bg-[#111118] border border-[#1E1E2E] text-[#E8E8F0] text-xs px-3 py-2 outline-none focus:border-[#C8A96E] transition-colors resize-none font-mono"
                />
                <div className="flex items-center justify-between mt-3">
                  <span className="text-[11px] text-[#6B7280]">
                    {tickersInput
                      .split(/[,\n]/)
                      .filter((t) => t.trim().length > 0).length} tickers ready
                  </span>
                  <button
                    onClick={handleBulkIngest}
                    disabled={ingesting}
                    className="flex items-center gap-2 bg-[#C8A96E] border border-[#C8A96E] text-[#0A0A0F] px-[14px] py-2 text-xs font-semibold cursor-pointer hover:bg-[#d8bd86] transition-colors disabled:opacity-50"
                  >
                    {ingesting ? (
                      <>
                        <span className="w-[12px] h-[12px] border-2 border-[#0A0A0F] border-t-transparent rounded-full animate-spin" />
                        Ingesting…
                      </>
                    ) : (
                      "Ingest Tickers"
                    )}
                  </button>
                </div>

                {ingestResult && (
                  <div className="mt-4 border-t border-[#1E1E2E] pt-4">
                    <div className="flex gap-6 mb-3">
                      <div>
                        <span className="font-mono text-[10px] text-[#6B7280]">Total</span>
                        <div className="font-mono text-[16px] font-semibold text-[#E8E8F0]">{ingestResult.total}</div>
                      </div>
                      <div>
                        <span className="font-mono text-[10px] text-[#6B7280]">Created</span>
                        <div className="font-mono text-[16px] font-semibold text-[#10B981]">{ingestResult.created}</div>
                      </div>
                      <div>
                        <span className="font-mono text-[10px] text-[#6B7280]">Existing</span>
                        <div className="font-mono text-[16px] font-semibold text-[#2DD4BF]">{ingestResult.existing}</div>
                      </div>
                      <div>
                        <span className="font-mono text-[10px] text-[#6B7280]">Failed</span>
                        <div className="font-mono text-[16px] font-semibold text-[#EF4444]">{ingestResult.failed}</div>
                      </div>
                    </div>
                    <div className="max-h-[200px] overflow-y-auto border border-[#1E1E2E]">
                      {Object.entries(ingestResult.results).map(([ticker, res]) => (
                        <div key={ticker} className="flex items-center justify-between px-3 py-2 text-xs border-b border-[#1E1E2E] last:border-b-0">
                          <span className="font-mono text-[#E8E8F0]">{ticker}</span>
                          <span className={
                            res.error ? "text-[#EF4444]" :
                            res.company === "created" ? "text-[#10B981]" : "text-[#2DD4BF]"
                          }>
                            {res.error ? `Failed: ${res.error}` :
                             res.company === "created" ? "Created + ingested" :
                             "Existing + refreshed"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {pipeline && (
              <div className="mb-8">
                <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">
                  Pipeline Today
                </h2>
                <div className="border border-[#1E1E2E] px-4 py-[13px]">
                  <div className="flex gap-6">
                    <div>
                      <span className="font-mono text-[10px] text-[#6B7280]">Active</span>
                      <div className="font-mono text-[18px] font-semibold text-[#2DD4BF]">{pipeline.active_runs}</div>
                    </div>
                    <div>
                      <span className="font-mono text-[10px] text-[#6B7280]">Completed</span>
                      <div className="font-mono text-[18px] font-semibold text-[#10B981]">{pipeline.completed_today}</div>
                    </div>
                    <div>
                      <span className="font-mono text-[10px] text-[#6B7280]">Failed</span>
                      <div className="font-mono text-[18px] font-semibold text-[#EF4444]">{pipeline.failed_today}</div>
                    </div>
                    <div>
                      <span className="font-mono text-[10px] text-[#6B7280]">Cost</span>
                      <div className="font-mono text-[18px] font-semibold text-[#C8A96E]">${pipeline.total_cost_today.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="mb-8">
              <h2 className="m-0 mb-3 font-mono text-[11px] tracking-[0.1em] uppercase text-[#EF4444]">
                Danger Zone
              </h2>
              <div className="border border-[#1E1E2E]">
                <div className="flex items-center justify-between px-4 py-[13px]">
                  <div>
                    <div className="text-[13px] text-[#E8E8F0]">Clear All Agent Logs</div>
                    <div className="text-[11px] text-[#6B7280] mt-[2px]">Removes all historical agent run data</div>
                  </div>
                  <button className="bg-transparent border border-[#EF4444] text-[#EF4444] px-3 py-[7px] text-[11px] font-semibold cursor-pointer hover:bg-[rgba(239,68,68,0.1)] transition-colors">
                    Clear Logs
                  </button>
                </div>
                <div className="flex items-center justify-between px-4 py-[13px] border-t border-[#1E1E2E]">
                  <div>
                    <div className="text-[13px] text-[#E8E8F0]">Reset Ingestion Pipeline</div>
                    <div className="text-[11px] text-[#6B7280] mt-[2px]">Re-run full ingestion from scratch</div>
                  </div>
                  <button className="bg-transparent border border-[#EF4444] text-[#EF4444] px-3 py-[7px] text-[11px] font-semibold cursor-pointer hover:bg-[rgba(239,68,68,0.1)] transition-colors">
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
