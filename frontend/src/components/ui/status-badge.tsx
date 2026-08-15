import * as React from "react";
import { cn } from "@/lib/utils";

export type StatusType = "active" | "inactive" | "warning" | "error" | "secure" | "scanning" | "info";

export interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, pulse = true, className }) => {
  const statusConfig: Record<StatusType, { color: string; dot: string; text: string }> = {
    active: { color: "border-emerald-500/30 bg-emerald-500/15 text-emerald-300", dot: "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]", text: "Active" },
    secure: { color: "border-cyan-500/30 bg-cyan-500/15 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.2)]", dot: "bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]", text: "Secure" },
    scanning: { color: "border-blue-500/30 bg-blue-500/15 text-blue-300", dot: "bg-blue-400 animate-ping", text: "Scanning" },
    warning: { color: "border-amber-500/30 bg-amber-500/15 text-amber-300", dot: "bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)]", text: "Warning" },
    error: { color: "border-red-500/40 bg-red-500/20 text-red-300 font-bold animate-pulse", dot: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.9)]", text: "Critical" },
    inactive: { color: "border-slate-700 bg-slate-800/80 text-slate-400", dot: "bg-slate-500", text: "Offline" },
    info: { color: "border-indigo-500/30 bg-indigo-500/15 text-indigo-300", dot: "bg-indigo-400", text: "Info" },
  };

  const config = statusConfig[status] || statusConfig.info;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide shadow-sm select-none",
        config.color,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full inline-block", config.dot, pulse && status === "active" ? "animate-pulse" : "")} />
      {label || config.text}
    </span>
  );
};
