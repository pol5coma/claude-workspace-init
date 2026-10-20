import type { Status } from "../api";

export const STATUS_LABEL: Record<Status, string> = {
  pending: "Pending",
  awaiting_plan_approval: "Awaiting plan approval",
  ready: "Ready",
  running: "Running",
  blocked: "Blocked",
  provisional: "Provisional",
  awaiting_review: "Awaiting review",
  needs_revalidation: "Needs revalidation",
  accepted: "Accepted",
  not_applicable: "Not applicable",
};

/** CSS custom property holding each status colour (defined in styles.css). */
export function statusVar(status: Status | string): string {
  return `var(--status-${status.replace(/_/g, "-")})`;
}

/** Domain colour per C-Agent; specialists inherit their primary officer's colour. */
export const DOMAIN_COLOR: Record<string, string> = {
  Human: "var(--human)",
  CAOAO: "var(--orchestrator)",
  CEAO: "#5a63c8",
  CPAO: "#8a5fc0",
  CTAO: "#3b86b8",
  CMAO: "#c2577f",
  CFAO: "#3d8f6e",
  COAO: "#b98a33",
  CRAO: "#c87443",
  CISAO: "#bd5340",
  CLAO: "#6c7685",
};

export const KIND_COLOR: Record<string, string> = {
  run_created: "var(--human)",
  delegation: "var(--orchestrator)",
  phase_plan: "#3b86b8",
  phase_approve: "#4f9a6c",
  prepare: "#3b86b8",
  revise_plan: "#3b86b8",
  approve_plan: "#4f9a6c",
  start: "#4f7cc9",
  document: "#8a5fc0",
  deliver: "#8a5fc0",
  domain_review: "#cf9a3c",
  human_review: "#cf9a3c",
  accept: "#4f9a6c",
  promote: "#4f9a6c",
  block: "#c8553d",
  note: "#8a877f",
  human_prompt: "var(--human)",
  host_reply: "#a29e95",
  delegation_prompt: "var(--orchestrator)",
  subagent_report: "#8a5fc0",
  spado_command: "#a29e95",
};

export function kindColor(kind: string, category?: string | null): string {
  if (kind === "note" && category === "human_question") return "var(--human)";
  return KIND_COLOR[kind] ?? "#94a3b8";
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function shortId(id: string | null | undefined): string {
  return id ? id.slice(0, 8) : "—";
}
