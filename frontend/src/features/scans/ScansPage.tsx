import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, LockKeyhole, ShieldCheck, Radar, Server, Activity, Clock, Play, StopCircle, ArrowRight } from "lucide-react";

import { useIdentifiers } from "@/features/identifiers/api";
import { useConsent, useGrantConsent } from "@/features/privacy/api";
import { useCreateScan, useScans, useCancelScan } from "./api";
import { LayerScopeControl } from "./LayerScopeControl";
import { openScanSse } from "@/lib/sse";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

import type {
  ExposureLayer,
  ScanPublic,
} from "@/lib/types";

const TERMINAL_STATUSES = [
  "completed",
  "partial",
  "failed",
  "cancelled",
  "timed_out",
];

function consentPurpose(layer: ExposureLayer): string | null {
  if (layer === "deep") return "discovery.deep";
  if (layer === "constrained_dark") return "discovery.constrained_dark";
  return null;
}

export function ScansPage() {
  const ids = useIdentifiers();
  const consents = useConsent();
  const scans = useScans();
  const create = useCreateScan();
  const cancel = useCancelScan();
  const grantConsent = useGrantConsent();

  const verified = (ids.data || []).filter((item) => item.is_verified);

  const [selectedIdentifier, setSelectedIdentifier] = useState("");
  const [layerScope, setLayerScope] = useState<ExposureLayer>("surface");
  const [live, setLive] = useState<ScanPublic | null>(null);
  const [sseNote, setSseNote] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const requiredPurpose = consentPurpose(layerScope);

  const hasConsent = useMemo(
    () => (layer: ExposureLayer) => {
      const purpose = consentPurpose(layer);
      if (!purpose) return true;

      return Boolean(
        (consents.data || []).some(
          (item) => item.purpose === purpose && item.granted
        )
      );
    },
    [consents.data]
  );

  const selectedHasConsent = hasConsent(layerScope);

  useEffect(() => {
    if (!live?.id || TERMINAL_STATUSES.includes(live.status)) {
      return;
    }

    const stop = openScanSse(live.id, {
      onEvent: (event, data) => {
        if (
          event !== "scan" &&
          event !== "done" &&
          event !== "message"
        ) {
          return;
        }

        const payload = data as Partial<ScanPublic> & {
          scan_id?: string;
        };

        setLive((previous) =>
          previous
            ? {
                ...previous,
                status: payload.status || previous.status,
                progress_pct:
                  payload.progress_pct ?? previous.progress_pct,
                message: payload.message ?? previous.message,
                observation_count:
                  payload.observation_count ??
                  previous.observation_count,
                finding_count:
                  payload.finding_count ?? previous.finding_count,
                connector_runs:
                  payload.connector_runs ||
                  previous.connector_runs,
                meta: payload.meta ?? previous.meta,
              }
            : previous
        );

        if (event === "done") {
          setSseNote("Scan finished.");
        }
      },
      onError: (error) => setSseNote(error.message),
    });

    return stop;
  }, [live?.id, live?.status]);

  const grantAmberConsent = async () => {
    if (!requiredPurpose) return;

    await grantConsent.mutateAsync({
      purpose: requiredPurpose,
      scope: layerScope,
      details: {
        source: "scan_layer_control",
        layer: layerScope,
      },
    });

    setMessage(`Consent granted for ${layerScope} discovery.`);
  };

  const startScan = async () => {
    setMessage(null);

    if (!selectedIdentifier) {
      setMessage("Select a verified identifier.");
      return;
    }

    if (!selectedHasConsent) {
      setMessage(
        `Grant explicit consent for ${layerScope} before starting this scan.`
      );
      return;
    }

    try {
      const scan = await create.mutateAsync({
        identifier_id: selectedIdentifier,
        layer_scope: layerScope,
      });

      setLive(scan);
      setSseNote("SSE connected.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Console Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status="active" label="ORCHESTRATED INTELLIGENCE" pulse />
            <span className="text-xs font-mono text-slate-400">IN-MEMORY STREAMING ENGINE</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1 flex items-center gap-2.5">
            <Radar className="h-7 w-7 text-cyan-400" />
            Scans
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400 leading-relaxed">
            Start with Surface discovery. Deep and Constrained-Dark scans are
            optional Amber layers requiring explicit consent and provide
            metadata-only, best-effort coverage.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2 text-xs font-mono text-slate-300">
          <Server className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>Active Engines: <strong className="text-white font-bold">100% Online</strong></span>
        </div>
      </div>

      {/* Discovery Layer Controller */}
      <Card className="border-white/10 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 shadow-2xl backdrop-blur-md">
        <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-4">
          <CardTitle className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            Choose discovery layer
          </CardTitle>
          <CardDescription className="text-xs text-slate-400 font-mono">
            Amber scans never perform unrestricted crawling or direct onion access.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6 pt-6">
          <LayerScopeControl
            value={layerScope}
            onChange={setLayerScope}
            hasConsent={hasConsent}
          />

          {layerScope !== "surface" && !selectedHasConsent && (
            <div className="flex flex-col gap-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-xs font-mono text-amber-100 md:flex-row md:items-center md:justify-between shadow-lg">
              <div className="flex items-center gap-3">
                <LockKeyhole className="h-6 w-6 text-amber-400 shrink-0" />
                <span>
                  This layer requires explicit privacy boundary consent for{" "}
                  <code className="bg-black/40 px-1.5 py-0.5 rounded font-bold text-amber-300">{requiredPurpose}</code>.
                </span>
              </div>

              <Button
                variant="secondary"
                size="sm"
                className="bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border-amber-500/40 font-semibold shrink-0"
                onClick={grantAmberConsent}
                disabled={grantConsent.isPending}
              >
                Grant consent
              </Button>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-[1fr_auto]">
            <div className="space-y-1">
              <select
                aria-label="Verified identifier"
                className="flex h-11 w-full rounded-lg border border-white/15 bg-slate-950 px-4 text-xs font-mono text-white shadow-inner transition-colors focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                value={selectedIdentifier}
                onChange={(event) =>
                  setSelectedIdentifier(event.target.value)
                }
              >
                <option value="" className="bg-slate-900 text-slate-400">
                  Select verified identifier…
                </option>

                {verified.map((identifier) => (
                  <option key={identifier.id} value={identifier.id} className="bg-slate-900 text-white">
                    {identifier.type}: {identifier.value_display}
                  </option>
                ))}
              </select>
            </div>

            <Button
              variant="cyber"
              className="h-11 px-8 font-semibold shadow-lg shadow-cyan-500/25 text-sm"
              onClick={startScan}
              disabled={
                !selectedIdentifier ||
                !selectedHasConsent ||
                create.isPending
              }
            >
              <Play className="mr-2 h-4 w-4 text-cyan-300 fill-cyan-300" />
              {create.isPending ? "Queueing…" : "Start scan"}
            </Button>
          </div>

          {message && (
            <p className="rounded-lg bg-white/[0.04] border border-white/10 p-3 text-xs font-mono text-amber-300" role="status">
              {message}
            </p>
          )}

          <div className="border-t border-white/10 pt-4 flex flex-wrap gap-6 text-xs font-mono text-slate-400">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              Verified-only enforcement
            </span>
            <span className="inline-flex items-center gap-1.5">
              <LockKeyhole className="h-4 w-4 text-cyan-400" />
              Consent logged cryptographically
            </span>
            <span className="inline-flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              Amber results may be historical or incomplete
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Live SSE Streaming Scan Card */}
      {live && (
        <Card className="border-cyan-500/40 bg-gradient-to-b from-slate-900 to-slate-950 shadow-[0_0_30px_rgba(6,182,212,0.2)] border-2 animate-in fade-in-50">
          <CardHeader className="border-b border-cyan-500/20 bg-cyan-500/10 pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-white text-base font-bold">
                <Radar className="h-5 w-5 text-cyan-400 animate-spin" style={{ animationDuration: '3s' }} />
                Live scan
                <Badge variant="outline" className="bg-white/10 text-cyan-300 border-cyan-500/40 font-mono uppercase text-xs px-2.5">
                  {live.status}
                </Badge>
                <Badge variant="secondary" className="bg-black/40 text-slate-300 font-mono text-[10px] uppercase">
                  {live.layer_scope}
                </Badge>
              </CardTitle>
              <CardDescription className="text-xs font-mono text-cyan-200 mt-1">
                {live.message || "Initializing surface connector pipeline..."}
              </CardDescription>
            </div>
            <div className="text-right font-mono text-sm font-bold text-cyan-400">
              {live.progress_pct?.toFixed?.(0) ?? live.progress_pct}%
            </div>
          </CardHeader>

          <CardContent className="space-y-5 pt-5">
            <Progress value={live.progress_pct || 0} className="h-2.5 bg-slate-800" />

            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-black/40 p-3 text-xs font-mono text-slate-300">
              <span>Telemetry Feed:</span>
              <div className="flex items-center gap-4">
                <span>observations: <strong className="text-cyan-400">{live.observation_count}</strong></span>
                <span>findings: <strong className="text-amber-400">{live.finding_count}</strong></span>
              </div>
            </div>

            <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
              {(live.connector_runs || []).map((run) => (
                <div
                  key={run.connector_id}
                  className="flex justify-between items-center rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-mono"
                >
                  <span className="font-semibold text-slate-200 flex items-center gap-2">
                    <Server className="h-3.5 w-3.5 text-cyan-400" />
                    {run.connector_id}
                  </span>
                  <span className="text-slate-400 flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] uppercase bg-white/[0.03] border-white/15">
                      {run.status}
                    </Badge>
                    {run.skip_reason
                      ? ` (${run.skip_reason})`
                      : ""}
                    {run.cache_hit ? <Badge variant="secondary" className="text-[9px] bg-emerald-500/20 text-emerald-300 border-0">CACHE</Badge> : ""}
                  </span>
                </div>
              ))}
            </div>

            {sseNote && (
              <p className="text-xs font-mono text-slate-500 text-right" role="status">
                {sseNote}
              </p>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              {!TERMINAL_STATUSES.includes(live.status) && (
                <Button
                  size="sm"
                  variant="outline"
                  className="border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20 font-semibold"
                  onClick={() => cancel.mutate(live.id)}
                >
                  <StopCircle className="w-4 h-4 mr-1.5" /> Cancel
                </Button>
              )}

              <Button asChild size="sm" variant="cyber" className="font-semibold shadow-md">
                <Link to={`/app/scans/${live.id}`}>
                  Open detail <ArrowRight className="w-4 h-4 ml-1.5" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Historical Orchestration Ledger */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-sm font-bold tracking-tight text-white uppercase font-mono flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            History
          </h2>
          <span className="text-xs text-slate-500 font-mono">{(scans.data || []).length} Recorded Executions</span>
        </div>

        {scans.isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-14 w-full rounded-lg" />
            <Skeleton className="h-14 w-full rounded-lg" />
            <Skeleton className="h-14 w-full rounded-lg" />
          </div>
        )}

        {(scans.data || []).map((scan) => (
          <Link
            key={scan.id}
            to={`/app/scans/${scan.id}`}
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-xl border border-white/10 bg-slate-900/40 px-4 py-3 text-xs font-mono hover:bg-slate-900/70 transition-all duration-200 group"
          >
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="bg-cyan-500/10 text-cyan-300 border-cyan-500/30 font-bold uppercase">
                {scan.layer_scope}
              </Badge>
              <Badge variant="secondary" className="bg-white/[0.05] text-slate-300 border-white/15 uppercase">
                {scan.status}
              </Badge>
              <span className="text-slate-300 font-semibold">
                <strong className="text-amber-400 font-bold">{scan.finding_count}</strong> findings
              </span>
            </div>

            <span className="text-slate-500 group-hover:text-slate-400 transition-colors">
              {formatDate(scan.created_at)}
            </span>
          </Link>
        ))}

        {!scans.isLoading && !(scans.data || []).length && (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-8 text-center text-slate-400 font-mono text-xs">
            No scans recorded in history yet. Launch a discovery run above.
          </div>
        )}
      </div>
    </div>
  );
}
