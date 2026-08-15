# Sprint 23 --- Live Connector Runtime Certification, Evidence Trust Boundaries & Production Hardening

## Status

-   **Baseline:** Sprint 22 complete
-   **Backend baseline:** 95/95 tests passing
-   **Starting Alembic head:** `2ec027d8be5b`
-   **Sprint 22 decision:** CONDITIONAL GO
-   **Primary goal:** Move the connector subsystem from correctly
    isolated `test_only` architecture toward truthfully certified
    production runtimes, while formalizing evidence trust, runtime
    provenance, operational controls, and frontend performance.

------------------------------------------------------------------------

# 1. Mission

Sprint 22 established the security boundary required before real
external OSINT connectors can be treated as operational:

-   revalidation passes through canonical orchestration;
-   connector availability is DB-backed and fail-safe;
-   mock, fixture, and live provenance are separated;
-   live smoke testing is disabled by default;
-   temporal state transitions are deterministic;
-   review and timeline interfaces are production-capable;
-   `test_only` connectors are blocked from production execution.

Sprint 23 must now establish this principle:

> A connector is not production-ready because its package or executable
> exists. It must be reproducibly installed, runtime-detected,
> conformance-tested, certified for the exact runtime fingerprint, and
> prevented from contaminating trusted evidence if its runtime or
> certification changes.

The sprint has five outcomes:

1.  Real connector runtime packaging and certification.
2.  Canonical evidence trust and promotion rules.
3.  Production-safe connector operations and observability.
4.  Frontend connector visibility and bundle optimization.
5.  A production-readiness gate for identity discovery.

------------------------------------------------------------------------

# 2. Non-Negotiable Invariants

## 2.1 Discovery is not confirmation

``` text
Connector observation
        ↓
CandidateProfile
        ↓
Provenance + evidence
        ↓
Deterministic assessment
        ↓
Human review
        ↓
Optional user confirmation
```

No connector may directly create a confirmed identity.

## 2.2 Installation is not certification

``` text
runtime absent
→ test_only

runtime detected
→ installed_unverified

offline conformance passed
→ certified

authorized live smoke passed, if required
→ live_verified

feature enabled + valid certification + healthy runtime
→ available
```

## 2.3 Certification is runtime-specific

Certification must be bound to:

-   connector type;
-   adapter version;
-   runtime version;
-   runtime revision;
-   parser version;
-   conformance policy version;
-   runtime fingerprint.

Any relevant change must invalidate or stale the old certification.

## 2.4 Provenance meaning is immutable

Forbidden:

``` text
mock observation
→ UPDATE execution_mode = live
```

Required:

``` text
old mock observation remains mock
new real execution creates new live provenance
```

## 2.5 Live execution remains bounded

Every live execution must enforce:

-   ownership;
-   consent;
-   eligibility;
-   feature flags;
-   certification;
-   availability;
-   health;
-   budgets;
-   idempotency;
-   concurrency limits;
-   timeouts;
-   output limits;
-   safe process invocation;
-   secret redaction.

## 2.6 External output is always untrusted input

Certified connector output still requires:

-   schema validation;
-   canonicalization;
-   URL safety;
-   type validation;
-   size limits;
-   provenance preservation;
-   evidence-policy evaluation.

## 2.7 Normal tests remain offline

`pytest tests/ -ra` must remain deterministic, credential-free, and free
from live OSINT requests.

------------------------------------------------------------------------

# 3. Preflight Baseline

Before implementation run:

``` bash
pytest tests/ -ra
alembic heads
alembic current
npm run build
```

Expected baseline:

``` text
95 collected
95 passed
0 failed
0 errors

Alembic head:
2ec027d8be5b

Maigret:
runtime_version = null
availability = test_only

OSINTgram:
runtime_version = null
availability = test_only

enable_live_connector_smoke_tests = false
```

If the repository does not match, document and resolve the discrepancy
before continuing.

------------------------------------------------------------------------

# 4. Phase A --- Reproducible Connector Runtime Packaging

## 4.1 Maigret

Verify the actual runtime, not dependency metadata alone:

-   Is the package installed in the execution image?
-   Is the CLI or Python entry point callable?
-   What exact version is running?
-   Does the current adapter parser match its output?
-   Does runtime detection work inside the actual connector worker?

Preferred architecture:

``` text
dedicated OSINT connector worker
        ↓
pinned Maigret runtime
        ↓
non-root execution
        ↓
bounded subprocess
```

## 4.2 OSINTgram

Treat OSINTgram independently.

`1.1.0-mock` remains an adapter compatibility marker, not a verified
upstream runtime.

For a real runtime:

-   pin an exact release or immutable commit;
-   document the revision;
-   install reproducibly;
-   verify the actual command interface;
-   keep relationship expansion disabled unless separately approved;
-   resolve authentication secrets only at execution time;
-   never store raw session secrets in DB records, task payloads, APIs,
    logs, traces, exports, or certification records.

If a reproducible runtime cannot be established:

``` text
OSINTgram → remains test_only
```

This must not block independent Maigret certification.

## 4.3 Dedicated connector worker

Preferred topology:

``` text
api
worker-core
worker-identity-enrichment
worker-osint-connectors
```

The connector worker should, where practical, use:

-   non-root execution;
-   no privileged mode;
-   no Docker socket;
-   no host filesystem mounts;
-   bounded memory and CPU;
-   bounded process count;
-   temporary writable workspaces only.

Do not claim sandboxing controls that are not actually configured.

------------------------------------------------------------------------

# 5. Phase B --- Canonical Runtime Fingerprint

Create or extend:

``` text
backend/app/services/discovery/connectors/runtime_fingerprint_service.py
```

Generate a deterministic SHA-256 fingerprint from non-secret runtime
metadata:

``` text
connector_type
adapter_version
runtime_version
runtime_revision
runtime_identity
parser_version
conformance_policy_version
```

Secrets, user identifiers, session IDs, and target usernames must never
enter the fingerprint.

Extend `ConnectorCertificationRecord` if necessary with:

``` text
runtime_fingerprint
conformance_policy_version
parser_version
live_smoke_status
live_smoke_at
invalidated_at
invalidation_reason
```

------------------------------------------------------------------------

# 6. Phase C --- Certification State Machine

Keep these concepts separate.

## Certification

``` text
NOT_RUN
PASSED
FAILED
STALE
```

## Live smoke status

``` text
NOT_RUN
PASSED
FAILED
NOT_REQUIRED
```

## Availability

``` text
test_only
installed_unverified
certification_failed
available
temporarily_unhealthy
disabled
```

Required transitions:

``` text
runtime absent
→ test_only

runtime detected + no valid certification
→ installed_unverified

conformance failed
→ certification = FAILED
→ availability = certification_failed

conformance passed
→ certification = PASSED

feature disabled
→ disabled

health circuit open
→ temporarily_unhealthy

all required gates satisfied
→ available
```

A previous certification becomes `STALE` when the adapter, runtime,
parser, policy, revision, or runtime fingerprint changes.

Historical certification records must be preserved.

------------------------------------------------------------------------

# 7. Phase D --- Operator Certification CLI

The canonical certification mechanism remains operator-triggered.

Implement or complete:

``` bash
python -m app.tools.certify_connectors --all
python -m app.tools.certify_connectors --connector maigret
python -m app.tools.certify_connectors --connector osintgram
python -m app.tools.certify_connectors --connector maigret --live-smoke
```

The CLI must:

1.  detect runtime;
2.  calculate runtime fingerprint;
3.  run offline conformance;
4.  persist certification result;
5.  optionally run an authorized live smoke test;
6.  print a secret-safe report;
7.  exit non-zero on certification failure.

Never print cookies, session IDs, authorization headers, raw environment
secrets, or credential-bearing command lines.

------------------------------------------------------------------------

# 8. Phase E --- Real Runtime Conformance

The conformance harness must work against installed runtimes and verify:

-   runtime detection;
-   runtime version parsing;
-   capability declaration;
-   strict argument construction;
-   option-injection resistance;
-   command-injection resistance;
-   safe process creation;
-   timeout enforcement;
-   process termination;
-   temporary workspace cleanup;
-   output-size enforcement;
-   malformed and partial output handling;
-   parser compatibility;
-   secret redaction;
-   execution-mode assignment;
-   normalized provenance;
-   deterministic error mapping.

Default conformance must not require a live social-media account.

------------------------------------------------------------------------

# 9. Phase F --- Controlled Live Smoke Tests

Keep:

``` text
enable_live_connector_smoke_tests = false
```

Live smoke testing requires all of:

``` text
feature explicitly enabled
+
operator explicitly invokes --live-smoke
+
offline conformance passed
+
authorized test identity configured
```

Use only operator-controlled or explicitly authorized test identities.

For Maigret:

-   one authorized username;
-   bounded execution;
-   strict timeout;
-   strict output limit;
-   no recursive expansion.

For OSINTgram:

-   operator-controlled test account;
-   profile lookup only;
-   relationship extraction disabled;
-   strict timeout and output limits.

Persist only safe smoke-test metadata:

``` text
connector
runtime_fingerprint
status
capability
started_at
completed_at
normalized_result_count
error_category
report_fingerprint
```

Never persist test credentials.

------------------------------------------------------------------------

# 10. Phase G --- Evidence Trust Model

`execution_mode` tells how an observation was produced. Sprint 23 must
also determine whether it is eligible for trusted production reasoning.

Recommended trust classes:

``` text
TEST_ONLY
LIVE_UNCERTIFIED
LIVE_CERTIFIED
USER_CONFIRMED
```

Rules:

``` text
mock or fixture
→ TEST_ONLY

live + missing/stale/invalid certification
→ LIVE_UNCERTIFIED

live + valid certification for observation runtime
→ LIVE_CERTIFIED

explicit user confirmation
→ USER_CONFIRMED
```

User confirmation remains distinct from connector certification.

------------------------------------------------------------------------

# 11. Phase H --- Certification Snapshot on Provenance

Every live observation must preserve enough metadata to answer:

> Which exact certified runtime produced this observation?

Extend provenance if required with:

``` text
connector_certification_id
runtime_fingerprint
adapter_version
runtime_version
```

Required behavior:

``` text
connector upgraded later
→ old observation remains tied to old runtime context
→ new observation uses new runtime context
```

Never retroactively certify historical observations using a newer
runtime.

------------------------------------------------------------------------

# 12. Phase I --- Evidence Promotion Rules

Before connector evidence enters the match engine:

``` text
provenance
    ↓
execution mode
    ↓
certification validity at observation time
    ↓
freshness
    ↓
EvidenceTrustPolicy
    ↓
eligible evidence
```

The following must not affect trusted production scoring:

-   mock observations;
-   fixture observations;
-   test-only runtime observations;
-   uncertified or stale-runtime observations unless an explicit
    conservative policy permits them.

Untrusted observations should normally remain auditable rather than
being silently deleted.

------------------------------------------------------------------------

# 13. Phase J --- Incremental Reassessment on Trust Changes

Certification changes can alter evidence eligibility.

Examples:

``` text
PASSED → STALE
FAILED → PASSED
```

Do not globally recompute every identity.

Required:

``` text
certification state changes
        ↓
find provenance linked to affected runtime fingerprint
        ↓
identify affected candidates
        ↓
recalculate assessment input fingerprints
        ↓
recalculate changed assessments only
        ↓
rebuild changed clusters only
```

Reuse the existing incremental reassessment architecture.

------------------------------------------------------------------------

# 14. Phase K --- Connector Execution Audit

If existing orchestration records are insufficient, add a user-scoped
execution audit model containing safe metadata such as:

``` text
connector_type
orchestration_run_id
plan_item_id
user_id
runtime_fingerprint
certification_id
execution_mode
capability
started_at
completed_at
outcome
normalized_result_count
error_category
timeout_occurred
output_truncated
```

Never store raw secrets, cookies, authorization headers, unbounded
stdout/stderr, or credential-bearing commands.

Avoid a new table if existing orchestration models can cleanly hold this
information.

------------------------------------------------------------------------

# 15. Phase L --- Health and Failure Classification

Normalize real connector failures:

``` text
configuration_error
runtime_unavailable
authentication_error
rate_limited
remote_unavailable
timeout
parser_incompatible
malformed_output
resource_limit
unknown
```

Health effects must be deliberate:

``` text
invalid user input
→ does not trip circuit breaker

repeated remote timeout
→ health failure

parser incompatibility
→ runtime/certification problem

missing operator secret
→ configuration problem
```

------------------------------------------------------------------------

# 16. Phase M --- Concurrency Controls

Add configurable connector concurrency limits, for example:

``` text
maigret_max_concurrent_runs
osintgram_max_concurrent_runs
max_connector_runs_per_user
```

