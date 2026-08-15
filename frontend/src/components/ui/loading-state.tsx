import * as React from "react";
import { Shield, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface LoadingStateProps {
  label?: string;
  subtext?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  label = "Analyzing exposure intelligence...",
  subtext = "Querying zero-egress cryptographic graph",
  className,
}) => {
  return (
    <div className={cn("flex flex-col items-center justify-center p-12 text-center min-h-[250px]", className)}>
      <div className="relative mb-6 flex h-14 w-14 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 shadow-[0_0_30px_rgba(6,182,212,0.3)]">
        <Loader2 className="absolute inset-2 h-10 w-10 animate-spin text-cyan-400 opacity-50" />
        <Shield className="h-6 w-6 text-cyan-300 animate-pulse" />
      </div>
      <div className="text-sm font-semibold tracking-tight text-white mb-1">{label}</div>
      <div className="text-xs font-mono text-slate-400 opacity-80">{subtext}</div>
    </div>
  );
};
