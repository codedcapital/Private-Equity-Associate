"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  useId,
} from "react";

interface FlyoutContextValue {
  openFlyoutId: string | null;
  setOpenFlyoutId: (id: string | null) => void;
}

const FlyoutContext = createContext<FlyoutContextValue>({
  openFlyoutId: null,
  setOpenFlyoutId: () => {},
});

export function FlyoutProvider({ children }: { children: React.ReactNode }) {
  const [openFlyoutId, setOpenFlyoutId] = useState<string | null>(null);
  return (
    <FlyoutContext.Provider value={{ openFlyoutId, setOpenFlyoutId }}>
      {children}
    </FlyoutContext.Provider>
  );
}

export function useFlyout() {
  return useContext(FlyoutContext);
}

/* ─── Sparkline (SVG, no deps) ─── */
function Sparkline({
  data,
}: {
  data: { timestamp: string; value: number }[];
}) {
  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-[60px] border border-dashed border-[#1E1E2E] text-[10px] text-[#4b5160] font-mono">
        History builds over time
      </div>
    );
  }
  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const width = 280;
  const height = 60;
  const padding = 4;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((d.value - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="block"
    >
      <polyline
        fill="none"
        stroke="#C8A96E"
        strokeWidth="1.5"
        points={points.join(" ")}
      />
      {data.map((d, i) => {
        const x = padding + (i / (data.length - 1)) * (width - padding * 2);
        const y = height - padding - ((d.value - min) / range) * (height - padding * 2);
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="2"
            fill="#C8A96E"
            stroke="none"
          />
        );
      })}
    </svg>
  );
}

/* ─── Info Flyout Panel ─── */
export interface InfoFlyoutProps {
  label: string;
  formula: string;
  source: string;
  lastUpdated: string;
  history?: { timestamp: string; value: number }[];
  isOpen: boolean;
  onClose: () => void;
}

export function InfoFlyout({
  label,
  formula,
  source,
  lastUpdated,
  history,
  isOpen,
  onClose,
}: InfoFlyoutProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handleClick);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-[40]" />
      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed top-0 right-0 bottom-0 z-[50] bg-[#111118] border-l border-[#1E1E2E] shadow-2xl flex flex-col"
        style={{
          width: "clamp(320px, 380px, 100vw)",
          animation: "flyoutSlide 0.25s ease-out forwards",
        }}
      >
        <style>{`
          @keyframes flyoutSlide {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
          }
        `}</style>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1E1E2E]">
          <span className="font-mono text-[11px] tracking-[0.1em] uppercase text-[#6B7280]">
            Metric Details
          </span>
          <button
            onClick={onClose}
            className="text-[#6B7280] hover:text-[#E8E8F0] transition-colors cursor-pointer"
            aria-label="Close panel"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
          <div>
            <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280] mb-1">
              Label
            </div>
            <div className="text-[14px] font-semibold text-[#E8E8F0]">{label}</div>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280] mb-1">
              Formula / Definition
            </div>
            <div className="text-[13px] text-[#c4c6d0] leading-[1.55]">{formula}</div>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280] mb-1">
              Data Source
            </div>
            <div className="text-[13px] text-[#c4c6d0] leading-[1.55]">{source}</div>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280] mb-1">
              Last Computed
            </div>
            <div className="text-[13px] font-mono text-[#9aa0ad]">{lastUpdated}</div>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.08em] uppercase text-[#6B7280] mb-2">
              History
            </div>
            <Sparkline data={history || []} />
          </div>
        </div>
      </div>
    </>
  );
}

/* ─── Metric With Info ─── */
export interface MetricWithInfoProps {
  value: React.ReactNode;
  label: string;
  formula: string;
  source: string;
  lastUpdated: string | null;
  history?: { timestamp: string; value: number }[];
  className?: string;
  valueClassName?: string;
  valueStyle?: React.CSSProperties;
}

export function MetricWithInfo({
  value,
  label,
  formula,
  source,
  lastUpdated,
  history,
  className = "",
  valueClassName = "",
  valueStyle,
}: MetricWithInfoProps) {
  const { openFlyoutId, setOpenFlyoutId } = useFlyout();
  const id = useId();
  const isOpen = openFlyoutId === id;

  const handleOpen = useCallback(() => {
    setOpenFlyoutId(id);
  }, [id, setOpenFlyoutId]);

  const handleClose = useCallback(() => {
    setOpenFlyoutId(null);
  }, [setOpenFlyoutId]);

  return (
    <span className={`inline-flex items-center gap-[6px] ${className}`}>
      <span className={valueClassName} style={valueStyle}>
        {value}
      </span>
      <button
        onClick={handleOpen}
        className="inline-flex items-center justify-center text-[#4b5160] hover:text-[#9aa0ad] transition-colors cursor-pointer flex-shrink-0"
        aria-label={`Details for ${label}`}
        title={`Details for ${label}`}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4M12 8h.01" />
        </svg>
      </button>
      <InfoFlyout
        label={label}
        formula={formula}
        source={source}
        lastUpdated={lastUpdated ?? "—"}
        history={history}
        isOpen={isOpen}
        onClose={handleClose}
      />
    </span>
  );
}
