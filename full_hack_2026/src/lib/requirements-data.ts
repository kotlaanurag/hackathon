export type StageState = "complete" | "active" | "next" | "pending" | "error";
export type RequirementStatus = "in-progress" | "review" | "shipped" | "backlog" | "error";
export type Priority = "High" | "Med" | "Low";

export type Requirement = {
  id: string;
  title: string;
  lob: string;
  source: string;
  status: RequirementStatus;
  priority: Priority;
  owner: { initials: string; name: string };
  tags: string[];
  stages: StageState[]; // length 6
  error?: {
    type: string; // short label e.g. "Schema mismatch"
    reason: string; // full one-liner
  };
};

export const STAGE_LABELS = [
  "Requirements",
  "Tech Spec",
  "Build Prompt",
  "AAP",
  "Codegen",
  "Guide",
];

export const requirements: Requirement[] = [
  {
    id: "US-001",
    title: "Auto-generate QA test cases from acceptance criteria",
    lob: "Motor LoB",
    source: "EverAssist",
    status: "in-progress",
    priority: "High",
    owner: { initials: "AR", name: "Motor LoB" },
    tags: ["QA", "EverAssist"],
    stages: ["complete", "complete", "active", "next", "pending", "pending"],
  },
  {
    id: "US-002",
    title: "Mock IRIS Policy Admin interface for Motor LoB",
    lob: "Motor LoB",
    source: "GitHub Copilot",
    status: "in-progress",
    priority: "High",
    owner: { initials: "SK", name: "Motor LoB" },
    tags: ["Mock", "Copilot"],
    stages: ["complete", "complete", "active", "next", "pending", "pending"],
  },
  {
    id: "US-004",
    title: "Field mapping validation with real-time business logic",
    lob: "Motor LoB",
    source: "GitHub Copilot",
    status: "in-progress",
    priority: "Med",
    owner: { initials: "TN", name: "Motor LoB" },
    tags: ["Validation"],
    stages: ["complete", "active", "next", "pending", "pending", "pending"],
  },
  {
    id: "US-007",
    title: "Acceptance criteria traceability to test suite",
    lob: "QA",
    source: "EverAssist",
    status: "in-progress",
    priority: "Med",
    owner: { initials: "PR", name: "QA" },
    tags: ["Traceability"],
    stages: ["complete", "complete", "active", "next", "pending", "pending"],
  },
  {
    id: "US-003",
    title: "Regression suite auto-update on story change",
    lob: "Home LoB",
    source: "EverAssist",
    status: "review",
    priority: "High",
    owner: { initials: "PR", name: "Home LoB" },
    tags: ["Regression"],
    stages: ["complete", "complete", "complete", "active", "next", "pending"],
  },
  {
    id: "US-005",
    title: "Phased rollout delivery plan generator",
    lob: "All LoB",
    source: "EverAssist",
    status: "review",
    priority: "High",
    owner: { initials: "AR", name: "All LoB" },
    tags: ["Planning"],
    stages: ["complete", "complete", "complete", "active", "next", "pending"],
  },
  {
    id: "US-006",
    title: "Human-in-loop approval gate before code push",
    lob: "DevOps",
    source: "Copilot",
    status: "review",
    priority: "Med",
    owner: { initials: "SK", name: "DevOps" },
    tags: ["HITL", "DevOps"],
    stages: ["complete", "complete", "complete", "active", "next", "pending"],
  },
  {
    id: "US-011",
    title: "GitHub Copilot prompt MD standard format enforcement",
    lob: "Engineering",
    source: "Copilot",
    status: "shipped",
    priority: "High",
    owner: { initials: "PR", name: "Engineering" },
    tags: ["Standards"],
    stages: ["complete", "complete", "complete", "complete", "complete", "complete"],
  },
  {
    id: "US-012",
    title: "EverAssist requirement refinement for Home LoB",
    lob: "Home LoB",
    source: "EverAssist",
    status: "shipped",
    priority: "Med",
    owner: { initials: "TN", name: "Home LoB" },
    tags: ["Requirements"],
    stages: ["complete", "complete", "complete", "complete", "complete", "complete"],
  },
  {
    id: "US-014",
    title: "IRIS policy sync for Motor renewal flow",
    lob: "Motor LoB",
    source: "EverAssist",
    status: "error",
    priority: "High",
    owner: { initials: "AR", name: "Motor LoB" },
    tags: ["IRIS", "Sync"],
    stages: ["complete", "complete", "complete", "error", "pending", "pending"],
    error: {
      type: "Schema mismatch",
      reason: "IRIS endpoint /policies returned 422",
    },
  },
  {
    id: "US-015",
    title: "Codegen pipeline for Home LoB claims intake",
    lob: "Home LoB",
    source: "Copilot",
    status: "error",
    priority: "Med",
    owner: { initials: "SK", name: "Home LoB" },
    tags: ["Codegen"],
    stages: ["complete", "complete", "error", "pending", "pending", "pending"],
    error: {
      type: "API timeout",
      reason: "Build prompt service exceeded 30s timeout",
    },
  },
];

export const dashboardStats = {
  total: 12,
  inProgress: 4,
  review: 3,
  shipped: 2,
  backlog: 3,
};
