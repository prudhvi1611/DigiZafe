import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileText,
  KeyRound,
  Loader2,
  ShieldAlert,
  UserRoundCog,
  Sparkles,
  Play,
  StopCircle,
  RefreshCw,
  Sliders,
  AlertTriangle,
  Send,
  Lock,
  Database,
  Terminal,
  Layers
} from "lucide-react";
import { useIdentifiers } from "@/features/identifiers/api";
import {
  useBrokerCatalog,
  useBrokerStates,
  useCaptchaQueue,
  useCancelRemediationJob,
  useCreateComplaint,
  useCreateKnowRequest,
  useFreezeChecklist,
  useGeneratedRequests,
  useMarkRequestSent,
  useRemediationJobs,
  useSolveCaptcha,
  useStartBrokerOptOut,
  useUpdateFreezeItem,
  useVerifyBrokers,
} from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatDate, cn } from "@/lib/utils";

export function RemediationPage() {
  const identifiers = useIdentifiers();
  const catalog = useBrokerCatalog();
  const states = useBrokerStates();
  const jobs = useRemediationJobs();
  const captcha = useCaptchaQueue();
  const freeze = useFreezeChecklist();
  const requests = useGeneratedRequests();

  const startJob = useStartBrokerOptOut();
  const cancelJob = useCancelRemediationJob();
  const solveCaptcha = useSolveCaptcha();
  const updateFreeze = useUpdateFreezeItem();
  const verify = useVerifyBrokers();
  const createKnow = useCreateKnowRequest();
  const createComplaint = useCreateComplaint();
  const markSent = useMarkRequestSent();

  const verifiedEmails = useMemo(
    () =>
      (identifiers.data || []).filter(
        (item) => item.is_verified && item.type === "email"
      ),
    [identifiers.data]
  );

  const [identifierId, setIdentifierId] = useState("");
  const [selectedBrokers, setSelectedBrokers] = useState<string[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [zip, setZip] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"optout" | "telemetry" | "legal">("optout");

  const [knowRecipient, setKnowRecipient] = useState("");
  const [knowEmail, setKnowEmail] = useState("");
  const [complaintRecipient, setComplaintRecipient] = useState("");
  const [complaintFacts, setComplaintFacts] = useState("");

  const brokers = catalog.data?.brokers || [];

  const toggleBroker = (id: string) => {
    setSelectedBrokers((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  };

  const startOptOut = async () => {
    if (!identifierId) {
      setMessage("Please select a verified email identity anchor before dispatching remediation workers.");
      return;
    }

    try {
      await startJob.mutateAsync({
        identifier_id: identifierId,
        broker_ids: selectedBrokers.length ? selectedBrokers : undefined,
        dry_run: dryRun,
        profile: {
          display_name: displayName || undefined,
          state: state || undefined,
          city: city || undefined,
          zip: zip || undefined,
        },
      });

      setMessage(
        dryRun
          ? "✅ Dry-run neutralization job dispatched. Playwright worker will simulate opt-out sequences without submitting packets."
          : "🚀 Automated neutralization worker deployed! Live deletion forms are now being dispatched."
      );
    } catch (error) {
      setMessage(`❌ Error dispatching job: ${(error as Error).message}`);
    }
  };

  const stats = useMemo(() => {
    const activeJobsCount = (jobs.data || []).filter((j) => !["completed", "failed", "cancelled"].includes(j.status)).length;
    const captchaWaiting = (captcha.data || []).length;
    const freezeCompleted = (freeze.data || []).filter((f) => f.status === "done").length;
    const totalBrokers = brokers.length;
    return { activeJobsCount, captchaWaiting, freezeCompleted, totalBrokers };
  }, [jobs.data, captcha.data, freeze.data, brokers]);

  return (
    <div className="space-y-8 mt-8 animate-fade-in text-slate-100 pb-16">
      {/* Neutralization Console Header */}
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6 pb-4 border-b border-white/10">
        <div className="space-y-1.5 border-l-4 border-cyan-500 pl-4 py-1">
          <div className="flex items-center gap-2.5">
            <UserRoundCog className="h-7 w-7 text-cyan-400 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-cyan-300 bg-clip-text text-transparent">
              Automated Neutralization Console
            </h1>
            <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs uppercase font-mono tracking-wider">
              Zero-Egress Playwright Worker
            </Badge>
          </div>
          <p className="text-sm text-slate-400 max-w-3xl font-mono">
            Automated defensive removal pipeline targeting Green data brokers and leak aggregators. Local worker execution guarantees strict privacy with user-in-the-loop CAPTCHA arbitration.
          </p>
        </div>

        {/* Section Mode Navigation */}
        <div className="flex items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-white/10 shrink-0">
          <Button
            variant={activeTab === "optout" ? "cyber" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("optout")}
            className={cn("font-mono font-semibold text-xs px-4 h-9", activeTab === "optout" ? "shadow-md shadow-cyan-500/20" : "text-slate-400")}
          >
            <Play className="w-3.5 h-3.5 mr-2 text-cyan-400" />
            Neutralization Studio
          </Button>
          <Button
            variant={activeTab === "telemetry" ? "cyber" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("telemetry")}
            className={cn("font-mono font-semibold text-xs px-4 h-9", activeTab === "telemetry" ? "shadow-md shadow-cyan-500/20" : "text-slate-400")}
          >
            <Sliders className="w-3.5 h-3.5 mr-2 text-amber-400" />
            Worker Telemetry & CAPTCHA ({stats.captchaWaiting})
          </Button>
          <Button
            variant={activeTab === "legal" ? "cyber" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("legal")}
            className={cn("font-mono font-semibold text-xs px-4 h-9", activeTab === "legal" ? "shadow-md shadow-cyan-500/20" : "text-slate-400")}
          >
            <FileText className="w-3.5 h-3.5 mr-2 text-purple-400" />
            Legal & Freeze Matrix
          </Button>
        </div>
      </div>

      {/* Engine Telemetry Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-mono uppercase">Green Broker Catalog</p>
            <p className="text-2xl font-bold font-mono text-white mt-1">{stats.totalBrokers}</p>
          </div>
          <Database className="w-8 h-8 text-cyan-400/40" />
        </Card>

        <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-mono uppercase">Active Playwright Workers</p>
            <p className="text-2xl font-bold font-mono text-cyan-300 mt-1">{stats.activeJobsCount}</p>
          </div>
          <RefreshCw className={cn("w-8 h-8 text-cyan-300/40", stats.activeJobsCount > 0 && "animate-spin")} />
        </Card>

        <Card className={cn("border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between", stats.captchaWaiting > 0 && "border-amber-500/50 bg-amber-950/20")}>
          <div>
            <p className="text-xs text-slate-400 font-mono uppercase">CAPTCHA Interventions</p>
            <p className="text-2xl font-bold font-mono text-amber-400 mt-1">{stats.captchaWaiting}</p>
          </div>
          <KeyRound className="w-8 h-8 text-amber-400/50 animate-pulse" />
        </Card>

        <Card className="border-white/10 bg-slate-900/60 p-4 shadow-md flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-mono uppercase">Bureau Freezes Locked</p>
            <p className="text-2xl font-bold font-mono text-emerald-400 mt-1">{stats.freezeCompleted} / {(freeze.data || []).length || 4}</p>
          </div>
          <Lock className="w-8 h-8 text-emerald-400/40" />
        </Card>
      </div>

      {/* SECTION 1: NEUTRALIZATION STUDIO */}
      {activeTab === "optout" && (
        <Card className="border-white/10 bg-slate-900/70 shadow-xl overflow-hidden border-t-[6px] border-t-cyan-500">
          <CardHeader className="bg-slate-950/60 p-6 border-b border-white/10">
            <CardTitle className="text-xl font-bold text-white flex items-center gap-2.5">
              <Sparkles className="w-5 h-5 text-cyan-400" /> Dispatch Automated Broker Removal Playbook
            </CardTitle>
            <CardDescription className="text-slate-400 font-mono text-xs">
              Configure target identity anchors and defensive persona information. Playwright worker instances run locally in isolated container environments.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-6 space-y-6">
            {/* Identity & Persona Matrix */}
            <div className="bg-slate-950/40 p-5 rounded-xl border border-white/10 space-y-4">
              <h3 className="text-xs font-mono font-bold uppercase text-slate-400 tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-400" /> Target Anchor & Form Autofill Parameters
              </h3>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-1.5">
                  <Label htmlFor="remediation-identifier" className="text-xs font-mono text-slate-300">Verified Identity Email</Label>
                  <select
                    id="remediation-identifier"
                    className="flex h-10 w-full rounded-lg border border-white/15 bg-slate-900 px-3 text-xs font-mono text-white focus:border-cyan-500 outline-none"
                    value={identifierId}
                    onChange={(event) => setIdentifierId(event.target.value)}
                  >
                    <option value="">Select verified email…</option>
                    {verifiedEmails.map((identifier) => (
                      <option key={identifier.id} value={identifier.id}>
                        {identifier.value_display} ({identifier.type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="display-name" className="text-xs font-mono text-slate-300">Legal Name for Opt-Out Form</Label>
                  <Input
                    id="display-name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="Optional (e.g. Jane Doe)"
                    className="bg-slate-900 border-white/15 h-10 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="state" className="text-xs font-mono text-slate-300">Jurisdiction State</Label>
                  <Input
                    id="state"
                    value={state}
                    onChange={(event) => setState(event.target.value)}
                    placeholder="Optional (e.g. CA, NY, IL)"
                    className="bg-slate-900 border-white/15 h-10 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="city" className="text-xs font-mono text-slate-300">City</Label>
                  <Input
                    id="city"
                    value={city}
                    onChange={(event) => setCity(event.target.value)}
                    placeholder="Optional city name"
                    className="bg-slate-900 border-white/15 h-10 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="zip" className="text-xs font-mono text-slate-300">ZIP Code</Label>
                  <Input
                    id="zip"
                    value={zip}
                    onChange={(event) => setZip(event.target.value)}
                    placeholder="Optional postal code"
                    className="bg-slate-900 border-white/15 h-10 text-xs font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Dry-run preview banner */}
            <div className={cn("rounded-xl border p-4 transition-all flex items-start gap-4",
              dryRun ? "border-amber-500/40 bg-amber-950/20 text-amber-200" : "border-red-500/40 bg-red-950/20 text-red-200"
            )}>
              <div className="mt-0.5 shrink-0">
                <input
                  type="checkbox"
                  id="dryRunToggle"
                  checked={dryRun}
                  onChange={(event) => setDryRun(event.target.checked)}
                  className="h-5 w-5 rounded accent-amber-500 cursor-pointer"
                />
              </div>
              <label htmlFor="dryRunToggle" className="cursor-pointer space-y-1 min-w-0 flex-1">
                <span className="flex items-center gap-2 font-mono font-bold text-sm uppercase tracking-wide">
                  {dryRun ? "🛡️ Dry-Run Simulation Mode Enabled" : "⚠️ LIVE EXCLUSION PACKET TRANSMISSION ENABLED"}
                  <Badge variant="outline" className={cn("text-[10px] font-mono font-bold", dryRun ? "border-amber-500/50 text-amber-300 bg-black/30" : "border-red-500/50 text-red-300 bg-black/30")}>
                    {dryRun ? "SAFE PREVIEW" : "LIVE ACTION"}
                  </Badge>
                </span>
                <span className="block text-xs text-slate-300 font-mono leading-relaxed">
                  {dryRun ? "Worker will simulate network interactions and form navigation without transmitting removal requests. Recommended for initial target validation."
                         : "Worker will actively submit data deletion and removal demands to selected target brokers. Actions are irreversible once acknowledged."}
                </span>
              </label>
            </div>

            {/* Broker Target Selection Grid */}
            <div className="space-y-3.5">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <h3 className="font-bold text-base text-white flex items-center gap-2">
                  <Database className="w-4 h-4 text-cyan-400" /> Target Green Brokers ({selectedBrokers.length || "All"} Selected)
                </h3>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setSelectedBrokers(
                      selectedBrokers.length ? [] : brokers.map((b) => b.id)
                    )
                  }
                  className="text-xs font-mono h-8 bg-white/5 border-white/15 hover:bg-white/10"
                >
                  {selectedBrokers.length ? "Deselect All Targets" : "Select Entire Catalog"}
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 max-h-96 overflow-y-auto pr-1">
                {brokers.map((broker) => {
                  const isSelected = selectedBrokers.includes(broker.id);
                  return (
                    <div
                      key={broker.id}
                      onClick={() => toggleBroker(broker.id)}
                      className={cn(
                        "flex items-start gap-3 rounded-xl border p-3.5 cursor-pointer transition-all duration-200 select-none",
                        isSelected ? "border-cyan-500 bg-cyan-950/40 shadow-md shadow-cyan-500/10" : "border-white/10 bg-slate-950/50 hover:bg-slate-900/80"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        className="mt-1 h-4 w-4 accent-cyan-400 shrink-0 pointer-events-none"
                      />
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex flex-wrap items-center justify-between gap-1.5">
                          <span className="font-bold text-white text-sm truncate">{broker.name}</span>
                          <div className="flex items-center gap-1">
                            {broker.requires_captcha && (
                              <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[9px] uppercase font-mono">
                                CAPTCHA
                              </Badge>
                            )}
                            {broker.method === "manual" && (
                              <Badge variant="outline" className="text-[9px] uppercase font-mono text-slate-400">
                                Manual
                              </Badge>
                            )}
                          </div>
                        </div>
                        {broker.notes && (
                          <p className="text-[11px] font-mono text-slate-400 line-clamp-2 leading-tight">
                            {broker.notes}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Action Buttons & Status Telemetry */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-white/10">
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="cyber"
                  size="lg"
                  onClick={startOptOut}
                  disabled={startJob.isPending}
                  className="font-mono font-bold text-xs px-6 h-11 shadow-lg shadow-cyan-500/30"
                >
                  {startJob.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2 fill-current" />}
                  {dryRun ? "Execute Dry-Run Preview" : "Deploy Live Neutralization Workers"}
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => verify.mutate(undefined)}
                  disabled={verify.isPending}
                  className="font-mono font-semibold text-xs h-11 border-white/15 bg-white/5 hover:bg-white/10"
                >
                  {verify.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin text-cyan-400" /> : <ShieldAlert className="h-4 w-4 mr-2 text-cyan-400" />}
                  Verify Previous Removals
                </Button>
              </div>

              {message && (
                <div className="text-xs font-mono bg-slate-950 px-4 py-2.5 rounded-lg border border-white/15 text-cyan-300 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
                  {message}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* SECTION 2: WORKER TELEMETRY & CAPTCHA QUEUE */}
      {activeTab === "telemetry" && (
        <div className="space-y-6">
          {/* CAPTCHA Triage Console (Top Priority if active) */}
          <Card className={cn("border-white/10 bg-slate-900/70 shadow-lg overflow-hidden border-l-[6px]", (captcha.data || []).length > 0 ? "border-l-amber-500" : "border-l-slate-700")}>
            <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-amber-400 animate-bounce" />
                  CAPTCHA Arbitration & Manual Triage Queue
                </CardTitle>
                <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-mono uppercase">
                  User-In-The-Loop Enforced
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-slate-400">
                DigiZafe eschews third-party solver services (e.g. CapSolver) to maintain zero-egress integrity. Complete manual challenge steps directly in your local browser and release worker execution.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-5 space-y-4">
              {(captcha.data || []).map((item) => (
                <div key={item.id} className="rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-950/30 via-slate-900 to-slate-950 p-5 space-y-3 shadow-md">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2">
                    <div className="space-y-0.5">
                      <span className="font-bold text-white text-base tracking-tight">{item.broker_id}</span>
                      <p className="text-xs font-mono text-amber-300">
                        Challenge Type: <strong className="uppercase">{item.captcha_type}</strong> · Expires: {formatDate(item.expires_at)}
                      </p>
                    </div>

                    {item.page_url && (
                      <a
                        href={item.page_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold bg-amber-500/20 text-amber-200 hover:bg-amber-500/30 px-3 py-1.5 rounded-lg border border-amber-500/40 transition-colors"
                      >
                        Open Challenge Target <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </div>

                  <p className="text-sm text-slate-300 font-sans leading-relaxed">
                    {item.instructions || "Navigate to the official target URI above, complete the challenge verification in your local browser, and click Mark Complete to resume automation."}
                  </p>

                  <div className="flex items-center gap-3 pt-2">
                    <Button
                      size="sm"
                      variant="cyber"
                      onClick={() => solveCaptcha.mutate({ id: item.id, action: "manual_done" })}
                      className="text-xs font-mono font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                    >
                      <CheckCircle2 className="h-4 w-4 mr-1.5" />
                      Mark Challenge Complete & Resume Worker
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => solveCaptcha.mutate({ id: item.id, action: "skip" })}
                      className="text-xs font-mono text-slate-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      Skip Broker Target
                    </Button>
                  </div>
                </div>
              ))}

              {!captcha.isLoading && !(captcha.data || []).length && (
                <div className="py-8 text-center font-mono text-slate-400 text-xs space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400/50 mx-auto" />
                  <p className="text-sm font-semibold text-slate-300">Zero Pending CAPTCHA Arbitrations</p>
                  <p className="text-slate-500">All running worker jobs are progressing cleanly without required user interventions.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active & Previous Jobs + Broker State Split Studio */}
          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="border-white/10 bg-slate-900/60 shadow-md">
              <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-cyan-400" /> Active & Historical Job Executions
                </CardTitle>
                <CardDescription className="text-xs font-mono text-slate-400">
                  Real-time asynchronous progress telemetry from background workers.
                </CardDescription>
              </CardHeader>

              <CardContent className="p-5 space-y-4 max-h-[500px] overflow-y-auto">
                {(jobs.data || []).map((job) => (
                  <div key={job.id} className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <ClipboardList className="h-4 w-4 text-cyan-400" />
                        <span className="font-bold font-mono text-white text-sm uppercase">{job.job_type}</span>
                        <Badge variant="outline" className={cn("text-[10px] font-mono font-bold uppercase",
                          job.status === "completed" ? "border-emerald-500 text-emerald-300" :
                          job.status === "running" ? "border-cyan-500 text-cyan-300 animate-pulse" : "border-slate-600 text-slate-400"
                        )}>
                          {job.status}
                        </Badge>
                        {job.dry_run && <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-mono uppercase">DRY-RUN</Badge>}
                      </div>

                      {!["completed", "partial", "failed", "cancelled", "timed_out"].includes(job.status) && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => cancelJob.mutate(job.id)}
                          className="h-7 text-xs font-mono text-red-400 hover:text-red-300 hover:bg-red-500/10"
                        >
                          <StopCircle className="w-3.5 h-3.5 mr-1" /> Terminate Job
                        </Button>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs font-mono text-slate-400">
                        <span>Execution Telemetry</span>
                        <span className="text-cyan-300 font-bold">{job.progress_pct.toFixed(0)}%</span>
                      </div>
                      <Progress value={job.progress_pct} className="h-2 bg-slate-800" />
                      <p className="text-[11px] font-mono text-slate-400 truncate">{job.message || "Initializing target queue..."}</p>
                    </div>

                    {job.items && job.items.length > 0 && (
                      <div className="space-y-1 pt-2 border-t border-white/5 text-xs font-mono">
                        {job.items.map((item) => (
                          <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded bg-black/30 px-2.5 py-1.5">
                            <span className="text-slate-200">{item.broker_name}</span>
                            <span className="text-[10px] text-slate-400">
                              <span className={item.status === "removed" || item.status === "done" ? "text-emerald-400 font-bold" : "text-amber-400"}>{item.status}</span>
                              {item.skip_reason ? ` (${item.skip_reason})` : ""}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {!jobs.isLoading && !(jobs.data || []).length && (
                  <div className="py-12 text-center font-mono text-slate-400 text-xs">
                    No remediation job telemetry recorded in this session.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-900/60 shadow-md">
              <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="h-4 w-4 text-purple-400" /> Durable Broker State Repository
                </CardTitle>
                <CardDescription className="text-xs font-mono text-slate-400">
                  AIDR-inspired state tracking prevents redundant re-submissions and verifies durable deletion.
                </CardDescription>
              </CardHeader>

              <CardContent className="p-5 space-y-2 max-h-[500px] overflow-y-auto font-mono text-xs">
                {(states.data || []).map((stateRow) => (
                  <div key={stateRow.id} className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-950/50 p-3 hover:bg-slate-900/80 transition-colors">
                    <div className="min-w-0">
                      <div className="truncate font-bold text-white text-sm">{stateRow.broker_name}</div>
                      <div className="text-[11px] text-slate-400 truncate">{stateRow.detail || "No detailed telemetry recorded"}</div>
                    </div>
                    <Badge variant="outline" className="text-[10px] uppercase font-bold border-purple-500/30 text-purple-300 bg-purple-500/10 shrink-0">
                      {stateRow.status}
                    </Badge>
                  </div>
                ))}

                {!states.isLoading && !(states.data || []).length && (
                  <div className="py-12 text-center font-mono text-slate-400 text-xs">
                    No durable broker state records documented yet.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* SECTION 3: LEGAL & FREEZE MATRIX */}
      {activeTab === "legal" && (
        <div className="space-y-6">
          {/* Credit & Security Freeze Checklist */}
          <Card className="border-white/10 bg-slate-900/70 shadow-lg overflow-hidden border-l-[6px] border-l-emerald-500">
            <CardHeader className="bg-slate-950/60 p-5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                  <Lock className="h-5 w-5 text-emerald-400" /> National Bureau Credit & Security Freeze Checklist
                </CardTitle>
                <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-mono uppercase">
                  High-Impact Defense
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-slate-400">
                Execute free statutory credit freezes across major reporting bureaus (Equifax, Experian, TransUnion, Innovis) to neutralize synthetic identity fraudulent origination vectors.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-5 space-y-3">
              {(freeze.data || []).map((item) => (
                <div key={item.id} className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl border border-white/10 bg-slate-950/50 p-4 hover:bg-slate-900/80 transition-all">
                  <div className="space-y-1">
                    <span className="font-bold text-white text-base tracking-tight">{item.label}</span>
                    <br />
                    <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-mono text-cyan-400 hover:underline">
                      Open Official Bureau Portal <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <select
                      className={cn("h-9 rounded-lg border px-3 text-xs font-mono font-bold uppercase outline-none",
                        item.status === "done" ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300" :
                        item.status === "in_progress" ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-300" : "bg-slate-900 border-white/15 text-slate-300"
                      )}
                      value={item.status}
                      onChange={(event) => updateFreeze.mutate({ id: item.id, status: event.target.value })}
                    >
                      <option value="todo">Pending Action (To Do)</option>
                      <option value="in_progress">In Progress / Processing</option>
                      <option value="done">Freeze Confirmed Locked (Done)</option>
                      <option value="skipped">Skipped / N/A</option>
                    </select>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Legal & Regulatory Demand Generators */}
          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="border-white/10 bg-slate-900/60 shadow-md">
              <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="h-5 w-5 text-cyan-400" /> Statutory Right-to-Know Demand Draft Generator
                </CardTitle>
                <CardDescription className="text-xs font-mono text-slate-400">
                  Generate enforceable CCPA/GDPR personal information extraction and erasure demands.
                </CardDescription>
              </CardHeader>

              <CardContent className="p-5 space-y-4 font-mono text-xs">
                <div className="space-y-1.5">
                  <Label className="text-slate-300">Target Broker / Corporation Name</Label>
                  <Input
                    value={knowRecipient}
                    onChange={(event) => setKnowRecipient(event.target.value)}
                    placeholder="e.g. Acme Lexis Data Inc."
                    className="bg-slate-950 border-white/15 h-9 font-mono text-xs text-white"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-slate-300">Target Legal Compliance Email</Label>
                  <Input
                    value={knowEmail}
                    onChange={(event) => setKnowEmail(event.target.value)}
                    placeholder="privacy@brokerdomain.com (Optional)"
                    type="email"
                    className="bg-slate-950 border-white/15 h-9 font-mono text-xs text-white"
                  />
                </div>

                <Button
                  variant="cyber"
                  onClick={() =>
                    createKnow.mutate({
                      regime: "ccpa",
                      recipient_name: knowRecipient,
                      recipient_email: knowEmail || undefined,
                      identifier_id: identifierId || undefined,
                      include_deletion: true,
                    })
                  }
                  disabled={!knowRecipient || createKnow.isPending}
                  className="w-full font-mono font-bold text-xs h-10 shadow-md shadow-cyan-500/20"
                >
                  {createKnow.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                  Generate CCPA Right-To-Know / Erasure Draft
                </Button>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-900/60 shadow-md">
              <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-400" /> Regulatory AG Complaint Draft Generator
                </CardTitle>
                <CardDescription className="text-xs font-mono text-slate-400">
                  Generate formalized complaints to State Attorneys General for non-compliant brokers.
                </CardDescription>
              </CardHeader>

              <CardContent className="p-5 space-y-4 font-mono text-xs">
                <div className="space-y-1.5">
                  <Label className="text-slate-300">Non-Compliant Business / Broker Name</Label>
                  <Input
                    value={complaintRecipient}
                    onChange={(event) => setComplaintRecipient(event.target.value)}
                    placeholder="e.g. Rogue Broker Services"
                    className="bg-slate-950 border-white/15 h-9 font-mono text-xs text-white"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-slate-300">Factual Chronology of Non-Compliance</Label>
                  <textarea
                    className="min-h-[72px] w-full rounded-lg border border-white/15 bg-slate-950 px-3 py-2 text-xs font-mono text-white focus:border-red-500 outline-none"
                    value={complaintFacts}
                    onChange={(event) => setComplaintFacts(event.target.value)}
                    placeholder="Describe specific statutory deadline violations or refused opt-out packets..."
                  />
                </div>

                <Button
                  variant="destructive"
                  onClick={() =>
                    createComplaint.mutate({
                      regime: "ccpa",
                      recipient_name: complaintRecipient,
                      regulator: "ca_ag",
                      facts: complaintFacts,
                    })
                  }
                  disabled={!complaintRecipient || complaintFacts.length < 10 || createComplaint.isPending}
                  className="w-full font-mono font-bold text-xs h-10 shadow-md shadow-red-500/20"
                >
                  {createComplaint.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ShieldAlert className="w-4 h-4 mr-2" />}
                  Generate State Attorney General Complaint
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Generated Drafts Repository */}
          <Card className="border-white/10 bg-slate-900/60 shadow-md">
            <CardHeader className="bg-slate-950/40 p-5 border-b border-white/10">
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="h-5 w-5 text-purple-400" /> Generated Legal & Regulatory Demand Repository
              </CardTitle>
              <CardDescription className="text-xs font-mono text-slate-400">
                Click any draft to review statutory citations and copy text for dispatch.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-5 space-y-3 font-mono text-xs">
              {(requests.data || []).map((request) => (
                <details key={request.id} className="rounded-xl border border-white/10 bg-slate-950/50 p-4 group">
                  <summary className="cursor-pointer font-bold text-white flex items-center justify-between list-none">
                    <span className="group-hover:text-cyan-300 transition-colors">📄 {request.subject}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] uppercase text-purple-300 border-purple-500/30">{request.kind}</Badge>
                      <Badge variant="secondary" className="text-[10px] uppercase text-slate-300">{request.status}</Badge>
                    </div>
                  </summary>

                  <div className="mt-4 pt-3 border-t border-white/10 space-y-4">
                    <pre className="whitespace-pre-wrap rounded-lg bg-black/60 p-3.5 text-slate-300 border border-white/10 font-mono text-[11px] leading-relaxed overflow-x-auto">
                      {request.body}
                    </pre>

                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigator.clipboard.writeText(request.body)}
                        className="text-xs font-mono h-8 bg-white/5 border-white/15"
                      >
                        Copy Draft Text
                      </Button>
                      {request.status !== "sent_marked" && (
                        <Button
                          size="sm"
                          variant="cyber"
                          onClick={() => markSent.mutate(request.id)}
                          className="text-xs font-mono h-8 bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> Mark Transmission Sent
                        </Button>
                      )}
                    </div>
                  </div>
                </details>
              ))}

              {!requests.isLoading && !(requests.data || []).length && (
                <div className="py-10 text-center text-slate-400 font-mono text-xs">
                  No statutory legal demands generated yet. Use the generators above to create personalized regulatory notices.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

