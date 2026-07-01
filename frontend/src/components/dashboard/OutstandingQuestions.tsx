"use client";

import { useState } from "react";

interface QuestionItem {
  id: number;
  deal_id?: number | null;
  company_name: string;
  category: string;
  question: string;
  answer?: string | null;
  status: string;
  created_at: string;
}

interface OutstandingQuestionsProps {
  questions: QuestionItem[];
  onStatusChange?: (questionId: number, status: string) => void;
  onDealClick?: (dealId: number) => void;
}

function getStatusBorderColor(status: string): string {
  switch (status) {
    case "in_progress":
      return "border-[#2DD4BF]";
    case "blocked":
      return "border-[#EF4444]";
    default:
      return "border-[#1E1E2E]";
  }
}

export default function OutstandingQuestions({
  questions,
  onStatusChange,
  onDealClick,
}: OutstandingQuestionsProps) {
  const [items, setItems] = useState<QuestionItem[]>(questions);

  // Keep local state in sync if prop changes
  if (JSON.stringify(questions.map((q) => q.id)) !== JSON.stringify(items.map((q) => q.id))) {
    setItems(questions);
  }

  const handleToggle = (question: QuestionItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const newStatus = question.status === "resolved" ? "pending" : "resolved";
    const updated = items.map((q) => (q.id === question.id ? { ...q, status: newStatus } : q));
    setItems(updated);
    onStatusChange?.(question.id, newStatus);
  };

  const handleRowClick = (question: QuestionItem) => {
    if (question.deal_id != null && onDealClick) {
      onDealClick(question.deal_id);
    }
  };

  return (
    <div className="bg-[#111118] border border-[#1E1E2E]">
      <div className="px-4 py-3 border-b border-[#1E1E2E] flex items-center justify-between">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">✅ Outstanding Questions</div>
        <div className="font-mono text-[11px] text-[#6B7280]">{items.length} questions</div>
      </div>

      <div className="p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 text-center py-8">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#10B981"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 6L9 17l-5-5" />
            </svg>
            <div className="text-[13px] text-[#9aa0ad]">No outstanding questions. All clear.</div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {items.map((question) => (
              <div
                key={question.id}
                onClick={() => handleRowClick(question)}
                className={`bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex items-start gap-3 ${
                  question.deal_id != null && onDealClick
                    ? "cursor-pointer hover:bg-[#111118] transition-colors"
                    : ""
                }`}
              >
                {/* Checkbox */}
                <div
                  onClick={(e) => handleToggle(question, e)}
                  className={`flex-shrink-0 w-[16px] h-[16px] border ${getStatusBorderColor(
                    question.status
                  )} bg-[#0A0A0F] flex items-center justify-center mt-0.5 cursor-pointer`}
                >
                  {question.status === "resolved" && (
                    <svg
                      width="10"
                      height="10"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#10B981"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div
                    className={`text-[13px] ${
                      question.status === "resolved" ? "text-[#9aa0ad] line-through" : "text-[#E8E8F0]"
                    }`}
                  >
                    {question.question}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[11px] font-mono text-[#C8A96E]">{question.company_name}</span>
                    <span className="text-[9px] uppercase tracking-[0.06em] bg-[#0A0A0F] border border-[#1E1E2E] px-[5px] py-[1px] text-[#6B7280]">
                      {question.category}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
