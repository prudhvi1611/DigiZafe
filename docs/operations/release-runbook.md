# Release Runbook

## Pre-Release Validation (Release Candidate Gate)
Before deploying a new version to production, run the Release Candidate script to ensure all validations pass:
```bash
./scripts/release-candidate.sh
```

This script will:
1. Run backend linting and static type checking.
2. Verify Alembic migrations.
3. Run backend unit and integration tests.
4. Verify the frontend production build.
5. Build immutable API and Worker container images.

## Smoke Testing
Run the E2E smoke test against the built images before swapping traffic:
```bash
python scripts/smoke_test.py
```

## Deployment
1. Pull or deploy the new immutable images: `docker compose pull api worker`
2. Run database migrations: `docker compose run --rm api alembic upgrade head`
3. Restart the services: `docker compose up -d api worker`
4. Monitor `/metrics` for unexpected latency spikes or error rates.
