import React from "react";
import { useParams, Link } from "react-router-dom";
import { useScan } from "./api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";
import { Radar, AlertTriangle, Server, ShieldCheck, ArrowRight, Activity } from "lucide-react";

export function ScanDetailPage() {
  const { scanId } = useParams();
  const { data: scan, isLoading } = useScan(scanId);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <Skeleton className="h-12 w-1/3" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }
  if (!scan) return <div className="p-8 border border-white/10 bg-slate-900 rounded-xl text-center text-rose-400 font-mono text-sm">Scan not found</div>;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Scan Detail Header */}
      <div className="flex items-center justify-between border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status={scan.status === "completed" ? "secure" : "active"} label={scan.status.toUpperCase()} pulse={scan.status === "running"} />
            <span className="text-xs font-mono text-slate-400">ID: {scan.id}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1 flex items-center gap-2">
            <Radar className="h-7 w-7 text-cyan-400" />
            Scan detail
          </h1>
        </div>
        <Button asChild variant="cyber" size="sm" className="font-semibold shadow-md">
          <Link to="/app/findings">
            Findings <ArrowRight className="w-4 h-4 ml-1.5" />
          </Link>
        </Button>
      </div>

      <Card className="border-white/10 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 shadow-2xl backdrop-blur-md">
        <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-4 flex flex-row items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-3 text-white text-base">
              <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono uppercase text-xs px-3">
                {scan.status}
              </Badge>
              <Badge variant="outline" className="border-white/15 bg-white/5 font-mono uppercase text-xs px-3 text-slate-300">
                {scan.layer_scope}
              </Badge>
              <span className="text-xs font-mono text-slate-400 hidden sm:inline-block">{scan.id}</span>
            </CardTitle>
            <CardDescription className="text-xs font-mono text-slate-300">
              {scan.message || "Orchestrated discovery complete."}
            </CardDescription>
          </div>
          <div className="font-mono text-2xl font-bold text-cyan-400">
            {scan.progress_pct}%
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6 p-6">
          <Progress value={scan.progress_pct} className="h-2 bg-slate-800" />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
            <div className="rounded-xl border border-white/10 bg-black/30 p-3.5 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold">Timings</div>
              <div className="text-slate-300">Created: <strong className="text-white">{formatDate(scan.created_at)}</strong></div>
              <div className="text-slate-300">Finished: <strong className="text-white">{scan.finished_at ? formatDate(scan.finished_at) : "In progress"}</strong></div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/30 p-3.5 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold">Observations</div>
              <div className="text-2xl font-bold text-cyan-400">{scan.observation_count}</div>
              <div className="text-slate-400 text-[10px]">Surface items ingested</div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/30 p-3.5 space-y-1">
              <div className="text-slate-500 text-[10px] uppercase font-bold">Confirmed Findings</div>
              <div className="text-2xl font-bold text-amber-400">{scan.finding_count}</div>
              <div className="text-slate-400 text-[10px]">Actionable exposure threats</div>
            </div>
          </div>

          {(scan.meta as { attributions?: string[] } | null)?.attributions && (
            <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs font-mono text-slate-300 flex flex-wrap items-center gap-2">
              <span className="text-slate-400">Attributions:</span>
              <strong className="text-cyan-300">{(scan.meta as { attributions: string[] }).attributions.join(", ")}</strong>
            </div>
          )}

          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-slate-400 flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan-400" />
              Connector Execution Logs
            </h3>
            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {(scan.connector_runs || []).map((r, i) => (
                <div key={r.id || i} className="rounded-lg border border-white/10 bg-black/20 p-3.5 text-xs font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-white/[0.03] transition-colors">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="text-[10px] uppercase bg-cyan-500/10 border-cyan-500/30 text-cyan-300">
                      {r.status}
                    </Badge>
                    <span className="font-bold text-white text-sm">{r.connector_id}</span>
                  </div>
                  <div className="text-slate-400 flex flex-wrap items-center gap-3">
                    <span>obs: <strong className="text-cyan-400">{r.observation_count}</strong></span>
                    <span>findings: <strong className="text-amber-400">{r.finding_count}</strong></span>
                    {r.skip_reason ? <span className="text-amber-300/80">skip: {r.skip_reason}</span> : null}
                    {r.error ? <span className="text-rose-400">err: {r.error}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
