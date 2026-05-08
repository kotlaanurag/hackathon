import { useState } from "react";
import { Bot, Send, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "ai"; text: string };

const seed: Msg[] = [
  { role: "ai", text: "Hi — I'm EverAssist. I'll guide each pipeline stage. Ask me anything." },
  { role: "user", text: "Why is stage 4 paused?" },
  { role: "ai", text: "Stage 4 (AAP) requires human approval before execution to keep you in control of provisioning steps." },
];

export function ChatPanel({
  open,
  onToggle,
  topOffset,
  bottomOffset,
}: {
  open: boolean;
  onToggle: () => void;
  topOffset?: number;
  bottomOffset?: number;
}) {
  const [msgs, setMsgs] = useState<Msg[]>(seed);
  const [draft, setDraft] = useState("");

  function send() {
    if (!draft.trim()) return;
    setMsgs((m) => [...m, { role: "user", text: draft }]);
    const q = draft;
    setDraft("");
    setTimeout(() => {
      setMsgs((m) => [...m, { role: "ai", text: `Got it — exploring "${q}". (mock response)` }]);
    }, 600);
  }

  if (!open) {
    return (
      <button
        onClick={onToggle}
        style={{
          bottom: bottomOffset !== undefined ? `${bottomOffset + 12}px` : "calc(var(--footer-height, 56px) + 12px)",
        }}
        className="fixed right-4 z-30 hidden h-12 w-12 items-center justify-center rounded-full border surface-hero text-muted-foreground shadow-card hover:text-foreground lg:flex"
        aria-label="Open chat"
      >
        <Bot className="h-5 w-5" />
      </button>
    );
  }

  return (
    <aside
      style={{
        top: topOffset !== undefined ? `${topOffset}px` : "var(--nav-height, 56px)",
        bottom: bottomOffset !== undefined ? `${bottomOffset}px` : "var(--footer-height, 56px)",
      }}
      className={cn(
        "fixed right-0 z-20 hidden min-h-0 flex-col rounded-2xl border surface-hero backdrop-blur transition-all duration-300 lg:flex",
        "w-[340px]",
      )}
    >
      <button
        onClick={onToggle}
        className="absolute -left-3 top-6 flex h-6 w-6 items-center justify-center rounded-full border bg-surface-elevated text-muted-foreground hover:text-foreground"
        aria-label="Toggle chat"
      >
        <ChevronRight className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>

      {open ? (
        <div className="flex h-full min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center gap-2 border-b p-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple/15 text-purple">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <div className="font-display text-sm font-semibold">Assistant</div>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                Online · GPT-4o
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4 scrollbar-thin">
            {msgs.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
                    m.role === "user"
                      ? "bg-purple/20 text-foreground rounded-br-sm"
                      : "bg-surface-elevated text-foreground/90 rounded-bl-sm",
                  )}
                >
                  {m.text}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-auto shrink-0 border-t p-3">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {["Explain stage", "Suggest fix", "Summarize"].map((s) => (
                <button
                  key={s}
                  onClick={() => setDraft(s)}
                  className="inline-flex items-center gap-1 rounded-full border bg-background/40 px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  <Sparkles className="h-3 w-3" />
                  {s}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask EverAssist…"
                className="bg-background/60"
              />
              <Button size="icon" onClick={send} className="bg-purple hover:bg-purple/90 text-purple-foreground">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex h-full items-center justify-center">
          <Bot className="h-5 w-5 text-muted-foreground" />
        </div>
      )}
    </aside>
  );
}
