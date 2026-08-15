# DigiZafe — Sprint 20 Implementation Guide

**Sprint:** 20 — Unified Multi-Connector Orchestration, Evidence Freshness & Incremental Reassessment  
**Applies after:** Sprint 19 — OSINTgram Discovery Integration  
**Primary goal:** Turn Maigret, OSINTgram, and future approved connectors into one policy-driven orchestration layer with explicit budgets, freshness, idempotency, health-aware execution, and incremental deterministic reassessment.

> Core invariants:
>
> `connector orchestration ≠ unrestricted connector execution`
>
> `more connectors ≠ more independent evidence`
>
> `stale evidence ≠ false evidence`
>
> `connector failure ≠ negative identity evidence`
>
> `repeated observation ≠ repeated confidence`
>
> `reassessment must be incremental, deterministic, and user-scoped`

---

# 1. Mandatory Sprint 19 Preflight

Before implementing Sprint 20, verify the actual Sprint 19 repository state.

The Sprint 19 walkthrough contains one item that must be clarified before the baseline is frozen:

```text
OSINTgram adapter version: 1.1.0-mock
```

A value containing `mock` must not be represented as a verified upstream OSINTgram release unless it actually corresponds to a real, immutable dependency used in production.

Required preflight:

```text
1. Identify what "1.1.0-mock" actually means.
2. Determine whether automated tests use a mock adapter/version only.
3. Determine the exact real OSINTgram source/revision used by the runtime image.
4. If no real OSINTgram binary is installed, classify Sprint 19 as:
   connector architecture verified,
   live connector runtime not yet verified.
5. Record the exact immutable upstream version or commit before production enablement.
```

Do not block Sprint 20 architecture work solely because live platform access is unavailable, but do not claim production connector verification from mocked execution.

Also verify:

```text
pytest tests/
npm run build
alembic heads
alembic current
```

Expected starting migration head from the Sprint 19 walkthrough:

```text
b4585c600b84
```

Verify rather than assume it.

Required baseline report:

```text
backend passed / failed / skipped
frontend build result
actual Alembic head
Maigret runtime availability
OSINTgram runtime availability
real vs mocked connector status
queue consumers
feature flag defaults
```

---

# 2. Sprint Goal

Sprint 20 introduces a canonical orchestration layer above individual connectors.

Current architecture:

```text
Identity Anchor
   ├── Maigret flow
   └── OSINTgram flow
```

Target architecture:

```text
Verified Identity Anchor
        ↓
Discovery Request
        ↓
Connector Orchestrator
   ├── Eligibility Policy
   ├── Capability Policy
   ├── Consent Gate
   ├── Freshness Policy
   ├── Budget Policy
   ├── Health Policy
   ├── Deduplication
   └── Execution Planner
        ↓
Connector Execution Plan
   ├── Maigret
   ├── OSINTgram
   └── Future Approved Connectors
        ↓
Normalized Connector Observations
        ↓
Canonical Fact Layer
        ↓
Evidence Freshness / Staleness
        ↓
Incremental Match Reassessment
        ↓
Affected Cluster Rebuild
        ↓
Human Review
```

The orchestrator decides:

```text
which connector should run
for which eligible input
for which approved capability
whether existing observations are still fresh
whether execution budget remains
whether connector health permits execution
what downstream entities must be recalculated
```

It must not become a generic arbitrary job runner.

---

# 3. Scope

Sprint 20 should implement:

```text
canonical connector registry
connector orchestration service
execution planning
freshness policy
observation expiry/staleness
per-connector health state
execution budgets and quotas
idempotent orchestration runs
incremental reassessment
affected-cluster rebuilds
multi-connector provenance preservation
orchestration APIs
orchestration UI
privacy lifecycle
operational metrics
```

Sprint 20 should not implement:

```text
new unrestricted OSINT tools
recursive social graph crawling
automatic identity confirmation
LLM-based identity scoring
global cross-user identity correlation
connector access-control bypass
automatic PDSS confirmation
```

---

# 4. Feature Flags

Add:

```text
FEATURE_CONNECTOR_ORCHESTRATION=false
FEATURE_EVIDENCE_FRESHNESS=false
FEATURE_INCREMENTAL_REASSESSMENT=false
```

Safe default:

```text
false
```

Existing connector flags remain authoritative:

```text
FEATURE_MAIGRET_DISCOVERY
FEATURE_OSINTGRAM_DISCOVERY
```

Required:

```text
orchestration enabled
+
connector disabled
→ connector must not execute
```

The orchestrator cannot override connector-level kill switches.

