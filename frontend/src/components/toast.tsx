"use client";

import { createContext, useContext, useState, useCallback, useRef } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (type: ToastType, title: string, message?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be inside ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const addToast = useCallback((type: ToastType, title: string, message?: string) => {
    const id = String(++idRef.current);
    const toast: Toast = { id, type, title, message };
    setToasts((prev) => [...prev, toast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const iconColor = {
    success: "#10B981",
    error: "#EF4444",
    warning: "#F59E0B",
    info: "#2DD4BF",
  };

  const iconBg = {
    success: "rgba(16,185,129,0.12)",
    error: "rgba(239,68,68,0.12)",
    warning: "rgba(245,158,11,0.12)",
    info: "rgba(45,212,191,0.12)",
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-peFade flex items-start gap-3 bg-[#111118] border border-[#1E1E2E] px-4 py-3 min-w-[280px] max-w-[380px] shadow-lg cursor-pointer hover:border-[#2c2c42] transition-colors"
            onClick={() => removeToast(t.id)}
          >
            <div
              className="w-6 h-6 flex-none flex items-center justify-center mt-[1px]"
              style={{ background: iconBg[t.type] }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={iconColor[t.type]} strokeWidth="2.5">
                {t.type === "success" && <path d="M5 13l4 4L19 7" />}
                {t.type === "error" && <path d="M6 18L18 6M6 6l12 12" />}
                {t.type === "warning" && <path d="M12 9v4m0 4h.01M12 2L2 22h20L12 2z" />}
                {t.type === "info" && <path d="M12 16v-4M12 8h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />}
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-medium text-[#E8E8F0]">{t.title}</div>
              {t.message && (
                <div className="mt-[2px] text-[11px] text-[#9aa0ad] leading-[1.5]">{t.message}</div>
              )}
            </div>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" className="flex-none mt-[1px]">
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
