export type ChangeType = 
  | "FACT_APPEARED" 
  | "FACT_VALUE_CHANGED" 
  | "FACT_BECAME_STALE" 
  | "FACT_EXPIRED" 
  | "FACT_ABSENCE_SUSPECTED" 
  | "FACT_DISAPPEARED" 
  | "FACT_REAPPEARED" 
  | "FACT_SUPERSEDED" 
  | "CONTRADICTION_ADDED" 
  | "CONTRADICTION_RESOLVED" 
  | "USER_DECISION_CHANGED";

export type Materiality = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ReviewStatus = "OPEN" | "RESOLVED" | "SUPERSEDED";

export interface TimelineEvent {
  id: string;
  safe_title: string;
  affected_profile: string;
  detected_at: string;
  confidence: number;
  materiality: Materiality;
  review_status: ReviewStatus;
  provenance_source: string;
  change_type: ChangeType;
  previous_state?: Record<string, unknown> | null;
  new_state?: Record<string, unknown> | null;
  generation_reason?: string;
  observation_lineage?: string[];
  limitations?: string[];
  downstream_impact?: string;
}

export type ReviewResolution = 
  | "ACKNOWLEDGED" 
  | "THIS_IS_STILL_MINE" 
  | "THIS_IS_NOT_MINE" 
  | "EXPECTED_CHANGE" 
  | "REQUEST_REVALIDATION" 
  | "DISMISS_ALERT";

export type RevalidationState = 
  | "queued" 
  | "planning" 
  | "running" 
  | "partial_result" 
  | "completed" 
  | "no_action" 
  | "failed";

export interface ReviewItem {
  id: string;
  priority: Materiality;
  review_type: string;
  affected_profile: string;
  reason: string;
  related_events?: TimelineEvent[];
  created_at: string;
  status: ReviewStatus;
  available_actions: ReviewResolution[];
  revalidation_status?: RevalidationState;
  revalidation_detail?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor?: string;
  total?: number;
}
