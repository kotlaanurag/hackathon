import { Link, useNavigate } from "@tanstack/react-router";
import {
  Building2,
  Github,
  Sparkles,
  Tag,
  ArrowUpRight,
  Flame,
  CircleDot,
  Leaf,
  AlertTriangle,
  type LucideIcon,
} from "lucide-react";
import type { Requirement } from "@/lib/requirements-data";
import { MiniPipeline } from "./MiniPipeline";
import { cn } from "@/lib/utils";

const STATUS_CLS: Record<Requirement["status"], string> = {
  "in-progress": "bg-[#DBEAFE] text-[#1E40AF]",
  review: "bg-[#FEF3C7] text-[#92400E]",
  shipped: "bg-[#DCFCE7] text-[#166534]",
  backlog: "bg-[#F1F5F9] text-[#475569]",
  error: "bg-[oklch(94%_0.06_25)] text-[#c92a2a]",
};

const STATUS_LABEL: Record<Requirement["status"], string> = {
  "in-progress": "In Progress",
  review: "Awaiting Review",
  shipped: "Complete",
  backlog: "Backlog",
  error: "Failed",
};

const PRIORITY_CFG: Record<
  Requirement["priority"],
  { cls: string; Icon: LucideIcon }
> = {
  High: { cls: "bg-[#FEE2E2] text-[#B91C1C]", Icon: Flame },
  Med: { cls: "bg-[#DBEAFE] text-[#1D4ED8]", Icon: CircleDot },
  Low: { cls: "bg-[#DCFCE7] text-[#15803D]", Icon: Leaf },
};

function avatarUrl(seed: string) {
  // Deterministic real-person portrait from randomuser.me
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  const idx = Math.abs(hash) % 99;
  const gender = (Math.abs(hash) % 2) === 0 ? "men" : "women";
  return `https://randomuser.me/api/portraits/${gender}/${idx}.jpg`;
}


export function RequirementRow({ req }: { req: Requirement }) {
  const navigate = useNavigate();
  const goToRequirement = () => {
    navigate({ to: "/requirement/$id", params: { id: req.id } });
  };

  const Priority = PRIORITY_CFG[req.priority];
  const SourceIcon = req.source.toLowerCase().includes("copilot")
    ? Github
    : Sparkles;

  const isError = req.status === "error";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={goToRequirement}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          goToRequirement();
        }
      }}
      className={cn(
        "group relative flex cursor-pointer flex-col gap-3 overflow-hidden rounded-2xl border border-border/60 bg-card p-4 shadow-card transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.02] hover:border-primary/40 hover:shadow-xl active:scale-[0.99]",
        isError && "border-l-[3px] border-l-[#c92a2a] hover:border-l-[#c92a2a]",
      )}
    >
      {!isError && (
        <span
          className={cn(
            "absolute left-0 top-0 h-full w-1",
            req.status === "in-progress" && "bg-[#2563EB]",
            req.status === "review" && "bg-[#D97706]",
            req.status === "shipped" && "bg-[#16A34A]",
            req.status === "backlog" && "bg-[#94A3B8]",
          )}
        />
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold text-muted-foreground">
            <span className="text-primary">{req.id}</span>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                STATUS_CLS[req.status],
              )}
            >
              {STATUS_LABEL[req.status]}
            </span>
          </div>
          <Link
            to="/requirement/$id"
            params={{ id: req.id }}
            onClick={(e) => e.stopPropagation()}
            className="mt-1 flex items-start gap-1 font-display text-[14.5px] font-semibold leading-snug text-foreground group-hover:text-primary"
          >
            <span className="line-clamp-2">{req.title}</span>
            <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-0 transition group-hover:opacity-100" />
          </Link>
          {isError && req.error && (
            <div className="mt-1 font-mono text-[11px] text-[#c92a2a]">
              × {req.error.reason}
            </div>
          )}
        </div>
        {isError ? (
          <span
            className="flex shrink-0 items-center gap-1 rounded-full border border-[#c92a2a]/30 bg-[oklch(94%_0.06_25)] px-2 py-0.5 text-[11px] font-semibold text-[#c92a2a]"
            title={req.error?.type ?? "Failed"}
          >
            <AlertTriangle className="h-3 w-3" />
            {req.error?.type ?? "Failed"}
          </span>
        ) : (
          <span
            className={cn(
              "flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
              Priority.cls,
            )}
            title={`Priority: ${req.priority}`}
          >
            <Priority.Icon className="h-3 w-3" />
            {req.priority}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <Building2 className="h-3.5 w-3.5 text-[#7C3AED]" />
          {req.lob}
        </span>
        <span className="flex items-center gap-1">
          <SourceIcon className="h-3.5 w-3.5 text-[#0891B2]" />
          {req.source}
        </span>
      </div>

      <div className="rounded-xl border border-border/40 bg-surface-elevated/60 px-3 py-2.5">
        <MiniPipeline
          stages={req.stages}
          allComplete={req.status === "shipped"}
          requirementId={req.id}
        />
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[11.5px] text-muted-foreground">
          <img
            src={avatarUrl(req.owner.initials + req.id)}
            alt={req.owner.name}
            className="h-7 w-7 rounded-full border border-border/60 bg-white object-cover"
          />
          <div className="flex flex-col leading-tight">
            <span className="font-semibold text-foreground">
              {req.owner.initials}
            </span>
            <span className="text-[10.5px]">{req.owner.name}</span>
          </div>
        </div>
        {isError ? (
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => e.stopPropagation()}
              className="rounded-md border border-[#c92a2a] bg-white px-2.5 py-1 text-[11px] font-semibold text-[#c92a2a] transition hover:bg-[oklch(97%_0.03_25)]"
            >
              Retry
            </button>
            <button
              onClick={(e) => e.stopPropagation()}
              className="text-[11px] font-semibold text-[#c92a2a] underline-offset-2 hover:underline"
            >
              View Log
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-end gap-1">
            {req.tags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-surface-elevated px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                <Tag className="h-2.5 w-2.5" />
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
