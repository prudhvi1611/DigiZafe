import React, { useState } from "react";
import {
  useIdentifiers,
  useCreateIdentifier,
  useDeleteIdentifier,
  useStartVerify,
  useConfirmVerify,
} from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";
import type { IdentifierType } from "@/lib/types";
import { Fingerprint, Shield, Trash2, CheckCircle, Clock, AlertTriangle, KeyRound, Radio } from "lucide-react";

const TYPES: IdentifierType[] = ["email", "domain", "github_username", "username", "phone"];

export function IdentifiersPage() {
  const { data, isLoading } = useIdentifiers();
  const create = useCreateIdentifier();
  const del = useDeleteIdentifier();
  const start = useStartVerify();
  const confirm = useConfirmVerify();

  const [type, setType] = useState<IdentifierType>("email");
  const [value, setValue] = useState("");
  const [challenge, setChallenge] = useState<{
    id: string;
    challenge_id: string;
    method: string;
    instructions: Record<string, unknown>;
    dev_code?: string | null;
  } | null>(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    try {
      await create.mutateAsync({ type, value });
      setValue("");
      setMsg("Identifier added (unverified).");
    } catch (err) {
      setMsg((err as Error).message);
    }
  };

  const verifiedCount = (data || []).filter((i) => i.is_verified).length;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status="secure" label="VERIFIED ANCHOR TARGETS" pulse={false} />
            <span className="text-xs font-mono text-slate-400">G1 ENCLAVE BOUNDARY</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1">Identifiers</h1>
          <p className="text-sm text-slate-400 max-w-2xl leading-relaxed mt-1">
            G1: only <strong>verified</strong> identifiers can be scanned. Free path never requires paid APIs.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2 text-xs font-mono text-slate-300">
          <Fingerprint className="h-4 w-4 text-cyan-400 shrink-0" />
          <span>Verified Ratio: <strong className="text-white font-bold">{verifiedCount}</strong> / {(data || []).length}</span>
        </div>
      </div>

      {/* Add Identifier Command Form */}
      <Card className="border-white/10 bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 shadow-xl backdrop-blur-md">
        <CardHeader className="border-b border-white/5 bg-white/[0.02] pb-4">
          <CardTitle className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <Radio className="h-4 w-4 text-cyan-400 animate-pulse" />
            Add identifier
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Register cryptographic attack surfaces for continuous personal intelligence tracking.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-5">
          <form onSubmit={onAdd} className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div className="space-y-1.5 sm:w-48">
              <Label className="text-xs font-mono uppercase tracking-wider text-slate-300">Type</Label>
              <select
                className="flex h-10 w-full rounded-lg border border-white/15 bg-slate-900 px-3 text-xs font-mono text-white shadow-sm transition-colors focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                value={type}
                onChange={(e) => setType(e.target.value as IdentifierType)}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t} className="bg-slate-900 text-white">
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1 space-y-1.5">
              <Label className="text-xs font-mono uppercase tracking-wider text-slate-300">Value</Label>
              <Input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                required
                placeholder="you@example.com"
                className="font-mono text-sm border-white/15 bg-slate-950 focus:border-cyan-400"
              />
            </div>
            <Button type="submit" variant="cyber" disabled={create.isPending} className="h-10 px-6 font-semibold shadow-md">
              {create.isPending ? "Registering..." : "Add"}
            </Button>
          </form>
          {msg && (
            <p className="mt-3 text-xs font-mono text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded-md p-2 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-cyan-400 shrink-0" />
              {msg}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Active Verification Challenge Dialog / Card */}
      {challenge && (
        <Card className="border-cyan-500/40 bg-gradient-to-b from-slate-900 to-slate-950 shadow-[0_0_30px_rgba(6,182,212,0.2)] border-2 animate-in fade-in-50 duration-300">
          <CardHeader className="border-b border-cyan-500/20 bg-cyan-500/10 pb-4">
            <div className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-cyan-300 animate-bounce" />
              <div>
                <CardTitle className="text-base font-bold text-white tracking-tight">
                  Verification — {challenge.method}
                </CardTitle>
                <CardDescription className="text-xs text-cyan-200/80 mt-0.5 font-mono">
                  {typeof challenge.instructions.message === "string"
                    ? challenge.instructions.message
                    : JSON.stringify(challenge.instructions)}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            {challenge.dev_code && (
              <p className="rounded-lg border border-amber-500/40 bg-amber-500/15 p-3 text-xs font-mono text-amber-300 shadow-sm flex items-center justify-between">
                <span>LOCAL DEV VERIFICATION TOKEN:</span>
                <code className="bg-black/40 px-2 py-1 rounded text-sm font-bold tracking-widest text-amber-200 select-all">
                  {challenge.dev_code}
                </code>
              </p>
            )}
            {challenge.method === "email_code" && (
              <div className="space-y-1.5 max-w-sm">
                <Label className="text-xs font-mono text-slate-300">Verification Code</Label>
                <Input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Enter token code..."
                  className="font-mono text-center tracking-widest text-base"
                />
              </div>
            )}
            {(challenge.method === "dns_txt" || challenge.method === "github_proof") && (
              <pre className="overflow-auto rounded-lg border border-white/10 bg-black/50 p-4 font-mono text-xs text-slate-300">
                {JSON.stringify(challenge.instructions, null, 2)}
              </pre>
            )}
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setChallenge(null);
                  setCode("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="cyber"
                onClick={async () => {
                  await confirm.mutateAsync({
                    id: challenge.id,
                    challenge_id: challenge.challenge_id,
                    code: challenge.method === "email_code" ? code : undefined,
                  });
                  setChallenge(null);
                  setCode("");
                }}
                disabled={confirm.isPending}
              >
                {confirm.isPending ? "Confirming..." : "Confirm verification"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Identifiers Investigation List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-bold tracking-tight text-white uppercase font-mono">Registered Surface Map</h3>
          <span className="text-xs text-slate-500 font-mono">{(data || []).length} Records</span>
        </div>

        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
          </div>
        )}

        {!(data || []).length && !isLoading && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-12 text-center text-slate-400 font-mono text-sm">
            No personal identifiers registered yet. Add an email or handle above to begin zero-egress surface mapping.
          </div>
        )}

        {(data || []).map((id) => (
          <Card key={id.id} className="group border-white/10 bg-slate-900/60 hover:bg-slate-900/80 transition-all duration-200 shadow-md">
            <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-bold text-white tracking-tight text-base truncate">{id.value_display}</span>
                  <Badge variant="outline" className="font-mono text-[10px] uppercase bg-white/[0.04] border-white/15">
                    {id.type}
                  </Badge>
                  <Badge
                    variant={id.is_verified ? "default" : "secondary"}
                    className={
                      id.is_verified
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-mono"
                    }
                  >
                    {id.is_verified ? "verified" : "unverified"}
                  </Badge>
                </div>
                <p className="text-xs font-mono text-slate-400 truncate">
                  canonical: <span className="text-slate-300">{id.value_canonical}</span>
                  {id.verified_at ? ` · verified ${formatDate(id.verified_at)}` : ""}
                </p>
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                {!id.is_verified && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="font-medium text-xs border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-200 shadow-sm"
                    onClick={async () => {
                      const r = await start.mutateAsync({ id: id.id });
                      setChallenge({
                        id: id.id,
                        challenge_id: r.challenge_id,
                        method: r.method,
                        instructions: r.instructions,
                        dev_code: r.dev_code,
                      });
                      if (r.dev_code) setCode(r.dev_code);
                    }}
                  >
                    Verify
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-slate-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
                  onClick={() => del.mutate(id.id)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
