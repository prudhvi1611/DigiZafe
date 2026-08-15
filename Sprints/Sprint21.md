# DigiZafe — Sprint 21 Implementation Guide

**Sprint:** 21 — Temporal Evidence Timeline, Identity Change Detection & Human Review Queue  
**Applies after:** Sprint 20 — Unified Multi-Connector Orchestration, Evidence Freshness & Incremental Reassessment  
**Primary goal:** Add a deterministic temporal reasoning layer that records meaningful identity changes over time, classifies those changes conservatively, routes material changes into a user-controlled review queue, and triggers only bounded incremental reassessment.

> Core invariants:
>
> `change detected ≠ identity compromise`
>
> `profile disappeared ≠ user abandoned account`
>
> `avatar changed ≠ identity changed`
>
> `connector failure ≠ profile disappearance`
>
> `stale observation ≠ changed fact`
>
> `algorithmic review priority ≠ automatic user decision`
>
> `historical evidence must remain provenance-preserving`
>
> `temporal reasoning must remain deterministic and user-scoped`

---

# 1. Mandatory Sprint 20 Preflight

Before implementing Sprint 21, verify the actual Sprint 20 repository state.

The Sprint 20 completion summary reports:

```text
69 backend integration/unit tests passed
frontend updated to unified orchestration
orchestration run APIs implemented
incremental cluster fingerprints implemented
privacy export/shred extended
```

However, the final Sprint 20 report shown does not provide every required implementation detail from the Sprint 20 guide.

Therefore, Sprint 21 must begin with a focused verification audit.

Verify:

```text
pytest tests/
npm run build
alembic heads
alembic current
```

Record:

```text
passed
failed
skipped
xfailed
```

Do not assume the final migration head from the previous summary. Read it from the actual repository.

Also verify the following Sprint 20 invariants directly:

```text
IdentityOrchestrationRun exists and is user-scoped
ConnectorExecutionPlanItem exists and is user-scoped
orchestration input fingerprint exists
duplicate orchestration suppression works
freshness metadata exists
valid_from migration is valid on fresh and existing databases
budget enforcement exists
Redis failure behavior is bounded
connector health/circuit breaker exists
test_only connector behavior is explicit
material change detection exists
incremental reassessment is scoped
incremental cluster rebuild is scoped
cluster input_fingerprint exists
privacy export includes orchestration data
shredding removes orchestration data
```

If some Sprint 20 features were planned but not actually implemented, classify them:

```text
VERIFIED
PARTIAL
NOT_IMPLEMENTED
TEST_ONLY
```

Do not silently assume completeness from the task checklist.

---

# 2. Sprint 20 Runtime Truthfulness Gate

The previous baseline stated:

```text
Maigret:
test_only / mocked

OSINTgram:
test_only / mocked
```

Sprint 21 must preserve this distinction unless real runtimes have since been installed and independently verified.

Required:

```text
mock connector output
≠
live-world change observation
```

Temporal change detection must not create real user-facing change alerts from synthetic/mock connector output in a normal production environment.

In explicit test mode, fixtures may generate deterministic temporal changes for verification.

---

# 3. Sprint Goal

Sprint 21 introduces a temporal layer above canonical facts.

Target architecture:

```text
Verified Identity Anchor
        ↓
Unified Connector Orchestration
        ↓
Connector Provenance Observations
        ↓
Canonical Fact Resolution
        ↓
Temporal Fact State
        ↓
Change Detection
   ├── fact appeared
   ├── fact changed
   ├── fact disappeared
   ├── fact reappeared
   ├── fact became stale
   ├── fact expired
   └── contradiction emerged
        ↓
Change Classification
        ↓
Materiality / Review Priority
        ↓
Human Review Queue
        ↓
User Decision
        ↓
Incremental Reassessment
        ↓
Affected Cluster Rebuild
```

Sprint 21 must make DigiZafe capable of answering:

```text
What changed?
When was it first observed?
When was the previous state last seen?
Which connector observed the change?
Is the change confirmed, tentative, stale, or operationally uncertain?
Does the change materially affect identity assessment?
Does the user need to review it?
What downstream assessments were affected?
```

---

# 4. Scope

Sprint 21 should implement:

```text
temporal canonical fact state
identity change event model
deterministic change detector
change materiality policy
change confidence based on observation integrity
human review queue
review decisions
revalidation workflow
timeline API
review API
timeline frontend
review queue frontend
incremental reassessment integration
incremental cluster integration
privacy export/shred integration
retention policy
audit events
```

Sprint 21 should not implement:

```text
automatic account takeover conclusions
automatic identity confirmation
automatic identity dismissal
facial recognition
protected-attribute inference
global cross-user identity correlation
recursive social graph monitoring
unbounded continuous surveillance
new external OSINT connectors
LLM-based critical-path change classification
```

---

# 5. Feature Flags

Add:

```text
FEATURE_IDENTITY_TIMELINE=false
FEATURE_IDENTITY_CHANGE_DETECTION=false
FEATURE_IDENTITY_REVIEW_QUEUE=false
FEATURE_AUTOMATIC_REVALIDATION=false
```

Safe defaults:

```text
false
```

`FEATURE_AUTOMATIC_REVALIDATION` should remain independently controllable.

Required:

```text
change detection enabled
+
automatic revalidation disabled
→ changes may be recorded
→ no automatic connector execution
```

---

# 6. Versioned Policies

Add:

```text
IDENTITY_CHANGE_POLICY_VERSION = 1
IDENTITY_REVIEW_POLICY_VERSION = 1
```

Do not increment:

```text
IDENTITY_MATCH_ENGINE_VERSION
IDENTITY_MATCH_POLICY_VERSION
```

unless match scoring semantics actually change.

If Sprint 21 only changes when reassessment is triggered, not how evidence is scored:

```text
match engine/policy versions remain unchanged
```

Document the decision.

---

# 7. Temporal State Model

Introduce a canonical temporal state abstraction.

Possible domain object:

```text
TemporalFactState
```

Suggested fields:

```text
canonical_fact_key
current_value_fingerprint
current_normalized_value
first_observed_at
last_observed_at
last_confirmed_at
stale_after
expires_at
state
observation_count
connector_types
```

Possible states:

```text
current
stale
expired
superseded
absent_unconfirmed
absent_confirmed
```

Do not conflate:

```text
not observed in one run
```

with:

```text
confirmed absent
```

---

# 8. Absence Requires Special Treatment

This is a critical Sprint 21 invariant.

Required:

```text
connector did not return fact
≠
fact disappeared
```

A missing result may mean:

```text
connector failure
rate limit
partial output
parser failure
platform change
network failure
capability limitation
fact actually removed
```

Therefore, absence must be classified conservatively.

---

# 9. Absence Confirmation Policy

A fact may become:

```text
absent_unconfirmed
```

after a successful eligible revalidation fails to observe it.

It may become:

```text
absent_confirmed
```

only after the configured confirmation policy succeeds.

Recommended initial policy:

```text
profile existence:
2 successful independent revalidation attempts
separated by at least 24 hours

external link:
2 successful observations without the link
separated by at least 12 hours

bio field:
2 successful observations with changed normalized content

avatar:
one successful new fingerprint may confirm avatar change,
but old avatar disappearance alone is not negative identity evidence
```

These values must be configurable and versioned.

Mock/test mode may use compressed time windows.

---

# 10. Independent Revalidation Does Not Necessarily Mean Independent Connector

For disappearance confirmation, independence may come from:

```text
separate successful observations over time
```

or:

```text
multiple capable connectors
```

Do not require two connectors if only one approved connector can observe the fact.

However, multiple outputs from the same execution do not count as separate revalidations.

---

# 11. Identity Change Event Model

Create:

```text
IdentityChangeEvent
```

Suggested fields:

```text
id
user_id
anchor_id
candidate_profile_id nullable
canonical_fact_key
change_type
previous_value_fingerprint nullable
new_value_fingerprint nullable
previous_state
new_state
materiality
review_priority
confidence_state
detected_at
effective_at nullable
change_policy_version
source_observation_ids / lineage reference
status
created_at
```

Do not store secrets.

Avoid storing large raw connector payloads.

---

# 12. Change Types

Canonical initial change types:

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

Domain-specific safe display mappings may include:

```text
profile appeared
profile may no longer be available
username changed
display name changed
bio changed
external link added
external link removed
avatar changed
cross-link changed
```

---

# 13. Do Not Overstate Change Semantics

Never automatically convert:

```text
profile disappeared
```

into:

```text
account deleted
account banned
user abandoned account
identity stolen
```

Never automatically convert:

```text
username changed
```

into:

```text
account takeover
```

Never automatically convert:

```text
avatar changed
```

into:

```text
different person
```

Use evidence-bounded language.

---

# 14. Change Confidence States

Use deterministic confidence states such as:

```text
observed_once
revalidated
corroborated
operationally_uncertain
```

These describe observation integrity, not identity probability.

Example:

```text
profile absent in one successful run
→ observed_once / absence suspected

profile absent in two policy-compliant successful revalidations
→ revalidated / disappeared
```

---

# 15. Materiality Policy

Create:

```text
IdentityChangeMaterialityPolicy
```

Possible levels:

```text
informational
low
medium
high
critical_review
```

`critical_review` means:

```text
requires prominent human review
```

not:

```text
confirmed compromise
```

---

# 16. Initial Materiality Guidance

Suggested defaults:

```text
display name changed
→ low

bio changed
→ low

avatar changed
→ low

external link added
→ medium

external link removed
→ medium

confirmed profile URL unavailable after revalidation
→ high

username changed on a confirmed profile
→ high

new contradiction affecting a likely_match
→ high

user-confirmed profile now strongly conflicts with anchor evidence
→ critical_review

connector failure
→ no identity change event
```

All mappings must be configurable and versioned.

---

# 17. Review Priority Is Not Evidence Weight

Required:

```text
review_priority
≠
identity match score
```

A high-priority review event may exist because the consequence of uncertainty is important, not because the evidence is stronger.

---

# 18. Change Detector Service

Create:

```text
IdentityChangeDetectionService
```

Responsibilities:

```text
receive canonical fact state transition
compare previous and current state
apply change policy
deduplicate equivalent events
attach provenance lineage
calculate materiality
calculate review priority
emit downstream material-change event if appropriate
```

---

# 19. Change Event Idempotency

Generate a deterministic event fingerprint.

Possible inputs:

```text
user scope
canonical_fact_key
change_type
previous value/state fingerprint
new value/state fingerprint
change policy version
```

Required:

```text
same transition processed twice
→ one logical change event
```

---

# 20. Change Event History

Do not overwrite all prior changes with only the latest state.

Preserve history:

```text
username A
→ username B
→ username C
```

as distinct transitions.

