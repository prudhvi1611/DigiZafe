# Service Level Objectives (SLOs)

This document defines the baseline SLOs for DigiZafe operations based on the architectural constraints of Sprint 13.

## Availability
- **API Uptime**: 99.9% target for core features (Discovery, Score, Auth).
- **Graceful Degradation**: 
  - If Redis Broker is down, scan creation is paused, but reads (PDSS/Findings) remain 100% functional.
  - If Groq/Ollama fails, the system falls back to Deterministic Narrative. This preserves API uptime.
  - If Residual ML validation fails at startup (when explicitly enabled), the system fails closed. Operators may manually disable the feature to restart with Deterministic PDSS.
## Latency
- **API Request (Read)**: 95th percentile < 250ms for synchronous endpoints.
- **Narrative Generation**: 95th percentile < 3 seconds (when hitting LLM) and < 100ms on Deterministic Fallback.

## Data Retention & Privacy
- **Raw Evidence TTL**: Max 24 hours.
- **Summary Evidence TTL**: Max 30 days.
- **Account Deletion (Crypto-shred)**: Immediate removal of PII upon verified request; associated audit records are anonymized but retained for 365 days.

## Monitoring
- Prometheus metrics are available at `/metrics`. 
- **Security Constraint**: The `/metrics` endpoint is unauthenticated by design to support internal Prometheus scraping. It **MUST NOT** be publicly exposed to the internet. Protect it at the deployment/network layer (e.g., using ingress rules or internal VPC boundaries).
- Metric labels contain no PII, secrets, identifiers, user IDs, or unbounded high-cardinality values.
- Key metrics to monitor: `api_request_latency_seconds`, `api_request_count_total`, `worker_task_outcome_total`.
