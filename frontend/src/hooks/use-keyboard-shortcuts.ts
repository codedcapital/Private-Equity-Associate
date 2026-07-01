"use client";

import { useEffect, useCallback } from "react";

interface KeyboardShortcutsMap {
  onEdit?: () => void;
  onSave?: () => void;
  onCancel?: () => void;
  onToggleDataView?: () => void;
  onHelp?: () => void;
  onEscape?: () => void;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcutsMap) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ignore when typing in inputs/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        // Allow Escape and Cmd+S even in edit mode
        if (e.key !== "Escape" && !(e.metaKey && e.key === "s")) {
          return;
        }
      }

      const key = e.key.toLowerCase();

      switch (key) {
        case "e":
          if (!e.metaKey && !e.ctrlKey) {
            e.preventDefault();
            shortcuts.onEdit?.();
          }
          break;
        case "s":
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            shortcuts.onSave?.();
          }
          break;
        case "escape":
          e.preventDefault();
          shortcuts.onCancel?.() ?? shortcuts.onEscape?.();
          break;
        case "d":
          if (!e.metaKey && !e.ctrlKey) {
            e.preventDefault();
            shortcuts.onToggleDataView?.();
          }
          break;
        case "?":
          if (!e.metaKey && !e.ctrlKey) {
            e.preventDefault();
            shortcuts.onHelp?.();
          }
          break;
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}
