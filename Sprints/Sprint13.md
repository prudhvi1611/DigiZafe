# DigiZafe --- Sprint 13 Implementation Guide

**Sprint:** 13 --- Production Readiness, Observability, Reliability &
Release Hardening\
**Document version:** 1.0\
**Applies after:** Sprint 12 --- Optional Free Residual ML\
**Prerequisite:** Pre-Sprint 12 hardening gate complete; Sprint 12
Definition of Done complete\
**Primary goal:** Turn the completed Sprint 0--12 system into a
measurable, recoverable, operationally safe release candidate without
changing DigiZafe's core product architecture.

> Sprint 13 is a production-readiness sprint, not a feature-expansion
> sprint.
>
> The deterministic DigiZafe workflow remains authoritative:
> `Verify → Consent → Discover → Explain → Score → Prioritize → Remediate → Re-verify → Re-score`
>
> Residual ML remains optional, bounded, auxiliary, and disabled by
> default unless its evaluation and rollout gates explicitly approve
> otherwise.

------------------------------------------------------------------------

# 1. Sprint Goal

Sprint 13 hardens DigiZafe for reliable deployment and operation by
adding production-safe configuration validation, structured logs and
correlation IDs, metrics, health/readiness checks, worker and connector
observability, safe error handling, backup/restore validation,
disaster-recovery procedures, deployment/rollback runbooks, container
and dependency hardening, performance baselines, retention verification,
and release-candidate acceptance tests.

Sprint 13 does not redesign the architecture or introduce new discovery
sources.

------------------------------------------------------------------------

# 2. Non-Negotiable Constraints

Preserve all Sprint 0--12 invariants:

-   G1 self-only scanning and verified identifiers only.
-   Explicit consent before consent-gated egress.
-   Centralized `EgressFetcher`.
-   No unrestricted dark-web crawling or raw breach-dump storage.
-   Deterministic PDSS remains authoritative.
-   Residual ML remains optional and auxiliary.
-   Groq is used only for the approved grounded narrative path.
-   Deterministic narrative fallback remains available.
-   User-directed remediation remains authoritative.
-   RLS and per-user isolation remain enforced.
-   Evidence TTL and privacy deletion policies remain intact.
-   No secrets in logs, metrics, traces, frontend bundles, or API
    responses.

------------------------------------------------------------------------

# 3. Scope

## Included

-   startup configuration validation;
-   environment separation;
-   structured logging and correlation IDs;
-   metrics and health/readiness checks;
-   worker/queue and connector observability;
-   scan SLOs and operational thresholds;
-   safe error taxonomy;
-   backup, restore, and disaster-recovery validation;
-   graceful shutdown;
-   deployment and rollback documentation;
-   container and dependency hardening;
-   load/soak testing and performance baselines;
-   data-retention verification;
-   release-candidate acceptance tests;
-   optional residual ML operational monitoring;
-   Groq narrative monitoring without exposing prompt content or
    secrets.

## Excluded

-   new discovery connectors or broker automation;
-   new PDSS scoring semantics;
-   new ML architecture or online retraining;
-   replacing deterministic PDSS;
-   unrestricted third-party telemetry;
-   mandatory paid observability;
-   microservice decomposition.

------------------------------------------------------------------------

# 4. Mandatory Repository Preflight

Before adding modules, search for existing logging middleware,
correlation-ID support, health endpoints, metrics dependencies, Celery
monitoring, deployment scripts, CI workflows, backup/restore
documentation, error DTOs, and retention jobs. Reuse canonical settings
and domain contracts. Do not create parallel observability or
error-handling systems.

------------------------------------------------------------------------

# 5. Production Configuration Validation

Add or extend:

`backend/app/core/startup_validation.py`

Validate at startup:

-   environment and debug mode;
-   JWT/signing configuration;
-   PostgreSQL and Redis configuration;
-   CORS and trusted hosts;
-   Groq configuration when enabled;
-   Amber and constrained-dark configuration;
-   residual ML registry/checksum/schema when enabled;
-   evidence TTLs;
-   maximum egress response size.

Required production rules include:

``` text
APP_ENV=production → DEBUG=false

FEATURE_CONSTRAINED_DARK=true
→ endpoint configured
→ allowlist configured
→ destination passes policy

FEATURE_RESIDUAL_ML=true
→ trusted model metadata exists
→ checksum matches
→ feature schema is compatible

Groq narrative enabled
→ API key exists server-side
→ API key is never returned or logged
```

Unsafe production configuration must fail closed without printing secret
values.

------------------------------------------------------------------------

# 6. Structured Logging and Correlation

Use structured JSON-compatible logs in production. Support safe fields
such as timestamp, level, service, environment, event, request ID,
correlation ID, scan ID, connector-run ID, remediation-job ID, model
version, duration, and status.

Never log passwords, access/refresh tokens, authorization headers, MFA
secrets, verification tokens, Groq API keys, raw evidence bodies, raw
breach data, or unnecessary direct identifiers.

Propagate correlation context across:

``` text
HTTP request
→ scan
→ Celery task
→ connector run
→ egress event
→ finding normalization
→ scoring
→ recommendation/remediation
```

------------------------------------------------------------------------

# 7. Error Taxonomy

Consolidate stable error codes:

``` text
validation_error
authentication_error
authorization_error
verification_required
consent_required
rate_limited
connector_unavailable
egress_blocked
dependency_unavailable
scan_conflict
resource_not_found
model_unavailable
internal_error
```

Recommended API shape:

``` json
{
  "error": {
    "code": "verification_required",
    "message": "A verified identifier is required for this operation.",
    "request_id": "..."
  }
}
```

Never expose stack traces, SQL, filesystem paths, secret configuration,
upstream credentials, or sensitive raw provider responses.

------------------------------------------------------------------------

# 8. Health and Readiness

Provide:

``` text
GET /health/live
GET /health/ready
```

Liveness checks whether the process is alive. Readiness checks required
dependencies such as PostgreSQL, required Redis roles, migration
compatibility, and critical configuration.

Optional Groq, Common Crawl, Wayback, and residual ML outages must be
reported as degraded/optional and must not make the core API unready
unless explicitly configured as required.

------------------------------------------------------------------------

# 9. Metrics

Use a free/open standard, preferably Prometheus-compatible metrics, with
low-cardinality labels only.

Track:

``` text
HTTP request count/latency/status
scans started/completed/failed/duration
active scans
connector runs/failures/duration/cache hits/rate limits
egress blocked count
remediation jobs/failures/verification
narrative requests/provider failures/fallbacks/duration
residual ML evaluations/abstentions/unavailable/duration when enabled
```

Never use raw user IDs, identifiers, URLs, prompts, responses, or
feature vectors as metric labels.

------------------------------------------------------------------------

# 10. Operational SLOs

Create `docs/operations/slo.md`.

Measure initial internal SLOs for API availability, scan completion,
scan duration, connector failure rate, queue age, remediation failures,
and narrative fallback rate. Base thresholds on measured data rather
than unsupported promises.

------------------------------------------------------------------------

# 11. Celery and Worker Reliability

Validate task acknowledgements, retries, idempotency, duplicate
delivery, worker shutdown, stale task recovery, scan reconciliation, and
queue separation.

Retryable tasks must not duplicate durable side effects. PostgreSQL
remains authoritative; Celery result state is not the canonical scan
state.

Recommended idempotency dimensions:

``` text
scan_id + connector_id + attempt policy
remediation_job_id + action version
score_snapshot_id + model version
```

------------------------------------------------------------------------

# 12. Graceful Shutdown

On API or worker shutdown, stop accepting new work where appropriate,
preserve recoverable durable state, avoid marking unfinished work
successful, and allow reconciliation to recover stale operations.

Test termination during connector execution, scoring, remediation, and
residual ML evaluation.

------------------------------------------------------------------------

# 13. Connector Reliability

Verify connector timeouts, bounded retries, retryable/non-retryable
errors, caching, rate-limit handling, source attribution, partial scan
completion, and connector-specific failure isolation.

One connector failure must not automatically fail an entire scan when
partial completion is allowed. Amber connectors remain fail-closed when
policy or consent denies execution.

------------------------------------------------------------------------

