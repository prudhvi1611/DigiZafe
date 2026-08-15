# DigiZafe --- Sprint 15 Implementation Guide

**Sprint:** 15 --- Verified Identity Anchor & Alias Foundation  
**Document version:** 1.0  
**Applies after:** Sprint 14 --- Baseline Verification, Consolidation & Gap Closure  
**Architecture baseline:** Sprint 0--14 verified; Sprint 14 final decision = GO  
**Master context:** `MASTER_ENGINEERING_CONTEXT_2.md`  
**Primary goal:** Introduce the canonical, user-controlled Verified Identity Anchor that future candidate discovery and identity resolution will use, without changing the existing self-only, consent, privacy, evidence, graph, or PDSS boundaries.

> Sprint 14 verified the existing platform, resolved the Deep-scan consent-gateway P1 defect, froze canonical contracts, and documented safe extension points.
>
> Sprint 15 is the first feature-building sprint of Master Engineering Context 2.
>
> The core rule is:
>
> ```text
> discovered ≠ owned
> similar ≠ verified
> user-confirmed ≠ externally verified
> revoked ≠ active
> ```
>
> Sprint 15 must create a durable, explainable identity foundation. It must **not** yet perform Maigret discovery, OSINTgram enrichment, probabilistic identity matching, avatar similarity, or identity clustering.

---

# 1. Sprint Goal

Create a canonical **Verified Identity Anchor** representing the set of user-scoped facts DigiZafe is permitted to use in future self-identity resolution.

The anchor should unify, without collapsing their semantics:

```text
existing verified identifiers
user-confirmed aliases
user-confirmed profile references
verified cross-links where already supported
future candidate-resolution evidence
```

Expected architecture:

```text
Existing verified User
        │
        ├── Verified Identifiers
        │      ├── email
        │      ├── domain
        │      ├── username
        │      └── other canonical supported types
        │
        ▼
Verified Identity Anchor
        │
        ├── verified identifier references
        ├── user-confirmed aliases
        ├── user-confirmed profile references
        └── provenance + status + lifecycle
        │
        ▼
Existing Identity Graph integration
        │
        ▼
Future Sprint 16 Candidate Discovery
```

Sprint 15 must establish the data and service boundaries required for:

```text
Sprint 16 → Maigret Candidate Discovery
Sprint 17 → Identity Match Engine + Evidence Integrity
Sprint 18 → Avatar Similarity + Cross-Links + Identity Clusters
```

---

# 2. Non-Negotiable Constraints

Preserve all Sprint 0--14 invariants.

## 2.1 Self-only boundary

The Identity Anchor belongs only to the authenticated user.

It must not become:

- a global people-search profile;
- a cross-user identity database;
- a hidden dossier;
- a legal-identity inference engine;
- permission to scan arbitrary third parties;
- a mechanism to claim profiles automatically.

## 2.2 Verification semantics

Do not collapse these states:

```text
VERIFIED IDENTIFIER
→ ownership verified by the existing verification mechanism

USER-CONFIRMED ALIAS
→ user asserts the alias belongs to them

USER-CONFIRMED PROFILE
→ user asserts the profile belongs to them

DISCOVERED CANDIDATE
→ future Sprint 16 concept; not yet confirmed
```

A user-confirmed alias is not automatically equivalent to a cryptographically or challenge-verified identifier.

A user-confirmed profile is not automatically a platform-verified identity.

## 2.3 No automatic promotion

Never implement:

```text
new alias entered
→ automatically verified

profile URL entered
→ automatically verified by DigiZafe

existing graph similarity
→ automatically added to anchor

future candidate
→ automatically added to anchor
```

All anchor facts require an explicit origin and status.

## 2.4 No future-sprint leakage

Sprint 15 must not add:

```text
Maigret execution
OSINTgram
candidate discovery
CandidateProfile
identity match scoring
username rarity scoring
avatar similarity
identity clusters
negative identity evidence scoring
PDSS Risk Dimensions
identity drift detection
impersonation detection
remediation effectiveness
```

---

# 3. Sprint 14 Inputs That Must Be Reused

Before implementation, read:

```text
docs/audit/canonical-contracts.md
docs/audit/extension-points-for-sprint15.md
docs/audit/migration-status.md
docs/audit/sprint14-final-verification.md
docs/baseline/sprint0-13-baseline-manifest.md
docs/baseline/feature-flags.md
docs/baseline/runtime-components.md
```

Use the actual canonical:

```text
User model
Identifier model
IdentifierType
verification service
consent service
identity graph service
RLS pattern
encryption pattern
audit-event pattern
API router conventions
error DTO
frontend API/state conventions
migration conventions
test fixtures
```

If this guide conflicts with a verified canonical repository contract, preserve the canonical contract and document the adaptation.

Do not create duplicate infrastructure.

---

# 4. Core Domain Model

The recommended domain consists of:

```text
IdentityAnchor
IdentityAlias
ConfirmedProfileReference
IdentityAnchorEvent / existing AuditEvent integration
```

The implementation may adapt names to existing repository conventions.

Prefer extending existing canonical abstractions over introducing redundant tables.

---

# 5. IdentityAnchor

The Identity Anchor is the user-scoped root for future identity resolution.

Recommended conceptual fields:

```text
id
user_id
status
version
created_at
updated_at
last_confirmed_at
```

Recommended status:

```text
active
suspended
deleted
```

If the repository already has a natural one-to-one identity root, do not create a redundant table merely to match this document.

The essential invariant is:

```text
one active canonical identity anchor per user
```

unless the verified architecture explicitly supports multiple personas.

Sprint 15 should default to one anchor per user.

---

# 6. Verified Identifier Membership

Existing verified identifiers remain authoritative.

Do not copy identifier values into a second identity table unless required by the existing encryption or schema architecture.

Preferred relationship:

```text
IdentityAnchor
    │
    └── references existing verified Identifier records
```

Eligibility:

```text
identifier.user_id == anchor.user_id
AND identifier is verified
AND identifier is active
```

Unverified identifiers must not become verified anchor facts.

If an identifier is revoked, deleted, or loses verified eligibility according to the canonical system, anchor-derived use must reflect that state.

---

# 7. IdentityAlias

An alias is a user-controlled identity claim.

Examples:

```text
yuva123
yuva_dev
old_username
public display name
historical username
```

Recommended fields:

```text
id
user_id
anchor_id
alias_type
canonical_value
display_value
status
confirmation_method
confidence_class
created_at
updated_at
last_confirmed_at
revoked_at
```

Recommended alias types:

```text
username
display_name
historical_username
handle
other
```

Use an enum only if that matches canonical repository conventions.

Recommended status:

```text
active
revoked
```

Recommended confirmation method:

```text
user_asserted
derived_from_verified_identifier
verified_by_existing_mechanism
```

Do not use a numeric identity-match confidence score in Sprint 15.

---

# 8. Alias Canonicalization

Canonicalization must be deterministic and type-aware.

Examples:

```text
trim surrounding whitespace
Unicode normalization
platform-independent case normalization only where semantically safe
remove leading @ only for handle canonicalization if policy defines it
reject control characters
enforce length bounds
```

Do not globally lowercase values where case may be meaningful.

Store:

```text
display_value
canonical_value
```

when useful.

Uniqueness should normally be scoped to:

```text
user/anchor + alias_type + canonical_value + active state
```

Do not enforce global uniqueness across users.

The same username may legitimately belong to different people on different platforms or contexts.

---

# 9. ConfirmedProfileReference

Sprint 15 may allow the user to explicitly register a public profile they already know they own.

This is not a discovered candidate.

Recommended fields:

```text
id
user_id
anchor_id
platform
profile_url
canonical_profile_url
username_hint
status
confirmation_method
created_at
updated_at
last_confirmed_at
revoked_at
provenance
```

Recommended status:

```text
active
revoked
```

Recommended confirmation method:

```text
user_asserted
verified_cross_link
existing_verified_mechanism
```

Do not label `user_asserted` as externally verified.

---

# 10. Profile URL Safety

Profile URLs are untrusted input.

Sprint 15 should normalize and store references, but it must not create an unrestricted server-side URL fetch path.

Required:

- validate URL syntax;
- allow only `http`/`https` if URL schemes are stored;
- reject embedded credentials;
- normalize hostname;
- normalize known safe URL components;
- apply length limits;
- avoid automatically fetching the URL;
- never bypass `EgressFetcher`.

