# DigiZafe --- Sprint 17 Implementation Guide

**Sprint:** 17 --- Evidence-Integrity-Aware Identity Match Engine  
**Document version:** 1.0  
**Applies after:** Sprint 16 --- Maigret Candidate Discovery  
**Architecture baseline:** Sprint 0--16 implemented; Sprint 16 final migration head reported as `5c9980e0d0ad`  
**Master context:** `MASTER_ENGINEERING_CONTEXT_2.md`  
**Primary goal:** Build a deterministic, explainable, evidence-integrity-aware identity resolution engine that assesses whether a discovered `CandidateProfile` is likely associated with the user's Verified Identity Anchor, while preserving uncertainty, negative evidence, evidence dependence, collision risk, and human review.

> Sprint 16 established:
>
> ```text
> Verified Identity Anchor
> → eligible self-owned username inputs
> → consent/feature-gated Maigret discovery
> → CandidateDiscoveryRun
> → CandidateProfile
> → user review
> ```
>
> Sprint 17 adds the reasoning layer between **candidate discovery** and **identity confidence**.
>
> The central rule is:
>
> ```text
> evidence supports a hypothesis;
> evidence does not become proof merely because there is more of it.
> ```

---

# 1. Sprint Goal

Create a canonical identity-match engine that can answer:

```text
Why might this candidate belong to the user?
Why might it not belong to the user?
Which evidence is independent?
Which evidence is duplicated or derived?
How common is the matched username?
Are there contradictions?
Is there enough evidence to make an assessment?
Should the system abstain and require review?
```

Expected architecture:

```text
Verified Identity Anchor
        │
        ├── verified identifiers
        ├── user-confirmed aliases
        └── confirmed profiles
        │
        ▼
CandidateProfile
        │
        ├── Maigret provenance
        ├── platform
        ├── canonical profile URL
        └── observed username
        │
        ▼
Evidence Collection / Normalization
        │
        ├── positive evidence
        ├── negative evidence
        ├── neutral/unknown evidence
        ├── source reliability
        ├── independence groups
        └── collision context
        │
        ▼
Identity Match Engine
        │
        ├── deterministic scoring
        ├── confidence band
        ├── contradiction penalties
        ├── evidence caps
        └── abstention
        │
        ▼
IdentityMatchAssessment
        │
        ├── likely_match
        ├── possible_match
        ├── insufficient_evidence
        ├── unlikely_match
        └── conflicting_evidence
        │
        ▼
Explainability
        ├── Why Matched
        ├── Why Not Matched
        └── Evidence Breakdown
```

Sprint 17 must **not** silently promote algorithmic assessments into verified ownership.

---

# 2. Sprint 16 Preflight Corrections

Before implementing Sprint 17, verify the actual Sprint 16 implementation rather than relying only on the walkthrough summary.

Two statements in the Sprint 16 walkthrough require explicit clarification:

## 2.1 Candidate deduplication wording

The walkthrough says:

```text
Profiles are deduplicated globally across users via a strictly user-scoped canonical URL normalizer.
```

These two concepts conflict.

The required invariant is:

```text
deduplication is user-scoped
```

Preferred uniqueness semantics:

```text
user_id
+ canonical platform
+ canonical profile URL
→ one candidate identity location within that user's scope
```

Do not create a globally observable cross-user candidate identity index that leaks whether another user discovered or claimed a profile.

If the implementation is actually globally deduplicating candidate rows across users, fix this before or as a P0/P1 prerequisite to Sprint 17.

## 2.2 “Sandbox” wording

The walkthrough says discovered data operates in a sandbox.

Do not claim a dedicated sandbox unless one actually exists.

If Maigret runs as a bounded subprocess inside the existing Celery worker, document it accurately as:

```text
bounded subprocess isolation inside the worker execution boundary
```

not a dedicated security sandbox.

These clarifications do not automatically block Sprint 17 if the actual implementation is safe.

---

# 3. Non-Negotiable Identity Semantics

Preserve:

```text
discovered ≠ owned
similar ≠ verified
likely ≠ confirmed
user-confirmed ≠ externally verified
algorithmic assessment ≠ ownership proof
```

The match engine may produce an assessment.

It must not produce:

```text
verified identity
```

unless the existing verification system independently establishes that state.

---

# 4. Human Review Remains Authoritative for User Confirmation