The timeline must remain auditable.

---

# 21. Reappearance

If a previously confirmed-absent fact is observed again:

```text
FACT_REAPPEARED
```

Do not treat this as a brand-new unrelated identity fact if the canonical fact key and lineage establish continuity.

Reappearance may trigger reassessment.

---

# 22. Value Fingerprints

For sensitive or verbose values, store:

```text
normalized bounded representation
+
deterministic fingerprint
```

Do not unnecessarily persist full raw values.

For safe public values such as a canonical profile URL, normalized storage may be appropriate.

---

# 23. Timeline Ordering

The timeline should distinguish:

```text
detected_at
```

from:

```text
effective_at
```

If the exact effective time is unknown:

```text
effective_at = null
```

Do not pretend the system knows exactly when a platform-side change occurred.

---

# 24. Review Queue Model

Create:

```text
IdentityReviewItem
```

Suggested fields:

```text
id
user_id
anchor_id
change_event_id
candidate_profile_id nullable
review_type
priority
status
reason_code
created_at
reviewed_at nullable
reviewed_by_user_id nullable
resolution nullable
resolution_note nullable
```

Statuses:

```text
open
in_review
resolved
dismissed
superseded
```

---

# 25. Review Types

Initial review types:

```text
identity_change
conflicting_evidence
profile_availability_change
confirmed_profile_change
revalidation_required
```

Do not create a separate review model for every fact type.

---

# 26. Review Item Deduplication

Required:

```text
same unresolved material change
→ one active review item
```

If a later event supersedes the earlier issue:

```text
old review item
→ superseded

new review item
→ created if still materially relevant
```

---

# 27. User Review Resolutions

Supported initial resolutions:

```text
ACKNOWLEDGED
THIS_IS_STILL_MINE
THIS_IS_NOT_MINE
EXPECTED_CHANGE
REQUEST_REVALIDATION
DISMISS_ALERT
```

Map these carefully to existing domain actions.

---

# 28. Review Resolution Must Not Automatically Rewrite Identity State Without Policy

Examples:

```text
THIS_IS_STILL_MINE
```

may support continued ownership but should use the canonical existing confirmation flow.

```text
THIS_IS_NOT_MINE
```

should use the existing dismissal/revocation path.

Do not directly mutate multiple identity tables from the UI without service-layer policy.

---

# 29. Existing User Decisions Remain Canonical

Reuse:

```text
ConfirmedProfileReference
CandidateProfile confirmation/dismissal
IdentityAlias revocation
```

Do not create parallel ownership truth inside `IdentityReviewItem`.

The review queue coordinates decisions; it does not replace canonical identity models.

---

# 30. Review Audit Trail

Every resolution should record:

```text
review item
resolution
timestamp
user scope
resulting domain action
```

Do not log sensitive secrets.

---

# 31. Revalidation Requests

`REQUEST_REVALIDATION` should create a bounded request to the existing orchestration layer.

Required flow:

```text
Review Item
        ↓
Revalidation Request
        ↓
ConnectorOrchestrationService
        ↓
Eligibility
Consent
Budget
Health
Availability
        ↓
Execution Plan
```

The review queue must not bypass Sprint 20 controls.

---

# 32. Automatic Revalidation

If enabled:

```text
FEATURE_AUTOMATIC_REVALIDATION=true
```

only approved change types may schedule revalidation.

Recommended initial automatic eligibility:

```text
stale high-materiality fact
absence suspected on confirmed profile
high-priority contradiction requiring fresh observation
```

Still enforce:

```text
consent
budget
health
connector availability
cooldown
```

---

# 33. Revalidation Cooldown

Prevent loops.

Recommended configurable default:

```text
same fact automatic revalidation cooldown:
24 hours
```

Manual user-requested revalidation may use a different bounded policy.

Do not continuously retry unavailable connectors.

---

# 34. Revalidation Attempt Model

If needed, link revalidation to:

```text
IdentityReviewItem
IdentityChangeEvent
IdentityOrchestrationRun
```

Avoid creating an entirely separate execution engine.

---

# 35. Connector Failure During Revalidation

Required:

```text
revalidation connector failure
→ operationally_uncertain
→ review remains unresolved
```

not:

```text
fact disappeared
```

---

# 36. Partial Orchestration During Revalidation

If one capable connector succeeds and another fails:

```text
evaluate only successful observations
record partial_result
preserve operational uncertainty where relevant
```

Do not manufacture consensus.

---

# 37. Temporal Evidence and Match Engine

Sprint 21 should not introduce time-decay scoring merely because evidence is old.

Instead:

```text
current/fresh eligible evidence
→ available to evidence pipeline

stale evidence
→ policy-dependent current use or marked limitation

expired evidence
→ historical provenance, not current scoring input
```

Any actual score-weight changes require explicit Match Policy versioning.

---

# 38. Reassessment Trigger Rules

Material change events may trigger:

```text
mark current assessment stale
```

and then:

```text
incremental deterministic recalculation
```

Examples:

```text
confirmed profile disappeared after revalidation
username changed
new cross-link contradiction
external link materially changed
candidate ownership decision changed
```

Non-material events should not recalculate.

---

# 39. Reassessment Must Use Sprint 20 Fingerprints

Required:

```text
new material event
→ compute affected assessment input fingerprint

same fingerprint
→ no duplicate recalculation

changed fingerprint
→ new current assessment
```

Do not add a second independent reassessment mechanism.

---

# 40. Cluster Integration

