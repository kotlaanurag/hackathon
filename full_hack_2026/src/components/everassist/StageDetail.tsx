import { Check, Pencil, X, AlertTriangle } from "lucide-react";
import type { Stage } from "@/lib/pipeline-data";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./StatusBadge";
import { StreamingOutput } from "./StreamingOutput";
import { RequirementOnboarding } from "./RequirementOnboarding";

function MarkdownPreview({ src }: { src: string }) {
  // tiny renderer for h2, list, blockquote, bold, code
  const lines = src.split("\n");
  return (
    <div className="space-y-2 text-sm leading-relaxed text-foreground/90">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) return <h3 key={i} className="font-display text-base font-semibold text-foreground">{line.slice(3)}</h3>;
        if (line.startsWith("> ")) return <blockquote key={i} className="border-l-2 border-purple pl-3 text-purple/90 italic">{line.slice(2)}</blockquote>;
        if (/^\d+\.\s/.test(line)) return <div key={i} className="flex gap-2"><span className="font-mono text-cyan">{line.match(/^\d+/)?.[0]}.</span><span>{format(line.replace(/^\d+\.\s/, ""))}</span></div>;
        if (line.startsWith("- ")) return <div key={i} className="flex gap-2"><span className="text-purple">•</span><span>{format(line.slice(2))}</span></div>;
        if (line.startsWith("_") && line.endsWith("_")) return <p key={i} className="text-xs text-muted-foreground italic">{line.slice(1, -1)}</p>;
        if (!line.trim()) return <div key={i} className="h-1" />;
        return <p key={i}>{format(line)}</p>;
      })}
    </div>
  );
}

function format(s: string) {
  const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**")) return <strong key={i} className="text-foreground">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`")) return <code key={i} className="rounded bg-[var(--code-bg)] px-1.5 py-0.5 font-mono text-[12px] text-[color:var(--code-foreground)]">{p.slice(1, -1)}</code>;
    return <span key={i}>{p}</span>;
  });
}

export function StageDetail({ stage }: { stage: Stage }) {
  const isReview = stage.status === "review";
  const showTerminalAndActions = stage.id === 3 || stage.id === 4;
  return (
    <div className="animate-[expand_0.35s_cubic-bezier(0.22,1,0.36,1)] surface-hero h-full rounded-2xl border border-l-[3px] border-l-[#2563EB] p-6 shadow-card">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-mono text-[10px] tracking-widest">
            <span className="font-bold text-[#2563EB]">STAGE {String(stage.id).padStart(2, "0")}</span>
            <span className="text-muted-foreground"> · DETAIL</span>
          </div>
          <h2 className="font-display text-xl font-semibold">{stage.title}</h2>
        </div>
        <StatusBadge status={stage.status} />
      </div>

      {stage.id === 1 ? (
        <RequirementOnboarding />
      ) : (
      <>
      {isReview && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-purple/40 bg-purple/10 p-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-purple" />
          <div className="text-sm">
            <div className="font-semibold text-purple">Human-in-the-loop checkpoint</div>
            <p className="text-foreground/80">
              Review the proposed plan below. Execution is paused until you approve.
            </p>
          </div>
        </div>
      )}

      <div className={showTerminalAndActions ? "grid gap-5 lg:grid-cols-[35%_65%]" : "grid gap-5"}>
        <div className="surface-tint-purple rounded-xl border border-purple/20 p-5">
          <div className="mb-3 text-[10px] font-mono tracking-widest text-purple/80">STAGE {String(stage.id).padStart(2, "0")} · OUTPUT</div>
          <MarkdownPreview src={stage.content} />
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[13px] leading-[1.6] text-[#6B7280] marker:text-[10px] marker:text-[#6B7280]">
            <li>Extracted 6 acceptance criteria from US-001</li>
            <li>Identified 3 tool dependencies: postgres.query, vector.search, slack.notify</li>
            <li>Constraints applied: latency &lt; 500ms, schema validation, retry policy</li>
            <li>Safety guardrails: PII masking, rate limiting, audit logging</li>
          </ul>
        </div>

        {showTerminalAndActions && (
          <div className="space-y-4">
            {stage.streamingTokens.length > 0 ? (
              <StreamingOutput tokens={stage.streamingTokens} active={stage.status === "in-progress"} />
            ) : (
              <div className="flex h-full min-h-[140px] items-center justify-center rounded-xl border border-dashed bg-background/30 p-6 text-center text-xs text-muted-foreground">
                No live agent output for this stage.
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button size="sm" className="bg-success text-success-foreground hover:bg-success/90">
                <Check className="mr-1.5 h-4 w-4" /> Approve
              </Button>
              <Button size="sm" variant="secondary">
                <Pencil className="mr-1.5 h-4 w-4" /> Edit
              </Button>
              <Button size="sm" variant="ghost" className="text-destructive hover:bg-destructive/10 hover:text-destructive">
                <X className="mr-1.5 h-4 w-4" /> Reject
              </Button>
            </div>
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}
