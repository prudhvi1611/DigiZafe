# DigiZafe --- Sprint 16 Implementation Guide

**Sprint:** 16 --- Maigret Candidate Discovery  
**Document version:** 1.0  
**Applies after:** Sprint 15 --- Verified Identity Anchor & Alias Foundation  
**Architecture baseline:** Sprint 0--15 implemented; Sprint 15 Identity Anchor available at `/app/identity`  
**Master context:** `MASTER_ENGINEERING_CONTEXT_2.md`  
**Primary goal:** Add bounded, isolated, provenance-preserving Maigret-based username discovery that produces reviewable **candidate profiles** from eligible Identity Anchor inputs without claiming that discovered accounts belong to the user.

> Sprint 15 established the trusted input boundary:
>
> ```text
> verified identifiers
> user-confirmed aliases
> user-confirmed profiles
> ```
>
> Sprint 16 adds the first candidate-discovery capability.
>
> The central invariant is:
>
> ```text
> MAIGRET HIT ≠ CONFIRMED IDENTITY
> ```
>
> A discovered profile is only a candidate observation until later identity-resolution logic evaluates it and the user can review it.

---

# 1. Sprint Goal

Integrate Maigret as a controlled discovery adapter for eligible username/handle inputs from the Verified Identity Anchor.

Expected flow:

```text
Verified Identity Anchor
        │
        ├── verified username-like identifiers
        └── active user-confirmed username/handle aliases
                    │
                    ▼
        Discovery Eligibility Policy
                    │
                    ▼
        Existing Consent + Feature Flags
                    │
                    ▼
        Isolated Maigret Execution
                    │
                    ▼
        Raw Tool Output Adapter
                    │
                    ▼
        Candidate Normalization
                    │
                    ▼
        Canonical Profile URL Deduplication
                    │
                    ▼
        CandidateProfile Persistence
                    │
                    ▼
        Candidate Review Queue / UI
```

Sprint 16 must establish a clean boundary between:

```text
trusted discovery input
tool observation
candidate profile
confirmed identity
```

Only the first three exist in this sprint.

---

# 2. Non-Negotiable Invariants

Preserve all Sprint 0--15 security, privacy, and product invariants.

## 2.1 Candidate semantics

Never represent a Maigret result as:

```text
This account is definitely yours.
```

Use:

```text
Possible profile
Candidate profile
Discovered using alias X
Needs review
```

## 2.2 No automatic anchor promotion

Never implement:

```text
Maigret hit
→ add to ConfirmedProfileReference

Maigret hit
→ add to verified Identity Anchor

Maigret hit
→ confirmed graph edge

Maigret hit
→ PDSS confirmed-risk contribution
```

## 2.3 No identity-match score yet

Sprint 16 must not implement:

```text
same-person probability
username rarity score
avatar similarity
negative identity evidence
identity clusters
collision scoring
```

Those belong to Sprint 17 and Sprint 18.

## 2.4 Self-only input

Maigret execution may use only eligible inputs derived from the authenticated user's active Identity Anchor.

Do not accept arbitrary third-party usernames through the protected product workflow.

## 2.5 Existing consent and egress boundaries remain authoritative

Identity Anchor membership is not consent.

Before external discovery:

```text
authenticated user
+ eligible self-owned input
+ required consent
+ feature enabled
+ quota/rate policy
+ approved execution path
```

must all pass.

---

# 3. Sprint 15 Inputs to Reuse

Before implementation inspect the actual Sprint 15 code and documentation.

Reuse:

```text
IdentityAnchorService
IdentityAnchorSummary
anchor version/revision
verified Identifier model
active IdentityAlias records
ConfirmedProfileReference model
canonical platform/source semantics
RLS pattern
audit system
privacy export
ShredService
identity graph service
existing worker architecture
existing scan/discovery architecture
existing centralized egress policy
```

Do not create a second identity-input system.

---

# 4. Maigret Integration Strategy

Maigret is an external OSINT username-enumeration tool.

Treat it as:

```text
untrusted external tool dependency
```

even when executed locally.

The integration should use a dedicated adapter:

```text
MaigretAdapter
```

or equivalent canonical connector abstraction.

Responsibilities:

```text
validate eligible username input
build bounded invocation
execute in isolated worker context
enforce timeout
enforce resource limits where available
capture structured output
normalize errors
return tool observations
```

