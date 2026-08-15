# DigiZafe — Sprint 22 Implementation Guide

**Sprint:** 22 — Security Remediation, Temporal Integrity Completion, Production UI & Connector Runtime Certification  
**Applies after:** Sprint 21 — Temporal Evidence Timeline, Identity Change Detection & Human Review Queue  
**Primary goal:** Close the Sprint 21 security and verification gaps before extending the product UI, complete the temporal workflow, and establish a truthful certification boundary for real Maigret/OSINTgram runtimes.

---

# 1. Sprint 22 Is a Remediation-First Sprint

Sprint 21 added valuable temporal foundations, but the reported walkthrough contains two blocking inconsistencies that must be resolved before treating the baseline as production-ready.

## Blocking issue A — Revalidation bypasses budgets

The Sprint 21 walkthrough states:

```text
IdentityRevalidationService
→ skips standard budget policies
→ runs an immediate targeted scan
```

This violates the approved Sprint 20/21 invariant:

```text
manual revalidation
≠
budget bypass
```

Required architecture:

```text
Review Item
        ↓
IdentityRevalidationService
        ↓
ConnectorOrchestrationService
        ↓
Consent
Eligibility
Freshness policy
Budget
Health / circuit breaker
Runtime availability
Idempotency
Concurrency limits
        ↓
Execution Plan
```

Sprint 22 must remove any direct execution path that bypasses the canonical orchestration controls.

This is a **P1 security/resource-control defect** until verified fixed.

---

# 2. Blocking Issue B — Regression Count Dropped From 69 to 62

Sprint 20 preflight reported:

```text
69 tests passed
```

Sprint 21 completion reports:

```text
62 tests passed
```

A lower passing count is not automatically a regression, but it must be explained.

Sprint 22 must determine:

```text
Were 7 tests deleted?
Were tests renamed?
Were only unit tests run?
Were integration tests omitted?
Were tests deselected?
Were collection failures hidden?
Did the command differ?
```

Required:

```text
pytest tests/ -ra
```

Record:

```text
collected
passed
failed
skipped
xfailed
xpassed
deselected
errors
```

Do not claim full regression success until the test-count discrepancy is reconciled.

---

# 3. Sprint 21 Baseline Preflight

Before new feature work, verify:

```text
alembic heads
alembic current
alembic history
pytest tests/ -ra
frontend production build
```

Expected known migration:

```text
Sprint 20 starting head:
31ae10448288

Sprint 21 migration:
a5857207f85b
```

Verify the actual final head from the repository.

Also verify that the migration filename and revision metadata match.

---

# 4. Sprint 21 Verification Matrix

Classify every item as:

```text
VERIFIED
PARTIAL
NOT_IMPLEMENTED
DEFECT
TEST_ONLY
```

Verify:

```text
IdentityChangeEvent model
IdentityReviewItem model
IdentityReviewItemEvent association
event idempotency
review grouping
absence suspected state
confirmed disappearance policy
reappearance handling
avatar supersession
bio supersession
out-of-order observation handling
connector failure vs disappearance
review resolution concurrency
revalidation orchestration
revalidation budget enforcement
revalidation health enforcement
revalidation availability enforcement
automatic revalidation default
automatic revalidation cooldown
incremental reassessment
incremental cluster rebuild
privacy export
privacy shredding
RLS
timeline API pagination
review API pagination
frontend timeline implementation
frontend review queue implementation
```

Do not infer implementation from file names alone.

---

# 5. Sprint 22 Goal

After remediation, Sprint 22 should deliver:

```text
Secure canonical revalidation
        +
Complete temporal integrity
        +
Production-quality Timeline UI
        +
Production-quality Review Queue UI
        +
Connector Runtime Conformance Harness
        +
Truthful runtime certification
```

Target architecture:

```text
Identity Timeline
        ↓
Human Review Queue
        ↓
User Requests Revalidation
        ↓
Canonical Orchestrator
   ├── Consent
   ├── Budget
   ├── Health
   ├── Availability
   ├── Idempotency
   └── Concurrency
        ↓
Certified Connector Runtime
        ↓
Provenance Observation
        ↓
Temporal Change Detection
        ↓
Incremental Reassessment
        ↓
Affected Cluster Rebuild
```

---

# 6. Scope

Sprint 22 includes:

```text
P1 revalidation remediation
full regression reconciliation
temporal-state conformance audit
production Timeline UI
production Review Queue UI
review detail experience
revalidation status experience
connector runtime registry hardening
connector conformance harness
runtime certification records
controlled live smoke-test framework
mock/live evidence separation
observability
privacy and RLS regression
```

