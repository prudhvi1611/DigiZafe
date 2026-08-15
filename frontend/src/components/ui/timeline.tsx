import * as React from "react";
import { cn } from "@/lib/utils";

export type TimelineSeverity = "none" | "low" | "medium" | "high" | "critical" | "info";

export interface TimelineItemProps {
  timestamp?: string | React.ReactNode;
  title: string | React.ReactNode;
  subtitle?: string | React.ReactNode;
  severity?: TimelineSeverity;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  isLast?: boolean;
  className?: string;
}

const severityBorderMap: Record<TimelineSeverity, string> = {
  none: "border-slate-600 bg-slate-800 text-slate-400",
  low: "border-emerald-500/50 bg-emerald-500/20 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.3)]",
  medium: "border-amber-500/50 bg-amber-500/20 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.3)]",
  high: "border-orange-500/50 bg-orange-500/20 text-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.35)]",
  critical: "border-red-500/60 bg-red-500/20 text-red-400 font-bold shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse",
  info: "border-cyan-500/50 bg-cyan-500/20 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.3)]",
};

export const Timeline = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return <div className={cn("relative flex flex-col space-y-6 py-2", className)}>{children}</div>;
};

export const TimelineItem: React.FC<TimelineItemProps> = ({
  timestamp,
  title,
  subtitle,
  severity = "none",
  icon,
  children,
  isLast = false,
  className,
}) => {
  return (
    <div className={cn("relative flex gap-4 pb-2", className)}>
      {!isLast && (
        <div className="absolute left-4 top-9 bottom-0 w-px -translate-x-1/2 bg-gradient-to-b from-white/20 to-transparent" />
      )}
      <div
        className={cn(
          "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold backdrop-blur-md",
          severityBorderMap[severity]
        )}
      >
        {icon || <span className="h-2 w-2 rounded-full bg-current" />}
      </div>
      <div className="flex-1 min-w-0 flex flex-col space-y-2 pt-1">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div className="font-semibold text-white text-sm tracking-tight truncate">{title}</div>
          {timestamp && <div className="text-xs font-mono text-slate-400 shrink-0">{timestamp}</div>}
        </div>
        {subtitle && <div className="text-xs text-slate-400">{subtitle}</div>}
        {children && (
          <div className="mt-2 rounded-lg border border-white/10 bg-black/30 p-3.5 text-xs text-slate-300 shadow-inner">
            {children}
          </div>
        )}
      </div>
    </div>
  );
};