---

# 5. Canonical Connector Registry

Create a registry describing every approved connector.

Suggested interface:

```text
ConnectorDescriptor
- connector_type
- adapter_version
- runtime_version
- enabled
- availability
- capabilities
- queue
- timeout
- cost_weight
- freshness_policy
- health_policy
```

Initial connectors:

```text
maigret
osintgram
```

Do not dynamically load arbitrary connector names from user input.

---

# 6. Connector Runtime Version vs Adapter Version

Keep these separate:

```text
adapter_version
runtime_version
```

Example:

```text
adapter_version = internal DigiZafe adapter contract version
runtime_version = actual Maigret/OSINTgram version or immutable revision
```

Do not use a mock test version as a production runtime version.

For unavailable runtime:

```text
runtime_version = null
availability = unavailable / test_only
```

---

# 7. Connector Availability States

Canonical states:

```text
available
disabled
not_configured
test_only
degraded
rate_limited
temporarily_unavailable
unavailable
```

The orchestrator must use these states when planning.

Required:

```text
test_only
→ may be used in tests
→ must not be represented as live production execution
```

---

# 8. Orchestration Run Model

Create a model such as:

```text
IdentityOrchestrationRun
```

Suggested fields:

```text
id
user_id
anchor_id
status
policy_version
input_fingerprint
requested_capabilities
planned_connector_count
executed_connector_count
skipped_connector_count
started_at
completed_at
created_at
```

Statuses:

```text
planned
queued
running
completed
partial_result
failed
cancelled
```

---

# 9. Execution Plan Model

Persist a reproducible execution plan.

Suggested:

```text
ConnectorExecutionPlanItem
```

Fields:

```text
id
orchestration_run_id
connector_type
capability
input_alias_id
decision
decision_reason
freshness_state
health_state
budget_state
discovery_run_id
execution_status
created_at
```

Possible decisions:

```text
execute
skip_fresh
skip_disabled
skip_no_consent
skip_budget
skip_unavailable
skip_ineligible
skip_duplicate
```

This makes orchestration explainable.

---

# 10. Planning Must Be Deterministic

Required:

```text
same anchor version
+
same active aliases
+
same connector registry
+
same policy version
+
same freshness state
+
same budget state
→ same execution plan
```

Time-dependent inputs such as budget windows and freshness timestamps must be explicitly represented.

---

# 11. Input Fingerprint

Generate a deterministic fingerprint from relevant orchestration inputs.

Include:

```text
user_id scope
anchor_id
anchor_version
active eligible alias IDs and canonical values
requested capabilities
connector policy version
enabled connector set
```

Do not include raw secrets.

Use the fingerprint for:

```text
idempotency
duplicate-run suppression
auditability
```

---

# 12. Idempotent Run Creation

Repeated identical requests within an active idempotency window should not create uncontrolled duplicate executions.

Required:

```text
same user
+
same input fingerprint
+
equivalent active run
→ reuse or return existing run
```

Do not globally deduplicate across users.

---

# 13. Connector Eligibility Policy

For every connector/capability/input tuple evaluate:

```text
feature enabled?
connector available?
capability enabled?
input type eligible?
alias active?
consent valid?
budget available?
observation already fresh?
duplicate execution active?
```

Only then:

```text
execute
```

---

# 14. Freshness Is a First-Class Concept

Introduce canonical states:

```text
fresh
stale
expired
unknown
superseded
```

Do not treat:

```text
stale
```

as:

```text
false
```

Staleness means the observation may need revalidation.

---

# 15. Observation Freshness Metadata

Extend the canonical provenance/observation layer if necessary.

Recommended fields:

```text
observed_at
valid_from
stale_after
expires_at
superseded_at
freshness_policy_version
```

Do not rewrite historical `observed_at` timestamps when a fact is merely re-observed.

---

# 16. Connector-Specific Freshness Policy

Different observation types may have different freshness periods.

Example policy categories:

```text
profile_existence
username
display_name
bio_link
avatar
cross_link
relationship_context
```

Do not hard-code one TTL for every fact.

Store policy centrally and version it.

---

# 17. Freshness Policy Version

Add:

```text
EVIDENCE_FRESHNESS_POLICY_VERSION
```

Increment when TTL/staleness semantics materially change.

A policy change should allow affected observations to be reclassified without corrupting original provenance.

---

# 18. Re-observation Semantics

When the same canonical fact is observed again:

```text
same canonical fact
+
same normalized value
→ update last_observed_at / add provenance observation
→ do not duplicate identity evidence weight
```

If the value changes:

```text
old fact
→ historical/superseded according to policy

new fact
→ current observation
```

Preserve lineage.

---

# 19. Canonical Fact Layer

If not already explicit, introduce a canonical fact abstraction or service.

Conceptual:

```text
Connector Observations
        ↓
Canonical Fact Key
        ↓
Current Fact State
        ↓
Identity Evidence
```

Examples:

```text
profile_exists:<platform>:<canonical_profile_url>
username:<platform>:<canonical_username>
external_link:<source_profile>:<canonical_target>
avatar_fingerprint:<profile>:<fingerprint>
```

Connector count must not define evidence count.

---

# 20. Multi-Connector Corroboration

Multiple connectors may corroborate the same fact.

Required representation:

```text
one canonical fact
+
multiple provenance observations
```

Optional metadata:

```text
observed_by_connectors
first_observed_at
last_observed_at
```

Do not convert connector count directly into identity probability.

---

# 21. Independence Review

Sprint 20 must audit existing evidence independence rules.

Required examples:

```text
Maigret profile URL
+
OSINTgram same profile URL
→ one profile-existence fact

OSINTgram avatar URL
+
Sprint 18 pHash derived from that avatar
→ lineage preserved

bio link
+
cross-link evidence derived from same bio link
→ related provenance, not blindly independent
```

Add explicit `derived_from` relationships where necessary.

---

# 22. Budget Policy

Create a canonical:

```text
ConnectorBudgetPolicy
```

Possible dimensions:

```text
per-user runs per hour/day
per-connector runs
per-capability runs
max aliases per orchestration run
max concurrent runs
cost weight
failure cooldown
```

Exact values should be configurable.

---

# 23. Budget Decisions Must Be Explainable

Plan items skipped for budget reasons should record:

```text
skip_budget
```

with a safe reason code.

Do not expose sensitive infrastructure details.

---

# 24. Budget Is Not Billing

Sprint 20 budgets are operational safety controls.

They do not imply:

```text
monetary billing
credits
subscription pricing
```

unless separately implemented.

---

# 25. Health-Aware Planning

Create:

```text
ConnectorHealthService
```

Track:

```text
recent successes
recent normalized failures
rate-limit state
timeout rate
last success
last failure
cooldown_until
```

Do not store secrets in health records.

---

# 26. Health State Must Not Affect Identity Evidence

Required:

```text
connector unhealthy
→ skip/defer execution
```

not:

```text
connector unhealthy
→ candidate less likely to belong to user
```

Operational health and identity evidence are separate domains.

---

# 27. Circuit Breaker

Implement a bounded connector circuit breaker.

Possible:

```text
closed
open
half_open
```

Open after a configurable threshold of operational failures.

Required:

```text
open circuit
→ no new connector execution
→ planner records skip/defer reason
```

Do not create an infinite retry storm.

---

# 28. Failure Classification

Only operational failures should affect connector health.

Examples:

```text
timeout
tool_unavailable
session_expired
rate_limited
connector_error
```

Do not count:

```text
no profile found
```

as connector infrastructure failure.

---

# 29. Execution Ordering

The orchestrator may order plan items deterministically.

Possible policy:

```text
1. lower-cost / passive connector
2. source-specific connector
3. enrichment only for newly material observations
```

Do not run every connector merely because it exists.

---

# 30. Parallelism

Safe independent connector executions may run concurrently, subject to:

```text
per-user concurrency
per-connector concurrency
queue capacity
budget
health state
```

Do not create unbounded fan-out.

---

# 31. Queue Architecture

Preserve current logical isolation:

```text
Maigret
→ existing discovery/scans queue

OSINTgram
→ osint_connectors

Avatar / cross-link enrichment
→ identity_enrichment
```

The orchestrator coordinates tasks but should not collapse all workloads into one queue.

---

# 32. Orchestrator Queue

If asynchronous planning is needed, use a lightweight queue such as:

```text
orchestration
```

or an existing general Celery queue.

Planning tasks should not perform heavy connector work directly.

---

# 33. Orchestration State Machine

Recommended:

```text
PLANNED
   ↓
QUEUED
   ↓
RUNNING
   ├── all required items complete → COMPLETED
   ├── some valid + some failed/skipped → PARTIAL_RESULT
   └── no usable result + fatal orchestration error → FAILED
```

Connector no-result is not necessarily orchestration failure.

---

# 34. Child Run Linkage

Each connector execution should link back to:

```text
orchestration_run_id
```

Existing:

```text
CandidateDiscoveryRun
```

may remain the connector-level execution record.

Required hierarchy:

