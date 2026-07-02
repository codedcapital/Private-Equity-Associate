"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z", href: "/dashboard" },
  { id: "pipeline", label: "Pipeline", icon: "M4 4h5v16H4zM13 4h5v16h-5z", href: "/pipeline" },
  { id: "deals", label: "Deals", icon: "M3 7h18v13H3zM8 7V4h8v3", href: "/dashboard" },
  { id: "opportunity-discovery", label: "Opportunity Discovery", icon: "M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-4.3-4.3", href: "/opportunity-discovery" },
  { id: "research", label: "Research", icon: "M6 2h9l3 3v17H6zM14 2v4h4M9 12h6M9 16h6", href: "/research" },
  { id: "settings", label: "Settings", icon: "M4 7h16M4 12h16M4 17h16M9 7v0M15 12v0M7 17v0", href: "/settings" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[208px] flex-none bg-[#0A0A0F] border-r border-[#1E1E2E] flex flex-col sticky top-0 h-screen">
      {/* Logo */}
      <div className="h-[52px] flex-none flex items-center gap-[9px] px-4 border-b border-[#1E1E2E]">
        <div className="w-6 h-6 flex-none bg-[#C8A96E] flex items-center justify-center text-[#0A0A0F] font-mono font-bold text-[13px]">
          PE
        </div>
        <div className="flex flex-col leading-[1.1]">
          <span className="font-mono text-xs font-semibold tracking-[0.04em]">ASSOCIATE</span>
          <span className="text-[9px] text-[#6B7280] tracking-[0.18em] font-mono">v2.4 · INTERNAL</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col py-2 flex-1">
        {navItems.map((n) => {
          const isActive = pathname === n.href || (n.id === "deals" && pathname.startsWith("/deal")) || (n.id === "dashboard" && pathname === "/dashboard");
          return (
            <Link
              key={n.id}
              href={n.href}
              className={cn(
                "relative flex items-center gap-[11px] px-4 py-[9px] text-[13px] font-medium cursor-pointer transition-colors",
                isActive
                  ? "text-[#E8E8F0] bg-[#111118]"
                  : "text-[#9aa0ad] hover:text-[#E8E8F0] hover:bg-[#111118]"
              )}
            >
              <div
                className={cn(
                  "absolute left-0 top-0 bottom-0 w-[2px]",
                  isActive ? "bg-[#C8A96E]" : "bg-transparent"
                )}
              />
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="flex-none"
              >
                <path d={n.icon} />
              </svg>
              <span>{n.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-[#1E1E2E] px-4 py-3 flex items-center gap-[9px]">
        <div className="w-[26px] h-[26px] flex-none bg-[#1E1E2E] flex items-center justify-center font-mono text-[11px] text-[#C8A96E]">
          JR
        </div>
        <div className="leading-[1.2]">
          <div className="text-xs font-medium">J. Reyes</div>
          <div className="text-[10px] text-[#6B7280] font-mono">Senior Associate</div>
        </div>
      </div>
    </aside>
  );
}
