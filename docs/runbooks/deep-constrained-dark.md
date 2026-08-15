# Deep + Constrained-Dark Amber Runbook

## Purpose

Sprint 11 adds optional Amber discovery layers without changing the DigiZafe
modular-monolith architecture.

## Layers

| Layer | Default | Consent | Examples |
|---|---:|---:|---|
| surface | enabled | normal connector consent | XposedOrNot, crt.sh, RDAP, GitHub |
| deep | enabled | explicit `discovery.deep` | Common Crawl metadata, Wayback availability |
| constrained_dark | disabled | explicit `discovery.constrained_dark` | operator-approved public index metadata |

## Deep scan flow

1. User owns and verifies an identifier.
2. User opens the scan layer selector.
3. User selects `Deep`.
4. User grants `discovery.deep` consent.
5. User starts the scan.
6. Worker runs only Deep connectors.
7. Results are tagged `layer=deep`.
8. Findings are normalized as `archived_metadata`.
9. PDSS applies the Deep layer multiplier.
10. UI states that historical/index metadata does not prove current exposure.

## Constrained-Dark configuration

Constrained-Dark is disabled by default.

Required environment variables:

