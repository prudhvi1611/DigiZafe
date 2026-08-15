# Feature Integration Matrix

| Capability | Sprint | Canonical module | API/UI entry point | Persistence | Tests | Runtime verified | Status | Notes |
|---|---:|---|---|---|---|---|---|---|
| Authentication & JWT | 2 | `app.services.auth_service` | `/api/v1/auth/*` | Users DB | Unit/E2E | Yes | VERIFIED | Argon2, MFA hooks present |
| Verified Identifiers | 2 | `app.services.verification_service` | `/api/v1/identifiers` | Identifiers DB | Unit | Yes | VERIFIED | Strict challenge/response flow |
| Consent/Privacy | 8 | `app.services.consent_service` | `Privacy Center` | Consent DB | Unit | Yes | VERIFIED | Gatekeeper for Egress |
| Scan Orchestration | 3 | `app.services.discovery_service` | `/api/v1/scans` | Scans DB | Unit/Int | Yes | VERIFIED | Async worker processing |
| Connectors (Surface) | 4 | `app.connectors.impl.surface` | Scans Pipeline | Cache | Unit | Yes | VERIFIED | XposedOrNot, Gravatar, SERP |
| Connectors (Deep Amber) | 11 | `app.connectors.impl.deep` | Scans Pipeline | Cache | Unit | Yes | VERIFIED | CommonCrawl, Wayback |
| Findings Normalization | 5 | `app.services.findings_service` | UI Findings | Findings DB | Unit | Yes | VERIFIED | Canonicalization |
| Identity Graph | 6 | `app.services.identity_graph` | UI Graph | Identity DB | Unit | Yes | VERIFIED | Foundational Anchor |
| PDSS Scoring | 7 | `app.services.score_service` | UI PDSS | Score DB | Unit | Yes | VERIFIED | Deterministic Confirmed/Possible |
| Remediation & Recommendations | 9, 10 | `app.services.remediation_service` | UI Remediation | Remediation DB | Unit | Yes | VERIFIED | User-directed |
| Egress Bounds | 2, 13 | `app.security.egress` | Base Connector | N/A | Unit | Yes | VERIFIED | 5MB response cap |
| Residual ML | 12 | `app.ml.residual_model` | Background | N/A | None | N/A | OPTIONAL_DISABLED | Fail-safe |