Sprint 22 does not include:

```text
new OSINT connectors
unbounded monitoring
automatic identity confirmation
automatic compromise conclusions
facial recognition
cross-user identity correlation
credential harvesting
platform-protection bypasses
```

---

# 7. Phase A — Fix Revalidation Budget Bypass

Modify:

```text
IdentityRevalidationService
```

It must not directly invoke:

```text
Maigret task
OSINTgram task
connector adapter
raw Celery connector task
```

Instead:

```text
IdentityRevalidationService.request_revalidation(...)
        ↓
ConnectorOrchestrationService.create_orchestration_run(...)
```

The orchestration request should carry a bounded purpose:

```text
purpose = temporal_revalidation
```

and target scope:

```text
canonical_fact_key
candidate_profile_id
requested capability
```

The orchestrator remains the final authority.

---

# 8. Manual Revalidation Policy

Manual revalidation may receive different product limits from automatic revalidation, but it may not be unlimited.

Recommended initial policy:

```text
manual revalidations per user:
10 per hour
30 per day

same canonical fact:
minimum 5-minute duplicate suppression

maximum active equivalent revalidation:
1
```

These values must be configurable.

If Sprint 20 already has stricter global limits, the effective result should be the stricter applicable policy unless explicitly designed otherwise.

---

# 9. Automatic Revalidation Policy

Keep:

```text
FEATURE_AUTOMATIC_REVALIDATION=false
```

by default.

Recommended:

```text
same canonical fact automatic cooldown:
24 hours
```

Automatic execution must still obey:

```text
consent
budget
health
availability
idempotency
```

---

# 10. Revalidation Reason Codes

Use strict reason codes:

```text
USER_REQUESTED
ABSENCE_CONFIRMATION
HIGH_MATERIALITY_CHANGE
CONTRADICTION_REFRESH
STALE_CONFIRMED_PROFILE
```

Do not accept arbitrary connector commands from the frontend.

---

# 11. Revalidation Plan Decisions

Expose safe orchestration decisions:

```text
execute
skip_fresh
skip_budget
skip_unhealthy
skip_unavailable
skip_test_only
skip_duplicate
skip_no_consent
skip_ineligible
defer_runtime_control_unavailable
```

The review item remains unresolved when revalidation cannot produce a valid observation.

---

# 12. Revalidation Result Semantics

Required:

```text
connector completed successfully with valid observation
→ eligible temporal input

connector completed successfully with valid no-result
→ absence policy input

connector failed
→ operational uncertainty

connector timed out
→ operational uncertainty

connector unavailable
→ no identity conclusion

budget blocked
→ no identity conclusion

test_only blocked
→ no identity conclusion
```

---

# 13. Phase B — Temporal Integrity Completion

Audit Sprint 21 against the approved temporal model.

Required canonical change types:

```text
FACT_APPEARED
FACT_VALUE_CHANGED
FACT_BECAME_STALE
FACT_EXPIRED
FACT_ABSENCE_SUSPECTED
FACT_DISAPPEARED
FACT_REAPPEARED
FACT_SUPERSEDED
CONTRADICTION_ADDED
CONTRADICTION_RESOLVED
USER_DECISION_CHANGED
```

If Sprint 21 only implemented:

```text
APPEARED
DISAPPEARED
MODIFIED
```

expand the model safely.

Use a migration only if database enum/storage constraints require it.

---

# 14. Absence State Machine

Required:

```text
PRESENT
   ↓
successful eligible observation misses fact
   ↓
ABSENT_UNCONFIRMED
   ↓
FACT_ABSENCE_SUSPECTED
   ↓
policy-compliant successful revalidation
   ↓
ABSENT_CONFIRMED
   ↓
FACT_DISAPPEARED
```

Never:

```text
connector failure
→ disappeared
```

---

# 15. Avatar Replacement

Required:

```text
old avatar
→ superseded

new avatar
→ current

event
→ FACT_VALUE_CHANGED
```

Not:

```text
old avatar
→ disappeared
```

Avatar change remains weak contextual evidence and does not imply a different person.

---

# 16. Bio Replacement

Required:

```text
old bio
→ superseded

new bio
→ current

event
→ FACT_VALUE_CHANGED
```

---

# 17. External Link Removal

Initial policy:

