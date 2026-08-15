# Sprint 25 Performance Baseline

## Environment
- **Hardware**: Local Integration Environment (Docker Desktop on Windows/WSL)
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Concurrency Level**: 10 simultaneous connections

## Benchmark Results (50 requests per endpoint)

| Endpoint                 | p50 Latency (ms) | p95 Latency (ms) | Error Rate | Notes |
|--------------------------|------------------|------------------|------------|-------|
| `GET /api/v1/health`     | 1746.1           | 1933.6           | 0%         | Live healthcheck |
| `GET /api/v1/identity/anchors` | 479.0 | 551.9 | 100% | Auth middleware rejection (401) |

## Soak Testing & Backpressure
- **Bounded Lease Concurrency**: Verified that when Redis lease concurrency limits are hit, new requests are gracefully deferred or rejected according to `concurrency:connector_name:uuid` atomic leases.
- **Worker Recovery**: Tested terminating the celery worker mid-execution; leases expired properly without permanent lock leakage.

*Disclaimer: These are local benchmark results run against a disposable integration container stack. They DO NOT represent universal production capacity or cloud performance.*
