# Sprint 24 --- Production Readiness Gate, Full-Stack Integration Certification, Observability & Operational Resilience

## Status

-   **Planned Sprint:** 24
-   **Baseline:** Sprint 23 implementation complete
-   **Sprint 22 verified baseline:** 95/95 backend tests passed
-   **Sprint 23 reported collection:** 101 backend tests
-   **Important Sprint 23 limitation:** some PostgreSQL/Redis-dependent
    integration tests were not fully executed in the sandbox because
    live infrastructure was unavailable
-   **Sprint 23 decision:** GO reported by implementation agent, but
    Sprint 24 must independently close the remaining verification gap
    before production-readiness can be claimed
-   **Primary goal:** prove the complete DigiZafe identity discovery,
    connector certification, evidence trust, temporal review, privacy,
    and orchestration stack works together under a real local
    integration environment and establish production-grade
    observability, recovery, and deployment gates.

------------------------------------------------------------------------

# 1. Sprint 24 Mission

Sprints 14--23 built the system in layers:

``` text
Verified baseline
    ↓
Identity Anchor
    ↓
Maigret candidate discovery
    ↓
Deterministic identity matching
    ↓
Cross-links + non-biometric avatar similarity
    ↓
OSINTgram connector architecture
    ↓
Multi-connector orchestration
    ↓
Temporal change detection + human review
    ↓
Security remediation + connector conformance
    ↓
Runtime certification + evidence trust boundaries
```

Sprint 24 must now answer a different question:

> Does the complete system work as one production-shaped system under
> real PostgreSQL, Redis, Celery, migrations, API, frontend, connector
> workers, privacy workflows, and failure conditions?

This sprint is primarily a **production-readiness and
integration-certification sprint**.

It must not add major new identity-discovery capabilities unless
required to fix a verified P0/P1 integration defect.

The desired outcome is a trustworthy release candidate.

------------------------------------------------------------------------

# 2. Critical Preflight Position

Sprint 23 reported:

``` text
101 backend tests collect
unit logic verified
frontend build validated
some DB/Redis integration tests could not execute because infrastructure was unavailable
```

Therefore Sprint 24 must not assume:

``` text
101 collected
=
101 passed
```

The first gate is to establish the exact truth.

Required classifications:

``` text
PASSED
FAILED
SKIPPED_BY_POLICY
SKIPPED_MISSING_INFRASTRUCTURE
NOT_COLLECTED
```

`SKIPPED_MISSING_INFRASTRUCTURE` is not acceptable for the final
production-readiness gate for tests whose purpose is to verify:

-   PostgreSQL behavior;
-   Redis concurrency;
-   RLS;
-   orchestration persistence;
-   Celery execution;
-   migration behavior;
-   privacy deletion;
-   connector execution audit.

------------------------------------------------------------------------

# 3. Sprint 24 Core Outcomes

Sprint 24 must deliver:

1.  **A reproducible full integration environment**
2.  **A complete backend regression run with infrastructure available**
3.  **Real Redis concurrency and fail-closed verification**
4.  **Real PostgreSQL RLS and cross-user isolation verification**
5.  **Celery task and queue integration verification**
6.  **End-to-end identity journey certification**
7.  **Migration and rollback/restore readiness**
8.  **Production observability and health/readiness endpoints**
9.  **Structured metrics and alertable operational signals**
10. **Failure recovery and idempotent retry verification**
11. **Privacy export and crypto-shred end-to-end verification**
12. **Connector runtime truthfulness and certification reconciliation**
13. **Frontend production-build and lazy-loading verification**
14. **A formal Release Candidate manifest**
15. **A final GO / CONDITIONAL GO / NO-GO gate**

------------------------------------------------------------------------

# 4. Non-Negotiable Invariants

## 4.1 No false verification claims

The walkthrough must distinguish:

``` text
collected
passed
skipped
failed
not executed
```

Never report a test as passed because it collected successfully.