It must not:

```text
decide identity ownership
write directly to Identity Anchor
write directly to PDSS
bypass consent
bypass audit
bypass worker isolation
```

---

# 5. Execution Architecture

Preferred:

```text
API
→ durable discovery request
→ Celery worker
→ Maigret adapter
→ bounded subprocess
→ structured output
→ normalization
→ CandidateProfile persistence
```

Do not execute a long Maigret scan synchronously inside the API request.

The API should return a durable run/job identifier.

PostgreSQL remains authoritative for durable state.

---

# 6. Subprocess Isolation

If Maigret is invoked through a subprocess, enforce:

```text
argument list execution
no shell=True
fixed executable path/configuration
bounded timeout
bounded output size
controlled working directory
controlled environment
no user-controlled CLI flags
safe process termination
```

Never build:

```text
shell command string from username
```

Use:

```text
subprocess argument array
```

The user controls only the validated username-like input, not arbitrary command options.

---

# 7. Resource Limits

Where supported by the deployment environment, bound:

```text
wall-clock timeout
CPU time
memory
process count
open files
output size
concurrent Maigret jobs
```

At minimum implement:

```text
hard execution timeout
concurrency limit
maximum usernames per discovery run
maximum persisted candidates per input/run
maximum raw output retained
```

A timed-out or killed Maigret process must produce a controlled run state.

---

# 8. Dependency Strategy

Pin the Maigret dependency/version.

Record:

```text
tool name
tool version
installation method
checksum/lockfile state where applicable
supported Python/runtime version
known limitations
```

Do not silently track an unpinned upstream main branch.

If Maigret is optional at deployment time:

```text
FEATURE_MAIGRET_DISCOVERY=false
```

must allow the core application to start and function normally.

---

# 9. Feature Flag

Add a bounded feature flag:

```text
FEATURE_MAIGRET_DISCOVERY
```

Recommended default:

```text
false
```

until Sprint 16 acceptance.

When disabled:

```text
no Maigret execution
no subprocess launch
no candidate discovery network activity
clear API/UI disabled state
```

---

# 10. Discovery Eligibility Policy

Create one canonical policy/service method.

Eligible inputs should normally include:

```text
active verified username-like identifiers
active user-confirmed aliases of type username/handle
```

Do not automatically use:

```text
display names
email local-parts
domains
revoked aliases
arbitrary profile URL username hints
other users' data
```

unless explicitly approved by a future policy.

Recommended internal contract:

```text
DiscoveryIdentityInput
├── source_record_id
├── input_type
├── canonical_value
├── display_value
├── ownership_class
├── anchor_id
└── anchor_version
```

---

# 11. Input Validation

Before execution:

```text
input belongs to authenticated user
input is active
input is eligible type
input matches length bounds
input contains no control characters
input passes Maigret-safe username policy
anchor version is recorded
```

Reject or skip unsafe inputs.

Do not transform an arbitrary string into shell syntax.

---

# 12. Consent Boundary

Use the existing canonical ConsentService.

The exact required consent scope must follow the verified discovery architecture.

Expected behavior:

```text
Maigret discovery without required consent
→ clean 403 or canonical denial
→ zero worker execution
→ zero subprocess launch
→ zero external discovery egress
```

Add a regression test.

The Sprint 14 consent-gateway defect must not recur in this new path.

---

# 13. Candidate Discovery Run

Create or extend a durable run model.

Possible name:

```text
CandidateDiscoveryRun
```

If the existing scan/connector-run architecture can represent this cleanly, reuse it instead of creating a redundant run system.

Required semantics:

```text
id
user_id
anchor_id
anchor_version
source/tool
status
started_at
completed_at
input_count
candidate_count
error_code
created_at
```

Recommended states:

```text
queued
running
completed
partially_completed
failed
cancelled
timed_out
```

Use existing canonical state-machine conventions where possible.

---

# 14. CandidateProfile

Sprint 16 introduces the candidate profile concept.

Recommended fields:

```text
id
user_id
discovery_run_id
anchor_id
anchor_version
source_input_id
source_input_type
source_input_value_reference
platform
profile_url
canonical_profile_url
username_observed
display_name_observed
observation_status
candidate_status
source_tool
source_tool_version
first_observed_at
last_observed_at
created_at
updated_at
```

Do not store unnecessary raw page content.

Recommended candidate status:

```text
unreviewed
dismissed
queued_for_review
```

If the user explicitly confirms ownership in Sprint 16, route that action through the existing Sprint 15 `ConfirmedProfileReference` service and record the provenance. Do not directly mutate anchor tables from the Maigret adapter.

---

# 15. Candidate vs Observation

Keep these concepts distinct where the architecture benefits:

```text
Tool observation
→ Maigret reported a result

Candidate profile
→ normalized profile candidate derived from one or more observations
```

For Sprint 16, a simple model may combine them if provenance is preserved.

Do not create premature complexity.

However, preserve enough information for Sprint 17 to later introduce:

```text
canonical facts
evidence clusters
independence groups
derived_from
observation counts
```

---

# 16. Canonical Profile URL

Implement deterministic canonicalization.

At minimum:

```text
lowercase hostname
normalize scheme according to policy
remove default ports
strip fragments
normalize trailing slash where safe
remove known tracking query parameters
preserve path case where platform semantics require it
```

Do not apply one destructive rule to every platform.

Prefer:

```text
platform-aware canonicalization
```

with a safe generic fallback.

---

# 17. Candidate Deduplication

Within the user's scope:

```text
same canonical platform
+ same canonical profile URL
→ same candidate identity location
```

Repeated observations should update:

```text
last_observed_at
observation count/provenance
```

rather than creating uncontrolled duplicates.

Do not globally deduplicate across users in a way that leaks existence or ownership.

---

# 18. Provenance

Every candidate must explain:

```text
which anchor input triggered discovery
which tool found it
which tool version
which run
when
which canonical URL
```

Recommended:

```text
source_tool = maigret
source_tool_version
discovery_run_id
source_input_id
anchor_version
```

Future Sprint 17 depends on this provenance.

---

# 19. Raw Output Retention

Prefer:

```text
structured normalized result
```

over indefinite raw Maigret output.

If raw output is retained for debugging:

```text
bounded size
short TTL
user-scoped access
redacted where required
excluded from normal logs
purged automatically
```

Do not persist terminal escape sequences or uncontrolled megabyte-scale output.

---

# 20. Error Normalization

Map tool failures into stable internal errors:

```text
tool_unavailable
invalid_input
timeout
resource_limit
partial_result
parse_error
execution_error
cancelled
```

Do not expose raw stack traces or subprocess internals to the frontend.

Store safe diagnostic metadata for operators.

---

# 21. Partial Results

A Maigret run may partially succeed.

Support:

```text
partially_completed
```

when some inputs/results succeed and others fail.

Do not discard valid candidates merely because one site or input failed.

Do not mark the whole system unhealthy because Maigret has external-site failures.

---

# 22. Rate and Concurrency Controls

Add bounded controls:

```text
per-user discovery rate
global concurrent Maigret jobs
per-run input limit
cooldown if appropriate
```

Reuse existing rate-limit infrastructure.

Prevent:

```text
unbounded repeated scans
worker starvation
subprocess storms
```

---

# 23. Worker Queue

Prefer a dedicated or controlled queue if existing architecture supports it:

```text
osint_discovery
```

or equivalent.

The goal is to prevent long-running Maigret jobs from starving critical queues.

Document:

```text
task name
queue
timeout
retry policy
concurrency
cancellation behavior
```

---

# 24. Retry Policy

Do not blindly retry every failure.

Recommended:

```text
tool unavailable → limited retry
temporary execution failure → bounded retry
timeout → no immediate retry or very limited retry
invalid input → no retry
parse error → no automatic repeated storm
cancelled → no retry
```

Use deterministic retry limits.

---

# 25. Cancellation

If the existing scan architecture supports cancellation, integrate it.

Cancellation should:

```text
mark cancellation requested
terminate subprocess safely
prevent new child work
persist final cancelled state
preserve already-normalized candidates according to policy
```

---

# 26. Audit Events

Use the canonical audit system.

Recommended events:

```text
maigret_discovery_requested
maigret_discovery_started
maigret_discovery_completed
maigret_discovery_failed
maigret_discovery_cancelled
candidate_profile_dismissed
candidate_profile_confirmed_by_user
```

Do not log raw sensitive output.

---

# 27. Candidate Confirmation

Sprint 16 may provide a user review action:

```text
Candidate
→ user confirms “This is my profile”
→ existing ConfirmedProfileReference service
```

Required:

```text
confirmation_method = user_asserted
provenance references candidate/discovery run
```

Then:

```text
candidate status → confirmed_by_user or linked
```

Use a status name consistent with canonical contracts.

This is not algorithmic identity verification.

---

# 28. Candidate Dismissal

Allow the user to dismiss a candidate:

```text
This is not my profile
```

Persist the dismissal.

Do not immediately delete it, because Sprint 17 can later use the rejection as explicit negative/user evidence.

However:

```text
dismissed candidate
→ must not become active anchor input
→ must not contribute to confirmed PDSS risk
```

---

# 29. Review Queue

Provide a user-scoped review list.

Recommended filters:

```text
unreviewed
confirmed by user
dismissed
platform
discovery run
```

Default view:

```text
unreviewed candidates
```

Do not rank by identity-match confidence yet.

Possible deterministic ordering:

```text
newest discovery
platform
username
```

---

# 30. Existing Identity Graph Integration

Add only candidate-level graph semantics.

Possible:

```text
Anchor
→ DISCOVERED_CANDIDATE_PROFILE
→ CandidateProfile
```

or equivalent existing graph pattern.

Candidate edges must be visibly non-confirmed.

Do not use:

```text
confirmed_same_identity
```

unless the user explicitly confirms and the existing confirmed-profile service creates the appropriate confirmed relationship.

---

# 31. PDSS Boundary

Sprint 16 must not silently increase authoritative PDSS because Maigret found a username match.

Default:

```text
unreviewed candidate
→ no confirmed-risk contribution
```

If existing Possible-track policy allows candidate evidence, integration must be explicitly documented and deterministic.

The safest Sprint 16 default is:

```text
CandidateProfile discovery
→ identity review only
→ no PDSS change
```

Sprint 21 later performs formal identity-resolution/PDSS integration.

---

# 32. Privacy Export

Extend privacy export to include:

```text
candidate discovery runs
candidate profiles
candidate statuses
provenance
user confirmations/dismissals
```

according to existing export policy.

Do not export internal secrets or raw tool internals unnecessarily.

---

# 33. Deletion and Shredding

Extend the existing deletion lifecycle.

Verify:

```text
account deletion
→ discovery runs inaccessible/deleted
→ candidates inaccessible/deleted
→ raw output purged
→ graph candidate edges removed/deactivated
→ caches invalidated
```

No orphaned active candidate data.

---

# 34. API Design

Adapt to canonical route conventions.

Possible routes:

```text
POST   /api/v1/identity/discovery/maigret
GET    /api/v1/identity/discovery/runs
GET    /api/v1/identity/discovery/runs/{run_id}
POST   /api/v1/identity/discovery/runs/{run_id}/cancel

GET    /api/v1/identity/candidates
GET    /api/v1/identity/candidates/{candidate_id}
POST   /api/v1/identity/candidates/{candidate_id}/confirm
POST   /api/v1/identity/candidates/{candidate_id}/dismiss
```

Do not expose another user's run/candidate existence.

---

# 35. Discovery Request

Prefer selecting eligible anchor inputs by ID rather than accepting arbitrary raw usernames.

Example:

```json
{
  "identity_input_ids": ["..."]
}
```

The backend must resolve those IDs and verify:

```text
same user
active
eligible
current anchor
```

A convenience option:

```text
use_all_eligible_aliases = true
```

may be supported if bounded.

Do not accept unrestricted:

```json
{
  "username": "some-other-person"
}
```

through the protected self-discovery endpoint.

---

# 36. Discovery Response

Return:

```text
run ID
status
selected input count
anchor version
created timestamp
```

Do not wait synchronously for full Maigret completion.

---

# 37. Candidate Response DTO

Recommended:

```text
id
platform
profile_url
username_observed
candidate_status
source_tool
source_input_summary
first_observed_at
last_observed_at
discovery_run_id
```

Do not expose internal subprocess command lines or raw diagnostic output.

---

# 38. Frontend Scope

Extend `/app/identity`.

Recommended sections/tabs:

```text
Identity Anchor
Candidate Profiles
Discovery Runs
```

Candidate cards should show:

```text
platform
profile URL
username observed
discovered from alias
discovery date
status
```

Actions:

```text
This is mine
Not mine
Open profile
```

Opening the public profile should be a normal user browser navigation, not an unrestricted backend fetch.

---

