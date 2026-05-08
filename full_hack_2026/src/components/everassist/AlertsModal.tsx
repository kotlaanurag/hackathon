import { useEffect, useState } from "react";
import { AlertTriangle, Clock, FileWarning, Loader2, ShieldAlert } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type AlertSeverity = "high" | "med" | "low";
type AlertType = "blocked" | "stale" | "review";

type AlertItem = {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  message: string;
  detail: string;
  since: string;
};

// Mock API response — swap fetch() in here when backend is ready
async function fetchAlerts(): Promise<AlertItem[]> {
  await new Promise((r) => setTimeout(r, 650));
  return [
    {
      id: "US-003",
      type: "blocked",
      severity: "high",
      message: "Blocked in AAP stage for 6 days",
      detail: "Awaiting sign-off from Architecture Review Board. Escalation recommended.",
      since: "2026-04-28",
    },
    {
      id: "US-009",
      type: "stale",
      severity: "med",
      message: "Test data is stale",
      detail: "Mock dataset last refreshed 14 days ago. QA results may be unreliable.",
      since: "2026-04-20",
    },
    {
      id: "US-001",
      type: "review",
      severity: "med",
      message: "3 unreviewed test cases pending",
      detail: "Test cases generated on 2026-04-30 have not been reviewed by the QA owner.",
      since: "2026-04-30",
    },
    {
      id: "US-007",
      type: "blocked",
      severity: "high",
      message: "Tech Spec rejected — returned to Requirements",
      detail: "Spec rejected by LoB lead due to incomplete edge-case coverage.",
      since: "2026-05-01",
    },
    {
      id: "US-011",
      type: "stale",
      severity: "low",
      message: "Build Prompt not updated in 10 days",
      detail: "Prompt is out of sync with updated acceptance criteria from revision 3.",
      since: "2026-04-24",
    },
  ];
}

const TYPE_META: Record<AlertType, { label: string; Icon: React.ElementType }> = {
  blocked: { label: "Blocked", Icon: ShieldAlert },
  stale:   { label: "Stale",   Icon: Clock },
  review:  { label: "Review",  Icon: FileWarning },
};

const SEVERITY_CLS: Record<AlertSeverity, { row: string; badge: string; icon: string }> = {
  high: {
    row:   "border-red-100 bg-red-50",
    badge: "bg-red-100 text-red-700",
    icon:  "text-red-500",
  },
  med: {
    row:   "border-amber-100 bg-amber-50",
    badge: "bg-amber-100 text-amber-700",
    icon:  "text-amber-500",
  },
  low: {
    row:   "border-blue-100 bg-blue-50",
    badge: "bg-blue-100 text-blue-700",
    icon:  "text-blue-500",
  },
};

export function AlertsModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setAlerts(null);
    fetchAlerts().then((data) => {
      setAlerts(data);
      setLoading(false);
    });
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-700">
            <AlertTriangle className="h-4 w-4" />
            Issues Needing Attention
          </DialogTitle>
        </DialogHeader>

        <div className="mt-1 space-y-2 pb-1">
          {loading && (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              <span className="text-sm">Loading issues…</span>
            </div>
          )}

          {alerts?.map((alert) => {
            const { Icon } = TYPE_META[alert.type];
            const cls = SEVERITY_CLS[alert.severity];
            return (
              <div
                key={`${alert.id}-${alert.type}`}
                className={`rounded-lg border px-4 py-3 ${cls.row}`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cls.icon}`} />
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[11px] font-semibold text-foreground">
                        {alert.id}
                      </span>
                      <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${cls.badge}`}>
                        {TYPE_META[alert.type].label}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-foreground">{alert.message}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{alert.detail}</p>
                  </div>
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                    {alert.since}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
