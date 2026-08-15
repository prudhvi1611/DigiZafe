import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.03] to-transparent p-12 text-center shadow-lg backdrop-blur-md",
        className
      )}
    >
      <div className="relative mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-cyan-500/20 bg-cyan-500/10 text-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.25)]">
        <div className="absolute inset-0 rounded-full bg-cyan-400/10 animate-ping opacity-25 pointer-events-none" />
        <div className="h-8 w-8 [&>svg]:h-full [&>svg]:w-full">{icon}</div>
      </div>
      <h3 className="text-lg font-semibold tracking-tight text-white mb-2">{title}</h3>
      <p className="max-w-md text-sm text-slate-400 leading-relaxed mb-6">{description}</p>
      {actionLabel && onAction && (
        <Button variant="cyber" size="default" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
