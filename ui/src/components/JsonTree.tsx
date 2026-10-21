// Collapsible, read-only JSON viewer for database rows.
export function JsonTree({ value, name, open = false }: { value: unknown; name?: string; open?: boolean }) {
  const key = name !== undefined ? <span className="k">{name}: </span> : null;
  if (value === null || typeof value !== "object") {
    const cls = typeof value === "string" ? "s" : "n";
    return (
      <div>
        {key}
        <span className={cls}>{JSON.stringify(value)}</span>
      </div>
    );
  }
  const entries = Array.isArray(value) ? value.map((v, i) => [String(i), v] as const) : Object.entries(value);
  const brackets = Array.isArray(value) ? ["[", "]"] : ["{", "}"];
  return (
    <details open={open}>
      <summary>
        {key}
        {brackets[0]}
        <span className="muted"> {entries.length} </span>
        {brackets[1]}
      </summary>
      {entries.map(([k, v]) => (
        <JsonTree key={k} name={k} value={v} />
      ))}
    </details>
  );
}
