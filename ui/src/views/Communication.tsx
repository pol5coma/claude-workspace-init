import { useEffect, useMemo, useRef, useState } from "react";
import type { Message, Messages } from "../api";
import { JsonTree } from "../components/JsonTree";
import { fitLaneWidth, HEADER, layoutLanes, ROW_HEIGHT } from "../lib/lanes";

const HEAD = HEADER - 16; // sticky lane-header height
import type { Directory } from "../lib/people";
import { formatTime, kindColor } from "../lib/status";

type Props = { messages: Messages; directory: Directory };
type View = "sequence" | "chat";

export function Communication({ messages, directory }: Props) {
  const [view, setView] = useState<View>("sequence");
  const [member, setMember] = useState("");
  const [kind, setKind] = useState("");
  const [subphase, setSubphase] = useState("");
  const [sources, setSources] = useState({ db: true, transcript: true });
  const [open, setOpen] = useState<Message | null>(null);

  const all = messages.messages;
  const members = useMemo(() => {
    const seen = new Map<string, string>();
    all.forEach((m) => [m.from, ...m.to].forEach((ref) => {
      const p = directory.person(ref);
      seen.set(p.definition, p.label);
    }));
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [all, directory]);
  const kinds = useMemo(() => [...new Set(all.map((m) => m.kind))].sort(), [all]);
  const subphases = useMemo(() => [...new Set(all.map((m) => m.subphase).filter(Boolean) as string[])].sort(), [all]);

  const filtered = all.filter(
    (m) =>
      sources[m.source] &&
      (!kind || m.kind === kind) &&
      (!subphase || m.subphase === subphase) &&
      (!member || [m.from, ...m.to].some((ref) => directory.person(ref).definition === member)),
  );

  return (
    <div className="comm">
      <div className="filters">
        <div className="toggle" role="tablist">
          {(["sequence", "chat"] as View[]).map((v) => (
            <button key={v} className={view === v ? "on" : ""} onClick={() => setView(v)}>
              {v === "sequence" ? "Sequence" : "Chat"}
            </button>
          ))}
        </div>
        <select value={member} onChange={(e) => setMember(e.target.value)} aria-label="Member">
          <option value="">All members</option>
          {members.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind">
          <option value="">All kinds</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select value={subphase} onChange={(e) => setSubphase(e.target.value)} aria-label="Subphase">
          <option value="">All subphases</option>
          {subphases.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <label>
          <input type="checkbox" checked={sources.db} onChange={(e) => setSources({ ...sources, db: e.target.checked })} />{" "}
          Database events
        </label>
        <label>
          <input
            type="checkbox"
            checked={sources.transcript}
            onChange={(e) => setSources({ ...sources, transcript: e.target.checked })}
            disabled={!messages.transcripts.available}
          />{" "}
          Transcripts {!messages.transcripts.available && <span className="muted">(not found)</span>}
        </label>
        <span className="count">{filtered.length} messages</span>
      </div>
      <div className="scroll">
        {filtered.length === 0 ? (
          <div className="empty">No messages match these filters.</div>
        ) : view === "sequence" ? (
          <SequenceDiagram messages={filtered} directory={directory} onOpen={setOpen} />
        ) : (
          <Chat messages={filtered} directory={directory} onOpen={setOpen} />
        )}
      </div>
      {open && <MessageDrawer message={open} directory={directory} onClose={() => setOpen(null)} />}
    </div>
  );
}

function SequenceDiagram({ messages, directory, onOpen }: { messages: Message[]; directory: Directory; onOpen: (m: Message) => void }) {
  const [available, setAvailable] = useState(1200);
  // Message labels on the left, lanes to their right; both shrink to fit the panel.
  const labelWidth = Math.round(Math.max(220, Math.min(300, available * 0.22)));
  const probe = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = probe.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setAvailable(element.clientWidth));
    observer.observe(element);
    setAvailable(element.clientWidth);
    return () => observer.disconnect();
  }, []);
  const laneCount = layoutLanes(messages, directory).lanes.length;
  const laneWidth = fitLaneWidth(available - labelWidth, laneCount);
  const layout = layoutLanes(messages, directory, laneWidth);
  const maxLabel = Math.floor(laneWidth / 7.2);
  const width = layout.width + labelWidth;
  return (
    <div ref={probe}>
    {/* Lane headers stay visible while scrolling through long runs. */}
    <svg className="sequence sequence-head" width={width} height={HEAD} aria-hidden="true">
      <g transform={`translate(${labelWidth}, 0)`}>
        {layout.lanes.map((lane) => (
          <g key={lane.key} className="lane-head">
            <rect x={lane.x - laneWidth / 2 + 5} y={6} width={laneWidth - 10} height={36} rx={10} />
            <text x={lane.x} y={22} textAnchor="middle" fontWeight={600}>
              {lane.person.label.length > maxLabel ? `${lane.person.label.slice(0, maxLabel - 1)}…` : lane.person.label}
            </text>
            <text x={lane.x} y={36} textAnchor="middle" fill="var(--muted)" style={{ fontSize: 10 }}>
              {lane.person.level}
            </text>
          </g>
        ))}
      </g>
    </svg>
    <svg
      className="sequence"
      width={width}
      height={layout.height - HEAD}
      viewBox={`0 ${HEAD} ${width} ${layout.height - HEAD}`}
      role="img"
      aria-label="Sequence diagram"
    >
      <g transform={`translate(${labelWidth}, 0)`}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="context-stroke" />
        </marker>
      </defs>
      {layout.lanes.map((lane) => (
        <line key={lane.key} className="lane-line" x1={lane.x} x2={lane.x} y1={HEAD} y2={layout.height} />
      ))}
      {layout.rows.map((row) => {
        const color = kindColor(row.message.kind, row.message.category);
        return (
          <g key={row.message.id} className="row" onClick={() => onOpen(row.message)} style={{ cursor: "pointer" }}>
            <rect x={-labelWidth} y={row.y - ROW_HEIGHT / 2} width={layout.width + labelWidth} height={ROW_HEIGHT} fill="transparent" />
            {row.to.length === 0 && <circle cx={row.from} cy={row.y} r={5} fill={color} />}
            {row.to.map((x, i) => (
              <line
                key={i}
                x1={row.from}
                x2={x + (x > row.from ? -6 : 6)}
                y1={row.y}
                y2={row.y}
                stroke={color}
                strokeWidth={row.message.source === "transcript" ? 1.4 : 2}
                strokeDasharray={row.message.source === "transcript" ? "5 4" : undefined}
                markerEnd="url(#arrow)"
              />
            ))}
            <circle cx={row.from} cy={row.y} r={3.5} fill={color} />
            <text x={-labelWidth + 8} y={row.y - 3}>
              <tspan fontWeight={600} fill={color}>
                {row.message.kind.replace(/_/g, " ")}
              </tspan>
              <tspan fill="var(--muted)"> · {formatTime(row.message.timestamp)}</tspan>
            </text>
            <text x={-labelWidth + 8} y={row.y + 12} fill="var(--muted)">
              {row.message.summary.length > labelWidth / 6.8 ? `${row.message.summary.slice(0, Math.floor(labelWidth / 6.8) - 1)}…` : row.message.summary}
            </text>
          </g>
        );
      })}
      </g>
    </svg>
    </div>
  );
}

