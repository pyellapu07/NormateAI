"use client";

import { Users, Briefcase, Palette } from "lucide-react";
import { cn } from "@/lib/utils";

export type Perspective = "pm" | "cfo" | "designer";

interface PerspectiveToggleProps {
  current: Perspective;
  onChange: (p: Perspective) => void;
}

const PERSPECTIVES = [
  {
    id: "pm" as Perspective,
    label: "Product Manager",
    icon: Users,
    description: "A/B tests, friction points, full report",
  },
  {
    id: "cfo" as Perspective,
    label: "CFO / Finance",
    icon: Briefcase,
    description: "Revenue impact, cost of inaction, ROI",
  },
  {
    id: "designer" as Perspective,
    label: "UX Designer",
    icon: Palette,
    description: "User quotes, empathy, accessibility",
  },
] as const;

export default function PerspectiveToggle({
  current,
  onChange,
}: PerspectiveToggleProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-ink-faint">
        Stakeholder View
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        {PERSPECTIVES.map(({ id, label, icon: Icon, description }) => (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={cn(
              "flex items-center gap-3 rounded-xl border p-3 text-left transition-all",
              current === id
                ? "border-brand-blue bg-brand-blue/5 shadow-sm"
                : "border-slate-100 hover:border-brand-blue/40 hover:bg-slate-50"
            )}
          >
            <div
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                current === id ? "bg-brand-blue/10" : "bg-slate-100"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4",
                  current === id ? "text-brand-blue" : "text-ink-muted"
                )}
              />
            </div>
            <div className="min-w-0">
              <span
                className={cn(
                  "block text-sm font-semibold leading-tight",
                  current === id ? "text-brand-blue" : "text-ink"
                )}
              >
                {label}
              </span>
              <span className="block text-[11px] leading-tight text-ink-faint mt-0.5">
                {description}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
