import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

export function Progress({ value, className }: { value?: number | null; className?: string }) {
  const val = value || 0;
  return (
    <ProgressPrimitive.Root
      className={cn(
        "relative h-2.5 w-full overflow-hidden rounded-full border border-white/5 bg-slate-900/80 shadow-inner",
        className
      )}
      value={val}
    >
      <ProgressPrimitive.Indicator
        className="h-full w-full flex-1 bg-gradient-to-r from-primary via-cyan-400 to-emerald-400 transition-all duration-500 ease-out shadow-[0_0_12px_rgba(6,182,212,0.5)]"
        style={{ transform: `translateX(-${100 - val}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}

