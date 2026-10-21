import type { Status } from "../api";
import type { ChartNode } from "../lib/orgchart";

export type CardData = {
  node: ChartNode;
  color: string;
  statuses: Record<string, Status>;
  flash: boolean;
  selected: boolean;
  human?: { objective: string; mode: string; pending: string[] };
  orchestrator?: { mainPhase: string | null; scope: string };
  host?: { prompts: number; delegations: number; reports: number };
};

export function cardClass(data: CardData): string {
  return ["card", data.node.dimmed && "dimmed", data.flash && "flash", data.selected && "selected"]
    .filter(Boolean)
    .join(" ");
}

export function cardStyle(data: CardData): React.CSSProperties {
  return { "--card-color": data.color } as React.CSSProperties;
}

export function lastAction(data: CardData): string | null {
  const events = data.node.instances.map((i) => i.last_event).filter(Boolean) as { kind: string; timestamp: string }[];
  const last = events.sort((a, b) => a.timestamp.localeCompare(b.timestamp)).at(-1);
  return last ? last.kind.replace(/_/g, " ") : null;
}

export function count(data: CardData, kind: string): number {
  return data.node.instances.reduce((sum, i) => sum + (i.event_kinds[kind] ?? 0), 0);
}

/** "Founder / Business Lead" -> "FB"; "Product Manager" -> "PM". */
export function initials(text: string): string {
  const words = text.split(/[\s/&-]+/).filter((w) => /^[A-Za-z]/.test(w));
  return words
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}
