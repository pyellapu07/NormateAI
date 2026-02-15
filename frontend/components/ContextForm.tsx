"use client";

import { ClipboardList, Calendar } from "lucide-react";
import type { AnalysisContext } from "@/lib/utils";

interface ContextFormProps {
  context: AnalysisContext;
  onChange: (context: AnalysisContext) => void;
}

export default function ContextForm({ context, onChange }: ContextFormProps) {
  const update = (field: keyof AnalysisContext, value: string) => {
    onChange({ ...context, [field]: value });
  };

  return (
    <div className="space-y-5">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <ClipboardList className="h-5 w-5 text-brand-amber" />
        <h3 className="text-sm font-semibold text-ink">Research Context</h3>
      </div>

      {/* Research Question */}
      <div className="space-y-1.5">
        <label
          htmlFor="research-question"
          className="text-sm font-medium text-ink"
        >
          Research Question{" "}
          <span className="text-red-400">*</span>
        </label>
        <textarea
          id="research-question"
          value={context.researchQuestion}
          onChange={(e) => update("researchQuestion", e.target.value)}
          placeholder='e.g. "Why did mobile engagement drop 34% after our Q3 redesign?"'
          rows={3}
          className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink placeholder:text-ink-faint transition-colors focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/20"
        />
        <p className="text-xs text-ink-faint">
          What are you trying to learn from this data?
        </p>
      </div>

      {/* Product Description */}
      <div className="space-y-1.5">
        <label
          htmlFor="product-desc"
          className="text-sm font-medium text-ink"
        >
          Product / Feature Description{" "}
          <span className="text-red-400">*</span>
        </label>
        <textarea
          id="product-desc"
          value={context.productDescription}
          onChange={(e) => update("productDescription", e.target.value)}
          placeholder='e.g. "Agricultural bulletin web platform for East African crop forecasting — serves government agencies and NGOs"'
          rows={2}
          className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink placeholder:text-ink-faint transition-colors focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/20"
        />
      </div>

      {/* Time Period (optional) */}
      <div className="space-y-1.5">
        <label
          htmlFor="time-period"
          className="flex items-center gap-1.5 text-sm font-medium text-ink"
        >
          <Calendar className="h-3.5 w-3.5 text-ink-muted" />
          Time Period
          <span className="text-xs font-normal text-ink-faint">(optional)</span>
        </label>
        <input
          id="time-period"
          type="text"
          value={context.timePeriod || ""}
          onChange={(e) => update("timePeriod", e.target.value)}
          placeholder="e.g. Jan 2025 – Mar 2025"
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint transition-colors focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/20"
        />
      </div>
    </div>
  );
}