```text
first successful absence
→ FACT_ABSENCE_SUSPECTED

second successful absence
separated by at least 12 hours
→ FACT_DISAPPEARED
```

Configurable and versioned.

---

# 18. Profile Disappearance

Initial policy:

```text
2 successful eligible revalidation attempts
separated by at least 24 hours
```

before:

```text
FACT_DISAPPEARED
```

---

# 19. Reappearance

Required:

```text
confirmed absent fact
+
later valid observation
→ FACT_REAPPEARED
```

Historical disappearance remains preserved.

---

# 20. Out-of-Order Observations

Required policy:

```text
older observation arrives after newer current state
→ preserve provenance
→ do not roll current state backward solely because it was inserted later
```

Use:

```text
observed_at
run lineage
detected_at
```

not database insertion order alone.

---

# 21. Event Idempotency

Use deterministic:

```text
event_fingerprint
```

based on:

```text
user scope
canonical_fact_key
change type
previous state/value fingerprint
new state/value fingerprint
change policy version
```

Required:

```text
worker retry
→ no duplicate event

duplicate provenance
→ no duplicate transition
```

---

# 22. Phase C — Reassessment Safety

The Sprint 21 summary states:

```text
Medium, High, or Critical changes
→ review queue

material changes
→ immediate IdentityMatchEngine reassessment
→ cluster recalculation
```

Audit this carefully.

Required architecture:

```text
IdentityChangeEvent
        ↓
Materiality Policy
        ↓
IdentityReassessmentCoordinator
        ↓
assessment input fingerprint
        ↓
recalculate only if fingerprint changed
        ↓
affected cluster dependency scope
        ↓
cluster input fingerprint
        ↓
rebuild only if changed
```

Do not call the Match Engine and Cluster Service blindly on every event.

---

# 23. Review Threshold vs Reassessment Threshold

These are separate policies.

Example:

```text
medium change
→ may create review item

medium change
→ may or may not alter assessment input
```

Required:

```text
review creation
≠
automatic score recalculation
```

Recalculate only when the canonical evidence input materially changed.

---

# 24. Phase D — Production Timeline UI

Replace the Sprint 21 `TimelinePage` stub with a production-quality interface.

Create or complete:

```text
TimelinePage.tsx
IdentityTimelineView.tsx
TimelineEventCard.tsx
TimelineFilters.tsx
TimelineEventDetails.tsx
```

---

# 25. Timeline UI Requirements

Display:

```text
safe event title
affected profile
detected time
observation confidence
materiality
review status
provenance source
```

Expandable detail:

```text
previous state
new state
why the event was generated
observation lineage
limitations
downstream assessment impact
```

---

# 26. Timeline Filters

Support:

```text
change type
materiality
candidate profile
review status
date range
```

All server-side queries remain user-scoped.

---

# 27. Timeline Pagination

Use:

```text
bounded cursor pagination
```

Recommended:

```text
default page size = 20
maximum = 100
```

Stable ordering:

```text
detected_at DESC
id DESC
```

or equivalent deterministic cursor ordering.

---

# 28. Timeline Safe Language

Examples:

```text
Observed username change

Avatar changed

A previously observed link is no longer present in repeated successful observations

This profile may be unavailable and needs revalidation

A conflicting signal was detected
```

Never infer:

```text
account hacked
identity stolen
different person
```

without separate evidence.

---

# 29. Phase E — Production Review Queue UI

Replace the `ReviewQueuePage` stub.

Create or complete:

```text
ReviewQueuePage.tsx
IdentityReviewQueue.tsx
ReviewItemCard.tsx
ReviewDetailDrawer.tsx
RevalidationStatus.tsx
```

---

# 30. Review Queue Requirements

Display:

```text
priority
review type
affected profile
reason
related timeline events
created time
current status
available actions
```

Actions:

```text
ACKNOWLEDGED
THIS_IS_STILL_MINE
THIS_IS_NOT_MINE
EXPECTED_CHANGE
REQUEST_REVALIDATION
DISMISS_ALERT
```

Use strict backend enums.

---

# 31. Grouped Review Events

Because Sprint 21 created:

```text
IdentityReviewItemEvent
```

the UI must show all related timeline events.

Example:

```text
Review: Profile information changed

Related events:
- Avatar changed
- Bio changed
- External link added
```

Do not hide individual history.

---

# 32. Revalidation UX

When the user requests revalidation:

```text
Review Item
        ↓
Orchestration Run
```

Show:

```text
queued
planning
running
partial_result
completed
no_action
failed
```

