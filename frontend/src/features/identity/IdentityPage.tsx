import React from "react";
import { useIdentityGraph, useRebuildGraph } from "./api";
import { IdentityGraphView } from "@/components/graph/IdentityGraphView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { IdentityAnchorView } from "./IdentityAnchorView";
import { IdentityDiscoveryView } from "./IdentityDiscoveryView";
import { Network, RefreshCw, Layers, ShieldCheck } from "lucide-react";

export function IdentityPage() {
  const graph = useIdentityGraph();
  const rebuild = useRebuildGraph();

  return (
    <div className="space-y-10 animate-fade-in">
      {/* Identity Workspace Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status="active" label="GRAPH REASONING ENGINE" pulse />
            <span className="text-xs font-mono text-slate-400">DECIBAN / FELLEGI–SUNTER</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1 flex items-center gap-2.5">
            <Network className="h-7 w-7 text-cyan-400" />
            Identity graph
          </h1>
          <p className="text-sm text-slate-400 max-w-2xl leading-relaxed mt-1">
            Deciban / Fellegi–Sunter pairwise cryptographic links among <em>your</em> verified identifiers.
          </p>
        </div>
        <Button
          variant="cyber"
          onClick={() => rebuild.mutate()}
          disabled={rebuild.isPending}
          className="font-semibold shadow-lg shadow-cyan-500/20"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${rebuild.isPending ? "animate-spin" : ""}`} />
          {rebuild.isPending ? "Rebuilding…" : "Rebuild graph"}
        </Button>
      </div>

      {graph.data && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-2xl backdrop-blur-md overflow-hidden">
            <IdentityGraphView graph={graph.data} />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border-white/10 bg-gradient-to-b from-slate-900/80 to-slate-950 shadow-xl">
              <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                    <Layers className="h-4 w-4 text-cyan-400" />
                    Edges
                  </CardTitle>
                  <Badge variant="outline" className="text-[10px] font-mono border-white/15">
                    Model {graph.data.model_version}
                  </Badge>
                </div>
                <CardDescription className="text-xs text-slate-400">
                  Pairwise cryptographic linkage determinations across target anchors
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-2 max-h-64 overflow-y-auto">
                {graph.data.edges.map((e) => (
                  <div key={e.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-mono">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="bg-cyan-500/15 text-cyan-300 border-cyan-500/30 uppercase text-[10px]">
                        {e.decision}
                      </Badge>
                      <span className="text-slate-300 font-semibold">p={e.match_prob.toFixed(3)}</span>
                    </div>
                    <span className="text-slate-400 text-[11px]">
                      review={e.review_status}
                    </span>
                  </div>
                ))}
                {!graph.data.edges.length && <p className="text-xs text-slate-400 font-mono italic py-4 text-center">No edges discovered yet.</p>}
              </CardContent>
            </Card>

            {(graph.data.collisions || []).length > 0 && (
              <Card className="border-amber-500/30 bg-gradient-to-b from-slate-900/80 to-slate-950 shadow-xl">
                <CardHeader className="border-b border-amber-500/20 bg-amber-500/5 pb-3">
                  <CardTitle className="text-base font-bold text-amber-300 flex items-center gap-2">
                    Collisions / review
                  </CardTitle>
                  <CardDescription className="text-xs text-amber-200/70">
                    Ambiguous probabilistic links requiring manual human analyst verification
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-4 text-xs font-mono text-slate-300 space-y-2">
                  {(graph.data.collisions || []).map((c) => (
                    <div key={c.id} className="rounded-lg border border-white/10 bg-black/20 p-2.5">
                      {c.reason}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      <hr className="border-t border-white/10 my-12" />

      <IdentityAnchorView />

      <hr className="border-t border-white/10 my-12" />

      <IdentityDiscoveryView />
    </div>
  );
}
