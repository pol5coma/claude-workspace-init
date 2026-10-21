// Deterministic tiered layout of the C-organization: Human → CAOAO → C-suite → specialists.
// Specialists hang under their primary officer (first owner of their subphase), so the chart
// always reads the same way, unlike a force layout.
import type { Definition, Instance, Organization } from "../api";

export type NodeKind = "human" | "host" | "orchestrator" | "officer" | "specialist";
export type EdgeKind = "reports" | "secondary" | "delegation" | "session";

export type ChartNode = {
  id: string;
  kind: NodeKind;
  x: number;
  y: number;
  width: number;
  height: number;
  definition?: Definition;
  instances: Instance[];
  dimmed: boolean;
  column?: string;
};

export type ChartEdge = { id: string; source: string; target: string; kind: EdgeKind };
export type Band = { level: string; label: string; y: number; height: number };
export type Chart = { nodes: ChartNode[]; edges: ChartEdge[]; bands: Band[]; width: number; height: number };

export const SIZE: Record<NodeKind, { width: number; height: number }> = {
  human: { width: 380, height: 170 },
  host: { width: 270, height: 150 },
  orchestrator: { width: 430, height: 190 },
  officer: { width: 276, height: 188 },
  specialist: { width: 264, height: 146 },
};

const COLUMN_GAP = 36;
const STACK_GAP = 20;
const BAND_PAD = 52;
const BAND_GAP = 40;
const HOST_GAP = 84;

export type LayoutOptions = { showAll: boolean; includeHost: boolean };

function naturalSubphase(definition: Definition): number[] {
  return (definition.subphases[0] ?? "99").split(".").map(Number);
}

function compareSubphase(a: Definition, b: Definition): number {
  const [x, y] = [naturalSubphase(a), naturalSubphase(b)];
  return x[0] - y[0] || (x[1] ?? 0) - (y[1] ?? 0) || a.id.localeCompare(b.id);
}

/**
 * The officer column each specialist is drawn under. A specialist reports to every owner of its
 * subphase; it hangs from the least-loaded visible owner (ties: brief order) so columns stay
 * balanced, and dashed lines connect it to the other owners. Without a visible owner: CAOAO.
 */
export function assignColumns(specialists: Definition[], visibleOfficers: string[]): Map<string, string> {
  const load = new Map(visibleOfficers.map((id) => [id, 0]));
  const assignment = new Map<string, string>();
  for (const specialist of specialists) {
    const candidates = specialist.reports_to.filter((id) => load.has(id));
    if (!candidates.length) {
      assignment.set(specialist.id, "CAOAO");
      continue;
    }
    const chosen = candidates.reduce((best, id) => (load.get(id)! < load.get(best)! ? id : best));
    load.set(chosen, load.get(chosen)! + 1);
    assignment.set(specialist.id, chosen);
  }
  return assignment;
}

