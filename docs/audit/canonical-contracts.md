# Canonical Contracts Inventory

| Concept | Canonical Python Module | Persistence Representation | API Representation | Notes |
|---|---|---|---|---|
| `IdentifierType` | `app.domain.identifiers` | `identifiers.type` | `type: "email"` | Only email supported currently |
| `ExposureLayer` | `app.domain.exposure` | `scans.layer_scope` | `layer_scope: "surface"` | `deep`, `constrained_dark` are optional |
| Finding Kind/Type | `app.schemas.scan.FindingPublic` | `findings.category` | `category` / `title` | Canonicalized by `FindingsService` |
| Scan Status | `app.domain.scan_states` | `scans.status` | `status: "pending" | "completed"` | Async driven |
| Connector-Run Status | `app.domain.scan_states` | `connector_runs.status` | `status: "completed"` | Maps directly to Scan Status |
| Consent State | `app.models.consent.ConsentGrant` | `consent_grants` | N/A (Internal checks) | Handled by `ConsentService` |
| Verification State | `app.models.identifier.Identifier` | `identifiers.is_verified` | `is_verified: boolean` | Authoritative |
| PDSS Score DTO | `app.schemas.score.ScorePublic` | `scores.score` | `ScorePublic` | Includes Confidence & History |
| Recommendations | `app.models.remediation.Remediation` | `remediation_records` | `RemediationPublic` | Dependent on Score |
| User Isolation | `app.api.deps.CurrentUser` | RLS (`user_id`) | Central middleware | Applied across all API scopes |
