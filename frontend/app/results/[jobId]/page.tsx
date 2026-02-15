"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Loader2,
  ArrowLeft,
  Download,
  AlertTriangle,
  RefreshCw,
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

  const handleExportPDF = async () => {
    if (!reportRef.current) return;
    setIsExporting(true);

    try {
      // Small delay to ensure any hover states or UI jitters settle
      await new Promise((resolve) => setTimeout(resolve, 100));

      const element = reportRef.current;
      
      // Capture the canvas with specific overrides for PDF aesthetics
      const canvas = await html2canvas(element, {
        scale: 2, 
        useCORS: true,
        logging: false,
        backgroundColor: '#F8FAFC', // Slightly cleaner off-white
        windowWidth: 1200, // Forces a consistent desktop-like width for the PDF layout
        onclone: (clonedDoc) => {
          // Find the element in the cloned document and add extra padding for the PDF
          const el = clonedDoc.getElementById("results-container");
          if (el) {
            el.style.padding = "40px";
            el.style.gap = "32px"; // Increases spacing between cards
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
      
      const margin = 10; // 10mm margin for a professional look
      const contentWidth = pdfWidth - (margin * 2);
      
      const imgProps = pdf.getImageProperties(imgData);
      const imgRenderHeight = (imgProps.height * contentWidth) / imgProps.width;

      let heightLeft = imgRenderHeight;
      let position = margin; // Start with the margin at the top

      // Page 1
      pdf.addImage(imgData, 'JPEG', margin, position, contentWidth, imgRenderHeight, undefined, 'FAST');
      heightLeft -= (pdfHeight - margin * 2);

      // Subsequent Pages
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
          <div className="flex flex-col items-center gap-4 py-32">
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
          <div className="flex flex-col items-center gap-4 py-32">
            <div className="rounded-full bg-red-50 p-4">
               <AlertTriangle className="h-10 w-10 text-red-500" />
            </div>
            <p className="text-lg font-semibold text-ink">Analysis failed to load</p>
            <button 
                onClick={() => window.location.reload()} 
                className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" /> Try Again
            </button>
          </div>
        )}

        {state === "ready" && result && (
          <div 
            ref={reportRef} 
            id="results-container" 
            className="flex flex-col gap-8 transition-all"
          >
            <div className="border-b border-slate-100 pb-8 text-center">
               <h1 className="mb-2 text-2xl font-bold text-ink">Root Cause Analysis</h1>
               <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                Report ID: {jobId} • {new Date(result.generatedAt).toLocaleDateString()}
              </p>
            </div>

            <ProblemSummaryCard summary={result.problemSummary} />

            <div className="grid gap-8 lg:grid-cols-2">
              <QuantEvidenceCard items={result.quantEvidence} />
              <QualEvidenceCard items={result.qualEvidence} />
            </div>

            <ActionsCard actions={result.actions} />

            <div className="grid gap-8 lg:grid-cols-2">
              <ABTestCard tests={result.abTests} />
              <MetricsCard metrics={result.metrics} />
            </div>
            
            {/* Minimalist Footer for PDF only */}
            <div className="mt-12 hidden border-t border-slate-100 pt-8 text-center print:block">
                <p className="text-xs text-slate-400">Generated by Normate AI Insights Engine</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}