# 14. Backup and Restore

Create `docs/operations/backup-restore.md`.

Back up durable PostgreSQL data and required trusted model
artifacts/registry metadata when residual ML is enabled. Redis cache is
not authoritative backup data.

Perform a documented restore test:

``` text
create isolated test data
→ backup
→ destroy isolated test database
→ restore
→ migrate if required
→ verify user isolation
→ verify scans/findings/scores/audit history
```

Secrets must be restored through the deployment secret-management
process, not embedded in backups.

------------------------------------------------------------------------

# 15. Disaster Recovery

Create `docs/operations/disaster-recovery.md`.

Document recovery for database loss, Redis loss, worker loss, API
restart, corrupted optional ML artifacts, Groq outage, connector outage,
and accidental Amber configuration problems.

Expected fail-safe behavior:

``` text
Groq outage → deterministic narrative fallback
ML corruption → ML unavailable/abstained; PDSS unaffected
Redis cache loss → cache rebuilds; durable PostgreSQL state preserved
connector outage → isolated failure and reconciliation/partial-result policy
```

------------------------------------------------------------------------

# 16. Data Retention Verification

Add automated tests or scheduled checks for raw evidence TTL, summary
evidence TTL, cache TTL, expired verification challenges, token-record
retention, stale connector runs, remediation artifacts, and user
deletion/crypto-shred behavior.

Retention jobs must be idempotent, observable, retry-safe, and must
never log deleted sensitive payloads.

------------------------------------------------------------------------

# 17. API and Frontend Security Hardening

Verify trusted hosts, production CORS allowlists, HTTPS assumptions,
proxy headers, content-type validation, request-size limits, and rate
limits for sensitive endpoints.

Review frontend security headers and Content Security Policy. Do not use
wildcard credentialed CORS in production.

------------------------------------------------------------------------

# 18. Container Hardening

Review Dockerfiles and production Compose configuration.

Required goals:

-   non-root runtime where practical;
-   minimal runtime dependencies;
-   no development server in production;
-   no secrets baked into images;
-   deterministic dependency installation;
-   health checks;
-   explicitly scoped writable directories;
-   Playwright worker isolated from the API process.

------------------------------------------------------------------------

# 19. Dependency and Supply-Chain Review

Review Python dependencies, Node dependencies, container base images,
and CI action pinning. Remove unused packages and resolve reachable
high-severity vulnerabilities or document them as release blockers.

Do not blindly perform unrelated major-version upgrades during this
sprint.

------------------------------------------------------------------------

# 20. Performance Baseline

Create `docs/performance/sprint13-baseline.md`.

Measure representative flows including login, identifier listing, scan
creation, scan status/SSE, score retrieval, recommendation retrieval,
and privacy export initiation.

Use controlled mocks for external connectors. Do not load-test
third-party public services without permission.

Record p50, p95, p99 where statistically meaningful, error rate,
database behavior, and worker queue age.

------------------------------------------------------------------------

# 21. Load and Soak Tests

Add a reproducible harness for concurrent authenticated reads, scan
creation within configured limits, worker queue behavior, SSE lifecycle,
repeated deterministic scoring, and controlled optional residual ML
evaluation.

Use synthetic/test data only.

------------------------------------------------------------------------

# 22. Database Query Review

Review high-frequency paths for N+1 queries, missing indexes, unbounded
list endpoints, oversized JSON payloads, and unnecessary evidence
loading. Add pagination where required without weakening RLS or user
isolation.

------------------------------------------------------------------------

# 23. Release Configuration Profiles

Define explicit development, test, and production profiles.

Recommended production defaults:

``` text
DEBUG=false
FEATURE_CONSTRAINED_DARK=false
FEATURE_RESIDUAL_ML=false
deterministic narrative fallback enabled
Groq optional and server-side only
```

Never silently enable experimental features merely because a model
artifact or API key exists.

------------------------------------------------------------------------

# 24. Groq Operational Boundary

Groq remains an optional narrative provider:

``` text
Groq configured and authorized
→ grounded request
→ validate response
→ narrative

timeout / 429 / 5xx / invalid response
→ deterministic grounded fallback
```

