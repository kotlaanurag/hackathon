import { useState } from "react";
import {
  X,
  Plus,
  FileSpreadsheet,
  Upload,
  Trash2,
  Target,
  Users,
  CheckCircle2,
  Tag,
  Calendar,
  Building2,
  ListChecks,
  FileText,
  Sparkles,
  Loader2,
  Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";

type ExtraReq = { id: string; text: string };

export function RequirementOnboarding() {
  const [title, setTitle] = useState("Auto-triage support tickets with LLM classifier");
  const [lob, setLob] = useState("Customer Experience");
  const [priority, setPriority] = useState("P1 · High");
  const [targetDate, setTargetDate] = useState("2026-06-15");
  const [goal, setGoal] = useState(
    "Reduce ticket triage time by 60% and route P1 incidents to the on-call engineer within 30 seconds.",
  );
  const [stakeholders, setStakeholders] = useState("Support Ops, Engineering, CX, PagerDuty owners");
  const [acceptance, setAcceptance] = useState(
    "P1 tickets auto-classified within 30s\nFalse-positive routing < 2%\nShadow mode validated for 48h before go-live",
  );
  const [extras, setExtras] = useState<ExtraReq[]>([
    { id: "e1", text: "PII masking on all inbound payloads" },
    { id: "e2", text: "Audit log retained for 90 days" },
  ]);
  const [newExtra, setNewExtra] = useState("");
  const [files, setFiles] = useState<{ name: string; size: string }[]>([
    { name: "BRD-Triage-v3.xlsx", size: "182 KB" },
  ]);

  const addExtra = () => {
    if (!newExtra.trim()) return;
    setExtras((p) => [...p, { id: crypto.randomUUID(), text: newExtra.trim() }]);
    setNewExtra("");
  };

  const onUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFiles((p) => [...p, { name: f.name, size: `${Math.round(f.size / 1024)} KB` }]);
  };

  const acceptanceList = acceptance.split("\n").filter(Boolean);

  const [mdOpen, setMdOpen] = useState(false);
  const [mdLoading, setMdLoading] = useState(false);
  const [markdown, setMarkdown] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const buildLocalMarkdown = () =>
    [
      `# ${title}`,
      "",
      `**Generated:** ${new Date().toISOString()}`,
      "",
      "## Overview",
      "",
      "| Field | Value |",
      "| --- | --- |",
      `| Line of Business | ${lob || "—"} |`,
      `| Priority | ${priority || "—"} |`,
      `| Target Date | ${targetDate || "—"} |`,
      `| Stakeholders | ${stakeholders || "—"} |`,
      "",
      "## Business Goal",
      "",
      goal || "_No goal provided._",
      "",
      "## Acceptance Criteria",
      "",
      ...(acceptanceList.length ? acceptanceList.map((a) => `- [ ] ${a}`) : ["_None specified._"]),
      "",
      "## Additional Requirements",
      "",
      ...(extras.length ? extras.map((e) => `- ${e.text}`) : ["_None specified._"]),
      "",
      "## Attachments",
      "",
      ...(files.length ? files.map((f) => `- \`${f.name}\` (${f.size})`) : ["_No files attached._"]),
    ].join("\n");

  const STUB_API =
    (import.meta.env.VITE_STUB_API_URL as string | undefined) ?? "http://localhost:8001";

  const buildPayload = () => ({
    title,
    lob,
    priority,
    target_date: targetDate,
    stakeholders,
    goal,
    acceptance_criteria: acceptanceList,
    additional_requirements: extras.map((e) => e.text),
    attachments: files,
  });

  const handleGenerate = async () => {
    setMdOpen(true);
    setMdLoading(true);
    try {
      const res = await fetch(`${STUB_API}/api/requirements/generate-md`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { markdown: string };
      setMarkdown(data.markdown);
    } catch {
      setMarkdown(buildLocalMarkdown());
    } finally {
      setMdLoading(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${STUB_API}/api/requirements/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { requirement_id: string };
      toast.success(`Requirement submitted as ${data.requirement_id}`);
    } catch {
      toast.success("Requirement submitted (offline mock).");
    } finally {
      setSubmitting(false);
      setMdOpen(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[58%_42%]">
      {/* LEFT — Form */}
      <div className="surface-tint-blue space-y-5 rounded-xl border border-[#2563EB]/20 p-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#2563EB]" />
          <div className="font-mono text-[10px] tracking-widest text-[#2563EB]/80">
            INTAKE FORM · MOCK DATA PRE-FILLED
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field icon={<FileText className="h-3.5 w-3.5" />} label="Requirement Title" full>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} className="bg-background" />
          </Field>
          <Field icon={<Building2 className="h-3.5 w-3.5" />} label="Line of Business">
            <Input value={lob} onChange={(e) => setLob(e.target.value)} className="bg-background" />
          </Field>
          <Field icon={<Tag className="h-3.5 w-3.5" />} label="Priority">
            <Input value={priority} onChange={(e) => setPriority(e.target.value)} className="bg-background" />
          </Field>
          <Field icon={<Calendar className="h-3.5 w-3.5" />} label="Target Date">
            <Input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="bg-background"
            />
          </Field>
          <Field icon={<Users className="h-3.5 w-3.5" />} label="Stakeholders">
            <Input
              value={stakeholders}
              onChange={(e) => setStakeholders(e.target.value)}
              className="bg-background"
            />
          </Field>
        </div>

        <Field icon={<Target className="h-3.5 w-3.5" />} label="Business Goal" full>
          <Textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={3}
            className="bg-background"
          />
        </Field>

        <Field icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="Acceptance Criteria (one per line)" full>
          <Textarea
            value={acceptance}
            onChange={(e) => setAcceptance(e.target.value)}
            rows={4}
            className="bg-background font-mono text-[12px]"
          />
        </Field>

        {/* Excel upload */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium text-foreground/80">
            <FileSpreadsheet className="h-3.5 w-3.5 text-[#16A34A]" /> Excel Upload
          </div>
          <label className="group flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-dashed border-[#16A34A]/40 bg-[#16A34A]/5 px-4 py-3 transition hover:bg-[#16A34A]/10">
            <div className="flex items-center gap-2.5">
              <div className="rounded-md bg-[#16A34A]/15 p-2">
                <Upload className="h-4 w-4 text-[#16A34A]" />
              </div>
              <div>
                <div className="text-sm font-medium">Drop .xlsx or click to upload</div>
                <div className="text-[11px] text-muted-foreground">BRD, criteria sheet, or backlog export</div>
              </div>
            </div>
            <span className="rounded-md border border-[#16A34A]/40 bg-background px-2.5 py-1 font-mono text-[10px] tracking-widest text-[#16A34A]">
              BROWSE
            </span>
            <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={onUpload} />
          </label>

          {files.length > 0 && (
            <ul className="mt-2 space-y-1.5">
              {files.map((f, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between rounded-md border border-border/60 bg-background px-3 py-1.5 text-[12px]"
                >
                  <span className="flex items-center gap-2">
                    <FileSpreadsheet className="h-3.5 w-3.5 text-[#16A34A]" />
                    <span className="font-medium">{f.name}</span>
                    <span className="text-muted-foreground">· {f.size}</span>
                  </span>
                  <button
                    onClick={() => setFiles((p) => p.filter((_, j) => j !== i))}
                    className="text-muted-foreground transition hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Additional Requirements */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium text-foreground/80">
            <ListChecks className="h-3.5 w-3.5 text-purple" /> Additional Requirements
          </div>
          <ul className="mb-2 space-y-1.5">
            {extras.map((e) => (
              <li
                key={e.id}
                className="flex items-center justify-between rounded-md border border-purple/20 bg-purple/5 px-3 py-1.5 text-[12px]"
              >
                <span className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-purple" />
                  {e.text}
                </span>
                <button
                  onClick={() => setExtras((p) => p.filter((x) => x.id !== e.id))}
                  className="text-muted-foreground transition hover:text-destructive"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Input
              value={newExtra}
              onChange={(e) => setNewExtra(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addExtra())}
              placeholder="e.g. SOC2 logging required"
              className="bg-background"
            />
            <Button type="button" onClick={addExtra} variant="secondary" size="sm">
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
          </div>
        </div>
      </div>

      {/* RIGHT — Preview */}
      <div className="flex flex-col gap-4">
        <div className="surface-tint-purple flex-1 rounded-xl border border-purple/20 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="font-mono text-[10px] tracking-widest text-purple/80">
              REQUIREMENT SUMMARY · LIVE PREVIEW
            </div>
            <span className="rounded-full border border-[#D97706]/40 bg-[#D97706]/10 px-2 py-0.5 font-mono text-[9px] tracking-widest text-[#D97706]">
              PENDING REVIEW
            </span>
          </div>

          <h3 className="font-display text-base font-semibold leading-snug">{title}</h3>

          <div className="mt-3 grid grid-cols-2 gap-3 text-[12px]">
            <Meta icon={<Building2 className="h-3 w-3" />} label="LoB" value={lob} />
            <Meta icon={<Tag className="h-3 w-3" />} label="Priority" value={priority} />
            <Meta icon={<Calendar className="h-3 w-3" />} label="Target" value={targetDate} />
            <Meta icon={<Users className="h-3 w-3" />} label="Stakeholders" value={stakeholders} />
          </div>

          <Section title="Goal">
            <p className="text-[12.5px] leading-relaxed text-foreground/85">{goal}</p>
          </Section>

          <Section title="Acceptance Criteria">
            <ul className="space-y-1.5">
              {acceptanceList.map((a, i) => (
                <li key={i} className="flex gap-2 text-[12.5px] leading-snug">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          </Section>

          {extras.length > 0 && (
            <Section title="Additional Requirements">
              <ul className="space-y-1">
                {extras.map((e) => (
                  <li key={e.id} className="flex gap-2 text-[12.5px]">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-purple" />
                    <span>{e.text}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {files.length > 0 && (
            <Section title="Attachments">
              <ul className="space-y-1">
                {files.map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-[12px]">
                    <FileSpreadsheet className="h-3.5 w-3.5 text-[#16A34A]" />
                    <span className="font-medium">{f.name}</span>
                    <span className="text-muted-foreground">· {f.size}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleGenerate}
            className="flex-1 bg-success text-success-foreground hover:bg-success/90"
          >
            <Sparkles className="mr-1.5 h-4 w-4" /> Generate Requirements
          </Button>
          <Button variant="ghost" className="text-destructive hover:bg-destructive/10 hover:text-destructive">
            <X className="mr-1.5 h-4 w-4" /> Reject
          </Button>
        </div>
      </div>

      <Dialog open={mdOpen} onOpenChange={setMdOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[#2563EB]" />
              Generated Requirements
            </DialogTitle>
            <DialogDescription>
              Review the generated Markdown specification before submitting it to the pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-auto rounded-md border border-border/60 bg-muted/40 p-4">
            {mdLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Generating Markdown…
              </div>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-foreground">
                {markdown}
              </pre>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMdOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || mdLoading} className="gap-2">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({
  label,
  icon,
  children,
  full,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <div className={full ? "sm:col-span-2" : ""}>
      <Label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-foreground/80">
        <span className="text-[#2563EB]">{icon}</span>
        {label}
      </Label>
      {children}
    </div>
  );
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-background/70 px-2.5 py-1.5">
      <div className="flex items-center gap-1 font-mono text-[9px] tracking-widest text-muted-foreground">
        <span className="text-purple">{icon}</span>
        {label.toUpperCase()}
      </div>
      <div className="mt-0.5 truncate text-[12px] font-medium">{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <div className="mb-1.5 font-mono text-[9px] tracking-widest text-purple/80">
        {title.toUpperCase()}
      </div>
      {children}
    </div>
  );
}
