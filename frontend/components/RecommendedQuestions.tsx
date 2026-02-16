"use client";

import { MessageCircleQuestion, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface RecommendedQuestionsProps {
  questions: string[];
  onQuestionClick?: (question: string) => void;
}

export default function RecommendedQuestions({
  questions,
  onQuestionClick,
}: RecommendedQuestionsProps) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="rounded-2xl border border-purple-200 bg-gradient-to-br from-white to-purple-50/30 p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-100">
          <MessageCircleQuestion className="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <h3 className="font-display text-lg font-bold text-ink">
            Dig Deeper
          </h3>
          <p className="text-xs text-ink-faint">
            AI-suggested follow-up questions
          </p>
        </div>
      </div>

      <div className="space-y-2.5">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onQuestionClick?.(q)}
            className={cn(
              "group flex w-full items-start gap-3 rounded-xl border border-purple-100 bg-white px-4 py-3.5 text-left transition-all",
              onQuestionClick
                ? "hover:border-purple-300 hover:shadow-md hover:bg-purple-50/30 active:scale-[0.995]"
                : "cursor-default"
            )}
          >
            <Sparkles
              className={cn(
                "mt-0.5 h-4 w-4 shrink-0 text-purple-400 transition-colors",
                onQuestionClick && "group-hover:text-purple-600"
              )}
            />
            <p className="text-sm leading-relaxed text-ink/80 group-hover:text-ink">
              {q}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