Existing Sprint 16 actions remain:

```text
This is mine
Not mine
```

The algorithm may assist review, but must not replace explicit confirmation.

Required:

```text
high algorithmic score
→ still not automatically ConfirmedProfileReference
```

Only an approved explicit user action or a future independently verified mechanism may create that relationship.

---

# 5. Core Domain Concepts

Sprint 17 should introduce or formalize:

```text
IdentityEvidence
IdentityMatchAssessment
EvidenceIndependenceGroup
SourceReliabilityPolicy
CollisionContext
MatchExplanation
```

Do not create unnecessary tables if some concepts can remain deterministic service-layer structures.

Persist only what is required for:

```text
reproducibility
auditability
review
recalculation
privacy export
```

---

# 6. IdentityEvidence

An evidence item is a normalized observation relevant to the hypothesis:

```text
H = CandidateProfile belongs to the user represented by IdentityAnchor
```

Recommended conceptual fields:

```text
id
user_id
anchor_id
anchor_version
candidate_profile_id
evidence_type
direction
strength_class
source_type
source_reference
source_reliability_class
independence_group
canonical_fact_key
observed_value_reference
derived_from
created_at
expires_at
status
```

Recommended direction:

```text
positive
negative
neutral
unknown
```

Do not force every observation to support or oppose the match.

---

# 7. Evidence Types

Initial Sprint 17 evidence should remain conservative and based on already available trusted data.

Possible evidence types:

```text
exact_username_match
normalized_username_match
historical_alias_match
confirmed_profile_cross_reference
verified_identifier_cross_reference
platform_username_consistency
explicit_user_confirmation
explicit_user_dismissal
username_collision_risk
contradictory_profile_reference
stale_observation
insufficient_profile_data
```

Only implement evidence types supported by actual available data.

Do not invent profile facts that Maigret did not collect.

---

# 8. Explicit User Evidence

Treat user actions as a distinct evidence class.

Examples:

```text
user confirmed candidate
→ strong explicit positive user evidence

user dismissed candidate
→ strong explicit negative user evidence
```

Do not reinterpret dismissal as a weak algorithmic signal.

Preserve provenance:

```text
who
when
candidate
action
```

A later algorithmic recalculation must not silently override an explicit user dismissal.

---

# 9. Evidence Direction

Each evidence type must have a documented direction policy.

Example:

```text
exact match to active user-confirmed alias
→ positive

exact match to very common username
→ positive but collision-limited

explicit user dismissal
→ negative

candidate conflicts with a confirmed profile identity
→ negative or conflicting

missing data
→ unknown, not negative
```

Important:

```text
absence of evidence ≠ evidence of absence
```

Do not penalize candidates merely because a platform does not expose a field.

---

# 10. Canonical Facts

Multiple raw observations may represent the same underlying fact.

Example:

```text
Maigret result URL
platform parser result
normalized username field
```

may all derive from:

```text
candidate uses username "yuva_dev" on GitHub
```

Create a canonical fact key or equivalent deterministic deduplication mechanism.

Example:

```text
platform:github|fact:username|value:yuva_dev
```

Do not count duplicated representations as independent evidence.

---

# 11. Evidence Independence

This is a core Sprint 17 requirement.

Evidence that comes from the same underlying source or fact must not be multiplied.

Example:

```text
Maigret reports profile URL
URL parser extracts username
candidate row stores same username
```

These are not three independent signals.

Assign an:

```text
independence_group
```

or equivalent.

Possible groups:

```text
maigret_profile_observation:<candidate>
user_assertion:<record>
verified_identifier:<record>
confirmed_profile:<record>
cross_link:<source>
```

The scoring engine must cap contribution per independence group.

---

# 12. derived_from Lineage

Evidence transformations must preserve lineage.

Example:

```text
Maigret raw observation
→ normalized candidate URL
→ extracted username
→ exact alias comparison
```

The final evidence should retain:

```text
derived_from
```

or equivalent provenance.

This prevents derived facts from masquerading as independent sources.

---

# 13. Source Reliability

Introduce a deterministic reliability policy.

Possible classes:

```text
authoritative
high
medium
low
unknown
```

Examples:

```text
existing DigiZafe ownership verification
→ authoritative for the verified identifier itself

explicit user confirmation
→ high user-asserted evidence

Maigret site existence observation
→ medium/variable discovery evidence

derived URL parsing
→ reliability inherited from source observation

unknown third-party metadata
→ low/unknown
```