After affected candidate assessment changes:

```text
IdentityReassessmentCoordinator
        ↓
affected candidate IDs
        ↓
IdentityClusterService
        ↓
input_fingerprint comparison
        ↓
rebuild only affected cluster scope
```

Preserve Sprint 18/20 conflict safety.

---

# 41. Timeline API

Suggested endpoints:

```text
GET /api/v1/identity/timeline
GET /api/v1/identity/timeline/{event_id}
```

Filters may include:

```text
candidate_profile_id
change_type
materiality
date range
```

All filters must remain user-scoped.

---

# 42. Review Queue API

Suggested:

```text
GET  /api/v1/identity/reviews
GET  /api/v1/identity/reviews/{review_id}
POST /api/v1/identity/reviews/{review_id}/resolve
POST /api/v1/identity/reviews/{review_id}/revalidate
```

Do not accept arbitrary backend action names.

Use a strict resolution enum.

---

# 43. Timeline Pagination

Timeline history may grow.

Implement:

```text
bounded page size
stable ordering
cursor pagination preferred
```

Do not return unbounded history.

---

# 44. Review Queue Pagination

Use bounded pagination.

Recommended default:

```text
20 items
```

Maximum should be configurable.

---

# 45. Timeline Frontend

Create a component/page such as:

```text
IdentityTimelineView.tsx
```

Display:

```text
what changed
when detected
current confidence state
materiality
affected profile
review status
```

Use conservative wording.

---

# 46. Safe Timeline Language

Examples:

```text
Observed username change

A previously observed external link is no longer present in recent successful observations

This profile may be unavailable and needs revalidation

A new conflicting signal was detected

The avatar image changed
```

Avoid:

```text
Your account was hacked

Someone stole your identity

This is definitely a different person
```

unless independently established by a separate, appropriate system.

---

# 47. Review Queue Frontend

Create:

```text
IdentityReviewQueue.tsx
```

Show:

```text
priority
reason
supporting change
why review is requested
available actions
```

Do not force users to understand internal evidence IDs.

---

# 48. Review Detail View

Display:

```text
previous known state
new observed state
observation timestamps
provenance sources
limitations
current assessment impact
```

Do not expose:

```text
operator secrets
raw cookies
internal environment values
cross-user data
```

---

# 49. Explain Revalidation

When revalidation is unavailable, show safe reasons:

```text
Connector disabled
Connector unavailable
Observation is still fresh
Execution budget reached
Revalidation already in progress
```

Do not expose internal secret errors.

---

# 50. Notifications

Sprint 21 may create in-app review notifications.

Do not add external email/SMS/push delivery unless already supported and explicitly required.

Notification creation should deduplicate with the review item.

---

# 51. Privacy Export

Extend export to include:

```text
identity change events
review items
review resolutions
revalidation linkage
timeline metadata
```

Include normalized user-scoped data only.

---

# 52. Privacy Shredding

Account deletion must remove:

```text
IdentityChangeEvent
IdentityReviewItem
review resolutions
user-scoped revalidation links
timeline-derived user data
```

Do not remove shared connector operational health unless it contains user-specific data.

---

# 53. Retention Policy

Define retention separately for:

```text
identity timeline
review items
operational revalidation logs
temporary connector output
```

Recommended:

```text
identity change history:
retained with user account unless user deletion policy requires removal

resolved review items:
retained for audit/history with user account

temporary raw connector output:
existing short-lived policy only
```

Do not store raw connector payloads merely to build a timeline.

---

# 54. RLS / Cross-User Isolation

Mandatory:

```text
User A cannot read User B timeline
User A cannot read User B change event
User A cannot read User B review item
User A cannot resolve User B review item
User A cannot request revalidation for User B fact
User A cannot infer User B temporal state
```

Any failure is P0.

---

# 55. Change Detection Tests

Required:

```text
same fact re-observed unchanged
→ no change event

new fact
→ FACT_APPEARED

normalized value changes
→ FACT_VALUE_CHANGED

fact becomes stale
→ FACT_BECAME_STALE

fact expires
→ FACT_EXPIRED

one successful run misses fact
→ FACT_ABSENCE_SUSPECTED
→ not FACT_DISAPPEARED

connector failure misses fact
→ no disappearance event

partial result misses fact
→ no confirmed disappearance

policy-compliant repeated successful absence
→ FACT_DISAPPEARED

disappeared fact observed again
→ FACT_REAPPEARED
```

---

# 56. Change Idempotency Tests

Required:

```text
same transition processed twice
→ one logical event

worker retry
→ no duplicate event

duplicate provenance
→ no duplicate change event
```

---

# 57. Materiality Tests

Required:

```text
display name change
→ configured low materiality

confirmed profile disappearance after revalidation
→ configured high materiality

connector failure
→ no identity materiality event

new contradiction
→ configured high review priority
```

---

# 58. Review Queue Tests

Required:

```text
material change
→ review item created according to policy

same unresolved change processed twice
→ one active review item

superseding change
→ old review item superseded if appropriate

resolve ACKNOWLEDGED
→ review status resolved

THIS_IS_STILL_MINE
→ canonical existing confirmation service used

THIS_IS_NOT_MINE
→ canonical existing dismissal/revocation service used

REQUEST_REVALIDATION
→ Sprint 20 orchestration controls enforced
```

---

# 59. Revalidation Tests

Required:

