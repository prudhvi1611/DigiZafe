# Runtime Components Inventory

## Celery Workers
| Worker / Task | Queue | Retry Policy | Idempotency |
|---|---|---|---|
| `tasks.discovery.run_connector_task` | default | 3 retries (exp backoff) | Yes. Upserts findings via normalizer. |
| `tasks.reconciliation.reconcile_stale_scans` | scheduled | None | Yes. Marks timeouts. |
| `tasks.retention.enforce_retention` | scheduled | None | Yes. Purges expired evidence. |

## External Dependencies
- PostgreSQL (Primary State)
- Redis Broker (Celery tasks)
- Redis Cache (Connector HTTP caching)

## Centralized Egress
All HTTP requests made to external discovery endpoints funnel strictly through `app.connectors.base.ConnectorBase.fetch()` or explicitly authorized isolated Playwright tasks. Direct usage of `requests`, `urllib`, or `httpx` in business logic is prohibited and was confirmed absent.