# 39. Discovery UX

Before starting discovery, clearly show:

```text
which aliases/usernames will be searched
that external public services may be queried
that results are candidates, not confirmed identities
```

Use the existing consent workflow.

Do not imply:

```text
DigiZafe will find every account
```

---

# 40. Candidate Status UX

Use clear labels:

```text
Needs review
Confirmed by you
Dismissed
```

Do not use:

```text
Verified match
98% yours
AI confirmed
```

---

# 41. Empty and Failure States

Support:

```text
no eligible aliases
feature disabled
consent required
run queued
run running
no candidates found
partial results
tool timeout
tool unavailable
```

A Maigret failure must not crash the Identity page.

---

# 42. Observability

Add low-cardinality metrics if supported:

```text
maigret_runs_total{status}
maigret_run_duration_seconds
maigret_candidates_total{platform}
maigret_subprocess_timeouts_total
```

Be cautious with platform labels if the catalog is unbounded; use a bounded registry or omit the label.

Never label metrics with:

```text
username
user ID
profile URL
alias
email
```

---

# 43. Logging

Structured logs may include:

```text
run ID
task ID
tool version
status
candidate count
duration
safe error code
```

Do not log:

```text
raw output
full user alias where unnecessary
profile page content
credentials
cookies
tokens
```

---

# 44. Security Tests

Required:

```text
arbitrary username injection blocked
shell metacharacters cannot become CLI options
shell=False / argument-array execution verified
cross-user input IDs rejected
cross-user run access rejected
cross-user candidate access rejected
feature disabled → zero execution
consent denied → zero execution
timeout terminates process
output size bounded
```

---

# 45. Unit Tests

Test:

```text
input eligibility
username validation
canonical profile URL
platform normalization
candidate deduplication
error normalization
status transitions
anchor-version capture
```

---

# 46. Adapter Tests

Use controlled fixtures/mocks.

Test:

```text
successful structured output
no results
partial results
malformed output
timeout
non-zero exit
tool unavailable
large output
```

Do not make the normal test suite depend on live public websites.

---

# 47. Worker Tests

Test:

```text
task registration
queue routing
run queued → running → completed
partial completion
failure
timeout
cancellation
duplicate task delivery
idempotent candidate persistence
```

---

# 48. API Tests

Test:

```text
request discovery
feature disabled
consent missing
no eligible inputs
invalid input IDs
cross-user input IDs
list own runs
get own run
cancel own run
list own candidates
confirm own candidate
dismiss own candidate
cross-user candidate actions
```

---

# 49. Privacy Tests

Verify:

```text
export includes runs/candidates
deletion removes candidate data
raw-output TTL works if raw output exists
graph candidate edges cleaned
cache invalidation
```

---

# 50. Sprint 15 Regression

Re-run:

```text
Identity Anchor retrieval
alias add/revoke
confirmed profile add/revoke
zero network fetch on profile creation
anchor versioning
privacy export
ShredService
cross-user identity isolation
frontend identity page build
```

---

# 51. Sprint 14 Regression

Re-run critical baseline tests:

```text
Deep scan without consent → 403
actual zero egress
Surface scan functional
PDSS deterministic
Confirmed/Possible semantics unchanged
Groq fallback
Residual ML disabled path
```

---

# 52. Migration Strategy

Create a focused migration only if new durable tables are required.

Possible:

```text
candidate_discovery_runs
candidate_profiles
candidate_profile_observations
```

Do not create `candidate_profile_observations` unless the repository genuinely needs separate observation persistence now.

Required verification:

```text
Sprint 15 head → Sprint 16 head
fresh DB → Sprint 16 head
one intended migration head
application startup
```

Important: verify the actual Sprint 15 migration head. Do not assume the old Sprint 14 head `56863a2cf14f` is still current after Sprint 15.

---

# 53. Suggested Backend Layout

Adapt to the actual repository.

Possible:

```text
backend/app/
├── models/
│   └── candidate_profile.py
├── schemas/
│   └── identity_discovery.py
├── services/
│   ├── candidate_discovery_service.py
│   └── candidate_review_service.py
├── connectors/
│   └── maigret_adapter.py
├── tasks/
│   └── identity_discovery.py
└── api/v1/
    └── identity_discovery.py
```

Do not create duplicate abstractions if existing scan/connector/task layers fit.

---

# 54. Suggested Frontend Layout

