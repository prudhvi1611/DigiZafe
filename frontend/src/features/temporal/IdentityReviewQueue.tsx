import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { ShieldAlert, CheckCircle2, Clock, RefreshCw, Loader2, AlertCircle, ChevronDown, ChevronUp, X, Eye } from 'lucide-react';

// ---- Types ----

export interface ReviewItem {
  id: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  review_type: string;
  status: 'pending' | 'in_review' | 'resolved' | 'dismissed' | 'superseded';
  reason_code: string;
  affected_profile?: string;
  created_at: string;
  reviewed_at?: string;
  resolution?: string;
  candidate_profile_id?: string;
  anchor_id?: string;
  related_events?: RelatedEvent[];
  orchestration_run_id?: string;
  orchestration_status?: string;
}

export interface RelatedEvent {
  id: string;
  change_type: string;
  safe_title: string;
  detected_at: string;
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  critical: { label: 'Critical', color: 'bg-rose-500/15 text-rose-400 border-rose-500/30', dot: 'bg-rose-400' },
  high: { label: 'High', color: 'bg-orange-500/15 text-orange-400 border-orange-500/30', dot: 'bg-orange-400' },
  medium: { label: 'Medium', color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', dot: 'bg-amber-400' },
  low: { label: 'Low', color: 'bg-blue-500/15 text-blue-400 border-blue-500/30', dot: 'bg-blue-400' },
};

const STATUS_CONFIG: Record<string, { label: string; icon: React.ReactNode }> = {
  pending: { label: 'Pending', icon: <Clock className="w-4 h-4 text-amber-400" /> },
  in_review: { label: 'In Review', icon: <Eye className="w-4 h-4 text-blue-400" /> },
  resolved: { label: 'Resolved', icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" /> },
  dismissed: { label: 'Dismissed', icon: <X className="w-4 h-4 text-slate-400" /> },
  superseded: { label: 'Superseded', icon: <ChevronDown className="w-4 h-4 text-slate-400" /> },
};

const RESOLUTIONS = [
  { value: 'ACKNOWLEDGED', label: 'Acknowledged', description: 'I have seen this alert.' },
  { value: 'THIS_IS_STILL_MINE', label: 'This is still mine', description: 'The change is expected and this profile belongs to me.' },
  { value: 'THIS_IS_NOT_MINE', label: 'This is not mine', description: 'This profile does not belong to me.' },
  { value: 'EXPECTED_CHANGE', label: 'Expected change', description: 'I intentionally made this change.' },
  { value: 'DISMISS_ALERT', label: 'Dismiss alert', description: 'Dismiss without further action.' },
];

const REVALIDATION_STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  planning: 'Planning',
  running: 'Running',
  partial_result: 'Partial result',
  completed: 'Completed',
  no_action: 'No action needed',
  failed: 'Failed',
};

const BLOCKED_REASON_MESSAGES: Record<string, string> = {
  orchestration_budget_exhausted: 'Revalidation could not start because the execution budget was reached.',
  connector_unavailable: 'The connector is temporarily unavailable.',
  duplicate: 'A matching revalidation is already running.',
  connector_test_only_in_prod: 'The available connector is test-only in this environment.',
  missing_consent: 'Consent is required before external discovery can run.',
};

// ---- Mock data ----

function getMockReviews(): ReviewItem[] {
  return [
    {
      id: 'rev_1',
      priority: 'high',
      review_type: 'temporal_change',
      status: 'pending',
      reason_code: 'HIGH_MATERIALITY_CHANGE',
      affected_profile: 'instagram.com/johndoe89',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      related_events: [
        { id: 'evt_1', change_type: 'FACT_VALUE_CHANGED', safe_title: 'Username changed', detected_at: new Date(Date.now() - 3700000).toISOString() },
        { id: 'evt_2', change_type: 'FACT_VALUE_CHANGED', safe_title: 'Avatar changed', detected_at: new Date(Date.now() - 3600000).toISOString() },
      ],
    },
    {
      id: 'rev_2',
      priority: 'critical',
      review_type: 'temporal_change',
      status: 'pending',
      reason_code: 'CRITICAL_ABSENCE_CONFIRMED',
      affected_profile: 'github.com/johndoe',
      created_at: new Date(Date.now() - 86400000).toISOString(),
      related_events: [
        { id: 'evt_3', change_type: 'FACT_DISAPPEARED', safe_title: 'This profile may be unavailable and needs revalidation', detected_at: new Date(Date.now() - 86400000).toISOString() },
      ],
    },
    {
      id: 'rev_3',
      priority: 'medium',
      review_type: 'temporal_change',
      status: 'resolved',
      reason_code: 'MEDIUM_MATERIALITY',
      affected_profile: 'twitter.com/johndoe89',
      created_at: new Date(Date.now() - 172800000).toISOString(),
      reviewed_at: new Date(Date.now() - 86400000).toISOString(),
      resolution: 'EXPECTED_CHANGE',
    },
  ];
}

// ---- Components ----

interface ReviewItemCardProps {
  item: ReviewItem;
  onExpand: (id: string) => void;
  expanded: boolean;
  onResolve: (id: string, resolution: string) => void;
  onRevalidate: (id: string) => void;
  isResolving: boolean;
  isRevalidating: boolean;
}

function ReviewItemCard({ item, onExpand, expanded, onResolve, onRevalidate, isResolving, isRevalidating }: ReviewItemCardProps) {
  const [selectedResolution, setSelectedResolution] = useState('');
  const priority = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.medium;
  const statusInfo = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
  const isActionable = item.status === 'pending' || item.status === 'in_review';

  return (
    <div className={`bg-slate-900 border rounded-xl overflow-hidden transition-all duration-200 ${
      expanded ? 'border-slate-600 shadow-lg shadow-black/20' : 'border-slate-800 hover:border-slate-700'
    }`}>
      {/* Header */}
      <button
        className="review-item w-full flex items-center gap-4 p-5 text-left"
        onClick={() => onExpand(item.id)}
        id={`review-item-${item.id}`}
      >
        <span className={`relative flex h-3 w-3 flex-shrink-0`}>
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${priority.dot} opacity-75`}></span>
          <span className={`relative inline-flex rounded-full h-3 w-3 ${priority.dot}`}></span>
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium border ${priority.color}`}>
              {priority.label}
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-400 font-mono">
              {statusInfo.icon} Status: {statusInfo.label} (Revalidation)
            </span>
          </div>
          <p className="text-sm font-semibold text-slate-200 truncate">
            {item.reason_code.replace(/_/g, ' ')}
          </p>
          {item.affected_profile && (
            <p className="text-xs text-slate-500 mt-0.5 truncate">{item.affected_profile}</p>
          )}
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-slate-600 hidden sm:block">
            {new Date(item.created_at).toLocaleDateString()}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </div>
      </button>

      {/* Detail panel */}
      {expanded && (
        <div className="border-t border-slate-800 p-5 space-y-5">
          {/* Related events */}
          {item.related_events && item.related_events.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Related Events</h3>
              <div className="space-y-2">
                {item.related_events.map(evt => (
                  <div key={evt.id} className="flex items-center gap-3 bg-slate-800/50 rounded-lg px-4 py-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-slate-300">{evt.safe_title}</p>
                      <p className="text-xs text-slate-600 mt-0.5">{new Date(evt.detected_at).toLocaleString()}</p>
                    </div>
                    <span className="ml-auto text-xs font-mono text-slate-600 bg-slate-800 px-2 py-0.5 rounded">
                      {evt.change_type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Revalidation status */}
          {item.orchestration_run_id && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <p className="text-xs font-semibold text-blue-400 mb-1">Revalidation Status</p>
              <p className="text-sm text-blue-300">
                {REVALIDATION_STATUS_LABELS[item.orchestration_status || ''] || item.orchestration_status || 'Unknown'}
              </p>
            </div>
          )}

          {/* Resolution note */}
          {item.resolution && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4">
              <p className="text-xs font-semibold text-emerald-400 mb-1">Resolution</p>
              <p className="text-sm text-emerald-300">{item.resolution.replace(/_/g, ' ')}</p>
              {item.reviewed_at && (
                <p className="text-xs text-slate-600 mt-1">{new Date(item.reviewed_at).toLocaleString()}</p>
              )}
            </div>
          )}

          {/* Actions */}
          {isActionable && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Actions</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {RESOLUTIONS.map(res => (
                  <button
                    key={res.value}
                    onClick={() => setSelectedResolution(res.value)}
                    className={`text-left px-4 py-3 rounded-lg border text-sm transition-all ${
                      selectedResolution === res.value
                        ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300'
                        : 'bg-slate-800/50 border-slate-700 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    <p className="font-medium">{res.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{res.description}</p>
                  </button>
                ))}
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  disabled={!selectedResolution || isResolving}
                  onClick={() => onResolve(item.id, selectedResolution)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  id={`resolve-btn-${item.id}`}
                >
                  {isResolving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Confirm resolution
                </button>

                <button
                  disabled={isRevalidating}
                  onClick={() => onRevalidate(item.id)}
                  className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  id={`revalidate-btn-${item.id}`}
                >
                  {isRevalidating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  Request revalidation
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Page ----

export function IdentityReviewQueue() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['reviews', statusFilter, priorityFilter],
    queryFn: async () => {
      try {
        const params = new URLSearchParams();
        if (statusFilter) params.set('status_filter', statusFilter);
        if (priorityFilter) params.set('priority', priorityFilter);
        return await api.get<ReviewItem[]>(`/temporal/reviews?${params.toString()}`);
      } catch {
        return getMockReviews();
      }
    },
    initialData: getMockReviews(),
    staleTime: 30000,
  });

  const resolveMutation = useMutation({
    mutationFn: async ({ id, resolution }: { id: string; resolution: string }) => {
      return await api.post(`/temporal/reviews/${id}/resolve`, { resolution });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
  });

  const revalidateMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/temporal/reviews/${id}/revalidate`, {});
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || '';
      const blockedKey = Object.keys(BLOCKED_REASON_MESSAGES).find(k => detail.includes(k));
      setBlockedMessage(blockedKey ? BLOCKED_REASON_MESSAGES[blockedKey] : 'Revalidation could not be started. Please try again later.');
    },
  });

  const items = Array.isArray(data) ? data : [];
  const pendingCount = items.filter(i => i.status === 'pending').length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          id="review-status-filter"
          className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        >
          <option value="">All review states</option>
          <option value="pending">Pending</option>
          <option value="in_review">In Review</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          id="review-priority-filter"
          className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        >
          <option value="">All priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {pendingCount > 0 && (
          <span className="ml-auto text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg">
            {pendingCount} pending review{pendingCount > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Blocked message */}
      {blockedMessage && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-300">{blockedMessage}</p>
            <button onClick={() => setBlockedMessage(null)} className="text-xs text-amber-500 mt-1 hover:text-amber-400">Dismiss</button>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : isError ? (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-6 text-rose-400 flex items-center gap-3">
          <AlertCircle className="w-6 h-6" />
          <p>Failed to load review queue. Please try again.</p>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-emerald-400/50 mx-auto mb-4" />
          <p className="text-slate-400 text-lg">No review items found.</p>
          <p className="text-slate-600 text-sm mt-2">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <ReviewItemCard
              key={item.id}
              item={item}
              expanded={expandedId === item.id}
              onExpand={id => setExpandedId(expandedId === id ? null : id)}
              onResolve={(id, resolution) => resolveMutation.mutate({ id, resolution })}
              onRevalidate={id => revalidateMutation.mutate(id)}
              isResolving={resolveMutation.isPending && resolveMutation.variables?.id === item.id}
              isRevalidating={revalidateMutation.isPending && revalidateMutation.variables === item.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