Prefer Redis-backed distributed controls when multiple workers can
execute concurrently.

If the concurrency-control backend is unavailable:

``` text
do not allow unlimited execution
→ fail closed or safely defer
```

------------------------------------------------------------------------

# 17. Phase N --- Secret Boundary Verification

For OSINTgram and any authenticated connector, verify:

``` text
secret read only inside execution worker
secret not stored in DB
secret not in Celery payload
secret not returned by API
secret not in privacy export
secret not in certification records
secret not in execution audit
secret redacted from logs and exceptions
```

Add explicit regression tests using injected sentinel secret values.

------------------------------------------------------------------------

# 18. Phase O --- Connector Status API

Extend the existing certification endpoint or add a safe descriptor DTO.

Example:

``` json
{
  "connector": "maigret",
  "availability": "available",
  "certification_status": "PASSED",
  "health": "healthy",
  "runtime_version": "0.4.4",
  "adapter_version": "0.4.4-adapter",
  "live_smoke_status": "PASSED",
  "capabilities": ["username_discovery"],
  "last_certified_at": "..."
}
```

Do not expose secrets, raw environment values, unnecessary executable
paths, or internal stack traces.

------------------------------------------------------------------------

# 19. Phase P --- Frontend Connector Operations

Add:

``` text
frontend/src/features/discovery/ConnectorStatusPanel.tsx
```

Display:

-   connector name;
-   availability;
-   certification status;
-   runtime version;
-   health;
-   capabilities;
-   last certification time;
-   test-only/live status.

Safe labels:

``` text
Test only
Installed — verification required
Certified
Temporarily unavailable
Disabled
Certification failed
```

------------------------------------------------------------------------

# 20. Phase Q --- Evidence Origin Labels

Candidate and match-detail UI should distinguish:

``` text
Test data
Live observation
Certified live observation
User-confirmed profile
```

Use:

``` text
Observed by a certified connector
```

not:

``` text
Verified identity
```

Connector certification must never be presented as proof that the
discovered profile belongs to the user.

------------------------------------------------------------------------

# 21. Phase R --- Frontend Bundle Performance

Sprint 22 reported an initial JavaScript bundle of approximately:

``` text
1.26 MB
~374 kB gzip
```

Implement route-level lazy loading for at least:

-   Timeline;
-   Review Queue;
-   Identity Discovery;
-   Identity Clusters;
-   Connector Operations.

Run:

``` bash
npm run build
```

Report before and after:

``` text
initial entry bundle
largest lazy chunk
gzip sizes
```

The goal is measurable reduction of the initial application bundle
without a framework rewrite.

------------------------------------------------------------------------

# 22. Phase S --- AsyncMock Warning Cleanup

Sprint 22 reported one non-fatal `RuntimeWarning` involving `AsyncMock`.

Find and fix the actual await/mock issue.

Target:

``` text
0 failed
0 errors
0 unexpected RuntimeWarnings
```

Do not globally suppress the warning instead of fixing it.

------------------------------------------------------------------------

# 23. Phase T --- Privacy and Lifecycle

Classify every new record.

## User-linked records

If a record contains `user_id`, verify:

-   user-scoped access;
-   privacy export where appropriate;
-   shredding/account deletion.

## Operational records

Connector certification records are system/operator records and should
not be included in a user's identity export unless they contain
user-linked information.

Document the classification explicitly.

------------------------------------------------------------------------

# 24. Phase U --- API and RLS Boundaries

Add tests proving:

``` text
User A cannot access User B connector execution audit
User A cannot access User B orchestration details
User A cannot target User B candidate for revalidation
User A cannot alter/promote User B provenance
User A cannot access connector certification administration
```

Certification mutation remains operator-controlled.

------------------------------------------------------------------------

# 25. Phase V --- Migration Strategy

A Sprint 23 migration may be required for:

-   runtime fingerprint fields;
-   certification history fields;
-   provenance certification linkage;
-   execution audit records.

Verify:

``` text
fresh DB
→ alembic upgrade head
```

and:

``` text
Sprint 22 DB at 2ec027d8be5b
→ alembic upgrade head
```

Report starting head, Sprint 23 migration IDs, and final head.

------------------------------------------------------------------------

# 26. Required Automated Tests

## Runtime fingerprint

