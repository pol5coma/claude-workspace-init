import type { Status } from "../api";
import { STATUS_LABEL, statusVar } from "../lib/status";

/** A soft status dot with an optional label. */
export function StatusDot({ status, label }: { status: Status; label?: string | null }) {
  return (
    <span className="dot-label" title={STATUS_LABEL[status]}>
      <span className="dot" style={{ "--dot": statusVar(status) } as React.CSSProperties} />
      {label === null ? null : (label ?? STATUS_LABEL[status])}
    </span>
  );
}

export { StatusDot as StatusChip };