```text
request revalidation
→ orchestration run linked

missing consent
→ no connector execution

budget exhausted
→ no connector execution

connector unhealthy
→ no connector execution

connector test_only in production mode
→ no live execution

connector failure
→ operationally uncertain
→ no disappearance confirmation

successful revalidation
→ temporal state updated
```

---

# 60. Automatic Revalidation Tests

If implemented:

```text
feature disabled
→ no automatic run

eligible high-materiality stale fact
→ bounded orchestration request

cooldown active
→ no duplicate run

budget exhausted
→ no run

connector unavailable
→ no run
```

---

# 61. Reassessment Regression

Required:

```text
non-material timeline event
→ no reassessment

material fact change
→ affected candidate reassessed

same assessment fingerprint
→ no duplicate assessment

unrelated candidate
→ unchanged
```

---

# 62. Cluster Regression

Required:

```text
affected candidate assessment changes
→ affected cluster scope evaluated

unrelated cluster
→ unchanged

same cluster fingerprint
→ no rebuild

transitive conflict trap
→ still blocked

incremental result
→ semantically equivalent to full rebuild
```

---

# 63. Timeline Ordering Tests

Required:

```text
stable chronological ordering
same detected_at values
→ deterministic tie-breaker

pagination
→ no duplicate or missing events across pages
```

---

# 64. Temporal Race Tests

Test concurrent observations.

Example:

```text
Connector A observes old value
Connector B observes new value
results arrive out of order
```

The final temporal state must use:

```text
observation time
run lineage
policy
```

not merely database insertion order.

---

# 65. Out-of-Order Observation Policy

Define deterministic handling.

Recommended:

```text
older observation arrives after newer current state
→ preserve as historical provenance
→ do not automatically roll current state backward
```

Unless policy establishes that the older observation represents a later effective state.

Document the rule.

---

# 66. Clock Handling

Use UTC timestamps.

Do not trust connector-provided timestamps blindly.

Distinguish:

```text
observed_at
source_reported_at
detected_at
```

if source timestamps are supported.

---

# 67. Source Timestamp Trust

Connector-reported timestamps are untrusted metadata unless validated.

Do not use an arbitrary external timestamp to reorder canonical state without policy.

---

# 68. Timeline Integrity

Once created, historical change events should not be casually mutated.

Corrections may:

```text
supersede
annotate
link corrective event
```

rather than silently rewriting history.

---

# 69. Event Fingerprint

Recommended:

```text
SHA-256(
  user_scope
  canonical_fact_key
  change_type
  previous_state_fingerprint
  new_state_fingerprint
  change_policy_version
)
```

Exact serialization must be canonical and tested.

---

# 70. Review Fingerprint

Recommended:

```text
change_event_id
review_type
review_policy_version
```

or another deterministic equivalent.

Prevent duplicate active review items.

---

# 71. Database Models

Likely new:

```text
IdentityChangeEvent
IdentityReviewItem
```

Potentially extend:

```text
CandidateProvenanceObservation
IdentityOrchestrationRun
IdentityMatchAssessment
IdentityCluster
```

Do not create duplicate state tables where existing canonical models are sufficient.

---

# 72. Recommended Services

```text
TemporalFactStateService
IdentityChangeDetectionService
IdentityChangeMaterialityPolicy
IdentityReviewQueueService
IdentityRevalidationService
```

Reuse:

```text
CanonicalFactService
EvidenceFreshnessService
ConnectorOrchestrationService
IdentityReassessmentCoordinator
IdentityClusterService
```

---

# 73. Recommended Tasks

Possible:

```text
detect_identity_changes
process_identity_review_policy
schedule_eligible_revalidation
expire_temporal_facts
```

Do not create heavy connector execution inside these tasks.

Delegate external execution to Sprint 20 orchestration.

---

# 74. Periodic Expiry Task

A bounded periodic task may evaluate:

```text
stale_after
expires_at
```

Required:

```text
process in batches
user-scoped records remain isolated
idempotent transitions
no full-table uncontrolled scan
```

Use indexed queries.

---

# 75. Expiry Task Frequency

Recommended initial:

```text
hourly
```

or another bounded operational cadence.

Do not require minute-level polling unless justified.

---

# 76. Database Indexes

Consider indexes on:

```text
IdentityChangeEvent.user_id
IdentityChangeEvent.detected_at
IdentityChangeEvent.canonical_fact_key

IdentityReviewItem.user_id
IdentityReviewItem.status
IdentityReviewItem.priority
IdentityReviewItem.created_at

CandidateProvenanceObservation.stale_after
CandidateProvenanceObservation.expires_at
```

Verify query plans where practical.

---

# 77. Migration Strategy

Create one focused Sprint 21 migration unless repository conventions require otherwise.

Before:

```text
alembic heads
alembic current
```

After:

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

# 78. Existing Data Backfill

If new non-null temporal fields are added:

```text
use safe staged migration
```

Do not repeat the Sprint 20 `valid_from` non-null failure.

Recommended pattern:

```text
add nullable column
backfill deterministically
validate
make non-null if required
```

Test migration against representative existing rows.

---

# 79. API Security

All timeline/review endpoints require canonical current-user authorization.

Do not accept:

```text
user_id
```

from the request body as the ownership authority.

Derive user scope from authenticated context.

---

# 80. Review Resolution Concurrency

Use optimistic or transactional concurrency control.

Required:

```text
two simultaneous resolution requests
→ one canonical final resolution
→ no duplicate domain action
```

---

# 81. Revalidation Concurrency

Required:

```text
same review item requests revalidation twice concurrently
→ one active equivalent orchestration request
```

Reuse Sprint 20 idempotency.

---

# 82. No Alert Storms

One changing profile may generate multiple low-level fact transitions.

Review policy should group related changes where appropriate.

Example:

```text
same profile
same orchestration run
bio changed
external link changed
avatar changed
```

may create:

```text
multiple timeline events
+
one grouped review item
```

if policy determines they represent one review context.

---

# 83. Review Grouping

If implemented, use a deterministic grouping key.

Possible:

```text
user
candidate profile
material change window
review type
```

Do not hide individual timeline events.

---

# 84. Change Burst Window

Recommended initial grouping window:

```text
30 minutes
```

Configurable and versioned.

This is for review grouping, not fact semantics.

---

# 85. Timeline vs Review Queue

Required distinction:

```text
Timeline
→ all meaningful historical changes

Review Queue
→ subset requiring user attention
```

Not every timeline event needs a review item.

---

# 86. Review Queue Ordering

Recommended:

```text
priority descending
created_at ascending within priority
```

Use deterministic tie-breakers.

---

# 87. Critical Review Language

Even for `critical_review`, use:

```text
Important identity change needs review
```

not:

```text
Critical identity theft detected
```

unless such a conclusion is independently and appropriately established.

---

# 88. Existing Confirmed Profiles

Changes affecting `ConfirmedProfileReference` should receive stronger review priority than changes affecting an unreviewed candidate.

This affects:

```text
review priority
```

not automatically:

```text
identity match score
```

---

# 89. Dismissed Candidates

By default, do not continuously generate review items for dismissed candidates.

Historical timeline may remain.

Reactivation requires explicit policy.

---

# 90. Revoked Aliases

Do not automatically schedule new discovery/revalidation from revoked aliases.

Historical events remain user-scoped.

---

# 91. Anchor Version Changes

If the Identity Anchor version changes:

```text
existing assessments may become stale
```

but do not generate a misleading platform change event unless an actual external fact changed.

Anchor changes are user-domain events and may be recorded separately if useful.

---

# 92. User Decision Events

If included in timeline:

```text
profile confirmed by user
profile dismissed by user
alias revoked by user
```

label them clearly as:

```text
user action
```

not connector-detected change.

---

# 93. Provenance Display

For each change, display safe provenance such as:

```text
Observed through Maigret
Observed through OSINTgram
Confirmed through repeated successful revalidation
```

If connector is mocked/test-only:

```text
Test observation
```

must be clearly represented in development/test UI.

---

# 94. No Mock Data in Production Timeline

Mandatory:

```text
test_only connector
+
production environment
→ no synthetic timeline event
```

Test fixtures must be isolated from production data.

---

# 95. Metrics

Recommended:

```text
identity_change_events_total by change_type
review_items_created_total by priority
review_items_resolved_total by resolution
revalidation_requests_total
revalidation_skipped_total by reason
change_detection_deduplications_total
absence_suspected_total
absence_confirmed_total
incremental_reassessments_from_change_total
```

Avoid user IDs as metric labels.

---

# 96. Audit Events

Recommended:

```text
identity_change_detected
identity_review_created
identity_review_resolved
identity_revalidation_requested
identity_revalidation_completed
identity_fact_absence_suspected
identity_fact_disappearance_confirmed
```

Do not log raw secrets.

---

