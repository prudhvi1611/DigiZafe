import React, { useState, useMemo } from "react";
import { useIdentifiers } from "@/features/identifiers/api";
import { useGeneratePlan, useLatestPlan, useUpdateRecommendation } from "./api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  ShieldCheck,
  ShieldAlert,
  GitBranch,
  Sparkles,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Loader2,
  ListFilter,
  Layers,
  ArrowUpRight,
  Terminal,
  AlertOctagon
} from "lucide-react";

export function RecommendationsPage() {
  const ids = useIdentifiers();
  const [identifierId, setIdentifierId] = useState("");
  const [selectedLane, setSelectedLane] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("open");

  const plan = useLatestPlan(identifierId || undefined);
  const generate = useGeneratePlan();
  const update = useUpdateRecommendation();

  // Filtered and sorted recommendations
  const filteredRecommendations = useMemo(() => {
    if (!plan.data?.recommendations) return [];
    return plan.data.recommendations.filter((r) => {
      const matchLane = selectedLane === "all" || r.lane.toLowerCase() === selectedLane.toLowerCase();
      const matchStatus =
        selectedStatus === "all" ? true :
        selectedStatus === "open" ? r.status !== "done" && r.status !== "dismissed" :
        r.status.toLowerCase() === selectedStatus.toLowerCase();
      return matchLane && matchStatus;
    });
  }, [plan.data, selectedLane, selectedStatus]);

  const stats = useMemo(() => {
    const list = plan.data?.recommendations || [];
    const doneCount = list.filter((r) => r.status === "done").length;
    const openCount = list.filter((r) => r.status !== "done" && r.status !== "dismissed").length;
    const autoCount = list.filter((r) => r.lane === "automated" || r.lane === "semi-automated").length;
    return { total: list.length, doneCount, openCount, autoCount };
  }, [plan.data]);

  return (
    <div className="space-y-6 mt-8 animate-fade-in text-slate-100 pb-12">
      {/* Strategic Matrix Header */}
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6 pb-4 border-b border-white/10">
        <div className="space-y-1.5 border-l-4 border-emerald-500 pl-4 py-1">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-7 w-7 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-emerald-300 bg-clip-text text-transparent">
              Strategic Remediation & Hardening Matrix
            </h1>
            <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs uppercase font-mono tracking-wider">
              DAG-Optimized Engine
            </Badge>
          </div>
          <p className="text-sm text-slate-400 max-w-3xl font-mono">
            Two-lane defensive mitigation playbook (Guided UI procedures + Semi-automated Green broker removal). Actions are mathematically sorted by urgency ROI and Directed Acyclic Graph (DAG) prerequisite dependencies.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0 bg-slate-900/80 p-2 rounded-xl border border-white/10">
          <select
            className="h-9 rounded-lg border border-white/15 bg-slate-950 px-3 text-xs font-mono text-slate-200 focus:border-emerald-500/50 outline-none"
            value={identifierId}
            onChange={(e) => setIdentifierId(e.target.value)}
          >
            <option value="">All Scopes (Global Matrix)</option>
            {(ids.data || []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.value_display} ({i.type})
              </option>
            ))}
          </select>
          <Button
            variant="cyber"
            size="sm"
            onClick={() => generate.mutate({ identifier_id: identifierId || undefined })}
            disabled={generate.isPending}
            className="font-mono font-semibold text-xs h-9 shadow-md shadow-emerald-500/20"
          >
            {generate.isPending ? (
              <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Computing DAG...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5 mr-1.5 text-emerald-300" /> Generate Intelligence Plan</>
            )}
          </Button>
        </div>
      </div>

      {/* Plan Telemetry & Credit Freeze Alert */}
      {plan.data && (
        <div className="space-y-4">
          {plan.data.freeze_recommended && (
            <Card className="border border-red-500/50 bg-gradient-to-r from-red-950/40 via-slate-900 to-slate-950 p-4 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4 animate-pulse">
              <div className="flex items-start md:items-center gap-3">
                <AlertOctagon className="w-8 h-8 text-red-400 shrink-0 mt-0.5 md:mt-0" />
                <div className="space-y-0.5">
                  <h3 className="font-bold font-mono text-base text-red-200 uppercase tracking-wide">
                    Immediate Credit & Security Freeze Recommended
                  </h3>
                  <p className="text-xs text-slate-300 font-mono">
                    High-impact financial or government identifiers detected in recent leak corpora. Engage national credit bureau freezes immediately.
                  </p>
                </div>
              </div>
              <Button size="sm" variant="destructive" className="font-mono font-semibold text-xs shrink-0 shadow-md">
                View Freeze Targets & Procedures
              </Button>
            </Card>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-mono uppercase">Total Mitigation Steps</p>
                <p className="text-2xl font-bold font-mono text-white mt-1">{stats.total}</p>
              </div>
              <Layers className="w-8 h-8 text-cyan-400/40" />
            </Card>

            <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-mono uppercase">Pending Action Items</p>
                <p className="text-2xl font-bold font-mono text-amber-400 mt-1">{stats.openCount}</p>
              </div>
              <Terminal className="w-8 h-8 text-amber-400/40" />
            </Card>

            <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-mono uppercase">Automated Lane Capable</p>
                <p className="text-2xl font-bold font-mono text-cyan-300 mt-1">{stats.autoCount}</p>
              </div>
              <GitBranch className="w-8 h-8 text-cyan-300/40" />
            </Card>

            <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-mono uppercase">Resolved Mitigations</p>
                <p className="text-2xl font-bold font-mono text-emerald-400 mt-1">{stats.doneCount}</p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-emerald-400/40" />
            </Card>
          </div>

          {/* Filters Toolbar */}
          <Card className="border-white/10 bg-slate-900/40 p-3 shadow-md">
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-1 bg-black/30 p-1 rounded-lg border border-white/10">
                <span className="text-slate-400 px-2 flex items-center gap-1">
                  <ListFilter className="w-3.5 h-3.5 text-emerald-400" /> Execution Lane:
                </span>
                {["all", "guided", "automated", "semi-automated"].map((l) => (
                  <button
                    key={l}
                    onClick={() => setSelectedLane(l)}
                    className={cn(
                      "px-2.5 py-1 rounded text-[11px] capitalize transition-all",
                      selectedLane === l ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold" : "text-slate-400 hover:text-slate-200"
                    )}
                  >
                    {l}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1 bg-black/30 p-1 rounded-lg border border-white/10">
                <span className="text-slate-400 px-2">Status Filter:</span>
                {["open", "done", "dismissed", "all"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setSelectedStatus(st)}
                    className={cn(
                      "px-2.5 py-1 rounded text-[11px] uppercase transition-all",
                      selectedStatus === st ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold" : "text-slate-400 hover:text-slate-200"
                    )}
                  >
                    {st === "open" ? "Active Queue" : st}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Recommendations Playbook List */}
          <div className="space-y-4">
            {filteredRecommendations.map((r, idx) => (
              <Card
                key={r.id}
                className={cn(
                  "border-white/10 bg-slate-900/70 hover:bg-slate-900/90 transition-all shadow-lg overflow-hidden border-l-[6px]",
                  r.status === "done" ? "border-l-emerald-500 bg-slate-950/40 opacity-75" :
                  r.priority >= 0.8 ? "border-l-red-500" :
                  r.priority >= 0.5 ? "border-l-orange-500" : "border-l-cyan-500"
                )}
              >
                <CardHeader className="p-5 pb-3 border-b border-white/5 bg-white/[0.01]">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="font-mono text-xs font-bold text-slate-400">#{idx + 1}</span>
                      <CardTitle className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                        {r.title}
                      </CardTitle>
                      <Badge className={cn("text-[10px] font-mono uppercase font-bold",
                        r.lane === "automated" ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                      )}>
                        {r.lane} lane
                      </Badge>
                      <Badge variant="outline" className={cn("text-[10px] font-mono uppercase",
                        r.status === "done" ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold" : "text-slate-300 border-white/15 bg-black/20"
                      )}>
                        {r.status}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono bg-slate-800 border border-white/15 px-2.5 py-1 rounded text-cyan-300 font-semibold">
                        Urgency ROI: {r.priority.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-5 space-y-4">
                  <p className="text-sm text-slate-300 leading-relaxed font-sans">{r.summary}</p>

                  {(r.depends_on || []).length > 0 && (
                    <div className="flex items-center gap-2 bg-black/40 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-amber-300">
                      <GitBranch className="w-4 h-4 shrink-0 text-amber-400" />
                      <span>DAG Prerequisite Dependencies required before completion: <strong>{(r.depends_on || []).join(", ")}</strong></span>
                    </div>
                  )}

                  {r.steps && r.steps.length > 0 && (
                    <div className="space-y-2 bg-slate-950/60 p-4 rounded-xl border border-white/10">
                      <h4 className="text-xs font-mono font-bold uppercase text-slate-400 tracking-wider mb-2">
                        Execution Playbook Procedures
                      </h4>
                      <ol className="space-y-2 text-sm font-mono text-slate-300">
                        {r.steps.map((stepText, i) => (
                          <li key={i} className="flex items-start gap-3">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-cyan-500/20 text-[11px] font-bold text-cyan-300 border border-cyan-500/30">
                              {i + 1}
                            </span>
                            <span className="leading-relaxed">{stepText}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-white/5">
                    <div className="flex flex-wrap items-center gap-3">
                      {r.links && r.links.map((l) => (
                        <a
                          key={l.url}
                          href={l.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan-400 bg-cyan-950/40 px-3 py-1.5 rounded-lg border border-cyan-500/30 hover:bg-cyan-950 hover:underline"
                        >
                          {l.label} <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      ))}
                    </div>

                    <div className="flex items-center gap-2.5 shrink-0">
                      {r.status !== "dismissed" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => update.mutate({ id: r.id, status: "dismissed" })}
                          disabled={update.isPending}
                          className="text-xs font-mono hover:bg-red-500/20 hover:text-red-300"
                        >
                          <XCircle className="w-3.5 h-3.5 mr-1 text-red-400" />
                          Dismiss / Defer
                        </Button>
                      )}
                      {r.status !== "done" && (
                        <Button
                          size="sm"
                          variant="cyber"
                          onClick={() => update.mutate({ id: r.id, status: "done" })}
                          disabled={update.isPending}
                          className="text-xs font-mono font-semibold shadow-md shadow-emerald-500/20 bg-emerald-600 hover:bg-emerald-500 text-white"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-white" />
                          Mark Mitigated
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {!filteredRecommendations.length && (
              <Card className="border-white/10 bg-slate-900/40 p-12 text-center text-slate-400 font-mono space-y-3">
                <ShieldCheck className="w-12 h-12 text-emerald-400/40 mx-auto animate-pulse" />
                <p className="text-base font-semibold text-slate-200">All defensive mitigations in this view are resolved or inactive.</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Your cryptographic privacy anchor is in an optimal defensive posture according to the current DAG model.
                </p>
                {(selectedLane !== "all" || selectedStatus !== "open") && (
                  <Button variant="outline" size="sm" onClick={() => { setSelectedLane("all"); setSelectedStatus("open"); }}>
                    Reset Playbook Filters
                  </Button>
                )}
              </Card>
            )}
          </div>
        </div>
      )}

      {!plan.data && !plan.isLoading && (
        <Card className="border-white/10 bg-slate-900/60 p-16 text-center text-slate-400 font-mono space-y-4">
          <ShieldAlert className="w-16 h-16 text-cyan-400/50 mx-auto animate-bounce" />
          <h3 className="text-xl font-bold text-white">No Strategic Hardening Plan Initialized</h3>
          <p className="text-sm text-slate-400 max-w-lg mx-auto">
            Select an identity scope above and click <strong>Generate Intelligence Plan</strong> to evaluate your exposure corpus against our defensive DAG mitigation ruleset.
          </p>
          <Button
            variant="cyber"
            onClick={() => generate.mutate({ identifier_id: identifierId || undefined })}
            disabled={generate.isPending}
            className="font-mono font-semibold px-6"
          >
            <Sparkles className="w-4 h-4 mr-2 text-emerald-300" /> Generate First Playbook
          </Button>
        </Card>
      )}
    </div>
  );
}

