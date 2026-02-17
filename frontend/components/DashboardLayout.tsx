"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutGrid, Layers, Briefcase, Bell, Search, Brain } from "lucide-react";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const NAV_SECTIONS = [
  {
    label: "OVERVIEW",
    items: [
      { href: "/", icon: LayoutGrid, title: "Dashboard" },
    ],
  },
  {
    label: "ANALYSIS",
    items: [
      { href: "/screens", icon: Layers, title: "Screens" },
      { href: "/research", icon: Search, title: "Research" },
      { href: "/personas", icon: Brain, title: "Personas" },
    ],
  },
  {
    label: "TOOLS",
    items: [
      { href: "/portfolio", icon: Briefcase, title: "Portfolio" },
      { href: "/alerts", icon: Bell, title: "Alerts" },
    ],
  },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-[260px] min-w-[260px] bg-sidebar backdrop-blur-[16px] border-r border-border hidden lg:flex flex-col sticky top-0 h-screen overflow-y-auto animate-slide-in-left">
        {/* Brand */}
        <div className="px-5 py-6 border-b border-border animate-fade-in-up">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
              <LayoutGrid size={18} className="text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-text-primary tracking-tight">Skeptical Analyst</h1>
              <p className="text-[10px] text-text-tertiary">Due Diligence Engine</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-6">
          {(() => {
            let globalIndex = 0;
            return NAV_SECTIONS.map((section) => (
              <div key={section.label}>
                <p className="px-3 mb-2 text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">
                  {section.label}
                </p>
                <div className="space-y-1">
                  {section.items.map((item) => {
                    const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                    const delay = globalIndex * 0.05 + 0.2;
                    globalIndex++;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 opacity-0 animate-fade-in-up",
                          isActive
                            ? "bg-primary/12 text-primary border-l-[3px] border-primary"
                            : "text-text-secondary hover:bg-primary/8 hover:text-text-primary"
                        )}
                        style={{ animationDelay: `${delay}s`, animationFillMode: 'forwards' }}
                      >
                        <item.icon size={18} />
                        <span>{item.title}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ));
          })()}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto relative z-10">
        <div className="max-w-6xl mx-auto p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
