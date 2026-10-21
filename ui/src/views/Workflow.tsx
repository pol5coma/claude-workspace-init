import { useState } from "react";
import type { Activity, Overview } from "../api";
import { StatusChip } from "../components/StatusChip";
import type { Directory } from "../lib/people";
import { formatTime } from "../lib/status";

type Props = { overview: Overview; directory: Directory; onOpenDocument: (id: string) => void };

export function Workflow({ overview, directory, onOpenDocument }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const scope = new Set(overview.scope_subphases);
  const dependencies = new Set(
    overview.scope.kind === "subphase"
      ? overview.scope_subphases.flatMap((sid) => overview.workflow.subphases[sid].dependencies)
      : [],
  );
  const statusOf = new Map(overview.status.phases.flatMap((p) => p.subphases.map((s) => [s.id, s] as const)));

  return (
    <div className="scroll">
      <p className="notice" style={{ marginTop: 0, marginBottom: 20 }}>
        Scope: <strong>{overview.scope.kind === "workflow" ? "full workflow" : `${overview.scope.kind} ${overview.scope.id}`}</strong>
        {overview.scope.kind === "subphase" && dependencies.size > 0 && " · dashed tiles are its input dependencies"}
        {" · "}Main phase: <strong>{overview.main_phase ?? "—"}</strong>
      </p>
      <div className="phases">
        {overview.workflow.phases.map((phase) => {
          const inScope = phase.subphases.some((s) => scope.has(s));
          const plan = overview.phase_plans[phase.id];
          return (
            <section
              key={phase.id}
              className={["phase", !inScope && "out", overview.main_phase === phase.id && "main"].filter(Boolean).join(" ")}
            >
              <h3>
                <span className="num">{phase.id}</span> {phase.title}
              </h3>
              <div className="phase-meta">
                {overview.phase_reviews[phase.id] ? (
                  <StatusChip status="accepted" label="Closed" />
                ) : plan ? (
                  <StatusChip
                    status={plan.approved_by ? "ready" : "awaiting_plan_approval"}
                    label={`Plan v${plan.version} · ${plan.approved_by ? `approved by ${directory.person(plan.approved_by).label}` : "awaiting approval"}`}
                  />
                ) : (
                  <span>{inScope ? "No phase plan yet" : "Outside this run"}</span>
                )}
              </div>
              {phase.subphases.map((sid) => {
                const definition = overview.workflow.subphases[sid];
                const state = statusOf.get(sid);
                const latest = state?.instances.at(-1);
                return (
                  <button
                    key={sid}
                    className={["tile", !scope.has(sid) && !dependencies.has(sid) && "out", dependencies.has(sid) && "dep"].filter(Boolean).join(" ")}
                    onClick={() => setSelected(sid)}
                  >
                    <span className="sid">{sid}</span>
                    <span className="title">{definition.title}</span>
                    <span className="under">
                      <StatusChip status={state?.status ?? "pending"} />
                      <span>{definition.owners.join(" · ")}</span>
                      {latest?.out_of_order && <span className="tag">out of order</span>}
                    </span>
                  </button>
                );
              })}
            </section>
          );
        })}
      </div>
      {selected && (
        <SubphaseDrawer
          sid={selected}
          overview={overview}
          directory={directory}
          onClose={() => setSelected(null)}
          onOpenDocument={onOpenDocument}
        />
      )}
    </div>
  );
}

