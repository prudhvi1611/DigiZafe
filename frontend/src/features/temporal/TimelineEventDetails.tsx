import React from 'react';
import { TimelineEvent } from './types';
import { Info, GitCommit, AlertTriangle, ArrowRight, ShieldAlert, FileText, CheckCircle2, Terminal } from 'lucide-react';

interface TimelineEventDetailsProps {
  event: TimelineEvent;
}

export function TimelineEventDetails({ event }: TimelineEventDetailsProps) {
  return (
    <div className="space-y-6 text-slate-300 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <h4 className="font-bold text-white uppercase text-sm tracking-wide flex items-center gap-2">
          <FileText className="w-4 h-4 text-emerald-400" /> Investigation Event Details
        </h4>
        <span className="text-slate-400 bg-white/[0.04] border border-white/10 px-2.5 py-1 rounded-md text-[11px]">
          ID: {event.id}
        </span>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* State Changes Diff */}
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-950/80 p-4 shadow-lg">
            <h5 className="text-slate-400 font-bold mb-3 flex items-center gap-1.5 uppercase text-xs tracking-wider border-b border-white/10 pb-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> State Transition Diff
            </h5>
            <div className="space-y-2 overflow-x-auto">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-rose-500/5 border border-rose-500/20 p-2.5 rounded-lg">
                <span className="text-rose-400 font-bold flex items-center gap-1.5 shrink-0">
                  <span className="w-2 h-2 rounded-full bg-rose-400 inline-block" /> Previous State:
                </span>
                <code className="text-rose-200 break-all text-right">
                  {event.previous_state ? JSON.stringify(event.previous_state, null, 2) : 'null'}
                </code>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-emerald-500/5 border border-emerald-500/20 p-2.5 rounded-lg">
                <span className="text-emerald-400 font-bold flex items-center gap-1.5 shrink-0">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" /> New State:
                </span>
                <code className="text-emerald-200 break-all text-right">
                  {event.new_state ? JSON.stringify(event.new_state, null, 2) : 'null'}
                </code>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-950/80 p-4 shadow-lg">
            <h5 className="text-slate-400 font-bold mb-2 flex items-center gap-1.5 uppercase text-xs tracking-wider">
              <Info className="w-4 h-4 text-cyan-400" /> Algorithmic Generation Reason
            </h5>
            <p className="text-slate-300 bg-white/[0.02] rounded-lg p-3 leading-relaxed border border-white/10 text-xs">
              {event.generation_reason || "No explicit generation reason recorded by connector."}
            </p>
          </div>
        </div>

        {/* Lineage & Limitations */}
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-950/80 p-4 shadow-lg">
            <h5 className="text-slate-400 font-bold mb-3 flex items-center gap-1.5 uppercase text-xs tracking-wider border-b border-white/10 pb-2">
              <GitCommit className="w-4 h-4 text-purple-400" /> Observation Provenance Lineage
            </h5>
            {event.observation_lineage && event.observation_lineage.length > 0 ? (
              <div className="space-y-1.5">
                {event.observation_lineage.map((line, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-black/40 border border-white/10 px-3 py-2 rounded-lg hover:border-purple-500/30 transition-colors">
                    <span className="text-slate-500 font-bold">Step [{idx + 1}]</span>
                    <code className="text-purple-300 font-bold">{line}</code>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-500 italic py-2 text-center">No provenance lineage recorded</div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-white/10 bg-slate-950/80 p-3.5 shadow-lg">
              <h5 className="text-slate-400 font-bold mb-2 flex items-center gap-1.5 uppercase text-[11px] tracking-wider">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Evidence Limitations
              </h5>
              {event.limitations && event.limitations.length > 0 ? (
                <ul className="list-disc list-inside text-slate-300 space-y-1 text-xs">
                  {event.limitations.map((lim, idx) => (
                    <li key={idx} className="leading-relaxed">{lim}</li>
                  ))}
                </ul>
              ) : (
                <span className="text-slate-500 text-xs italic">None known</span>
              )}
            </div>

            <div className="rounded-xl border border-white/10 bg-slate-950/80 p-3.5 shadow-lg">
              <h5 className="text-slate-400 font-bold mb-2 flex items-center gap-1.5 uppercase text-[11px] tracking-wider">
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400" /> Downstream Impact
              </h5>
              <p className="text-xs text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 p-2.5 rounded-lg leading-relaxed font-semibold">
                {event.downstream_impact || "No downstream impact recorded."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