Show safe connector plan states.

Do not expose secrets.

---

# 33. Revalidation Blocked UX

Examples:

```text
Revalidation could not start because the execution budget was reached.

The connector is temporarily unavailable.

A matching revalidation is already running.

The available connector is test-only in this environment.

Consent is required before external discovery can run.
```

---

# 34. Review Resolution Concurrency

The UI must handle:

```text
409 conflict
already resolved
superseded review
```

without duplicating actions.

---

# 35. Phase F — Connector Runtime Certification

The system currently has a historical gap:

```text
adapter architecture verified
≠
real connector runtime verified
```

Sprint 22 introduces a formal certification boundary.

---

# 36. Connector Availability States

Canonical states:

```text
test_only
installed_unverified
certification_failed
available
temporarily_unhealthy
disabled
```

Do not use:

```text
available
```

for a connector merely because its adapter imports successfully.

---

# 37. Connector Descriptor

The registry should expose:

```text
connector_type
adapter_version
runtime_version nullable
runtime_revision nullable
availability
capabilities
queue
timeout
output_limit
health_policy
certification_status
last_certified_at nullable
```

No secrets.

---

# 38. Runtime Version Detection

Each adapter should implement a bounded method such as:

```text
detect_runtime()
```

It may verify:

```text
binary exists
version command succeeds
expected executable identity
```

Do not execute arbitrary user input.

---

# 39. Connector Conformance Harness

Create:

```text
ConnectorConformanceHarness
```

It should test adapters against a common contract.

Required checks:

```text
runtime detection
capability declaration
strict argument construction
shell=False / create_subprocess_exec
timeout behavior
process cleanup
output size limit
temporary workspace cleanup
parser behavior
malformed output handling
secret redaction
normalized provenance output
test-only blocking
```

---

# 40. Conformance Result

Create a domain object or persisted record:

```text
ConnectorCertificationResult
```

Suggested fields:

```text
connector_type
adapter_version
runtime_version
runtime_revision
environment
certification_status
checks_passed
checks_failed
certified_at
report_fingerprint
```

Do not store credentials.

Persistence is recommended if runtime certification affects availability.

---

# 41. Certification Status

Use:

```text
NOT_RUN
PASSED
FAILED
STALE
```

A runtime change should invalidate previous certification:

```text
runtime version/revision changed
→ certification = STALE
```

---

# 42. Availability Gate

Required:

```text
runtime installed
+
certification passed
+
feature enabled
+
health acceptable
→ available
```

Not:

```text
binary exists
→ available
```

---

# 43. Maigret Certification

Verify:

```text
actual installed runtime
actual version
supported CLI arguments
structured output behavior
timeout
process cleanup
parser compatibility
provenance normalization
```

Do not assume compatibility from a Python package version alone.

---

# 44. OSINTgram Certification

OSINTgram is more operationally fragile because of authentication/session requirements.

Verify:

```text
actual source/runtime revision
supported commands
session injection boundary
secret redaction
output parsing
timeout
process cleanup
capability support
```

Do not label:

```text
1.1.0-mock
```

as a real runtime version.

If still mocked:

```text
runtime_version = null
availability = test_only
```

---

# 45. Upstream Pinning

For real connector packaging, prefer:

```text
immutable package version
```

or:

```text
immutable commit SHA
```

Avoid:

```text
latest
main
master
```

for production certification.

---

# 46. Reproducible Runtime

Prefer dedicated immutable runtime packaging.

Possible architecture:

```text
api
worker
connector runtime image
```

or a securely pinned worker image.

Do not dynamically install arbitrary upstream code during a user request.

---

# 47. Dedicated Connector Isolation

Evaluate whether real connector execution should remain inside the general worker.

Preferred production direction:

```text
OSINT connector worker
        ↓
restricted queue
restricted environment
bounded filesystem
bounded process execution
no unnecessary application secrets
```

Sprint 22 may document a migration path if full container isolation is not yet implemented.

---

# 48. Controlled Live Smoke Testing

Live smoke tests must be:

```text
explicitly enabled
environment-gated
operator-controlled
bounded
non-recursive
using authorized test identities/accounts
```

Do not run live smoke tests automatically in the normal unit test suite.

---

# 49. Live Test Flag

Add:

```text
ENABLE_LIVE_CONNECTOR_SMOKE_TESTS=false
```

default:

```text
false
```

---

# 50. Live Smoke Test Requirements

A live smoke test should verify only:

```text
runtime starts
authorized bounded query executes
output parses
provenance normalizes
no secret appears in logs
process exits cleanly
```

It should not perform broad or recursive collection.

---

# 51. Mock vs Live Provenance

Every provenance observation should preserve:

```text
execution_mode
```

Possible:

```text
mock
fixture
live
```

Required:

```text
mock/fixture observation
→ cannot masquerade as live evidence
```

---

# 52. Production Evidence Gate

In production:

```text
execution_mode != live
```

must not be presented as real-world evidence.

Test environments may display it clearly as:

```text
TEST OBSERVATION
```

---

# 53. Certification and Orchestration

The orchestrator should consume registry status:

```text
test_only
→ skip_test_only

installed_unverified
→ skip_unavailable

certification_failed
→ skip_unavailable

available
→ eligible subject to other policies

temporarily_unhealthy
→ skip_unhealthy
```

---

# 54. Certification Is Not Health

Required distinction:

```text
certification
→ runtime contract is valid

health
→ runtime is currently operational
```

A certified connector may become temporarily unhealthy.

---

# 55. Certification Is Not Consent

Required:

```text
certified connector
≠
permission to run
```

Consent remains independently enforced.

---

# 56. Phase G — Observability

Add metrics for:

```text
revalidation_requests_total
revalidation_blocked_total by reason
temporal_events_total by type
review_items_total by priority
review_resolutions_total by resolution
connector_certification_runs_total
connector_certification_failures_total
connector_live_smoke_tests_total
```

Avoid user IDs as metric labels.

---

# 57. Audit Events

Recommended:

```text
identity_revalidation_requested
identity_revalidation_blocked
identity_revalidation_started
identity_revalidation_completed
connector_certification_started
connector_certification_passed
connector_certification_failed
connector_runtime_status_changed
```

No secrets.

---

# 58. Privacy

Extend export only if new user-scoped data is introduced.

Certification records are generally operational/system records, not user identity data.

Do not include:

```text
operator credentials
session IDs
environment secrets
raw connector command environments
```

---

# 59. RLS

Mandatory tests:

```text
User A cannot read User B timeline
User A cannot read User B review
User A cannot resolve User B review
User A cannot revalidate User B fact
User A cannot access User B orchestration linkage
```

Connector certification endpoints, if exposed, should be admin/operator-scoped or read-only sanitized status as appropriate.

---

# 60. API Routes

Preserve existing Sprint 21 routes if already canonical:

```text
GET  /api/v1/temporal/timeline
GET  /api/v1/temporal/reviews
POST /api/v1/temporal/reviews/{id}/resolve
POST /api/v1/temporal/reviews/{id}/revalidate
```

Add detail endpoints if absent:

```text
GET /api/v1/temporal/timeline/{event_id}
GET /api/v1/temporal/reviews/{review_id}
```

Do not rename working routes solely for aesthetics.

---

# 61. Connector Status API

Suggested sanitized endpoint:

```text
GET /api/v1/discovery/connectors
```

Return:

```text
connector
availability
runtime version if safe
certification status
health status
capabilities
```

No secrets.

---

# 62. Certification API

Prefer operator-only or CLI/management command execution.

Possible:

```text
python -m app.tools.certify_connectors
```

Do not expose an unrestricted public endpoint that launches arbitrary runtime certification.

---

# 63. Required Security Tests

```text
manual revalidation
→ budget enforced

automatic revalidation
→ budget enforced

revalidation
→ health enforced

revalidation
→ consent enforced

revalidation
→ test_only blocked in production

duplicate revalidation
→ idempotent

User A
→ cannot revalidate User B fact

connector adapter
→ no shell injection

connector certification
→ no secret leakage

mock provenance
→ cannot appear as live production evidence
```

---

# 64. Required Regression Reconciliation

Produce a test inventory.

Compare:

```text
Sprint 20:
69 passed

Sprint 21:
62 passed
```

Report exactly why.

Acceptable explanations include:

```text
test files intentionally consolidated
tests renamed
test command differed
```

But the final Sprint 22 suite must run the full canonical command.

---

# 65. Required Temporal Tests

```text
unchanged fact
→ no event

first valid absence
→ absence suspected

connector failure
→ no disappearance

partial result
→ no disappearance

policy-confirmed absence
→ disappeared

new avatar
→ old superseded

new bio
→ old superseded

reappearance
→ reappeared event

out-of-order observation
→ no rollback

worker retry
→ no duplicate event
```

---

# 66. Required Review Tests

