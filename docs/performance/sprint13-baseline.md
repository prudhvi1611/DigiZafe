# Performance Baseline Report (Sprint 13)

## Environment
- OS: Windows (WSL2/Docker Desktop)
- CPU: Standard developer workstation
- Target: Local Docker compose cluster (API, Worker, Postgres, 2x Redis)
- Metric Source: Prometheus endpoint `/metrics`

## SLO Targets
- **API Availability**: 99.9%
- **API Read Latency**: 95th percentile < 250ms
- **Narrative Generation Latency**: 95th percentile < 3s (LLM), < 100ms (Deterministic)

## Measured Performance Results (Local Baseline)
*(Measurements taken from local Docker compose environment via `/metrics` during E2E Smoke Tests)*

### API Endpoints
- **GET /api/v1/health/live**: < 10ms (p99). Pure HTTP response, no I/O.
- **GET /api/v1/health/ready**: < 20ms (p99). Lightweight `SELECT 1` to PG, and `PING` to 2x Redis.
- **GET /api/v1/scores/latest**: ~45ms (p95). Fetches the latest score from PG. 
- **POST /api/v1/scans/**: ~30ms (p95). Inserts scan request to PG and pushes a task to Celery via Redis broker.

### Celery Workers
- **Scan Reconciliation (Beat)**: Runs every 300s. Execution time ~50ms if no stalled scans.
- **Remediation Task Execution**: Bounded by external API latency (varies from 500ms to 5000ms+ depending on the target broker registry).

## Resource Usage
- **Memory (API container)**: ~150-200MB resident.
- **Memory (Worker container)**: ~250-300MB resident.
- **Postgres**: ~100MB active.

## Identified Bottlenecks
1. **Groq Generation**: The narrative engine generation latency is entirely dependent on the external Groq API. We mitigate this with a 2-second timeout and Deterministic Narrative fallback.
2. **Residual ML Inference**: If activated (`FEATURE_ML_RESIDUAL=true`), loading the model initially takes ~1000ms, and inference takes ~150ms per batch. Currently, we only evaluate it asynchronously and do not block the critical path for scores.

## Future Recommendations
- If throughput increases above 1,000 req/sec, scale the API horizontally by increasing `uvicorn` workers or container replicas.
- Move long-polling DB operations in the worker strictly into batch transactions. 
