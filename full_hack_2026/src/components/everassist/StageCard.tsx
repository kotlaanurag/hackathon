import { ChevronDown, ClipboardList, FileCode2, Sparkles, GitBranch, Code2, BookOpen, type LucideIcon } from "lucide-react";
import type { Stage } from "@/lib/pipeline-data";
import { StatusBadge } from "./StatusBadge";
import { cn } from "@/lib/utils";

const iconMap: Record<string, LucideIcon> = {
  ClipboardList, FileCode2, Sparkles, GitBranch, Code2, BookOpen,
};

export function StageCard({
  stage,
  active,
  onClick,
}: {
  stage: Stage;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = iconMap[stage.icon] ?? Sparkles;
  const isComplete = stage.status === "complete";
  const isActive = stage.status === "in-progress";
  const isReview = stage.status === "review";
  const isPending = stage.status === "pending";
  const isCompletedStage = stage.id === 1 || stage.id === 2;

  const cardTone =
    isCompletedStage
      ? "border-l-4 border-l-[#16A34A] border-[#DCFCE7] bg-[#F0FDF4] opacity-75"
      : isActive
        ? "border-2 border-[#2563EB] bg-white shadow-[0_0_0_4px_rgba(37,99,235,0.12),0_8px_16px_rgba(37,99,235,0.08)]"
        : isReview
          ? "border-l-4 border-l-[#D97706] border-[#FDE68A] bg-[#FFFBEB] shadow-[0_0_0_4px_rgba(217,119,6,0.1)]"
          : "border-transparent bg-[#F9FAFB] opacity-50 shadow-none";

  const iconTone =
    isComplete
      ? "border-[#BBF7D0] text-[#16A34A] bg-[#DCFCE7]"
      : isActive
        ? "border-[#93C5FD] text-[#2563EB] bg-[#DBEAFE]"
        : isReview
          ? "border-[#FCD34D] text-[#D97706] bg-[#FEF3C7]"
          : "border-[#E5E7EB] text-[#9CA3AF] bg-[#F3F4F6]";

  const stageTextTone =
    isPending ? "text-[#9CA3AF]"
    : isCompletedStage ? "text-[#6B7280]"
    : isActive ? "text-[#111827]"
    : "text-[#92400E]";

  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex w-[170px] shrink-0 items-center gap-2.5 rounded-xl border p-2.5 text-left",
        "transition-all duration-300 shadow-card hover:-translate-y-0.5",
        cardTone,
      )}
    >
      {active && (
        <div className="pointer-events-none absolute inset-0 z-10 rounded-xl border-2 border-[#2563EB] shadow-[0_0_0_3px_rgba(37,99,235,0.14),0_6px_12px_rgba(37,99,235,0.12)]" />
      )}

      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
          iconTone,
        )}
      >
        <Icon className="h-4 w-4" strokeWidth={2} />
      </div>

      <div className="min-w-0 flex-1">
        <div className={cn("font-mono text-[9px] tracking-widest", stageTextTone)}>
          STAGE {String(stage.id).padStart(2, "0")}
        </div>
        <div className={cn("truncate font-display text-[13px] font-semibold leading-tight", stageTextTone)}>
          {stage.shortTitle}
        </div>
      </div>

      <ChevronDown
        className={cn(
          "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-300",
          active && "rotate-180 text-[#2563EB]",
        )}
      />

      {isActive && (
        <div className="absolute inset-x-0 bottom-0 h-[3px] overflow-hidden rounded-b-2xl">
          <div className="h-full w-[40%] bg-[#2563EB] animate-[pipeline-progress_2s_ease-in-out_infinite]" />
        </div>
      )}

      {active && (
        <div className="pointer-events-none absolute -bottom-4 left-1/2 -translate-x-1/2 text-sm leading-none text-[#2563EB]">
          ▼
        </div>
      )}
    </button>
  );
}
