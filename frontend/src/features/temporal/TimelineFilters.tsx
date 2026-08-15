import React, { useState } from 'react';
import { Search, Filter, RotateCcw, SlidersHorizontal, Check } from 'lucide-react';
import { ChangeType, Materiality, ReviewStatus } from './types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface TimelineFiltersState {
  change_type?: ChangeType | "";
  materiality?: Materiality | "";
  candidate_profile?: string;
  review_status?: ReviewStatus | "";
  date_from?: string;
  date_to?: string;
}

interface TimelineFiltersProps {
  filters: TimelineFiltersState;
  onChange: (filters: TimelineFiltersState) => void;
}

export function TimelineFilters({ filters, onChange }: TimelineFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    onChange({ ...filters, [name]: value });
  };

  const resetFilters = () => {
    onChange({});
  };

  const activeCount = Object.values(filters).filter(v => v !== "" && v !== undefined).length;

  return (
    <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-white/10 rounded-xl p-5 mb-6 shadow-2xl backdrop-blur-md text-xs font-mono">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-2 text-emerald-400">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              Filter Investigation Timeline
              {activeCount > 0 && (
                <Badge variant="outline" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-[10px] px-2 font-bold">
                  {activeCount} active
                </Badge>
              )}
            </h3>
            <p className="text-slate-400 text-xs mt-0.5">Isolate high-materiality events and suspected absence signals.</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="text-slate-400 hover:text-white h-9 px-3 font-mono text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5 text-amber-400" /> Reset
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="border-white/15 bg-white/[0.03] hover:bg-white/[0.08] text-slate-200 h-9 font-mono text-xs font-bold shadow-sm"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 mr-2 text-emerald-400" />
            {showAdvanced ? "Hide Filters" : "Filter Options"}
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold uppercase text-[11px]">Profile / Keyword Search</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-400" />
            <input 
              type="text" 
              name="candidate_profile"
              value={filters.candidate_profile || ""}
              onChange={handleChange}
              placeholder="Search affected profile..." 
              className="w-full bg-slate-950 border border-white/15 rounded-lg pl-9 pr-3 h-10 text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold uppercase text-[11px]">Change Type</label>
          <select 
            name="change_type" 
            value={filters.change_type || ""}
            onChange={handleChange}
            className="w-full bg-slate-950 border border-white/15 rounded-lg px-3 h-10 text-white focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
          >
            <option value="" className="bg-slate-900 text-slate-400">All Change Types</option>
            <option value="FACT_APPEARED" className="bg-slate-900">Fact Appeared</option>
            <option value="FACT_VALUE_CHANGED" className="bg-slate-900">Value Changed</option>
            <option value="FACT_BECAME_STALE" className="bg-slate-900">Became Stale</option>
            <option value="FACT_EXPIRED" className="bg-slate-900">Expired</option>
            <option value="FACT_ABSENCE_SUSPECTED" className="bg-slate-900">Absence Suspected</option>
            <option value="FACT_DISAPPEARED" className="bg-slate-900">Disappeared</option>
            <option value="FACT_REAPPEARED" className="bg-slate-900">Reappeared</option>
            <option value="FACT_SUPERSEDED" className="bg-slate-900">Superseded</option>
            <option value="CONTRADICTION_ADDED" className="bg-slate-900">Contradiction</option>
            <option value="CONTRADICTION_RESOLVED" className="bg-slate-900">Resolved</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold uppercase text-[11px]">Materiality Rating</label>
          <select 
            name="materiality" 
            value={filters.materiality || ""}
            onChange={handleChange}
            className="w-full bg-slate-950 border border-white/15 rounded-lg px-3 h-10 text-white focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
          >
            <option value="" className="bg-slate-900 text-slate-400">Any Materiality</option>
            <option value="CRITICAL" className="bg-slate-900 text-rose-400 font-bold">Critical Severity</option>
            <option value="HIGH" className="bg-slate-900 text-orange-400 font-bold">High Severity</option>
            <option value="MEDIUM" className="bg-slate-900 text-amber-300">Medium Severity</option>
            <option value="LOW" className="bg-slate-900 text-blue-300">Low Severity</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold uppercase text-[11px]">Audit Status</label>
          <select 
            name="review_status" 
            value={filters.review_status || ""}
            onChange={handleChange}
            className="w-full bg-slate-950 border border-white/15 rounded-lg px-3 h-10 text-white focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
          >
            <option value="" className="bg-slate-900 text-slate-400">Any Audit Status</option>
            <option value="OPEN" className="bg-slate-900 text-amber-400 font-bold">Open Action</option>
            <option value="RESOLVED" className="bg-slate-900 text-emerald-400">Resolved</option>
            <option value="SUPERSEDED" className="bg-slate-900 text-slate-400">Superseded</option>
          </select>
        </div>
      </div>

      {showAdvanced && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 pt-4 border-t border-white/10 animate-in fade-in-50 duration-200">
          <div className="space-y-1.5">
            <label className="text-slate-400 font-bold uppercase text-[11px]">From Date</label>
            <input 
              type="date"
              name="date_from"
              value={filters.date_from || ""}
              onChange={handleChange}
              className="w-full bg-slate-950 border border-white/15 rounded-lg px-3 h-10 text-white focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-400 font-bold uppercase text-[11px]">To Date</label>
            <input 
              type="date"
              name="date_to"
              value={filters.date_to || ""}
              onChange={handleChange}
              className="w-full bg-slate-950 border border-white/15 rounded-lg px-3 h-10 text-white focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 transition-all text-xs"
            />
          </div>
        </div>
      )}
    </div>
  );
}
