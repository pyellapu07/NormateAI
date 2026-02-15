import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Shared Types ──────────────────────────────────────────────

export interface UploadedFile {
  file: File;
  name: string;
  size: number;
  type: string;
}

export interface AnalysisContext {
  researchQuestion: string;
  productDescription: string;
  timePeriod?: string;
}

export interface AnalysisJob {
  jobId: string;
  status: "pending" | "processing" | "completed" | "failed";
  createdAt: string;
}

export interface QuantEvidence {
  metric: string;
  value: string;
  change?: string;
  direction?: "up" | "down" | "flat";
}

export interface QualEvidence {
  theme: string;
  sentiment: number;
  sentimentLabel: "positive" | "negative" | "neutral" | "mixed";
  quotes: string[];
}

export interface RecommendedAction {
  title: string;
  description: string;
  evidence: string;
  impact: "High" | "Medium" | "Low";
  difficulty: "High" | "Medium" | "Low";
  estimatedEffect: string;
}

export interface ABTest {
  name: string;
  control: string;
  treatment: string;
  metric: string;
  duration: string;
}

export interface TrackedMetric {
  name: string;
  current: string;
  target: string;
}

export interface AnalysisResult {
  jobId: string;
  status: "completed" | "failed";
  problemSummary: string;
  quantEvidence: QuantEvidence[];
  qualEvidence: QualEvidence[];
  actions: RecommendedAction[];
  abTests: ABTest[];
  metrics: TrackedMetric[];
  generatedAt: string;
}

// ── Helpers ──────────────────────────────────────────────────

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function sentimentColor(score: number): string {
  if (score >= 0.3) return "text-emerald-600";
  if (score <= -0.3) return "text-red-500";
  return "text-ink-muted";
}

export function impactBadgeColor(impact: string): string {
  switch (impact) {
    case "High":
      return "bg-red-100 text-red-700 border-red-200";
    case "Medium":
      return "bg-amber-100 text-amber-700 border-amber-200";
    case "Low":
      return "bg-emerald-100 text-emerald-700 border-emerald-200";
    default:
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}
