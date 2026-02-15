"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Clock,
  Shield,
  Layers,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import FileUpload from "@/components/FileUpload";
import ContextForm from "@/components/ContextForm";
import { submitAnalysis } from "@/lib/api";
import { cn, type AnalysisContext } from "@/lib/utils";

type SubmitState = "idle" | "submitting" | "success" | "error";

export default function HomePage() {
  const router = useRouter();

  const [quantFiles, setQuantFiles] = useState<File[]>([]);
  const [qualFiles, setQualFiles] = useState<File[]>([]);
  const [context, setContext] = useState<AnalysisContext>({
    researchQuestion: "",
    productDescription: "",
    timePeriod: "",
  });
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canSubmit =
    quantFiles.length > 0 &&
    qualFiles.length > 0 &&
    context.researchQuestion.trim().length > 10 &&
    context.productDescription.trim().length > 5;

  const handleAnalyze = async () => {
    if (!canSubmit || submitState === "submitting") return;

    setSubmitState("submitting");
    setErrorMsg(null);

    try {
      const job = await submitAnalysis(quantFiles, qualFiles, context);
      setSubmitState("success");

      // Navigate to results after a short delay for the success animation
      setTimeout(() => {
        router.push(`/results/${job.jobId}`);
      }, 800);
    } catch (err: unknown) {
      setSubmitState("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Something went wrong."
      );
    }
  };

  return (
    <div className="min-h-screen bg-surface">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-slate-100 grain-overlay">
        {/* Background grid */}
        <div className="absolute inset-0 grid-pattern" />

        {/* Gradient blobs */}
        <div className="pointer-events-none absolute -top-32 right-0 h-80 w-80 rounded-full bg-brand-blue/5 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 left-10 h-60 w-60 rounded-full bg-brand-purple/5 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-16 sm:py-20 text-center">
          <div className="mx-auto max-w-2xl">
            <div className="mb-5 inline-flex items-center gap-1.5 rounded-full bg-brand-blue/10 px-3 py-1 text-xs font-semibold text-brand-blue">
              <Sparkles className="h-3 w-3" />
              AI-Powered Research Synthesis
            </div>

            <h1 className="font-display text-4xl font-bold tracking-tight text-ink sm:text-5xl">
              Fuse your research data.
              <br />
              <span className="bg-gradient-to-r from-brand-blue via-brand-purple to-brand-amber bg-clip-text text-transparent">
                Get clarity in seconds.
              </span>
            </h1>

            <p className="mt-5 text-lg leading-relaxed text-ink-muted text-balance">
              Upload your quantitative metrics and qualitative feedback. Normate AI
              triangulates the data and delivers ranked, actionable UX
              recommendations — backed by statistical evidence and user quotes.
            </p>
          </div>

          {/* Value props */}
          <div className="mx-auto mt-10 grid max-w-xl grid-cols-3 gap-6">
            {[
              { icon: Clock, label: "60-second analysis" },
              { icon: Layers, label: "Multi-source fusion" },
              { icon: Shield, label: "Evidence-backed" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex flex-col items-center gap-1.5">
                <Icon className="h-5 w-5 text-brand-blue/60" />
                <span className="text-xs font-medium text-ink-muted">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="mx-auto max-w-4xl px-6 py-12">
        {/* Step indicator */}
        <div className="mb-8 flex items-center justify-center gap-8 text-xs font-medium">
          {["Upload Data", "Add Context", "Analyze"].map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold",
                  i === 0
                    ? "bg-brand-blue text-white"
                    : i === 1
                      ? quantFiles.length > 0 && qualFiles.length > 0
                        ? "bg-brand-blue text-white"
                        : "bg-slate-100 text-ink-faint"
                      : canSubmit
                        ? "bg-brand-blue text-white"
                        : "bg-slate-100 text-ink-faint"
                )}
              >
                {i + 1}
              </span>
              <span className="hidden sm:inline text-ink-muted">{step}</span>
            </div>
          ))}
        </div>

        <div className="space-y-8">
          {/* File Uploads - side by side on desktop */}
          <div className="grid gap-6 md:grid-cols-2">
            <FileUpload
              variant="quant"
              files={quantFiles}
              onFilesChange={setQuantFiles}
            />
            <FileUpload
              variant="qual"
              files={qualFiles}
              onFilesChange={setQualFiles}
            />
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-slate-200" />
            <span className="text-xs font-medium text-ink-faint">
              Research Context
            </span>
            <div className="h-px flex-1 bg-slate-200" />
          </div>

          {/* Context Form */}
          <div className="mx-auto max-w-2xl">
            <ContextForm context={context} onChange={setContext} />
          </div>

          {/* Analyze Button */}
          <div className="flex flex-col items-center gap-3 pt-4">
            <button
              onClick={handleAnalyze}
              disabled={!canSubmit || submitState === "submitting"}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-xl px-8 py-3.5 text-sm font-semibold text-white shadow-lg transition-all duration-200",
                canSubmit && submitState === "idle"
                  ? "bg-brand-blue hover:bg-brand-blue-dark hover:shadow-xl hover:shadow-brand-blue/25 active:scale-[0.98]"
                  : submitState === "submitting"
                    ? "bg-brand-blue/80 cursor-wait"
                    : submitState === "success"
                      ? "bg-emerald-500"
                      : "bg-slate-300 cursor-not-allowed"
              )}
            >
              {submitState === "idle" && (
                <>
                  <Sparkles className="h-4 w-4" />
                  Analyze Data
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
              {submitState === "submitting" && (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading & Processing...
                </>
              )}
              {submitState === "success" && (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Redirecting to Results...
                </>
              )}
              {submitState === "error" && (
                <>
                  <Sparkles className="h-4 w-4" />
                  Retry Analysis
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            {!canSubmit && submitState === "idle" && (
              <p className="text-xs text-ink-faint">
                Upload files and fill in the research context to begin.
              </p>
            )}

            {errorMsg && (
              <p className="max-w-md rounded-lg bg-red-50 px-4 py-2 text-center text-sm text-red-600">
                {errorMsg}
              </p>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-100 py-8 text-center text-xs text-ink-faint">
        Normate AI — named after Don Norman, father of user experience.
        <br />
        Built by Pete · UMD Xylem Institute
      </footer>
    </div>
  );
}
