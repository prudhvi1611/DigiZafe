# Sprint 25 — Final Production Release Certification, Migration Integrity, CI/CD, Performance & Operational Handover

## Status
- **Sprint:** 25
- **Role:** Final planned sprint for the current DigiZafe roadmap
- **Baseline:** Sprint 24 integration certification
- **Reported verification:** 101/101 backend tests passed against Docker-hosted PostgreSQL, Redis, and Celery
- **Primary objective:** convert the Sprint 24 release candidate into a reproducible, immutable, deployable, performance-characterized, security-regressed, operationally documented final release.

# 1. Mission

Sprint 24 proved that DigiZafe works against real infrastructure. Sprint 25 must prove that it can be built reproducibly, migrated safely, tested automatically, deployed predictably, observed, recovered, upgraded, and handed over with truthful limitations.

This sprint must not add major new OSINT capabilities. It focuses on:
1. migration integrity;
2. CI/CD enforcement;
3. release reproducibility;
4. performance and capacity characterization;
5. resilience testing;
6. final security and privacy regression;
7. connector runtime truthfulness;
8. operational runbooks;
9. final release artifacts;
10. final system acceptance.

# 2. Critical Preflight — Historical Migration Integrity

Sprint 24 reports that historical migration `11cf1eaeb4ad` was patched to enable and force RLS on `identity_orchestration_runs`.

Before final release, determine whether that migration has ever been applied outside disposable development/test databases.

If it has been applied to any persistent/shared environment, do not rely on rewriting historical migration history. Restore the canonical historical migration where possible and create a new forward-only Sprint 25 corrective migration that establishes the required final state.

Verify directly:
- `pg_class.relrowsecurity`
- `pg_class.relforcerowsecurity`
- `pg_policies`
- required NOT NULL constraints
- foreign keys
- uniqueness constraints

The final repository must have one canonical migration chain.

# 3. Non-Negotiable Principles

- No major feature inflation.
- No false production claims.
- Connector certification never means identity ownership verification.
- Mock/fixture/test-only evidence must never influence trusted production scoring.
- External OSINT remains consent-gated, budgeted, health-aware, certified, concurrency-bounded, provenance-preserving, and human-reviewed.
- A release must be reproducible from documented commands, not only from one developer machine.

# 4. Phase A — Freeze Sprint 24 Baseline

Record:
- git commit SHA and branch;
- working-tree status;
- Alembic head;
- Docker Compose configuration;
- Python, Node, PostgreSQL, Redis, and Celery versions;
- exact backend test result;
- frontend build result.

Create `docs/releases/sprint24-certified-baseline.md`.

# 5. Phase B — Migration History & Upgrade Matrix

Audit all Alembic revisions for:
- edited historical migrations;
- branch divergence;
- multiple heads;
- RLS changes;
- NOT NULL changes;
- connector certification changes;
- temporal and execution-audit changes.

Run:
- `alembic heads`
- `alembic history --verbose`
- `alembic current`

Create a forward-only Sprint 25 corrective migration where required.

Test:
- empty database → final head;
- Sprint 23 database → final head;
- Sprint 24 certified database → final head.

Do not perform destructive migration experiments on non-disposable databases.

# 6. Phase C — CI/CD Production Gate

Create or finalize CI, preferably `.github/workflows/ci.yml` if GitHub is used.

Pipeline stages:
1. static validation;
2. backend unit tests;
3. start real PostgreSQL and Redis;
4. apply Alembic migrations;
5. backend integration tests;
6. RLS/ownership tests;
7. Redis concurrency tests;
8. privacy/security regression;
9. frontend production build;
10. container image build;
11. dependency and secret scanning;
12. release manifest generation.

CI must fail on:
- backend failure;
- unexpected infrastructure-test skip;
- migration failure;
- multiple Alembic heads;
- frontend build failure;
- secret scanning failure;
- release-blocking dependency finding according to project policy;
- container build failure.

Do not replace required PostgreSQL/Redis integration tests with SQLite or mocks.

# 7. Phase D — Test Classification

Formalize markers such as:
- `unit`
- `integration`
- `postgres`
- `redis`
- `celery`
- `security`
- `privacy`
- `connector`
- `live_connector`
- `slow`

Normal CI must never accidentally make live external OSINT requests. Live connector tests remain explicitly gated.

# 8. Phase E — Container Reproducibility

