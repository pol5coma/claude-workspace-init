import { useEffect, useMemo, useRef, useState } from "react";
import {
  type Messages,
  type Organization,
  type Overview,
  pulseKey,
  type RevisionMeta,
  usePulse,
  useRunData,
  useRuns,
  useSource,
} from "./api";
import { Directory } from "./lib/people";
import { formatTime } from "./lib/status";
import { COrganization } from "./views/COrganization";
import { Communication } from "./views/Communication";
import { Database } from "./views/Database";
import { Documents } from "./views/Documents";
import { Workflow } from "./views/Workflow";

const TABS = [
  ["org", "C-Organization"],
  ["workflow", "Workflow"],
  ["communication", "Communication"],
  ["documents", "Documents"],
  ["database", "Database"],
] as const;
type Tab = (typeof TABS)[number][0];

function readHash(): { run?: string; tab?: Tab } {
  const params = new URLSearchParams(window.location.hash.slice(1));
  return { run: params.get("run") ?? undefined, tab: (params.get("tab") as Tab) ?? undefined };
}

export function App() {
  const runs = useRuns();
  const source = useSource();
  const initial = readHash();
  const [runId, setRunId] = useState<string | undefined>(initial.run);
  const [tab, setTab] = useState<Tab>(initial.tab ?? "org");
  const list = runs.data ?? [];
  const current = runId && list.some((r) => r.id === runId) ? runId : list.at(-1)?.id;

  useEffect(() => {
    if (current) window.history.replaceState(null, "", `#run=${current}&tab=${tab}`);
  }, [current, tab]);

  if (runs.error) {
    return <div className="empty">Cannot read SPADO state: {String(runs.error.message)}</div>;
  }
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">S</span>
          SPADO <small>C-Organization</small>
        </div>
        {list.length > 0 && (
          <select value={current} onChange={(e) => setRunId(e.target.value)} aria-label="Run">
            {[...list].reverse().map((r) => (
              <option key={r.id} value={r.id}>
                {r.scope.kind === "workflow" ? "Full workflow" : `${r.scope.kind[0].toUpperCase()}${r.scope.kind.slice(1)} ${r.scope.id}`} —{" "}
                {r.objective.slice(0, 44)}
              </option>
            ))}
          </select>
        )}
        <span className="spacer" />
        <span className="source" title={source.data?.label}>
          {source.data?.label === "demo" ? "Demo data" : source.data?.label.split("/").filter(Boolean).at(-1)}
          {" · read-only"}
        </span>
      </header>
      {!current ? (
        <div className="empty" style={{ gridRow: "2 / 4" }}>
          {runs.isLoading ? (
            "Loading…"
          ) : (
            <>
              <h2>No runs yet</h2>
              <p>
                Start one from your host, e.g. <code>/spdlc --new-run --subphase initial-ideation --mode semi-auto</code>. This page
                updates automatically.
              </p>
            </>
          )}
        </div>
      ) : (
        <RunView key={current} runId={current} tab={tab} setTab={setTab} />
      )}
    </div>
  );
}

function RunView({ runId, tab, setTab }: { runId: string; tab: Tab; setTab: (t: Tab) => void }) {
  const pulse = usePulse(runId);
  const key = pulseKey(pulse.data);
  const overview = useRunData<Overview>(runId, "", key);
  const org = useRunData<Organization>(runId, "/organization", key);
  const messages = useRunData<Messages>(runId, "/messages", key);
  const documents = useRunData<RevisionMeta[]>(runId, "/documents", key);
  const [document, setDocument] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const previous = useRef(key);

  useEffect(() => {
    if (previous.current !== key && previous.current !== "initial") {
      setLive(true);
      const timer = setTimeout(() => setLive(false), 2600);
      previous.current = key;
      return () => clearTimeout(timer);
    }
    previous.current = key;
  }, [key]);

  const directory = useMemo(
    () => new Directory(org.data?.definitions ?? [], messages.data?.actors ?? org.data?.instances ?? []),
    [org.data, messages.data],
  );
  const openDocument = (id: string) => {
    setDocument(id);
    setTab("documents");
  };
  const o = overview.data;
  const error = overview.error ?? org.error;

  return (
    <>
      <section className="hero">
        <div className="hero-text">
          {o && (
            <>
              <div className="eyebrow">
                {o.scope.kind === "workflow" ? "Full workflow" : `${o.scope.kind} ${o.scope.id}`} ·{" "}
                {o.workflow.title.split("(")[0].trim()}
              </div>
              <h1 title={o.objective}>{o.objective}</h1>
              <div className="meta">
                <span className="pill accent">{o.mode}</span>
                <span className="pill" title="Run version: one per recorded transition">
                  Version {o.version}
                </span>
                <span className="pill" title="Recorded state, not live process telemetry">
                  <span className={`live ${live ? "pulsing" : ""}`} />
                  Updated {formatTime(o.updated_at)}
                </span>
              </div>
            </>
          )}
        </div>
        <nav className="segmented" aria-label="Views">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </section>
      <main className="content">
        {error ? (
          <div className="empty">Cannot read this run: {String(error.message)}</div>
        ) : !o || !org.data ? (
          <div className="empty">Loading run…</div>
        ) : tab === "org" ? (
          <COrganization
            overview={o}
            org={org.data}
            messages={messages.data}
            documents={documents.data}
            directory={directory}
            onOpenDocument={openDocument}
          />
        ) : tab === "workflow" ? (
          <Workflow overview={o} directory={directory} onOpenDocument={openDocument} />
        ) : tab === "communication" ? (
          messages.data ? <Communication messages={messages.data} directory={directory} /> : <div className="empty">Loading…</div>
        ) : tab === "documents" ? (
          <Documents
            runId={runId}
            pulse={key}
            documents={documents.data ?? []}
            selected={document}
            onSelect={setDocument}
            directory={directory}
          />
        ) : (
          <Database runId={runId} pulse={key} directory={directory} />
        )}
      </main>
    </>
  );
}
