// Sequence-diagram layout: one lane per organization member, ordered by tier like the org chart.
import type { Message } from "../api";
import type { Directory, Person } from "./people";

export type Lane = { key: string; person: Person; x: number };
export type Row = { message: Message; y: number; from: number; to: number[] };
export type Sequence = { lanes: Lane[]; rows: Row[]; width: number; height: number };

export const LANE_WIDTH = 148;
export const MIN_LANE_WIDTH = 84;

/** Lane width that fits `available` pixels, between MIN_LANE_WIDTH and LANE_WIDTH. */
export function fitLaneWidth(available: number, lanes: number): number {
  if (lanes <= 0) return LANE_WIDTH;
  return Math.max(MIN_LANE_WIDTH, Math.min(LANE_WIDTH, Math.floor(available / lanes)));
}
export const ROW_HEIGHT = 46;
export const HEADER = 64;

export function layoutLanes(messages: Message[], directory: Directory, laneWidth = LANE_WIDTH): Sequence {
  const people = new Map<string, Person>();
  for (const message of messages) {
    for (const ref of [message.from, ...message.to]) {
      const person = directory.person(ref);
      if (!people.has(person.definition)) people.set(person.definition, person);
    }
  }
  const ordered = [...people.values()].sort((a, b) => {
    const [x, y] = [directory.rank(a), directory.rank(b)];
    return x[0] - y[0] || x[1] - y[1] || a.label.localeCompare(b.label);
  });
  const lanes = ordered.map((person, index) => ({
    key: person.definition,
    person,
    x: index * laneWidth + laneWidth / 2,
  }));
  const position = new Map(lanes.map((lane) => [lane.key, lane.x]));
  const x = (ref: string) => position.get(directory.person(ref).definition) ?? 0;
  const rows = messages.map((message, index) => ({
    message,
    y: HEADER + index * ROW_HEIGHT + ROW_HEIGHT / 2,
    from: x(message.from),
    to: message.to.map(x),
  }));
  return {
    lanes,
    rows,
    width: Math.max(lanes.length, 1) * laneWidth,
    height: HEADER + Math.max(messages.length, 1) * ROW_HEIGHT + 16,
  };
}
