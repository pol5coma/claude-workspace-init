import type { NodeProps } from "@xyflow/react";
import { Handles } from "./Handles";
import { type CardData, cardClass, cardStyle, count, lastAction } from "./cardData";

export function OrchestratorCard({ data }: NodeProps) {
  const d = data as CardData;
  const last = lastAction(d);
  return (
    <div className={cardClass(d)} style={cardStyle(d)}>
      <Handles />
      <div className="card-top">
        <div className="monogram">AO</div>
        <div className="card-heading">
          <div className="card-name">CAOAO</div>
          <div className="card-sub">Chief Agent Orchestrator Agentic Officer</div>
        </div>
        <span className="tag">{d.orchestrator?.scope}</span>
      </div>
      <div className="card-sub" style={{ marginTop: -2 }}>
        {last ? `Last: ${last}` : "Waiting for delegation"}
      </div>
      <div className="metrics">
        <div className="metric">
          <strong>{count(d, "prepare") + count(d, "phase_plan") + count(d, "revise_plan")}</strong>
          <span>Plans</span>
        </div>
        <div className="metric">
          <strong>{count(d, "delegation")}</strong>
          <span>Delegations</span>
        </div>
        <div className="metric">
          <strong>{count(d, "accept")}</strong>
          <span>Accepted</span>
        </div>
        <div className="metric">
          <strong>{d.orchestrator?.mainPhase ?? "—"}</strong>
          <span>Main phase</span>
        </div>
      </div>
    </div>
  );
}