function Chat({ messages, directory, onOpen }: { messages: Message[]; directory: Directory; onOpen: (m: Message) => void }) {
  return (
    <div className="chat">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`bubble ${m.source}`}
          style={{ "--kind-color": kindColor(m.kind, m.category) } as React.CSSProperties}
          onClick={() => onOpen(m)}
        >
          <div className="bubble-head">
            <span className="who">{directory.person(m.from).label}</span>
            <span className="muted">→ {m.to.map((t) => directory.person(t).label).join(", ") || "—"}</span>
            <span className="tag" style={{ color: kindColor(m.kind, m.category) }}>
              {m.kind.replace(/_/g, " ")}
            </span>
            {m.subphase && <span className="tag">{m.subphase}</span>}
            {m.source === "transcript" && <span className="tag">transcript</span>}
            <span className="muted" style={{ marginLeft: "auto" }}>
              {formatTime(m.timestamp)}
            </span>
          </div>
          <div className="bubble-body">{m.summary}</div>
        </div>
      ))}
    </div>
  );
}

function MessageDrawer({ message, directory, onClose }: { message: Message; directory: Directory; onClose: () => void }) {
  return (
    <aside className="drawer" aria-label="Message">
      <header>
        <div>
          <h2>{message.kind.replace(/_/g, " ")}</h2>
          <div className="muted">
            {directory.person(message.from).title} → {message.to.map((t) => directory.person(t).title).join(", ") || "—"}
          </div>
        </div>
        <button className="close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <div className="body">
        <dl className="kv">
          <dt>When</dt>
          <dd>{formatTime(message.timestamp)}</dd>
          <dt>Source</dt>
          <dd>{message.source === "db" ? "spado_events (database)" : `Claude Code transcript · ${message.session}`}</dd>
          {message.subphase && (
            <>
              <dt>Subphase</dt>
              <dd>{message.subphase}</dd>
            </>
          )}
          <dt>Summary</dt>
          <dd>{message.summary}</dd>
          {message.rationale && (
            <>
              <dt>Rationale</dt>
              <dd>{message.rationale}</dd>
            </>
          )}
        </dl>
        {message.text && (
          <div className="section">
            <h3>{message.kind === "delegation_prompt" ? "Prompt sent to the agent" : "Text"}</h3>
            <pre>{message.text}</pre>
          </div>
        )}
        {message.payload && (
          <div className="section json">
            <h3>Payload</h3>
            <JsonTree value={message.payload} open />
          </div>
        )}
        {message.result && (
          <div className="section json">
            <h3>Result</h3>
            <JsonTree value={message.result} open />
          </div>
        )}
      </div>
    </aside>
  );
}