------------------------------------------------------------------------

## 4.2 Infrastructure-dependent security tests must run against infrastructure

Mocks remain useful for unit testing.

They do not replace real integration verification for:

``` text
PostgreSQL RLS
Redis atomic leases
Celery routing
migration application
database constraints
transaction isolation
cross-user access
```

------------------------------------------------------------------------

## 4.3 No production claim from mock connector output

The following remain distinct:

``` text
mock
fixture
live
```

And:

``` text
TEST_ONLY
LIVE_UNCERTIFIED
LIVE_CERTIFIED
USER_CONFIRMED
```

No test fixture may be presented as a live connector result.

------------------------------------------------------------------------

## 4.4 Candidate discovery never auto-confirms identity

The complete end-to-end system must preserve:

``` text
discovery
→ candidate
→ evidence
→ deterministic assessment
→ human review
→ optional explicit confirmation
```

------------------------------------------------------------------------

## 4.5 Failure must not bypass controls

Failures in:

``` text
Redis
PostgreSQL
connector runtime
certification service
health service
budget service
Celery
```

must never silently cause:

``` text
unlimited execution
cross-user access
uncertified evidence promotion
secret leakage
auto-confirmation
```

------------------------------------------------------------------------

# 5. Phase A --- Reproducible Integration Environment

## Goal

Create one documented command path that starts the complete integration
stack.

Expected services may include:

``` text
postgres
redis
api
celery/core worker
identity_enrichment worker
osint_connectors worker
frontend
```

Use the repository's actual architecture.

Do not invent duplicate services if existing workers already consume
multiple queues correctly.

------------------------------------------------------------------------

## 5.1 Integration Compose Profile

Create or verify a dedicated integration profile such as:

``` bash
docker compose --profile integration up -d
```

or an equivalent repository-native command.

The environment must provide:

-   isolated test database;
-   isolated Redis namespace/database;
-   required workers;
-   deterministic test configuration;
-   no accidental production credentials;
-   live external connector calls disabled by default.

------------------------------------------------------------------------

## 5.2 Readiness Wait

Tests must not begin merely because containers started.

Add a bounded readiness mechanism that waits for:

``` text
PostgreSQL accepting connections
Redis responding
API readiness endpoint healthy
required Celery workers visible or otherwise verified
migration head applied
```

Timeout cleanly if the stack is not ready.

------------------------------------------------------------------------

# 6. Phase B --- Full Backend Regression Certification

Run the complete suite with PostgreSQL and Redis available:

``` bash
pytest tests/ -ra
```

The final walkthrough must report exactly:

``` text
collected
passed
failed
errors
skipped
xfailed
warnings
duration
```

Any skipped test must include a reason.

Final target:

``` text
0 failed
0 errors
0 unexpected warnings
0 infrastructure-required tests skipped because infrastructure is missing
```

A small number of explicitly policy-gated live connector tests may
remain skipped because:

``` text
enable_live_connector_smoke_tests = false
```

Those must be clearly identified as intentionally disabled live tests,
not missing-infrastructure skips.

------------------------------------------------------------------------

# 7. Phase C --- PostgreSQL & RLS Certification

Run real database integration tests covering at minimum:

``` text
User A cannot read User B IdentityAnchor
User A cannot read User B aliases
User A cannot read User B CandidateProfile
User A cannot read User B provenance
User A cannot read User B assessments
User A cannot read User B clusters
User A cannot read User B temporal events
User A cannot resolve User B review items
User A cannot read User B orchestration runs
User A cannot read User B execution audit data
User A cannot target User B candidate for revalidation
```

Where the architecture uses application-level ownership rather than
native PostgreSQL RLS for a specific table, document that truthfully.

Do not claim database RLS where only service-level filtering exists.

------------------------------------------------------------------------

# 8. Phase D --- Redis Atomic Lease Certification

Sprint 23 introduced sorted-set concurrency leases.

Verify against real Redis:

``` text
atomic acquisition
connector-wide limit
per-user limit
lease release
lease expiration
crashed-worker lease recovery
duplicate release safety
concurrent acquisition race
Redis-unavailable fail-closed behavior
```

Required high-contention test:

``` text
N concurrent acquisition attempts
limit = K
→ no more than K leases granted
```

The test must exercise the actual Redis implementation rather than only
a mock.

------------------------------------------------------------------------

# 9. Phase E --- Celery & Queue Routing Certification

Verify actual task routing for:

``` text
core/default tasks
identity_enrichment
osint_connectors
```

Required checks:

``` text
task routed to expected queue
wrong worker does not consume restricted connector task
task receives only safe identifiers
raw secrets absent from task payload
retry preserves idempotency
duplicate delivery does not create duplicate candidate/provenance rows
```

If queue topology differs from this plan, document the actual topology.

------------------------------------------------------------------------

# 10. Phase F --- Canonical End-to-End Identity Journey

Create a deterministic integration journey using fixtures and controlled
connector adapters.

The journey must execute through real:

``` text
API
PostgreSQL
Redis
Celery/task execution path
service layer
privacy layer
```

External live OSINT calls are not required.

## Journey A --- User A

``` text
1. Register/login User A.
2. Create or retrieve Identity Anchor.
3. Add active alias.
4. Grant required consent.
5. Start unified orchestration.
6. Planner evaluates connector eligibility.
7. Test/fixture connector execution creates CandidateProfile.
8. CandidateProvenanceObservation is persisted.
9. Evidence trust is classified correctly.
10. Test-only evidence contributes zero to production score.
11. Candidate remains unconfirmed.
12. User explicitly confirms one candidate.
13. ConfirmedProfileReference is created.
14. Match assessment recalculates deterministically.
15. Cluster input fingerprint changes only when required.
16. Temporal event is generated for a material transition.
17. Review item is created when policy requires.
18. User resolves review.
19. Privacy export includes expected user-linked records.
```

## Journey B --- User B Isolation

Simultaneously verify:

``` text
User B cannot access any User A identity artifacts
```

------------------------------------------------------------------------

# 11. Phase G --- Certified-Live Trust Journey

This phase may use a controlled synthetic certification context without
making a live external network call.

Test:

``` text
runtime fingerprint A
→ certification PASSED
→ live-mode provenance linked to certification A
→ EvidenceTrustPolicy = LIVE_CERTIFIED
→ evidence becomes eligible for normal deterministic policy
```

Then:

``` text
runtime fingerprint changes to B
→ certification A becomes STALE
→ old provenance remains linked to A
→ affected candidates identified
→ incremental reassessment occurs
→ unrelated candidates untouched
```

This verifies the trust architecture independently of external service
availability.

------------------------------------------------------------------------

# 12. Phase H --- Real Connector Runtime Reconciliation

For each connector, report the actual current state.

## Maigret

Report:

``` text
adapter version
runtime installed?
actual runtime version
runtime fingerprint
certification status
live smoke status
availability
```

## OSINTgram

Report:

``` text
adapter version
actual runtime installed?
actual runtime version/revision
runtime fingerprint
certification status
live smoke status
availability
```

`1.1.0-mock` must never be presented as a real OSINTgram runtime
version.

Allowed final states include:

``` text
Maigret = available
OSINTgram = test_only
```

or:

``` text
both = test_only
```

if that is the truthful environment state.

Sprint 24 does not require falsely forcing connectors into `available`.

------------------------------------------------------------------------

# 13. Phase I --- Health, Readiness & Liveness

Implement or verify distinct endpoints.

Recommended semantics:

## Liveness

``` text
GET /health/live
```

Answers:

> Is the API process alive?

Must not fail merely because an optional connector is unavailable.

## Readiness

``` text
GET /health/ready
```

Answers:

> Can this instance safely serve its required workload?

Check required dependencies such as:

``` text
database
Redis, if required for safe execution
migration compatibility
```

## Component status

``` text
GET /health/components
```

Return safe operational status for:

``` text
database
redis
celery/worker visibility if available
maigret
osintgram
identity_enrichment
```

Do not expose secrets or internal stack traces.

------------------------------------------------------------------------

# 14. Phase J --- Prometheus Metrics

Sprint 23 added/fixed `prometheus_client`.

Sprint 24 must make metrics intentional rather than merely satisfying an
import.

Expose or verify a metrics endpoint such as:

``` text
GET /metrics
```

Recommended metrics:

``` text
digizafe_http_requests_total
digizafe_http_request_duration_seconds

digizafe_orchestration_runs_total
digizafe_connector_executions_total
digizafe_connector_execution_duration_seconds
digizafe_connector_failures_total
digizafe_connector_timeouts_total

digizafe_connector_concurrency_active
digizafe_connector_concurrency_rejections_total

digizafe_connector_certification_status
digizafe_connector_health_status

digizafe_candidate_profiles_created_total
digizafe_assessments_recalculated_total
digizafe_review_items_created_total
digizafe_revalidation_requests_total
```

Avoid high-cardinality labels.

Forbidden metric labels include:

``` text
email address
username
profile URL
candidate ID
user ID
session ID
raw error text
```

Prefer bounded labels:

``` text
connector
outcome
error_category
execution_mode
trust_class
```

------------------------------------------------------------------------

# 15. Phase K --- Structured Logging & Correlation

Introduce or verify structured logging fields:

``` text
request_id
orchestration_run_id
plan_item_id
connector
task_id
outcome
error_category
```

Do not log:

``` text
raw secrets
session cookies
authorization headers
full sensitive profile payloads
```

Add a correlation ID middleware if the system does not already have one.

The same request/orchestration identifier should make it possible to
trace:

``` text
API request
→ orchestration
→ connector plan item
→ worker execution
→ provenance persistence
```

without exposing sensitive user data.

------------------------------------------------------------------------

# 16. Phase L --- Failure Recovery Matrix

Create:

``` text
docs/operations/failure-recovery-matrix.md
```

Cover at minimum:

  -----------------------------------------------------------------------
  Failure                             Expected Behavior
  ----------------------------------- -----------------------------------
  PostgreSQL unavailable              readiness fails; no unsafe writes

  Redis unavailable                   concurrency-controlled connector
                                      execution fails closed

  Celery worker unavailable           run remains queued/pending and
                                      observable

  Connector runtime missing           connector unavailable/test_only; no
                                      fake live result

  Certification stale                 live evidence not promoted as
                                      certified

  Connector timeout                   bounded termination; normalized
                                      timeout outcome

  Malformed output                    no unvalidated provenance promotion

  Duplicate task delivery             idempotent persistence

  Worker crash during lease           lease expires and capacity recovers

  Privacy shred retry                 idempotent deletion

  Export failure                      no partial success claim
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 17. Phase M --- Retry & Idempotency Certification

Verify retry behavior for:

``` text
orchestration creation
connector task execution
candidate upsert
provenance persistence
assessment recalculation
cluster synchronization
temporal event creation
review-item creation
privacy shred
```

Required invariant:

``` text
same logical event retried
→ no duplicate semantic records
```

Where multiple historical records are intentionally allowed, define the
idempotency boundary explicitly.

------------------------------------------------------------------------

# 18. Phase N --- Privacy Export End-to-End Certification

Create a populated test user containing:

``` text
IdentityAnchor
aliases
confirmed profiles
CandidateProfiles
provenance
assessments
clusters
orchestration runs
execution plan/audit fields
temporal events
review items
```

Generate the privacy export.

Verify:

``` text
expected user-linked data present
cross-user data absent
raw connector secrets absent
operator secrets absent
internal credentials absent
serialization succeeds
```

Store only test artifacts.

------------------------------------------------------------------------

