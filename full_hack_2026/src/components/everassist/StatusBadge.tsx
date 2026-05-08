import { Check, Clock, Loader2, UserCheck } from "lucide-react";
import type { StageStatus } from "@/lib/pipeline-data";
import { cn } from "@/lib/utils";

const map: Record<StageStatus, { label: string; cls: string; Icon: React.ComponentType<{ className?: string }> }> = {
  pending: {
    label: "Pending",
    cls: "bg-muted text-muted-foreground border-border",
    Icon: Clock,
  },
  "in-progress": {
    label: "In Progress",
    cls: "bg-cyan/10 text-cyan border-cyan/30",
    Icon: Loader2,
  },
  review: {
    label: "Awaiting Review",
    cls: "bg-purple/15 text-purple border-purple/40",
    Icon: UserCheck,
  },
  complete: {
    label: "Complete",
    cls: "bg-success/10 text-success border-success/30",
    Icon: Check,
  },
};

export function StatusBadge({ status, className }: { status: StageStatus; className?: string }) {
  const { label, cls, Icon } = map[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide uppercase",
        cls,
        className,
      )}
    >
      <Icon className={cn("h-3 w-3", status === "in-progress" && "animate-spin")} />
      {label}
    </span>
  );
}
