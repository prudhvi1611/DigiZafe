export type IdentifierType =
  | "email"
  | "phone"
  | "username"
  | "domain"
  | "github_username";

export interface UserPublic {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  mfa_required?: boolean;
}

export interface IdentifierPublic {
  id: string;
  type: string;
  value_display: string;
  value_canonical: string;
  is_verified: boolean;
  verified_at?: string | null;
  verification_method?: string | null;
  last_revalidated_at?: string | null;
  created_at: string;
}

export interface VerificationStartResponse {
  challenge_id: string;
  method: string;
  expires_at: string;
  instructions: Record<string, unknown>;
  dev_code?: string | null;
}

export interface ScanPublic {
  id: string;
  identifier_id: string;
  status: string;
  layer_scope: string;
  connector_ids?: string[] | null;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
  observation_count: number;
  finding_count: number;
  deadline_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  meta?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  connector_runs?: ScanConnectorRun[];
}

export interface ScanConnectorRun {
  id: string;
  connector_id: string;
  status: string;
  skip_reason?: string | null;
  error?: string | null;
  cache_hit: boolean;
  observation_count: number;
  finding_count: number;
  result_meta?: Record<string, unknown> | null;
}

export interface FindingPublic {
  id: string;
  identifier_id: string;
  kind: string;
  source: string;
  title: string;
  summary: string;
  severity_hint: string;
  confidence: number;
  layer: string;
  track: string;
  raw_ref?: string | null;
  attributes?: Record<string, unknown> | null;
  attribution?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  times_seen: number;
  status: string;
  created_at: string;
}

export interface ScorePublic {
  id?: string | null;
  identifier_id?: string | null;
  model_version: string;
  score_confirmed: number;
  score_possible: number;
  score_combined: number;
  severity: string;
  vector: string;
  metrics?: Record<string, number> | null;
  contributions?: Contribution[] | null;
  counterfactuals?: Counterfactual[] | null;
  attributions?: string[] | null;
  explanation_summary: string;
  finding_count: number;
  trigger?: string;
  created_at?: string | null;
  meta?: Record<string, unknown> | null;
  residual_ml?: ResidualMLPublic | null;
}

export interface ResidualMLPublic {
  status: 'disabled' | 'evaluated' | 'abstained';
  model_version: string;
  schema_version: string;
  delta: number;
  abstained: boolean;
  reason?: string | null;
}

export interface Contribution {
  finding_id: string;
  kind: string;
  source: string;
  track: string;
  title: string;
  base: number;
  temporal: number;
  environmental: number;
  surprisal: number;
  reuse: number;
  raw_score: number;
  weighted_score: number;
  drivers?: Record<string, unknown>[];
  vector_fragment?: string;
}

export interface Counterfactual {
  action?: string;
  finding_id?: string;
  title?: string;
  source?: string;
  score_before?: number;
  score_after?: number;
  delta?: number;
  narrative?: string;
}

export interface RecommendationPublic {
  id: string;
  plan_id: string;
  identifier_id?: string | null;
  code: string;
  lane: string;
  title: string;
  summary: string;
  urgency: number;
  effort_hours: number;
  roi: number;
  priority: number;
  sort_order: number;
  depends_on?: string[] | null;
  related_finding_ids?: string[] | null;
  steps?: string[] | null;
  links?: { label: string; url: string }[] | null;
  playbook_key: string;
  meta?: Record<string, unknown> | null;
  status: string;
  model_version: string;
  created_at: string;
}

export interface PlanPublic {
  id: string;
  identifier_id?: string | null;
  model_version: string;
  score_snapshot_id?: string | null;
  freeze_recommended: boolean;
  dag_order?: string[] | null;
  summary: string;
  meta?: Record<string, unknown> | null;
  created_at: string;
  recommendations: RecommendationPublic[];
}