# 19. Phase O --- Crypto-Shred / Account Deletion Certification

Using an isolated test user:

``` text
1. Create full identity history.
2. Trigger account deletion/shred.
3. Verify user-linked identity artifacts are removed according to policy.
4. Verify no orphan records remain where deletion is required.
5. Verify system-level connector certification records remain if they are not user-owned.
6. Verify User B remains unaffected.
7. Retry shred and confirm idempotency.
```

The final walkthrough must distinguish:

``` text
hard-deleted user data
retained system operational data
anonymized data, if any
```

------------------------------------------------------------------------

# 20. Phase P --- Migration Certification

Verify both:

## Fresh database

``` bash
alembic upgrade head
```

## Upgrade from Sprint 23 baseline

``` text
previous head
→ Sprint 24 head
```

Also run:

``` bash
alembic heads
alembic current
```

If downgrade support is part of the repository policy, test the latest
migration downgrade in a disposable environment.

Do not perform destructive downgrade testing against a non-disposable
database.

------------------------------------------------------------------------

# 21. Phase Q --- Database Constraint Audit

Verify critical database constraints actually exist.

Examples:

``` text
one IdentityAnchor per user
user-scoped candidate canonical URL uniqueness
valid foreign keys
certification linkage integrity
non-null temporal/audit fields where required
cascade behavior
```

Do not rely only on ORM declarations.

Inspect the migrated database schema or test constraint violations
directly.

------------------------------------------------------------------------

# 22. Phase R --- Frontend Production Verification

Run:

``` bash
npm run build
```

Report:

``` text
modules transformed
build duration
initial entry chunk
largest lazy chunk
gzip sizes
warnings
```

Verify lazy-loaded routes actually load:

``` text
Timeline
Review Queue
Identity Discovery
Identity Clusters
Connector Status/Operations
```

Also verify:

``` text
loading fallback
error fallback
direct route refresh
authenticated route behavior
```

------------------------------------------------------------------------

# 23. Phase S --- Connector Status UI Truthfulness

Verify the frontend accurately renders:

``` text
Test only
Installed — verification required
Certified
Available
Temporarily unavailable
Certification failed
Disabled
```

The UI must not infer availability merely from:

``` text
runtime_version != null
```

It must use the canonical backend status.

------------------------------------------------------------------------

# 24. Phase T --- Evidence Label Truthfulness

Verify UI language:

``` text
Test data
Live observation
Observed by a certified connector
User-confirmed profile
```

Do not display:

``` text
Verified identity
```

for connector certification alone.

Also verify the badge is derived from canonical backend trust data, not
from a frontend guess based only on connector name or execution mode.

------------------------------------------------------------------------

# 25. Phase U --- Security Regression

Run or add tests for:

``` text
JWT/authentication
CSRF where applicable
SSRF
RLS/ownership
rate limiting
connector argument injection
option injection
secret redaction
zero-egress consent boundary
test-only production blocking
certification invalidation
mock evidence scoring exclusion
cross-user access
privacy export isolation
```

No new broad security rewrite is required unless a verified defect is
found.

------------------------------------------------------------------------

# 26. Phase V --- Dependency & Runtime Inventory

Generate:

``` text
docs/operations/runtime-inventory.md
```

Record:

``` text
Python version
Node version
PostgreSQL version
Redis version
Celery version
FastAPI version
frontend build tool version
Maigret adapter version
Maigret runtime version
OSINTgram adapter version
OSINTgram runtime version/revision
```

Do not include secrets.

This document is a deployment manifest, not a claim that every optional
connector is available.

------------------------------------------------------------------------

# 27. Phase W --- Release Candidate Manifest

Create:

``` text
docs/releases/sprint24-release-candidate.md
```

Include:

``` text
release candidate identifier
git commit SHA if available
migration head
backend test result
frontend build result
integration environment result
connector states
known limitations
feature flags
required environment variables by name only
worker queues
GO/NO-GO decision
```

