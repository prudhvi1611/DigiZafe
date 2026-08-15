import React from 'react';
import { RevalidationState } from './types';
import { Loader2, CheckCircle2, XCircle, Clock, AlertTriangle, AlertOctagon } from 'lucide-react';
import clsx from 'clsx';

interface RevalidationStatusProps {
  status: RevalidationState;
  detail?: string;
  className?: string;
}

export function RevalidationStatus({ status, detail, className }: RevalidationStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'queued':
        return { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500/10', label: 'Queued' };
      case 'planning':
        return { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Planning', spin: true };
      case 'running':
        return { icon: Loader2, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Running', spin: true };
      case 'partial_result':
        return { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Partial Result' };
      case 'completed':
        return { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Completed' };
      case 'no_action':
        return { icon: Clock, color: 'text-slate-500', bg: 'bg-slate-500/10', label: 'No Action Taken' };
      case 'failed':
        return { icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-500/10', label: 'Failed' };
      default:
        return { icon: AlertOctagon, color: 'text-slate-400', bg: 'bg-slate-500/10', label: status };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      <div className={clsx("inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-700/50 w-fit", config.bg)}>
        <Icon className={clsx("w-4 h-4", config.color, config.spin && "animate-spin")} />
        <span className={clsx("text-xs font-semibold tracking-wide uppercase", config.color)}>
          {config.label}
        </span>
      </div>
      {detail && (
        <div className="text-xs text-slate-400 bg-slate-900/50 border border-slate-800 p-2 rounded max-w-md flex gap-2 items-start">
          <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
          <span>{detail}</span>
        </div>
      )}
    </div>
  );
}

// Temporary import for the fallback icon
import { AlertCircle } from 'lucide-react';
