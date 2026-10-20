import type { NodeProps } from "@xyflow/react";
import { Handles } from "./Handles";
import { StatusDot } from "./StatusChip";
import { type CardData, cardClass, cardStyle, initials, lastAction } from "./cardData";

export function SpecialistCard({ data }: NodeProps) {
  const d = data as CardData;
  const definition = d.node.definition!;
  const [role] = definition.name.split(" — ");
  const latest = d.node.instances.flatMap((i) => i.activities).at(-1);
  const subphase = definition.subphases[0];
  const last = lastAction(d);
  return (
    <div className={cardClass(d)} style={cardStyle(d)}>
      <Handles />
      <div className="card-top">
        <div className="monogram small">{initials(role)}</div>
        <div className="card-heading">
          <div className="card-role" title={role}>
            {role}
          </div>
          <div className="card-sub">Subphase {subphase}</div>
        </div>
      </div>
      <StatusDot status={d.statuses[subphase] ?? "pending"} />
      <div className="card-foot">
        {latest ? (
          <>
            <span>
              Plan <b>v{latest.plan_version}</b>
            </span>
            <span>
              <b>{latest.outputs.length}</b> {latest.outputs.length === 1 ? "output" : "outputs"}
            </span>
            {last && <span className="right">{last}</span>}
          </>
        ) : (
          <span>{d.node.dimmed ? "Not yet delegated" : "Delegated · no activity yet"}</span>
        )}
      </div>
    </div>
  );
}
