import { Fragment, useState } from "react";
import { type ActorRow, type DbCounts, type EventRow, useRunData } from "../api";
import { JsonTree } from "../components/JsonTree";
import type { Directory } from "../lib/people";
import { formatTime, kindColor, shortId } from "../lib/status";

type Table = "spado_runs" | "spado_events" | "spado_actors" | "spado_embeddings";
const PATHS: Record<Table, string> = {
  spado_runs: "/db/runs",
  spado_events: "/db/events",
  spado_actors: "/db/actors",
  spado_embeddings: "/db/embeddings",
};

export function Database({ runId, pulse, directory }: { runId: string; pulse: string; directory: Directory }) {
  const [table, setTable] = useState<Table>("spado_events");
  const counts = useRunData<DbCounts>(runId, "/db", pulse);
  const rows = useRunData<unknown[]>(runId, PATHS[table], pulse);
  return (
    <div className="split">
      <nav className="list" aria-label="Tables">
        <div className="group">PostgreSQL tables (read-only)</div>
        {(Object.keys(PATHS) as Table[]).map((name) => (
          <button key={name} className={name === table ? "active" : ""} onClick={() => setTable(name)}>
            <code>{name}</code>
            <div className="sub">
              {counts.data ? `${counts.data[name] ?? 0} ${name === "spado_embeddings" ? "chunks" : "rows"} in this run` : "…"}
            </div>
          </button>
        ))}
        <p className="notice" style={{ padding: "10px 14px" }}>
          Credential hashes are never sent to the browser. Rows are scoped to the selected run.
        </p>
      </nav>
      <div className="scroll">
        {!rows.data ? (
          <p className="muted">Loading…</p>
        ) : table === "spado_events" ? (
          <Events rows={rows.data as EventRow[]} directory={directory} />
        ) : table === "spado_actors" ? (
          <Actors rows={rows.data as ActorRow[]} directory={directory} />
        ) : rows.data.length === 0 ? (
          <div className="empty">No rows.</div>
        ) : (
          <div className="json">
            <JsonTree value={table === "spado_runs" ? rows.data[0] : rows.data} name={table === "spado_runs" ? "data" : "rows"} open />
          </div>
        )}
      </div>
    </div>
  );
}

function Events({ rows, directory }: { rows: EventRow[]; directory: Directory }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="table-card">
    <table className="grid">
      <thead>
        <tr>
          <th>#</th>
          <th>created_at</th>
          <th>actor</th>
          <th>kind</th>
          <th>rationale</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <Fragment key={row.id}>
            <tr className="clickable" onClick={() => setOpen(open === row.id ? null : row.id)}>
              <td className="num">{index + 1}</td>
              <td style={{ whiteSpace: "nowrap" }}>{formatTime(row.timestamp)}</td>
              <td>{directory.person(row.actor).label}</td>
              <td style={{ color: kindColor(row.request.kind), fontWeight: 600 }}>{row.request.kind}</td>
              <td>{row.request.rationale}</td>
            </tr>
            {open === row.id && (
              <tr>
                <td colSpan={5} className="json">
                  <JsonTree value={{ id: row.id, actor_id: row.actor, request: row.request, result: row.result }} open />
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
    </div>
  );
}

function Actors({ rows, directory }: { rows: ActorRow[]; directory: Directory }) {
  return (
    <div className="table-card">
    <table className="grid">
      <thead>
        <tr>
          <th>id</th>
          <th>definition</th>
          <th>level</th>
          <th>parent</th>
          <th>subphases</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>
              <code>{shortId(row.id)}</code>
            </td>
            <td>{directory.person(row.id).title}</td>
            <td>{row.level}</td>
            <td>{row.parent_id ? directory.person(row.parent_id).label : "—"}</td>
            <td>{row.subphases?.join(", ") || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
}
