# ADR 0014 — Single SSRF-guarded EgressFetcher

## Decision
All non-browser egress uses one fetcher: scheme allowlist, DNS resolve, private/metadata IP block, no redirects, timeouts, size cap, per-host semaphore, ledger.

## Status
Accepted (Sprint 2)