# 97. P0/P1 Defect Policy

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
bypass Sprint 20 budgets
bypass connector health controls
change PDSS semantics
automatically confirm identity
introduce global identity correlation
```

---

# 98. Implementation Order

## Phase A — Sprint 20 Audit

```text
full tests
frontend build
migration head
orchestration models
freshness
budgets
health
idempotency
incremental reassessment
cluster fingerprint behavior
privacy lifecycle
```

## Phase B — Temporal Domain

```text
temporal states
change types
confidence states
policy versions
```

## Phase C — Database

```text
IdentityChangeEvent
IdentityReviewItem
indexes
migration
existing-data safety
```

## Phase D — Change Detection

```text
state transitions
event fingerprints
out-of-order handling
idempotency
```

## Phase E — Materiality

```text
materiality policy
review priority
safe semantics
```

## Phase F — Review Queue

```text
review creation
deduplication
grouping
resolution
canonical domain actions
```

## Phase G — Revalidation

```text
review-triggered orchestration
automatic eligibility
cooldowns
operational uncertainty
```

## Phase H — Incremental Downstream Processing

```text
assessment fingerprint
affected reassessment
cluster fingerprint
affected rebuild
```

## Phase I — Privacy / API / Frontend

```text
export
shred
timeline API
review API
timeline UI
review queue UI
```

## Phase J — Verification

```text
RLS
temporal races
absence policy
idempotency
review concurrency
revalidation controls
incremental equivalence
full regression
```

---

# 99. Required Final Walkthrough

At completion report:

1. Actual Sprint 20 starting migration head.
2. Sprint 21 migration ID.
3. Final Alembic head.
4. Preflight backend test counts.
5. Final backend test counts.
6. Frontend production build result.
7. Sprint 20 feature verification matrix.
8. Maigret runtime status.
9. OSINTgram runtime status.
10. Mock/test-only behavior.
11. Sprint 21 feature flags and defaults.
12. Identity Change Policy version.
13. Identity Review Policy version.
14. Match Engine version decision.
15. Match Policy version decision.
16. Temporal fact states.
17. Absence confirmation policy.
18. Exact revalidation thresholds/windows.
19. IdentityChangeEvent schema.
20. IdentityReviewItem schema.
21. Change types.
22. Change confidence states.
23. Materiality levels.
24. Initial materiality mappings.
25. Event fingerprint algorithm.
26. Review fingerprint/deduplication algorithm.
27. Out-of-order observation policy.
28. Timestamp trust policy.
29. Reappearance behavior.
30. Historical event immutability behavior.
31. Review types.
32. Review statuses.
33. Review resolutions.
34. Mapping of review resolutions to canonical services.
35. Review grouping behavior.
36. Change burst window.
37. Revalidation cooldown.
38. Automatic revalidation eligibility.
39. Sprint 20 budget enforcement during revalidation.
40. Sprint 20 health enforcement during revalidation.
41. Test-only connector blocking during revalidation.
42. Operational uncertainty behavior.
43. Reassessment trigger rules.
44. Assessment fingerprint reuse.
45. Incremental cluster integration.
46. Incremental/full rebuild equivalence.
47. Timeline API routes.
48. Review API routes.
49. Pagination behavior.
50. Timeline frontend.
51. Review queue frontend.
52. Safe user-facing language examples.
53. Privacy export result.
54. Shred/account deletion result.
55. Retention policy.
56. RLS/cross-user isolation result.
57. Change detection tests.
58. Absence confirmation tests.
59. Connector failure vs disappearance tests.
60. Change idempotency tests.
61. Materiality tests.
62. Review queue tests.
63. Review resolution concurrency tests.
64. Revalidation idempotency tests.
65. Automatic revalidation tests if enabled.
66. Out-of-order observation tests.
67. Timeline pagination tests.
68. Incremental reassessment tests.
69. Incremental cluster tests.
70. Transitive conflict regression.
71. Maigret regression.
72. OSINTgram regression.
73. Sprint 20 orchestration regression.
74. Sprint 20 freshness regression.
75. Sprint 20 budget regression.
76. Sprint 20 health/circuit-breaker regression.
77. Sprint 19 secret-boundary regression.
78. Sprint 18 enrichment/clustering regression.
79. Sprint 17 deterministic match regression.
80. Sprint 16 candidate discovery regression.
81. Sprint 15 Identity Anchor regression.
82. Sprint 14 critical security regression.
83. PDSS regression.
84. P0–P3 issues found.
85. Minimal fixes applied.
86. Files created or modified.
87. Remaining accepted limitations.
88. GO / CONDITIONAL GO / NO-GO decision for Sprint 22.

Do not predetermine GO.

---

# 100. Definition of Done

## Baseline

- [ ] Sprint 20 actual migration head verified.
- [ ] Full preflight backend suite executed.
- [ ] Frontend build passes.
- [ ] Sprint 20 orchestration implementation verified.
- [ ] Sprint 20 freshness implementation verified.
- [ ] Sprint 20 budget behavior verified.
- [ ] Sprint 20 health behavior verified.
- [ ] Sprint 20 idempotency verified.
- [ ] Incremental reassessment verified.
- [ ] Incremental cluster fingerprint behavior verified.
- [ ] Mock vs live connector status remains truthful.

## Temporal State

- [ ] Canonical temporal states implemented.
- [ ] Observation time separated from detection time.
- [ ] Out-of-order observations handled deterministically.
- [ ] Connector failure cannot create disappearance.
- [ ] Partial result cannot create confirmed disappearance.
- [ ] Absence suspicion and confirmed disappearance are distinct.
- [ ] Reappearance supported.
- [ ] Historical provenance preserved.

## Change Detection

- [ ] IdentityChangeEvent implemented.
- [ ] Change types canonical.
- [ ] Event fingerprint implemented.
- [ ] Duplicate processing is idempotent.
- [ ] Same unchanged fact creates no change event.
- [ ] Material changes create deterministic events.
- [ ] Historical events are not silently rewritten.

## Materiality

- [ ] Materiality policy implemented.
- [ ] Review priority separated from evidence score.
- [ ] Conservative language used.
- [ ] Connector failures have no identity materiality.
- [ ] Confirmed-profile changes receive appropriate review priority.

## Review Queue

- [ ] IdentityReviewItem implemented.
- [ ] Review item deduplication works.
- [ ] Review grouping is deterministic if enabled.
- [ ] Review resolutions use strict enums.
- [ ] Canonical existing identity services are reused.
- [ ] Concurrent resolution is safe.
- [ ] Timeline remains separate from review queue.

## Revalidation

- [ ] Revalidation uses Sprint 20 orchestration.
- [ ] Consent remains enforced.
- [ ] Budgets remain enforced.
- [ ] Health/circuit breaker remains enforced.
- [ ] Connector availability remains enforced.
- [ ] Test-only connector cannot execute as live in production.
- [ ] Cooldowns prevent loops.
- [ ] Connector failure creates uncertainty, not disappearance.
- [ ] Duplicate revalidation requests are suppressed.

## Incremental Processing

- [ ] Material events trigger only affected reassessment.
- [ ] Non-material events do not trigger reassessment.
- [ ] Assessment fingerprints prevent duplicate history.
- [ ] Only affected cluster scope is evaluated.
- [ ] Cluster fingerprints prevent unnecessary rebuilds.
- [ ] Incremental and full rebuild results are semantically equivalent.
- [ ] Transitive conflict safety remains intact.

## API / Frontend

- [ ] Timeline API user-scoped.
- [ ] Review API user-scoped.
- [ ] Pagination bounded.
- [ ] Timeline UI implemented.
- [ ] Review queue UI implemented.
- [ ] Safe language used.
- [ ] Test observations clearly distinguished in test mode.
- [ ] No mock data presented as live production evidence.

## Privacy / Security

- [ ] Export includes timeline/review data.
- [ ] Shredding removes timeline/review data.
- [ ] User A cannot access User B timeline.
- [ ] User A cannot access User B reviews.
- [ ] User A cannot resolve User B review.
- [ ] User A cannot revalidate User B fact.
- [ ] No operator secrets exposed.
- [ ] No raw connector credentials stored.

## Regression

- [ ] Sprint 20 orchestration intact.
- [ ] Sprint 20 freshness intact.
- [ ] Sprint 20 budgets intact.
- [ ] Sprint 20 health controls intact.
- [ ] Sprint 19 secret boundary intact.
- [ ] Sprint 18 enrichment/clustering intact.
- [ ] Sprint 17 deterministic scoring intact.
- [ ] Sprint 16 candidate review intact.
- [ ] Sprint 15 Identity Anchor intact.
- [ ] Sprint 14 security baseline intact.
- [ ] PDSS semantics unchanged.
- [ ] Full backend suite passes.
- [ ] Frontend production build passes.

Release gate:

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 101. GO / NO-GO Gate for Sprint 22

## GO

Proceed when:

```text
temporal state transitions are deterministic
connector failure cannot create disappearance
absence requires policy-compliant confirmation
change events are idempotent
historical provenance is preserved
review items are user-scoped
review resolutions use canonical identity services
revalidation cannot bypass Sprint 20 controls
non-material changes do not cause unnecessary reassessment
incremental cluster rebuilding remains correct
privacy lifecycle passes
cross-user isolation passes
mock/test-only observations cannot masquerade as live evidence
P0 = 0
P1 = 0 or explicitly accepted
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
cross-user isolation
secret security
consent
connector execution controls
temporal integrity
change-event correctness
review decision integrity
privacy
```

## NO-GO

Do not begin Sprint 22 with:

```text
connector failure interpreted as profile disappearance
one missing result treated as confirmed deletion
duplicate change events from retries
review actions bypassing canonical identity services
revalidation bypassing budget/health/consent controls
mock connector data presented as live evidence
global cross-user timeline correlation
unbounded timeline queries
broken review concurrency
full-user or global reassessment for every low-level change
broken cluster conflict safety
broken privacy deletion
unresolved P0
unaccepted P1
```

---

# 102. Recommended Sprint 22 Direction

After temporal evidence and review workflows are stable, Sprint 22 should focus on:

```text
Real Connector Runtime Packaging
+
Connector Conformance Harness
+
Controlled Live Smoke Testing
+
Production Readiness Gate
```

This is the right point to close the current gap:

```text
architecture verified with mocks
≠
real connector runtime verified
```

Suggested Sprint 22 architecture:

```text
Connector Source / Immutable Revision
        ↓