export function layoutOrgChart(org: Organization, options: LayoutOptions): Chart {
  const instances = new Map<string, Instance[]>();
  for (const instance of org.instances) {
    instances.set(instance.definition, [...(instances.get(instance.definition) ?? []), instance]);
  }
  const delegated = (id: string) => (instances.get(id)?.length ?? 0) > 0;
  const byId = new Map(org.definitions.map((d) => [d.id, d]));
  const officers = org.definitions.filter(
    (d) => d.level === "officer" && (options.showAll || d.in_scope || delegated(d.id)),
  );
  const visibleOfficers = new Set(officers.map((d) => d.id));
  const specialists = org.definitions
    .filter((d) => d.level === "specialist" && ((d.in_scope && d.scope_subphases.length > 0) || delegated(d.id)))
    .sort(compareSubphase);

  const columns: { id: string; members: Definition[] }[] = officers.map((o) => ({ id: o.id, members: [] }));
  const orphan = { id: "CAOAO", members: [] as Definition[] };
  const assignment = assignColumns(specialists, officers.map((o) => o.id));
  for (const specialist of specialists) {
    const owner = assignment.get(specialist.id)!;
    (columns.find((c) => c.id === owner) ?? orphan).members.push(specialist);
  }
  if (orphan.members.length) columns.push(orphan);

  const columnWidth = Math.max(SIZE.officer.width, SIZE.specialist.width);
  const columnsWidth = columns.length * columnWidth + Math.max(0, columns.length - 1) * COLUMN_GAP;
  const topWidth = SIZE.orchestrator.width + (options.includeHost ? 2 * (HOST_GAP + SIZE.host.width) : 0);
  const width = Math.max(columnsWidth, topWidth, SIZE.human.width);
  const offset = (width - columnsWidth) / 2;
  const center = width / 2;

  const tallest = Math.max(1, ...columns.map((c) => c.members.length));
  const bands: Band[] = [];
  let y = 0;
  for (const [level, label, height] of [
    ["human", "Human", SIZE.human.height],
    ["orchestrator", "Orchestration", SIZE.orchestrator.height],
    ["officer", "C-suite · Chief Agentic Officers", SIZE.officer.height],
    ["specialist", "Specialists", tallest * SIZE.specialist.height + (tallest - 1) * STACK_GAP],
  ] as const) {
    bands.push({ level, label, y, height: height + BAND_PAD + 24 });
    y += height + BAND_PAD + 24 + BAND_GAP;
  }
  const top = (level: string) => bands.find((b) => b.level === level)!.y + BAND_PAD;

  const nodes: ChartNode[] = [];
  const human = byId.get("Human");
  nodes.push({
    id: "Human",
    kind: "human",
    ...SIZE.human,
    x: center - SIZE.human.width / 2,
    y: top("human"),
    definition: human,
    instances: instances.get("Human") ?? [],
    dimmed: false,
  });
  nodes.push({
    id: "CAOAO",
    kind: "orchestrator",
    ...SIZE.orchestrator,
    x: center - SIZE.orchestrator.width / 2,
    y: top("orchestrator"),
    definition: byId.get("CAOAO"),
    instances: instances.get("CAOAO") ?? [],
    dimmed: !delegated("CAOAO"),
  });
  if (options.includeHost) {
    nodes.push({
      id: "host",
      kind: "host",
      ...SIZE.host,
      x: center + SIZE.orchestrator.width / 2 + HOST_GAP,
      y: top("orchestrator") + (SIZE.orchestrator.height - SIZE.host.height) / 2,
      instances: [],
      dimmed: false,
    });
  }
  columns.forEach((column, index) => {
    const x = offset + index * (columnWidth + COLUMN_GAP);
    const officer = byId.get(column.id);
    if (officer && officer.level === "officer") {
      nodes.push({
        id: officer.id,
        kind: "officer",
        ...SIZE.officer,
        x: x + (columnWidth - SIZE.officer.width) / 2,
        y: top("officer"),
        definition: officer,
        instances: instances.get(officer.id) ?? [],
        dimmed: !delegated(officer.id),
        column: column.id,
      });
    }
    column.members.forEach((specialist, row) => {
      nodes.push({
        id: specialist.id,
        kind: "specialist",
        ...SIZE.specialist,
        x: x + (columnWidth - SIZE.specialist.width) / 2,
        y: top("specialist") + row * (SIZE.specialist.height + STACK_GAP),
        definition: specialist,
        instances: instances.get(specialist.id) ?? [],
        dimmed: !delegated(specialist.id),
        column: column.id,
      });
    });
  });

  const present = new Set(nodes.map((n) => n.id));
  const edges: ChartEdge[] = [];
  const add = (source: string, target: string, kind: EdgeKind) => {
    if (present.has(source) && present.has(target)) {
      edges.push({ id: `${kind}:${source}->${target}`, source, target, kind });
    }
  };
  add("Human", "CAOAO", "reports");
  if (options.includeHost) add("Human", "host", "session");
  officers.forEach((o) => add("CAOAO", o.id, "reports"));
  for (const specialist of specialists) {
    const primary = assignment.get(specialist.id)!;
    add(primary, specialist.id, "reports");
    specialist.reports_to
      .filter((id) => id !== primary && visibleOfficers.has(id))
      .forEach((id) => add(id, specialist.id, "secondary"));
  }
  // Actual delegations that bypass the reporting line (e.g. CAOAO assigning a specialist).
  const definitionOf = new Map(org.instances.map((i) => [i.id, i.definition]));
  const seen = new Set<string>();
  for (const instance of org.instances) {
    const parent = instance.parent_id ? definitionOf.get(instance.parent_id) : undefined;
    const child = byId.get(instance.definition);
    if (!parent || !child) continue;
    const expected =
      child.level === "orchestrator" ? "Human" : child.level === "officer" ? "CAOAO" : (assignment.get(child.id) ?? "CAOAO");
    const key = `${parent}->${child.id}`;
    if (parent !== expected && !seen.has(key)) {
      seen.add(key);
      add(parent, child.id, "delegation");
    }
  }
  const last = bands[bands.length - 1];
  return { nodes, edges, bands, width, height: last.y + last.height };
}

/** Handles for an edge between two laid-out nodes: downward, upward or sideways. */
export function handlesFor(source: ChartNode, target: ChartNode): { sourceHandle: string; targetHandle: string } {
  if (source.y + source.height <= target.y) return { sourceHandle: "bottom-out", targetHandle: "top-in" };
  if (target.y + target.height <= source.y) return { sourceHandle: "top-out", targetHandle: "bottom-in" };
  return source.x < target.x
    ? { sourceHandle: "right-out", targetHandle: "left-in" }
    : { sourceHandle: "left-out", targetHandle: "right-in" };
}
