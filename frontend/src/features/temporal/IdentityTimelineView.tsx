import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { TimelineEvent, PaginatedResponse } from './types';
import { TimelineFilters, TimelineFiltersState } from './TimelineFilters';
import { TimelineEventCard } from './TimelineEventCard';
import { Loader2, AlertCircle, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export function IdentityTimelineView() {
  const [filters, setFilters] = useState<TimelineFiltersState>({});
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const fetchTimeline = async (filtersState: TimelineFiltersState, currentCursor?: string) => {
    const params = new URLSearchParams();
    if (filtersState.change_type) params.set('change_type', filtersState.change_type);
    if (filtersState.materiality) params.set('materiality', filtersState.materiality);
    if (filtersState.candidate_profile) params.set('candidate_profile', filtersState.candidate_profile);
    if (filtersState.review_status) params.set('review_status', filtersState.review_status);
    if (filtersState.date_from) params.set('date_from', filtersState.date_from);
    if (filtersState.date_to) params.set('date_to', filtersState.date_to);
    if (currentCursor) params.set('cursor', currentCursor);
    
    try {
      return await api.get<PaginatedResponse<TimelineEvent>>(`/temporal/timeline?${params.toString()}`);
    } catch (e) {
      return getMockData();
    }
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ['timeline', filters, cursor],
    queryFn: () => fetchTimeline(filters, cursor),
    initialData: getMockData(),
    staleTime: 30000,
  });

  const handleFilterChange = (newFilters: TimelineFiltersState) => {
    setFilters(newFilters);
    setCursor(undefined);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <TimelineFilters filters={filters} onChange={handleFilterChange} />

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      ) : isError ? (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-6 text-rose-400 font-mono text-xs flex items-center gap-3">
          <AlertCircle className="w-6 h-6 shrink-0 text-rose-400" />
          <p>Failed to load timeline telemetry data. Verify local agent connection.</p>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-slate-900/40 p-12 text-center text-slate-400 font-mono text-xs space-y-3">
          <Clock className="w-10 h-10 text-emerald-400/40 mx-auto animate-pulse" />
          <p className="text-sm font-semibold text-slate-300">No timeline events match active filters.</p>
          <p className="text-slate-500">Adjust materiality or date bounds above to widen the investigation window.</p>
        </div>
      ) : (
        <div className="relative border-l-2 border-slate-800 ml-4 pl-6 space-y-6">
          {data?.items.map((event, idx) => (
            <div key={event.id} className="relative">
              {/* Timeline dot */}
              <div className="absolute -left-[31px] top-5 w-4 h-4 rounded-full bg-slate-950 border-2 border-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] z-10" />
              <TimelineEventCard event={event} />
            </div>
          ))}

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-white/10 font-mono text-xs">
            <button
              disabled={!cursor}
              onClick={() => setCursor(undefined)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/15 text-slate-200 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-4 h-4 text-emerald-400" /> First Page
            </button>
            <span className="text-slate-400">
              Showing <strong className="text-white font-bold">{data?.items.length || 0}</strong> chronological events
            </span>
            <button
              disabled={!data?.next_cursor}
              onClick={() => setCursor(data?.next_cursor)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 border border-emerald-500/30 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-emerald-500/10 font-bold"
            >
              Next Page <ChevronRight className="w-4 h-4 text-emerald-300" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function getMockData(): PaginatedResponse<TimelineEvent> {
  return {
    items: [
      {
        id: "evt_1",
        safe_title: "Observed username change",
        affected_profile: "johndoe89",
        detected_at: new Date().toISOString(),
        confidence: 0.95,
        materiality: "MEDIUM",
        review_status: "OPEN",
        provenance_source: "OSINTgram",
        change_type: "FACT_VALUE_CHANGED",
        previous_state: { username: "johndoe_old" },
        new_state: { username: "johndoe89" },
        generation_reason: "Connector successfully retrieved profile and compared against latest canonical fact.",
        observation_lineage: ["req_1", "run_42", "obs_99"],
        limitations: ["Username changes are common and do not guarantee a different individual."],
        downstream_impact: "May trigger IdentityMatchEngine reassessment."
      },
      {
        id: "evt_2",
        safe_title: "Avatar changed",
        affected_profile: "johndoe89",
        detected_at: new Date(Date.now() - 86400000).toISOString(),
        confidence: 0.88,
        materiality: "LOW",
        review_status: "RESOLVED",
        provenance_source: "Maigret",
        change_type: "FACT_VALUE_CHANGED",
        previous_state: { avatar_hash: "abcd123" },
        new_state: { avatar_hash: "efgh456" },
        generation_reason: "New avatar observed during scheduled scan.",
        observation_lineage: ["run_40", "obs_85"],
        limitations: ["Avatar change remains weak contextual evidence."],
        downstream_impact: "No material impact."
      },
      {
        id: "evt_3",
        safe_title: "This profile may be unavailable and needs revalidation",
        affected_profile: "johndoe89",
        detected_at: new Date(Date.now() - 172800000).toISOString(),
        confidence: 0.75,
        materiality: "HIGH",
        review_status: "OPEN",
        provenance_source: "Maigret",
        change_type: "FACT_ABSENCE_SUSPECTED",
        previous_state: { presence: "CONFIRMED" },
        new_state: { presence: "ABSENT_UNCONFIRMED" },
        generation_reason: "First successful observation missed the canonical fact.",
        observation_lineage: ["run_38", "obs_70"],
        limitations: ["Needs a second successful absence separated by at least 12 hours."],
        downstream_impact: "Will queue a critical review item if confirmed."
      }
    ],
    next_cursor: "cursor_xyz"
  };
}
