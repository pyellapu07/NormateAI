"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import {
  BarChart3,
  MessageSquareText,
  FileSpreadsheet,
  FileText,
  X,
  Upload,
  AlertCircle,
} from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";

// ── Types ───────────────────────────────────────────────────

interface FileUploadProps {
  variant: "quant" | "qual";
  files: File[];
  onFilesChange: (files: File[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
}

const CONFIG = {
  quant: {
    title: "Quantitative Data",
    description: "CSV or Excel files with metrics, analytics, or survey scores",
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        ".xlsx",
      ],
      "application/vnd.ms-excel": [".xls"],
    },
    icon: BarChart3,
    accentColor: "brand-blue",
    fileIcon: FileSpreadsheet,
    formats: "CSV, XLS, XLSX",
  },
  qual: {
    title: "Qualitative Data",
    description:
      "Text files with transcripts, feedback, interviews, or open-ended responses",
    accept: {
      "text/plain": [".txt"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "application/msword": [".doc"],
    },
    icon: MessageSquareText,
    accentColor: "brand-purple",
    fileIcon: FileText,
    formats: "TXT, DOC, DOCX",
  },
} as const;

// ── Component ───────────────────────────────────────────────

export default function FileUpload({
  variant,
  files,
  onFilesChange,
  maxFiles = 5,
  maxSizeMB = 25,
}: FileUploadProps) {
  const config = CONFIG[variant];
  const Icon = config.icon;
  const FileIcon = config.fileIcon;
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      setError(null);

      if (rejected.length > 0) {
        const reasons = rejected
          .flatMap((r) => r.errors.map((e) => e.message))
          .join(", ");
        setError(reasons);
        return;
      }

      const totalFiles = files.length + accepted.length;
      if (totalFiles > maxFiles) {
        setError(`Maximum ${maxFiles} files allowed.`);
        return;
      }

      onFilesChange([...files, ...accepted]);
    },
    [files, maxFiles, onFilesChange]
  );

  const removeFile = (index: number) => {
    const next = [...files];
    next.splice(index, 1);
    onFilesChange(next);
    setError(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: config.accept,
    maxSize: maxSizeMB * 1024 * 1024,
    maxFiles,
  });

  const isQuant = variant === "quant";

  return (
    <div className="flex flex-col gap-3">
      {/* Label */}
      <div className="flex items-center gap-2">
        <Icon
          className={cn(
            "h-5 w-5",
            isQuant ? "text-brand-blue" : "text-brand-purple"
          )}
        />
        <h3 className="text-sm font-semibold text-ink">{config.title}</h3>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 transition-all duration-200",
          isDragActive
            ? "dropzone-active"
            : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50",
          files.length > 0 && "py-5"
        )}
      >
        <input {...getInputProps()} />

        {files.length === 0 ? (
          <>
            <div
              className={cn(
                "mb-3 flex h-12 w-12 items-center justify-center rounded-xl transition-colors",
                isQuant
                  ? "bg-brand-blue/10 text-brand-blue"
                  : "bg-brand-purple/10 text-brand-purple"
              )}
            >
              <Upload className="h-5 w-5" />
            </div>
            <p className="text-sm font-medium text-ink">
              Drop files here or{" "}
              <span
                className={cn(
                  "underline underline-offset-2",
                  isQuant ? "text-brand-blue" : "text-brand-purple"
                )}
              >
                browse
              </span>
            </p>
            <p className="mt-1 text-xs text-ink-muted">{config.description}</p>
            <p className="mt-2 rounded-md bg-slate-100 px-2.5 py-1 font-mono text-[11px] text-ink-faint">
              {config.formats} · max {maxSizeMB}MB each
            </p>
          </>
        ) : (
          <div className="w-full space-y-2">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${i}`}
                className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2"
              >
                <FileIcon
                  className={cn(
                    "h-4 w-4 shrink-0",
                    isQuant ? "text-brand-blue" : "text-brand-purple"
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-ink">
                    {file.name}
                  </p>
                  <p className="text-xs text-ink-faint">
                    {formatFileSize(file.size)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(i);
                  }}
                  className="rounded-md p-1 text-ink-faint transition-colors hover:bg-slate-200 hover:text-ink"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}

            {files.length < maxFiles && (
              <p className="pt-1 text-center text-xs text-ink-faint">
                Drop more files or click to add ({files.length}/{maxFiles})
              </p>
            )}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