```text
related events
→ grouped review

different review type
→ separate review context

all grouped events remain linked

concurrent resolution
→ one final resolution

THIS_IS_STILL_MINE
→ canonical service

THIS_IS_NOT_MINE
→ canonical service

REQUEST_REVALIDATION
→ canonical orchestration
```

---

# 67. Required Reassessment Tests

```text
review item created
→ does not itself force score change

non-material evidence input unchanged
→ no assessment

material evidence fingerprint changed
→ affected assessment recalculated

same assessment fingerprint
→ no duplicate history

unrelated candidate
→ unchanged
```

---

# 68. Required Cluster Tests

```text
assessment unchanged
→ no cluster rebuild

affected cluster fingerprint unchanged
→ no rebuild

affected cluster fingerprint changed
→ bounded rebuild

unrelated cluster
→ unchanged

transitive conflict trap
→ preserved

incremental result
→ equivalent to full rebuild
```

---

# 69. Required Connector Conformance Tests

For every adapter:

```text
runtime unavailable
runtime version detection
strict argument validation
option injection
command injection
timeout
process kill
temporary directory cleanup
oversized output
malformed output
partial output
secret redaction
normalization
mock/live execution mode
```

---

# 70. Required Certification Tests

```text
runtime absent
→ NOT_RUN / unavailable

runtime installed but certification not run
→ installed_unverified

certification fails
→ certification_failed

certification passes
→ available subject to feature/health

runtime version changes
→ certification stale
```

---

# 71. Fresh Database Verification

Run:

```text
alembic upgrade head
```

against a fresh database.

Verify all migrations from Sprint 0 through Sprint 22 apply linearly.

---

# 72. Existing Database Verification

Upgrade a representative Sprint 21 database to Sprint 22.

Verify:

```text
no data loss
temporal events preserved
review links preserved
orchestration links preserved
```

---

# 73. Frontend Build

Run the canonical production build command.

Report exact result.

Do not report only Docker image build success if the actual frontend compilation command can be run directly.

---

# 74. Full Backend Regression

Run:

```text
pytest tests/ -ra
```

Report:

```text
collected
passed
failed
skipped
xfailed
xpassed
deselected
errors
```

---

# 75. P0/P1 Policy

P0 examples:

```text
cross-user temporal data exposure
cross-user review action
secret leakage
```

P1 examples:

```text
revalidation bypasses budget
revalidation bypasses consent
test-only data shown as live evidence
connector failure creates disappearance
duplicate execution bypasses idempotency
```

No GO with unresolved P0.

No GO with unresolved P1 unless explicitly accepted through a documented engineering decision.

---

# 76. Implementation Order

```text
1. Freeze Sprint 21 repository state.
2. Verify actual Alembic head.
3. Reconcile 69 vs 62 test counts.
4. Audit Sprint 21 implementation against the approved guide.
5. Classify VERIFIED/PARTIAL/NOT_IMPLEMENTED/DEFECT/TEST_ONLY.
6. Reproduce revalidation budget bypass.
7. Add regression test for the bypass.
8. Route revalidation through ConnectorOrchestrationService.
9. Verify consent, budget, health, availability, idempotency.
10. Verify manual and automatic revalidation policies.
11. Complete absence-suspected state if missing.
12. Complete disappearance confirmation if missing.
13. Complete reappearance if missing.
14. Verify avatar supersession.
15. Verify bio supersession.
16. Verify out-of-order handling.
17. Verify event idempotency.
18. Audit reassessment trigger behavior.
19. Ensure assessment fingerprint gating.
20. Audit cluster rebuild behavior.
21. Ensure cluster fingerprint gating.
22. Replace TimelinePage stub.
23. Implement timeline filters and pagination.
24. Implement timeline detail UI.
25. Replace ReviewQueuePage stub.
26. Implement grouped review detail UI.
27. Implement revalidation status UI.
28. Implement safe blocked-state messaging.
29. Harden connector availability states.
30. Implement runtime detection.
31. Implement ConnectorConformanceHarness.
32. Implement certification result model/state if required.
33. Implement certification invalidation on runtime change.
34. Add controlled live smoke-test framework.
35. Keep live smoke tests disabled by default.
36. Preserve mock/live provenance separation.
37. Add observability.
38. Verify privacy export.
39. Verify shredding.
40. Run RLS tests.
41. Run temporal tests.
42. Run review tests.
43. Run revalidation security tests.
44. Run reassessment tests.
45. Run cluster tests.
46. Run connector conformance tests.
47. Run full backend regression.
48. Run frontend production build.
49. Verify fresh DB migration.
50. Verify existing DB upgrade.
51. Produce final walkthrough.
52. Make GO / CONDITIONAL GO / NO-GO decision for Sprint 23.
```

