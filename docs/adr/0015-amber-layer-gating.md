# ADR 0015 — Deep and Constrained-Dark Amber Layer Gating

## Status

Accepted — Sprint 11

## Context

DigiZafe must expand beyond Surface discovery while preserving:

- self-only ownership verification;
- free-first operation;
- explicit provenance;
- no unrestricted dark-web crawling;
- no raw dumps;
- no paid hard dependency;
- honest limitations.

## Decision

Amber discovery is implemented as a layer-scoped scan:

- `surface`
- `deep`
- `constrained_dark`

Each Amber layer:

1. Requires explicit user consent.
2. Uses only connectors whose declared capability matches the scan layer.
3. Runs through the existing Connector SDK.
4. Uses `EgressFetcher` for all external HTTP.
5. Uses cache and rate limits.
6. Persists metadata-only observations.
7. Preserves source attribution.
8. Marks findings as `possible` unless stronger evidence exists.
9. Exposes limitations in API and frontend copy.

## Deep connectors

- Common Crawl URL-index metadata.
- Internet Archive Wayback availability metadata.

## Constrained-Dark connector

A configurable operator-approved public JSON index adapter is included but
disabled by default. It requires an HTTPS endpoint and explicit host allowlist.

## Rejected

- Direct Tor access.
- `.onion` crawling.
- Credentialed marketplaces.
- Raw dump retrieval.
- Unrestricted third-party search.
- Paid threat feeds as a core dependency.

## Consequences

Amber coverage is narrower than commercial threat intelligence products, but
the behavior is safer, explainable, free-first, and aligned with the frozen
DigiZafe architecture.
