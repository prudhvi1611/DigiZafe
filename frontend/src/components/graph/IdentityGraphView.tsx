import { useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { IdentityGraphPublic } from "@/lib/types";

export function IdentityGraphView({ graph }: { graph: IdentityGraphPublic }) {
  const elements = useMemo(() => {
    const nodes = graph.nodes.map((n) => ({
      data: {
        id: n.id,
        label: `${n.type}\n${n.value_display}`,
        verified: n.is_verified,
      },
    }));
    const edges = graph.edges
      .filter((e) => e.decision !== "none")
      .map((e) => ({
        data: {
          id: e.id,
          source: e.left_identifier_id,
          target: e.right_identifier_id,
          label: `${(e.match_prob * 100).toFixed(0)}%`,
          decision: e.decision,
        },
      }));
    return [...nodes, ...edges];
  }, [graph]);

  const stylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-wrap": "wrap",
        "text-valign": "center",
        "text-halign": "center",
        "font-size": 9,
        color: "#e2e8f0",
        "background-color": "#0ea5e9",
        width: 56,
        height: 56,
        "text-max-width": 70,
      },
    },
    {
      selector: "node[verified = 0], node[verified = false]",
      style: { "background-color": "#64748b" },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": "#475569",
        "target-arrow-color": "#475569",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": 8,
        color: "#94a3b8",
      },
    },
    {
      selector: 'edge[decision = "auto_link"]',
      style: { "line-color": "#22c55e", "target-arrow-color": "#22c55e" },
    },
    {
      selector: 'edge[decision = "review"]',
      style: { "line-color": "#eab308", "target-arrow-color": "#eab308" },
    },
  ];

  if (!graph.nodes.length) {
    return <p className="text-sm text-muted-foreground">Add and verify identifiers, then rebuild the graph.</p>;
  }

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-xl border bg-card/30">
      <CytoscapeComponent
        elements={elements as never}
        style={{ width: "100%", height: "100%" }}
        stylesheet={stylesheet as never}
        layout={{ name: "cose", animate: false, padding: 30 } as never}
        cy={(cy: any) => {
          cy.userZoomingEnabled(true);
          cy.userPanningEnabled(true);
        }}
      />
    </div>
  );
}