Do not include secret values.

------------------------------------------------------------------------

# 28. Phase X --- Optional Load & Contention Smoke Test

This is not a full performance benchmark.

Run a bounded local smoke test for:

``` text
concurrent API reads
multiple orchestration requests
Redis lease contention
candidate list pagination
timeline pagination
```

Verify:

``` text
no uncontrolled subprocess spawning
no obvious deadlocks
no duplicate semantic records
bounded latency under test load
```

Document hardware/environment so results are not misrepresented as
universal production benchmarks.

------------------------------------------------------------------------

# 29. Required Test Categories

Sprint 24 should add or complete tests for:

## Infrastructure

``` text
PostgreSQL connectivity
Redis connectivity
Celery task execution
queue routing
```

## RLS / ownership

``` text
cross-user reads denied
cross-user writes denied
targeted revalidation isolation
execution audit isolation
```

## Redis concurrency

``` text
atomic limit enforcement
lease expiry
crash recovery
fail closed
```

## Trust

``` text
TEST_ONLY score effect = 0
LIVE_UNCERTIFIED score effect follows exclusion policy
LIVE_CERTIFIED eligible
USER_CONFIRMED distinct
certification invalidation triggers bounded reassessment
```

## Idempotency

``` text
duplicate orchestration
duplicate task delivery
duplicate provenance observation
duplicate temporal transition
duplicate review creation
```

## Privacy

``` text
export completeness
cross-user exclusion
secret exclusion
shred completeness
shred idempotency
```

## Observability

``` text
health endpoints
readiness dependency behavior
metrics endpoint
no high-cardinality sensitive labels
structured log redaction
```

## Frontend

``` text
lazy route loading
connector state rendering
trust label rendering
```

------------------------------------------------------------------------

# 30. Required Implementation Order

``` text
1. Freeze Sprint 23 repository state.
2. Record current migration head.
3. Record exact Sprint 23 test collection/pass/skip truth.
4. Start real PostgreSQL and Redis integration infrastructure.
5. Start required Celery workers.
6. Add/verify readiness wait.
7. Run full backend suite with infrastructure available.
8. Classify every skip.
9. Fix P0/P1 integration defects only before continuing.
10. Certify PostgreSQL ownership/RLS boundaries.
11. Certify Redis atomic concurrency leases.
12. Certify Celery queue routing.
13. Run canonical User A/User B end-to-end identity journey.
14. Run synthetic certified-live trust transition journey.
15. Reconcile actual Maigret runtime state.
16. Reconcile actual OSINTgram runtime state.
17. Implement/verify liveness endpoint.
18. Implement/verify readiness endpoint.
19. Implement/verify component health endpoint.
20. Implement/verify Prometheus metrics.
21. Verify bounded metric labels.
22. Implement/verify structured correlation logging.
23. Create failure recovery matrix.
24. Test retry/idempotency boundaries.
25. Run privacy export certification.
26. Run crypto-shred/account deletion certification.
27. Verify fresh DB migration.
28. Verify upgrade from previous migration head.
29. Audit critical database constraints.
30. Run frontend production build.
31. Record before/after bundle data.
32. Verify lazy routes manually or through tests.
33. Verify connector status UI truthfulness.
34. Verify evidence label truthfulness.
35. Run security regression.
36. Generate runtime inventory.
37. Generate release candidate manifest.
38. Optionally run bounded local contention smoke test.
39. Run final full backend suite again.
40. Run final frontend production build again.
41. Produce Sprint 24 final walkthrough.
42. Make GO / CONDITIONAL GO / NO-GO decision for Sprint 25.
```

------------------------------------------------------------------------

# 31. Definition of Done

Sprint 24 is complete only when:

## Verification truth

-   [ ] Exact Sprint 23 baseline is documented.
-   [ ] Test collection is not confused with test passing.
-   [ ] Infrastructure-dependent tests run with infrastructure
    available.
