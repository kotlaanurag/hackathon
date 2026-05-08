export type StageStatus = "pending" | "in-progress" | "review" | "complete";

export type Stage = {
  id: number;
  title: string;
  shortTitle: string;
  description: string;
  status: StageStatus;
  icon: string;
  content: string;
  streamingTokens: string[];
  humanInLoop?: boolean;
};

export const initialStages: Stage[] = [
  {
    id: 1,
    title: "Requirement Onboarding",
    shortTitle: "Requirements",
    description: "Capture stakeholder intent and acceptance criteria.",
    status: "complete",
    icon: "ClipboardList",
    content: `## Business Requirements\n\n- **Goal:** Reduce ticket triage time by 60%.\n- **Stakeholders:** Support Ops, Engineering, CX.\n- **Acceptance:** P1 tickets auto-classified within 30s.\n\n_Onboarded by Alex Chen · Approved by Priya Rao_`,
    streamingTokens: [],
  },
  {
    id: 2,
    title: "Tech Spec",
    shortTitle: "Tech Spec",
    description: "Architectural decisions, data flow, integration map.",
    status: "complete",
    icon: "FileCode2",
    content: `## Technical Specification\n\n- **Stack:** TypeScript · Postgres · Vector DB\n- **Pattern:** Event-driven, queue-backed classifier\n- **SLO:** 99.9% availability, < 800ms p95\n\nIntegration with Zendesk, Slack, and PagerDuty via webhooks.`,
    streamingTokens: [],
  },
  {
    id: 3,
    title: "Build Prompt",
    shortTitle: "Build Prompt",
    description: "Compile spec into executable agent prompt bundle.",
    status: "in-progress",
    icon: "Sparkles",
    content: `## Build Prompt Synthesis\n\nCompiling spec → agent-ready prompt with constraints, tools, and guardrails.`,
    streamingTokens: [
      "Analyzing technical specification…\n",
      "Extracting constraints: latency, schema, retries…\n",
      "Binding tools: postgres.query, vector.search, slack.notify…\n",
      "Generating system prompt v0.4…\n",
      "Validating against safety policy ✓\n",
    ],
  },
  {
    id: 4,
    title: "Agent Action Plan",
    shortTitle: "AAP",
    description: "Step-by-step plan awaiting human approval.",
    status: "review",
    icon: "GitBranch",
    humanInLoop: true,
    content: `## Proposed Action Plan\n\n1. Provision \`tickets_classified\` table\n2. Deploy \`triage-agent\` worker (3 replicas)\n3. Wire Zendesk webhook → queue\n4. Backfill 30d of historical tickets\n5. Enable shadow mode for 48h\n\n> **Human review required** before execution.`,
    streamingTokens: [],
  },
  {
    id: 5,
    title: "Code Generation",
    shortTitle: "Codegen",
    description: "Generate, lint, and test production code.",
    status: "pending",
    icon: "Code2",
    content: `Awaiting AAP approval to begin code generation.`,
    streamingTokens: [],
  },
  {
    id: 6,
    title: "Project Guide",
    shortTitle: "Guide",
    description: "Hand-off documentation, runbook, and onboarding.",
    status: "pending",
    icon: "BookOpen",
    content: `Project guide will be generated after deployment.`,
    streamingTokens: [],
  },
];
