# Deployment Runbook

This runbook outlines the standard procedure for deploying a new release of DigiZafe to the production environment.

## Prerequisites

1.  **Release Manifest:** Ensure a final release manifest exists for the target version (e.g., `docs/releases/final-release-manifest.md`).
2.  **Environment Variables:** Verify all required production environment variables are present in the target environment's `.env` file or secrets manager.
3.  **Container Registry Access:** Ensure the host has pull access to the container registry where the immutable application images are stored.

## 1. Prepare Environment

SSH into the target deployment host and navigate to the deployment directory.

```bash
cd /opt/digizafe
git pull origin main
git checkout <RELEASE_TAG>
```

Verify the `.env` file contains required secrets and settings. Do NOT commit the `.env` file to version control.

## 2. Pull Images

Pull the specific container image tags associated with this release. Avoid using `latest` for production.

```bash
docker compose pull
```

## 3. Run Migrations

Before restarting the application containers, apply any pending database migrations. 

```bash
# Temporarily start only the database (if not already running)
docker compose up -d postgres redis-broker redis-cache

# Run the alembic upgrade head command via a temporary API container
docker compose run --rm api alembic upgrade head
```

Verify that the migration completed successfully and there are no errors in the output.

## 4. Deploy Application

Restart the application stack to pick up the new images and code.

```bash
docker compose up -d
```

This will start/restart the `api`, `worker`, `remediation-worker`, `beat`, and `frontend` services in the correct dependency order.

## 5. Post-Deployment Verification

1.  **Check Container Status:**
    ```bash
    docker compose ps
    ```
    Ensure all containers are in the `Up (healthy)` state.

2.  **Check API Readiness:**
    ```bash
    curl -f https://<YOUR_DOMAIN>/api/v1/health/ready
    ```
    The response should indicate `status: ok`.

3.  **Smoke Test UI:** Navigate to the production URL in a browser, log in, and verify the dashboard loads without errors.

4.  **Verify Connectors:** Check the Connector Status Panel in the UI (or `/api/v1/connectors/certification`) to ensure connectors initialized properly.

## Rollback Procedure

If the deployment fails or causes critical errors, proceed immediately to the `rollback-runbook.md`.
