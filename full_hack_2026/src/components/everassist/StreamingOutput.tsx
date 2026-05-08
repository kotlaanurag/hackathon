import { useEffect, useState } from "react";

export function StreamingOutput({ tokens, active }: { tokens: string[]; active: boolean }) {
  const [text, setText] = useState("");
  const full = tokens.join("");

  useEffect(() => {
    if (!active) { setText(full); return; }
    setText("");
    let i = 0;
    const id = setInterval(() => {
      i += 2;
      setText(full.slice(0, i));
      if (i >= full.length) clearInterval(id);
    }, 28);
    return () => clearInterval(id);
  }, [active, full]);

  return (
    <div className="surface-code overflow-hidden rounded-xl border font-mono text-xs leading-relaxed shadow-card">
      <div className="flex items-center justify-between border-b border-[var(--code-border)] px-4 py-2">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-destructive/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-success/80" />
        </div>
        <div className="flex items-center gap-2 text-[10px] tracking-widest text-[color:var(--code-foreground)]/60">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan animate-pulse" />
          AGENT STREAM · v0.4
        </div>
      </div>
      <pre className="whitespace-pre-wrap px-4 py-3 text-[color:var(--code-foreground)]">
        {text}
        {active && <span className="ml-0.5 inline-block h-3 w-1.5 translate-y-0.5 bg-cyan animate-[blink_1s_steps(2,start)_infinite]" />}
      </pre>
    </div>
  );
}