---

# 77. Final Walkthrough Requirements

Report:

1. Sprint 21 starting migration head.
2. Sprint 22 migration ID, if any.
3. Final Alembic head.
4. Exact explanation for 69 vs 62 tests.
5. Preflight full test inventory.
6. Final full test inventory.
7. Frontend build result.
8. Sprint 21 verification matrix.
9. Revalidation bypass reproduction.
10. Revalidation bypass fix.
11. Regression test for budget enforcement.
12. Manual revalidation limits.
13. Automatic revalidation limits.
14. Revalidation cooldown.
15. Consent enforcement result.
16. Budget enforcement result.
17. Health enforcement result.
18. Availability enforcement result.
19. Idempotency result.
20. Revalidation orchestration linkage.
21. Temporal states.
22. Change types.
23. Absence-suspected behavior.
24. Disappearance confirmation policy.
25. Reappearance behavior.
26. Avatar supersession.
27. Bio supersession.
28. External-link removal policy.
29. Out-of-order observation policy.
30. Event idempotency result.
31. Review grouping behavior.
32. Review-event association behavior.
33. Review resolution concurrency.
34. Reassessment trigger policy.
35. Assessment fingerprint behavior.
36. Cluster fingerprint behavior.
37. Incremental/full cluster equivalence.
38. Timeline UI components.
39. Timeline filters.
40. Timeline pagination.
41. Timeline detail behavior.
42. Review Queue UI components.
43. Review detail behavior.
44. Revalidation UX.
45. Safe language examples.
46. Connector registry availability states.
47. Maigret adapter version.
48. Maigret runtime version.
49. Maigret runtime revision.
50. Maigret certification status.
51. OSINTgram adapter version.
52. OSINTgram runtime version.
53. OSINTgram runtime revision.
54. OSINTgram certification status.
55. Meaning/status of any remaining `1.1.0-mock`.
56. ConnectorConformanceHarness checks.
57. Runtime version detection.
58. Certification invalidation behavior.
59. Live smoke-test feature flag.
60. Live smoke-test execution result, if explicitly enabled.
61. Mock/live provenance separation.
62. Test-only production blocking.
63. Connector secret-redaction tests.
64. Privacy export result.
65. Shred/account deletion result.
66. RLS result.
67. Temporal regression result.
68. Review regression result.
69. Revalidation regression result.
70. Sprint 20 orchestration regression.
71. Sprint 20 budget regression.
72. Sprint 20 health regression.
73. Sprint 20 freshness regression.
74. Sprint 19 secret-boundary regression.
75. Sprint 18 enrichment/clustering regression.
76. Sprint 17 match-engine regression.
77. Sprint 16 discovery regression.
78. Sprint 15 Identity Anchor regression.
79. Sprint 14 security regression.
80. PDSS regression.
81. Fresh database migration result.
82. Existing database upgrade result.
83. P0–P3 issues found.
84. Minimal fixes applied.
85. Files created or modified.
86. Remaining limitations.
87. GO / CONDITIONAL GO / NO-GO decision for Sprint 23.

Do not predetermine GO.

---

# 78. Definition of Done

## Security Remediation

- [ ] Revalidation no longer bypasses budgets.
- [ ] Revalidation no longer bypasses canonical orchestration.
- [ ] Consent enforced.
- [ ] Health/circuit breaker enforced.
- [ ] Runtime availability enforced.
- [ ] Idempotency enforced.
- [ ] Concurrent duplicate revalidation suppressed.
- [ ] P1 regression test added.

## Regression Integrity

- [ ] 69 vs 62 discrepancy explained.
- [ ] Full canonical test command executed.
- [ ] Exact collection/pass/fail/skip counts reported.
- [ ] No hidden collection errors.
- [ ] Frontend production build passes.

## Temporal Integrity

- [ ] Absence suspected distinct from disappearance.
- [ ] Connector failure cannot create disappearance.
- [ ] Partial result cannot create disappearance.
- [ ] Reappearance supported.
- [ ] Avatar replacement uses supersession.
- [ ] Bio replacement uses supersession.
- [ ] Out-of-order observations cannot roll state backward.
- [ ] Event retries are idempotent.