Verify production-shaped builds for API, worker, and frontend.

Requirements:
- pinned base image versions where practical;
- non-root runtime where supported;
- no development secrets baked into images;
- no unnecessary test fixtures in production images;
- health checks;
- deterministic dependency installation.

Record immutable image identifiers/digests where available.

# 9. Phase F — Configuration Validation

Classify environment variables as:
- required;
- optional;
- development-only;
- test-only;
- secret.

Production startup should fail clearly on missing required configuration without printing secret values.

Create `docs/operations/configuration-reference.md`.

# 10. Phase G — Final Connector Runtime Certification

For Maigret and OSINTgram report:
- adapter version;
- runtime installed or not;
- actual runtime version/revision;
- runtime fingerprint;
- conformance policy version;
- certification status;
- live smoke status;
- final availability.

Allowed truthful states include:
- AVAILABLE
- CERTIFIED_NOT_LIVE_SMOKE_TESTED
- INSTALLED_UNVERIFIED
- TEST_ONLY
- DISABLED

Do not present mock compatibility labels as real runtime versions.

Live smoke tests remain disabled by default and require explicit operator enablement, explicit CLI invocation, and an authorized test target.

# 11. Phase H — Performance Baseline

Create a bounded benchmark suite measuring:
- health endpoint latency;
- authenticated Identity Anchor read;
- candidate pagination;
- timeline pagination;
- review queue pagination;
- orchestration creation;
- assessment recalculation;
- representative privacy export;
- Redis lease acquisition under contention.

Record:
- hardware/environment;
- concurrency;
- request count;
- p50;
- p95;
- p99 where meaningful;
- error rate.

Create `docs/performance/sprint25-performance-baseline.md`.

Do not present local benchmark results as universal production capacity.

# 12. Phase I — Backpressure & Concurrency

Using fixture/test adapters only, test:
- multiple concurrent orchestration requests;
- connector concurrency limit K;
- queue accumulation;
- lease contention;
- budget rejection;
- worker recovery;
- duplicate requests.

Verify:
- no more than K active connector executions;
- excess work is rejected/deferred according to policy;
- no uncontrolled subprocess spawning;
- no duplicate semantic candidates;
- no leaked leases.

# 13. Phase J — Bounded Soak Test

Run a 30–60 minute synthetic/test workload.

Observe:
- memory growth;
- DB connection pool behavior;
- Redis lease cleanup;
- queue depth;
- task failures;
- duplicate records;
- unhandled exceptions.

This is a lifecycle smoke test, not proof of long-term production stability.

# 14. Phase K — Failure Injection

Test controlled failures:
- Redis unavailable;
- PostgreSQL unavailable;
- Celery worker restart;
- connector timeout;
- worker crash while holding a lease;
- stale certification;
- malformed connector output;
- duplicate task delivery.

Verify behavior matches `docs/operations/failure-recovery-matrix.md` and update documentation where reality differs.

# 15. Phase L — Backup & Restore Drill

Using disposable infrastructure:
1. populate representative data;
2. create PostgreSQL backup;
3. replace/destroy disposable DB;
4. restore backup;
5. start application;
6. verify migration state;
7. verify representative identity data;
8. verify cross-user isolation;
9. verify continued processing.

Create `docs/operations/backup-restore-runbook.md`.

# 16. Phase M — Privacy & Data Lifecycle Final Audit

Re-run:
- privacy export;
- cross-user exclusion;
- secret exclusion;
- account deletion;
- crypto-shred;
- retry/idempotency.

Create `docs/privacy/data-ownership-retention-matrix.md`.

Cover at least:
- IdentityAnchor
- IdentityAlias
- ConfirmedProfileReference
- CandidateProfile
- CandidateProvenanceObservation
- IdentityMatchAssessment
- IdentityCluster
- IdentityChangeEvent
- IdentityReviewItem
- IdentityOrchestrationRun
- ConnectorExecutionPlanItem
- ConnectorCertificationRecord

For each, document owner, user-data status, export behavior, deletion behavior, system retention, and retention reason.

# 17. Phase N — Final Security Regression

Verify:
- authentication;
- authorization;
- RLS/ownership;
- CSRF where applicable;
- SSRF;
- rate limiting;
- connector argument/option injection;
- secret redaction;
- zero-egress consent boundary;
- test-only production blocking;
- certification invalidation;
- mock evidence exclusion;
- privacy isolation.

