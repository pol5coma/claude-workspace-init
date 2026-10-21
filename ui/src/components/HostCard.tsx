import type { NodeProps } from "@xyflow/react";
import { Handles } from "./Handles";
import { type CardData, cardClass, cardStyle } from "./cardData";

// The Claude Code session the Human talks to; known only from local transcripts.
export function HostCard({ data }: NodeProps) {
  const d = data as CardData;
  return (
    <div className={cardClass(d)} style={cardStyle(d)}>
      <Handles />
      <div className="card-top">
        <div className="monogram round" style={{ fontFamily: "var(--sans)", fontSize: 20 }}>
          ✳
        </div>
        <div className="card-heading">
          <div className="card-name" style={{ fontSize: 18 }}>
            Claude Code
          </div>
          <div className="card-sub">Host session · from transcripts</div>
        </div>
      </div>
      <div className="metrics" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="metric">
          <strong>{d.host?.prompts ?? 0}</strong>
          <span>Prompts</span>
        </div>
        <div className="metric">
          <strong>{d.host?.delegations ?? 0}</strong>
          <span>Delegations</span>
        </div>
        <div className="metric">
          <strong>{d.host?.reports ?? 0}</strong>
          <span>Reports</span>
        </div>
      </div>
    </div>
  );
}
