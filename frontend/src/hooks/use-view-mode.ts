"use client";

import { useState, useCallback, useEffect } from "react";
import type { ViewMode } from "@/types/overview";

export interface UseViewModeResult {
  viewMode: ViewMode;
  toggleViewMode: () => void;
  setViewMode: (mode: ViewMode) => void;
}

export function useViewMode(initial: ViewMode = "document"): UseViewModeResult {
  const [viewMode, setViewModeState] = useState<ViewMode>(initial);

  // Persist to localStorage
  useEffect(() => {
    const stored = localStorage.getItem("pe_view_mode") as ViewMode | null;
    if (stored && (stored === "document" || stored === "data")) {
      setViewModeState(stored);
    }
  }, []);

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeState(mode);
    localStorage.setItem("pe_view_mode", mode);
  }, []);

  const toggleViewMode = useCallback(() => {
    const next = viewMode === "document" ? "data" : "document";
    setViewMode(next);
  }, [viewMode, setViewMode]);

  return { viewMode, toggleViewMode, setViewMode };
}
