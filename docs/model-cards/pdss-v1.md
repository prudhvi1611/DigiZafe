# Model Card — PDSS v1.1.0

**Status:** Accepted (Sprint 12)  
**Type:** Hybrid deterministic exposure score (CVSS-inspired metric groups + surprisal)  
**Tracks:** Confirmed / Possible  
**Training data:** None (rules + catalogs)  
**Version:** pdss-v1.1.0  
**Catalog:** `shared/score_model/pdss_catalog.json`

## Intended use
Score an individual's **verified** digital exposure from DigiZafe findings (surface free path, XposedOrNot primary breaches, etc.) with full explainability.

## Metrics (vector groups)
| Code | Name | Role |
|------|------|------|
| S | Sensitivity | How sensitive exposed data types are |
| D | Discoverability | How easily found on public surface |
| L | Linkability | Cross-identifier / cross-source link risk |
| I | Impact | Harm potential (password plaintext, financial, etc.) |
| T | Temporal | Recency + reuse over time |
| E | Environmental | Identifier criticality, layer, identity-graph density |
| U | Surprisal | Non-saturating information-style contribution |
| R | Reuse | Same breach/ref across sources |

**Combined score:** 0.0–10.0 with severity bands (none/low/medium/high/critical).  
**Vector string example:** `PDSS:pdss-v1.1.0/S:0.72/D:1.00/L:0.08/I:0.65/T:0.81/E:1.04/U:1.20/R:0.08/SC:6.4/SV:medium`

## Two-track
- **Confirmed:** high-confidence breaches/exposures (e.g. XposedOrNot breach list confidence ≥ threshold in normalize)
- **Possible:** SERP/username presence/lower confidence  
Possible track weighted (~0.55) in combined score.

## XposedOrNot drivers
Uses finding attributes when present: `breach_name`, `xposed_data`, `password_risk`, `risk_label`, `xposed_date`, `xposed_records`. Attribution preserved on score snapshot.

## Explainability (G3)
Every compute persists:
- `score_snapshots` with contributions + counterfactuals
- `explanation_records` (summary, per-contribution drivers, counterfactual narratives)

## Out of scope
Opaque black-box ML as sole score; third-party scanning; paid API dependence.

## Limitations
- Deterministic catalogs may under/over-weight rare breach types.
- Recency uses year when only year available.
- Aggregate whole-user score uses default identifier criticality when identifier_id is null.

## Change control
Bump `model_version` + update this model card; never silent formula changes in production.

## Layer Handling (Pre-Sprint 12 Consolidation)

PDSS preserves the finding layer:

- `surface`
- `deep`
- `constrained_dark`

The catalog sets all layer multipliers to `1.0`. The exposure layer serves as provenance and context, and must not automatically increase the severity or PDSS score.

Amber findings are normally placed on the Possible track because:

- archived metadata may be stale;
- URL-index presence does not prove page content;
- a public-index result does not prove current exposure;
- connector coverage is incomplete.

Amber findings must preserve:

- source;
- layer;
- attribution;
- metadata-only status;
- current-exposure uncertainty.

The score must not describe historical or indexed metadata as a confirmed
current breach without an independent confirmed finding.