```text
IdentityOrchestrationRun
   ├── Maigret CandidateDiscoveryRun
   └── OSINTgram CandidateDiscoveryRun
```

---

# 35. Do Not Rewrite Stable Connector Adapters

Sprint 20 should orchestrate existing adapters.

Avoid large rewrites of:

```text
MaigretAdapter
OSINTgramAdapter
AvatarSimilarityService
CrossLinkEvidenceService
```

unless a concrete defect is found.

---

# 36. Incremental Reassessment Service

Create a service such as:

```text
IdentityReassessmentCoordinator
```

Input:

```text
materially changed canonical facts
```

Output:

```text
affected candidate IDs
affected current assessments
affected cluster IDs
```

---

# 37. Material Change Detection

Recalculate only when a material input changes.

Material examples:

```text
new canonical fact
fact superseded
fact expires
new contradiction
user confirmation
user dismissal
alias revoked
confirmed profile revoked
policy version changes
```

Non-material examples:

```text
same fact re-observed unchanged
duplicate connector provenance
same raw-result fingerprint
```

---

# 38. Assessment Fingerprint

Each current assessment should have or derive an input fingerprint.

Conceptual:

```text
candidate
+
anchor version
+
current material evidence fact keys
+
engine version
+
policy version
→ assessment_input_fingerprint
```

Required:

```text
same fingerprint
→ no duplicate recalculation
```

---

# 39. Evidence Expiry and Assessment Staleness

When material evidence expires:

```text
assessment
→ stale
```

Then:

```text
recalculate using remaining current evidence
```

Do not delete historical assessments solely because evidence becomes stale.

---

# 40. User Decisions Remain Authoritative Review Events

Required:

```text
user confirmed
user dismissed
```

remain distinguishable from algorithmic evidence.

Freshness expiration must not silently erase a user decision.

---

# 41. Cluster Incremental Rebuild

Determine affected clusters from changed candidate assessments.

Required:

```text
candidate assessment materially changes
→ rebuild only affected cluster neighborhood
```

Do not rebuild every user cluster for every observation.

---

# 42. Preserve Transitive Conflict Safety

Sprint 18 invariant remains:

```text
A supports B
B supports C
A conflicts with C

→ no blind A+B+C supported cluster
```

Incremental rebuild must preserve the same pairwise contradiction checks as full rebuild.

---

# 43. Full Rebuild Fallback

Provide an explicit:

```text
full user-scoped rebuild
```

for:

```text
policy migration
repair
administrative recovery
```

It must remain:

```text
user-scoped
bounded
audited
```

Never global by default.

---

# 44. Orchestration API

Possible endpoints:

```text
POST /api/v1/identity/orchestration/runs
GET  /api/v1/identity/orchestration/runs
GET  /api/v1/identity/orchestration/runs/{id}
GET  /api/v1/identity/connectors
```

Optional:

```text
POST /api/v1/identity/orchestration/runs/{id}/cancel
```

Do not expose raw connector commands.

---

# 45. Orchestration Request DTO

Possible:

```text
alias_ids
requested_capabilities
force_refresh = false
```

`force_refresh` must still obey:

```text
feature flags
consent
budget
health policy
connector availability
```

It may bypass freshness skipping only if policy permits.

---

# 46. No User-Controlled Connector Internals

Do not accept:

```text
queue name
timeout
binary path
raw flags
session secret
output path
retry count
```

from the normal user request.

---

# 47. Connector Status API

Return safe information:

```text
connector
availability
enabled
capabilities
health state
```

Do not return:

```text
secret
environment variable value
internal credential path
raw authentication error
```

---

# 48. Frontend — Unified Discovery

Update the identity discovery UI to provide one primary action:

```text
Discover Profiles
```

The backend orchestrator decides eligible connectors.

Optionally show advanced source selection only if product requirements need it.

---

# 49. Frontend — Execution Plan Transparency

Show safe states:

```text
Maigret — running
OSINTgram — skipped: connector not configured
Avatar enrichment — queued
```

Do not expose infrastructure-sensitive details.

---

# 50. Frontend — Freshness

Display useful freshness labels:

```text
Observed recently
May be outdated
Revalidation pending
```

Avoid presenting exact TTL mechanics unless useful.

---

# 51. Frontend — Refresh

Allow bounded refresh:

```text
Refresh discovery
```

but the backend remains authoritative.

The UI must not promise that every connector will execute.

---

# 52. Privacy Export

Extend export to include:

```text
orchestration runs
execution plan decisions
connector observations
freshness metadata
assessment history
cluster versions where already exportable
```

