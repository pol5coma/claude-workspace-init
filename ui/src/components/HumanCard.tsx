import type { NodeProps } from "@xyflow/react";
import { Handles } from "./Handles";
import { type CardData, cardClass, cardStyle } from "./cardData";

export function HumanCard({ data }: NodeProps) {
  const d = data as CardData;
  const pending = d.human?.pending ?? [];
  return (
    <div className={cardClass(d)} style={cardStyle(d)}>
      <Handles />
      <div className="card-top">
        <div className="monogram round">H</div>
        <div className="card-heading">
          <div className="card-name">
            Human <small>{d.human?.mode?.toUpperCase()}</small>
          </div>
          <div className="card-sub">Sets the objective and delegates authority</div>
        </div>
      </div>
      <div className="card-body">{d.human?.objective}</div>
      <div className="card-foot">
        {pending.length ? (
          <>
            <span className="dot-label">
              <span className="dot" style={{ "--dot": "var(--status-awaiting-plan-approval)" } as React.CSSProperties} />
              {pending[0]}
            </span>
            {pending.length > 1 && <span className="right">+{pending.length - 1} more</span>}
          </>
        ) : (
          <span className="dot-label">
            <span className="dot" style={{ "--dot": "var(--status-accepted)" } as React.CSSProperties} />
            Nothing waiting on you
          </span>
        )}
      </div>
    </div>
  );
}
