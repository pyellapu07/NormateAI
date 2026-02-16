"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Clock,
  FileText,
  Trash2,
  AlertTriangle,
  Loader2,
  FolderOpen,
  ArrowRight,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { getHistory, deleteHistoryItem, wipeHistory } from "@/lib/api";
import { cn, formatDate, type HistoryJob } from "@/lib/utils";

export default function HistoryPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<HistoryJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWipeConfirm, setShowWipeConfirm] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory();
      setJobs(data.jobs);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (jobId: string) => {
    setDeleting(jobId);
    try {
      await deleteHistoryItem(jobId);
      setJobs((prev) => prev.filter((j) => j.job_id !== jobId));
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeleting(null);
    }
  };

  const handleWipeAll = async () => {
    try {
      await wipeHistory();
      setJobs([]);
      setShowWipeConfirm(false);
    } catch (err) {
      console.error("Wipe failed:", err);
    }
  };

  const statusConfig = {
    completed: {
      icon: CheckCircle2,
      bg: "bg-emerald-100",
      text: "text-emerald-700",
      iconColor: "text-emerald-600",
      label: "Completed",
    },
    failed: {
      icon: XCircle,
      bg: "bg-red-100",
      text: "text-red-700",
      iconColor: "text-red-600",
      label: "Failed",
    },
    processing: {
      icon: Loader2,
      bg: "bg-amber-100",
      text: "text-amber-700",
      iconColor: "text-amber-600",
      label: "Processing",
    },
    pending: {
      icon: Clock,
      bg: "bg-slate-100",
      text: "text-slate-600",
      iconColor: "text-slate-500",
      label: "Pending",
    },
  };

  return (
    <div className="min-h-screen bg-surface">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 py-12">
        {/* Header */}
        <div className="mb-10 flex items-end justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Report History
            </h1>
            <p className="mt-2 text-base text-ink-muted">
              {jobs.length > 0
                ? `${jobs.length} past ${jobs.length === 1 ? "analysis" : "analyses"}`
                : "Your past analyses will appear here"}
            </p>
          </div>

          {jobs.length > 0 && !showWipeConfirm && (
            <button
              onClick={() => setShowWipeConfirm(true)}
              className="flex items-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-medium text-red-600 transition-all hover:bg-red-50 hover:shadow-sm"
            >
              <Trash2 className="h-4 w-4" />
              Clear All
            </button>
          )}
        </div>

        {/* Wipe confirmation */}
        {showWipeConfirm && (
          <div className="mb-8 animate-fade-in rounded-2xl border border-red-200 bg-gradient-to-r from-red-50 to-white p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-100">
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-red-900">
                  Delete all {jobs.length} reports?
                </p>
                <p className="mt-1 text-xs text-red-700/80">
                  This permanently removes all analysis data from the database.
                </p>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={handleWipeAll}
                    className="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700"
                  >
                    Yes, Delete All
                  </button>
                  <button
                    onClick={() => setShowWipeConfirm(false)}
                    className="rounded-lg border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-ink transition-colors hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center gap-4 py-32">
            <Loader2 className="h-10 w-10 animate-spin text-brand-blue" />
            <p className="text-sm text-ink-muted">Loading history...</p>
          </div>
        )}

        {/* Empty state */}
        {!loading && jobs.length === 0 && (
          <div className="flex flex-col items-center gap-5 py-32">
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-slate-100">
              <FolderOpen className="h-10 w-10 text-slate-300" />
            </div>
            <div className="text-center">
              <p className="text-lg font-semibold text-ink">No reports yet</p>
              <p className="mt-1 text-sm text-ink-muted">
                Upload data and run your first analysis to get started.
              </p>
            </div>
            <button
              onClick={() => router.push("/")}
              className="mt-2 flex items-center gap-2 rounded-xl bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-brand-blue-dark hover:shadow-md"
            >
              New Analysis
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Job list */}
        {!loading && jobs.length > 0 && (
          <div className="space-y-3">
            {jobs.map((job, i) => {
              const config =
                statusConfig[job.status as keyof typeof statusConfig] ||
                statusConfig.pending;
              const StatusIcon = config.icon;

              return (
                <div
                  key={job.job_id}
                  className="group flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 transition-all hover:border-brand-blue/40 hover:shadow-md"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  {/* Status icon */}
                  <div
                    className={cn(
                      "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
                      config.bg
                    )}
                  >
                    <StatusIcon
                      className={cn(
                        "h-5 w-5",
                        config.iconColor,
                        job.status === "processing" && "animate-spin"
                      )}
                    />
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[15px] font-semibold text-ink">
                      {job.research_question}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(job.created_at)}
                      </span>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                          config.bg,
                          config.text
                        )}
                      >
                        {config.label}
                      </span>
                      {job.product_description && (
                        <span className="hidden truncate sm:inline text-ink-faint">
                          {job.product_description.slice(0, 50)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex shrink-0 items-center gap-2">
                    {job.status === "completed" && (
                      <button
                        onClick={() => router.push(`/results/${job.job_id}`)}
                        className="flex items-center gap-1.5 rounded-xl bg-brand-blue px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-blue-dark hover:shadow-sm"
                      >
                        <FileText className="h-3.5 w-3.5" />
                        View
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(job.job_id)}
                      disabled={deleting === job.job_id}
                      className="rounded-xl border border-slate-200 p-2 text-ink-faint transition-all hover:border-red-200 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
                    >
                      {deleting === job.job_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
