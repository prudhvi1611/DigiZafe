import React from "react";
import { CheckCircle2, Circle, Rocket, ShieldCheck, ArrowRight, Sparkles, Terminal, Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { useIdentifiers } from "@/features/identifiers/api";
import { useScans } from "@/features/scans/api";
import { useLatestScore } from "@/features/scores/api";
import { useLatestPlan } from "@/features/recommendations/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { OnboardingStep } from "@/lib/types";
import { cn } from "@/lib/utils";

export function OnboardingPage() {
  const identifiers = useIdentifiers();
  const scans = useScans();
  const score = useLatestScore();
  const plan = useLatestPlan();

  const totalIdentifiers = identifiers.data?.length || 0;
  const verifiedIdentifiers =
    identifiers.data?.filter((identifier) => identifier.is_verified).length || 0;
  const hasScan = (scans.data || []).length > 0;
  const hasScore = !!score.data;
  const hasPlan = !!plan.data;

  const steps: OnboardingStep[] = [
    {
      id: "identifier",
      title: "Register Primary Identity Anchor",
      description: "Initialize your profile with an email address, primary username, domain, or phone number.",
      complete: totalIdentifiers > 0,
      href: "/app/identifiers",
    },
    {
      id: "verify",
      title: "Complete Cryptographic Verification",
      description: "Confirm genuine domain/email control. DigiZafe enforces strictly verified ownership prior to scanning.",
      complete: verifiedIdentifiers > 0,
      href: "/app/identifiers",
    },
    {
      id: "scan",
      title: "Execute Deep Discovery Scan",
      description: "Deploy offline OSINT processing engines and dark-web correlation connectors to surface exposures.",
      complete: hasScan,
      href: "/app/scans",
    },
    {
      id: "score",
      title: "Quantify PDSS Posture Vectors",
      description: "Analyze CVSS-equivalent scoring drivers, residual ML anomaly forecasts, and defensive simulations.",
      complete: hasScore,
      href: "/app/scores",
    },
    {
      id: "remediate",
      title: "Deploy Neutralization Workflows",
      description: "Execute guided opt-out automation, CAPTCHA arbitration queues, and automated takedown letters.",
      complete: hasPlan,
      href: "/app/remediation",
    },
  ];

  const completed = steps.filter((step) => step.complete).length;
  const percent = Math.round((completed / steps.length) * 100);

  return (
    <div className="space-y-8 mt-8 animate-fade-in text-slate-100 pb-16 max-w-6xl mx-auto">
      {/* Hero Onboarding Banner */}
      <section className="relative overflow-hidden rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-slate-900/95 via-slate-900/80 to-cyan-950/40 p-8 md:p-12 shadow-2xl">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="absolute right-10 bottom-10 opacity-10 pointer-events-none hidden lg:block">
          <Terminal className="w-64 h-64 text-cyan-400" />
        </div>

        <div className="relative z-10 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
            <div className="flex items-center gap-4">
              <div className="rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 p-4 border border-cyan-500/40 shadow-inner">
                <Rocket className="h-8 w-8 text-cyan-400 animate-bounce" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold uppercase text-cyan-300 tracking-wider">Analyst Initialization Sequence</span>
                  <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono uppercase">
                    Zero-Egress Secured
                  </Badge>
                </div>
                <h1 className="text-3xl font-extrabold tracking-tight text-white mt-1">
                  Build Your Defensive Exposure Profile
                </h1>
              </div>
            </div>
          </div>

          <p className="max-w-3xl text-sm font-mono text-slate-300 leading-relaxed">
            Welcome to <strong className="text-cyan-300">DigiZafe V1.0</strong>. To maintain complete data privacy without sending unencrypted identifiers over the network, initialize your local workspace through this 5-stage sovereign investigation pipeline.
          </p>

          {/* High-tech Progress Gauge */}
          <div className="max-w-2xl bg-slate-950/80 p-5 rounded-xl border border-white/10 space-y-2.5 shadow-inner">
            <div className="flex justify-between text-xs font-mono text-slate-300 font-bold">
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Initialization Progress: {completed} of {steps.length} Stages Completed</span>
              </span>
              <span className="text-cyan-300 text-sm">{percent}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-black/60 p-0.5 border border-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-500 shadow-sm transition-all duration-500 ease-out"
                style={{ width: `${percent}%` }}
              />
            </div>
            <p className="text-[11px] font-mono text-slate-400 italic pt-1">
              {percent === 100 ? "🎉 All mandatory initialization stages complete! You are ready for continuous SOC surveillance." : "Complete the remaining highlighted action steps below to fully activate automated surface tracking."}
            </p>
          </div>
        </div>
      </section>

      {/* Step Grid */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {steps.map((step, index) => (
          <Card
            key={step.id}
            className={cn(
              "border-white/10 bg-slate-900/70 shadow-lg transition-all duration-200 hover:border-white/20 flex flex-col justify-between overflow-hidden relative",
              step.complete ? "border-t-[4px] border-t-emerald-500 bg-emerald-950/10" : "border-t-[4px] border-t-cyan-500"
            )}
          >
            <div>
              <CardHeader className="p-5 pb-3">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-white/10">
                    STAGE 0{index + 1}
                  </span>
                  <Badge variant={step.complete ? "default" : "secondary"} className={cn("text-[10px] font-mono uppercase font-bold",
                    step.complete ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  )}>
                    {step.complete ? "COMPLETED" : "ACTION PENDING"}
                  </Badge>
                </div>
                <CardTitle className="flex items-center gap-2.5 text-base font-bold text-white">
                  {step.complete ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 animate-pulse" />
                  ) : (
                    <Circle className="h-5 w-5 text-slate-500 shrink-0" />
                  )}
                  <span>{step.title}</span>
                </CardTitle>
              </CardHeader>

              <CardContent className="p-5 pt-0">
                <p className="text-xs font-mono text-slate-400 leading-relaxed">
                  {step.description}
                </p>
              </CardContent>
            </div>

            <div className="p-5 pt-3 border-t border-white/5 bg-slate-950/40">
              <Button
                asChild
                variant={step.complete ? "outline" : "cyber"}
                className={cn("w-full font-mono font-bold text-xs h-9 justify-between px-4",
                  step.complete ? "border-white/15 bg-white/5 hover:bg-white/10 text-slate-300" : "bg-cyan-500 text-black hover:bg-cyan-400 shadow-md shadow-cyan-500/20"
                )}
              >
                <Link to={step.href}>
                  <span>{step.complete ? "Review Workspace" : "Execute Stage Now"}</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </Button>
            </div>
          </Card>
        ))}

        {/* Informative Sovereign Security Card */}
        <Card className="border-emerald-500/40 bg-gradient-to-br from-emerald-950/30 via-slate-900 to-slate-950 shadow-lg p-6 flex flex-col justify-between border-l-[6px] border-l-emerald-500 font-mono text-xs text-emerald-200">
          <div className="space-y-3">
            <div className="flex items-center gap-2 font-bold text-sm text-emerald-300">
              <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 animate-pulse" />
              <span>Sovereign Zero-Egress Guarantee</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              DigiZafe operates strictly under a client-enforced architectural boundary. Your raw unverified identifiers will never be transmitted to external threat servers or commercial aggregators.
            </p>
            <div className="bg-emerald-950/50 p-3 rounded-lg border border-emerald-500/30 text-[11px] text-slate-300 space-y-1">
              <div className="flex items-center gap-2 font-bold text-emerald-300">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                <span>Verified Ownership Lock</span>
              </div>
              <p className="text-slate-400">
                External reconnaissance queries require explicit verification tokens before activation.
              </p>
            </div>
          </div>
          <div className="pt-4 text-right text-[10px] text-emerald-400/80 font-bold uppercase tracking-wider">
            System Architecture Protected
          </div>
        </Card>
      </div>
    </div>
  );
}
