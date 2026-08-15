from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DigiZafe"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    master_key_file: str = "./secrets/master.key"

    # Database
    database_url: str = Field(..., description="Async SQLAlchemy URL (postgresql+asyncpg://...)")

    # Redis
    redis_broker_url: str = "redis://localhost:6379/0"
    redis_cache_url: str = "redis://localhost:6380/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json | console

    # Feature flags
    feature_xposedornot: bool = True
    feature_hibp_breach_api: bool = False
    feature_capsolver: bool = False
    feature_ml_residual: bool = False
    feature_maigret_discovery: bool = False
    feature_identity_cross_links: bool = False
    feature_avatar_similarity: bool = False
    feature_identity_clustering: bool = False
    feature_osintgram_discovery: bool = False
    feature_connector_orchestration: bool = False
    feature_evidence_freshness: bool = False
    feature_incremental_reassessment: bool = False
    feature_identity_timeline: bool = False
    feature_identity_change_detection: bool = False
    feature_identity_review_queue: bool = False
    feature_automatic_revalidation: bool = False
    # Sprint 22: Live connector smoke testing — disabled by default, operator-controlled
    enable_live_connector_smoke_tests: bool = False

    # Optional keys
    hibp_api_key: str | None = None
    capsolver_api_key: str | None = None
    xposedornot_api_key: str | None = None

    # Quotas
    default_user_scan_quota_per_day: int = 20

    # === Sprint 1: Auth & Crypto ===
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 14
    jwt_secret_key: str | None = None  # falls back to secret_key

    mfa_issuer: str = "DigiZafe"
    mfa_totp_digits: int = 6
    mfa_totp_interval: int = 30

    audit_retention_days: int = 365
    password_min_length: int = 12
    max_failed_login_attempts: int = 10
    login_lockout_minutes: int = 15

    # === Sprint 2: Identifiers & Verification ===
    egress_timeout_seconds: float = 10.0
    egress_allowed_schemes: str = "http,https"
    egress_host_allowlist: str = ""  # comma-separated; empty = public internet
    egress_max_response_bytes: int = 5242880  # 5MB
    github_token: str | None = None

    verification_token_ttl_minutes: int = 30
    verification_email_code_length: int = 6
    verification_dev_expose_code: bool = True

    identifier_revalidation_days: int = 90

    # === Sprint 3: Connectors ===
    connector_default_cache_ttl_seconds: int = 3600
    connector_negative_cache_ttl_seconds: int = 86400
    connector_per_user_probe_quota_per_day: int = 30

    xposedornot_base_url: str = "https://api.xposedornot.com"
    xposedornot_rate_per_second: float = 1.5
    xposedornot_rate_per_hour: int = 20
    xposedornot_rate_per_day: int = 80
    xposedornot_attribution: str = (
        "Data: XposedOrNot (https://xposedornot.com) — free personal tier; respect ToS"
    )

    feature_pwned_passwords: bool = True
    pwned_passwords_base_url: str = "https://api.pwnedpasswords.com"

    feature_crtsh: bool = True
    feature_rdap: bool = True
    feature_github_connector: bool = True
    feature_gravatar: bool = True
    feature_username_presence: bool = True
    feature_serp_ddg: bool = True

    # === Sprint 4: Discovery & Evidence ===
    scan_default_deadline_minutes: int = 30
    scan_max_concurrent_per_user: int = 2
    scan_reconcile_interval_seconds: int = 60
    scan_stale_running_minutes: int = 45

    evidence_raw_ttl_hours: int = 24
    evidence_summary_ttl_days: int = 30

    sse_poll_interval_seconds: float = 1.5
    sse_heartbeat_seconds: float = 15.0
    sse_max_duration_seconds: int = 1800

    # === Sprint 5: Identity & PDSS ===
    pdss_model_version: str = "pdss-v1.0.0"
    pdss_catalog_path: str = "./shared/score_model/pdss_catalog.json"
    deciban_weights_path: str = "./shared/score_model/deciban-weights.json"

    linkage_auto_link_prob: float = 0.95
    linkage_review_prob: float = 0.70
    linkage_collision_flag_prob: float = 0.50

    score_history_retention_days: int = 365
    whatif_max_findings_removed: int = 50

    # === Sprint 6: Recommendations & Alerts ===
    recommendation_model_version: str = "rec-v1.0.0"
    recommendation_catalog_path: str = "./shared/score_model/recommendation_catalog.json"

    alert_score_jump_threshold: float = 1.0
    alert_new_high_severity: bool = True
    alert_retention_days: int = 90

    rescan_cooldown_hours: int = 6
    feature_scheduled_rescans: bool = True
    scheduled_rescan_interval_hours: int = 168
    alert_reconcile_interval_seconds: int = 120

    # === Sprint 7: Remediation ===
    feature_remediation: bool = True

    broker_optout_recheck_days: int = 90
    broker_email_confirm_retry_days: int = 14
    broker_max_concurrent_jobs_per_user: int = 1
    broker_job_deadline_minutes: int = 120
    broker_runner_timeout_seconds: int = 90
    broker_registry_path: str = "./shared/config/broker_registry/brokers_green.json"

    playwright_headless: bool = True
    playwright_slow_mo_ms: int = 0
    playwright_user_data_dir: str = "/tmp/digizafe-pw"

    captcha_mode: str = "manual"  # manual | open_in_browser | capsolver
    captcha_queue_ttl_hours: int = 48

    remediation_auto_rescore: bool = True
    remediation_auto_rescan: bool = False
    remediation_verify_after_submit: bool = True

    feature_update_brokers: bool = True
    update_brokers_interval_hours: int = 168

    # === Sprint 8: Privacy / Rights / Explain ===
    feature_data_export: bool = True
    feature_crypto_shred: bool = True
    feature_grounded_narrative: bool = True
    feature_residual_ml: bool = False

    # === Sprint 11: Deep + Constrained-Dark Free Amber ===
    feature_deep_amber: bool = True
    feature_constrained_dark: bool = False
    amber_scan_requires_consent: bool = True
    
    common_crawl_enabled: bool = True
    common_crawl_collection: str = ""
    common_crawl_index_base_url: str = "https://index.commoncrawl.org"
    common_crawl_max_results: int = 50
    common_crawl_cache_ttl_seconds: int = 21600
    common_crawl_rate_per_second: float = 0.2
    common_crawl_rate_per_hour: int = 30
    common_crawl_rate_per_day: int = 100
    
    wayback_enabled: bool = True
    wayback_availability_url: str = "https://archive.org/wayback/available"
    wayback_max_results: int = 10
    wayback_cache_ttl_seconds: int = 21600
    wayback_rate_per_second: float = 0.2
    wayback_rate_per_hour: int = 30
    wayback_rate_per_day: int = 100
    
    amber_public_index_url: str = ""
    amber_public_index_host_allowlist: str = ""
    amber_public_index_query_param: str = "q"
    amber_public_index_max_results: int = 25
    amber_public_index_cache_ttl_seconds: int = 21600
    amber_public_index_rate_per_second: float = 0.1
    amber_public_index_rate_per_hour: int = 10
    amber_public_index_rate_per_day: int = 30

    @property
    def amber_public_index_hosts(self) -> str:
        return self.amber_public_index_host_allowlist

    # === Sprint 12: Residual ML ===
    residual_ml_model_version: str = "residual-risk-v1"
    residual_ml_model_path: str = "./ml/models/residual-risk-v1.joblib"
    residual_ml_feature_schema_version: str = "residual-features-v1"
    residual_ml_max_abs_delta: float = 5.0
    residual_ml_min_confidence: float = 0.70
    residual_ml_timeout_ms: int = 250
    residual_ml_fail_open_to_deterministic: bool = True

    export_max_bytes: int = 52_428_800
    export_include_audit: bool = True
    export_include_egress: bool = True

    # === Sprint 18: Enrichment & Clustering ===
    avatar_max_download_bytes: int = 2097152 # 2MB
    avatar_max_width: int = 2048
    avatar_max_height: int = 2048
    avatar_max_decoded_pixels: int = 4194304 # 2048x2048
    avatar_network_timeout_seconds: float = 10.0
    avatar_processing_timeout_seconds: float = 5.0
    avatar_max_redirects: int = 3
    avatar_supported_mime_types: list[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    
    avatar_similarity_exact_hash_algo: str = "sha256"
    avatar_similarity_phash_threshold: int = 8

    # === Sprint 20: Orchestration & Freshness ===
    connector_orchestration_policy_version: int = 1
    evidence_freshness_policy_version: int = 1
    
    orchestration_max_runs_per_user_per_hour: int = 5
    orchestration_max_runs_per_user_per_day: int = 20
    orchestration_max_active_runs_per_user: int = 1
    orchestration_max_aliases_per_run: int = 5
    orchestration_max_executions_per_run: int = 10
    orchestration_max_concurrent_per_connector_per_user: int = 1
    
    maigret_max_concurrent_runs: int = 10
    osintgram_max_concurrent_runs: int = 5

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_evaluation_window_seconds: int = 300
    circuit_breaker_open_cooldown_seconds: int = 600
    circuit_breaker_half_open_probe_count: int = 1

    account_delete_grace_hours: int = 24
    account_delete_dev_immediate: bool = True
    account_delete_confirm_phrase: str = "DELETE MY DIGIZAFE ACCOUNT"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    narrative_timeout_seconds: float = 60.0
    narrative_enabled: bool = True

    narrative_max_findings: int = 15
    narrative_max_tokens: int = 800
    narrative_temperature: float = 0.2

    # === Sprint 21: Temporal Evidence & Review ===
    identity_change_policy_version: int = 1
    identity_review_policy_version: int = 1
    change_burst_window_minutes: int = 30
    automatic_revalidation_cooldown_hours: int = 24
    
    manual_revalidation_max_runs_per_user_per_hour: int = 10
    manual_revalidation_max_runs_per_user_per_day: int = 30

    @field_validator("cors_origins", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("secret_key")
    @classmethod
    def secret_key_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret_key or self.secret_key

    @property
    def egress_schemes(self) -> set[str]:
        return {s.strip().lower() for s in self.egress_allowed_schemes.split(",") if s.strip()}

    @property
    def egress_allowlist_hosts(self) -> set[str]:
        return {h.strip().lower() for h in self.egress_host_allowlist.split(",") if h.strip()}

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

@lru_cache
def get_settings() -> Settings:
    return Settings()