Monitor request count, latency, failure class, and fallback count. Never
log API keys, raw sensitive prompts, or unnecessary provider responses.
Application readiness must not depend on Groq.

------------------------------------------------------------------------

# 25. Residual ML Operational Boundary

Residual ML remains optional, local, bounded, auxiliary, and disabled by
default.

Production readiness requires trusted artifacts, checksum verification
before deserialization, schema compatibility, model versioning, safe
abstention, no user-controlled model path, and no network dependency.

If Sprint 12 evaluation concluded NO-GO, preserve
`FEATURE_RESIDUAL_ML=false`. Technical pipeline success alone is not
approval to enable the model.

------------------------------------------------------------------------

# 26. Release Candidate CI Gate

Require:

``` text
backend lint/static checks
backend unit tests
backend integration tests
security tests
migration tests
frontend typecheck/tests/production build
contract/OpenAPI drift tests
Sprint 0–12 regression suite
```

Long-running tests may use a dedicated release workflow, but release
must require their successful result.

------------------------------------------------------------------------

# 27. Migration Release Gate

Before release:

``` bash
alembic heads
alembic upgrade head
```

Validate the expected single head, fresh install, supported historical
upgrade, startup validation after migration, RLS, and database
invariants. Document rollback/forward-fix strategy.

------------------------------------------------------------------------

# 28. Release and Rollback Runbooks

Create:

``` text
docs/operations/release-runbook.md
docs/operations/rollback-runbook.md
```

Release flow:

``` text
1. Verify CI
2. Verify backup
3. Verify migration head
4. Build immutable images
5. Apply migration
6. Deploy API/workers/frontend
7. Run readiness checks
8. Run smoke tests
9. Monitor errors/queues/scans
10. Mark release complete
```

Rollback must distinguish application rollback, database
forward-fix/rollback, feature-flag disable, connector disable, Groq
disable, and residual ML disable.

------------------------------------------------------------------------

# 29. Smoke Test and Release Journey

Create a release smoke test for health, login, verified identifier read,
safe scan creation, scan status, score retrieval, recommendations, and
privacy/audit endpoints.

Also validate the complete release-candidate journey:

``` text
register/login
→ verification required
→ verify ownership
→ Surface scan
→ findings/provenance
→ deterministic PDSS
→ explanation
→ recommendations
→ remediation
→ re-verification/re-score
→ privacy export/audit
```

Negative/fallback checks:

``` text
Deep without consent → blocked with zero egress
Constrained-Dark disabled → zero connector execution
Groq unavailable → deterministic narrative
Residual ML disabled → core product unchanged
```

------------------------------------------------------------------------

# 30. Incident Response

Create `docs/operations/incident-response.md`.

Cover security/privacy incidents, database outage, queue/worker outage,
connector abuse/rate-limit incidents, Groq/provider incidents, Amber
destination misconfiguration, and residual ML artifact issues.

Process:

``` text
detect
→ contain
→ disable optional feature if relevant
→ preserve audit evidence
→ recover
→ verify
→ document
```

------------------------------------------------------------------------

# 31. Required Tests

## Configuration

-   production with debug enabled fails startup;
-   unsafe constrained-dark configuration fails closed;
-   enabled residual ML with invalid trusted artifact becomes
    unavailable/fails according to approved policy.

## Logging

-   request IDs exist;
-   correlation propagates;
-   tokens/secrets are absent from captured logs.

## Health

-   optional provider outage does not fail liveness/readiness;
-   required database outage fails readiness.

## Reliability

-   retries do not duplicate durable side effects;
-   stale reconciliation is idempotent;
-   graceful shutdown preserves recoverable state.

## Privacy

-   purge is idempotent;
-   expired raw evidence is removed;
-   durable provenance remains according to policy;
-   user deletion still works.

## Release

-   fresh migration;
-   supported upgrade;
-   frontend production build;
-   OpenAPI/contract test;
-   full regression suite.

------------------------------------------------------------------------

# 32. Suggested Commit Plan

