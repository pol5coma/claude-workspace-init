import type { Messages, Organization, RevisionMeta } from "../api";
import { type Directory, domainColor, HOST } from "../lib/people";
import { formatTime, kindColor, shortId } from "../lib/status";
import { initials } from "./cardData";
import { StatusDot } from "./StatusChip";

type Props = {
  nodeId: string;
  org: Organization;
  messages: Messages | undefined;
  documents: RevisionMeta[] | undefined;
  directory: Directory;
  onClose: () => void;
  onOpenDocument?: (id: string) => void;
};

export function ActorPanel({ nodeId, org, messages, documents, directory, onClose, onOpenDocument }: Props) {
  const definition = org.definitions.find((d) => d.id === nodeId);
  const instances = org.instances.filter((i) => i.definition === nodeId);
  const ids = new Set(nodeId === HOST ? [HOST] : instances.map((i) => i.id).concat(`def:${nodeId}`));
  const related = (messages?.messages ?? []).filter((m) => ids.has(m.from) || m.to.some((t) => ids.has(t)));
  const threads = (messages?.threads ?? []).filter((t) => ids.has(t.actor));
  const authored = (documents ?? []).filter((d) => ids.has(d.author));
  const activities = instances.flatMap((i) => i.activities);
  const reviews = instances.flatMap((i) => i.reviews);
  const isHost = nodeId === HOST;
  const color = isHost ? "var(--accent)" : domainColor(definition);
  const level = definition?.level;
  const title = isHost
    ? "Claude Code"
    : level === "specialist"
      ? definition!.name.split(" — ")[0]
      : (definition?.acronym ?? nodeId);
  const monogram = isHost
    ? "✳"
    : level === "officer"
      ? definition!.acronym.slice(1, -2)
      : level === "orchestrator"
        ? "AO"
        : level === "human"
          ? "H"
          : initials(title);

  return (
    <aside className="drawer" aria-label={`${title} details`} style={{ "--card-color": color } as React.CSSProperties}>
      <header>
        <div
          className={`monogram ${level === "human" || isHost ? "round" : ""}`}
          style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}
        >
          {monogram}
        </div>
        <div>
          <h2>
            {title}
            {definition?.traditional && (
              <span className="muted" style={{ fontFamily: "var(--sans)", fontSize: 12, marginLeft: 8 }}>
                {definition.traditional}
              </span>
            )}
          </h2>
          <div className="muted">{isHost ? "Host session, reconstructed from local transcripts" : definition?.name}</div>
        </div>
        <button className="close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <div className="body">
        {definition && (
          <div className="section">
            <h3>Mandate</h3>
            <p>{definition.mandate}</p>
          </div>
        )}
        {definition && definition.level !== "human" && (
          <div className="section">
            <dl className="kv">
              <dt>Reports to</dt>
              <dd>{definition.reports_to.join(", ") || "—"}</dd>
              <dt>In this run</dt>
              <dd>{definition.scope_subphases.length ? `Subphases ${definition.scope_subphases.join(", ")}` : "—"}</dd>
              <dt>Skills</dt>
              <dd>{definition.skills.join(", ") || "—"}</dd>
            </dl>
          </div>
        )}

        {!isHost && (
          <div className="section">
            <h3>Identities</h3>
            {instances.length === 0 && <p className="muted">Not delegated in this run yet.</p>}
            <div className="stack">
              {instances.map((instance) => (
                <div className="item" key={instance.id}>
                  <dl className="kv">
                    <dt>Actor</dt>
                    <dd>
                      <code>{shortId(instance.id)}</code>
                    </dd>
                    <dt>Delegated by</dt>
                    <dd>{instance.parent_id ? directory.person(instance.parent_id).title : "—"}</dd>
                    <dt>Events</dt>
                    <dd>{instance.event_count}</dd>
                    <dt>Last action</dt>
                    <dd>
                      {instance.last_event
                        ? `${instance.last_event.kind.replace(/_/g, " ")} · ${formatTime(instance.last_event.timestamp)}`
                        : "—"}
                    </dd>
                  </dl>
                </div>
              ))}
            </div>
          </div>
        )}

        {activities.length > 0 && (
          <div className="section">
            <h3>Activities</h3>
            <div className="stack">
              {activities.map((a) => (
                <div className="item" key={a.id} style={{ display: "flex", gap: 14, alignItems: "center" }}>
                  <strong style={{ color: "var(--text)" }}>{a.subphase}</strong>
                  <StatusDot status={a.status} />
                  <span className="muted" style={{ marginLeft: "auto" }}>
                    Plan v{a.plan_version} · {a.outputs.length} {a.outputs.length === 1 ? "output" : "outputs"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {reviews.length > 0 && (
          <div className="section">
            <h3>Reviews given</h3>
            <div className="stack">
              {reviews.map((r) => (
                <div className="item" key={`${r.activity}-${r.timestamp}`}>
                  <div className="when">
                    <StatusDot
                      status={r.decision === "approved" ? "accepted" : "blocked"}
                      label={r.decision === "approved" ? "Approved" : "Changes requested"}
                    />
                    {r.subphase && <span>· {r.subphase}</span>}
                    <span>· {formatTime(r.timestamp)}</span>
                  </div>
                  {r.evidence}
                </div>
              ))}
            </div>
          </div>
        )}

        {authored.length > 0 && (
          <div className="section">
            <h3>Documents written</h3>
            <div className="stack">
              {authored.map((doc) => (
                <button
                  key={doc.id}
                  className="item"
                  style={{ textAlign: "left", display: "flex", gap: 10, alignItems: "center" }}
                  onClick={() => onOpenDocument?.(doc.id)}
                >
                  <code>{doc.path}</code>
                  <span className="muted">r{doc.sequence}</span>
                  {doc.official && <StatusDot status="accepted" label="Official" />}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="section">
          <h3>Communication · {related.length}</h3>
          {related.length === 0 && <p className="muted">No messages yet.</p>}
          <div className="stack">
            {related.slice(-40).map((m) => {
              const outgoing = ids.has(m.from);
              const other = outgoing
                ? m.to.map((t) => directory.person(t).label).join(", ") || "—"
                : directory.person(m.from).label;
              return (
                <div className="item" key={m.id} style={{ borderLeft: `3px solid ${kindColor(m.kind, m.category)}` }}>
                  <div className="when">
                    {outgoing ? "To" : "From"} <strong style={{ color: "var(--text)" }}>{other}</strong>
                    <span>· {m.kind.replace(/_/g, " ")}</span>
                    {m.source === "transcript" && <span>· transcript</span>}
                    <span style={{ marginLeft: "auto" }}>{formatTime(m.timestamp)}</span>
                  </div>
                  {m.summary}
                </div>
              );
            })}
          </div>
        </div>

        {threads.map((thread) => (
          <div className="section" key={thread.agent}>
            <h3>Transcript · {thread.description || thread.subagent_type}</h3>
            <div className="stack">
              {thread.messages.map((item, index) => (
                <details className="item" key={index}>
                  <summary>
                    <span className="tag" style={{ marginRight: 8 }}>
                      {item.tool ?? item.role}
                    </span>
                    {item.text.slice(0, 80)}
                  </summary>
                  <pre style={{ marginTop: 10 }}>{item.text}</pre>
                </details>
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