Do not perform a broad security rewrite unless a verified defect requires it.

# 18. Phase O — Secret & Sensitive Data Scan

Scan:
- repository;
- test fixtures;
- logs;
- privacy export fixtures;
- Docker configuration;
- CI configuration;
- generated release artifacts.

Look for:
- session IDs;
- API keys;
- authorization headers;
- private keys;
- database passwords;
- unintended real user identifiers.

Document false positives and remediation.

# 19. Phase P — Dependency & Supply-Chain Audit

Inventory Python, Node, and container dependencies.

Check for:
- critical known vulnerabilities;
- unmaintained direct dependencies;
- unpinned critical runtime dependencies;
- unexpected packages.

Classify findings as P0/P1/P2/P3/accepted risk.

Create `docs/security/sprint25-dependency-audit.md`.

Do not perform risky major upgrades merely to make the report look clean.

# 20. Phase Q — Observability Acceptance

Verify:
- `/health/live`
- `/health/ready`
- `/health/components`
- `/metrics`

Verify safe correlation:
`API request → orchestration run → plan item → task → connector execution → provenance`

Ensure logs/metrics do not expose:
- raw session secrets;
- authorization headers;
- emails;
- usernames;
- profile URLs;
- raw user IDs as metric labels.

# 21. Phase R — Alerting Recommendations

Create `docs/operations/alerting-recommendations.md`.

Cover:
- API readiness failure;
- PostgreSQL unavailable;
- Redis unavailable;
- Celery queue backlog;
- connector timeout/failure spike;
- concurrency rejection spike;
- certification becoming stale;
- privacy job failure;
- elevated 5xx rate.

Keep recommendations deployment-vendor neutral unless the project already uses a specific platform.

# 22. Phase S — Frontend Final Acceptance

Run `npm run build`.

Verify:
- route-level lazy loading;
- direct route refresh;
- authenticated routing;
- Connector Status Panel;
- evidence trust labels;
- Timeline;
- Review Queue;
- Identity Discovery;
- Clusters;
- loading/error states.

Perform a production-build smoke test against the integration API, not only TypeScript compilation.

# 23. Phase T — API Contract Snapshot

Generate/preserve the final OpenAPI schema as `docs/api/openapi-sprint25.json` or repository equivalent.

Verify important endpoints:
- Identity Anchor;
- discovery/orchestration;
- connector certification;
- assessments;
- clusters;
- timeline;
- reviews;
- health.

# 24. Phase U — Operational Runbooks

Create/finalize:
- `docs/operations/deployment-runbook.md`
- `docs/operations/rollback-runbook.md`
- `docs/operations/backup-restore-runbook.md`
- `docs/operations/connector-certification-runbook.md`
- `docs/operations/incident-response-runbook.md`

Runbooks should contain executable procedures, not only architecture descriptions.

# 25. Phase V — Final Architecture Documentation

Create `docs/architecture/final-system-architecture.md`.

Document:

`User → Authentication/RLS → Identity Anchor → Consent → Connector Orchestration → Eligibility/Budget/Health/Certification/Concurrency → Bounded Worker Execution → Candidate + Immutable Provenance → Evidence Trust Policy → Deterministic Match Engine → Conservative Clustering → Temporal Change Detection → Human Review → Explicit User Confirmation → Privacy Export/Crypto-Shred`

Operational layer:
`PostgreSQL + Redis + Celery + Docker + CI/CD + Migrations + Health + Metrics + Structured Logs + Backup/Restore`

# 26. Phase W — Final Threat Model

Create/update `docs/security/final-threat-model.md`.

Cover:
- cross-tenant access;
- SSRF;
- command injection;
- connector credential leakage;
- malicious usernames/options;
- untrusted connector output;
- mock evidence contamination;
- certification drift;
- Redis failure;
- worker crash;
- duplicate task delivery;
- privacy export leakage;
- migration mistakes;
- operator misuse.

For each: asset, threat, control, verification, residual risk.

# 27. Phase X — Known Limitations Register

Create `docs/releases/final-known-limitations.md`.

Potential limitations:
- optional connector runtimes not installed;
- live connector smoke tests not performed;
- external platform instability;
- OSINT incompleteness;
- deterministic scoring limitations;
- avatar similarity is non-biometric and only weak/moderate evidence;
- connector certification does not prove identity ownership.

