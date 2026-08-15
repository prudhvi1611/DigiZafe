import * as React from "react";
import { cn } from "@/lib/utils";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "outline"
  | "destructive"
  | "success"
  | "warning"
  | "info"
  | "critical";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: BadgeVariant }) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors shadow-sm",
        variant === "default" && "border-cyan-500/30 bg-cyan-500/15 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.15)]",
        variant === "secondary" && "border-white/10 bg-slate-800/60 text-slate-300",
        variant === "destructive" && "border-red-500/30 bg-red-500/15 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]",
        variant === "outline" && "border-white/20 bg-transparent text-slate-300",
        variant === "success" && "border-emerald-500/30 bg-emerald-500/15 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.15)]",
        variant === "warning" && "border-amber-500/30 bg-amber-500/15 text-amber-300",
        variant === "info" && "border-blue-500/30 bg-blue-500/15 text-blue-300",
        variant === "critical" && "border-red-600/50 bg-red-600/20 text-red-300 font-bold animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.35)]",
        className
      )}
      {...props}
    />
  );
}