If profile verification by network request is not already an approved canonical capability:

```text
store reference
→ do not fetch
```

Future discovery/enrichment must use the centralized egress architecture.

---

# 11. Platform Semantics

Avoid creating an unbounded, hardcoded platform enum if the existing connector/source registry already provides canonical platform IDs.

Preferred:

```text
canonical source/platform identifier
```

If a platform registry exists, reuse it.

If no registry exists, use a bounded normalized string with validation and document the future migration path.

Do not introduce Maigret's site catalog as the canonical DigiZafe platform registry in Sprint 15.

---

# 12. Provenance

Every anchor fact must answer:

```text
Who added this?
How was it established?
When?
What is its current status?
Can it be revoked?
```

Recommended provenance fields or equivalent:

```text
source_type
source_reference
confirmation_method
created_by
created_at
last_confirmed_at
```

Never expose another user's provenance.

---

# 13. Confidence Semantics

Sprint 15 should use semantic confidence classes, not probabilistic identity scores.

Recommended:

```text
verified
user_confirmed
unverified
revoked
```

or equivalent canonical statuses.

Do not implement:

```text
91% identity match
0.84 same-person probability
```

Those belong to Sprint 17.

The API and UI must clearly distinguish:

```text
Verified by DigiZafe ownership workflow
Confirmed by you
```

---

# 14. Revocation

Users must be able to revoke:

```text
alias
confirmed profile reference
```

Revocation should:

```text
mark inactive/revoked
preserve audit history where policy allows
exclude from future active discovery inputs
update graph state if integrated
not silently delete unrelated evidence
```

If hard deletion is the canonical privacy behavior for this data class, follow that design.

Revocation must be idempotent.

---

# 15. Identity Anchor Service

Create or extend a canonical service, for example:

```text
IdentityAnchorService
```

Responsibilities:

```text
get_or_create_anchor(user)
list active anchor facts
add alias
revoke alias
add confirmed profile reference
revoke confirmed profile reference
resolve verified identifier membership
build safe anchor summary
emit audit events
coordinate graph updates
```

It must not:

```text
perform candidate discovery
call Maigret
call OSINTgram
score identity matches
fetch arbitrary profile URLs
change PDSS
```

---

# 16. Safe Anchor Summary

Future sprints need a bounded representation of the anchor.

Recommended DTO:

```text
IdentityAnchorSummary
├── verified_identifiers
├── active_aliases
├── confirmed_profiles
├── anchor_version
└── updated_at
```

The summary should expose only the minimum data required for the caller.

Do not create one giant DTO containing encrypted/raw internal fields.

---

# 17. Anchor Versioning

Introduce a monotonic or deterministic anchor version if it fits the architecture.

The version should change when active identity inputs change:

```text
verified identifier becomes eligible/ineligible
alias added/revoked
profile reference added/revoked
```

Future discovery runs can record:

```text
anchor_version
```

to explain which identity inputs were used.

Do not store secrets in the version.

Possible implementation:

```text
integer revision
```

or a deterministic safe hash over internal record IDs/status versions.

Prefer the simplest compatible option.

---

# 18. Database Migration

Create one focused Sprint 15 migration, adapted to existing schema.

Possible tables:

```text
identity_anchors
identity_aliases
confirmed_profile_references
```

Do not create a separate audit table if the canonical audit-event system can represent anchor changes.

## Required constraints

```text
one active anchor per user
foreign keys to user/anchor
user ownership
bounded field lengths
valid status values
timestamps
revocation fields
safe uniqueness
```

## Required indexes

Consider:

```text
identity_anchors(user_id)
identity_aliases(anchor_id, status)
identity_aliases(user_id, canonical_value)
confirmed_profile_references(anchor_id, status)
confirmed_profile_references(user_id, canonical_profile_url)
```

Use actual query patterns.

## Migration verification

Run:

```text
alembic heads
alembic upgrade head
fresh database → head
Sprint 14 head → Sprint 15 head
```

Expected:

```text
one intended head
```

---

# 19. RLS and Ownership

Apply the canonical Sprint 14 RLS pattern.

Required:

```text
user can access only own anchor
user can access only own aliases
user can access only own confirmed profiles
```