Possible:

```text
frontend/src/
├── api/
│   └── identityDiscovery.ts
├── components/identity/
│   ├── CandidateProfileList.tsx
│   ├── CandidateProfileCard.tsx
│   ├── DiscoveryRunList.tsx
│   └── StartDiscoveryDialog.tsx
└── pages/
    └── existing IdentityPage.tsx
```

Prefer extending the existing `/app/identity` experience.

---

# 55. Documentation

Create or update:

```text
docs/identity/maigret-candidate-discovery.md
docs/identity/candidate-profile-semantics.md
docs/security/maigret-execution-boundary.md
docs/privacy/candidate-discovery-data-handling.md
```

Document:

```text
eligible inputs
consent boundary
execution isolation
tool version
candidate semantics
deduplication
retention
privacy lifecycle
known limitations
```

---

# 56. Known Maigret Limitations to Communicate

The system must acknowledge:

```text
username existence does not prove identity
sites may return false positives
sites may block or rate-limit requests
site definitions can become stale
profiles may be deleted/private/renamed
same username may belong to different people
tool results may vary over time
```

These limitations should influence UX and future Sprint 17 scoring.

---

# 57. Implementation Order

## Phase A — Preflight

```text
inspect Sprint 15 implementation
verify actual migration head
verify anchor summary/input contract
verify worker/connector conventions
```

## Phase B — Domain

```text
discovery run
→ candidate profile
→ provenance
→ status
→ deduplication
```

## Phase C — Adapter

```text
pinned Maigret
→ bounded subprocess
→ timeout
→ structured output
→ error normalization
```

## Phase D — Orchestration

```text
eligible anchor input
→ consent
→ feature flag
→ durable run
→ worker
→ adapter
→ normalization
→ candidate persistence
```

## Phase E — Review

```text
candidate list
→ confirm via Sprint 15 service
→ dismiss
→ audit
```

## Phase F — Privacy/Graph

```text
export
→ deletion
→ graph candidate edges
```

## Phase G — Frontend

```text
start discovery
→ run progress
→ candidate review
```

## Phase H — Verification

```text
unit
→ adapter
→ worker
→ API
→ security
→ privacy
→ frontend
→ Sprint 15 regression
→ Sprint 14 regression
```

---

# 58. P0/P1 Defect Policy

For defects discovered during implementation:

```text
reproduce
→ classify
→ regression test
→ smallest safe fix
→ affected tests
→ document
```

Stop for approval only if the fix would:

```text
change frozen security/privacy invariants
change PDSS semantics
require major architectural redesign
introduce breaking API changes
expand into Sprint 17+
```

---

# 59. Required Final Walkthrough

At completion provide:

```text
1. Architecture implemented
2. Actual Sprint 15 starting migration head
3. Sprint 16 migration ID and final head
4. Maigret version and dependency strategy
5. Execution isolation controls
6. Feature flag behavior
7. Consent and zero-execution results
8. CandidateProfile schema and semantics
9. Candidate deduplication behavior
10. API endpoints
11. Worker/task/queue behavior
12. Frontend changes
13. Candidate confirm/dismiss behavior
14. Identity graph integration
15. Privacy export/deletion results
16. Security test results
17. Full backend test results
18. Frontend build results
19. Sprint 15 regression results
20. Sprint 14 regression results
21. P0–P3 issues found
22. Minimal fixes applied
23. Files created/modified
24. Remaining limitations
25. GO / CONDITIONAL GO / NO-GO for Sprint 17
```

Do not predetermine GO.

---

# 60. Definition of Done

## Discovery input

- [ ] Only eligible active Identity Anchor inputs can trigger Maigret.
- [ ] Cross-user inputs are rejected.
- [ ] Revoked aliases are excluded.
- [ ] Anchor version is captured.
- [ ] Arbitrary third-party username input is not exposed through the protected workflow.

## Consent and feature control

- [ ] `FEATURE_MAIGRET_DISCOVERY` exists.
- [ ] Disabled state causes zero execution.
- [ ] Missing consent causes zero worker/subprocess execution.
- [ ] Existing consent service is reused.

## Maigret execution

- [ ] Version is pinned.
- [ ] Execution occurs outside synchronous API handling.
- [ ] No `shell=True`.
- [ ] User input cannot control arbitrary CLI flags.
- [ ] Timeout exists.
- [ ] Concurrency is bounded.
- [ ] Output is bounded.
- [ ] Failure states are normalized.