function SubphaseDrawer({
  sid,
  overview,
  directory,
  onClose,
  onOpenDocument,
}: {
  sid: string;
  overview: Overview;
  directory: Directory;
  onClose: () => void;
  onOpenDocument: (id: string) => void;
}) {
  const definition = overview.workflow.subphases[sid];
  const state = overview.status.phases.flatMap((p) => p.subphases).find((s) => s.id === sid);
  const findings = overview.review.filter((f) => f.subphase === sid || state?.instances.some((a) => a.id === f.activity));
  return (
    <aside className="drawer" aria-label={`Subphase ${sid}`}>
      <header>
        <div>
          <h2>
            {sid} · {definition.title}
          </h2>
          <div className="muted">{definition.slug}</div>
        </div>
        <button className="close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <div className="body">
        <dl className="kv">
          <dt>Owners</dt>
          <dd>{definition.owners.join(", ")}</dd>
          <dt>Specialists</dt>
          <dd>{definition.specialists.join(", ")}</dd>
          <dt>Depends on</dt>
          <dd>{definition.dependencies.join(", ") || "—"}</dd>
          <dt>Deliverable</dt>
          <dd>{definition.deliverable}</dd>
          <dt>Exit criterion</dt>
          <dd>{definition.exit_criteria}</dd>
          <dt>Applicability</dt>
          <dd>{definition.applicability}</dd>
        </dl>
        {findings.length > 0 && (
          <div className="section">
            <h3>Review findings</h3>
            <ul className="plain">
              {findings.map((f, i) => (
                <li key={i}>
                  <strong>{f.code}</strong> {f.dependency && `(${f.dependency})`} {f.action ?? f.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
        {(state?.instances ?? []).length === 0 && <p className="muted section">No activity recorded for this subphase.</p>}
        {(state?.instances ?? []).map((activity) => (
          <ActivityDetail key={activity.id} activity={activity} directory={directory} onOpenDocument={onOpenDocument} />
        ))}
      </div>
    </aside>
  );
}

function ActivityDetail({
  activity,
  directory,
  onOpenDocument,
}: {
  activity: Activity;
  directory: Directory;
  onOpenDocument: (id: string) => void;
}) {
  const plan = activity.plan;
  return (
    <div className="section">
      <h3>
        Activity #{activity.sequence} · <StatusChip status={activity.status} />
      </h3>
      <dl className="kv">
        <dt>Mode</dt>
        <dd>
          {activity.mode}
          {activity.arrangement && ` · ${activity.arrangement}`}
        </dd>
        <dt>Owner</dt>
        <dd>{directory.person(activity.owner).title}</dd>
        {activity.reason && (
          <>
            <dt>Reason</dt>
            <dd>{activity.reason}</dd>
          </>
        )}
        <dt>Plan</dt>
        <dd>
          v{plan.version} ·{" "}
          {plan.approved_by
            ? `approved by ${directory.person(plan.approved_by).label} ${formatTime(plan.approved_at)}`
            : "not approved"}
        </dd>
        <dt>Objective</dt>
        <dd>{plan.objective}</dd>
        <dt>Actions</dt>
        <dd>
          <ul className="plain">
            {plan.actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </dd>
        <dt>Criteria</dt>
        <dd>
          <ul className="plain">
            {plan.criteria.map((c) => (
              <li key={c}>
                {c}
                {activity.criteria_evidence[c] && <div className="muted">evidence: {activity.criteria_evidence[c]}</div>}
              </li>
            ))}
          </ul>
        </dd>
        {plan.assumptions.length > 0 && (
          <>
            <dt>Assumptions</dt>
            <dd>{plan.assumptions.join("; ")}</dd>
          </>
        )}
        {plan.missing_dependencies.length > 0 && (
          <>
            <dt>Missing inputs</dt>
            <dd>{plan.missing_dependencies.join(", ")}</dd>
          </>
        )}
        <dt>Inputs</dt>
        <dd>{Object.keys(plan.inputs).length ? Object.keys(plan.inputs).map((r) => <code key={r}>{r.slice(0, 8)} </code>) : "—"}</dd>
        <dt>Outputs</dt>
        <dd>
          {activity.outputs.length
            ? activity.outputs.map((r) => (
                <button key={r} className="tag" onClick={() => onOpenDocument(r)}>
                  {r.slice(0, 8)}
                </button>
              ))
            : "—"}
        </dd>
        <dt>Domain reviews</dt>
        <dd>
          {Object.keys(activity.domain_reviews).length
            ? Object.entries(activity.domain_reviews).map(([role, evidence]) => (
                <div key={role}>
                  <strong>{role}</strong> ✓ {evidence.split(": ").slice(1).join(": ")}
                </div>
              ))
            : "—"}
        </dd>
        <dt>Human review</dt>
        <dd>{activity.human_review ?? "—"}</dd>
      </dl>
    </div>
  );
}