-   same metadata → same fingerprint;
-   adapter change → different fingerprint;
-   runtime change → different fingerprint;
-   parser/policy change → different fingerprint;
-   secrets never enter fingerprint.

## Certification

-   runtime absent → `test_only`;
-   runtime detected without certification → `installed_unverified`;
-   conformance failure → `certification_failed`;
-   conformance pass → `PASSED`;
-   runtime change → old certification `STALE`;
-   disabled feature → `disabled`;
-   open circuit → `temporarily_unhealthy`;
-   all gates satisfied → `available`.

## Live smoke gates

-   flag false → blocked;
-   flag true without explicit invocation → no smoke test;
-   failed offline conformance → blocked;
-   unauthorized target → blocked;
-   authorized target + explicit invocation → allowed.

All external execution must be mocked in the normal suite.

## Evidence trust

-   mock → `TEST_ONLY`;
-   fixture → `TEST_ONLY`;
-   live + uncertified → `LIVE_UNCERTIFIED`;
-   live + valid certification → `LIVE_CERTIFIED`;
-   user confirmation → `USER_CONFIRMED`.

## Scoring boundaries

-   mock evidence does not affect production score;
-   fixture evidence does not affect production score;
-   uncertified live evidence does not silently affect trusted score;
-   certified live evidence can enter normal evidence policy;
-   user confirmation remains distinct.

## Historical certification context

-   observation retains its runtime/certification context;
-   runtime upgrade does not rewrite old provenance;
-   new observation uses new runtime fingerprint.

## Incremental reassessment

-   unchanged certification → no reassessment;
-   certification becomes stale → affected candidates only;
-   certification becomes valid → affected candidates only;
-   unrelated candidates/users remain untouched.

## Failure classification

Test:

-   invalid input;
-   authentication error;
-   rate limit;
-   timeout;
-   missing runtime;
-   parser incompatibility;
-   malformed output.

## Concurrency

-   connector limit enforced;
-   per-user limit enforced;
-   duplicate orchestration suppressed;
-   concurrency backend unavailable → fail closed or safely defer.

## Secret leakage

Search sentinel secrets across:

-   logs;
-   exceptions;
-   Celery payloads;
-   API responses;
-   privacy exports;
-   certification records;
-   execution audits.

Expected: zero leaks.

## RLS

Test cross-user denial for:

-   execution audit;
-   targeted revalidation;
-   orchestration details;
-   candidate access.

------------------------------------------------------------------------

# 27. Real Runtime Certification Procedure

For each connector:

## Step 1 --- Install reproducibly

Build the actual connector worker image.

## Step 2 --- Detect runtime

Run:

``` bash
python -m app.tools.certify_connectors --connector <name>
```

Expected initial transition:

``` text
test_only → installed_unverified
```

## Step 3 --- Run offline conformance

Expected on success:

``` text
certification = PASSED
```

## Step 4 --- Optional authorized live smoke

Only when explicitly enabled:

``` bash
python -m app.tools.certify_connectors   --connector <name>   --live-smoke
```

## Step 5 --- Verify final availability

Only after all required gates:

``` text
availability = available
```

## Step 6 --- Bounded authorized orchestration

Verify:

``` text
execution_mode = live
runtime_fingerprint populated
certification linkage populated
provenance normalized
candidate remains unconfirmed
```

------------------------------------------------------------------------

# 28. Production Safety Test for Any Connector Claimed Available

Before a connector is described as production-live:

1.  Run it against an authorized test identity.
2.  Verify CandidateProfile creation/update.
3.  Verify `execution_mode = live`.
4.  Verify runtime fingerprint and certification linkage.
5.  Verify candidate is not auto-confirmed.
6.  Verify evidence trust classification.
7.  Verify deterministic assessment behavior.
8.  Verify privacy export behavior.
9.  Verify shredding behavior.
10. Verify zero secret leakage.

If this is not performed, the connector may be offline-certified but
must not be described as live-smoke verified.

------------------------------------------------------------------------

# 29. Required Implementation Order

