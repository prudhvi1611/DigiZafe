import React, { useState } from "react";
import { useIdentifiers } from "@/features/identifiers/api";
import { useFindings } from "@/features/findings/api";
import { useComputeScore, useLatestScore, useScoreHistory } from "./api";
import { PdssGauge } from "@/components/charts/PdssGauge";
import { PdssBreakdown } from "@/components/charts/PdssBreakdown";
import { RiskAutopsy } from "@/components/creative/RiskAutopsy";
import { WhatIfSimulator } from "@/components/creative/WhatIfSimulator";
import { NarrativeBriefing } from "@/components/creative/NarrativeBriefing";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, cn } from "@/lib/utils";
import {
  Activity,
  Sparkles,
  ShieldAlert,
  Loader2,
  Cpu,
  TrendingDown,
  LineChart,
  Target,
  FileSearch
} from "lucide-react";

export function ScoresPage() {
  const ids = useIdentifiers();
  const [identifierId, setIdentifierId] = useState<string>("");

  const score = useLatestScore(identifierId || undefined);
  const findings = useFindings(identifierId || undefined);
  const history = useScoreHistory(identifierId || undefined);
  const compute = useComputeScore();

  return (
    <div className="space-y-8 mt-8 animate-fade-in text-slate-100 pb-16">
      {/* Threat Quantification Header */}
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6 pb-4 border-b border-white/10">
        <div className="space-y-1.5 border-l-4 border-cyan-500 pl-4 py-1">
          <div className="flex items-center gap-2.5">
            <Activity className="h-7 w-7 text-cyan-400 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-cyan-300 bg-clip-text text-transparent">
              PDSS Autonomous Threat Quantification Matrix
            </h1>
            <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs uppercase font-mono tracking-wider">
              Realtime CVSS/PDSS Telemetry
            </Badge>
          </div>
          <p className="text-sm text-slate-400 max-w-3xl font-mono">
            Quantify external attack surface exposure through deterministic scoring vectors, experimental residual ML signals, and interactive defensive simulation modeling.
          </p>
        </div>

        {/* Action & Scope Controls */}
        <div className="flex flex-wrap items-center gap-3 shrink-0 bg-slate-900/80 p-2 rounded-xl border border-white/10">
          <select
            className="h-9 rounded-lg border border-white/15 bg-slate-950 px-3 text-xs font-mono text-slate-200 focus:border-cyan-500/50 outline-none"
            value={identifierId}
            onChange={(event) => setIdentifierId(event.target.value)}
          >
            <option value="">Whole Identity Profile (Global Aggregation)</option>
            {(ids.data || []).map((identifier) => (
              <option key={identifier.id} value={identifier.id}>
                {identifier.type.toUpperCase()}: {identifier.value_display}
              </option>
            ))}
          </select>

          <Button
            variant="cyber"
            size="sm"
            onClick={() =>
              compute.mutate({
                identifier_id: identifierId || undefined,
                persist: true,
              })
            }
            disabled={compute.isPending}
            className="font-mono font-semibold text-xs h-9 shadow-md shadow-cyan-500/20 px-4"
          >
            {compute.isPending ? (
              <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Computing Vectors...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5 mr-1.5 text-cyan-400" /> Recompute PDSS Score</>
            )}
          </Button>
        </div>
      </div>

      {score.data ? (
        <div className="space-y-8">
          {/* Top Exposure & ML Vector Dashboard */}
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="border-white/10 bg-slate-900/70 shadow-lg lg:col-span-2 overflow-hidden border-t-[6px] border-t-cyan-500 flex flex-col justify-between">
              <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                    <Target className="h-5 w-5 text-cyan-400" /> Current Surface Exposure Telemetry
                  </CardTitle>
                  <Badge variant="outline" className="text-xs font-mono font-bold border-cyan-500/40 text-cyan-300">
                    Model v{score.data.model_version}
                  </Badge>
                </div>
                <CardDescription className="text-xs font-mono text-slate-400">
                  {score.data.explanation_summary}
                </CardDescription>
              </CardHeader>

              <CardContent className="p-6 flex flex-col sm:flex-row items-center justify-around gap-6 flex-1">
                <div className="shrink-0 flex justify-center">
                  <PdssGauge
                    score={score.data.score_combined}
                    severity={score.data.severity}
                  />
                </div>

                <div className="space-y-4 flex-1 min-w-0 font-mono text-xs">
                  <div className="space-y-1">
                    <span className="text-slate-400 uppercase text-[11px] font-bold tracking-wider">Formal Vector String</span>
                    <p className="break-all rounded-lg border border-white/15 bg-slate-950 p-3.5 text-cyan-300 font-mono text-xs leading-relaxed shadow-inner">
                      {score.data.vector}
                    </p>
                  </div>

                  {(score.data.attributions || []).length > 0 && (
                    <div className="space-y-1">
                      <span className="text-slate-400 uppercase text-[11px] font-bold tracking-wider">Primary Risk Attributions</span>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {score.data.attributions?.map((attr, idx) => (
                          <Badge key={idx} className="bg-slate-800 text-slate-200 border border-white/10 text-[10px]">
                            {attr}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Residual ML Signal or Quick Stats */}
            {score.data.residual_ml && score.data.residual_ml.status !== 'disabled' ? (
              <Card className="border-white/10 bg-gradient-to-br from-slate-900/90 via-purple-950/20 to-slate-950 shadow-lg border-t-[6px] border-t-purple-500 flex flex-col justify-between">
                <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                      <Cpu className="h-5 w-5 text-purple-400 animate-pulse" />
                      Residual ML Intelligence
                    </CardTitle>
                    <Badge className="bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] uppercase font-mono">
                      EXPERIMENTAL
                    </Badge>
                  </div>
                  <CardDescription className="text-xs font-mono text-slate-400">
                    Non-deterministic heuristic anomaly signal evaluating latent threat likelihood.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-6 space-y-4 flex-1 flex flex-col justify-center font-mono">
                  {score.data.residual_ml.status === 'abstained' ? (
                    <div className="text-center py-6 space-y-2">
                      <ShieldAlert className="w-8 h-8 text-amber-400/50 mx-auto" />
                      <p className="text-xs text-slate-300 font-bold">Heuristic Engine Abstained</p>
                      <p className="text-[11px] text-slate-400">Reason: {score.data.residual_ml.reason}</p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="flex items-center justify-between border-b border-white/10 pb-4">
                        <div>
                          <span className="text-[11px] text-slate-400 uppercase font-bold">Predicted Risk Delta</span>
                          <p className="text-3xl font-bold text-purple-400 font-mono mt-1">
                            {score.data.residual_ml.delta > 0 ? "+" : ""}
                            {score.data.residual_ml.delta.toFixed(2)}
                          </p>
                        </div>
                        <div className="text-right text-[11px] text-slate-400 space-y-0.5">
                          <p>Model: <strong className="text-slate-200">{score.data.residual_ml.model_version}</strong></p>
                          <p>Schema: <strong className="text-slate-200">{score.data.residual_ml.schema_version}</strong></p>
                        </div>
                      </div>
                      <p className="text-[11px] italic text-slate-400 leading-tight">
                        * Synthetic validation and diagnostic modeling only. Does not alter deterministic zero-egress compliance boundaries.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="border-white/10 bg-slate-900/60 shadow-lg border-t-[6px] border-t-emerald-500 flex flex-col justify-center p-6 text-center font-mono text-xs text-slate-400 space-y-3">
                <ShieldAlert className="w-10 h-10 text-emerald-400/40 mx-auto" />
                <p className="font-bold text-slate-200 text-sm">Deterministic Posture Locked</p>
                <p>Residual heuristic modeling disabled for this profile scope. All risk metrics are derived strictly from empirical evidence graphs.</p>
              </Card>
            )}
          </div>

          {/* Interactive Creative Studios */}
          <div className="space-y-8">
            <RiskAutopsy score={score.data} />
            <PdssBreakdown score={score.data} />
            <WhatIfSimulator
              score={score.data}
              findings={findings.data || []}
              identifierId={identifierId || undefined}
            />
            <NarrativeBriefing identifierId={identifierId || undefined} />
          </div>

          {/* Score Historical Trend Repository */}
          <Card className="border-white/10 bg-slate-900/70 shadow-lg">
            <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <LineChart className="h-5 w-5 text-cyan-400" /> Historical Score Chronology & Remediation Impact
                </CardTitle>
                <Badge variant="outline" className="text-xs font-mono border-slate-700 text-slate-300">
                  {(history.data || []).length} Records Logged
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-slate-400">
                Track historical PDSS trajectories before and after automated neutralization runs.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-5 space-y-2 text-xs font-mono">
              {(history.data || []).map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-xl border border-white/10 bg-slate-950/50 p-3.5 hover:bg-slate-900/80 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Badge className={cn("text-[10px] font-bold uppercase w-20 justify-center",
                      item.severity === "critical" || item.severity === "high" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" :
                      item.severity === "medium" ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    )}>
                      {item.severity}
                    </Badge>
                    <div>
                      <span className="font-bold text-white text-base mr-2">{item.score_combined.toFixed(1)}</span>
                      <span className="text-slate-400">Trigger: <strong className="text-slate-200 uppercase">{item.trigger}</strong></span>
                    </div>
                  </div>
                  <span className="text-slate-400 text-[11px]">
                    {formatDate(item.created_at)}
                  </span>
                </div>
              ))}

              {!history.isLoading && !(history.data || []).length && (
                <div className="py-12 text-center text-slate-400 font-mono text-xs space-y-2">
                  <FileSearch className="w-8 h-8 text-slate-500 mx-auto" />
                  <p>No historical PDSS calculations logged for this scope yet.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        /* Meaningful Empty State when no score exists */
        <Card className="border-white/10 bg-slate-900/40 p-16 text-center text-slate-300 font-mono space-y-5 rounded-2xl shadow-xl">
          <div className="rounded-2xl bg-cyan-500/10 p-4 border border-cyan-500/20 w-20 h-20 mx-auto flex items-center justify-center shadow-inner">
            <Target className="h-10 w-10 text-cyan-400 animate-bounce" />
          </div>
          <div className="space-y-2 max-w-lg mx-auto">
            <h3 className="text-xl font-bold text-white tracking-tight">Zero Posture Quantifications Recorded</h3>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              The PDSS calculation engine requires active discovery findings or verified identity anchors to compute attack surface risk vectors. Execute an initial scan and trigger computation.
            </p>
          </div>
          <div className="pt-2">
            <Button
              variant="cyber"
              size="lg"
              onClick={() => compute.mutate({ identifier_id: identifierId || undefined, persist: true })}
              disabled={compute.isPending}
              className="font-mono font-bold text-xs shadow-lg shadow-cyan-500/30 px-6 h-11"
            >
              {compute.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2 text-cyan-300" />}
              {compute.isPending ? "Evaluating Identity Graph..." : "Compute Initial PDSS Score Now"}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
