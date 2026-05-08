import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { AlertTriangle, ChevronDown, Plus, Sparkles } from "lucide-react";
import { TopBar } from "@/components/everassist/TopBar";
import { RequirementRow } from "@/components/everassist/RequirementRow";
import { NewRequirementModal } from "@/components/everassist/NewRequirementModal";
import { AlertsModal } from "@/components/everassist/AlertsModal";
import { PipelineHealth } from "@/components/everassist/PipelineHealth";
import { Button } from "@/components/ui/button";
import { requirements } from "@/lib/requirements-data";
import type { RequirementStatus } from "@/lib/requirements-data";

export const Route = createFileRoute("/")({
  component: Dashboard,
  head: () => ({
    meta: [
      { title: "EverAssist · Requirements Pipeline Dashboard" },
      {
        name: "description",
        content:
          "EverAssist requirements pipeline dashboard — track every story from intake to production across the 6-stage AI delivery pipeline.",
      },
    ],
  }),
});

type SectionConfig = {
  key: RequirementStatus;
  label: string;
  subtitle: string;
  color: string; // bar / pill border / accent
  bg: string; // panel background gradient
  border: string; // panel border
};

const SECTIONS: SectionConfig[] = [
  {
    key: "error",
    label: "Errors",
    subtitle: "Pipeline failures requiring intervention",
    color: "#c92a2a",
    bg: "linear-gradient(180deg, oklch(94% 0.06 25), oklch(97% 0.03 25) 60%)",
    border: "oklch(82% 0.10 25)",
  },
  {
    key: "in-progress",
    label: "In Progress",
    subtitle: "AI pipeline currently processing these requirements",
    color: "#2563d8",
    bg: "linear-gradient(180deg, oklch(93% 0.04 255), oklch(96% 0.025 255) 60%)",
    border: "oklch(85% 0.06 255)",
  },
  {
    key: "review",
    label: "Awaiting Review",
    subtitle: "Human approval required before code push",
    color: "#c47a07",
    bg: "linear-gradient(180deg, oklch(94% 0.05 80), oklch(97% 0.025 80) 60%)",
    border: "oklch(85% 0.07 80)",
  },
  {
    key: "shipped",
    label: "Done",
    subtitle: "Shipped to production",
    color: "#2a8a40",
    bg: "linear-gradient(180deg, oklch(94% 0.05 150), oklch(97% 0.025 150) 60%)",
    border: "oklch(85% 0.07 150)",
  },
];

// const DONUT_SEGMENTS = [
//   { label: "Shipped", value: dashboardStats.shipped, color: "#16A34A" },
//   { label: "In progress", value: dashboardStats.inProgress, color: "#2563EB" },
//   { label: "In review", value: dashboardStats.review, color: "#D97706" },
//   { label: "Backlog", value: dashboardStats.backlog, color: "#9CA3AF" },
// ];

// const SUMMARY_STAGES: { short: string; long: string; state: StageState }[] = [
//   { short: "Req's", long: "Requirements", state: "complete" },
//   { short: "Spec", long: "Tech Spec", state: "complete" },
//   { short: "Prompt", long: "Build Prompt", state: "active" },
//   { short: "AAP", long: "AAP Review", state: "next" },
//   { short: "Code", long: "Code-gen", state: "pending" },
//   { short: "Guide", long: "Guide Doc", state: "pending" },
// ];

// const STAGE_STATE_CLS: Record<StageState, string> = {
//   complete: "bg-[#DBEAFE] text-[#1E40AF]",
//   active: "bg-[#2563EB] text-white",
//   next: "bg-[#93C5FD] text-white",
//   pending: "bg-[#F1F5F9] text-[#94A3B8]",
// };

const ALERTS = [
  "US-003 blocked in AAP (6 days)",
  "US-009 test data stale",
  "US-001 has 3 unreviewed test cases",
];

function AlertBanner({ onReviewAll }: { onReviewAll: () => void }) {
  return (
    <div className="mb-4 flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
      <p className="flex-1 text-sm text-amber-800">
        <span className="font-semibold">{ALERTS.length} issues need attention</span>
        {" · "}
        {ALERTS.join(" · ")}
      </p>
      <button
        onClick={onReviewAll}
        className="flex shrink-0 items-center gap-1.5 rounded-full border border-amber-400 px-3 py-1 text-xs font-semibold text-amber-600 transition hover:bg-amber-100"
      >
        Review all
        <ChevronDown className="h-3 w-3" />
      </button>
    </div>
  );
}

