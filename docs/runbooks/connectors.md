# Connectors Runbook (Sprint 3)

## Probe a verified email
1. Login → add email → verify (Sprint 2)
2. `GET /api/v1/connectors` — catalog
3. `POST /api/v1/connectors/probe/{identifier_id}`  
   Body optional: `{"connector_ids":["xposedornot","gravatar"]}`
4. UI must show XposedOrNot attribution when their data appears

## Rate limits
If skip_reason=rate_limited — surface honestly; rely on cache; do not spin.

## Admin disable
Superuser: `PATCH /api/v1/connectors/xposedornot` `{"enabled":false}`
