import { Handle, Position } from "@xyflow/react";

// Invisible connection points on every side; orgchart.handlesFor picks the pair per edge.
export function Handles() {
  const style = { opacity: 0, width: 6, height: 6, border: 0 };
  return (
    <>
      <Handle id="top-in" type="target" position={Position.Top} style={style} />
      <Handle id="top-out" type="source" position={Position.Top} style={style} />
      <Handle id="bottom-in" type="target" position={Position.Bottom} style={style} />
      <Handle id="bottom-out" type="source" position={Position.Bottom} style={style} />
      <Handle id="left-in" type="target" position={Position.Left} style={style} />
      <Handle id="left-out" type="source" position={Position.Left} style={style} />
      <Handle id="right-in" type="target" position={Position.Right} style={style} />
      <Handle id="right-out" type="source" position={Position.Right} style={style} />
    </>
  );
}
