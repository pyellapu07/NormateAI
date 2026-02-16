"use client";

import {
  TrendingUp,
  TrendingDown,
  Minus,
  Quote,
  ArrowRight,
  FlaskConical,
  Target,
  Zap,
  Lightbulb,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";
import { cn, impactBadgeColor } from "@/lib/utils";
import type {
  QuantEvidence,
  QualEvidence,
  RecommendedAction,
  ABTest,
  TrackedMetric,
} from "@/lib/utils";

// ── Problem Summary ─────────────────────────────────────────

export function ProblemSummaryCard({ summary }: { summary: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-gradient-to-br from-white via-white to-red-50/40 p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100">
          <Zap className="h-5 w-5 text-red-600" />
        </div>
        <div>
          <h2 className="font-display text-xl font-bold text-ink">
            Root Cause Analysis
          </h2>
          <p className="text-xs text-ink-faint">AI-synthesized problem summary</p>
        </div>
      </div>
      <p className="text-base leading-[1.8] text-ink/90">{summary}</p>
    </div>
  );
}

// ── Quant Evidence ──────────────────────────────────────────

export function QuantEvidenceCard({ items }: { items: QuantEvidence[] }) {
  const DirectionIcon = {
    up: TrendingUp,
    down: TrendingDown,
    flat: Minus,
  };

  return (
    <div className="rounded-2xl border border-blue-200 bg-gradient-to-br from-white to-blue-50/20 p-6 shadow-sm">
      <h3 className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brand-blue">
        <TrendingUp className="h-4 w-4" />
        Quantitative Evidence
      </h3>
      <div className="space-y-2.5">
        {items.map((item, i) => {
          const Icon = DirectionIcon[item.direction || "flat"];
          const isNegativeDirection =
            item.direction === "down" ||
            (item.direction === "up" &&
              /bounce|error|churn|latency/i.test(item.metric));
          const isPositiveDirection =
            item.direction === "up" &&
            !/bounce|error|churn|latency/i.test(item.metric);

          return (
            <div
              key={i}
              className={cn(
                "flex items-center gap-3 rounded-xl px-4 py-3 transition-colors",
                isNegativeDirection
                  ? "bg-red-50/80 border border-red-200"
                  : isPositiveDirection
                    ? "bg-emerald-50/80 border border-emerald-200"
                    : "bg-slate-50 border border-slate-100"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  isNegativeDirection
                    ? "text-red-500"
                    : isPositiveDirection
                      ? "text-emerald-500"
                      : "text-ink-faint"
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-ink">{item.metric}</p>
                <p className="text-xs text-ink-muted">{item.value}</p>
              </div>
              {item.change && (
                <span
                  className={cn(
                    "shrink-0 rounded-md px-2.5 py-1 text-xs font-bold",
                    isNegativeDirection
                      ? "bg-red-100 text-red-700"
                      : isPositiveDirection
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-ink-muted"
                  )}
                >
                  {item.change}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Qual Evidence ───────────────────────────────────────────

export function QualEvidenceCard({ items }: { items: QualEvidence[] }) {
  return (
    <div className="rounded-2xl border border-purple-200 bg-gradient-to-br from-white to-purple-50/20 p-6 shadow-sm">
      <h3 className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brand-purple">
        <Quote className="h-4 w-4" />
        Qualitative Evidence
      </h3>
      <div className="space-y-5">
        {items.map((item, i) => (
          <div key={i}>
            <div className="mb-2.5 flex items-center justify-between">
              <span className="text-sm font-bold text-ink">{item.theme}</span>
              <span
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs font-bold",
                  item.sentiment >= 0.3
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : item.sentiment <= -0.3
                      ? "border-red-200 bg-red-50 text-red-700"
                      : "border-slate-200 bg-slate-50 text-ink-muted"
                )}
              >
                {item.sentimentLabel} ({item.sentiment.toFixed(2)})
              </span>
            </div>
            {item.quotes.map((q, qi) => (
              <blockquote
                key={qi}
                className="mb-2 flex gap-2.5 rounded-lg border border-purple-100 bg-purple-50/40 px-4 py-3"
              >
                <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-purple/50" />
                <p className="text-[13px] italic leading-relaxed text-ink/75">{q}</p>
              </blockquote>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Actions (Expanded) ──────────────────────────────────────

function ActionItem({
  action,
  rank,
}: {
  action: RecommendedAction;
  rank: number;
}) {
  const [expanded, setExpanded] = useState(rank <= 2);

  return (
    <div
      className={cn(
        "rounded-xl border overflow-hidden transition-all",
        action.impact === "High"
          ? "border-red-200 bg-gradient-to-br from-white to-red-50/30"
          : action.impact === "Medium"
            ? "border-amber-200 bg-gradient-to-br from-white to-amber-50/30"
            : "border-slate-200 bg-white"
      )}
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-start gap-3 p-4 text-left"
      >
        <span
          className={cn(
            "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white break-word",
            action.impact === "High"
              ? "bg-red-500"
              : action.impact === "Medium"
                ? "bg-amber-500"
                : "bg-brand-blue"
          )}
        >
          {rank}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-bold text-ink leading-snug">
            {action.title}
          </h4>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <span
              className={cn(
                "rounded-md border px-2.5 py-0.5 text-[11px] font-bold",
                impactBadgeColor(action.impact)
              )}
            >
              {action.impact} Impact
            </span>
            <span className="rounded-md border border-slate-200 bg-white px-2.5 py-0.5 text-[11px] font-bold text-ink-muted">
              {action.difficulty} Effort
            </span>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="mt-1 h-4 w-4 shrink-0 text-ink-faint" />
        ) : (
          <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-ink-faint" />
        )}
      </button>

      {/* Body — collapsible */}
      {expanded && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3 space-y-3">
          {/* Description */}
          <p className="text-sm leading-relaxed text-ink/85">
            {action.description}
          </p>

          {/* Evidence */}
          <div className="rounded-lg bg-slate-50 border border-slate-100 px-3.5 py-2.5">
            <p className="text-xs font-bold text-ink-faint uppercase tracking-wider mb-1 break-word">
              Evidence
            </p>
            <p className="text-xs leading-relaxed text-ink-muted break-word">
              {action.evidence}
            </p>
          </div>

          {/* Estimated Effect */}
          <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5">
            <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div>
              <p className="text-xs font-bold text-amber-800">
                Estimated Effect
              </p>
              <p className="text-xs leading-relaxed text-amber-700">
                {action.estimatedEffect}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ActionsCard({ actions }: { actions: RecommendedAction[] }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-white to-amber-50/20 p-6 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brand-amber-dark">
          <Lightbulb className="h-4 w-4" />
          Recommended Actions
        </h3>
        <span className="text-xs font-semibold text-ink-faint">
          {actions.length} actions &middot; ranked by impact
        </span>
      </div>
      <div className="space-y-3">
        {actions.map((action, i) => (
          <ActionItem key={i} action={action} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}

// ── A/B Test ────────────────────────────────────────────────

export function ABTestCard({ tests }: { tests: ABTest[] }) {
  return (
    <div className="rounded-2xl border border-purple-200 bg-gradient-to-br from-white to-purple-50/30 p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <FlaskConical className="h-4 w-4 text-brand-purple" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-brand-purple">
          Suggested A/B Tests
        </h3>
      </div>
      <div className="space-y-4">
        {tests.map((test, i) => (
          <div
            key={i}
            className="rounded-xl border border-purple-100 bg-white p-4"
          >
            <p className="mb-3 text-sm font-bold text-ink">{test.name}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <span className="font-bold text-ink-faint block mb-0.5">Control</span>
                <p className="text-ink-muted leading-relaxed">{test.control}</p>
              </div>
              <div className="rounded-lg bg-purple-50 px-3 py-2">
                <span className="font-bold text-purple-600 block mb-0.5">Treatment</span>
                <p className="text-ink-muted leading-relaxed">{test.treatment}</p>
              </div>
              <div>
                <span className="font-bold text-ink-faint">Measure: </span>
                <span className="text-ink-muted">{test.metric}</span>
              </div>
              <div>
                <span className="font-bold text-ink-faint">Duration: </span>
                <span className="text-ink-muted">{test.duration}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Metrics to Track ────────────────────────────────────────

export function MetricsCard({ metrics }: { metrics: TrackedMetric[] }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-white to-amber-50/20 p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-4 w-4 text-brand-amber" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-brand-amber-dark">
          Metrics to Track
        </h3>
      </div>
      <div className="space-y-2">
        {metrics.map((m, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg bg-amber-50/50 border border-amber-100 px-4 py-3"
          >
            <span className="text-sm font-bold text-ink">{m.name}</span>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-ink-faint">
                Now: <span className="font-bold text-ink">{m.current}</span>
              </span>
              <ArrowRight className="h-3 w-3 text-brand-blue" />
              <span className="font-bold text-brand-blue">{m.target}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
