import {
  Background,
  Controls,
  type Edge,
  MarkerType,
  type Node,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Messages, Organization, Overview, RevisionMeta, Status } from "../api";
import { ActorPanel } from "../components/ActorPanel";
import type { CardData } from "../components/cardData";
import { HostCard } from "../components/HostCard";
import { HumanCard } from "../components/HumanCard";
import { OfficerCard } from "../components/OfficerCard";
import { OrchestratorCard } from "../components/OrchestratorCard";
import { SpecialistCard } from "../components/SpecialistCard";
import { TierBand } from "../components/TierBand";
import { type ChartEdge, handlesFor, layoutOrgChart } from "../lib/orgchart";
import { type Directory, domainColor, HOST } from "../lib/people";
import { kindColor } from "../lib/status";

const nodeTypes = {
  band: TierBand,
  human: HumanCard,
  orchestrator: OrchestratorCard,
  officer: OfficerCard,
  specialist: SpecialistCard,
  host: HostCard,
};

const EDGE_STYLE: Record<ChartEdge["kind"], React.CSSProperties> = {
  reports: { stroke: "var(--line)", strokeWidth: 1.25 },
  secondary: { stroke: "var(--line)", strokeWidth: 1, strokeDasharray: "5 6", opacity: 0.8 },
  delegation: { stroke: "var(--orchestrator)", strokeWidth: 1.25, strokeDasharray: "1.5 5", strokeLinecap: "round" },
  session: { stroke: "var(--accent)", strokeWidth: 1, strokeDasharray: "5 6", opacity: 0.7 },
};
const RECENT = 3;

type Props = {
  overview: Overview;
  org: Organization;
  messages: Messages | undefined;
  documents: RevisionMeta[] | undefined;
  directory: Directory;
  onOpenDocument: (id: string) => void;
};

function scopeLabel(overview: Overview): string {
  const { kind, id } = overview.scope;
  return kind === "workflow" ? "Full workflow" : `${kind} ${id}`;
}

function humanPending(overview: Overview): string[] {
  const pending: string[] = [];
  for (const [phase, plan] of Object.entries(overview.phase_plans)) {
    if (!plan.approved_by && ["semi-auto", "manual"].includes(overview.mode)) pending.push(`Approve phase ${phase}`);
  }
  for (const phase of overview.status.phases) {
    for (const sub of phase.subphases) {
      const latest = sub.instances.at(-1);
      if (latest?.status === "awaiting_plan_approval") pending.push(`Approve plan ${sub.id}`);
      if (latest?.mode === "manual" && latest.status === "awaiting_review" && !latest.human_review)
        pending.push(`Review ${sub.id}`);
    }
  }
  return pending;
}