A safely handled, truthful limitation is not automatically a release blocker.

# 28. Phase Y — Final Version & Immutable Manifest

Assign the release version according to repository conventions, for example `v1.0.0-rc1` only if consistent with the project's versioning scheme.

Create `docs/releases/final-release-manifest.md` containing:
- release version;
- git commit SHA;
- build timestamp;
- migration head;
- runtime versions;
- backend result;
- frontend result;
- CI result;
- container identifiers;
- connector states;
- certification states;
- performance baseline;
- security audit;
- known limitations;
- final decision.

Never include secret values.

# 29. Phase Z — Clean-Room Release Rehearsal

From a clean checkout:
1. configure safe integration environment;
2. build containers;
3. start dependencies;
4. apply migrations;
5. start API/workers/frontend;
6. wait for readiness;
7. run backend tests;
8. run frontend build/smoke verification;
9. run representative E2E journey;
10. verify health and metrics;
11. verify connector status truthfulness;
12. verify privacy export;
13. verify backup procedure;
14. produce release manifest.

The purpose is to detect undocumented developer-machine dependencies.

# 30. Required Implementation Order

1. Freeze Sprint 24 certified baseline.
2. Record repository/runtime state.
3. Audit historical migration edits.
4. Restore immutable migration history where required.
5. Create forward-only Sprint 25 corrective migration.
6. Verify one Alembic head.
7. Run migration matrix.
8. Add/finalize pytest markers.
9. Build CI with real PostgreSQL and Redis.
10. Verify container reproducibility.
11. Validate production configuration.
12. Reconcile Maigret state.
13. Reconcile OSINTgram state.
14. Run performance baseline.
15. Run backpressure/concurrency test.
16. Run bounded soak test.
17. Run controlled failure injection.
18. Verify failure recovery documentation.
19. Perform backup/restore drill.
20. Run final privacy lifecycle audit.
21. Generate data ownership/retention matrix.
22. Run final security regression.
23. Run secret scan.
24. Run dependency audit.
25. Verify observability.
26. Create alerting recommendations.
27. Run frontend final acceptance.
28. Generate OpenAPI snapshot.
29. Finalize operational runbooks.
30. Finalize architecture documentation.
31. Finalize threat model.
32. Finalize known limitations.
33. Assign release version according to project convention.
34. Generate immutable release manifest.
35. Perform clean-room release rehearsal.
36. Run final backend suite.
37. Run final frontend production build.
38. Verify final migration head.
39. Produce Sprint 25 final walkthrough.
40. Make FINAL GO / CONDITIONAL GO / NO-GO decision.

# 31. Definition of Done

## Migration integrity
- Historical migration integrity audited.
- No production fix depends solely on rewriting an already-applied migration.
- Corrective changes exist as forward migration(s) where required.
- One canonical Alembic head.
- Fresh DB, Sprint 23 upgrade, and Sprint 24 upgrade pass.
- Final RLS state verified directly in PostgreSQL.

## CI/CD
- CI runs backend and frontend gates.
- Required integration tests use real PostgreSQL and Redis.
- CI applies migrations.
- Unexpected infrastructure-test skips fail the gate.
- Live external connector tests remain separately gated.

## Backend & security
- Full final backend suite passes.
- 0 failures and 0 errors.
- No required test skipped for missing infrastructure.
- Cross-user isolation passes.
- SSRF, connector injection, secret redaction, test-only exclusion, and certification invalidation pass.
- No unresolved P0/P1 security defect.

## Privacy
- Privacy export passes.
- Cross-user and secret exclusion pass.
- Crypto-shred/account deletion passes.
- Shred retry is idempotent.
- Data ownership/retention matrix exists.

## Performance & resilience
- Performance baseline exists.
- Redis and connector contention are bounded.
- Backpressure verified.
- Bounded soak test completes without release-blocking defect.
- Failure injection documented.
- Backup/restore succeeds.

## Observability
- Liveness, readiness, component health, and metrics work.
- Structured correlation works.
- Sensitive/high-cardinality telemetry audit passes.
- Alerting recommendations exist.

## Connectors
- Maigret and OSINTgram states are truthful.
- Mock labels are not presented as real runtime versions.
- Optional unavailable connectors do not falsely appear available.
- Connector certification is not presented as identity verification.