Exclude:

```text
operator secrets
raw environment values
internal credential material
```

---

# 53. Shredding

Account deletion must remove:

```text
user orchestration runs
plan items
user-scoped observations
derived freshness state
user-scoped reassessment artifacts
user-scoped connector provenance
```

Shared connector runtime health may remain if it contains no user-identifiable data.

---

# 54. Data Retention

Define retention for:

```text
completed orchestration runs
execution plan history
operational failure details
temporary connector outputs
```

Do not retain verbose operational artifacts indefinitely without purpose.

---

# 55. RLS / Cross-User Isolation

Required:

```text
User A cannot read User B orchestration run
User A cannot read User B plan
User A cannot force-refresh User B alias
User A cannot trigger reassessment for User B candidate
User A cannot rebuild User B cluster
User A cannot infer User B connector observations
```

Any failure is P0.

---

# 56. Orchestration Idempotency Tests

Required:

```text
same request submitted twice
→ no uncontrolled duplicate connector execution

same active input fingerprint
→ existing run reused or duplicate safely suppressed

same connector observation repeated
→ provenance may update
→ evidence weight does not inflate
```

---

# 57. Freshness Tests

Required:

```text
fresh observation
→ connector skipped when refresh unnecessary

stale observation
→ eligible for revalidation

expired observation
→ affected assessment becomes stale

same fact re-observed
→ freshness renewed without duplicate evidence

changed fact
→ old provenance preserved
→ new current fact materialized
```

---

# 58. Budget Tests

Required:

```text
budget available
→ eligible execution

budget exhausted
→ skip_budget

force_refresh
+
budget exhausted
→ still blocked unless explicit privileged policy exists

User A budget
→ independent of User B
```

---

# 59. Health Tests

Required:

```text
repeated operational failures
→ circuit opens

open circuit
→ execution skipped

cooldown expires
→ half-open probe

successful probe
→ circuit closes

no-result
→ does not count as infrastructure failure
```

---

# 60. Incremental Reassessment Tests

Required:

```text
duplicate provenance only
→ no assessment recalculation

new material fact
→ affected candidate recalculated

unrelated candidate
→ not recalculated

evidence expires
→ affected assessment stale/recalculated

policy version changes
→ affected scope recalculated deterministically
```

---

# 61. Incremental Cluster Tests

Required:

```text
Candidate A assessment changes
→ affected cluster neighborhood rebuilt

unrelated cluster
→ unchanged

transitive conflict trap
→ still blocked

same cluster input fingerprint
→ no duplicate cluster version
```

---

# 62. Connector Regression Tests

Maigret:

```text
still independently executable
feature flag respected
candidate deduplication intact
provenance intact
```

OSINTgram:

```text
operator secret remains worker-only
feature flag respected
test-only/live status accurate
candidate deduplication intact
provenance intact
```

---

# 63. Mock vs Live Connector Verification

Automated CI may use mocks.

Required reporting distinction:

```text
adapter contract tests
mocked connector integration tests
live connector smoke tests
```

Do not merge these into one vague statement such as:

```text
OSINTgram fully verified
```

unless a real runtime smoke test was actually executed.

---

# 64. Live Smoke Tests

Live smoke tests should be:

```text
optional
environment-gated
manual or protected CI
non-blocking for ordinary unit tests
```

They must not expose secrets.

Record:

```text
executed / not executed
runtime revision
result
```

---

# 65. Operational Metrics

Recommended:

```text
orchestration_runs_total
orchestration_duration
plan_items_total by decision
connector_executions_total
connector_skips_total
connector_health_state
freshness_skips_total
reassessments_total
cluster_rebuilds_total
```

Avoid high-cardinality user identifiers as metric labels.

---

# 66. Audit Events

Recommended:

```text
orchestration_run_created
orchestration_plan_created
connector_execution_planned
connector_execution_skipped
connector_execution_completed
evidence_became_stale
assessment_recalculated
cluster_incrementally_rebuilt
```

Do not log secrets or excessive raw OSINT data.

---

# 67. Migration Strategy

If new tables are added:

```text
IdentityOrchestrationRun
ConnectorExecutionPlanItem
```

generate one focused Sprint 20 migration.

Before migration:

```text
alembic heads
alembic current
```

After migration:

```text
alembic upgrade head
alembic heads
alembic current
```

Test:

```text
existing database upgrade
fresh database upgrade
one intended head
```

---

# 68. Recommended Models

Likely new:

```text
IdentityOrchestrationRun
ConnectorExecutionPlanItem
```