Service-layer ownership checks must complement database isolation where the architecture requires both.

Test:

```text
User A anchor inaccessible to User B
User A alias inaccessible to User B
User A profile reference inaccessible to User B
guessed IDs rejected
cross-user mutation rejected
cross-user revocation rejected
```

Any failure is P0.

---

# 20. Encryption and Data Minimization

Use existing encryption infrastructure where required.

Do not automatically classify every alias as requiring field-level encryption if the canonical architecture does not do so; follow the Sprint 14 data-classification pattern.

At minimum:

- minimize duplicate identifier values;
- never store passwords or platform credentials;
- never store session cookies;
- never store private profile content;
- never fetch/store unnecessary profile bodies;
- ensure deletion/crypto-shred compatibility.

---

# 21. Audit Events

Use the canonical audit system.

Recommended event types or equivalents:

```text
identity_anchor_created
identity_alias_added
identity_alias_revoked
confirmed_profile_added
confirmed_profile_revoked
identity_anchor_exported
```

Do not put raw secrets into audit payloads.

Audit payloads may include safe metadata:

```text
record ID
alias type
platform
confirmation method
status transition
```

Avoid raw sensitive values unless existing audit policy explicitly permits them.

---

# 22. Existing Identity Graph Integration

Sprint 15 should integrate anchor facts into the existing identity graph only through canonical graph services.

Possible graph semantics:

```text
User/Identity root
→ HAS_VERIFIED_IDENTIFIER
→ HAS_CONFIRMED_ALIAS
→ CLAIMS_PROFILE
```

Use existing edge naming conventions.

Do not introduce future probabilistic edges yet:

```text
same_username_candidate
avatar_similar_to
confirmed_same_identity
rejected_same_identity
```

unless already canonical.

Every graph relationship must retain:

```text
ownership
status
provenance
confidence class
```

Graph failure should not leave the primary database transaction in a corrupt state.

Choose a consistent transactional/outbox/reconciliation pattern based on the existing architecture.

---

# 23. API Design

Adapt routes to existing `/api/v1` conventions.

Recommended:

```text
GET    /api/v1/identity/anchor

GET    /api/v1/identity/aliases
POST   /api/v1/identity/aliases
DELETE /api/v1/identity/aliases/{alias_id}

GET    /api/v1/identity/profiles
POST   /api/v1/identity/profiles
DELETE /api/v1/identity/profiles/{profile_id}
```

If canonical semantics prefer explicit revoke endpoints:

```text
POST /api/v1/identity/aliases/{id}/revoke
POST /api/v1/identity/profiles/{id}/revoke
```

Use one consistent pattern.

Do not expose cross-user identifiers in routes.

---

# 24. API DTOs

Recommended request DTOs:

```text
CreateIdentityAliasRequest
CreateConfirmedProfileRequest
```

Recommended response DTOs:

```text
IdentityAnchorResponse
IdentityAliasResponse
ConfirmedProfileResponse
IdentityAnchorSummaryResponse
```

Do not return:

```text
encryption metadata
internal keys
other-user data
raw audit internals
```

Use the canonical error DTO.

---

# 25. Alias Creation Rules

Required flow:

```text
authenticated user
→ validate input
→ canonicalize
→ check user-scoped active duplicate
→ create user-confirmed alias
→ update anchor version
→ graph integration
→ audit event
→ response
```

Duplicate active aliases should be:

```text
idempotent
```

or return a stable canonical conflict according to existing API conventions.

Do not create multiple active duplicate rows.

---

# 26. Alias Revocation Rules

Required flow:

```text
authenticated user
→ ownership check
→ active alias
→ revoke
→ update anchor version
→ graph state update
→ audit
```

Repeated revocation should be safely idempotent.

A revoked alias must not be returned as an active future discovery input.

---

# 27. Confirmed Profile Creation Rules

Required flow:

```text
authenticated user
→ validate URL
→ canonicalize URL
→ validate platform identifier
→ user explicitly confirms ownership
→ create profile reference
→ update anchor version
→ graph integration
→ audit
```

The API/UI must not imply that DigiZafe independently verified ownership when the method is `user_asserted`.

---

# 28. Confirmed Profile Revocation Rules

Required flow:

```text
authenticated user
→ ownership check
→ revoke
→ exclude from active anchor summary
→ update graph state
→ update anchor version
→ audit
```

Revocation must not erase unrelated historical findings.

---

# 29. Verified Identifier Synchronization

The anchor must reflect the canonical identifier system.

Preferred options:

## Option A — Dynamic membership

```text
anchor summary queries active verified identifiers
```

Advantages:

```text
no duplication
immediate consistency
```

## Option B — Explicit membership records

Use only if required by existing architecture.

If explicit membership is used, synchronization must handle:

```text
identifier verified
identifier revoked
identifier deleted
```

Do not create two competing sources of truth.

The Sprint 14 canonical Identifier model remains authoritative.

---

# 30. Consent Boundary

Adding an alias or confirmed profile does not automatically grant permission for all future external discovery.

Sprint 15 must preserve:

```text
identity anchor
≠ consent grant
```

Future Sprint 16 discovery must still evaluate:

```text
verified/self-owned input eligibility
scan scope
consent
feature flags
egress policy
quota
```

Do not store “global permanent consent” inside the anchor.

---

# 31. Privacy Export

Extend the existing privacy export to include, as appropriate:

```text
identity anchor metadata
aliases
confirmed profile references
statuses
confirmation methods
created/revoked timestamps
```

Do not expose internal secrets or other users' data.

Add regression tests.

---

# 32. Account Deletion and Crypto-Shred

Extend deletion behavior so identity-anchor data follows the canonical privacy lifecycle.

Verify:

```text
account deletion
→ anchor inaccessible
→ aliases inaccessible
→ confirmed profiles inaccessible
→ graph references removed/deactivated
→ caches invalidated
→ encrypted data crypto-shredded where applicable
```

Any orphaned personally scoped anchor data is a P0/P1 issue depending on exposure.

---

# 33. Caching

Do not add caching unless useful.

If anchor summaries are cached:

```text
cache key must be user-scoped
cache invalidated on add/revoke/verification-state change
Redis remains non-authoritative
```

Never use raw sensitive values as cache keys when avoidable.

---

# 34. Frontend Scope

Add a focused **My Identity Anchor** experience using existing frontend conventions.

Recommended sections:

```text
Verified Identifiers
Aliases
Confirmed Profiles
```

Each item should display its semantic status clearly.

Examples:

```text
Verified by DigiZafe
Confirmed by you
Revoked
```

Do not show:

```text
91% match
AI says this is you
```

Sprint 17 owns identity-match confidence.

---

# 35. Frontend: Add Alias

The UI should allow:

```text
alias type
alias value
explicit confirmation
```

Suggested confirmation language:

```text
I confirm that this alias or username belongs to me or has been used by me.
```

Do not use manipulative wording.

Show validation and duplicate states clearly.

---

# 36. Frontend: Add Confirmed Profile

Allow:

```text
platform
profile URL
optional username hint
explicit ownership confirmation
```

Suggested semantics:

```text
Confirmed by you
```

not:

```text
Verified account
```

unless an actual approved verification mechanism establishes that status.

---

# 37. Frontend: Revocation

Users must be able to revoke aliases and profile references.

Before revocation, explain:

```text
This will remove the item from your active identity anchor and future discovery inputs. Existing historical findings may remain according to retention and audit policy.
```

Use existing confirmation-dialog patterns.

---

# 38. Frontend Route

Use existing route conventions.

Possible:

```text
/identity
/identity/anchor
```

Do not create duplicate navigation if an existing identity-graph or account area is the correct canonical home.

The implementation agent must inspect Sprint 14 frontend documentation first.

---

# 39. Future Discovery Input Contract

Sprint 15 must expose a safe internal contract for Sprint 16.

Example:

```text
DiscoveryIdentityInput
├── source_record_id
├── input_type
├── canonical_value
├── ownership_class
├── active
└── anchor_version
```

Allowed ownership classes may include:

```text
verified_identifier
user_confirmed_alias
user_confirmed_profile
```

Sprint 16 will decide which classes are eligible for which discovery operation.

Do not include:

```text
arbitrary candidate
rejected identity
other user's alias
```

---

# 40. Anchor Snapshot

Provide a way to create a stable internal snapshot for future scans.

Conceptually:

```text
AnchorSnapshot
├── anchor_id
├── anchor_version
├── created_at
└── references to eligible active facts
```

Do not necessarily persist a new snapshot table in Sprint 15 unless needed.

A deterministic serialized summary or future scan-time manifest may be sufficient.

The goal is future reproducibility:

```text
Which identity inputs were active when this discovery run started?
```

---

# 41. No Identity Scoring Yet

Sprint 15 must not create a weighted identity score.

Do not implement:

```text
same username = +20
verified domain = +50
profile = 80% match
```

Sprint 17 will introduce:

```text
IdentityEvidence
IdentityMatchAssessment
negative evidence
evidence independence
collision detection
confidence bands
```

Sprint 15 only creates trusted input semantics.

---

# 42. Testing Strategy

Required logical groups:

```text
unit
service
API
database/migration
RLS/isolation
graph integration
privacy
frontend
regression
```

---

# 43. Unit Tests

Test:

```text
alias canonicalization
alias validation
profile URL canonicalization
profile URL rejection
status transitions
anchor version increment
active/revoked filtering
duplicate detection
```

Include Unicode and boundary cases.

---

# 44. Service Tests

Test:

```text
get/create anchor
add alias
duplicate alias
revoke alias
repeat revoke
add confirmed profile
duplicate profile
revoke profile
verified identifier membership
safe anchor summary
```

Verify no network request occurs merely by adding a profile URL.

---

# 45. API Tests

Test:

```text
GET own anchor
create alias
list aliases
revoke alias
create profile
list profiles
revoke profile
invalid inputs
unauthenticated access
stable error DTOs
```

---

# 46. Cross-User Isolation Tests

Required:

```text
User A cannot read User B anchor
User A cannot read User B alias
User A cannot revoke User B alias
User A cannot read User B profile
User A cannot revoke User B profile
```

Test direct guessed IDs.

Any failure is P0.

---

# 47. Migration Tests

Verify:

```text
Sprint 14 head → Sprint 15 head
fresh database → Sprint 15 head
one intended head
application startup
```

If downgrade tests are part of the canonical project, run them.

---

# 48. Graph Integration Tests

Verify:

```text
alias added
→ expected graph representation

alias revoked
→ inactive/removed according to canonical graph policy

profile added
→ expected claims-profile representation

profile revoked
→ no longer active
```

Graph updates must not create cross-user edges.

---

# 49. Privacy Tests

Verify:

```text
privacy export includes anchor data
account deletion removes/inactivates anchor data
crypto-shred compatibility
cache invalidation
no orphaned active graph facts
```

---

# 50. Regression Tests

Re-run Sprint 14 critical regressions, especially:

```text
Deep scan without consent → 403 and zero egress
Surface scan still works
verified identifier flow still works
PDSS unchanged
Groq fallback unchanged
Residual ML disabled path unchanged
```

Sprint 15 must not regress the verified baseline.

---

# 51. Frontend Tests

Verify:

```text
production build
identity-anchor page renders
verified identifiers display correctly
alias add/revoke
profile add/revoke
status labels
validation errors
authorization errors
empty states
loading states
```

---

# 52. Suggested File Layout

Adapt to the actual repository.

Possible backend additions:

```text
backend/app/
├── models/
│   ├── identity_anchor.py
│   ├── identity_alias.py
│   └── confirmed_profile_reference.py
├── schemas/
│   └── identity_anchor.py
├── services/
│   └── identity_anchor_service.py
├── api/v1/
│   └── identity.py
└── repositories/
    └── identity_anchor_repository.py
```

Possible frontend additions:

```text
frontend/src/
├── pages/
│   └── IdentityAnchorPage.*
├── components/identity/
│   ├── VerifiedIdentifiers.*
│   ├── AliasList.*
│   ├── AddAliasDialog.*
│   ├── ConfirmedProfileList.*
│   └── AddConfirmedProfileDialog.*
└── api/
    └── identity.*
```

Do not create every file mechanically. Reuse existing project structure.

---

# 53. Suggested API Examples

## Add alias

```json
{
  "alias_type": "username",
  "value": "yuva_dev"
}
```

Response semantics:

```json
{
  "id": "...",
  "alias_type": "username",
  "display_value": "yuva_dev",
  "status": "active",
  "confirmation_method": "user_asserted"
}
```

