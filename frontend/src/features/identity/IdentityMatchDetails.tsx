import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, CheckCircle, AlertTriangle, ShieldCheck } from "lucide-react";
import { useIdentityAssessment, useRecalculateAssessment } from "./api";

interface Props {
  candidateId: string;
}

export function IdentityMatchDetails({ candidateId }: Props) {
  const assessmentQuery = useIdentityAssessment(candidateId);
  const recalculate = useRecalculateAssessment();

  if (assessmentQuery.isLoading) {
    return (
      <div className="space-y-3 mt-4">
        <Skeleton className="h-20 w-full rounded-lg" />
        <Skeleton className="h-12 w-full rounded-lg" />
      </div>
    );
  }

  if (assessmentQuery.isError || !assessmentQuery.data) {
    return (
      <div className="mt-4 p-4 border border-white/10 rounded-lg bg-black/30 text-xs font-mono text-slate-400 text-center">
        Assessment currently unavailable.
      </div>
    );
  }

  const data = assessmentQuery.data;

  return (
    <div className="mt-4 border border-white/10 rounded-xl p-5 bg-slate-950/90 shadow-2xl space-y-5 animate-in fade-in-50 duration-200">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-white/10 pb-3">
        <div>
          <h4 className="font-bold text-sm text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
            Algorithmic Assessment
          </h4>
          <p className="text-xs font-mono text-slate-400 mt-0.5">
            Engine v{data.engine_version} <span className="text-slate-600">|</span> Policy v{data.policy_version}
          </p>
        </div>
        <Button 
          variant="outline" 
          size="sm"
          className="border-white/15 bg-white/5 hover:bg-cyan-500/20 hover:text-cyan-300 hover:border-cyan-500/30 text-xs font-mono shrink-0"
          disabled={recalculate.isPending}
          onClick={() => recalculate.mutate(candidateId)}
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-cyan-400 ${recalculate.isPending ? "animate-spin" : ""}`} />
          {recalculate.isPending ? "Recalculating..." : "Recalculate"}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 bg-black/40 border border-white/5 rounded-lg p-3">
        <div>
          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-1.5">Confidence Band</div>
          <Badge variant="outline" className="bg-cyan-500/15 text-cyan-300 border-cyan-500/30 font-mono text-xs uppercase font-bold px-3">
            {data.confidence_band}
          </Badge>
        </div>
        <div>
          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-1.5">Status</div>
          <Badge variant="secondary" className="bg-white/[0.06] text-slate-200 font-mono text-xs uppercase px-3">
            {data.assessment_status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      <div className="space-y-4 pt-1">
        {data.explanation_mapping?.why_matched?.length > 0 && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3.5">
            <div className="text-xs font-mono font-bold mb-2 text-emerald-300 uppercase flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              Why this might be a match
            </div>
            <ul className="list-disc list-inside text-xs text-slate-300 space-y-1 font-mono leading-relaxed pl-1">
              {data.explanation_mapping.why_matched.map((item: any, i: number) => (
                <li key={i}>{item.message_text}</li>
              ))}
            </ul>
          </div>
        )}

        {data.explanation_mapping?.why_not_matched?.length > 0 && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3.5">
            <div className="text-xs font-mono font-bold mb-2 text-amber-300 uppercase flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              Limitations or Evidence against
            </div>
            <ul className="list-disc list-inside text-xs text-slate-300 space-y-1 font-mono leading-relaxed pl-1">
              {data.explanation_mapping.why_not_matched.map((item: any, i: number) => (
                <li key={i}>{item.message_text}</li>
              ))}
            </ul>
          </div>
        )}
        
        {data.explanation_mapping?.why_matched?.length === 0 && data.explanation_mapping?.why_not_matched?.length === 0 && (
          <div className="text-xs font-mono text-slate-400 italic">No specific explanation available.</div>
        )}
      </div>
      
      <div className="pt-3 border-t border-white/10 text-xs font-mono text-slate-400 flex items-center justify-between">
        <span>Cryptographic Score: <strong className="text-white">{data.score}</strong></span>
        <span>Independent Groups: <strong className="text-cyan-400">{new Set(data.evidence_snapshot?.map((e: any) => e.independence_group)).size}</strong></span>
      </div>
    </div>
  );
}