Potentially extend:

```text
CandidateProvenanceObservation
CandidateDiscoveryRun
IdentityMatchAssessment
IdentityCluster
```

Avoid creating duplicate models for facts already represented canonically.

---

# 69. Recommended Services

```text
ConnectorRegistry
ConnectorOrchestrationService
ConnectorEligibilityPolicy
ConnectorBudgetService
ConnectorHealthService
EvidenceFreshnessService
CanonicalFactService
IdentityReassessmentCoordinator
```

Do not over-fragment trivial logic.

Use existing services where they already provide canonical behavior.

---

# 70. Recommended Tasks

Possible:

```text
plan_identity_orchestration
finalize_identity_orchestration
revalidate_stale_observations
recalculate_affected_assessments
rebuild_affected_clusters
```

Connector execution remains delegated to connector-specific tasks.

---

# 71. Cancellation

If cancellation is implemented:

```text
cancel not-started plan items
mark run cancelled/partial as appropriate
do not corrupt completed observations
```

Do not promise reliable termination of already-running external connector processes unless implemented and tested.

---

# 72. Retry Policy

Retries must be normalized by error type.

Examples:

```text
timeout
→ bounded retry if policy permits

rate_limited
→ defer until cooldown

invalid_input
→ no retry

feature_disabled
→ no retry

session_unavailable
→ no rapid retry loop
```

---

# 73. No Retry-Based Evidence Inflation

Repeated connector retries that return the same fact must not:

```text
increase score
create duplicate candidates
create uncontrolled evidence rows
```

---

# 74. Policy Versioning

Add:

```text
CONNECTOR_ORCHESTRATION_POLICY_VERSION
EVIDENCE_FRESHNESS_POLICY_VERSION
```

Only increment existing:

```text
IDENTITY_MATCH_ENGINE_VERSION
IDENTITY_MATCH_POLICY_VERSION
```

if match semantics actually change.

Document all version decisions.

---

# 75. Baseline Compatibility

Sprint 20 must preserve:

```text
Sprint 14 security baseline
Sprint 15 Identity Anchor
Sprint 16 Maigret discovery
Sprint 17 deterministic match engine
Sprint 18 enrichment and clustering
Sprint 19 OSINTgram connector boundary
```

---

# 76. PDSS Boundary

Required:

```text
orchestration
freshness
connector corroboration
identity reassessment
cluster rebuild
```

must not automatically create or confirm:

```text
PDSS exposure
```

PDSS semantics remain unchanged.

---

# 77. P0/P1 Defect Policy

For defects:

```text
reproduce
classify
add regression test
apply smallest safe fix
rerun affected suite
document
```

Stop for approval if a fix would:

```text
weaken cross-user isolation
weaken consent
weaken secret handling
bypass connector kill switches
change PDSS semantics
introduce global identity correlation
```

---

# 78. Implementation Order

## Phase A — Sprint 19 Baseline Audit

```text
full backend suite
frontend build
migration head
real vs mock connector verification
queue consumers
feature flags
```

## Phase B — Canonical Registry

```text
connector descriptors
capabilities
runtime status
version separation
```

## Phase C — Orchestration Models

```text
IdentityOrchestrationRun
ConnectorExecutionPlanItem
migration
RLS
```

## Phase D — Policies

```text
eligibility
freshness
budget
health
```

## Phase E — Planner

```text
deterministic input fingerprint
execution decisions
idempotency
```

## Phase F — Execution

```text
dispatch existing connector tasks
track child discovery runs
finalize orchestration state
```

## Phase G — Canonical Facts and Freshness

```text
deduplication
re-observation
supersession
expiry
```

## Phase H — Incremental Reassessment

```text
material change detection
affected candidates
assessment fingerprints
bounded recalculation
```

## Phase I — Incremental Clustering

```text
affected cluster scope
deterministic rebuild
conflict safety
```

## Phase J — Privacy / API / Frontend

```text
export
shred
orchestration API
connector status
unified discovery UI
freshness UI
```

## Phase K — Verification

```text
idempotency
freshness
budget
health
RLS
incremental reassessment
cluster safety
full regression
```

---

# 79. Required Final Walkthrough

At completion provide:

1. Actual Sprint 19 starting migration head.
2. Sprint 20 migration ID and final head.
3. Full preflight backend test counts.
4. Frontend preflight build result.
5. Exact Maigret runtime version.
6. Exact OSINTgram real runtime version/revision.
7. Meaning and removal/retention of `1.1.0-mock`.
8. Which tests used mocks.
9. Whether a live OSINTgram smoke test was executed.
10. Connector registry schema.
11. Connector availability states.
12. Feature flags and defaults.
13. Orchestration policy version.
14. Freshness policy version.
15. Identity match engine/policy version decision.
16. Orchestration run schema.
17. Execution plan schema.
18. RLS policy.
19. Input fingerprint algorithm.
20. Idempotency behavior.
21. Connector eligibility rules.
22. Freshness states.
23. Exact freshness TTLs by observation type.
24. Re-observation behavior.
25. Supersession behavior.
26. Canonical fact key rules.
27. Cross-connector deduplication behavior.
28. Independence/derived-from rules.
29. Budget policy and exact configured limits.
30. Health policy.
31. Circuit-breaker thresholds.
32. Connector failure classification.
33. Execution ordering.
34. Concurrency limits.
35. Queue routing.
36. Orchestration state machine.
37. Child discovery-run linkage.
38. Material-change rules.
39. Assessment input fingerprint.
40. Incremental reassessment behavior.
41. Incremental cluster rebuild behavior.
42. Full rebuild fallback.
43. Orchestration API.
44. Connector status API.
45. Frontend unified discovery behavior.
46. Privacy export result.
47. Shred/account deletion result.
48. RLS/cross-user isolation results.
49. Idempotency test results.
50. Freshness test results.
51. Budget test results.
52. Health/circuit-breaker test results.
53. Incremental reassessment test results.
54. Incremental clustering test results.
55. Maigret regression result.
56. OSINTgram regression result.
57. Sprint 19 secret-leakage regression.
58. Sprint 18 enrichment/clustering regression.
59. Sprint 17 deterministic match regression.
60. Sprint 16 candidate discovery regression.
61. Sprint 15 Identity Anchor regression.
62. Sprint 14 critical security regression.
63. PDSS regression result.
64. Final backend test counts.
65. Final frontend production build result.
66. P0–P3 issues found.
67. Minimal fixes applied.
68. Files created or modified.
69. Remaining limitations.
70. GO / CONDITIONAL GO / NO-GO decision for Sprint 21.

Do not predetermine GO.

---

# 80. Definition of Done

## Baseline

- [ ] Full Sprint 19 backend suite executed.
- [ ] Frontend build passes.
- [ ] Actual Alembic head verified.
- [ ] `1.1.0-mock` status clarified.
- [ ] Real connector runtime status accurately documented.
- [ ] Mock tests distinguished from live verification.

## Registry

- [ ] Maigret registered.
- [ ] OSINTgram registered.
- [ ] Adapter and runtime versions separated.
- [ ] Capabilities explicit.
- [ ] Availability states canonical.
- [ ] Connector kill switches remain authoritative.

## Orchestration

- [ ] User-scoped orchestration runs.
- [ ] Reproducible execution plans.
- [ ] Deterministic input fingerprint.
- [ ] Idempotent duplicate suppression.
- [ ] No arbitrary connector commands.
- [ ] Existing connector queues preserved.
- [ ] Child runs linked to parent orchestration run.

## Freshness

- [ ] Fresh/stale/expired/unknown/superseded states supported.
- [ ] TTLs centrally configured.
- [ ] Freshness policy versioned.
- [ ] Re-observation does not duplicate evidence.
- [ ] Historical provenance preserved.
- [ ] Stale does not mean false.

## Budget and Health

- [ ] Per-user budgets enforced.
- [ ] Connector-specific limits enforced.
- [ ] Health state tracked.
- [ ] Circuit breaker implemented.
- [ ] No-result is not infrastructure failure.
- [ ] Open circuit prevents execution.
- [ ] No retry storms.

## Evidence Integrity

- [ ] One canonical fact may have multiple connector provenance records.
- [ ] Connector count does not equal evidence count.
- [ ] Derived evidence lineage preserved.
- [ ] Repeated observations do not inflate confidence.
- [ ] Operational failures do not create negative identity evidence.

## Incremental Reassessment

- [ ] Material changes identified.
- [ ] Duplicate provenance does not trigger unnecessary recalculation.
- [ ] Only affected candidates recalculated.
- [ ] Assessment fingerprints prevent duplicate history.
- [ ] Evidence expiry marks affected assessments stale.

## Clustering

- [ ] Only affected cluster neighborhoods rebuilt.
- [ ] Unrelated clusters unchanged.
- [ ] Transitive conflict safety preserved.
- [ ] Cluster input fingerprints prevent duplicate versions.
- [ ] Full rebuild fallback is user-scoped.

## Security and Privacy

