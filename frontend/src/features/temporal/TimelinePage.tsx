import React from 'react';
import { IdentityTimelineView } from './IdentityTimelineView';
import { Activity, Clock, ShieldCheck, Database } from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';

export function TimelinePage() {
  return (
    <div className="space-y-8 animate-fade-in text-slate-200">
      {/* Console Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status="active" label="LIVE TEMPORAL ENGINE" pulse />
            <span className="text-xs font-mono text-slate-400">STATE LINEAGE TRACKING</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1 flex items-center gap-2.5">
            <Activity className="h-7 w-7 text-emerald-400 animate-pulse" style={{ animationDuration: '3s' }} />
            Identity Timeline
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400 leading-relaxed">
            Track canonical evidence over time with side-by-side state transition diffs, observation lineage, and algorithmic materiality filtering.
          </p>
        </div>
        <div className="flex items-center gap-3 bg-slate-900/60 border border-white/10 rounded-xl px-4 py-2.5 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-emerald-300">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Cryptographic Auditing: <strong>Active</strong></span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-slate-400">
            <Database className="h-3.5 w-3.5 text-cyan-400" />
            <span>Append-only Ledger</span>
          </div>
        </div>
      </div>

      <main>
        <IdentityTimelineView />
      </main>
    </div>
  );
}
