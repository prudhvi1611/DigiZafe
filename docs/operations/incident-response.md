# Incident Response Runbook

## Overview
This runbook covers how to respond to common operational incidents in DigiZafe. All incidents must be managed by the designated **Incident Commander (IC)**, supported by the **Platform Engineering** and **Security Operations** leads.

## Severity 1: Critical Security Compromise

### 1.1 Data Breach / PII Leak / Cross-User RLS Exposure
1. **Symptoms**: Reports of users seeing other users' data, or external pastebin dumps containing DigiZafe data.
2. **Action**: Stop all external traffic immediately: `docker compose stop api`.
3. **Escalation**: Notify Incident Commander.
4. **Investigation**: Review PostgreSQL audit logs and API logs. Verify Postgres Row-Level Security (RLS) configuration.
5. **Recovery**: Patch the vulnerability. Notify affected users. Do not restart API until the IC confirms the fix.

### 1.2 Signing / Encryption Secret Compromise
1. **Symptoms**: `secrets/master.key` or JWT secrets leaked in a public repository or exposed logs.
2. **Action**: Suspend all services: `docker compose stop api worker`.
3. **Escalation**: Notify Incident Commander.
4. **Recovery**:
   - Rotate the master key and JWT secrets.
   - For JWT: Invalidate all active sessions.
   - For Master Key: This requires a specialized offline key-translation script to decrypt all database MFA tokens with the old key and re-encrypt with the new key.
   - Deploy new secrets and restart services.

### 1.3 Backup Compromise
1. **Symptoms**: Unauthorized access to the S3 bucket or cold storage where PostgreSQL backups are kept.
2. **Action**: Revoke compromised IAM credentials.
3. **Escalation**: Notify Incident Commander.
4. **Investigation**: Assume all encrypted backups were downloaded. Since backups are encrypted at rest with AES-256, verify if the encryption keys were also compromised. If yes, treat as a full Data Breach (1.1).

### 1.4 Account Takeover (ATO)
1. **Symptoms**: Anomalous login patterns, brute force alerts, or user reports of unauthorized actions.
2. **Action**: Lock the affected accounts (`is_active=False`) via admin console or DB.
3. **Escalation**: Notify Security Operations Lead.
4. **Recovery**: Invalidate user sessions, require password reset, and mandate MFA enrollment for affected users.

## Severity 2: High Impact Operational / Security Events

### 2.1 SSRF / Egress Bypass
1. **Symptoms**: API requests attempting to access internal network space (e.g., `169.254.169.254` or `10.0.x.x`) that succeed.
2. **Action**: Update the Egress Fetcher `egress_host_allowlist` configuration to explicitly block the abused domains/IPs, or disable the vulnerable connector.
3. **Escalation**: Notify Platform Engineering Lead.

### 2.2 Malicious / Compromised Connector
1. **Symptoms**: Upstream OSINT provider begins returning poisoned data, malicious payloads, or redirecting to phishing sites.
2. **Action**: Disable the specific connector in `connector_configs` table (`is_active=False`).
3. **Escalation**: Notify Platform Engineering Lead.
4. **Recovery**: Purge cached Redis results for this connector. Invalidate recent `Observation` rows originating from this connector.

### 2.3 Core Database Unreachable
1. **Symptoms**: `/health/ready` fails. API returns 503s.
2. **Action**: Check `docker compose logs postgres`.
3. **Recovery**:
   - If out of space: Expand volume or clear old WALs.
   - If corrupted: Follow Disaster Recovery plan to restore from backup.
4. **Escalation**: Notify Platform Engineering Lead.

## Severity 3: Degraded Performance & Failures

### 3.1 Worker Queues Stalling
1. **Symptoms**: Scans remain `running` for > 30 minutes. Worker metrics show no completions.
2. **Action**: Restart the worker container `docker compose restart worker`.
3. **Recovery**: Stale scans will be automatically reconciled by the `reconcile_scans_task` periodic beat.

### 3.2 Crypto-Shred / Deletion Failure
1. **Symptoms**: Prometheus metrics show failed `crypto_shred` Celery tasks, or privacy audit logs show errors.
2. **Action**: Manually verify if the user's data remains in the database.
3. **Escalation**: Notify Platform Engineering Lead.
4. **Recovery**: Identify the foreign key constraint or database lock causing the failure, patch the `execute_shred` logic, and manually re-queue the deletion task.

## Severity 4: Localized Service Outages

### 4.1 Redis Outage
1. **Symptoms**: `/health/ready` fails for `broker_redis_unavailable` or `cache_redis_unavailable`.
2. **Action**: Restart Redis containers `docker compose restart redis-broker redis-cache`.
3. **Impact**: Scans in progress might be dropped if the broker AOF is lost, but they will be reconciled safely.

### 4.2 Optional ML Corruption
1. **Symptoms**: Service fails to start with `startup_validation_failed` due to `Residual ML artifact checksum mismatch`.
2. **Action**: Set `FEATURE_ML_RESIDUAL=false` and restart `api` and `worker`. The system will fall back to Deterministic PDSS.
3. **Recovery**: Rebuild the model and update the registry with the new trusted checksum.
