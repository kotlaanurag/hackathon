import { Link } from "@tanstack/react-router";
import {
  ClipboardList,
  FileText,
  Sparkles,
  ListChecks,
  Code2,
  BookOpen,
  Check,
  X,
  type LucideIcon,
} from "lucide-react";
import type { StageState } from "@/lib/requirements-data";
import { STAGE_LABELS } from "@/lib/requirements-data";
import { cn } from "@/lib/utils";

const STAGE_ICONS: LucideIcon[] = [
  ClipboardList,
  FileText,
  Sparkles,
  ListChecks,
  Code2,
  BookOpen,
];

const NODE_CLS: Record<StageState, string> = {
  complete: "bg-[#16A34A] text-white border-[#16A34A]",
  active: "bg-[#2563EB] text-white border-[#2563EB] ring-4 ring-[#2563EB]/15",
  next: "bg-white text-[#2563EB] border-[#93C5FD]",
  pending: "bg-white text-[#94A3B8] border-[#E2E8F0]",
  error: "bg-[#c92a2a] text-white border-[#c92a2a] ring-4 ring-[#c92a2a]/20",
};

const LINE_CLS: Record<StageState, string> = {
  complete: "bg-[#16A34A]",
  active: "bg-[#16A34A]",
  next: "bg-[#E2E8F0]",
  pending: "bg-[#E2E8F0]",
  error: "bg-[#E2E8F0]",
};

export function MiniPipeline({
  stages,
  allComplete,
  requirementId,
}: {
  stages: StageState[];
  allComplete?: boolean;
  requirementId?: string;
}) {
  return (
    <div className="flex w-full items-center">
      {stages.map((s, i) => {
        const state: StageState = allComplete ? "complete" : s;
        const Icon = STAGE_ICONS[i];
        const node = (
          <div
            className={cn(
              "relative flex h-7 w-7 items-center justify-center rounded-full border-2 transition group-hover/node:scale-110",
              NODE_CLS[state],
            )}
            title={STAGE_LABELS[i]}
            aria-label={`${STAGE_LABELS[i]} — ${state}`}
          >
            {state === "complete" ? (
              <Check className="h-3.5 w-3.5" strokeWidth={3} />
            ) : state === "error" ? (
              <X className="h-3.5 w-3.5" strokeWidth={3} />
            ) : (
              <Icon className="h-3.5 w-3.5" strokeWidth={2.25} />
            )}
          </div>
        );

        return (
          <div key={i} className="flex flex-1 items-center last:flex-initial">
            {requirementId ? (
              <Link
                to="/requirement/$id"
                params={{ id: requirementId }}
                search={{ stage: i + 1 }}
                onClick={(e) => e.stopPropagation()}
                className="group/node shrink-0"
              >
                {node}
              </Link>
            ) : (
              <div className="group/node shrink-0">{node}</div>
            )}
            {i < stages.length - 1 && (
              <div
                className={cn(
                  "mx-1 h-[3px] flex-1 rounded-full",
                  LINE_CLS[allComplete ? "complete" : s],
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