``` text
1. Freeze Sprint 22 baseline.
2. Verify 95/95 tests.
3. Verify Alembic head 2ec027d8be5b.
4. Verify frontend production build.
5. Verify both connectors currently report test_only.
6. Audit canonical connector interfaces.
7. Audit worker/container topology.
8. Define reproducible runtime packaging.
9. Implement dedicated connector worker image if appropriate.
10. Implement runtime fingerprinting.
11. Extend certification persistence if required.
12. Implement certification invalidation.
13. Complete operator certification CLI.
14. Run offline conformance against installed runtimes.
15. Keep live smoke disabled by default.
16. Implement controlled live smoke framework.
17. Add provenance certification snapshot/linkage.
18. Implement EvidenceTrustPolicy.
19. Block mock/fixture evidence from production scoring.
20. Define uncertified-live evidence behavior.
21. Implement incremental reassessment on trust changes.
22. Add/extend safe connector execution audit.
23. Normalize failure categories.
24. Harden health integration.
25. Add connector concurrency controls.
26. Verify secret boundaries.
27. Add connector status API.
28. Add ConnectorStatusPanel.
29. Add evidence origin/trust labels.
30. Implement route-level code splitting.
31. Fix AsyncMock warning.
32. Update privacy/export/shred behavior where required.
33. Add RLS tests.
34. Add runtime fingerprint tests.
35. Add certification tests.
36. Add live-smoke gate tests.
37. Add evidence trust tests.
38. Add scoring-boundary tests.
39. Add historical certification tests.
40. Add incremental reassessment tests.
41. Add failure-classification tests.
42. Add concurrency tests.
43. Add secret-leakage tests.
44. Run full backend suite.
45. Run frontend production build.
46. Verify fresh DB migration.
47. Verify Sprint 22 → Sprint 23 upgrade.
48. If a real runtime is installed, certify it.
49. If explicitly authorized, run bounded live smoke.
50. Perform production safety test for any connector claimed available.
51. Produce final walkthrough.
52. Make GO / CONDITIONAL GO / NO-GO decision for Sprint 24.
```

------------------------------------------------------------------------

# 30. Definition of Done

Sprint 23 is complete only when:

### Regression

-   [ ] Sprint 22 baseline verified.
-   [ ] Full backend suite passes.
-   [ ] Frontend production build passes.
-   [ ] Alembic chain is linear.
-   [ ] AsyncMock warning is fixed or precisely justified.

### Runtime truthfulness

-   [ ] Adapter and runtime versions are distinct.
-   [ ] `1.1.0-mock` is not presented as a real OSINTgram runtime.
-   [ ] Runtime fingerprints are deterministic.
-   [ ] Certification is runtime-bound.
-   [ ] Runtime changes invalidate old certification.

### Certification

-   [ ] Operator CLI works.
-   [ ] Offline conformance works.
-   [ ] Certification is durable.
-   [ ] History is preserved.
-   [ ] Failure blocks availability.
-   [ ] Stale certification cannot silently remain available.

### Live execution

-   [ ] Live smoke remains disabled by default.
-   [ ] Explicit operator action is required.
-   [ ] Authorized test identities only.
-   [ ] Execution is bounded.
-   [ ] Normal pytest performs no live calls.

### Evidence trust

-   [ ] Mock and fixture evidence are classified.
-   [ ] Live uncertified evidence is distinguishable.
-   [ ] Certified live evidence is distinguishable.
-   [ ] User confirmation remains distinct.
-   [ ] Mock/fixture evidence cannot influence production scoring.
-   [ ] Historical provenance retains original execution mode.
-   [ ] Historical observations retain runtime/certification context.

### Operations

-   [ ] Failure categories normalized.
-   [ ] Health integration correct.
-   [ ] Concurrency limits enforced.
-   [ ] Budgets intact.
-   [ ] Idempotency intact.
-   [ ] Secret leakage tests pass.

### Frontend

-   [ ] Connector status UI implemented.
-   [ ] Test-only and certified-live states visible.
-   [ ] Evidence labels are safe and non-misleading.
-   [ ] Route-level code splitting implemented.
-   [ ] Before/after bundle sizes reported.

### Privacy and isolation

-   [ ] User-linked new records handled by export/shredding.
-   [ ] Operational certification records correctly classified.
-   [ ] Cross-user tests pass.

------------------------------------------------------------------------

# 31. GO / CONDITIONAL GO / NO-GO

## GO for Sprint 24

Allowed when:

``` text
P0 = 0
unresolved P1 = 0
full regression passes
frontend build passes
migration chain valid
evidence trust boundary verified
mock/fixture data blocked from production scoring
certification state truthful
secret leakage tests pass
```

A real connector does not have to be available for architectural GO if
its status is truthfully reported.

