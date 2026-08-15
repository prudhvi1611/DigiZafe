import React, { useState } from "react";
import {
  Download,
  Eye,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  Trash2,
  AlertTriangle,
  FileText,
  Terminal,
  Database,
  Lock,
  Loader2,
  CheckCircle2,
  ShieldAlert
} from "lucide-react";
import {
  useAuditEvents,
  useConsent,
  useCreateExport,
  useEgressEvents,
  useExportPackage,
  useGrantConsent,
  useRequestAccountDeletion,
  useRevokeConsent,
} from "./api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatDate, cn } from "@/lib/utils";

export function PrivacyPage() {
  const consent = useConsent();
  const audit = useAuditEvents();
  const egress = useEgressEvents();

  const createExport = useCreateExport();
  const exportPackage = useExportPackage(createExport.data?.id);
  const grant = useGrantConsent();
  const revoke = useRevokeConsent();
  const deletion = useRequestAccountDeletion();

  const [purpose, setPurpose] = useState("discovery.xposedornot");
  const [scope, setScope] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const startExport = async () => {
    try {
      await createExport.mutateAsync({
        include_audit: true,
        include_egress: true,
      });
      setMessage("✅ Cryptographic data export package successfully compiled and ready for local extraction.");
    } catch (error) {
      setMessage(`❌ Export generation failed: ${(error as Error).message}`);
    }
  };

  const downloadExport = () => {
    const packageData = exportPackage.data?.package;
    if (!packageData) return;

    const blob = new Blob([JSON.stringify(packageData, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "digizafe-data-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const executeDeletion = async () => {
    try {
      await deletion.mutateAsync({
        confirm_phrase: confirmPhrase,
        immediate: false,
      });
      setMessage("🚨 Account deletion and permanent cryptographic shredding scheduled.");
      setShowDeleteModal(false);
    } catch (error) {
      setMessage(`❌ Deletion failure: ${(error as Error).message}`);
    }
  };

  return (
    <div className="space-y-8 mt-8 animate-fade-in text-slate-100 pb-16">
      {/* Privacy Governance Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 pb-4 border-b border-white/10">
        <div className="space-y-1.5 border-l-4 border-violet-500 pl-4 py-1">
          <div className="flex items-center gap-2.5">
            <LockKeyhole className="h-7 w-7 text-violet-400 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-violet-300 bg-clip-text text-transparent">
              Privacy & Cryptographic Governance Center
            </h1>
            <Badge className="bg-violet-500/20 text-violet-300 border border-violet-500/30 text-xs uppercase font-mono tracking-wider">
              Zero-Egress Boundary
            </Badge>
          </div>
          <p className="text-sm text-slate-400 max-w-3xl font-mono">
            Full control over your identity records, cryptographic data exports, processing consent mandates, and immutable audit ledgers.
          </p>
        </div>
      </div>

      {message && (
        <div
          className="rounded-xl border border-cyan-500/40 bg-slate-900/90 p-4 text-xs font-mono text-cyan-200 shadow-md flex items-center gap-3 animate-slide-up"
          role="status"
        >
          <Terminal className="w-5 h-5 text-cyan-400 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* SECTION 1: DATA SOVEREIGNTY & SHREDDING STUDIO */}
      <section className="grid gap-6 lg:grid-cols-2">
        {/* Export Card */}
        <Card className="border-white/10 bg-slate-900/70 shadow-lg overflow-hidden border-t-[6px] border-t-cyan-500 flex flex-col justify-between">
          <div>
            <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                  <Download className="h-5 w-5 text-cyan-400" /> Cryptographic Data Export
                </CardTitle>
                <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-mono uppercase">
                  JSON ARCHIVE
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-slate-400">
                Compile a verifiable machine-readable archive of all identity anchors, findings, and processing logs stored in your local repository.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 space-y-4">
              <div className="bg-slate-950/50 p-4 rounded-xl border border-white/10 text-xs font-mono space-y-2 text-slate-300">
                <p className="font-semibold text-cyan-300">Included Intelligence Payloads:</p>
                <ul className="list-disc list-inside space-y-1 text-slate-400 text-[11px]">
                  <li>All verified and candidate identity anchors and attributes</li>
                  <li>Historical PDSS risk vector calculations and ML signals</li>
                  <li>Complete immutable audit trail & zero-egress network ledgers</li>
                  <li>Generated legal CCPA/GDPR erasure drafts and complaint records</li>
                </ul>
              </div>

              {createExport.data && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 text-xs font-mono space-y-3 animate-fade-in">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-cyan-300">Archive Package Ready:</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] uppercase border-cyan-500 text-cyan-300 bg-black/40">
                        {createExport.data.status}
                      </Badge>
                      <span className="text-slate-300 font-bold">
                        {(createExport.data.size_bytes / 1024).toFixed(1)} KB
                      </span>
                    </div>
                  </div>

                  {exportPackage.data?.package ? (
                    <Button
                      variant="cyber"
                      className="w-full font-mono font-bold text-xs h-10 shadow-lg shadow-cyan-500/20"
                      onClick={downloadExport}
                    >
                      <Download className="w-4 h-4 mr-2" /> Download JSON Archive
                    </Button>
                  ) : (
                    <div className="text-center text-slate-400 py-2 flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-cyan-400" /> Retrieving encrypted package payload...
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </div>

          <div className="p-6 pt-0">
            <Button
              variant="outline"
              onClick={startExport}
              disabled={createExport.isPending}
              className="w-full font-mono font-semibold text-xs h-10 border-white/15 bg-white/5 hover:bg-white/10"
            >
              {createExport.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin text-cyan-400" /> : <Database className="w-4 h-4 mr-2 text-cyan-400" />}
              {createExport.isPending ? "Compiling Cryptographic Package..." : "Create Data Export"}
            </Button>
          </div>
        </Card>

        {/* Shredding & Deletion Card */}
        <Card className="border-white/10 bg-slate-900/70 shadow-lg overflow-hidden border-t-[6px] border-t-rose-600 flex flex-col justify-between">
          <div>
            <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                  <Trash2 className="h-5 w-5 text-rose-500" /> Account Crypto-Shredding
                </CardTitle>
                <Badge className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono uppercase">
                  IRREVERSIBLE ACTION
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-slate-400">
                Initiate a complete cryptographic erasure of your user profile, encryption keypairs, and local database rows.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 space-y-4">
              <div className="bg-rose-950/20 border border-rose-500/30 p-4 rounded-xl text-xs font-mono text-rose-200 space-y-2">
                <div className="flex items-center gap-2 font-bold text-rose-300">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>Permanent Cryptographic Destruction</span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Upon authorization, DigiZafe immediately rotates and overwrites your master database key wrapping parameters, making recovery of your historical scans and findings impossible.
                </p>
              </div>

              <div className="space-y-1.5 font-mono text-xs">
                <Label htmlFor="delete-phrase" className="text-slate-300">
                  Type <span className="text-rose-400 font-bold">DELETE MY DIGIZAFE ACCOUNT</span> to authorize
                </Label>
                <Input
                  id="delete-phrase"
                  value={confirmPhrase}
                  onChange={(event) => setConfirmPhrase(event.target.value)}
                  placeholder="DELETE MY DIGIZAFE ACCOUNT"
                  className="bg-slate-950 border-white/15 h-10 font-mono text-xs text-white focus:border-rose-500"
                />
              </div>
            </CardContent>
          </div>

          <div className="p-6 pt-0">
            <Button
              variant="destructive"
              onClick={() => setShowDeleteModal(true)}
              disabled={confirmPhrase !== "DELETE MY DIGIZAFE ACCOUNT" || deletion.isPending}
              className="w-full font-mono font-bold text-xs h-10 shadow-lg shadow-rose-500/20"
            >
              <Trash2 className="w-4 h-4 mr-2" /> Shred Account & Crypto-Purge
            </Button>
          </div>
        </Card>
      </section>

      {/* Custom Confirmation Dialog for Account Deletion */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-rose-500/50 rounded-xl p-6 max-w-md w-full space-y-5 shadow-2xl animate-scale-up">
            <div className="flex items-center gap-3 text-rose-400 border-b border-white/10 pb-3">
              <AlertTriangle className="w-7 h-7 shrink-0 animate-pulse" />
              <div>
                <h3 className="text-lg font-bold text-white">Confirm Permanent Shred</h3>
                <p className="text-xs font-mono text-slate-400">Irreversible cryptographic destruction</p>
              </div>
            </div>
            <p className="text-xs font-mono text-slate-300 leading-relaxed">
              Are you absolutely certain? This will immediately schedule your account and all associated telemetry for permanent deletion and crypto-shredding.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDeleteModal(false)}
                className="text-xs font-mono text-slate-400 hover:text-white"
              >
                Cancel / Abort
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={executeDeletion}
                disabled={deletion.isPending}
                className="text-xs font-mono font-bold h-9 px-4 shadow-lg shadow-rose-500/30"
              >
                {deletion.isPending ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : null}
                Yes, Delete Account
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: CONSENT CENTER & ZERO-EGRESS BOUNDARY */}
      <Card className="border-white/10 bg-slate-900/70 shadow-lg overflow-hidden border-l-[6px] border-l-amber-500">
        <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-amber-400" /> External Processing Consent Center
            </CardTitle>
            <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-mono uppercase">
              Explicit Authorization Required
            </Badge>
          </div>
          <CardDescription className="text-xs font-mono text-slate-400">
            DigiZafe strictly adheres to zero-egress default isolation. Inspect and manage which specific processing purposes have been authorized to communicate with external threat feeds.
          </CardDescription>
        </CardHeader>

        <CardContent className="p-6 space-y-6 font-mono text-xs">
          <div className="bg-slate-950/40 p-4 rounded-xl border border-white/10 space-y-3">
            <p className="font-bold text-slate-200 text-sm">Grant New Processing Authorization Scope</p>
            <div className="grid gap-3 md:grid-cols-[2fr_2fr_auto]">
              <div className="space-y-1">
                <Label className="text-[11px] text-slate-400">Target Processing Purpose</Label>
                <Input
                  value={purpose}
                  onChange={(event) => setPurpose(event.target.value)}
                  placeholder="discovery.xposedornot"
                  className="bg-slate-900 border-white/15 h-9 font-mono text-xs text-white"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-slate-400">Optional Constraint Scope</Label>
                <Input
                  value={scope}
                  onChange={(event) => setScope(event.target.value)}
                  placeholder="Optional scope parameters"
                  className="bg-slate-900 border-white/15 h-9 font-mono text-xs text-white"
                />
              </div>
              <div className="flex items-end">
                <Button
                  variant="cyber"
                  onClick={() => grant.mutate({ purpose, scope: scope || undefined })}
                  disabled={!purpose || grant.isPending}
                  className="h-9 px-6 font-mono font-bold text-xs bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                >
                  {grant.isPending ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />}
                  Grant Consent
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-2.5">
            <h4 className="font-bold text-slate-300 uppercase text-[11px] tracking-wider">Active & Historical Grant Ledger</h4>
            {(consent.data || []).map((item) => (
              <div
                key={`${item.id || item.purpose}-${item.created_at}`}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl border border-white/10 bg-slate-950/60 p-4 hover:bg-slate-900/80 transition-colors"
              >
                <div className="space-y-1">
                  <div className="font-bold text-white text-sm flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5 text-amber-400" />
                    <span>{item.purpose}</span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Constraint Scope: <strong className="text-slate-200">{item.scope || "Global / Unscoped"}</strong> · Granted on {formatDate(item.created_at)}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <Badge variant={item.granted ? "default" : "secondary"} className={cn("text-[10px] font-mono uppercase font-bold",
                    item.granted ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                  )}>
                    {item.granted ? "AUTHORIZED (GRANTED)" : "REVOKED / LOCKED"}
                  </Badge>

                  {item.granted && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => revoke.mutate(item.purpose)}
                      className="text-xs font-mono text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 h-8"
                    >
                      Revoke Authorization
                    </Button>
                  )}
                </div>
              </div>
            ))}

            {!consent.isLoading && !(consent.data || []).length && (
              <div className="py-8 text-center font-mono text-slate-400 text-xs border border-dashed border-white/10 rounded-xl">
                No active external processing consent authorizations recorded in this profile repository.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* SECTION 3: IMMUTABLE AUDIT & EGRESS TELEMETRY LEDGER */}
      <section className="grid gap-6 xl:grid-cols-2">
        {/* Audit Transparency */}
        <Card className="border-white/10 bg-slate-900/60 shadow-md flex flex-col">
          <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <Eye className="h-4 w-4 text-cyan-400" /> Immutable Audit Transparency Stream
            </CardTitle>
            <CardDescription className="text-xs font-mono text-slate-400">
              Cryptographically verified logging of all local profiling and scan executions.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-5 max-h-[360px] space-y-2 overflow-y-auto font-mono text-xs flex-1">
            {(audit.data || []).map((event) => (
              <div key={event.id} className="rounded-lg border border-white/10 bg-slate-950/60 p-3 text-xs flex flex-col gap-1 hover:bg-slate-900/80 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold text-cyan-300">{event.action}</span>
                  <span className="text-[10px] text-slate-500">
                    {formatDate(event.created_at)}
                  </span>
                </div>
                {event.resource_type && (
                  <div className="text-[11px] text-slate-400 truncate">
                    Target: <strong className="text-slate-200">{event.resource_type}</strong> · {event.resource_id || "—"}
                  </div>
                )}
              </div>
            ))}

            {!audit.isLoading && !(audit.data || []).length && (
              <div className="py-12 text-center text-slate-400 text-xs font-mono">
                No historical audit log events present in repository.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Egress Ledger */}
        <Card className="border-white/10 bg-slate-900/60 shadow-md flex flex-col">
          <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" /> Zero-Egress Network Transmission Ledger
            </CardTitle>
            <CardDescription className="text-xs font-mono text-slate-400">
              Strict documentation of external network hosts contacted during authorized processing.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-5 max-h-[360px] space-y-2 overflow-y-auto font-mono text-xs flex-1">
            {(egress.data || []).map((event) => (
              <div key={event.id} className="rounded-lg border border-white/10 bg-slate-950/60 p-3 text-xs flex flex-col gap-1.5 hover:bg-slate-900/80 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold text-white truncate max-w-[220px]">{event.destination_host}</span>
                  <Badge variant={event.success ? "default" : "destructive"} className={cn("text-[10px] uppercase font-bold",
                    event.success ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                  )}>
                    {event.success ? "TRANSMITTED (SUCCESS)" : "BLOCKED / FAILED"}
                  </Badge>
                </div>
                <div className="text-[11px] text-slate-400 flex items-center justify-between gap-2">
                  <span>Purpose: <strong className="text-slate-200">{event.purpose}</strong> ({event.method})</span>
                  <span className="text-[10px] text-slate-500">{formatDate(event.created_at)}</span>
                </div>
              </div>
            ))}

            {!egress.isLoading && !(egress.data || []).length && (
              <div className="py-12 text-center text-slate-400 text-xs font-mono">
                No external network egress transactions logged in this session.
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