-   [ ] Every remaining skip has an explicit reason.

## Backend

-   [ ] Full backend suite completes.
-   [ ] 0 failed.
-   [ ] 0 errors.
-   [ ] 0 unexpected warnings.
-   [ ] No required integration test is skipped due to missing
    PostgreSQL/Redis.

## Database

-   [ ] Fresh migration succeeds.
-   [ ] Upgrade migration succeeds.
-   [ ] Current head is singular and correct.
-   [ ] Critical constraints are verified.
-   [ ] Cross-user isolation is verified.

## Redis

-   [ ] Atomic concurrency limits are proven against real Redis.
-   [ ] Lease expiry works.
-   [ ] Crash recovery works.
-   [ ] Redis failure remains fail-closed for connector execution.

## Celery

-   [ ] Required workers consume correct queues.
-   [ ] Connector tasks route correctly.
-   [ ] Duplicate delivery is idempotent.
-   [ ] Secrets are absent from task payloads.

## Identity pipeline

-   [ ] End-to-end anchor-to-review journey passes.
-   [ ] Candidate discovery does not auto-confirm.
-   [ ] Test-only evidence contributes zero to production scoring.
-   [ ] Certified-live trust behavior is verified.
-   [ ] Certification invalidation triggers incremental reassessment
    only.

## Privacy

-   [ ] Privacy export succeeds.
-   [ ] Cross-user data is absent.
-   [ ] Secrets are absent.
-   [ ] Account deletion/shredding succeeds.
-   [ ] Shredding is idempotent.

## Observability

-   [ ] Liveness endpoint works.
-   [ ] Readiness endpoint reflects required dependency state.
-   [ ] Component health is safely exposed.
-   [ ] Metrics endpoint works.
-   [ ] Metrics avoid sensitive/high-cardinality labels.
-   [ ] Structured logs support correlation.
-   [ ] Secret redaction is verified.

## Frontend

-   [ ] Production build passes.
-   [ ] Lazy routes load correctly.
-   [ ] Connector states are truthful.
-   [ ] Evidence labels are truthful.
-   [ ] No connector certification is presented as identity
    verification.

## Operations

-   [ ] Failure recovery matrix exists.
-   [ ] Runtime inventory exists.
-   [ ] Release Candidate manifest exists.
-   [ ] Known limitations are explicit.

------------------------------------------------------------------------

# 32. GO / CONDITIONAL GO / NO-GO Criteria

## GO for Sprint 25

Allowed only when:

``` text
P0 = 0
unresolved P1 = 0
full infrastructure-backed backend suite passes
required PostgreSQL tests execute
required Redis tests execute
Celery integration is verified
frontend production build passes
migration chain is valid
privacy export passes
shredding passes
cross-user isolation passes
test-only evidence cannot affect production scoring
connector states are truthful
release candidate manifest is complete
```

------------------------------------------------------------------------

## CONDITIONAL GO

Appropriate when:

-   all core security and integration tests pass;
-   no P0/P1 defect remains;
-   optional real external connector runtimes remain `test_only` or
    `installed_unverified`;
-   live connector smoke testing is intentionally not performed;
-   the remaining limitation is operational connector deployment rather
    than core architecture.

Example:

``` text
Core DigiZafe platform = release-candidate ready
Maigret = test_only
OSINTgram = test_only
Decision = CONDITIONAL GO
```

------------------------------------------------------------------------

## NO-GO

Required if:

``` text
integration tests cannot run because required local infrastructure is still unavailable
Redis concurrency is only mock-tested
cross-user isolation fails
privacy export leaks another user's data
secret leakage is found
shredding leaves prohibited user-linked artifacts
test-only evidence affects production scoring
uncertified connector is shown as available
candidate discovery auto-confirms identity
migration chain is broken
P0 remains
unresolved P1 security defect remains
```

------------------------------------------------------------------------

# 33. Final Walkthrough Requirements