Do not claim that Maigret proves ownership.

Reliability must be documented per source/evidence type.

---

# 14. Reliability Is Not Identity Confidence

Keep separate:

```text
source reliability
```

and:

```text
identity-match confidence
```

A highly reliable observation that:

```text
a profile exists
```

does not mean it is highly likely that:

```text
the profile belongs to this user
```

---

# 15. Username Collision Risk

An exact username match can be weak or strong depending on how collision-prone the username is.

Sprint 17 should introduce a bounded collision-risk policy.

Possible factors:

```text
username length
character diversity
dictionary/common-name patterns
numeric suffix patterns
frequency within the user's own candidate set
number of distinct candidate profiles discovered for the same username
```

Do not pretend to know global internet username frequency without a reliable dataset.

If no validated external frequency dataset exists, use:

```text
local collision heuristics
```

and label them accordingly.

---

# 16. Username Rarity / Surprisal

If implemented, use a deterministic heuristic rather than unsupported probability claims.

Possible output:

```text
high_collision
medium_collision
low_collision
unknown
```

Avoid:

```text
this username has a 0.003% collision probability
```

unless backed by a validated model/dataset.

A distinctive username may receive a stronger evidence cap than a common username.

---

# 17. Negative Evidence

Sprint 17 must treat negative evidence as first-class.

Examples:

```text
explicit user dismissal
conflicting confirmed profile
known different username identity on same canonical profile
candidate associated with incompatible verified cross-reference
```

Only use actual supported facts.

Do not infer sensitive personal attributes.

Do not create negative evidence from:

```text
missing avatar
missing bio
private profile
no display name
```

unless a documented evidence rule justifies it.

---

# 18. Contradictions

Create explicit contradiction handling.

Possible assessment state:

```text
conflicting_evidence
```

Examples:

```text
strong positive alias match
+
explicit user dismissal

or

candidate URL already confirmed as not owned
+
new rediscovery
```

The engine should surface the conflict rather than average it away.

---

# 19. Evidence Expiration and Staleness

Evidence may become stale.

Examples:

```text
candidate observed months ago
profile URL no longer current
alias revoked after discovery
anchor version changed
```

Sprint 17 should define:

```text
active
stale
superseded
revoked
```

or equivalent.

Do not silently use revoked anchor facts as current positive evidence.

---

# 20. Anchor Version Awareness

Every assessment must record:

```text
anchor_version
```

used for evaluation.

If the active anchor changes:

```text
alias added
alias revoked
confirmed profile added
confirmed profile revoked
verified identifier eligibility changed
```

existing assessments may become:

```text
stale
```

or require recalculation.

---

# 21. Candidate Version Awareness

If candidate facts change, assessments must be reproducible.

Record a candidate revision or deterministic assessment input fingerprint if useful.

At minimum preserve:

```text
candidate updated_at
evidence set version/fingerprint
engine version
policy version
```

---

# 22. IdentityMatchAssessment

Recommended conceptual fields:

```text
id
user_id
anchor_id
anchor_version
candidate_profile_id
engine_version
policy_version
assessment_status
score
confidence_band
positive_evidence_count
negative_evidence_count
independent_group_count
collision_class
created_at
updated_at
stale_at
```

Do not expose `score` as a probability unless it truly is calibrated as one.

Prefer:

```text
match score
```

rather than:

```text
probability
```

---

# 23. Assessment Status

Recommended:

```text
likely_match
possible_match
insufficient_evidence
unlikely_match
conflicting_evidence
```

Optional:

```text
confirmed_by_user
dismissed_by_user
```

may remain candidate review states rather than algorithmic assessment states.

Keep user action and algorithm output semantically separate.

---

# 24. Confidence Bands

Recommended UI-facing bands:

```text
Strong supporting evidence
Moderate supporting evidence
Limited evidence
Conflicting evidence
Evidence against match
```

or concise canonical equivalents.

Avoid false precision.

If a numeric score exists internally, pair it with:

```text
explanation
evidence counts
independence groups
collision context
```

---

# 25. Deterministic Scoring Engine

The Sprint 17 engine must be deterministic.

Same:

```text
anchor version
candidate facts
evidence set
engine version
policy version
```

must produce the same result.

