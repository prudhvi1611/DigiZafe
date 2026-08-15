# Discovery & Evidence (Sprint 4)

## Flow
1. Verify identifier (Sprint 2) — **required** (G1)
2. `POST /api/v1/scans` `{ "identifier_id": "..." }`
3. Worker runs connectors (XposedOrNot primary for email)
4. Observations (TTL) → Findings (durable, deduped)
5. SSE: `GET /api/v1/scans/{id}/events`
6. List findings: `GET /api/v1/findings?identifier_id=`

## State machine
- Scan: pending → running → completed | partial | failed | cancelled | timed_out
- Per-connector run: pending → running → succeeded | skipped | failed | timed_out
- Reconcile beat task self-heals stale/deadline scans

## 3-layer evidence
| Layer | Store | TTL |
|-------|-------|-----|
| raw | observations + evidence_blobs.layer=raw | EVIDENCE_RAW_TTL_HOURS (24h) |
| summary | evidence_blobs.layer=summary | EVIDENCE_SUMMARY_TTL_DAYS (30d) |
| durable | findings + evidence_blobs.layer=durable | no auto-TTL |

## G1
- Service: `require_verified`
- DB triggers on scans / observations / findings
- Unverified insert → `G1_VIOLATION`

## XposedOrNot
- Findings source=`xposedornot`, kind=`breach`
- Attribution in finding.attribution + scan.meta.attributions
- Consent + egress_ledger on every email send