export function COrganization({ overview, org, messages, documents, directory, onOpenDocument }: Props) {
  const [showAll, setShowAll] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [flash, setFlash] = useState<Set<string>>(new Set());
  const seen = useRef<number | null>(null);
  const all = messages?.messages ?? [];
  const includeHost = Boolean(messages?.transcripts.available && all.some((m) => m.from === HOST || m.to.includes(HOST)));
  const chart = useMemo(() => layoutOrgChart(org, { showAll, includeHost }), [org, showAll, includeHost]);
  const present = useMemo(() => new Map(chart.nodes.map((n) => [n.id, n])), [chart]);
  // Frame the hierarchy (top tiers + first row of specialists) at a readable size; scroll for the rest.
  const framed = useMemo(() => {
    const firstRow = Math.min(...chart.nodes.filter((n) => n.kind === "specialist").map((n) => n.y));
    return chart.nodes.filter((n) => n.kind !== "specialist" || n.y === firstRow).map((n) => ({ id: n.id }));
  }, [chart]);

  // Flash the members involved in messages that arrived since the last refresh.
  useEffect(() => {
    if (seen.current !== null && all.length > seen.current) {
      const involved = new Set<string>();
      for (const m of all.slice(seen.current)) {
        for (const ref of [m.from, ...m.to]) involved.add(directory.person(ref).definition);
      }
      setFlash(involved);
      const timer = setTimeout(() => setFlash(new Set()), 1700);
      seen.current = all.length;
      return () => clearTimeout(timer);
    }
    seen.current = all.length;
  }, [all, directory]);

  const statuses = useMemo(() => {
    const map: Record<string, Status> = {};
    overview.status.phases.forEach((p) => p.subphases.forEach((s) => (map[s.id] = s.status)));
    return map;
  }, [overview]);

  const nodes: Node[] = useMemo(() => {
    const bands: Node[] = chart.bands.map((band) => ({
      id: `band:${band.level}`,
      type: "band",
      position: { x: -60, y: band.y },
      data: { label: band.label },
      style: { width: chart.width + 120, height: band.height },
      draggable: false,
      selectable: false,
      zIndex: -1,
    }));
    const pending = humanPending(overview);
    const cards: Node[] = chart.nodes.map((node) => {
      const data: CardData = {
        node,
        color: node.kind === "host" ? "var(--accent)" : domainColor(node.definition),
        statuses,
        flash: flash.has(node.id),
        selected: selected === node.id,
        human: { objective: overview.objective, mode: overview.mode, pending },
        orchestrator: { mainPhase: overview.main_phase, scope: scopeLabel(overview) },
        host: {
          prompts: all.filter((m) => m.kind === "human_prompt").length,
          delegations: all.filter((m) => m.kind === "delegation_prompt").length,
          reports: all.filter((m) => m.kind === "subagent_report").length,
        },
      };
      return {
        id: node.id,
        type: node.kind,
        position: { x: node.x, y: node.y },
        data,
        style: { width: node.width, height: node.height },
        draggable: false,
      };
    });
    return [...bands, ...cards];
  }, [chart, overview, statuses, flash, selected, all]);

  const edges: Edge[] = useMemo(() => {
    const structural: Edge[] = chart.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      ...handlesFor(present.get(edge.source)!, present.get(edge.target)!),
      type: "smoothstep",
      pathOptions: { borderRadius: 18 },
      style: EDGE_STYLE[edge.kind],
      selectable: false,
    }));
    const recent = all.slice(-RECENT);
    const overlay: Edge[] = [];
    recent.forEach((m, index) => {
      const from = directory.person(m.from).definition;
      const isLatest = index === recent.length - 1;
      for (const ref of m.to) {
        const to = directory.person(ref).definition;
        const [a, b] = [present.get(from), present.get(to)];
        if (!a || !b || a === b) continue;
        overlay.push({
          id: `msg:${m.id}:${to}`,
          source: from,
          target: to,
          ...handlesFor(a, b),
          animated: true,
          zIndex: 5,
          label: isLatest ? m.summary.slice(0, 54) : undefined,
          labelStyle: { fontSize: 11.5, fontWeight: 500, fill: "var(--text)" },
          labelBgStyle: { fill: "var(--surface)", stroke: "var(--hairline-strong)" },
          labelBgPadding: [10, 6] as [number, number],
          labelBgBorderRadius: 999,
          markerEnd: { type: MarkerType.ArrowClosed, color: kindColor(m.kind, m.category) },
          style: { stroke: kindColor(m.kind, m.category), strokeWidth: isLatest ? 2 : 1.25, opacity: isLatest ? 0.95 : 0.4 },
          selectable: false,
        });
      }
    });
    return [...structural, ...overlay];
  }, [chart, present, all, directory]);

  return (
    <div className="org">
      <div className="org-toolbar glass">
        <label className="switch">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Whole organization
        </label>
      </div>
      <ReactFlow
        key={`${showAll}:${includeHost}`}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ nodes: framed, padding: 0.06, maxZoom: 1 }}
        minZoom={0.15}
        maxZoom={1.6}
        panOnScroll
        zoomOnPinch
        zoomOnDoubleClick={false}
        colorMode="system"
        nodesConnectable={false}
        onNodeClick={(_, node) => node.type !== "band" && setSelected(node.id)}
        onPaneClick={() => setSelected(null)}
      >
        <Background gap={28} size={1} color="var(--hairline-strong)" />
        <Controls showInteractive={false} position="bottom-right" style={{ margin: 18 }} />
      </ReactFlow>
      <div className="org-legend glass">
        <span>
          <span className="legend-line" />
          reports to
        </span>
        <span>
          <span className="legend-line dashed" />
          co-owner
        </span>
        <span>
          <span className="legend-line dotted" />
          delegated by
        </span>
        <span>
          <span className="legend-line message" />
          latest messages
        </span>
        <span className="muted">Dashed card · not delegated yet</span>
      </div>
      {selected && (
        <ActorPanel
          nodeId={selected}
          org={org}
          messages={messages}
          documents={documents}
          directory={directory}
          onClose={() => setSelected(null)}
          onOpenDocument={onOpenDocument}
        />
      )}
    </div>
  );
}
