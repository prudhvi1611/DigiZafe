import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchBarProps extends React.InputHTMLAttributes<HTMLInputElement> {
  onClear?: () => void;
  shortcut?: string;
}

export const SearchBar = React.forwardRef<HTMLInputElement, SearchBarProps>(
  ({ className, value, onChange, onClear, placeholder = "Search investigation items...", shortcut, ...props }, ref) => {
    return (
      <div className={cn("relative flex items-center w-full max-w-md", className)}>
        <Search className="absolute left-3.5 h-4 w-4 text-slate-400 pointer-events-none" />
        <input
          ref={ref}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="flex h-10 w-full rounded-lg border border-white/10 bg-black/40 pl-10 pr-10 py-2 text-sm text-foreground shadow-inner transition-all duration-200 placeholder:text-slate-500 focus:border-cyan-500/60 focus:bg-black/70 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50"
          {...props}
        />
        {value ? (
          <button
            type="button"
            onClick={() => {
              if (onClear) onClear();
            }}
            className="absolute right-3 p-1 rounded-md text-slate-400 hover:text-white focus:outline-none focus:ring-1 focus:ring-white/30"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : shortcut ? (
          <kbd className="absolute right-3 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-white/10 bg-slate-800 px-1.5 font-mono text-[10px] font-medium text-slate-400 opacity-80">
            {shortcut}
          </kbd>
        ) : null}
      </div>
    );
  }
);
SearchBar.displayName = "SearchBar";
