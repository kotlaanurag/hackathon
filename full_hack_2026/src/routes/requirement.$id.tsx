import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Activity, Cpu, ArrowLeft, Building2, Hash, GitBranch, Workflow } from "lucide-react";
import { initialStages } from "@/lib/pipeline-data";
import { requirements } from "@/lib/requirements-data";
import { TopBar } from "@/components/everassist/TopBar";
import { Pipeline } from "@/components/everassist/Pipeline";
import { StageDetail } from "@/components/everassist/StageDetail";
import { ChatPanel } from "@/components/everassist/ChatPanel";

export const Route = createFileRoute("/requirement/$id")({
  component: Index,
  validateSearch: (search: Record<string, unknown>): { stage?: number } => {
    const s = search.stage ? Number(search.stage) : undefined;
    return s ? { stage: s } : {};
  },
  head: () => ({
    meta: [
      { title: "HighlineHub · AI Delivery Pipeline" },
      { name: "description", content: "HighlineHub orchestrates a 6-stage AI delivery pipeline from requirements to production guide, with human-in-the-loop control." },
    ],
  }),
});

function Index() {
  const { id } = Route.useParams();
  const { stage: stageParam } = Route.useSearch();
  const req = requirements.find((r) => r.id === id) ?? requirements[0];
  const [stages] = useState(initialStages);
  const [selectedStage, setSelectedStage] = useState<number>(
    stageParam && stageParam >= 1 && stageParam <= 6 ? stageParam : 3,
  );
  useEffect(() => {
    if (stageParam && stageParam >= 1 && stageParam <= 6) {
      setSelectedStage(stageParam);
    }
  }, [stageParam]);
  const [env, setEnv] = useState<"Demo" | "Live">("Demo");
  const [demo, setDemo] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
  const [navHeight, setNavHeight] = useState(56);
  const [footerHeight, setFooterHeight] = useState(56);
  const [chatTopOffset, setChatTopOffset] = useState(56);
  const navRef = useRef<HTMLDivElement>(null);
  const footerRef = useRef<HTMLElement>(null);
  const pipelineRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const active = stages.find((s) => s.id === selectedStage)!;
  const completed = stages.filter((s) => s.status === "complete").length;
  const layoutVars = {
    "--nav-height": `${navHeight}px`,
    "--footer-height": `${footerHeight}px`,
  } as CSSProperties;

  useEffect(() => {
    const measure = () => {
      const navH = navRef.current?.getBoundingClientRect().height ?? 56;
      const footerH = footerRef.current?.getBoundingClientRect().height ?? 56;
      const pipelineBottom = pipelineRef.current?.getBoundingClientRect().bottom;

      setNavHeight(navH);
      setFooterHeight(footerH);

      if (pipelineBottom !== undefined) {
        setChatTopOffset(Math.max(navH, pipelineBottom));
      } else {
        setChatTopOffset(navH);
      }
    };

    measure();
    window.addEventListener("resize", measure);
    const contentEl = contentRef.current;
    contentEl?.addEventListener("scroll", measure);

    return () => {
      window.removeEventListener("resize", measure);
      contentEl?.removeEventListener("scroll", measure);
    };
  }, []);

  return (
    <div style={layoutVars} className="flex h-screen flex-col overflow-hidden text-foreground">
      <div className="bg-grid flex h-full flex-1 flex-col overflow-hidden">
        <div ref={navRef}>
          <TopBar />
        </div>

        <div ref={contentRef} className="flex flex-1 flex-col gap-4 overflow-y-auto overflow-x-hidden pb-4">
          {/* Hero / Pipeline header */}
          <section ref={pipelineRef} className="surface-hero ml-[calc(50%-50vw)] w-screen rounded-xl border px-5 py-3 shadow-card">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Link to="/" className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border/60 bg-background/60 text-muted-foreground transition hover:border-[#2563EB]/40 hover:text-[#2563EB]" aria-label="Back to dashboard">
                  <ArrowLeft className="h-3.5 w-3.5" />
                </Link>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] tracking-widest text-muted-foreground">
                    <span className="inline-flex items-center gap-1"><Building2 className="h-3 w-3" />{req.lob}</span>
                    <span className="text-border">·</span>
                    <span className="inline-flex items-center gap-1"><Hash className="h-3 w-3" />{req.id}</span>
                    <span className="text-border">·</span>
                    <span className="inline-flex items-center gap-1 text-[#2563EB]"><Workflow className="h-3 w-3" />Requirement → Production</span>
                  </div>
                  <h1 className="truncate font-display text-lg font-semibold tracking-tight sm:text-xl">
                    {req.title}
                  </h1>
                </div>
              </div>
              <div className="hidden items-center gap-1.5 rounded-md border border-border/60 bg-background/60 px-2 py-1 font-mono text-[10px] tracking-widest text-muted-foreground sm:inline-flex">
                <GitBranch className="h-3 w-3 text-[#2563EB]" />
                {completed}/{stages.length} STAGES
              </div>
            </div>

            <Pipeline stages={stages} activeId={selectedStage} onSelect={setSelectedStage} />
          </section>

          <div className={`mx-auto flex w-full max-w-[1600px] flex-1 gap-4 px-4 ${chatOpen ? "lg:pr-[340px]" : "lg:pr-12"}`}>
            <main className="min-w-0 flex flex-1 flex-col gap-4">
              {/* Detail */}
              <div className="flex-1">
                <StageDetail key={active.id} stage={active} />
              </div>
            </main>

          </div>
        </div>

        {/* Footer status */}
        <footer ref={footerRef} className="w-full shrink-0 grid grid-cols-1 items-center gap-1 border-t bg-card/40 px-4 py-1 text-[11px] text-muted-foreground md:grid-cols-[1fr_auto_1fr]">
          <div className="flex items-center gap-3 md:justify-self-start">
            <span className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${demo ? "bg-cyan" : "bg-success"} animate-pulse`} />
              {demo ? "Mock Mode" : "Connected"}
            </span>
            <span className="hidden items-center gap-1 sm:inline-flex">
              <Cpu className="h-3 w-3" /> orchestrator-1
            </span>
            <span className="hidden items-center gap-1 md:inline-flex">
              <Activity className="h-3 w-3" /> 99.98%
            </span>
          </div>
          <div className="flex items-center justify-center gap-3 font-mono text-[10px] tracking-widest">
            <InlineStat label="PROG" value={`${completed}/${stages.length}`} tone="blue" />
            <InlineStat label="AGENTS" value="3" tone="green" />
            <InlineStat label="LAT" value="412ms" tone="amber" />
          </div>
          <div className="hidden font-mono text-[10px] tracking-wide md:inline md:justify-self-end">© EverAssist · 2026</div>
        </footer>

        <ChatPanel
          open={chatOpen}
          onToggle={() => setChatOpen((o) => !o)}
          topOffset={chatTopOffset}
          bottomOffset={footerHeight}
        />
      </div>
    </div>
  );
}

function InlineStat({ label, value, tone }: { label: string; value: string; tone: "blue" | "green" | "amber" }) {
  const toneCls =
    tone === "blue" ? "text-[#2563EB]"
    : tone === "green" ? "text-[#16A34A]"
    : "text-[#D97706]";
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-[#94A3B8]">{label}</span>
      <span className={`font-semibold ${toneCls}`}>{value}</span>
    </span>
  );
}