## Add confirmed profile

```json
{
  "platform": "github",
  "profile_url": "https://github.com/example",
  "username_hint": "example"
}
```

Response must clearly represent:

```text
confirmation_method = user_asserted
```

unless a stronger approved mechanism was actually used.

---

# 54. Error Semantics

Use canonical error DTOs.

Expected cases:

```text
400 invalid input
401 unauthenticated
403 forbidden/cross-user
404 missing resource
409 active duplicate, if canonical API uses conflict
422 schema validation, if canonical framework uses it
```

Do not leak:

```text
database internals
other-user existence
secret values
stack traces
```

---

# 55. Observability

Add low-cardinality metrics only if the existing observability architecture supports them.

Possible:

```text
identity_anchor_operations_total{operation,status}
identity_aliases_total{status}
confirmed_profile_operations_total{operation,status}
```

Avoid labels containing:

```text
user ID
alias
username
profile URL
email
domain
```

Structured logs may include safe internal correlation IDs according to existing policy.

---

# 56. Feature Flags

The core Identity Anchor should normally be a first-class feature after Sprint 15 acceptance.

If rollout control is required, use one bounded feature flag such as:

```text
FEATURE_IDENTITY_ANCHOR
```

Do not create many unnecessary flags.

Future flags:

```text
FEATURE_MAIGRET_DISCOVERY
FEATURE_OSINTGRAM
```

belong to later sprints.

---

# 57. Documentation

Create or update:

```text
docs/identity/identity-anchor.md
docs/identity/alias-semantics.md
docs/identity/confirmed-profile-semantics.md
docs/privacy/identity-resolution-data-handling.md
```

If equivalent documents exist, update them rather than duplicating.

Document:

- ownership semantics;
- verification vs user confirmation;
- revocation;
- canonicalization;
- privacy lifecycle;
- future Sprint 16 discovery boundary.

---

# 58. Implementation Order

## Phase A — Read Sprint 14 outputs

```text
canonical contracts
extension points
migration baseline
RLS pattern
audit pattern
frontend conventions
```

## Phase B — Domain design

```text
Identity Anchor
→ aliases
→ confirmed profiles
→ status/provenance
→ versioning
```

## Phase C — Migration

```text
focused schema
→ constraints
→ indexes
→ RLS
→ upgrade tests
```

## Phase D — Backend

```text
repository
→ service
→ DTOs
→ API
→ audit
→ graph integration
```

## Phase E — Privacy

```text
export
→ deletion
→ crypto-shred
→ cache invalidation
```

## Phase F — Frontend

```text
My Identity Anchor
→ verified identifiers
→ aliases
→ confirmed profiles
→ revoke controls
```

## Phase G — Verification

```text
unit
→ API
→ RLS
→ migration
→ graph
→ privacy
→ frontend
→ Sprint 14 regression
```

---

# 59. P0/P1 Defect Policy

If implementation reveals a baseline defect:

```text
reproduce
→ classify
→ regression test
→ smallest safe fix
→ affected tests
→ document
```

Stop for approval only if the required fix would:

```text
change frozen security/privacy invariants
change PDSS semantics
require major database redesign
introduce a breaking API change
expand into future sprint scope
```

---

# 60. Required Final Walkthrough

At completion provide:

```text
1. Architecture implemented
2. Migration ID and migration verification
3. Models/tables added or reused
4. API endpoints added
5. Frontend changes
6. RLS/isolation results
7. Privacy export/deletion results
8. Graph integration results
9. Test results
10. Sprint 14 regression results
11. P0–P3 issues found
12. Minimal fixes applied
13. Files created/modified
14. Remaining limitations
15. GO / CONDITIONAL GO / NO-GO for Sprint 16
```

Do not predetermine GO.

---

# 61. Definition of Done

## Domain

- [ ] One canonical active Identity Anchor per user or documented equivalent.
- [ ] Existing verified identifiers integrate without creating a competing source of truth.
- [ ] User-confirmed aliases are supported.
- [ ] User-confirmed profile references are supported.
- [ ] Verification and user-confirmation semantics remain distinct.
- [ ] Revocation is supported.
- [ ] Anchor version/revision is available for future reproducibility.

