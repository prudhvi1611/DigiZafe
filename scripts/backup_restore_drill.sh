#!/usr/bin/env bash
set -e

# Backup and Restore Drill for DigiZafe Integration Environment
# This script targets the isolated integration database only.

DB_CONTAINER="digizafe-postgres-1"
DB_USER="digizafe"
DB_NAME="digizafe"
BACKUP_FILE="/tmp/digizafe_integration_backup.dump"

echo "=== DigiZafe Backup & Restore Drill ==="

# 1. Verify we are targeting the integration DB
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "ERROR: Integration DB container '${DB_CONTAINER}' not found."
  echo "This script must only be run against the local integration environment."
  exit 1
fi

echo "[1/4] Running pg_dump to create backup..."
docker exec -i ${DB_CONTAINER} pg_dump -U ${DB_USER} -F c -d ${DB_NAME} > ${BACKUP_FILE}
echo "Backup created at ${BACKUP_FILE}"

echo "[2/4] Dropping and recreating the database to simulate data loss..."
# Terminate existing connections first
docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();"
docker exec -i ${DB_CONTAINER} dropdb -U ${DB_USER} ${DB_NAME} || echo "Drop DB failed, maybe it was already dropped?"
docker exec -i ${DB_CONTAINER} createdb -U ${DB_USER} ${DB_NAME}

echo "[3/4] Running pg_restore to restore backup..."
docker exec -i ${DB_CONTAINER} pg_restore -U ${DB_USER} -d ${DB_NAME} -1 < ${BACKUP_FILE} || true

echo "[4/4] Verifying restored state..."
MIGRATION_HEAD=$(docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT version_num FROM alembic_version LIMIT 1;" | xargs)
if [ -z "$MIGRATION_HEAD" ]; then
  echo "ERROR: Alembic migration head not found after restore."
  exit 1
fi
echo "Alembic Head successfully verified: ${MIGRATION_HEAD}"

echo "=== Backup & Restore Drill Completed Successfully ==="
