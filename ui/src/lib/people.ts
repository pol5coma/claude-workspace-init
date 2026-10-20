import type { ActorRow, Definition, Instance, Level } from "../api";
import { DOMAIN_COLOR } from "./status";

export const HOST = "host";

/** Who an actor reference (instance UUID, `def:ROLE`, `host`, `agent:…`) stands for. */
export type Person = {
  ref: string;
  definition: string; // org-chart node id: definition id, "host" or the raw ref
  label: string;
  title: string;
  level: Level | "host";
  delegated: boolean;
};

const LEVEL_ORDER: Record<string, number> = { human: 0, host: 1, orchestrator: 1, officer: 2, specialist: 3 };

export class Directory {
  private byInstance = new Map<string, ActorRow | Instance>();
  private definitions = new Map<string, Definition>();
  private order = new Map<string, number>();

  constructor(definitions: Definition[], actors: (ActorRow | Instance)[]) {
    definitions.forEach((d, index) => {
      this.definitions.set(d.id, d);
      this.order.set(d.id, index);
    });
    actors.forEach((a) => this.byInstance.set(a.id, a));
  }

  definition(id: string): Definition | undefined {
    return this.definitions.get(id);
  }

  person(ref: string): Person {
    if (ref === HOST) {
      return { ref, definition: HOST, label: "Claude Code", title: "Host session (transcript)", level: "host", delegated: true };
    }
    if (ref.startsWith("agent:")) {
      return { ref, definition: ref, label: ref.slice(6, 18), title: "Unlinked subagent", level: "specialist", delegated: true };
    }
    const instance = this.byInstance.get(ref);
    const definitionId = instance ? instance.definition : ref.startsWith("def:") ? ref.slice(4) : ref;
    const definition = this.definitions.get(definitionId);
    const level: Level = instance?.level ?? definition?.level ?? "specialist";
    return {
      ref,
      definition: definitionId,
      label: definition ? (level === "specialist" ? specialistShort(definition) : definition.acronym) : definitionId,
      title: definition?.name ?? definitionId,
      level,
      delegated: Boolean(instance),
    };
  }

  /** Stable tier order: Human, host/CAOAO, officers (catalog order), specialists (catalog order). */
  rank(person: Person): [number, number] {
    return [LEVEL_ORDER[person.level] ?? 4, this.order.get(person.definition) ?? 999];
  }
}

export function specialistShort(definition: Definition): string {
  const role = definition.name.split(" — ")[0];
  const sub = definition.subphases[0];
  return sub ? `${role} · ${sub}` : role;
}

export function domainColor(definition: Definition | undefined): string {
  if (!definition) return "var(--muted)";
  return DOMAIN_COLOR[definition.id] ?? DOMAIN_COLOR[definition.reports_to[0]] ?? "var(--muted)";
}