## Security

- [ ] Authentication required.
- [ ] RLS/ownership enforced.
- [ ] Cross-user access tests pass.
- [ ] Profile URLs do not trigger unrestricted fetches.
- [ ] No credentials/session cookies stored.
- [ ] Existing consent/egress invariants remain unchanged.

## Database

- [ ] Focused migration created.
- [ ] Sprint 14 head upgrades successfully.
- [ ] Fresh database reaches Sprint 15 head.
- [ ] One intended migration head remains.
- [ ] Constraints/indexes/RLS verified.

## Backend

- [ ] Anchor service implemented.
- [ ] Alias create/list/revoke implemented.
- [ ] Confirmed profile create/list/revoke implemented.
- [ ] Safe anchor summary implemented.
- [ ] Audit events emitted.
- [ ] Existing graph integration completed safely.

## Privacy

- [ ] Export includes appropriate anchor data.
- [ ] Account deletion handles anchor data.
- [ ] Crypto-shred compatibility verified.
- [ ] Cache invalidation verified if caching exists.

## Frontend

- [ ] My Identity Anchor experience implemented.
- [ ] Verified identifiers displayed.
- [ ] Alias add/revoke works.
- [ ] Confirmed profile add/revoke works.
- [ ] Status semantics are clear.
- [ ] Production build passes.

## Regression

- [ ] Sprint 14 critical tests still pass.
- [ ] Deep scan without consent still returns 403.
- [ ] Zero-egress invariant remains protected.
- [ ] Surface scan remains functional.
- [ ] PDSS output semantics remain unchanged.
- [ ] Groq fallback remains functional.
- [ ] Residual ML disabled path remains unchanged.

## Documentation

- [ ] Identity Anchor documented.
- [ ] Alias semantics documented.
- [ ] Confirmed profile semantics documented.
- [ ] Privacy handling documented.
- [ ] Sprint 16 discovery input contract documented.

## Release gate

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 62. GO / NO-GO Gate for Sprint 16

## GO

Proceed to Maigret Candidate Discovery when:

```text
Identity Anchor is canonical
verified identifiers remain authoritative
aliases/profile references are user-scoped
revocation works
RLS/isolation passes
privacy lifecycle passes
future discovery input contract is stable
Sprint 14 regressions remain green
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
ownership
privacy
security
migration health
discovery input correctness
```

## NO-GO

Do not begin Sprint 16 with:

```text
cross-user identity data exposure
ambiguous verification semantics
unrestricted URL fetching
duplicate identifier source of truth
broken revocation
broken privacy deletion
migration instability
unresolved P0
unaccepted P1
```

---

# 63. Handoff to Sprint 16

Sprint 16 will consume:

```text
IdentityAnchorSummary
active verified identifiers
active user-confirmed aliases
active confirmed profile references
anchor version
canonical platform/source semantics
existing consent service
existing egress boundary
existing worker architecture
existing connector conventions
```

Sprint 16 will add:

```text
bounded Maigret candidate discovery
CandidateProfile normalization
candidate provenance
candidate deduplication
candidate review queue foundation
```

Sprint 16 must preserve:

```text
Maigret hit ≠ confirmed identity
```

No candidate may silently become an active anchor fact.

---

# 64. Final Sprint 15 Principle

Sprint 15 creates the trusted **input boundary** for future identity resolution.

The system must be able to say:

```text
This email/domain/identifier was verified through DigiZafe's ownership workflow.

This alias was confirmed by you.

This profile was confirmed by you.

These are different evidence classes.
```

That distinction is foundational.

The target architecture after Sprint 15 is:

```text
VERIFIED USER
      │
      ▼
VERIFIED IDENTITY ANCHOR
      │
      ├── verified identifiers
      ├── user-confirmed aliases
      └── user-confirmed profiles
      │
      ▼
SPRINT 16: BOUNDED CANDIDATE DISCOVERY
      │
      ▼
SPRINT 17: EVIDENCE-INTEGRITY-AWARE IDENTITY MATCHING
```

Sprint 15 is complete when DigiZafe has a secure, user-controlled, revocable, privacy-compatible, explainable identity anchor that future discovery can consume without inventing ownership.

---

**End of Sprint 15 Implementation Guide**
