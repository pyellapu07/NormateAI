"use client";

import Link from "next/link";
import { History } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="h-10 w-10 flex-shrink-0 overflow-hidden">
            <img
              src="/logoNormate.png"
              alt="Normate AI Logo"
              className="h-full w-full object-cover"
            />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-display text-lg font-bold tracking-tight text-ink">
              Normate
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-brand-blue">
              AI
            </span>
          </div>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <Link
            href="/history"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:bg-slate-100 hover:text-ink"
          >
            <History className="h-4 w-4" />
            <span className="hidden sm:inline">History</span>
          </Link>

          <span className="hidden sm:inline-block rounded-full bg-brand-blue/10 px-3 py-1 text-xs font-semibold text-brand-blue">
            Beta
          </span>
        </div>
      </div>
    </nav>
  );
}
