import type { AnalysisContext, AnalysisJob, AnalysisResult, HistoryJob } from "./utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ── Submit Analysis ─────────────────────────────────────────

export async function submitAnalysis(
  quantFiles: File[],
  qualFiles: File[],
  context: AnalysisContext
): Promise<AnalysisJob> {
  const formData = new FormData();

  quantFiles.forEach((f) => formData.append("quant_files", f));
  qualFiles.forEach((f) => formData.append("qual_files", f));

  formData.append("research_question", context.researchQuestion);
  formData.append("product_description", context.productDescription);
  if (context.timePeriod) {
    formData.append("time_period", context.timePeriod);
  }
  if (context.arpu !== undefined && context.arpu !== null) {
    formData.append("arpu", String(context.arpu));
  }

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(body.detail || "Failed to submit analysis", res.status);
  }

  return res.json();
}

// ── Poll for Results ────────────────────────────────────────

export async function getResults(jobId: string): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/results/${jobId}`);

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(body.detail || "Failed to fetch results", res.status);
  }

  return res.json();
}

// ── Poll with retry logic ───────────────────────────────────

export async function pollForResults(
  jobId: string,
  onProgress?: (status: string) => void,
  maxAttempts: number = 60,
  intervalMs: number = 2000
): Promise<AnalysisResult> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const result = await getResults(jobId);

      if (result.status === "completed") {
        return result;
      }

      if (result.status === "failed") {
        throw new ApiError("Analysis failed on the server.", 500);
      }

      onProgress?.(`Processing... (${attempt + 1}s)`);
    } catch (err) {
      if (err instanceof ApiError && err.status !== 202) {
        throw err;
      }
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new ApiError("Analysis timed out. Please try again.", 408);
}

// ── History ─────────────────────────────────────────────────

export async function getHistory(): Promise<{ jobs: HistoryJob[] }> {
  const res = await fetch(`${API_BASE}/api/history`);
  if (!res.ok) {
    throw new ApiError("Failed to fetch history", res.status);
  }
  return res.json();
}

export async function deleteHistoryItem(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/history/${jobId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new ApiError("Failed to delete report", res.status);
  }
}

export async function wipeHistory(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/history`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new ApiError("Failed to wipe history", res.status);
  }
}

// ── Chat ────────────────────────────────────────────────────

export async function chatWithAnalysis(
  jobId: string,
  question: string,
  reportContext: Record<string, unknown>
): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/chat/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, report_context: reportContext }),
  });

  if (!res.ok) {
    throw new ApiError("Chat request failed", res.status);
  }
  return res.json();
}

// ── Health Check ────────────────────────────────────────────

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
