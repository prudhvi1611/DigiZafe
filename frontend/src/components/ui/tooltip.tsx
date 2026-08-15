import * as React from "react";
import { cn } from "@/lib/utils";

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  side?: "top" | "bottom" | "left" | "right";
}

export function Tooltip({ content, children, className, side = "top" }: TooltipProps) {
  const [open, setOpen] = React.useState(false);

  const sideClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 -translate-y-2 mb-1",
    bottom: "top-full left-1/2 -translate-x-1/2 translate-y-2 mt-1",
    left: "right-full top-1/2 -translate-y-1/2 -translate-x-2 mr-1",
    right: "left-full top-1/2 -translate-y-1/2 translate-x-2 ml-1",
  };

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <div
          role="tooltip"
          className={cn(
            "absolute z-50 px-2.5 py-1.5 text-xs font-medium text-white bg-slate-900 border border-white/20 rounded-md shadow-xl backdrop-blur-md whitespace-nowrap pointer-events-none animate-in fade-in-0 zoom-in-95 duration-150",
            sideClasses[side],
            className
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
}