export interface IdentityGraphPublic {
  nodes: { id: string; type: string; value_display: string; is_verified: boolean }[];
  edges: {
    id: string;
    left_identifier_id: string;
    right_identifier_id: string;
    match_weight: number;
    match_prob: number;
    decision: string;
    review_status: string;
  }[];
  collisions?: { id: string; reason: string }[];
  model_version: string;
}

export interface ApiError {
  detail?: string | unknown;
  title?: string;
  code?: string;
}
export interface BrokerCatalogItem {
  id: string;
  name: string;
  method: string;
  legality: string;
  opt_out_url: string;
  requires_captcha: boolean;
  requires_email_confirm: boolean;
  form_field_map?: Record<string, string>;
  success_hints?: string[];
  enabled?: boolean;
  notes?: string;
}

export interface BrokerStatePublic {
  id: string;
  broker_id: string;
  broker_name: string;
  status: string;
  last_success_at?: string | null;
  last_attempt_at?: string | null;
  last_verified_at?: string | null;
  total_runs: number;
  detail?: string | null;
  meta?: Record<string, unknown> | null;
  updated_at: string;
}

export interface RemediationJobItem {
  id: string;
  broker_id: string;
  broker_name: string;
  status: string;
  skip_reason?: string | null;
  error?: string | null;
  detail?: string | null;
  result_meta?: Record<string, unknown> | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface RemediationJob {
  id: string;
  identifier_id?: string | null;
  job_type: string;
  status: string;
  dry_run: boolean;
  broker_ids?: string[] | null;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
  result_summary?: Record<string, unknown> | null;
  deadline_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  items: RemediationJobItem[];
}

export interface CaptchaQueueItem {
  id: string;
  job_id: string;
  broker_id: string;
  status: string;
  page_url?: string | null;
  captcha_type: string;
  instructions?: string | null;
  expires_at: string;
  created_at: string;
}

export interface FreezeChecklistItem {
  id: string;
  target_id: string;
  label: string;
  url: string;
  status: string;
  notes?: string | null;
  completed_at?: string | null;
}

export interface GeneratedRequest {
  id: string;
  kind: string;
  regime: string;
  recipient_name?: string | null;
  recipient_email?: string | null;
  subject: string;
  body: string;
  status: string;
  deadline_at?: string | null;
  sent_at?: string | null;
  created_at: string;
}

export interface ConsentItem {
  id?: string | null;
  purpose: string;
  scope?: string | null;
  granted: boolean;
  created_at?: string | null;
  revoked_at?: string | null;
  details?: Record<string, unknown> | null;
}

export interface AuditEvent {
  id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
  correlation_id?: string | null;
}

export interface EgressEvent {
  id: string;
  purpose: string;
  destination_host: string;
  method: string;
  status_code?: number | null;
  success: boolean;
  summary?: Record<string, unknown> | null;
  created_at: string;
}

export interface ExportJob {
  id: string;
  status: string;
  include_audit: boolean;
  include_egress: boolean;
  size_bytes: number;
  expires_at: string;
  created_at: string;
  ready_at?: string | null;
  error?: string | null;
}

export interface ExportPackageResponse {
  job: ExportJob;
  package?: Record<string, unknown> | null;
}

export interface NarrativeBriefing {
  id?: string | null;
  score_snapshot_id?: string | null;
  identifier_id?: string | null;
  mode: string;
  model_name?: string | null;
  title: string;
  body_markdown: string;
  grounded: boolean;
  facts_used?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface CounterfactualResponse {
  score_snapshot_id?: string | null;
  counterfactuals: Counterfactual[];
  explanation_summary: string;
  vector?: string | null;
  score_combined?: number | null;
}

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  complete: boolean;
  href: string;
}
export type ExposureLayer = "surface" | "deep" | "constrained_dark";

export interface LayerMetadata {
  layer: ExposureLayer;
  label: string;
  description: string;
  warning: string;
  requires_explicit_consent: boolean;
}

export interface LayerCatalogResponse extends Array<LayerMetadata> {}

export interface ScanCreateRequest {
  identifier_id: string;
  connector_ids?: string[];
  layer_scope: ExposureLayer;
}

