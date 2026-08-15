import * as React from "react";
import { cn } from "@/lib/utils";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export interface KpiCardProps {
  title: string;
  value: string | number;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral" | "good" | "bad" | "info";
  subtitle?: string;
  icon?: React.ReactNode;
  statusColor?: "emerald" | "amber" | "red" | "cyan" | "violet" | "slate";
  onClick?: () => void;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  trend,
  trendDirection = "neutral",
  subtitle,
  icon,
  statusColor = "cyan",
  onClick,
  className,
}) => {
  const isGood = trendDirection === "up" || trendDirection === "good";
  const isBad = trendDirection === "down" || trendDirection === "bad";

  const glowStyles: Record<string, string> = {
    emerald: "hover:border-emerald-500/30 hover:shadow-[0_4px_24px_rgba(16,185,129,0.15)]",
    amber: "hover:border-amber-500/30 hover:shadow-[0_4px_24px_rgba(245,158,11,0.15)]",
    red: "hover:border-red-500/30 hover:shadow-[0_4px_24px_rgba(239,68,68,0.2)]",
    cyan: "hover:border-cyan-500/30 hover:shadow-[0_4px_24px_rgba(6,182,212,0.2)]",
    violet: "hover:border-violet-500/30 hover:shadow-[0_4px_24px_rgba(139,92,246,0.2)]",
    slate: "hover:border-slate-500/30",
  };

  const statusDot: Record<string, string> = {
    emerald: "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]",
    amber: "bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)]",
    red: "bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]",
    cyan: "bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]",
    violet: "bg-violet-400 shadow-[0_0_8px_rgba(139,92,246,0.8)]",
    slate: "bg-slate-400",
  };

  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : "region"}
      tabIndex={onClick ? 0 : undefined}
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-xl border border-white/10 bg-gradient-to-b from-white/[0.05] to-transparent p-5 text-card-foreground shadow-lg backdrop-blur-md transition-all duration-300",
        glowStyles[statusColor] || glowStyles.cyan,
        onClick && "cursor-pointer hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <span className={cn("h-2 w-2 rounded-full", statusDot[statusColor] || statusDot.slate)} />
          <span className="truncate">{title}</span>
        </div>
        {icon && <div className="h-5 w-5 text-slate-400 transition-colors group-hover:text-white shrink-0">{icon}</div>}
      </div>

      <div className="my-3 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
        {trend && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[11px] font-semibold font-mono",
              isGood ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "",
              isBad ? "bg-red-500/15 text-red-400 border border-red-500/30" : "",
              !isGood && !isBad ? "bg-slate-800 text-slate-400 border border-white/10" : ""
            )}
          >
            {isGood && <ArrowUpRight className="h-3 w-3" />}
            {isBad && <ArrowDownRight className="h-3 w-3" />}
            {!isGood && !isBad && <Minus className="h-3 w-3" />}
            {trend}
          </span>
        )}
      </div>

      {subtitle && <div className="text-xs text-slate-400 line-clamp-1">{subtitle}</div>}
    </div>
  );
};
