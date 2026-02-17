"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { MoreVertical } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ActionMenuItem {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  variant?: "default" | "danger";
  disabled?: boolean;
}

interface ActionMenuProps {
  items: ActionMenuItem[];
}

export default function ActionMenu({ items }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return;

    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((prev) => !prev);
        }}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-white/10 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
        aria-label="Actions"
        aria-expanded={open}
      >
        <MoreVertical size={16} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-40 min-w-[160px] bg-[rgba(10,15,26,0.95)] backdrop-blur-[16px] border border-border rounded-xl py-1.5 shadow-2xl animate-in">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                onClick={(e) => {
                  e.stopPropagation();
                  if (!item.disabled) {
                    setOpen(false);
                    item.onClick();
                  }
                }}
                disabled={item.disabled}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-left transition-colors duration-150",
                  "disabled:opacity-40 disabled:cursor-not-allowed",
                  item.variant === "danger"
                    ? "text-red-400 hover:bg-red-500/10"
                    : "text-text-secondary hover:text-text-primary hover:bg-white/5"
                )}
              >
                {Icon && <Icon size={14} />}
                {item.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
