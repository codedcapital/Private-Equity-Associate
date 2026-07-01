"use client";

import { useState, useCallback, useEffect } from "react";

export type ThemeMode = "default" | "high-contrast";

export interface UseThemeModeResult {
  theme: ThemeMode;
  isHighContrast: boolean;
  toggleTheme: () => void;
}

export function useThemeMode(): UseThemeModeResult {
  const [theme, setTheme] = useState<ThemeMode>("default");

  useEffect(() => {
    const stored = localStorage.getItem("pe_theme") as ThemeMode | null;
    if (stored && (stored === "default" || stored === "high-contrast")) {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "high-contrast") {
      document.documentElement.classList.add("high-contrast");
    } else {
      document.documentElement.classList.remove("high-contrast");
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const next = theme === "default" ? "high-contrast" : "default";
    setTheme(next);
    localStorage.setItem("pe_theme", next);
  }, [theme]);

  return { theme, isHighContrast: theme === "high-contrast", toggleTheme };
}