- [ ] Cross-user orchestration access blocked.
- [ ] Cross-user plan access blocked.
- [ ] Cross-user reassessment blocked.
- [ ] Cross-user cluster rebuild blocked.
- [ ] Connector secrets remain excluded from orchestration data.
- [ ] Privacy export updated.
- [ ] Shredding updated.
- [ ] Shared connector operational state contains no user secrets.

## Regression

- [ ] Maigret intact.
- [ ] OSINTgram intact.
- [ ] Sprint 19 secret boundary intact.
- [ ] Sprint 18 avatar/cross-link/clustering intact.
- [ ] Sprint 17 deterministic scoring intact.
- [ ] Sprint 16 candidate review intact.
- [ ] Sprint 15 Identity Anchor intact.
- [ ] Sprint 14 security baseline intact.
- [ ] PDSS semantics unchanged.
- [ ] Frontend production build passes.

Release gate:

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 81. GO / NO-GO Gate for Sprint 21

## GO

Proceed when:

```text
connector runtime status is truthfully represented
orchestration is deterministic
connector kill switches remain authoritative
fresh observations prevent unnecessary reruns
stale observations can be revalidated
budgets prevent uncontrolled execution
health failures trigger bounded circuit breaking
multi-connector observations deduplicate into canonical facts
repeated observations do not inflate identity confidence
reassessment is incremental
cluster rebuilds are scoped
privacy lifecycle passes
cross-user isolation passes
P0 = 0
P1 = 0 or explicitly accepted
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
cross-user isolation
secret security
consent
connector access boundaries
evidence integrity
determinism
privacy
```

## NO-GO

Do not begin Sprint 21 with:

```text
mock connector represented as verified live runtime
orchestrator bypassing connector feature flags
unbounded connector fan-out
global cross-user deduplication
connector count directly inflating identity score
stale evidence treated as contradiction
retry storms
broken circuit breaker
full-database reassessment for every observation
global cluster rebuilds
broken privacy deletion
unresolved P0
unaccepted P1
```

---

# 82. Recommended Sprint 21 Direction

After orchestration and freshness are stable, Sprint 21 should focus on:

```text
Evidence Timeline
+
Identity Change Detection
+
User Review Queue
+
Explainable Revalidation
```

Target:

```text
Canonical Identity Facts
        ↓
Temporal Evidence Timeline
        ↓
Change Detection
   ├── username changed
   ├── profile disappeared
   ├── bio link changed
   ├── avatar changed
   └── cross-link changed
        ↓
Material Change Classification
        ↓
Incremental Reassessment
        ↓
User Review Queue
```

Sprint 21 should improve temporal reasoning and reviewability rather than adding more connectors immediately.

---

# 83. Final Sprint 20 Principle

Sprint 20 is not about running every connector.

It is about deciding when a connector should run, when it should not run, and what must change when new information arrives.

The system should be able to say:

```text
This alias is eligible.

Maigret already produced a fresh observation, so it does not need to run again.

OSINTgram is disabled, unavailable, test-only, unhealthy, or eligible according to its actual runtime state.

The same profile observed by multiple connectors remains one canonical identity fact with multiple provenance records.

A materially changed fact triggers reassessment only for affected candidates.

Only affected identity clusters are rebuilt.

Operational connector failures do not become negative identity evidence.
```

Target architecture after Sprint 20:

```text
VERIFIED IDENTITY ANCHOR
        ↓
UNIFIED CONNECTOR ORCHESTRATOR
   ├── ELIGIBILITY
   ├── CONSENT
   ├── CAPABILITY
   ├── FRESHNESS
   ├── BUDGET
   ├── HEALTH
   └── IDEMPOTENCY
        ↓
BOUNDED CONNECTOR EXECUTION
   ├── MAIGRET
   └── OSINTGRAM
        ↓
MULTI-CONNECTOR PROVENANCE
        ↓
CANONICAL FACTS
        ↓
FRESHNESS / STALENESS
        ↓
INCREMENTAL DETERMINISTIC REASSESSMENT
        ↓
AFFECTED CLUSTER REBUILD
        ↓
HUMAN REVIEW
```

Sprint 20 is complete when DigiZafe has one deterministic, policy-driven orchestration layer that coordinates approved connectors without bypassing their security boundaries; prevents unnecessary and duplicate execution; distinguishes fresh, stale, expired, and superseded observations; preserves multi-connector provenance without double counting; applies budgets and health-aware circuit breaking; and incrementally recalculates only the identity assessments and clusters actually affected by material evidence changes.

---

**End of Sprint 20 Implementation Guide**
