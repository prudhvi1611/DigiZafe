import * as React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-white/[0.06] border border-white/5 bg-gradient-to-r from-white/[0.04] via-white/[0.08] to-white/[0.04] bg-[length:400%_100%] transition-all",
        className
      )}
      {...props}
    />
  );
}
