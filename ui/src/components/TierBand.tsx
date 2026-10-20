import type { NodeProps } from "@xyflow/react";

export type BandData = { label: string };

// Background band labelling one level of the C-organization.
export function TierBand({ data }: NodeProps) {
  const { label } = data as BandData;
  return (
    <div className="band">
      <span className="band-label">{label}</span>
    </div>
  );
}
