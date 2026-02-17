"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Search } from "lucide-react";
import { searchTickers } from "@/lib/api";
import type { SearchResult } from "@/types/analysis";

interface TickerSearchInputProps {
  onSelect: (ticker: string, name: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export default function TickerSearchInput({
  onSelect,
  placeholder = "Search ticker... (Ctrl+K)",
  autoFocus = false,
}: TickerSearchInputProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 1) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await searchTickers(q);
      setResults(data.results);
      setIsOpen(data.results.length > 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (val: string) => {
    setQuery(val);
    setActiveIdx(-1);
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => doSearch(val), 300);
  };

  const handleSelect = (result: SearchResult) => {
    setQuery("");
    setIsOpen(false);
    setResults([]);
    onSelect(result.symbol, result.name);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx((prev) => Math.min(prev + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx((prev) => Math.max(prev - 1, 0)); }
    else if (e.key === "Enter" && activeIdx >= 0) { e.preventDefault(); handleSelect(results[activeIdx]); }
    else if (e.key === "Escape") { setIsOpen(false); }
  };

  return (
    <div className="relative w-full">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary" size={16} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="w-full pl-11 pr-4 py-3.5 bg-[rgba(10,15,26,0.6)] border border-border rounded-xl text-text-primary placeholder:text-text-tertiary font-mono text-sm focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none transition-all duration-200"
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        />
        {loading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <ul role="listbox" className="absolute z-50 w-full mt-2 bg-[rgba(10,15,26,0.95)] backdrop-blur-[16px] rounded-xl shadow-lg max-h-60 overflow-y-auto animate-fade-in border border-border">
          {results.map((r, i) => (
            <li
              key={r.symbol}
              role="option"
              aria-selected={i === activeIdx}
              className={`px-4 py-3 cursor-pointer flex items-center gap-3 transition-colors duration-150 first:rounded-t-xl last:rounded-b-xl ${
                i === activeIdx ? "bg-primary/10" : "hover:bg-primary/10"
              }`}
              onMouseDown={() => handleSelect(r)}
            >
              <span className="font-mono font-bold text-text-primary">{r.symbol}</span>
              <span className="text-sm text-text-secondary truncate">{r.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
