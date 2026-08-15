import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Radar, UserCheck, ShieldAlert, CheckCircle2, XCircle } from "lucide-react";
import { IdentityMatchDetails } from "./IdentityMatchDetails";
import {
  useIdentityAnchor,
  useOrchestrationRuns,
  useCandidateProfiles,
  useStartDiscovery,
  useConfirmCandidate,
  useDismissCandidate
} from "./api";

export function IdentityDiscoveryView() {
  const anchorQuery = useIdentityAnchor();
  const runsQuery = useOrchestrationRuns();
  const candidatesQuery = useCandidateProfiles();
  const startDiscovery = useStartDiscovery();
  const confirmCandidate = useConfirmCandidate();
  const dismissCandidate = useDismissCandidate();
  const [expandedCandidate, setExpandedCandidate] = useState<string | null>(null);

  const activeAliases = anchorQuery.data?.aliases?.filter((a: any) => 
    a.status === "active" && (a.alias_type === "username" || a.alias_type === "handle")
  ) || [];

  const handleDiscover = () => {
    if (activeAliases.length === 0) return;
    const ids = activeAliases.map((a: any) => a.id);
    startDiscovery.mutate(ids);
  };

  return (
    <div className="space-y-6 mt-8 animate-fade-in">
      <div className="border-l-4 border-violet-500 pl-4 py-1">
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Candidate Profiles
        </h2>
        <p className="text-slate-400 text-xs font-mono">
          Discover public profiles linked to your aliases. Results are candidates and may belong to someone else.
        </p>
      </div>

      <Card className="border-white/10 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 shadow-xl backdrop-blur-md">
        <CardHeader className="border-b border-white/10 bg-white/[0.02] flex flex-row items-center justify-between pb-4">
          <div className="space-y-1">
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <Radar className="h-5 w-5 text-cyan-400 animate-pulse" />
              Discovery Orchestration Runs
            </CardTitle>
            <CardDescription className="text-xs text-slate-400 font-mono">
              We will plan and execute connector runs for {activeAliases.length} active username{activeAliases.length !== 1 ? 's' : ''}.
            </CardDescription>
          </div>
          <Button 
            variant="cyber"
            onClick={handleDiscover} 
            disabled={activeAliases.length === 0 || startDiscovery.isPending}
            className="font-semibold shadow-md shrink-0"
          >
            {startDiscovery.isPending ? "Starting..." : "Discover Profiles"}
          </Button>
        </CardHeader>
        <CardContent className="p-4">
          <div className="space-y-2">
            {(runsQuery.data || []).slice(0, 3).map((run: any) => (
              <div key={run.id} className="flex flex-wrap justify-between items-center text-xs font-mono border border-white/10 bg-black/20 p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="bg-cyan-500/10 text-cyan-300 border-cyan-500/30 uppercase text-[10px] font-bold">
                    {run.status}
                  </Badge>
                  <span className="text-slate-400">{new Date(run.created_at).toLocaleString()}</span>
                </div>
                <div className="text-slate-300 font-semibold mt-1 sm:mt-0">
                  <strong className="text-cyan-400">{run.completed_count}</strong> / {run.planned_count} connectors completed
                </div>
              </div>
            ))}
            {!runsQuery.data?.length && <p className="text-slate-400 text-xs font-mono italic text-center py-3">No orchestration runs yet.</p>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {(candidatesQuery.data || []).map((c: any) => (
          <Card key={c.id} className="candidate-card border-white/10 bg-slate-900/60 hover:bg-slate-900/80 transition-all duration-200 shadow-lg overflow-hidden">
            <CardContent className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5 min-w-0">
                <div className="flex items-center gap-2.5">
                  <span className="font-bold text-white text-base tracking-tight">{c.platform}</span>
                  <Badge variant={
                    c.candidate_status === 'unreviewed' ? 'default' :
                    c.candidate_status === 'confirmed_by_user' ? 'secondary' : 'outline'
                  } className={
                    c.candidate_status === 'unreviewed' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 text-[10px] font-mono uppercase' :
                    c.candidate_status === 'confirmed_by_user' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-[10px] font-mono uppercase' : 'bg-slate-800 text-slate-400 text-[10px] font-mono uppercase'
                  }>
                    {c.candidate_status === 'unreviewed' ? 'Needs review' :
                     c.candidate_status === 'confirmed_by_user' ? 'Confirmed by you' : 'Dismissed'}
                  </Badge>
                </div>
                <a href={c.profile_url} target="_blank" rel="noreferrer" className="text-sm text-cyan-400 hover:underline block truncate font-mono">
                  {c.profile_url}
                </a>
                <div className="text-xs font-mono text-slate-400">
                  Observed alias: <span className="text-white font-semibold">{c.username_observed}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2.5 shrink-0">
                <Button 
                  variant="outline" 
                  size="sm"
                  className="border-white/15 bg-white/5 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/30 font-semibold text-xs"
                  disabled={dismissCandidate.isPending}
                  onClick={() => dismissCandidate.mutate(c.id)}
                >
                  <XCircle className="w-3.5 h-3.5 mr-1.5 text-red-400" />
                  Not mine
                </Button>
                <Button 
                  size="sm"
                  variant="cyber"
                  className="font-semibold text-xs shadow-md shadow-cyan-500/20"
                  disabled={confirmCandidate.isPending}
                  onClick={() => confirmCandidate.mutate(c.id)}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-cyan-300" />
                  This is mine
                </Button>
              </div>
            </CardContent>
            
            {c.candidate_status === 'unreviewed' && (
              <div className="border-t border-white/5 bg-black/20 px-5 py-3">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="w-full text-xs font-mono text-slate-300 hover:text-white hover:bg-white/[0.04] flex items-center justify-center" 
                  onClick={() => setExpandedCandidate(expandedCandidate === c.id ? null : c.id)}
                >
                  {expandedCandidate === c.id ? (
                    <><ChevronUp className="w-4 h-4 mr-1 text-cyan-400"/> Hide Match Assessment</>
                  ) : (
                    <><ChevronDown className="w-4 h-4 mr-1 text-cyan-400"/> View Algorithmic Match Assessment</>
                  )}
                </Button>
                {expandedCandidate === c.id && <IdentityMatchDetails candidateId={c.id} />}
              </div>
            )}
          </Card>
        ))}
        {!candidatesQuery.isLoading && !(candidatesQuery.data || []).length && (
          <div className="rounded-xl border border-white/10 bg-black/20 p-8 text-center text-slate-400 font-mono text-xs">
            No discovery candidate profiles available yet. Execute a discovery run above.
          </div>
        )}
      </div>
    </div>
  );
}
