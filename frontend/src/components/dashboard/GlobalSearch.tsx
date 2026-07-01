"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface SearchResult {
  type: string;
  id: number | string;
  title: string;
  subtitle?: string | null;
  url: string;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
  onResultSelect: (url: string) => void;
  onSearch: (query: string) => Promise<{ results: SearchResult[] }>;
}

function typeColor(type: string): string {
  switch (type) {
    case "company":
      return "#2DD4BF";
    case "deal":
      return "#C8A96E";
    case "memo":
      return "#10B981";
    case "research":
      return "#6B7280";
    default:
      return "#6B7280";
  }
}

export default function GlobalSearch({ isOpen, onClose, onResultSelect, onSearch }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setResults([]);
      setSelectedIndex(-1);
      setLoading(false);
    }
  }, [isOpen]);

  // Escape key handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Arrow key navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen || results.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1 < results.length ? prev + 1 : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : results.length - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < results.length) {
          handleSelect(results[selectedIndex]);
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, results, selectedIndex]);

  const handleSelect = useCallback(
    (result: SearchResult) => {
      onResultSelect(result.url);
      onClose();
    },
    [onResultSelect, onClose]
  );

  const handleQueryChange = (value: string) => {
    setQuery(value);
    setSelectedIndex(-1);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (value.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const response = await onSearch(value);
        setResults(response.results ?? []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  };

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center pt-[15vh]">
      <div
        ref={containerRef}
        className="w-[600px] max-w-[90vw] bg-[#111118] border border-[#1E1E2E] shadow-2xl flex flex-col"
        style={{ maxHeight: "60vh" }}
      >
        {/* Search input */}
        <div className="bg-[#0A0A0F] border-b border-[#1E1E2E] px-4 py-3 flex items-center gap-2 flex-shrink-0">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#6B7280"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="Search companies, deals, research..."
            className="flex-1 bg-transparent outline-none text-[#E8E8F0] text-[14px] placeholder:text-[#6B7280]"
          />
          <button
            onClick={onClose}
            className="text-[#6B7280] hover:text-[#E8E8F0] text-[18px] leading-none px-1"
            aria-label="Close search"
          >
            ×
          </button>
        </div>

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="px-4 py-6 text-center text-[13px] text-[#6B7280]">Searching...</div>
          ) : query.length < 2 ? (
            <div className="px-4 py-6 text-center text-[13px] text-[#6B7280]">
              Type at least 2 characters...
            </div>
          ) : results.length === 0 ? (
            <div className="px-4 py-6 text-center text-[13px] text-[#6B7280]">No results found</div>
          ) : (
            <div className="flex flex-col">
              {results.map((result, index) => (
                <div
                  key={`${result.type}-${result.id}`}
                  onClick={() => handleSelect(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`px-4 py-2 cursor-pointer flex items-center gap-3 ${
                    index === selectedIndex ? "bg-[#0A0A0F]" : "hover:bg-[#0A0A0F]"
                  }`}
                >
                  <span className="text-[10px] leading-none flex-shrink-0" style={{ color: typeColor(result.type) }}>
                    ●
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] text-[#E8E8F0] truncate">{result.title}</div>
                    {result.subtitle && (
                      <div className="text-[11px] text-[#6B7280] truncate">{result.subtitle}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
