import { describe, expect, it } from "vitest";
import type { Messages, Organization } from "../api";
import { LANE_WIDTH, layoutLanes } from "../lib/lanes";
import { Directory } from "../lib/people";
import messages from "./fixtures/messages.json";
import organization from "./fixtures/organization.json";

const data = messages as unknown as Messages;
const directory = new Directory((organization as unknown as Organization).definitions, data.actors);

describe("layoutLanes", () => {
  const sequence = layoutLanes(data.messages, directory);

  it("orders lanes by organization tier", () => {
    const levels = sequence.lanes.map((l) => l.person.level);
    const rank = { human: 0, host: 1, orchestrator: 1, officer: 2, specialist: 3 } as const;
    expect(levels.map((l) => rank[l])).toEqual([...levels.map((l) => rank[l])].sort());
    expect(sequence.lanes[0].person.label).toBe("Human");
  });

  it("merges instances of one role into a single lane", () => {
    const keys = sequence.lanes.map((l) => l.key);
    expect(new Set(keys).size).toBe(keys.length);
    expect(keys).toContain("CTAO"); // addressed as def:CTAO before delegation
  });

  it("places arrows on their lanes, one row per message", () => {
    expect(sequence.rows).toHaveLength(data.messages.length);
    const x = new Map(sequence.lanes.map((l) => [l.key, l.x]));
    const review = sequence.rows.find((r) => r.message.kind === "domain_review")!;
    expect(review.from).toBe(x.get("CEAO"));
    expect(review.to).toEqual([x.get("CAOAO")]);
    expect(sequence.width).toBe(sequence.lanes.length * LANE_WIDTH);
  });
});
