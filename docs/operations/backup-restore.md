# Backup and Restore

## RPO and RTO Targets
- **Recovery Point Objective (RPO)**: 1 Hour (maximum acceptable data loss).
- **Recovery Time Objective (RTO)**: 4 Hours (maximum acceptable downtime).

## Component Backup Strategy

### 1. PostgreSQL (Primary Datastore)
All durable state, including findings, users, and audit logs, is stored in PostgreSQL.

**Backup Command**:
Run this command from the deployment host to back up the database into an SQL file:
```bash
docker compose exec postgres pg_dump -U postgres -d digizafe > backup_$(date +%F).sql
```

**Retention**: Keep daily backups for 30 days. Weekly backups for 1 year.
**Encryption**: Backups must be encrypted at rest using AES-256 before being moved to cold storage. Access controls should be tightly restricted (least privilege) as backups contain PII.

### 2. Redis Broker
The Redis Broker uses persistent AOF (Append Only File) semantics.
- **Backup**: We do **not** backup the Redis Broker.
- **Recovery**: If the Redis Broker loses its AOF, the broker state is lost. The system recovers safely using Postgres-backed reconciliation tasks. Postgres tracks pending/running jobs. Stalled jobs will be rediscovered and redispatched safely without duplicate side effects due to celery task idempotency.

### 3. Redis Cache
The Redis Cache is strictly ephemeral and disposable.
- **Backup**: Do NOT backup the Redis Cache.
- **Recovery**: Cache misses will occur until the cache is naturally repopulated.

### 4. Cryptographic Key Material
The `secrets/master.key` file encrypts sensitive data (e.g. MFA secrets).
- **Backup**: The key material must be securely backed up in a KMS or secure offline vault separate from database backups.
- **WARNING**: Do NOT lose the master key. Restoring a PostgreSQL database without the matching master key will render all MFA tokens permanently unreadable.
- **Crypto-Shredding Guarantee**: The master key must NEVER be destroyed. Crypto-shredding works by destroying user-specific encrypted blobs and salts in the database. Restoring an old database backup *will* restore the shredded user's data, which is a privacy violation. Ensure backup retention policies comply with deletion requests, or write a script to re-shred accounts upon restoration.

### 5. Residual ML Artifacts
Residual ML artifacts must be backed up alongside the database if `FEATURE_ML_RESIDUAL=true`.
```bash
tar -czvf ml_backup_$(date +%F).tar.gz ml/models/
```

## Restore Procedure

1. Stop the API and workers: `docker compose stop api worker`
2. Drop and recreate the database, or restore into a fresh instance:
```bash
docker compose exec -T postgres psql -U postgres -d digizafe < backup_YYYY-MM-DD.sql
```
3. Run Alembic migrations to ensure the schema matches the code:
```bash
docker compose run --rm api alembic upgrade head
```
4. Restore `secrets/master.key` if the host was lost.
5. Restore ML models to `ml/models/` if necessary.
6. Restart services: `docker compose start api worker`

### Restore Verification
After restore, immediately perform these verification steps:
1. Call `/health/ready` and verify HTTP 200.
2. Verify you can log in with a test account.
3. Validate that you can decrypt a user's MFA setting or initiate a dummy scan.
4. Run `scripts/smoke_test.py` to confirm full critical path integrity.