Do not use an LLM as the authoritative scorer.

Do not use Groq as the authoritative scorer.

LLMs may later summarize an already-computed assessment, but deterministic evidence logic remains authoritative.

---

# 26. Recommended Scoring Shape

Use a bounded additive or rule-based model with:

```text
positive contributions
negative contributions
independence-group caps
collision modifiers
contradiction rules
minimum evidence thresholds
abstention
```

Conceptually:

```text
raw_positive
- raw_negative
→ independence caps
→ collision adjustment
→ contradiction rules
→ evidence sufficiency gate
→ bounded match score
→ assessment status
```

The exact weights must be documented and tested.

---

# 27. No Double Counting

Required invariant:

```text
one underlying fact
→ one bounded contribution
```

Example:

```text
username in URL
username field
Maigret queried username
```

must not become three independent exact-match bonuses.

Add explicit tests.

---

# 28. Evidence Caps

Possible caps:

```text
per canonical fact
per independence group
per source family
per evidence type
```

The purpose is to prevent:

```text
many correlated observations
→ artificial certainty
```

---

# 29. Minimum Evidence Threshold

An exact username match alone should not always produce `likely_match`.

Especially:

```text
common username
+
no independent corroboration
```

should normally result in:

```text
possible_match
```

or:

```text
insufficient_evidence
```

depending on policy.

---

# 30. Abstention

The engine must be able to say:

```text
insufficient_evidence
```

This is a successful outcome.

Do not force every candidate into:

```text
match
not match
```

Abstention is required when evidence is weak, sparse, or too dependent.

---

# 31. Explicit User Confirmation Override Semantics

If the user has already confirmed:

```text
This is mine
```

the UI should display:

```text
Confirmed by you
```

The algorithmic assessment may still be stored for explanation, but must not downgrade the user action into an algorithmic label.

Similarly:

```text
Not mine
```

must remain explicit user dismissal.

---

# 32. Why Matched

Create structured explanations.

Example:

```text
Why this may be your profile:
- Exact match to an active username you confirmed.
- The username is classified as low-collision by the local heuristic.
- A separate confirmed profile cross-reference supports the candidate.
```

Generate from structured evidence templates.

Do not use free-form LLM reasoning as the authoritative explanation.

---

# 33. Why Not Matched

Examples:

```text
Why confidence is limited:
- The username is collision-prone.
- Only one independent evidence group is available.
- No independent corroborating identity evidence is available.
```

Or:

```text
Evidence against the match:
- You previously dismissed this candidate.
```

---

# 34. Explanation Integrity

Every explanation line must map to actual evidence.

Required:

```text
explanation item
→ evidence ID(s)
→ evidence rule
```

No hallucinated explanation.

---

# 35. Evidence Collection Service

Create or extend:

```text
IdentityEvidenceService
```

Responsibilities:

```text
collect supported evidence
normalize evidence
assign canonical fact keys
assign independence groups
assign source reliability
mark direction
preserve lineage
```

It must not:

```text
perform Maigret discovery
fetch arbitrary profile pages
use avatar similarity
infer sensitive attributes
```

---

# 36. Identity Match Engine Service

Create:

```text
IdentityMatchEngine
```

Responsibilities:

```text
load candidate
load current anchor
collect evidence
deduplicate canonical facts
apply independence caps
apply collision policy
apply negative evidence
detect contradictions
calculate deterministic score
assign assessment status
build structured explanation
persist assessment
```

---

# 37. Assessment Recalculation

Support recalculation when:

```text
candidate discovered again
candidate confirmed/dismissed
anchor changes
evidence changes
policy version changes
```

Use existing worker architecture if recalculation may be asynchronous.

Avoid synchronous fan-out across every candidate during a single API request.

---

# 38. Recalculation Idempotency

Required:

```text
same input fingerprint
+ same engine/policy version
→ same assessment
```

Repeated task delivery must not create uncontrolled duplicate assessments.

Possible approach:

```text
one current assessment per candidate + version
```

with history retained if required.

---

# 39. API Design

Adapt to existing conventions.

Possible:

```text
GET  /api/v1/identity/candidates/{candidate_id}/assessment
POST /api/v1/identity/candidates/{candidate_id}/assessment/recalculate
GET  /api/v1/identity/candidates/{candidate_id}/evidence
```

Optional bulk endpoint:

```text
POST /api/v1/identity/assessments/recalculate
```

must remain bounded.

Do not expose other users' evidence.

---

# 40. Candidate List Integration

Extend candidate responses with a safe summary:

```text
assessment_status
confidence_band
match_score if policy permits
assessment_updated_at
assessment_stale
```

Do not return raw internal weighting details unless intended for explainability UI.

---

# 41. Evidence API

Safe evidence response may include:

```text
evidence type
direction
strength class
source class
independence group summary
human-readable explanation
timestamp
status
```

Do not expose:

```text
other-user data
secret internal identifiers
raw private data
unnecessary sensitive values
```

---

# 42. Frontend Scope

Extend `/app/identity` candidate review.

Candidate card may show:

```text
Needs review
Likely match
Possible match
Insufficient evidence
Unlikely match
Conflicting evidence
```

But preserve:

```text
Confirmed by you
Dismissed
```

as distinct user decisions.

---

# 43. Match Details Drawer/Page

Provide:

```text
Assessment summary
Why Matched
Why Not Matched
Evidence groups
Collision context
Assessment freshness
```

Do not overwhelm the default candidate card with raw scoring internals.

---

# 44. UI Language

Use:

```text
Likely match
Possible match
Limited evidence
Conflicting evidence
```

Avoid:

```text
This is definitely you
AI verified
100% match
```

---

# 45. Identity Graph Integration

Add assessment semantics only if the existing graph supports them safely.

Possible:

```text
CandidateProfile
→ ASSESSED_AGAINST
→ IdentityAnchor
```

with properties:

```text
assessment status
engine version
policy version
timestamp
```

Do not convert `likely_match` into a confirmed identity edge.

Confirmed graph relationships remain tied to explicit confirmation/verification.

---

# 46. PDSS Boundary

Sprint 17 remains primarily an identity-resolution sprint.

Default:

```text
algorithmic likely_match
→ no automatic Confirmed PDSS contribution
```

If the existing Possible track can safely represent unconfirmed identity evidence, any integration must be:

```text
explicit
deterministic
documented
bounded
reversible
```

The safest default is still:

```text
assessment assists review
→ no authoritative PDSS change
```

Formal PDSS identity integration should occur only in the planned later sprint.

---

# 47. Privacy Export

Extend export to include:

```text
identity evidence
identity match assessments
assessment status
score/band if stored
engine version
policy version
explanations
```

according to existing privacy policy.

Do not expose unnecessary internal secrets.

---

# 48. Deletion and Shredding

Extend ShredService/account deletion.

Verify:

```text
evidence deleted/inaccessible
assessments deleted/inaccessible
graph assessment edges cleaned
cache invalidated
no orphaned identity-resolution data
```

---

# 49. Audit Events

Use canonical audit infrastructure.

Recommended:

```text
identity_assessment_created
identity_assessment_recalculated
identity_assessment_became_stale
identity_candidate_confirmed_by_user
identity_candidate_dismissed_by_user
```

Do not log sensitive raw evidence unnecessarily.

---

# 50. Policy Versioning

Define:

```text
IDENTITY_MATCH_ENGINE_VERSION
IDENTITY_MATCH_POLICY_VERSION
```

or equivalent.

Every assessment records both.

Changing weights/rules must increment the appropriate version.

This is required for reproducibility.

---

# 51. Configuration

Weights and thresholds may be code-defined or validated configuration.

Do not allow unsafe arbitrary runtime modification without audit/versioning.

Document:

```text
positive weights
negative weights
caps
thresholds
collision modifiers
minimum evidence rules
```

---

# 52. Suggested Initial Evidence Policy

The implementation agent must adapt exact values after inspecting available evidence.

A safe conceptual policy:

```text
explicit user confirmation
→ handled as user state, not ordinary score

explicit user dismissal
→ strong negative / user override state

exact active confirmed alias match
→ positive

exact historical/revoked alias match
→ weak/contextual, not current strong evidence

confirmed profile cross-reference
→ strong positive if truly independent

same Maigret observation represented multiple ways
→ one capped independence group

high collision username
→ cap username-only confidence

one independent group only
→ cannot reach highest algorithmic band

contradictory strong evidence
→ conflicting_evidence
```

Do not blindly copy these into production weights without tests and documentation.

---

# 53. Security and Abuse Boundaries

Sprint 17 must not create:

```text
arbitrary people matching
cross-user identity correlation
global identity graph joins
sensitive attribute inference
face recognition
biometric identification
```

Assessment remains:

```text
authenticated user
+ own Identity Anchor
+ own candidate profiles
```

---

# 54. RLS and Ownership

Required:

```text
User A cannot read User B evidence
User A cannot read User B assessment
User A cannot trigger recalculation for User B candidate
User A cannot infer existence through error differences
```

Any failure is P0.

---

# 55. Migration Strategy

Create focused tables only if required.

Possible:

```text
identity_evidence
identity_match_assessments
```

Do not persist independence groups in a separate table unless needed.

Verify actual starting head:

```text
5c9980e0d0ad
```

only after checking the repository.

Then verify:

```text
Sprint 16 head → Sprint 17 head
fresh database → Sprint 17 head
one intended head
application startup
```

---

# 56. Unit Tests

Test:

```text
canonical fact deduplication
independence grouping
source reliability mapping
positive evidence
negative evidence
unknown evidence
collision classification
evidence caps
minimum evidence threshold
contradiction handling
abstention
deterministic score
confidence band mapping
policy versioning
```

---

# 57. No-Double-Counting Tests

Required examples:

```text
same username from URL + candidate field + Maigret query
→ one bounded fact/group contribution
```

and:

```text
repeated discovery of same candidate
→ does not multiply confidence indefinitely
```

---

# 58. Collision Tests

Test:

```text
common/simple username
→ capped confidence with username-only evidence

distinctive username
→ stronger but still non-verifying evidence

multiple candidates with same searched username
→ collision context increases uncertainty
```

Do not depend on live internet data.

---

# 59. Negative Evidence Tests

Test:

```text
explicit dismissal
strong contradiction
revoked alias
stale evidence
missing data
```

Verify:

```text
missing data
≠ automatic negative evidence
```

---

# 60. Determinism Tests

For fixed fixtures:

```text
same inputs
→ exact same score
→ exact same status
→ exact same explanation evidence mapping
```

Run across repeated executions.

---

# 61. Service Tests

Test:

```text
assess unreviewed candidate
recalculate assessment
anchor change marks/recalculates stale assessment
candidate rediscovery
user confirmation
user dismissal
conflicting evidence
insufficient evidence
```

---

# 62. API Tests

Test:

```text
get own assessment
get own evidence
recalculate own candidate
cross-user access denied
missing candidate
stale assessment
stable error DTO
```

---

# 63. Privacy Tests

Verify:

```text
export contains evidence/assessment data
account deletion removes it
graph cleanup
cache invalidation
```

---

# 64. Sprint 16 Regression

Re-run:

```text
Maigret feature disabled → zero execution
consent denied → zero execution
eligible input enforcement
command-injection resistance
timeout behavior
candidate deduplication
candidate confirm/dismiss
privacy export
ShredService
cross-user isolation
frontend discovery UI
```

Also explicitly verify:

```text
candidate deduplication is user-scoped
```

---

# 65. Sprint 15 Regression

Re-run:

```text
Identity Anchor
alias add/revoke
confirmed profile add/revoke
anchor versioning
zero network fetch on profile creation
privacy lifecycle
cross-user isolation
```

---

# 66. Sprint 14 Critical Regression

Re-run:

```text
Deep scan without consent → 403 + zero egress
Surface scan functional
deterministic PDSS unchanged
Confirmed/Possible semantics unchanged
Groq fallback
Residual ML disabled path
```

---

# 67. Frontend Tests

Verify:

```text
candidate assessment badges
match details
Why Matched
Why Not Matched
confirmed-by-user state remains distinct
dismissed state remains distinct
stale assessment state
empty evidence
conflicting evidence
production build
```

---

# 68. Observability

Low-cardinality metrics if supported:

```text
identity_assessments_total{status}
identity_assessment_duration_seconds
identity_assessments_stale_total
```

Do not label with:

```text
username
profile URL
user ID
candidate ID
```

---

# 69. Suggested Backend Layout

Adapt to actual repository:

```text
backend/app/
├── models/
│   ├── identity_evidence.py
│   └── identity_match_assessment.py
├── schemas/
│   └── identity_assessment.py
├── services/
│   ├── identity_evidence_service.py
│   ├── identity_match_engine.py
│   └── identity_collision_policy.py
└── api/v1/
    └── identity_assessment.py
```