Reproducible Runtime Image
        ↓
Connector Conformance Harness
   ├── capability contract
   ├── output schema
   ├── timeout behavior
   ├── process cleanup
   ├── secret boundary
   ├── parser resilience
   └── provenance normalization
        ↓
Environment-Gated Live Smoke Test
        ↓
Runtime Certification
        ↓
available
```

A connector should move from:

```text
test_only
```

to:

```text
available
```

only after passing the defined runtime certification gate.

---

# 103. Final Sprint 21 Principle

Sprint 21 is not about producing more alerts.

It is about distinguishing a real, meaningful identity change from:

```text
a repeated observation
a stale observation
a connector failure
a partial result
a temporary absence
a mock test result
```

The system should be able to say:

```text
This profile was observed previously.

A recent successful observation indicates that one public fact changed.

The change has been recorded with provenance.

The system does not claim why the change happened.

This change is important enough for the user to review.

If revalidation is requested, the existing orchestration layer will decide whether a connector may safely run.

Only materially affected identity assessments and clusters will be recalculated.
```

Target architecture after Sprint 21:

```text
VERIFIED IDENTITY ANCHOR
        ↓
UNIFIED CONNECTOR ORCHESTRATION
        ↓
MULTI-CONNECTOR PROVENANCE
        ↓
CANONICAL FACT STATE
        ↓
TEMPORAL EVIDENCE TIMELINE
        ↓
DETERMINISTIC CHANGE DETECTION
   ├── APPEARED
   ├── CHANGED
   ├── STALE
   ├── EXPIRED
   ├── ABSENCE SUSPECTED
   ├── DISAPPEARED
   ├── REAPPEARED
   └── CONFLICT
        ↓
MATERIALITY POLICY
        ↓
HUMAN REVIEW QUEUE
        ↓
USER-CONTROLLED RESOLUTION / REVALIDATION
        ↓
INCREMENTAL DETERMINISTIC REASSESSMENT
        ↓
AFFECTED CLUSTER REBUILD
```

Sprint 21 is complete when DigiZafe can preserve and explain the temporal evolution of user-scoped identity evidence; distinguish missing data from confirmed change; create idempotent, provenance-backed change events; prioritize only material changes for human review; route revalidation through the existing bounded orchestration controls; preserve user authority over identity decisions; and incrementally update only the assessments and clusters actually affected by verified material changes.

---

**End of Sprint 21 Implementation Guide**