``` bash
git commit -m "feat(ops): add production startup configuration validation"
git commit -m "feat(obs): add structured logging and correlation ids"
git commit -m "feat(obs): add health readiness and operational metrics"
git commit -m "fix(workers): harden retries idempotency and graceful shutdown"
git commit -m "test(retention): verify evidence and privacy lifecycle policies"
git commit -m "test(perf): add controlled performance and load baselines"
git commit -m "docs(ops): add backup recovery release rollback and incident runbooks"
git commit -m "ci(release): add sprint 0-12 release candidate quality gates"
```

------------------------------------------------------------------------

# 33. Sprint 13 Definition of Done

## Configuration

-   [ ] Production startup validation exists.
-   [ ] Unsafe settings fail closed.
-   [ ] Secrets are never printed.
-   [ ] Experimental features remain disabled by default.

## Observability

-   [ ] Structured logs and correlation IDs exist.
-   [ ] Metrics use low-cardinality labels.
-   [ ] Liveness and readiness are distinct.
-   [ ] Optional Groq/ML outages do not make the core API unready.

## Reliability

-   [ ] Worker retry/idempotency is tested.
-   [ ] Graceful shutdown is tested.
-   [ ] Reconciliation remains authoritative and idempotent.
-   [ ] Connector failures are isolated according to policy.

## Security and privacy

-   [ ] No secrets appear in logs or metrics.
-   [ ] Egress security tests remain green.
-   [ ] Verified-only and consent zero-egress tests remain green.
-   [ ] Retention/purge tests are green.
-   [ ] RLS and user-isolation tests are green.
-   [ ] Dependency/security review is complete.

## Recovery

-   [ ] Backup procedure is documented.
-   [ ] Restore is tested in isolation.
-   [ ] Disaster-recovery behavior is documented.
-   [ ] Redis loss does not imply durable-data loss.

## Performance

-   [ ] Performance baseline exists.
-   [ ] Controlled load tests pass for the selected deployment target.
-   [ ] No critical unbounded endpoint or N+1 issue remains.

## Release

-   [ ] Fresh migration succeeds.
-   [ ] Supported upgrade succeeds.
-   [ ] Expected Alembic head is verified.
-   [ ] Frontend production build succeeds.
-   [ ] Backend, security, and Sprint 0--12 regression suites pass.
-   [ ] Release and rollback runbooks exist.
-   [ ] Release smoke test succeeds.

## Product invariants

-   [ ] Deterministic PDSS remains authoritative.
-   [ ] Residual ML remains optional and bounded.
-   [ ] Groq remains narrative-only.
-   [ ] Deterministic narrative fallback works.
-   [ ] Constrained-Dark remains disabled by default.
-   [ ] User-directed remediation remains authoritative.

------------------------------------------------------------------------

# 34. Sprint Completion Rule

Sprint 13 is complete when DigiZafe has a reproducible release-candidate
process and can demonstrate:

``` text
safe startup
+ observable operation
+ recoverable failures
+ tested backups
+ controlled deployment
+ controlled rollback
+ privacy retention enforcement
+ full Sprint 0–12 regression safety
```

This does not mean production can never experience bugs or outages. It
means the system has defined controls to detect, contain, diagnose,
recover from, and safely roll back operational failures.

------------------------------------------------------------------------

# 35. Final Architecture After Sprint 13

``` text
User
  ↓
Authentication + verified identity
  ↓
Consent
  ↓
Controlled discovery
  ↓
Evidence + provenance
  ↓
Confirmed / Possible tracks
  ↓
Deterministic PDSS
  ↓
Explainable recommendations
  ↓
User-directed remediation
  ↓
Re-verification and re-scoring
  ↓
Optional bounded residual ML
  ↓
Grounded narrative
    ├─ Groq when configured and authorized
    └─ deterministic fallback
  ↓
Production operations layer
    ├─ configuration validation
    ├─ structured logs
    ├─ metrics
    ├─ health/readiness
    ├─ backup/restore
    ├─ incident response
    └─ release/rollback controls
```

**Next recommended phase after Sprint 13:** controlled release-candidate
validation, user acceptance testing, and research evaluation. Do not
automatically add another feature sprint until operational evidence
identifies the next priority.

**End of Sprint 13 Implementation Guide.**