## CONDITIONAL GO

Appropriate when architecture and security pass but a connector remains:

``` text
test_only
or
installed_unverified
```

because live runtime deployment or authorized smoke testing remains
pending.

## NO-GO

Required if:

``` text
mock/fixture evidence affects production scoring
test-only connector executes in production
certification survives an incompatible runtime change
secrets leak
cross-user connector data is accessible
live smoke runs automatically
connector bypasses orchestration controls
P0 remains
unresolved P1 security defect remains
```

------------------------------------------------------------------------

# 32. Final Walkthrough Requirements

The final Sprint 23 walkthrough must explicitly report:

1.  Sprint 22 starting migration head.
2.  Sprint 23 migration ID(s).
3.  Final Alembic head.
4.  Baseline backend test count.
5.  Final backend test count.
6.  Failed/skipped/error/warning counts.
7.  Frontend build result.
8.  Initial bundle before Sprint 23.
9.  Initial bundle after Sprint 23.
10. Lazy chunks introduced.
11. AsyncMock warning disposition.
12. Canonical connector adapter interface location.
13. Worker/container topology.
14. Maigret adapter version.
15. Maigret actual runtime version.
16. Maigret runtime fingerprint.
17. Maigret certification status.
18. Maigret live smoke status.
19. Maigret final availability.
20. OSINTgram adapter version.
21. OSINTgram actual runtime version.
22. OSINTgram runtime fingerprint.
23. OSINTgram certification status.
24. OSINTgram live smoke status.
25. OSINTgram final availability.
26. Final disposition of `1.1.0-mock`.
27. Certification states.
28. Availability states.
29. Runtime fingerprint inputs.
30. Certification invalidation behavior.
31. Certification persistence.
32. Certification history behavior.
33. Certification CLI command.
34. Conformance checks executed.
35. Conformance failures found.
36. Minimal fixes applied.
37. Live smoke feature flag.
38. Live smoke authorization method.
39. Live smoke result, if run.
40. Confirmation that normal pytest makes no live calls.
41. Evidence trust classes.
42. Mock evidence scoring behavior.
43. Fixture evidence scoring behavior.
44. Uncertified-live evidence behavior.
45. Certified-live evidence behavior.
46. User-confirmed evidence behavior.
47. Provenance certification linkage.
48. Historical provenance immutability.
49. Incremental reassessment after trust changes.
50. Connector execution audit behavior.
51. Failure categories.
52. Health/circuit-breaker behavior.
53. Concurrency limits.
54. Budget enforcement result.
55. Idempotency result.
56. Secret storage policy.
57. Secret leakage test result.
58. Connector status API result.
59. Connector Status frontend result.
60. Evidence-label frontend result.
61. Privacy export result.
62. Shredding result.
63. RLS result.
64. Fresh DB migration result.
65. Sprint 22 DB upgrade result.
66. Real connector production safety test result, if applicable.
67. P0 issues.
68. P1 issues.
69. P2/P3 limitations.
70. GO / CONDITIONAL GO / NO-GO for Sprint 24.

------------------------------------------------------------------------

# 33. Expected End State

``` text
Identity Anchor
      ↓
Unified Connector Orchestrator
      ↓
Eligibility + Consent + Budget + Health
      ↓
Runtime Availability + Certification
      ↓
Bounded Connector Worker
      ↓
Normalized Provenance
      ↓
Execution Mode + Runtime Fingerprint
      ↓
Evidence Trust Policy
      ↓
Candidate Profile
      ↓
Deterministic Match Assessment
      ↓
Temporal Change Detection
      ↓
Human Review
      ↓
Optional User Confirmation
```

For every connector-derived observation, DigiZafe should be able to
answer:

``` text
Who owns this data boundary?
Which connector produced it?
Was execution mock, fixture, or live?
Which exact runtime produced it?
Was that runtime certified?
Was certification valid for that observation?
When was it observed?
Is it fresh?
Is it eligible for production scoring?
Has the user confirmed or dismissed it?
```

------------------------------------------------------------------------

# 34. Final Sprint 23 Principle

> Do not optimize for making a connector appear live. Optimize for
> making every claim about connector availability, runtime identity,
> provenance, and evidence trust demonstrably true.

A connector remaining `test_only` is acceptable.

A connector being incorrectly labeled `available` is not.
