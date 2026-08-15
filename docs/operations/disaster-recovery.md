# Disaster Recovery

This document outlines recovery strategies for DigiZafe operations based on Sprint 13 architecture.

## Primary Outages
### Database (PostgreSQL) Loss
1. System will fail readiness checks (`/health/ready` returns 500/unready).
2. API operations will largely fail. 
3. **Recovery**: Restore from latest backup (see `backup-restore.md`). Run migrations. Check integrity.

### Redis Loss
1. System will fail `/health/ready` (returns 503 Service Unavailable if any Redis dependency is down).
2. **Redis Cache Loss**: The cache is strictly disposable. Restarting the cache container allows the system to rebuild data on demand without data loss.
3. **Redis Broker Loss**: The broker uses persistent AOF semantics. While queue state may be lost if AOF is unrecoverable, the system relies on Postgres-backed reconciliation. Re-dispatch missing work through the scheduled reconciliation tasks (which scan Postgres for stalled tasks) to safely restart them. Idempotency guarantees in Celery tasks prevent duplicate side effects.

### Worker Loss
1. API remains up and responds to reads.
2. Scans remain in `running` or `pending` indefinitely.
3. **Recovery**: Restart celery worker containers. The `scan_stale_running_minutes` and reconciliation tasks will catch stalled scans and retry or fail them gracefully.

### Optional Subsystems
1. **Groq / LLM Outage**: Wait out the outage. System automatically falls back to Deterministic Narrative. No action required.
2. **Residual ML Corruption**: If `FEATURE_ML_RESIDUAL=true` but artifact checksum validation fails at startup, the system fails closed and refuses to boot. Operators must either restore a valid model or disable the feature (`FEATURE_ML_RESIDUAL=false`) and restart to fall back to the Deterministic PDSS algorithm, which will operate normally.
3. **Third-party Connector Outage**: External OSINT API limits/outages will result in specific connectors returning `failed`. The scan itself will complete with partial findings (or fail closed if consent requires it). Wait out the upstream outage.
