# Backup and Restore Runbook

This runbook outlines the procedures for safely backing up and restoring the DigiZafe PostgreSQL database. It is intended for operational and disaster-recovery purposes.

## 1. Safety Principles

*   **Never** restore a disposable or staging backup into the production database.
*   **Always** verify the environment variables before running any `pg_restore` command. The script must require explicit acknowledgement to prevent accidental overwrites.
*   Never hardcode credentials in scripts. Always inject them via the environment.
*   The backup process only covers PostgreSQL. Redis is used as a broker and cache and its state is considered ephemeral (except for queues, which should ideally drain before a planned backup).

## 2. Backup Procedure

To perform a logical backup of the database, use `pg_dump`:

```bash
#!/bin/bash
set -e

# Load environment configuration (e.g., from .env)
# Must define: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
source .env

BACKUP_FILE="digizafe_backup_$(date +%F_%H-%M-%S).sql"

echo "Creating backup of database: $POSTGRES_DB"
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f "$BACKUP_FILE"

echo "Backup created successfully: $BACKUP_FILE"
```

*For Docker environments:*
```bash
docker exec -t digizafe-postgres-1 pg_dump -U digizafe -d digizafe -F c -f /tmp/backup.dump
docker cp digizafe-postgres-1:/tmp/backup.dump ./digizafe_backup_$(date +%F).dump
```

## 3. Restore Procedure

To restore the backup into a target database, use `pg_restore`. 

> [!WARNING]
> **Data Loss Risk:** The following commands will drop the existing database and restore from the backup. Ensure you are operating on the correct environment (e.g., staging or disaster recovery instance).

```bash
#!/bin/bash
set -e

source .env
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "TARGET DATABASE: $POSTGRES_DB at $POSTGRES_HOST"
read -p "Are you absolutely sure you want to overwrite this database? (y/N) " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "Restoring database from $BACKUP_FILE..."

# Terminate existing connections and recreate database (requires superuser or createdb privilege on a maintenance db)
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB';"
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

# Restore the dump
PGPASSWORD=$POSTGRES_PASSWORD pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -1 "$BACKUP_FILE"

echo "Restore complete."
```

*For Docker environments:*
```bash
docker cp ./backup.dump digizafe-postgres-1:/tmp/backup.dump
docker exec -i digizafe-postgres-1 psql -U digizafe -d postgres -c "DROP DATABASE IF EXISTS digizafe WITH (FORCE);"
docker exec -i digizafe-postgres-1 psql -U digizafe -d postgres -c "CREATE DATABASE digizafe;"
docker exec -i digizafe-postgres-1 pg_restore -U digizafe -d digizafe -1 /tmp/backup.dump
```

## 4. Verification

After restoring, verify the following:
1.  **Migration State:** Run `alembic current` inside the API container to ensure the database head matches the application expectation.
2.  **Row-Level Security:** Execute a query as an application user to confirm RLS policies are actively enforcing data boundaries.
3.  **Application Health:** Check the `/api/v1/health` endpoints to verify all components (PostgreSQL, Redis, Celery) are connected and healthy.
