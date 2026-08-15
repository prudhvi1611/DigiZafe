import React, { useState } from 'react';
import { TimelineEvent } from './types';
import { TimelineEventDetails } from './TimelineEventDetails';
import { ChevronDown, ChevronRight, Activity, Clock, ShieldCheck, FileText, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { Badge } from '@/components/ui/badge';

interface TimelineEventCardProps {
  event: TimelineEvent;
}

export function TimelineEventCard({ event }: TimelineEventCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getMaterialityColor = (mat: string) => {
    switch (mat) {
      case 'CRITICAL': return 'bg-rose-500/15 text-rose-400 border-rose-500/40 shadow-[0_0_10px_rgba(244,63,94,0.15)] font-bold';
      case 'HIGH': return 'bg-orange-500/15 text-orange-400 border-orange-500/40 font-bold';
      case 'MEDIUM': return 'bg-amber-500/15 text-amber-300 border-amber-500/40 font-bold';
      case 'LOW': return 'bg-blue-500/15 text-blue-300 border-blue-500/40 font-bold';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'RESOLVED': return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'OPEN': return <AlertCircle className="w-3.5 h-3.5 text-amber-400" />;
      case 'SUPERSEDED': return <Clock className="w-3.5 h-3.5 text-slate-400" />;
      default: return null;
    }
  };

  return (
    <div className="timeline-event bg-gradient-to-r from-slate-900/90 via-slate-900 to-slate-950 border border-white/10 rounded-xl overflow-hidden transition-all duration-200 hover:border-emerald-500/40 hover:shadow-xl hover:shadow-emerald-500/5 group">
      <div 
        className="p-5 cursor-pointer flex flex-col md:flex-row md:items-center gap-4"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
      >
        <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-white/[0.04] border border-white/15 text-slate-400 group-hover:text-emerald-400 group-hover:border-emerald-500/40 transition-colors shadow-inner">
          <Activity className="w-5 h-5" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5 text-slate-200">
            <h3 className="font-bold text-base truncate tracking-tight text-white group-hover:text-emerald-300 transition-colors">{event.safe_title}</h3>
            <Badge variant="outline" className={clsx("px-2 py-0.5 rounded-md text-[10px] uppercase font-mono tracking-wider", getMaterialityColor(event.materiality))}>
              {event.materiality}
            </Badge>
            {event.change_type && (
              <span className="bg-black/50 border border-white/10 rounded px-2 py-0.5 text-[10px] font-mono text-cyan-300 flex items-center gap-1">
                <FileText className="w-3 h-3 text-cyan-400" /> {event.change_type}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Clock className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> 
              {new Date(event.detected_at).toLocaleString()}
            </span>
            <span className="flex items-center gap-1.5 text-cyan-300 font-semibold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              @{event.affected_profile}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 md:ml-auto md:border-l border-white/10 md:pl-6 font-mono text-xs">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="text-slate-500 w-20">Audit Status:</span>
              <span className="flex items-center gap-1.5 font-bold text-white uppercase">
                {getStatusIcon(event.review_status)} {event.review_status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500 w-20">Provenance:</span>
              <span className="text-emerald-300 font-bold bg-slate-950 px-2 py-0.5 rounded border border-white/15">
                {event.provenance_source}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500 w-20">Confidence:</span>
              <div className="flex items-center gap-2">
                <div className="w-12 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-400 h-full" style={{ width: `${Math.round(event.confidence * 100)}%` }} />
                </div>
                <span className="font-bold text-white">{(event.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
            {(event.confidence >= 0.8 || event.provenance_source.toLowerCase().includes('cert')) && (
              <div className="mt-1 flex items-center gap-1.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-2.5 py-1 rounded-lg w-fit text-[10px] font-bold tracking-wider shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span>CERTIFIED CONNECTOR EVIDENCE</span>
              </div>
            )}
          </div>

          <div className="flex-shrink-0 text-slate-500 group-hover:text-emerald-400 transition-colors bg-white/[0.02] p-2 rounded-lg border border-white/10">
            {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="p-5 border-t border-white/10 bg-black/40 animate-in slide-in-from-top-2 duration-200">
          <TimelineEventDetails event={event} />
        </div>
      )}
    </div>
  );
}