## Frontend
- Production build passes.
- Lazy routes and API integration smoke pass.
- Connector states and evidence trust labels render correctly.
- Loading/error states work.

## Operations
- Deployment, rollback, backup/restore, connector certification, and incident-response runbooks exist.
- Final architecture and threat model exist.
- Known limitations register exists.
- OpenAPI snapshot exists.
- Final release manifest exists.
- Clean-room release rehearsal succeeds.

# 32. Final Decision Criteria

## FINAL GO
Allowed when:
- P0 = 0;
- unresolved P1 = 0;
- migration history is safe;
- migration matrix passes;
- full infrastructure-backed suite passes;
- CI reproduces verification;
- security/privacy gates pass;
- backup/restore succeeds;
- no release-blocking performance/resilience defect exists;
- frontend acceptance passes;
- connector states are truthful;
- release rehearsal succeeds;
- final documentation is complete.

## CONDITIONAL GO
Appropriate when the core platform is fully verified but optional external connector deployment remains incomplete, for example:
- Core platform = production release candidate
- Maigret = certified or test_only
- OSINTgram = test_only
- live smoke tests = intentionally not run
- P0 = 0
- P1 = 0

The condition must be explicit and operational.

## NO-GO
Required for:
- historical migration rewrite being the only production fix;
- broken upgrade path or multiple Alembic heads;
- cross-user/RLS failure;
- test-only evidence affecting production scoring;
- secret leakage;
- privacy cross-user leakage;
- crypto-shred failure;
- Redis concurrency fail-open;
- unbounded connector execution;
- failed backup restore;
- required CI integration tests not executing;
- unresolved P0/P1 security defect;
- clean-room rehearsal failure due to undocumented dependencies.

# 33. Final Walkthrough Requirements

The final walkthrough must report at minimum:
1. Sprint 24 baseline commit and migration head.
2. Historical migration edit audit and remediation.
3. Sprint 25 migration ID(s) and final head.
4. Fresh/Sprint23/Sprint24 migration results.
5. Final RLS and constraint verification.
6. CI workflow and result.
7. Exact backend collected/passed/failed/error/skipped/warning counts.
8. Reason for every skip.
9. Backend duration and infrastructure versions.
10. Container build results and identifiers where available.
11. Maigret runtime/certification/availability.
12. OSINTgram runtime/certification/availability.
13. Performance environment and p50/p95 results.
14. Redis contention/backpressure results.
15. Soak-test duration and observations.
16. Redis/PostgreSQL/worker failure-injection results.
17. Lease crash-recovery and duplicate-task results.
18. Backup and restore results.
19. Privacy export and secret-scan results.
20. Crypto-shred and idempotency results.
21. Security regression and dependency audit results.
22. Health/readiness/components/metrics results.
23. Telemetry privacy audit and correlation result.
24. Frontend build/chunk/smoke results.
25. OpenAPI snapshot and runbook locations.
26. Architecture, threat model, and known-limitations locations.
27. Final release version and commit SHA.
28. Final release manifest location.
29. Clean-room rehearsal result.
30. P0/P1 findings, fixes, and remaining P2/P3 limitations.
31. FINAL GO / CONDITIONAL GO / NO-GO.

# 34. Final Expected System State

`User → Authentication/RLS → Verified Identity Anchor → Consent → Multi-Connector Orchestration → Eligibility + Budget + Health + Certification + Concurrency + Idempotency → Bounded Worker Execution → Candidate + Immutable Provenance → Evidence Trust Policy → Deterministic Match Engine → Conservative Clustering → Temporal Change Detection → Human Review → Explicit User Confirmation → Privacy Export/Crypto-Shred`

Supported by:

`PostgreSQL + Redis + Celery + Docker + CI/CD + Safe Migrations + Health + Readiness + Metrics + Structured Logs + Backup/Restore + Security Regression + Performance Baseline + Operational Runbooks + Immutable Release Manifest`

# 35. Final Sprint Principle

> The final release is not defined by adding one more feature. It is defined by proving that the features already built can be migrated, tested, deployed, observed, recovered, secured, and operated reproducibly without weakening the system's identity, privacy, or evidence-trust boundaries.

Sprint 25 closes the current DigiZafe roadmap by converting the Sprint 24 integration-certified release candidate into a reproducible, operationally documented final production release candidate.