## Candidate semantics

- [ ] Maigret results persist only as candidates.
- [ ] No automatic Identity Anchor promotion.
- [ ] No identity-match probability.
- [ ] Candidate provenance is complete.
- [ ] Canonical URL deduplication works.
- [ ] Repeated observations do not create uncontrolled duplicates.
- [ ] User can confirm or dismiss candidates.
- [ ] Confirmation routes through Sprint 15 confirmed-profile logic.
- [ ] Dismissal remains available as future negative/user evidence.

## Security

- [ ] Cross-user run isolation passes.
- [ ] Cross-user candidate isolation passes.
- [ ] Command injection tests pass.
- [ ] Timeout termination works.
- [ ] Feature-disabled zero execution passes.
- [ ] Consent-denied zero execution passes.

## Privacy

- [ ] Export includes appropriate candidate data.
- [ ] Account deletion handles discovery data.
- [ ] Raw output retention is bounded or disabled.
- [ ] Graph candidate data is cleaned correctly.

## Frontend

- [ ] `/app/identity` exposes candidate discovery/review.
- [ ] Candidate semantics are clearly non-confirmed.
- [ ] Run states are visible.
- [ ] Confirm/dismiss works.
- [ ] Failure/empty/disabled states work.
- [ ] Production build passes.

## Regression

- [ ] Sprint 15 Identity Anchor tests pass.
- [ ] Sprint 14 critical baseline tests pass.
- [ ] Deep-without-consent remains 403 + zero egress.
- [ ] Surface scanning remains functional.
- [ ] PDSS semantics remain unchanged.
- [ ] Groq fallback remains unchanged.
- [ ] Residual ML disabled behavior remains unchanged.

## Release gate

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 61. GO / NO-GO Gate for Sprint 17

## GO

Proceed when:

```text
Maigret execution is bounded and isolated
only eligible self-owned anchor inputs can trigger discovery
consent and feature flags fail closed
candidate provenance is complete
candidate URLs are canonically deduplicated
candidate review works
no candidate is automatically treated as confirmed identity
privacy lifecycle passes
Sprint 14–15 regressions remain green
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
ownership
candidate semantics
execution isolation
consent
privacy
provenance
deduplication
```

## NO-GO

Do not begin Sprint 17 with:

```text
arbitrary username scanning
cross-user discovery
command injection risk
unbounded subprocess execution
consent bypass
feature-flag bypass
candidate automatically promoted to identity
missing provenance
broken privacy deletion
migration instability
unresolved P0
unaccepted P1
```

---

# 62. Handoff to Sprint 17

Sprint 17 will consume:

```text
CandidateProfile
candidate provenance
discovery run
source input
anchor version
user confirmation
user dismissal
canonical profile URL
source tool/version
```

Sprint 17 will add:

```text
IdentityEvidence
IdentityMatchAssessment
positive evidence
negative evidence
evidence independence groups
canonical fact deduplication
source reliability semantics
username rarity/surprisal
collision detection
confidence bands
abstention/review-required state
Why Matched
Why Not Matched
```

Sprint 17 must preserve:

```text
candidate discovery
≠ identity proof
```

---

# 63. Final Sprint 16 Principle

Sprint 16 is a **discovery sprint**, not an identity-verification sprint.

The system should be able to say:

```text
You confirmed this username belongs to you.

Maigret searched supported public sites for that username.

These profiles were observed.

They may or may not belong to you.

Review them now; later evidence-aware identity resolution can assess them.
```

The target architecture after Sprint 16 is:

```text
VERIFIED IDENTITY ANCHOR
        │
        ▼
ELIGIBLE USERNAME INPUTS
        │
        ▼
BOUNDED MAIGRET EXECUTION
        │
        ▼
CANDIDATE PROFILES
        │
        ├── CONFIRMED BY USER
        ├── DISMISSED BY USER
        └── UNREVIEWED
        │
        ▼
SPRINT 17
EVIDENCE-INTEGRITY-AWARE IDENTITY MATCH ENGINE
```

Sprint 16 is complete when DigiZafe can safely discover, normalize, persist, deduplicate, explain, review, export, and delete Maigret-derived candidate profiles without ever confusing username discovery with identity ownership.

---

**End of Sprint 16 Implementation Guide**
