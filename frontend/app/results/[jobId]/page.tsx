"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Loader2,
  ArrowLeft,
  Download,
  AlertTriangle,
  RefreshCw,
  MessageCircle,
} from "lucide-react";
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import Navbar from "@/components/Navbar";
import {
  ProblemSummaryCard,
  QuantEvidenceCard,
  QualEvidenceCard,
  ActionsCard,
  ABTestCard,
  MetricsCard,
} from "@/components/InsightCard";
import FinancialImpactCard from "@/components/FinancialImpactCard";
import RecommendedQuestions from "@/components/RecommendedQuestions";
import PerspectiveToggle, { type Perspective } from "@/components/PerspectiveToggle";
import ChatSidebar from "@/components/ChatSidebar";
import { getResults } from "@/lib/api";
import type { AnalysisResult } from "@/lib/utils";

type PageState = "loading" | "ready" | "error";

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;
  const reportRef = useRef<HTMLDivElement>(null);

  const [state, setState] = useState<PageState>("loading");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [perspective, setPerspective] = useState<Perspective>("pm");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInitialQuestion, setChatInitialQuestion] = useState<string | undefined>();

  const handleExportPDF = async () => {
    if (!reportRef.current) return;
    setIsExporting(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 100));

      const element = reportRef.current;

      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#F8FAFC',
        windowWidth: 1200,
        onclone: (clonedDoc) => {
          const el = clonedDoc.getElementById("results-container");
          if (el) {
            el.style.padding = "40px";
            el.style.gap = "32px";
          }
        }
      });

      const imgData = canvas.toDataURL('image/jpeg', 0.95);
      const pdf = new jsPDF({
        orientation: 'p',
        unit: 'mm',
        format: 'a4',
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      const margin = 10;
      const contentWidth = pdfWidth - (margin * 2);

      const imgProps = pdf.getImageProperties(imgData);
      const imgRenderHeight = (imgProps.height * contentWidth) / imgProps.width;

      let heightLeft = imgRenderHeight;
      let position = margin;

      pdf.addImage(imgData, 'JPEG', margin, position, contentWidth, imgRenderHeight, undefined, 'FAST');
      heightLeft -= (pdfHeight - margin * 2);

      while (heightLeft > 0) {
        position = heightLeft - imgRenderHeight + margin;
        pdf.addPage();
        pdf.addImage(imgData, 'JPEG', margin, position, contentWidth, imgRenderHeight, undefined, 'FAST');
        heightLeft -= pdfHeight;
      }

      pdf.save(`Normate-Analysis-${jobId}.pdf`);
    } catch (error) {
      console.error('PDF export failed:', error);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const fetchResults = useCallback(async () => {
    try {
      const data = await getResults(jobId);
      if (data.status === "completed") {
        setResult(data);
        setState("ready");
        return true;
      }
      return false;
    } catch (err) {
      if (err instanceof Error && err.message.includes("still processing")) {
        return false;
      }
      setError(err instanceof Error ? err.message : "Failed to load results.");
      setState("error");
      return true;
    }
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;
    let timeout: NodeJS.Timeout;

    const poll = async () => {
      if (cancelled) return;
      const done = await fetchResults();
      if (!done && !cancelled) {
        setPollCount((c) => c + 1);
        timeout = setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [fetchResults]);

  const handleQuestionClick = (question: string) => {
    setChatInitialQuestion(question);
    setChatOpen(true);
  };

  // Perspective-based card visibility — each role gets a meaningfully different view
  const showFinancial = result?.financialImpact && (perspective === "cfo" || perspective === "pm");
  const showABTests = perspective === "pm" || perspective === "designer";
  const showMetrics = perspective === "pm" || perspective === "cfo";
  const showQuantEvidence = perspective === "pm" || perspective === "cfo";
  const showQualEvidence = perspective === "pm" || perspective === "designer";
  const showRecommendedQuestions = result?.suggestedQuestions && result.suggestedQuestions.length > 0;

  // Perspective-specific banner content
  const perspectiveBanner = {
    pm: {
      title: "Product Manager View",
      subtitle: "Full report — all evidence, actions, A/B tests, and metrics",
      color: "bg-brand-blue/5 border-brand-blue/20 text-brand-blue",
    },
    cfo: {
      title: "CFO / Finance View",
      subtitle: "Revenue impact, quantitative evidence, metrics, and cost of inaction",
      color: "bg-amber-50 border-amber-200 text-amber-800",
    },
    designer: {
      title: "UX Designer View",
      subtitle: "User quotes, qualitative themes, sentiment analysis, and A/B test ideas",
      color: "bg-purple-50 border-purple-200 text-purple-800",
    },
  };

  // Build report context for chat
  const reportContext: Record<string, unknown> = result
    ? {
        problemSummary: result.problemSummary,
        quantEvidence: result.quantEvidence,
        qualEvidence: result.qualEvidence,
        actions: result.actions,
        abTests: result.abTests,
        metrics: result.metrics,
      }
    : {};

  return (
    <div className="min-h-screen bg-surface">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-10 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-sm font-medium text-ink-muted transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </button>

          {state === "ready" && (
            <button
              onClick={handleExportPDF}
              disabled={isExporting}
              className="flex items-center gap-2 rounded-full bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-brand-blue-dark hover:shadow-md disabled:opacity-50"
            >
              {isExporting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating Report...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Export PDF
                </>
              )}
            </button>
          )}
        </div>

        {state === "loading" && (
          <div className="flex flex-col items-center gap-4 py-32 animate-fade-in">
            <Loader2 className="h-12 w-12 animate-spin text-brand-blue" />
            <div className="text-center">
              <p className="text-base font-medium text-ink">Synthesizing insights...</p>
              <div className="mt-4 h-1.5 w-64 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-gradient-to-r from-brand-blue to-brand-purple transition-all duration-1000"
                  style={{ width: `${Math.min(95, 10 + pollCount * 6)}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-col items-center gap-4 py-32 animate-fade-in">
            <div className="rounded-full bg-red-50 p-4">
              <AlertTriangle className="h-10 w-10 text-red-500" />
            </div>
            <p className="text-lg font-semibold text-ink">Analysis failed to load</p>
            {error && (
              <p className="text-sm text-ink-muted max-w-md text-center">{error}</p>
            )}
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" /> Try Again
            </button>
          </div>
        )}

        {state === "ready" && result && (
          <>
            {/* Perspective Toggle — above the report */}
            <div className="mb-8 animate-fade-in">
              <PerspectiveToggle current={perspective} onChange={setPerspective} />
            </div>

            {/* Perspective Banner */}
            <div className={`mb-4 rounded-xl border px-5 py-3 text-sm font-medium animate-fade-in ${perspectiveBanner[perspective].color}`}>
              <span className="font-bold">{perspectiveBanner[perspective].title}</span>
              <span className="mx-2">·</span>
              <span className="opacity-80">{perspectiveBanner[perspective].subtitle}</span>
            </div>

            <div
              ref={reportRef}
              id="results-container"
              className="flex flex-col gap-8 transition-all"
            >
              {/* Header */}
              <div className="border-b border-slate-100 pb-8 text-center animate-fade-in">
                <h1 className="mb-2 font-display text-3xl font-bold text-ink sm:text-4xl">
                  Root Cause Analysis
                </h1>
                <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                  Report ID: {jobId} &middot; {new Date(result.generatedAt).toLocaleDateString()}
                </p>
              </div>

              {/* Problem Summary — always visible */}
              <div className="stagger-1 animate-slide-up">
                <ProblemSummaryCard summary={result.problemSummary} />
              </div>

              {/* Financial Impact — CFO + PM perspectives */}
              {showFinancial && (
                <div className="stagger-2 animate-slide-up">
                  <FinancialImpactCard impact={result.financialImpact!} />
                </div>
              )}

              {/* Evidence Cards */}
              <div className="grid gap-8 lg:grid-cols-2">
                {showQuantEvidence && (
                  <div className="stagger-2 animate-slide-up">
                    <QuantEvidenceCard items={result.quantEvidence} />
                  </div>
                )}
                {showQualEvidence && (
                  <div className="stagger-3 animate-slide-up">
                    <QualEvidenceCard items={result.qualEvidence} />
                  </div>
                )}
              </div>

              {/* Actions — always visible */}
              <div className="stagger-3 animate-slide-up">
                <ActionsCard actions={result.actions} />
              </div>

              {/* A/B Tests + Metrics */}
              <div className="grid gap-8 lg:grid-cols-2">
                {showABTests && (
                  <div className="stagger-4 animate-slide-up">
                    <ABTestCard tests={result.abTests} />
                  </div>
                )}
                {showMetrics && (
                  <div className="stagger-4 animate-slide-up">
                    <MetricsCard metrics={result.metrics} />
                  </div>
                )}
              </div>

              {/* Recommended Questions */}
              {showRecommendedQuestions && (
                <div className="stagger-5 animate-slide-up">
                  <RecommendedQuestions
                    questions={result.suggestedQuestions}
                    onQuestionClick={handleQuestionClick}
                  />
                </div>
              )}

              {/* Minimalist Footer for PDF only */}
              <div className="mt-12 hidden border-t border-slate-100 pt-8 text-center print:block">
                <p className="text-xs text-slate-400">Generated by Normate AI Insights Engine</p>
              </div>
            </div>

            {/* Floating Chat Button */}
            <button
              onClick={() => {
                setChatInitialQuestion(undefined);
                setChatOpen(true);
              }}
              className="fixed bottom-8 right-8 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-brand-purple text-white shadow-lg shadow-brand-purple/25 transition-all hover:bg-brand-purple-dark hover:shadow-xl hover:shadow-brand-purple/30 active:scale-95"
              title="Chat with this analysis"
            >
              <MessageCircle className="h-6 w-6" />
            </button>

            {/* Chat Sidebar */}
            <ChatSidebar
              jobId={jobId}
              reportContext={reportContext}
              isOpen={chatOpen}
              onClose={() => setChatOpen(false)}
              initialQuestion={chatInitialQuestion}
            />
          </>
        )}
      </main>
    </div>
  );
}