Reuse existing structures where appropriate.

---

# 70. Suggested Frontend Layout

Possible:

```text
frontend/src/components/identity/
├── IdentityAssessmentBadge.tsx
├── IdentityMatchDetails.tsx
├── WhyMatched.tsx
├── WhyNotMatched.tsx
└── EvidenceBreakdown.tsx
```

Do not create unnecessary component fragmentation.

---

# 71. Documentation

Create or update:

```text
docs/identity/identity-match-engine.md
docs/identity/evidence-integrity.md
docs/identity/evidence-independence.md
docs/identity/username-collision-policy.md
docs/identity/identity-assessment-semantics.md
```

Document exact:

```text
evidence types
directions
reliability classes
independence rules
caps
weights
thresholds
abstention
contradiction handling
engine version
policy version
```

---

# 72. Implementation Order

## Phase A — Preflight

```text
verify Sprint 16 head
verify user-scoped candidate deduplication
verify actual Maigret execution boundary
inventory available candidate facts
```

## Phase B — Evidence model

```text
evidence types
→ direction
→ provenance
→ canonical facts
→ independence groups
→ reliability
```

## Phase C — Collision policy

```text
bounded local heuristics
→ collision class
→ confidence caps
```

## Phase D — Match engine

```text
collect
→ deduplicate
→ group
→ cap
→ positive/negative reasoning
→ contradiction
→ sufficiency
→ score
→ status
```

## Phase E — Explainability

```text
Why Matched
→ Why Not Matched
→ evidence mapping
```

## Phase F — Persistence/API

```text
assessment
→ evidence
→ recalculation
→ stale handling
```

## Phase G — Privacy/Graph

```text
export
→ deletion
→ graph assessment semantics
```

## Phase H — Frontend

```text
badges
→ match details
→ explanations
→ stale/conflict states
```

## Phase I — Verification

```text
unit
→ no-double-counting
→ collision
→ negative evidence
→ determinism
→ service
→ API
→ RLS
→ privacy
→ frontend
→ Sprint 14–16 regression
```

---

# 73. P0/P1 Defect Policy

