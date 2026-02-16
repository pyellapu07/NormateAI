"use client";

import { DollarSign, TrendingDown, AlertTriangle, ArrowUpRight } from "lucide-react";
import type { FinancialImpact } from "@/lib/utils";

interface FinancialImpactCardProps {
  impact: FinancialImpact;
}

export default function FinancialImpactCard({ impact }: FinancialImpactCardProps) {
  return (
    <div className="rounded-2xl border border-red-200 bg-gradient-to-br from-white via-white to-red-50/40 p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100">
          <DollarSign className="h-6 w-6 text-red-600" />
        </div>
        <div>
          <h3 className="font-display text-lg font-bold text-ink">
            Financial Impact
          </h3>
          <p className="text-xs text-ink-faint">
            Revenue implications based on your ARPU
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-red-100 bg-white p-4">
          <div className="mb-2 flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-red-500" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-red-600">
              Lost Revenue
            </span>
          </div>
          <p className="text-lg font-bold text-ink leading-snug">{impact.lostRevenue}</p>
        </div>

        <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
              Cost of Inaction
            </span>
          </div>
          <p className="text-lg font-bold text-ink leading-snug">{impact.costOfInaction}</p>
        </div>

        <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <ArrowUpRight className="h-4 w-4 text-emerald-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
              Recovery Potential
            </span>
          </div>
          <p className="text-lg font-bold text-ink leading-snug">{impact.recoveryPotential}</p>
        </div>
      </div>
    </div>
  );
}
