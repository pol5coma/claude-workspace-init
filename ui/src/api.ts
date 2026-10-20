// Types mirror the read-only JSON API served by `spado ui` (src/spado/ui/server.py).
import { useQuery } from "@tanstack/react-query";

export type Level = "human" | "orchestrator" | "officer" | "specialist";
export type Status =
  | "pending"
  | "awaiting_plan_approval"
  | "ready"
  | "running"
  | "blocked"
  | "provisional"
  | "awaiting_review"
  | "needs_revalidation"
  | "accepted"
  | "not_applicable";
export type Scope = { kind: "workflow" | "phase" | "subphase"; id: string | null };

export type RunSummary = {
  id: string;
  workflow: string;
  scope: Scope;
  objective: string;
  mode: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type Plan = {
  id: string;
  version: number;
  objective: string;
  deliverable: string;
  actions: string[];
  criteria: string[];
  inputs: Record<string, string>;
  assumptions: string[];
  missing_dependencies: string[];
  reused_activities: string[];
  approved_by: string | null;
  approved_at: string | null;
};

export type Activity = {
  id: string;
  sequence: number;
  subphase: string;
  mode: string;
  owner: string;
  previous_id: string | null;
  phase_plan_id: string | null;
  status: Status;
  plan: Plan;
  out_of_order: boolean;
  reason: string;
  arrangement: string | null;
  outputs: string[];
  domain_reviews: Record<string, string>;
  human_review: string | null;
  criteria_evidence: Record<string, string>;
};

export type SubphaseDefinition = {
  id: string;
  title: string;
  slug: string | null;
  phase: string;
  owners: string[];
  specialists: string[];
  dependencies: string[];
  deliverable: string;
  exit_criteria: string;
  applicability: string;
};

export type PhaseDefinition = {
  id: string;
  title: string;
  slug: string | null;
  lifecycle: string;
  subphases: string[];
};

export type Finding = {
  severity: string;
  code: string;
  subphase?: string;
  activity?: string;
  dependency?: string;
  action?: string;
  reason?: string;
};

export type Overview = {
  id: string;
  objective: string;
  scope: Scope;
  mode: string;
  version: number;
  created_at: string;
  updated_at: string;
  main_phase: string | null;
  scope_subphases: string[];
  workflow: {
    id: string;
    version: string;
    title: string;
    phases: PhaseDefinition[];
    subphases: Record<string, SubphaseDefinition>;
  };
  status: {
    phases: {
      id: string;
      closed: boolean;
      plan: Plan | null;
      subphases: { id: string; selected: boolean; status: Status; instances: Activity[] }[];
    }[];
  };
  review: Finding[];
  phase_plans: Record<string, Plan>;
  phase_reviews: Record<string, string>;
};

export type Definition = {
  id: string;
  name: string;
  acronym: string;
  traditional: string | null;
  level: Level;
  mandate: string;
  skills: string[];
  subphases: string[];
  scope_subphases: string[];
  reports_to: string[];
  in_scope: boolean;
};

export type Instance = {
  id: string;
  definition: string;
  level: Level;
  parent_id: string | null;
  subphases: string[];
  event_count: number;
  event_kinds: Record<string, number>;
  last_event: { kind: string; timestamp: string } | null;
  activities: { id: string; subphase: string; status: Status; plan_version: number; outputs: string[] }[];
  reviews: { activity: string; subphase: string | null; decision: string; evidence: string; timestamp: string }[];
};

export type Organization = {
  tiers: { level: Level; label: string }[];
  scope_subphases: string[];
  definitions: Definition[];
  instances: Instance[];
};

export type Message = {
  id: string;
  timestamp: string | null;
  source: "db" | "transcript";
  kind: string;
  category?: string | null;
  from: string;
  to: string[];
  summary: string;
  rationale?: string;
  text?: string;
  subphase?: string | null;
  activity?: string | null;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
  session?: string;
  subagent_type?: string;
};

export type ActorRow = {
  id: string;
  project: string;
  definition: string;
  level: Level;
  run_id: string | null;
  subphases: string[];
  parent_id: string | null;
};

export type Thread = {
  agent: string;
  actor: string;
  session: string;
  subagent_type: string;
  description: string;
  messages: { role: string; timestamp: string | null; text: string; tool?: string }[];
};

export type Messages = {
  messages: Message[];
  actors: ActorRow[];
  transcripts: { available: boolean; folder: string | null; sessions: string[] };
  threads: Thread[];
};

export type RevisionMeta = {
  id: string;
  sequence: number;
  path: string;
  digest: string;
  author: string;
  subphase: string | null;
  dependencies: string[];
  approved_by: string | null;
  supersedes: string | null;
  created_at: string;
  official: boolean;
  size: number;
};
export type Revision = RevisionMeta & { content: string };

export type EventRow = {
  id: string;
  actor: string;
  timestamp: string;
  request: { kind: string; payload: Record<string, unknown>; rationale: string };
  result: Record<string, unknown>;
};
export type DbCounts = Record<string, number>;
export type Pulse = { version: number; updated_at: string; event_count: number; transcripts: number };

export class ApiError extends Error {}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body.error ?? `${response.status} ${path}`);
  return body as T;
}

const POLL_MS = 2000;

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => getJson<RunSummary[]>("/api/runs"),
    refetchInterval: 5000,
  });
}

export function useSource() {
  return useQuery({
    queryKey: ["source"],
    queryFn: () => getJson<{ label: string }>("/api/source"),
    staleTime: Infinity,
  });
}

/** Polls the cheap pulse endpoint; its key changes only when the recorded state changes. */
export function usePulse(runId: string) {
  return useQuery({
    queryKey: ["pulse", runId],
    queryFn: () => getJson<Pulse>(`/api/runs/${runId}/pulse`),
    refetchInterval: POLL_MS,
  });
}

export function pulseKey(pulse: Pulse | undefined): string {
  return pulse ? `${pulse.version}:${pulse.event_count}:${pulse.transcripts}` : "initial";
}

export function useRunData<T>(runId: string, path: string, pulse: string) {
  return useQuery({
    queryKey: ["run", runId, path, pulse],
    queryFn: () => getJson<T>(`/api/runs/${runId}${path}`),
    // Keep showing the previous result only while the same view refreshes, never across views:
    // another path's rows have a different shape.
    placeholderData: (previous, query) => (query?.queryKey[2] === path ? previous : undefined),
    staleTime: Infinity,
  });
}
