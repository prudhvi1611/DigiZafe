# Rollback Runbook

## Rollback Strategy
The primary rollback strategy for DigiZafe is to **revert to the previous immutable image** (Image Rollback) and rely on backward-compatible database migrations. Alembic downgrade is NOT the automatic default and should be avoided whenever possible.

### 1. Minor Release Rollback (Backward-Compatible Schema or No Schema Changes)
If a recent release causes critical bugs or SLO violations, but the schema changes (if any) are backward-compatible:
1. Revert to the previous immutable image tag in your deployment manifests or `docker-compose.yml`.
2. Restart the services: `docker compose up -d api worker`
3. Verify `/health/ready` and ensure SLOs recover.
*Note: This is the preferred recovery path. Future releases should always aim to write non-breaking migrations (e.g. adding columns instead of dropping or renaming) so that older code versions can still run against the newer database schema.*

### 2. Major Release Rollback (Breaking Schema Changes)
If a release included breaking Alembic migrations and the older image CANNOT run against the new schema, choose one of the following paths:

**Path A: Forward Fix (Preferred)**
1. Keep the current release running or partially degraded.
2. Immediately commit a hotfix to patch the bug while preserving the new schema structure.
3. Deploy the hotfix.

**Path B: Backup Restore (Safe Data Regression)**
1. Restore the PostgreSQL database from a known good backup taken immediately before the release (see `backup-restore.md`).
2. Revert to the previous immutable image tag.
3. Restart services: `docker compose up -d api worker`
*(This will result in data loss for writes that occurred during the window the bad release was active).*

**Path C: Alembic Downgrade (Use With Extreme Caution)**
Only use schema downgrade if the downgrade path has been explicitly tested, reviewed, and is proven safe.
1. Identify the previous Alembic revision hash: `docker compose run --rm api alembic history`
2. Downgrade the database schema to the known good revision:
   ```bash
   docker compose run --rm api alembic downgrade <previous_revision_hash>
   ```
3. Revert to the previous immutable image tag.
4. Restart services: `docker compose up -d api worker`

**Warning**: Downgrading schemas may result in the automatic DROP of tables or columns, permanently destroying data written by the bad release. Always take a database backup before a major downgrade if preserving the interim data is critical.
