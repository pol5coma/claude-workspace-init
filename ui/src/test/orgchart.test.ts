import { describe, expect, it } from "vitest";
import type { Organization } from "../api";
import { type ChartNode, handlesFor, layoutOrgChart } from "../lib/orgchart";
import organization from "./fixtures/organization.json";

const org = organization as unknown as Organization;

function overlaps(a: ChartNode, b: ChartNode): boolean {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

describe("layoutOrgChart", () => {
  const chart = layoutOrgChart(org, { showAll: false, includeHost: true });
  const node = (id: string) => chart.nodes.find((n) => n.id === id)!;

  it("draws the four tiers top to bottom", () => {
    expect(chart.bands.map((b) => b.level)).toEqual(["human", "orchestrator", "officer", "specialist"]);
    expect(node("Human").y).toBeLessThan(node("CAOAO").y);
    expect(node("CAOAO").y).toBeLessThan(node("CPAO").y);
    expect(node("CPAO").y).toBeLessThan(node("spdlc-1-1").y);
  });

  it("never overlaps cards", () => {
    for (const [i, a] of chart.nodes.entries()) {
      for (const b of chart.nodes.slice(i + 1)) expect(overlaps(a, b), `${a.id} / ${b.id}`).toBe(false);
    }
  });

  it("hangs each specialist under one of its owners, balancing the columns", () => {
    for (const specialist of chart.nodes.filter((n) => n.kind === "specialist")) {
      const officer = node(specialist.column!);
      expect(specialist.definition!.reports_to).toContain(officer.id);
      expect(specialist.x + specialist.width / 2).toBeCloseTo(officer.x + officer.width / 2);
    }
    const heights = new Map<string, number>();
    chart.nodes.filter((n) => n.kind === "specialist").forEach((n) => heights.set(n.column!, (heights.get(n.column!) ?? 0) + 1));
    expect(Math.max(...heights.values())).toBeLessThanOrEqual(2);
  });

  it("shows only in-scope officers unless the whole organization is requested", () => {
    const officers = (c: typeof chart) => c.nodes.filter((n) => n.kind === "officer").map((n) => n.id);
    expect(officers(chart)).toEqual(["CEAO", "CPAO", "CTAO", "CMAO", "CFAO"]);
    expect(officers(layoutOrgChart(org, { showAll: true, includeHost: false }))).toHaveLength(9);
    expect(node("CTAO").dimmed).toBe(true);
    expect(node("CEAO").dimmed).toBe(false);
  });

  it("separates reporting, co-ownership and actual delegation lines", () => {
    const kinds = (source: string, target: string) =>
      chart.edges.filter((e) => e.source === source && e.target === target).map((e) => e.kind);
    expect(kinds("Human", "CAOAO")).toEqual(["reports"]);
    const founder = node("spdlc-1-1").column!;
    const other = founder === "CEAO" ? "CPAO" : "CEAO";
    expect(kinds(founder, "spdlc-1-1")).toEqual(["reports"]);
    expect(kinds(other, "spdlc-1-1")).toEqual(["secondary"]);
    expect(kinds("CAOAO", "spdlc-1-2")).toEqual(["delegation"]);
    expect(kinds("Human", "host")).toEqual(["session"]);
  });

  it("is deterministic", () => {
    expect(layoutOrgChart(org, { showAll: false, includeHost: true })).toEqual(chart);
  });

  it("picks handles by relative position", () => {
    expect(handlesFor(node("CAOAO"), node("CPAO"))).toEqual({ sourceHandle: "bottom-out", targetHandle: "top-in" });
    expect(handlesFor(node("CPAO"), node("CAOAO"))).toEqual({ sourceHandle: "top-out", targetHandle: "bottom-in" });
    expect(handlesFor(node("CEAO"), node("CPAO")).sourceHandle).toBe("right-out");
  });
});
