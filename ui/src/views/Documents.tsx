import { diffLines } from "diff";
import { useState } from "react";
import Markdown from "react-markdown";
import { type Revision, type RevisionMeta, useRunData } from "../api";
import { StatusDot } from "../components/StatusChip";
import type { Directory } from "../lib/people";
import { formatTime } from "../lib/status";

type Props = {
  runId: string;
  pulse: string;
  documents: RevisionMeta[];
  selected: string | null;
  onSelect: (id: string) => void;
  directory: Directory;
};

export function Documents({ runId, pulse, documents, selected, onSelect, directory }: Props) {
  const [compare, setCompare] = useState(false);
  const current = documents.find((d) => d.id === selected) ?? documents.at(-1);
  const revision = useRunData<Revision>(runId, current ? `/documents/${current.id}` : "/documents", pulse);
  const previous = useRunData<Revision>(runId, current?.supersedes ? `/documents/${current.supersedes}` : "/documents", pulse);
  const superseded = new Set(documents.map((d) => d.supersedes).filter(Boolean));
  const byPath = new Map<string, RevisionMeta[]>();
  documents.forEach((d) => byPath.set(d.path, [...(byPath.get(d.path) ?? []), d]));

  if (!documents.length) return <div className="empty">No documents recorded in this run yet.</div>;
  const content = current && revision.data && "content" in revision.data ? revision.data : null;
  const before = current?.supersedes && previous.data && "content" in previous.data ? previous.data : null;

  return (
    <div className="split">
      <nav className="list" aria-label="Documents">
        {[...byPath.entries()].map(([path, revisions]) => (
          <div key={path}>
            <div className="group">{path}</div>
            {[...revisions].reverse().map((d) => (
              <button key={d.id} className={d.id === current?.id ? "active" : ""} onClick={() => onSelect(d.id)}>
                <span className="row-title">
                  Revision {d.sequence}
                  <StatusDot
                    status={d.official ? "accepted" : superseded.has(d.id) ? "not_applicable" : "awaiting_review"}
                    label={d.official ? "Official" : superseded.has(d.id) ? "Superseded" : "Candidate"}
                  />
                </span>
                <div className="sub">
                  {directory.person(d.author).title.split(" — ")[0]} · {formatTime(d.created_at)}
                </div>
              </button>
            ))}
          </div>
        ))}
      </nav>
      <div className="scroll">
        {current && (
          <div className="doc">
            <div className="doc-head">
              <span className="path">{current.path}</span>
              <span className="tag">Revision {current.sequence}</span>
              <span className="tag">{current.approved_by ? `Promoted by ${directory.person(current.approved_by).label}` : "Not promoted"}</span>
              <span className="tag" title={current.digest}>
                SHA-256 {current.digest.slice(0, 8)}
              </span>
              {current.supersedes && (
                <label className="tag">
                  <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} /> compare with previous
                </label>
              )}
            </div>
            <div className="section markdown">
              {!content ? (
                <p className="muted">Loading…</p>
              ) : compare && before ? (
                <pre>
                  {diffLines(before.content, content.content).map((part, i) => (
                    <span key={i} className={part.added ? "diff-add" : part.removed ? "diff-del" : undefined}>
                      {part.value}
                    </span>
                  ))}
                </pre>
              ) : (
                <Markdown>{content.content}</Markdown>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
