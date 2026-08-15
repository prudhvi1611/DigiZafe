import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] select-none",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-[0_0_15px_rgba(6,182,212,0.2)] hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(6,182,212,0.35)] font-semibold",
        secondary: "bg-secondary border border-white/5 text-secondary-foreground hover:bg-secondary/80 hover:border-white/10",
        outline: "border border-input bg-transparent hover:bg-white/5 hover:text-foreground hover:border-white/20",
        ghost: "hover:bg-white/5 hover:text-foreground",
        destructive: "bg-destructive/90 text-destructive-foreground shadow-[0_0_15px_rgba(239,68,68,0.2)] hover:bg-destructive font-semibold",
        glass: "border border-white/10 bg-white/5 text-white backdrop-blur-md hover:bg-white/10 hover:border-white/20 shadow-sm",
        cyber: "bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] border border-cyan-300/30",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-md px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  }
);
Button.displayName = "Button";