## Reassessment / Clustering

- [ ] Review creation does not blindly force scoring.
- [ ] Assessment input fingerprint gates recalculation.
- [ ] Only affected candidate reassessed.
- [ ] Cluster input fingerprint gates rebuild.
- [ ] Only affected cluster scope rebuilt.
- [ ] Incremental/full equivalence passes.
- [ ] Transitive conflict safety passes.

## Timeline UI

- [ ] Sprint 21 stub replaced.
- [ ] Paginated timeline implemented.
- [ ] Filters implemented.
- [ ] Event details implemented.
- [ ] Safe language used.
- [ ] Provenance displayed safely.

## Review Queue UI

- [ ] Sprint 21 stub replaced.
- [ ] Grouped events visible.
- [ ] Strict review actions implemented.
- [ ] Revalidation status visible.
- [ ] Blocked states explained safely.
- [ ] Concurrent resolution handled.

## Connector Certification

- [ ] Availability states canonical.
- [ ] Runtime detection implemented.
- [ ] Conformance harness implemented.
- [ ] Certification status implemented.
- [ ] Runtime changes invalidate certification.
- [ ] Mock runtime not labeled live.
- [ ] Live smoke tests disabled by default.
- [ ] Live smoke tests use authorized bounded targets only.
- [ ] Secrets absent from certification logs/results.

## Privacy / RLS

- [ ] Export passes.
- [ ] Shredding passes.
- [ ] User A cannot read User B timeline.
- [ ] User A cannot read User B review.
- [ ] User A cannot resolve User B review.
- [ ] User A cannot revalidate User B fact.
- [ ] No secrets exposed.

---

# 79. GO / NO-GO Gate for Sprint 23

## GO

Proceed only when:

```text
revalidation budget bypass fixed
full regression count reconciled
P0 = 0
P1 = 0 or explicitly accepted
temporal absence semantics verified
event idempotency verified
review concurrency verified
assessment fingerprint gating verified
cluster fingerprint gating verified
production Timeline UI complete
production Review Queue UI complete
mock/live evidence separation verified
connector runtime status truthful
privacy and RLS pass
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
cross-user isolation
secret security
consent
budget enforcement
connector execution control
temporal integrity
review decision integrity
mock/live truthfulness
privacy
```

## NO-GO

Do not proceed with:

```text
revalidation bypassing budgets
revalidation bypassing consent
unexplained regression-test disappearance
connector failure interpreted as disappearance
mock data shown as live evidence
uncertified runtime marked available
duplicate temporal events from retries
blind reassessment on every review item
full graph rebuild on every temporal event
broken cross-user isolation
unresolved P0
unaccepted P1
```

---

# 80. Recommended Sprint 23 Direction

After Sprint 22 closes the security and runtime-verification gaps, Sprint 23 should focus on:

```text
Operational Production Readiness
+
Deployment Hardening
+
Background Job Reliability
+
Observability & SLOs
+
Backup / Restore
+
Disaster Recovery
+
Release Candidate Audit
```

Possible architecture:

```text
Verified Application Baseline
        ↓
Production Configuration Validation
        ↓
Queue Reliability / Retry Policy
        ↓
Database Backup & Restore Drill
        ↓
Secrets Rotation Drill
        ↓
Observability / Alerting
        ↓
Load & Failure Testing
        ↓
Release Candidate Security Audit
        ↓
Production Readiness Decision
```

---

# 81. Final Sprint 22 Principle

Sprint 22 must not treat a larger UI or a real connector binary as proof of production readiness.

The system must preserve this chain:

```text
User requests review or revalidation
        ↓
Canonical policy decides whether execution is allowed
        ↓
Only certified and healthy runtimes may execute
        ↓
Every observation preserves execution mode and provenance
        ↓
Temporal logic distinguishes change from operational failure
        ↓
Only materially changed evidence triggers reassessment
        ↓
Only affected clusters are rebuilt
        ↓
The user remains the authority for identity decisions
```

The critical correction is:

```text
targeted revalidation
≠
privileged bypass
```

A targeted scan may be narrower, but it must remain governed by:

```text
consent
budget
health
availability
idempotency
```

Sprint 22 is complete when DigiZafe has corrected the Sprint 21 revalidation bypass, reconciled the full regression baseline, completed the temporal and review user experience, preserved deterministic incremental processing, and established a truthful certification boundary between mocked connector architecture and genuinely verified runtime execution.

---

**End of Sprint 22 Implementation Guide**
