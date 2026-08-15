# Data Ownership and Retention Matrix

## Core Principles
1. **Tenant Isolation**: Row-Level Security (RLS) guarantees that cross-tenant access to `identity_orchestration_runs` and `candidate_provenance_observations` is impossible at the database engine level.
2. **Right to Erasure**: Hard deletions are supported via the `DELETE /api/v1/identity/anchors/{id}` cascade paths.
3. **Data Minimization**: PII is omitted from application logs, metrics, and telemetry.

## Matrix

| Data Entity | Owner | Retention Policy | Erasure Path |
|-------------|-------|------------------|--------------|
| `IdentityAnchor` | User | Indefinite until deleted | User-initiated cascade delete |
| `CandidateDiscoveryRun` | User | 90 days / User-initiated | Cascade delete via Anchor |
| `IdentityOrchestrationRun` | User | 90 days / User-initiated | Cascade delete via Anchor |
| `ResidualInferenceRecord` | System | 30 days (ephemeral) | Scheduled prune task |
| `ConnectorExecutionPlanItem` | User | Attached to Orchestration Run | Cascade delete |

## Audit Assertions
- No PII is logged in Datadog/Prometheus metrics.
- RLS ensures that `user_id = current_setting('rls.user_id')` is strictly enforced.