function Dashboard() {
  const [modalOpen, setModalOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<RequirementStatus | null>(null);
  const navigate = useNavigate();

  const handleAddNew = () => {
    navigate({
      to: "/requirement/$id",
      params: { id: requirements[0].id },
      search: { stage: 1 },
    });
  };

  const toggleFilter = (key: RequirementStatus) => {
    setStatusFilter((prev) => (prev === key ? null : key));
  };

  const healthSegments = SECTIONS.map((s) => ({
    key: s.key,
    label: s.label,
    color: s.color,
    value: requirements.filter((r) => r.status === s.key).length,
  }));

  return (
    <div className="flex h-screen flex-col overflow-hidden text-foreground">
      <div className="bg-grid flex h-full flex-1 flex-col overflow-hidden">
        <TopBar />
        <NewRequirementModal open={modalOpen} onOpenChange={setModalOpen} />
        <AlertsModal open={alertsOpen} onOpenChange={setAlertsOpen} />


        <div className="flex-1 overflow-y-auto">
          <div className="w-full px-6 py-3">
            <div className="mb-4 flex items-stretch gap-4">
              <div className="flex-1">
                <PipelineHealth
                  segments={healthSegments}
                  activeFilter={statusFilter}
                  onToggleFilter={toggleFilter}
                />
              </div>
              <div className="group flex items-center justify-end gap-4 rounded-xl border border-primary/20 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent px-5 py-3 shadow-card transition-all duration-300 ease-out hover:-translate-y-0.5 hover:scale-[1.02] hover:border-primary/40 hover:shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary transition-transform duration-300 group-hover:rotate-6 group-hover:scale-110">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Start a new requirement</div>
                    <div className="text-xs text-muted-foreground">Kick off the AI delivery pipeline in seconds</div>
                  </div>
                </div>
                <Button onClick={handleAddNew} className="gap-2 shadow-md transition-all duration-200 hover:scale-105 hover:shadow-lg active:scale-95">
                  <Plus className="h-4 w-4 transition-transform duration-200 group-hover:rotate-90" />
                  Add New Requirement
                </Button>
              </div>
            </div>

            {/* Summary panels */}
            {/* <div className="mb-6 flex gap-4">
              {/* Tickets donut */}
              {/* <div className="flex items-center gap-5 rounded-xl border border-border/60 bg-card px-5 py-4 shadow-card">
                <DonutChart segments={DONUT_SEGMENTS} total={dashboardStats.total} />
                <div className="flex flex-col gap-1.5">
                  {DONUT_SEGMENTS.map((seg) => (
                    <div key={seg.label} className="flex items-center gap-2 text-sm">
                      <span
                        className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: seg.color }}
                      />
                      <span className="text-foreground">{seg.label}</span>
                      <span className="ml-auto pl-4 font-semibold tabular-nums">{seg.value}</span>
                    </div>
                  ))}
                </div>
              </div> */}

              {/* Pipeline stages */}
              {/* <div className="flex flex-1 flex-col justify-between rounded-xl border border-border/60 bg-card px-5 py-4 shadow-card">
                <div className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Pipeline Stages
                </div>
                <SummaryPipeline />
              </div> */}
            {/* </div> */}

            {/* Sections */}
            <div className="flex flex-col gap-[18px]">
              {SECTIONS.map((section) => {
                const items = requirements.filter((r) => r.status === section.key);
                if (items.length === 0) return null;
                const collapsed = statusFilter !== null && statusFilter !== section.key;
                return (
                  <section
                    key={section.key}
                    className="rounded-2xl border transition-all duration-300"
                    style={{
                      background: section.bg,
                      borderColor: section.border,
                      padding: collapsed ? "10px 16px" : 20,
                    }}
                  >
                    <header className="flex items-center gap-3" style={{ marginBottom: collapsed ? 0 : 16 }}>
                      <span
                        aria-hidden
                        className="rounded-full"
                        style={{
                          width: 4,
                          height: collapsed ? 18 : 28,
                          background: section.color,
                        }}
                      />
                      <h2
                        className={collapsed ? "text-[14px] font-semibold leading-none" : "text-[18px] font-bold leading-none"}
                        style={{ color: section.color }}
                      >
                        {section.label}
                      </h2>
                      <span
                        className="inline-flex items-center rounded-[12px] border bg-white px-[10px] py-[2px] text-[12px] font-semibold"
                        style={{ borderColor: section.color, color: section.color }}
                      >
                        {items.length}
                      </span>
                      {!collapsed && (
                        <span className="text-[12px] text-[#6b7280]">{section.subtitle}</span>
                      )}
                    </header>
                    {!collapsed && (
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {items.map((req) => (
                          <RequirementRow key={req.id} req={req} />
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// function DonutChart({
//   segments,
//   total,
// }: {
//   segments: { label: string; value: number; color: string }[];
//   total: number;
// }) {
//   const r = 36;
//   const cx = 50;
//   const cy = 50;
//   const C = 2 * Math.PI * r;
//   let cumulative = 0;
//   return (
//     <div className="relative h-24 w-24 flex-shrink-0">
//       <svg viewBox="0 0 100 100" className="h-full w-full">
//         {segments.map((seg) => {
//           const fraction = seg.value / total;
//           const length = fraction * C;
//           const offset = C / 4 - cumulative * C;
//           cumulative += fraction;
//           return (
//             <circle key={seg.label} cx={cx} cy={cy} r={r} fill="none" stroke={seg.color}
//               strokeWidth="14" strokeDasharray={`${length} ${C}`} strokeDashoffset={offset} />
//           );
//         })}
//       </svg>
//       <div className="absolute inset-0 flex flex-col items-center justify-center">
//         <span className="text-xl font-bold leading-none">{total}</span>
//         <span className="mt-0.5 font-mono text-[10px] text-muted-foreground">tickets</span>
//       </div>
//     </div>
//   );
// }

// function SummaryPipeline() {
//   const SUMMARY_STAGES: { short: string; long: string; state: string }[] = [
//     { short: "Req's", long: "Requirements", state: "complete" },
//     { short: "Spec", long: "Tech Spec", state: "complete" },
//     { short: "Prompt", long: "Build Prompt", state: "active" },
//     { short: "AAP", long: "AAP Review", state: "next" },
//     { short: "Code", long: "Code-gen", state: "pending" },
//     { short: "Guide", long: "Guide Doc", state: "pending" },
//   ];
//   return (
//     <div>
//       <div className="flex w-full items-stretch">
//         {SUMMARY_STAGES.map((stage, i) => (
//           <div key={i} className="relative flex h-8 flex-1 items-center justify-center text-[11px] font-semibold tracking-wide">
//             {stage.short}
//           </div>
//         ))}
//       </div>
//       <div className="mt-1.5 flex w-full">
//         {SUMMARY_STAGES.map((stage) => (
//           <div key={stage.short} className="flex-1 text-center font-mono text-[10px] leading-tight text-muted-foreground">
//             {stage.long}
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// }