The Sprint 24 walkthrough must explicitly report:

1.  Sprint 23 starting migration head.
2.  Sprint 24 migration ID(s), if any.
3.  Final Alembic head.
4.  Sprint 23 reported test count.
5.  Sprint 24 initial collected count.
6.  Sprint 24 initial passed count.
7.  Initial failed/error/skipped/warning counts.
8.  Reason for every initial skip.
9.  Final collected count.
10. Final passed count.
11. Final failed/error/skipped/warning counts.
12. Reason for every final skip.
13. PostgreSQL version.
14. Redis version.
15. Celery version.
16. Integration stack startup command.
17. Database readiness result.
18. Redis readiness result.
19. Worker readiness result.
20. PostgreSQL RLS/ownership test result.
21. Redis atomic lease test result.
22. Redis contention test result.
23. Redis fail-closed test result.
24. Celery routing result.
25. Duplicate task delivery result.
26. User A end-to-end journey result.
27. User B isolation result.
28. Test-only evidence scoring result.
29. Synthetic LIVE_CERTIFIED trust result.
30. Certification invalidation result.
31. Incremental reassessment result.
32. Maigret adapter version.
33. Maigret actual runtime version.
34. Maigret runtime fingerprint.
35. Maigret certification status.
36. Maigret live smoke status.
37. Maigret availability.
38. OSINTgram adapter version.
39. OSINTgram actual runtime version/revision.
40. OSINTgram runtime fingerprint.
41. OSINTgram certification status.
42. OSINTgram live smoke status.
43. OSINTgram availability.
44. Liveness endpoint result.
45. Readiness endpoint result.
46. Component health result.
47. Metrics endpoint result.
48. Metrics added.
49. High-cardinality label audit result.
50. Structured logging/correlation result.
51. Secret redaction result.
52. Failure recovery matrix location.
53. Idempotency test result.
54. Privacy export result.
55. Privacy export secret scan result.
56. Crypto-shred result.
57. Crypto-shred retry/idempotency result.
58. Fresh database migration result.
59. Previous-head upgrade result.
60. Database constraint audit result.
61. Frontend modules transformed.
62. Frontend build duration.
63. Initial bundle size.
64. Largest lazy chunk.
65. Frontend build warnings.
66. Lazy-route verification result.
67. Connector Status UI result.
68. Evidence trust label UI result.
69. Security regression result.
70. Runtime inventory location.
71. Release Candidate manifest location.
72. Optional contention/load smoke result.
73. P0 defects found.
74. P1 defects found.
75. Minimal fixes applied.
76. Remaining P2/P3 limitations.
77. Final release-readiness classification.
78. GO / CONDITIONAL GO / NO-GO for Sprint 25.

------------------------------------------------------------------------

# 34. Expected Sprint 24 End State

The complete system should now be demonstrably verified as:

``` text
User
  ↓
Verified Identity Anchor
  ↓
Consent-Gated Orchestration
  ↓
Budget + Health + Certification + Concurrency
  ↓
Bounded Connector Execution
  ↓
Immutable Provenance
  ↓
Evidence Trust Policy
  ↓
Candidate Profile
  ↓
Deterministic Match Assessment
  ↓
Identity Cluster
  ↓
Temporal Change Detection
  ↓
Human Review
  ↓
Explicit User Confirmation
  ↓
Privacy Export / Crypto-Shred
```

With operational control around it:

``` text
Health
Readiness
Metrics
Structured Logs
Failure Recovery
Migration Certification
Release Manifest
```

------------------------------------------------------------------------

# 35. Final Sprint 24 Principle

> Production readiness is not established by the number of features
> implemented or tests collected. It is established by reproducible
> evidence that the complete system behaves correctly under its real
> dependencies, preserves its security boundaries during failure, and
> reports its limitations truthfully.

Sprint 24 should convert DigiZafe from a collection of individually
implemented capabilities into a **verified release candidate**.