For discovered defects:

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
change authoritative PDSS semantics
require major architecture redesign
introduce breaking API changes
expand into avatar/biometric matching or later sprint scope
```

---

# 74. Required Final Walkthrough

At completion provide:

```text
1. Actual Sprint 16 starting migration head
2. Sprint 17 migration ID and final head
3. Sprint 16 preflight findings
4. Confirmation that candidate deduplication is user-scoped
5. Actual Maigret execution-boundary description
6. Evidence types implemented
7. Evidence direction policy
8. Canonical fact deduplication rules
9. Independence-group rules
10. Source reliability policy
11. Collision-risk policy
12. Negative evidence handling
13. Contradiction handling
14. Deterministic scoring formula/rules
15. Evidence caps
16. Minimum evidence and abstention rules
17. Engine and policy versions
18. Assessment statuses and thresholds
19. Why Matched / Why Not Matched implementation
20. API endpoints
21. Frontend changes
22. RLS/cross-user isolation results
23. Privacy export/deletion results
24. Identity graph integration
25. PDSS regression result
26. Determinism test results
27. No-double-counting test results
28. Full backend test results
29. Frontend production build result
30. Sprint 16 regression results
31. Sprint 15 regression results
32. Sprint 14 critical regression results
33. P0–P3 issues found
34. Minimal fixes applied
35. Files created/modified
36. Remaining limitations
37. GO / CONDITIONAL GO / NO-GO for Sprint 18
```

Do not predetermine GO.

---

# 75. Definition of Done

## Evidence integrity

- [ ] Evidence has direction.
- [ ] Evidence has provenance.
- [ ] Evidence has source reliability.
- [ ] Evidence has canonical fact identity.
- [ ] Derived evidence preserves lineage.
- [ ] Correlated evidence is grouped.
- [ ] Duplicate facts do not multiply confidence.
- [ ] Missing data is not automatically negative evidence.

## Match engine

- [ ] Deterministic.
- [ ] Versioned.
- [ ] Positive evidence supported.
- [ ] Negative evidence supported.
- [ ] Collision context supported.
- [ ] Independence caps supported.
- [ ] Contradictions supported.
- [ ] Minimum evidence threshold supported.
- [ ] Abstention supported.
- [ ] Assessment freshness/staleness supported.

## Semantics

- [ ] Likely match does not mean verified identity.
- [ ] High score does not auto-confirm candidate.
- [ ] User confirmation remains distinct.
- [ ] User dismissal remains distinct.
- [ ] Maigret hit remains only candidate discovery.
- [ ] PDSS authoritative semantics remain unchanged unless explicitly approved.

## Explainability

- [ ] Why Matched implemented.
- [ ] Why Not Matched implemented.
- [ ] Every explanation maps to actual evidence.
- [ ] No LLM is authoritative for scoring/explanation facts.

## Security

- [ ] User-scoped assessment only.
- [ ] Cross-user evidence access blocked.
- [ ] Cross-user recalculation blocked.
- [ ] No arbitrary people matching.
- [ ] No sensitive-attribute inference.
- [ ] No biometric/face recognition.

## Privacy

- [ ] Evidence exported appropriately.
- [ ] Assessments exported appropriately.
- [ ] Deletion/shredding covers new data.
- [ ] Graph/caches cleaned.

## Regression

- [ ] Sprint 16 Maigret boundaries remain intact.
- [ ] Candidate deduplication verified user-scoped.
- [ ] Sprint 15 Identity Anchor remains intact.
- [ ] Sprint 14 consent/zero-egress regression remains green.
- [ ] PDSS remains deterministic and semantically unchanged.
- [ ] Frontend production build passes.

## Release gate

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 76. GO / NO-GO Gate for Sprint 18

## GO

Proceed when:

```text
identity evidence is canonical and provenance-preserving
correlated evidence cannot inflate confidence
negative evidence is first-class
collision risk limits username-only confidence
the engine can abstain
assessments are deterministic and versioned
explanations map to evidence
algorithmic matches do not auto-confirm identity
privacy/RLS pass
Sprint 14–16 regressions remain green
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
ownership
evidence integrity
double counting
negative evidence
determinism
privacy
cross-user isolation
assessment semantics
```

## NO-GO

Do not begin Sprint 18 with:

```text
global cross-user candidate correlation
double-counted evidence
algorithmic auto-confirmation
missing negative evidence
no abstention
unversioned scoring policy
non-deterministic authoritative scoring
cross-user evidence exposure
broken privacy deletion
unresolved P0
unaccepted P1
```

---

# 77. Handoff to Sprint 18

Sprint 18 will consume:

```text
IdentityEvidence
IdentityMatchAssessment
canonical facts
independence groups
source reliability
collision context
positive evidence
negative evidence
user confirmation
user dismissal
```

Sprint 18 may add:

```text
avatar perceptual similarity
safe image acquisition through approved egress
cross-link evidence
identity clusters
cluster-level contradictions
visual evidence independence
```

Sprint 18 must preserve:

```text
avatar similarity ≠ biometric identity verification
```

No face recognition or biometric identification should be introduced.

---

# 78. Final Sprint 17 Principle

Sprint 17 is where DigiZafe moves from:

```text
“I found the same username.”
```

to:

```text
“I found a candidate profile and can explain the evidence for and against it, how independent that evidence is, how collision-prone the username is, and whether there is enough evidence to make a useful assessment.”
```

The target architecture after Sprint 17 is:

```text
VERIFIED IDENTITY ANCHOR
        │
        ▼
MAIGRET CANDIDATE DISCOVERY
        │
        ▼
CANDIDATE PROFILE
        │
        ▼
CANONICAL IDENTITY EVIDENCE
        │
        ├── POSITIVE
        ├── NEGATIVE
        ├── UNKNOWN
        ├── RELIABILITY
        ├── INDEPENDENCE
        └── COLLISION CONTEXT
        │
        ▼
DETERMINISTIC MATCH ENGINE
        │
        ├── LIKELY MATCH
        ├── POSSIBLE MATCH
        ├── INSUFFICIENT EVIDENCE
        ├── UNLIKELY MATCH
        └── CONFLICTING EVIDENCE
        │
        ▼
HUMAN REVIEW
```

Sprint 17 is complete when DigiZafe can make deterministic, reproducible, evidence-integrity-aware identity assessments without confusing correlated observations with independent proof and without converting algorithmic confidence into verified ownership.

---

**End of Sprint 17 Implementation Guide**
