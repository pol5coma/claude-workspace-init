import type { NodeProps } from "@xyflow/react";
import { Handles } from "./Handles";
import { StatusDot } from "./StatusChip";
import { type CardData, cardClass, cardStyle, lastAction } from "./cardData";

const VISIBLE = 6;

export function OfficerCard({ data }: NodeProps) {
  const d = data as CardData;
  const definition = d.node.definition!;
  const reviews = d.node.instances.flatMap((i) => i.reviews);
  const approved = reviews.filter((r) => r.decision === "approved").length;
  const changes = reviews.filter((r) => r.decision === "changes_requested").length;
  const owned = definition.scope_subphases;
  const last = lastAction(d);
  return (
    <div className={cardClass(d)} style={cardStyle(d)}>
      <Handles />
      <div className="card-top">
        <div className="monogram">{definition.acronym.slice(1, -2)}</div>
        <div className="card-heading">
          <div className="card-name">
            {definition.acronym}
            {definition.traditional && <small>{definition.traditional}</small>}
          </div>
          <div className="card-sub">{definition.name.replace(" Agentic Officer", "")}</div>
        </div>
      </div>
      <div className="subphase-dots">
        {owned.slice(0, VISIBLE).map((sid) => (
          <StatusDot key={sid} status={d.statuses[sid] ?? "pending"} label={sid} />
        ))}
        {owned.length > VISIBLE && <span className="dot-label muted">+{owned.length - VISIBLE}</span>}
        {owned.length === 0 && <span className="muted" style={{ fontSize: 12.5 }}>No subphase in scope</span>}
      </div>
      <div className="card-foot">
        {d.node.dimmed ? (
          <span>Not yet delegated</span>
        ) : (
          <>
            <span>
              <b>{approved}</b> approved
            </span>
            <span>
              <b>{changes}</b> changes
            </span>
            {last && <span className="right">{last}</span>}
          </>
        )}
      </div>
    </div>
  );
}
