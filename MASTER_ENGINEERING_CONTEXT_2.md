# DigiZafe — MASTER ENGINEERING CONTEXT 2
## Identity Resolution, Self-OSINT Expansion & Post-Sprint-13 Evolution Plan

**Document version:** 1.0  
**Status:** Post-Sprint-13 continuation master plan  
**Baseline:** Existing DigiZafe Sprint 0–13 implementation  
**Primary rule:** **Audit and extend the existing system. Do not rebuild it from scratch.**  
**Architecture posture:** Privacy-first, self-only, evidence-grounded, deterministic-first, additive evolution  
**Next implementation sequence:** Baseline Audit → Identity Anchor → Candidate Discovery → Identity Resolution → Profile Exposure Intelligence → Graph/PDSS Integration → UX → Hardening

---

# 0. Purpose of This Document

This document is the second master engineering context for DigiZafe.

The original Sprint 0–13 program established the product foundation and the major end-to-end workflow:

```text
Verify
  ↓
Consent
  ↓
Discover
  ↓
Normalize evidence
  ↓
Explain
  ↓
Score with deterministic PDSS
  ↓
Prioritize recommendations
  ↓
Remediate
  ↓
Re-verify
  ↓
Re-score
```

The next phase expands DigiZafe from a verified-identifier exposure platform into a **verified self-identity resolution and personal exposure intelligence system**.

The key new question is:

> **Given a profile, account, username, avatar, alias, or public identity candidate discovered on the internet, how confidently can DigiZafe determine that it belongs to the verified user, and what exposure does that profile create?**

This phase must not weaken the existing self-only, consent, privacy, provenance, scoring, or remediation boundaries.

---

# 1. Current Baseline: Sprint 0–13

The repository should be treated as an **implemented but not yet fully trusted baseline**.

Many files have already been created from Sprint implementation guides. Therefore:

```text
file exists
≠ feature is integrated
≠ feature is tested
≠ feature is production-ready
```

Before adding new architecture, the implementation agent must inspect the real repository and determine:

- what is actually present;
- what imports successfully;
- what migrations exist and apply;
- what tests pass;
- what API contracts are live;
- what frontend routes compile;
- what services are wired into dependency injection;
- what workers and scheduled tasks are registered;
- what features are placeholders;
- what code is duplicated;
- what configuration is stale or conflicting.

## 1.1 Existing capability map

The intended Sprint 0–13 baseline includes:

| Area | Existing intended capability |
|---|---|
| Foundation | Monorepo, configuration, database, Redis, API, workers |
| Security | JWT/auth, Argon2, MFA, CSRF/SSRF controls, rate limits, RLS, encryption, secrets hygiene |
| Identity input | Canonical identifiers and ownership verification |
| Egress | Centralized `EgressFetcher`, destination controls, consent-aware external requests |
| Connectors | Connector SDK, free public connectors, provenance and rate limits |
| Discovery | Durable scan state machine, connector runs, reconciliation, SSE progress |
| Evidence | Three-layer evidence handling, TTL/purge, durable finding metadata |
| Scoring | Identity graph, deterministic two-track PDSS, explanations, score history, what-if |
| Recommendations | Priority/ROI/dependency-based recommendations and alerts |
| Remediation | AIDR-inspired user-directed broker/removal workflows and verification loops |
| Privacy | Export, consent, audit, egress transparency, crypto-shred/deletion |
| Frontend | Auth, identifiers, scans, findings, PDSS, recommendations, identity graph |
| UX | Risk autopsy, simulator, narrative briefing, remediation console, privacy center |
| Amber discovery | Deep public archive/index metadata and constrained public-index boundary |
| Residual ML | Optional, bounded, local, auxiliary ML evaluation path |
| Production readiness | Observability, reliability, backups, SLOs, release and rollback hardening |

## 1.2 Current authority hierarchy

When implementation documents disagree, use this order:

```text
1. Frozen security/privacy invariants
2. Current canonical repository implementation and migrations
3. MASTER_ENGINEERING_CONTEXT / approved architecture decisions
4. Sprint 13 production-hardening constraints
5. This MASTER_ENGINEERING_CONTEXT_2.md
6. Individual future sprint implementation examples
```

If a future requirement conflicts with a frozen invariant, stop and create a **Critical Blocker Note (CBN)** rather than silently changing architecture.

---

# 2. Mandatory Phase 0: Baseline Verification & Gap Audit

No new identity-resolution feature should be merged before the existing Sprint 0–13 baseline is audited.

## 2.1 Audit objectives

Create:

```text
docs/audit/post-sprint13-baseline-audit.md
docs/audit/feature-integration-matrix.md
docs/audit/test-gap-register.md
docs/audit/migration-status.md
```

For every Sprint 0–13 capability, classify it as:

```text
VERIFIED
PARTIALLY_VERIFIED
PRESENT_NOT_INTEGRATED
PLACEHOLDER
BROKEN
MISSING
BLOCKED
```

## 2.2 Required checks

Run and record, adapting commands to the actual repository:

```bash
docker compose config
docker compose build
docker compose up -d

alembic heads
alembic current
alembic upgrade head

pytest
# plus targeted unit, integration, security, migration and regression suites

cd frontend
npm install
npm run build
```

Also verify:

- application startup;
- PostgreSQL connectivity;
- Redis roles;
- Celery worker registration;
- beat/scheduled jobs;
- health and readiness;
- auth lifecycle;
- identifier verification;
- consent enforcement;
- zero-egress denial paths;
- Surface scan;
- Deep Amber consent path;
- finding normalization;
- PDSS calculation;
- recommendation generation;
- remediation dry-run/manual path;
- privacy export;
- deletion/crypto-shred;
- deterministic narrative fallback;
- residual ML disabled path;
- release smoke journey.

## 2.3 Repair policy

During the audit:

1. **Fix integration defects before adding replacement modules.**
2. **Reuse canonical models, enums, DTOs and services.**
3. Do not create `*_v2`, `new_*`, or parallel repositories merely to avoid understanding existing code.
4. Prefer small migrations and adapters over rewrites.
5. Preserve API compatibility unless a versioned contract change is required.
6. Add a regression test for every repaired critical defect.
7. Do not mark a sprint green because its files exist.

## 2.4 Exit gate

Phase 0 is complete only when:

```text
backend starts
database reaches one expected migration head
frontend production build passes
critical security tests pass
verified self-only scan path works
PDSS path works
privacy deletion path works
no known P0 integration blocker remains
```

P1 defects may remain only if documented with owner, impact, workaround and planned sprint.

---

# 3. Product Evolution: Verified True Profile / Identity Anchor

The next major capability is a **Verified Identity Anchor**.

A DigiZafe user may own multiple identifiers:

```text
email
domain
username
GitHub username
phone, where legally and technically supported
known aliases
confirmed profile URLs
avatar references
```

These identifiers must not be treated as independent facts forever. They should form a user-controlled identity anchor from which candidate profiles can be assessed.

## 3.1 Identity Anchor definition

An Identity Anchor is the durable, user-scoped set of facts that DigiZafe is allowed to use to answer:

> “Does this discovered candidate likely belong to the verified user?”

It is **not**:

- a global people-search profile;
- a hidden dossier;
- an inferred legal identity;
- a cross-user identity database;
- permission to scan arbitrary people;
- permission to automatically claim ownership of every username match.

## 3.2 Anchor evidence classes

Recommended anchor evidence:

```text
verified_identifier
user_confirmed_alias
user_confirmed_profile
verified_cross_link
avatar_reference
platform-specific verified account
historical confirmed alias
```

Each anchor fact must include:

```text
id
user_id
kind
canonical_value or protected reference
verification/confirmation method
confidence
source
created_at
last_confirmed_at
revoked_at
provenance
```

Sensitive values must follow existing encryption, minimization, RLS and deletion rules.

---

# 4. Critical Separation: Identity Match vs Exposure Risk

DigiZafe must maintain two separate reasoning problems.

## 4.1 Identity Match Assessment

Question:

> **How likely is this candidate profile to belong to the verified user?**

Possible result:

```text
confirmed
high_confidence
possible
ambiguous
rejected
insufficient_evidence
```

## 4.2 Exposure Risk Assessment

Question:

> **If this candidate belongs to the user, what privacy/security exposure does it create?**

This remains the responsibility of the evidence → finding → PDSS pipeline.

## 4.3 Non-negotiable rule

Never implement:

```text
high profile risk
→ therefore profile belongs to user
```

and never implement:

```text
username match
→ confirmed identity
```

The correct pipeline is:

```text
candidate discovery
→ identity evidence
→ identity match assessment
→ confirmed/possible/rejected relationship
→ exposure extraction
→ evidence normalization
→ Confirmed/Possible PDSS tracks
```

Identity confidence and exposure severity are different dimensions.

---

# 5. New Canonical Domain Concepts

Before creating any new model, search the repository for an equivalent concept.

If no canonical equivalent exists, introduce the following.

## 5.1 CandidateProfile

A normalized discovered profile candidate.

Recommended fields:

```text
id
user_id
scan_id
source_connector
platform
profile_url
canonical_profile_url
username
display_name
bio_summary
avatar_reference
declared_links
location_hint
discovered_at
last_observed_at
raw_evidence_ref
provenance
status
```

`status` should be one of:

```text
pending_assessment
confirmed
possible
ambiguous
rejected
superseded
```

Do not persist unnecessary raw profile bodies.

## 5.2 IdentityEvidence

A single reason for or against a candidate match.

Examples:

```text
exact verified username match
rare username match
confirmed profile cross-link
reciprocal cross-link
same avatar perceptual similarity
display-name similarity
bio alias match
domain ownership link
location consistency
temporal consistency
platform collision
common username penalty
conflicting identity evidence
user confirmation
user rejection
```

Recommended fields:

```text
id
candidate_profile_id
evidence_type
direction
weight
confidence
source
explanation
provenance
created_at
```

`direction`:

```text
supports_match
contradicts_match
neutral
```

## 5.3 IdentityMatchAssessment

A versioned assessment produced from identity evidence.

Recommended fields:

```text
id
candidate_profile_id
model_version
score
probability_or_confidence
classification
evidence_summary
collision_flags
requires_user_review
created_at
```

This should be deterministic first.

## 5.4 Alias

User-controlled aliases should be explicit and revocable.

```text
alias value
alias type
source
confirmed_by_user
confidence
active/revoked
```

A discovered alias must not silently become an identity anchor.

---

# 6. Candidate Discovery Architecture

Candidate discovery broadens **where DigiZafe looks**, but not **who DigiZafe is allowed to investigate**.

The input remains the verified user's own identity anchor.

```text
Verified Identity Anchor
        ↓
Consent and scan scope
        ↓
Candidate discovery connectors
        ↓
Normalized CandidateProfile records
        ↓
Identity Match Engine
```

Candidate discovery does not itself create confirmed findings.

---

# 7. Maigret Integration

Maigret should be integrated as a bounded candidate-discovery adapter for username-based public profile discovery.

## 7.1 Role

Maigret is used to answer:

> “Which public platform profiles may exist for this verified username or confirmed alias?”

Its results are **candidate profiles**, not confirmed identity.

## 7.2 Integration boundary

Preferred architecture:

```text
DigiZafe scan orchestration
  ↓
Maigret adapter/service
  ↓
bounded username query
  ↓
normalized candidate results
  ↓
CandidateProfile
  ↓
Identity Match Engine
```

Do not let Maigret bypass:

- verified-identifier requirements;
- scan quotas;
- consent policy;
- worker isolation;
- timeouts;
- subprocess/resource limits;
- provenance;
- user isolation.

## 7.3 Execution policy

Run Maigret outside the API request path.

Recommended:

```text
Celery worker / dedicated discovery worker
```

Apply:

```text
timeout
maximum sites
maximum result count
bounded concurrency
safe subprocess invocation
output size limit
version capture
failure isolation
```

Never interpolate untrusted values into a shell command string. Use an argument list or a controlled library interface.

## 7.4 Result semantics

Every Maigret hit begins as:

```text
CandidateProfile.status = pending_assessment
```

A username match alone should normally be weak or moderate evidence.

Promotion requires independent signals such as:

```text
verified username exact match
+
rare username evidence
+
cross-link to confirmed profile/domain
+
avatar similarity
+
user confirmation
```

## 7.5 Username uniqueness / surprisal

The identity engine may estimate how discriminative a username is.

Conceptually:

```text
common username
→ low identity weight

rare/high-surprisal username
→ stronger identity evidence
```

This must be used as one factor, not as proof.

---

# 8. OSINTgram Integration

OSINTgram should be treated as **optional and experimental enrichment**, not a core dependency.

## 8.1 Purpose

If technically and legally supportable, it may enrich a candidate Instagram profile with bounded metadata useful for self-exposure analysis.

## 8.2 Constraints

OSINTgram must not become:

- a required production dependency;
- a bypass around platform access controls;
- a credential-sharing mechanism;
- a scraping path that violates frozen policy;
- a reason for the core product to fail.

It must be:

```text
feature-flagged
disabled by default where appropriate
worker-isolated
rate-limited
consent-aware
failure-isolated
clearly labeled experimental
```

## 8.3 Authentication/session boundary

If a platform requires a user session, do not store credentials casually or embed them in source/config files.

Any future authenticated connector requires a separate reviewed design covering:

```text
credential/session ownership
secret storage
revocation
scope
platform terms
session expiry
audit
deletion
```

Until that design is approved, keep OSINTgram enrichment optional and non-authoritative.

---

# 9. Identity Match Engine

The Identity Match Engine combines independent evidence into an explainable match assessment.

## 9.1 Deterministic-first approach

Start with a versioned deterministic model.

Example evidence families:

```text
identifier match
username rarity
cross-link graph
avatar similarity
display-name similarity
alias consistency
domain association
location consistency
temporal consistency
collision/contradiction evidence
user confirmation
```

## 9.2 Example conceptual weighting

Do not hardcode these exact values without evaluation, but the hierarchy should resemble:

```text
user-confirmed ownership             very strong
verified reciprocal cross-link       very strong
verified domain/account link          strong
exact rare verified username          strong
high avatar similarity                moderate/strong
display-name similarity               weak/moderate
bio keyword overlap                   weak
generic username match                weak
conflicting verified owner signal     strong negative
common-name collision                 negative/uncertainty
user rejection                        decisive negative
```

## 9.3 Collision detection

The system must actively look for reasons a candidate may belong to someone else.

Collision flags may include:

```text
same username across unrelated identities
conflicting display names
conflicting locations
incompatible cross-links
different stable avatars
multiple active candidate clusters
known high-frequency username
user rejection
```

## 9.4 User review

Ambiguous candidates should enter a review queue.

The UI should show:

```text
candidate profile
platform
why DigiZafe found it
evidence supporting match
evidence against match
confidence
what confirming it will do
what rejecting it will do
```

The user must be able to:

```text
confirm
reject
leave undecided
revoke prior confirmation
```

---

# 10. Avatar Similarity

Avatar similarity may be used as supporting identity evidence.

## 10.1 Privacy-preserving preference

Prefer local feature extraction such as:

```text
perceptual hash
embedding generated locally
normalized similarity score
```

Avoid sending user images to an external AI service merely for identity matching.

## 10.2 Semantics

Avatar similarity is not face recognition proof.

Use wording such as:

```text
"Profile images appear visually similar"
```

not:

```text
"This is definitely the same person"
```

## 10.3 Storage

Prefer storing:

```text
derived hash/embedding
algorithm version
similarity score
source reference
```

rather than retaining unnecessary image copies.

Apply existing TTL and deletion policies.

---

# 11. Cross-Link Evidence

Cross-links are among the strongest public identity signals.

Examples:

```text
verified GitHub profile → personal domain
personal domain → social profile
confirmed social profile → another candidate profile
profile bio → verified domain
reciprocal links between two profiles
```

Represent links in the existing identity graph rather than creating a second graph system.

New edge types may include:

```text
claims_profile
links_to
same_username_candidate
avatar_similar_to
confirmed_same_identity
rejected_same_identity
alias_of
```

Every edge must retain:

```text
source
confidence
status
provenance
created_at
last_verified_at
```

---

# 12. Profile Exposure Intelligence

After identity resolution, confirmed and possible profiles may be analyzed for exposure.

Potential exposure categories:

```text
public email disclosure
public phone disclosure
location disclosure
employer/school disclosure
personal domain linkage
cross-platform account linkage
high discoverability
historical profile persistence
credential/breach association
overshared biographical data
stale abandoned accounts
impersonation/confusion risk
```

The system must distinguish:

```text
publicly visible
historically indexed
inferred
user-confirmed
third-party reported
```

Do not convert harmless public metadata into exaggerated severity.

---

# 13. PDSS Integration

The existing deterministic PDSS remains authoritative.

## 13.1 Two-track mapping

Identity resolution should map evidence into existing tracks:

```text
confirmed identity + confirmed exposure
→ Confirmed track

possible identity and/or uncertain exposure
→ Possible track

rejected candidate
→ excluded from active risk contribution
```

## 13.2 Identity confidence is not severity

Do not implement:

```text
higher identity confidence
→ higher severity
```

Instead:

```text
identity confidence
→ determines evidence track / contribution confidence

exposure characteristics
→ determine risk severity
```

## 13.3 Explainability

A score explanation should be able to say:

```text
This profile contributes to Possible risk because:
- the username matches a verified alias;
- the avatar is visually similar;
- no verified cross-link confirms ownership yet.

If you confirm the profile, its eligible findings may move from the Possible track to the Confirmed track.
```

---

# 14. Exposure Timeline

Add a user-facing exposure timeline built from existing durable facts.

Possible events:

```text
identifier verified
profile first discovered
historical archive observation
breach observation
candidate confirmed
candidate rejected
finding created
score changed
recommendation created
remediation started
removal verified
profile no longer observed
```

The timeline must not fabricate continuous exposure between two observations.

Use:

```text
first_observed_at
last_observed_at
event source
confidence
historical/current semantics
```

---

# 15. New Sprint Roadmap

The recommended continuation begins after Sprint 13.

---

# Sprint 14 — Baseline Verification, Consolidation & Gap Closure

**Goal:** Turn the copy-pasted/implemented Sprint 0–13 repository into a verified engineering baseline.

## Scope

- full repository inventory;
- import/startup repair;
- migration consolidation;
- duplicate abstraction detection;
- backend test execution;
- frontend production build;
- API contract verification;
- worker/beat registration checks;
- end-to-end smoke journey;
- security and privacy regression;
- feature integration matrix;
- documented blockers.

## Definition of Done

- no P0 blocker;
- expected single migration head;
- backend and frontend build;
- core self-only flow verified;
- all future work is based on actual repository state.

---

# Sprint 15 — Verified Identity Anchor & Alias Foundation

**Goal:** Create the canonical user-controlled identity anchor.

## Scope

- identity anchor service;
- verified identifier integration;
- alias CRUD and revocation;
- confirmed profile records;
- identity evidence model;
- identity assessment model;
- RLS and deletion;
- audit events;
- frontend identity-anchor management.

**Critical rule:** No discovered candidate becomes an anchor automatically.

---

# Sprint 16 — Maigret Candidate Discovery

**Goal:** Add bounded cross-platform candidate profile discovery from verified usernames and confirmed aliases.

## Scope

- Maigret adapter;
- isolated worker execution;
- resource/time/output limits;
- candidate normalization;
- provenance;
- canonical profile URL deduplication;
- candidate review queue;
- connector status and observability;
- tests with controlled fixtures.

**Critical rule:** Maigret results are candidates, not confirmed identities.

---

# Sprint 17 — Identity Match Engine v1 + Evidence Integrity

**Goal:** Deterministically assess candidate ownership without double-counting evidence.

## Scope

- versioned identity evidence catalog;
- deterministic match scoring;
- username rarity/surprisal;
- negative evidence;
- evidence independence groups;
- canonical fact deduplication;
- source reliability semantics;
- collision detection;
- confidence bands;
- abstention/review-required state;
- user confirm/reject/revoke;
- Why Matched / Why Not Matched explanations;
- evaluation fixtures.

**Definition of Done:** Every assessment is reproducible, explainable and resistant to repeated-source confidence inflation.

---

# Sprint 18 — Avatar Similarity, Cross-Links & Identity Clusters

**Goal:** Improve identity resolution with privacy-conscious visual, graph and clustering evidence.

## Scope

- local perceptual image features;
- optional local embedding path;
- versioned similarity algorithm;
- cross-link extraction;
- reciprocal-link evidence;
- identity cluster model;
- conflicting cluster detection;
- identity graph integration;
- privacy retention rules.

**Critical rule:** Avatar similarity remains supporting evidence, not biometric certainty.

---

# Sprint 19 — Optional OSINTgram / Platform Enrichment

**Goal:** Evaluate optional Instagram-oriented enrichment without making it a core dependency.

## Scope

- architecture/legal preflight;
- feature flag;
- isolated adapter;
- session/auth boundary review if required;
- bounded metadata normalization;
- candidate enrichment only;
- failure isolation;
- explicit limitations in UI.

A NO-GO result is valid if platform access, maintenance, legal, security or credential-handling risks are unacceptable.

---

# Sprint 20 — Profile Exposure Intelligence, Temporal Reasoning & Recurrence

**Goal:** Convert resolved profile context into explainable exposure findings over time.

## Scope

- profile exposure taxonomy;
- confirmed/possible normalization;
- exposure timeline;
- temporal identity reasoning;
- historical alias handling;
- stale/current/historical semantics;
- recurrence detection;
- persistent/resolved/reappeared exposure states;
- profile-specific recommendations;
- abandoned-account signals where evidence supports them.

---

# Sprint 21 — Identity Graph + PDSS Integration v2

**Goal:** Integrate identity resolution into the existing graph and deterministic risk model without conflating identity confidence with severity.

## Scope

- candidate/confirmed graph edges;
- evidence correlation-aware graph semantics;
- uncertainty propagation;
- PDSS track mapping;
- PDSS Risk Dimensions;
- score explanation updates;
- what-if identity confirmation simulation;
- rejected candidate exclusion;
- score-history compatibility;
- scan reproducibility manifest;
- model card update;
- regression suite.

Recommended PDSS dimensions:

```text
Credential Exposure
Identity Linkability
Public Discoverability
Profile Oversharing
Historical Persistence
Remediation Difficulty
```

The authoritative deterministic overall PDSS may remain, while dimensions explain the type of risk.

---

# Sprint 22 — Self-OSINT Investigation UX

**Goal:** Make the expanded system understandable and user-controlled.

## UX areas

```text
My Identity Anchor
Candidate Profiles
Identity Clusters
Why DigiZafe thinks this may be me
Evidence For / Against
Why Matched / Why Not Matched
Confirm / Reject / Undecided
Exposure Timeline
Profile Exposure Detail
Identity Graph
Confirmed vs Possible Risk
PDSS Risk Dimensions
Recommended Actions
```

The interface must communicate uncertainty instead of presenting probabilistic matches as facts.

---

# Sprint 23 — Identity Resolution Evaluation, Security & Release Hardening

**Goal:** Validate the new system as rigorously as Sprint 13 hardened the original system.

## Scope

- identity match evaluation dataset;
- false-positive analysis;
- calibration by confidence band;
- collision tests;
- cross-user isolation;
- adversarial username tests;
- copied-avatar tests;
- recycled-username tests;
- image handling review;
- subprocess isolation;
- Maigret resource abuse tests;
- OSINTgram boundary tests if enabled;
- deletion/crypto-shred verification;
- metrics and SLO additions;
- backup/restore compatibility;
- release acceptance tests.

**Primary optimization target:** Very low false-positive identity claims. Prefer uncertainty/review over false confirmation.

---

# Sprint 24 — Identity Drift, Impersonation & Account-Recycling Detection

**Goal:** Detect meaningful changes after identity confirmation.

## Scope

- identity drift states;
- username-change tracking;
- major profile-change detection;
- possible account recycling;
- ownership uncertainty;
- identity-confusion signals;
- possible impersonation candidates;
- re-verification workflows.

Recommended states:

```text
stable
changed
major_change
ownership_uncertain
possibly_recycled
possible_impersonation
```

The system must not accuse a profile of impersonation without sufficient evidence. Use cautious, evidence-grounded labels.

---

# Sprint 25 — Remediation Effectiveness & Long-Term Exposure Monitoring

**Goal:** Measure whether actions actually reduce exposure and whether removed exposure returns.

## Scope

- expected remediation impact;
- observed post-action impact;
- time to resolution;
- repeated verification;
- recurrence events;
- remediation effectiveness score;
- long-term exposure trend;
- action outcome analytics;
- closed-loop re-scan and re-score.

Example:

```text
Exposure found
→ remediation initiated
→ removal verified
→ repeated verification
→ exposure absent
→ PDSS/risk dimensions updated
→ recurrence watch
```

This remains deterministic analytics initially. Do not automatically train models on production user outcomes.

---

# 16. Data and Migration Strategy

Do not create all future tables in one migration.

Recommended migration sequence:

```text
Sprint 15
→ identity anchors / aliases / identity evidence / assessments

Sprint 16
→ candidate profiles / discovery run references

Sprint 17
→ assessment versioning / collision metadata

Sprint 18
→ derived visual evidence metadata if required

Sprint 20
→ exposure timeline/event structures only if existing audit/history models cannot be extended
```

Every migration must verify:

```text
upgrade from current Sprint 13 head
fresh install
single expected head
RLS
foreign keys
indexes
cascade/deletion semantics
crypto-shred compatibility
```

---

# 17. API Evolution

Extend `/api/v1` rather than creating an unrelated API tree.

Possible resources:

```text
GET    /api/v1/identity/anchor
POST   /api/v1/identity/aliases
DELETE /api/v1/identity/aliases/{id}

GET    /api/v1/identity/candidates
GET    /api/v1/identity/candidates/{id}
POST   /api/v1/identity/candidates/{id}/confirm
POST   /api/v1/identity/candidates/{id}/reject
POST   /api/v1/identity/candidates/{id}/reset-review

POST   /api/v1/identity/discovery
GET    /api/v1/identity/assessments/{candidate_id}

GET    /api/v1/identity/timeline
```

Actual routes must be chosen after checking existing route conventions.

All endpoints require user scoping and stable error DTOs.

---

# 18. Security and Abuse Boundaries

The expanded system must preserve:

```text
self-only
verified identifiers
explicit consent where required
bounded discovery
centralized egress
no unrestricted dark-web crawling
no raw breach dumps
no credential stuffing
no password-reset probing
no hidden people-search product
no cross-user identity inference
```

## 18.1 Candidate discovery abuse prevention

Apply:

```text
verified input requirement
per-user quotas
per-source limits
maximum candidate count
bounded recursion depth
no automatic alias expansion from unconfirmed data
worker isolation
timeouts
cancellation
audit
```

## 18.2 Expansion depth

Avoid recursive identity explosion.

Recommended default:

```text
verified anchor
→ discover candidates
→ assess candidates
→ only confirmed candidates may contribute new anchor links
```

Possible candidates must not recursively spawn unlimited new discovery.

---

# 19. Privacy Requirements

The identity-resolution phase handles more personal context, so minimization becomes more important.

Required:

- store only data needed for matching/exposure;
- keep raw fetched content short-lived;
- prefer derived features where possible;
- preserve source attribution;
- allow candidate rejection and deletion;
- include identity data in export;
- include it in account deletion/crypto-shred;
- never train future models automatically on user identity data;
- do not expose one user's candidate data to another user.

---

# 20. Observability Extensions

Add low-cardinality metrics such as:

```text
candidate_discovery_runs_total
candidate_profiles_discovered_total
identity_assessments_total{classification}
identity_review_actions_total{action}
identity_collision_flags_total{type}
maigret_runs_total{status}
maigret_duration_seconds
avatar_similarity_evaluations_total{status}
```

Do not put usernames, profile URLs, user IDs, images or aliases in metric labels.

Correlation should support:

```text
request
→ discovery run
→ candidate
→ assessment
→ user review
→ finding
→ score
```

---

# 21. Testing Strategy

## 21.1 Unit

Test:

- candidate normalization;
- URL canonicalization;
- username comparison;
- rarity/surprisal calculation;
- deterministic match scoring;
- collision penalties;
- confidence bands;
- graph edge creation;
- PDSS track mapping;
- rejection exclusion.

## 21.2 Integration

Test:

```text
verified username
→ candidate discovery fixture
→ candidate records
→ assessment
→ user confirmation
→ graph update
→ finding normalization
→ PDSS update
```

Also:

```text
possible candidate
→ Possible track only

rejected candidate
→ no active risk contribution

candidate belonging to another test user
→ inaccessible

deleted account
→ identity records removed/crypto-shredded
```

## 21.3 Adversarial cases

Include:

```text
common username shared by many people
same display name, different person
copied avatar
changed username
recycled username
fan account
impersonation account
stale historical profile
multiple legitimate accounts on one platform
conflicting location
conflicting cross-links
```

---

# 22. Evaluation Plan for Identity Matching

Do not claim identity-resolution accuracy without an evaluation set.

Create a curated, privacy-safe fixture set containing:

```text
true matches
false matches
ambiguous matches
common username collisions
rare username matches
avatar-only similarities
cross-link-confirmed matches
contradictory evidence
```

Measure:

```text
precision
recall
false-positive rate
false-negative rate
review/abstention rate
calibration by confidence band
performance by evidence family
```

For this product, false positive identity claims are especially costly. Prefer:

```text
uncertain → review
```

over:

```text
uncertain → auto-confirm
```

---

# 23. Residual ML Boundary

Sprint 12's optional residual ML remains separate.

Do not reuse residual-risk ML as an identity-matching model.

If ML is later considered for identity matching, it requires:

```text
separate feature schema
separate dataset
separate model card
separate evaluation
separate feature flag
separate privacy review
```

The deterministic identity match engine should ship first.

---

# 24. Grounded Narrative Boundary

The narrative provider may summarize approved structured facts.

It may say:

```text
DigiZafe found three candidate profiles. One is confirmed by a cross-link from your verified domain; two remain possible because they only share your username.
```

It must not independently decide:

```text
this profile is definitely you
```

Structured identity assessment remains authoritative.

Deterministic fallback remains mandatory.

---

# 25. Recommended End-State Architecture

```text
                    ┌─────────────────────────┐
                    │ Verified Identity Anchor│
                    └────────────┬────────────┘
                                 │
                         consent + scope
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
       Existing discovery                    Candidate discovery
       Surface / Deep / Amber                 Maigret / optional
               │                              platform enrichment
               │                                   │
               └──────────────┬────────────────────┘
                              │
                    Normalized evidence
                    + CandidateProfile
                              │
          Evidence Correlation + Source Reliability
                              │
                    Identity Match Engine
                    + Negative Evidence
                    + Identity Clusters
                              │
              ┌───────────────┼───────────────┐
              │               │               │
          Confirmed         Possible        Rejected
              │               │               │
              └───────┬───────┘               └→ excluded
                      │
             Profile exposure analysis
                      │
              Existing Identity Graph
                      │
             Deterministic PDSS tracks
                      │
              Explanation + Timeline
                      │
            Recommendations / Remediation
                      │
                 Re-verification
                      │
                   Re-score
```

---

# 26. Rules for AI Coding Agents

Every coding session must begin with:

```text
1. Read this document.
2. Read the original master engineering context.
3. Inspect the actual repository.
4. Search for existing canonical abstractions.
5. Run relevant tests before changing code.
6. Make the smallest compatible change.
7. Add/update tests.
8. Run migrations/build/tests.
9. Report exactly what changed and what remains unverified.
```

The agent must never:

- assume a sprint is green because files were pasted;
- rewrite working architecture without a documented reason;
- bypass verification or consent to make a demo work;
- duplicate enums/models/services unnecessarily;
- make Maigret hits confirmed identities automatically;
- use OSINTgram as a mandatory dependency;
- conflate identity confidence with risk severity;
- silently enable experimental ML;
- weaken privacy deletion or RLS;
- invent successful test results.

---

# 27. Definition of Success for Master Plan 2

The second-stage DigiZafe evolution is successful when a verified user can:

```text
1. Build a user-controlled identity anchor.
2. Discover bounded public candidate profiles from verified identifiers.
3. Understand why each candidate may or may not belong to them.
4. Confirm, reject or leave candidates undecided.
5. See profile-derived exposure with provenance and uncertainty.
6. View confirmed and possible risk separately.
7. Understand how identity evidence affects classification, not severity.
8. Receive grounded recommendations.
9. Remediate where supported.
10. Re-verify and observe risk changes.
11. Export or delete all associated personal data.
12. Understand when multiple sources are repeating the same underlying fact.
13. See why a candidate was matched or rejected.
14. Detect meaningful identity drift and possible account recycling.
15. Measure whether remediation actually reduced exposure and whether it recurred.
```

The system should be able to say:

> “We found this candidate because it shares your verified username. It remains Possible because the username is common and no verified cross-link confirms ownership.”

and, when stronger evidence exists:

> “This profile is Confirmed because it is directly linked from your verified domain and reciprocally links back to a profile you previously confirmed.”

That explainable distinction is the core of the next DigiZafe phase.

---

# 28. Immediate Next Action

Do **not** start with Maigret integration.

Start with:

```text
Sprint 14
→ Baseline Verification, Consolidation & Gap Closure
```

Only after the real Sprint 0–13 implementation is verified should the repository proceed to:

```text
Sprint 15
→ Verified Identity Anchor & Alias Foundation
```

This sequence prevents the new identity-resolution layer from being built on unverified migrations, broken contracts, duplicate abstractions, or incomplete security controls.

---

# Appendix A — Sprint 11–13 Baseline Incorporated

This plan treats the following uploaded implementation guides as part of the current baseline:

- DigiZafe — Sprint 11 Deep + Constrained-Dark Free Amber
- DigiZafe --- Sprint 12 Implementation Guide
- DigiZafe --- Sprint 13 Implementation Guide

Their architectural roles are preserved as follows:

- **Sprint 11:** Deep + Constrained-Dark Amber remains metadata-first, consented, bounded, centralized through existing egress controls, and layer-neutral for severity.
- **Sprint 12:** Residual ML remains optional, local, bounded, explainable, auxiliary, and disabled by default unless evaluation supports enabling it.
- **Sprint 13:** Production readiness remains a mandatory operational baseline: configuration validation, structured logs, health/readiness, metrics, worker reliability, backup/restore, disaster recovery, retention verification, release gates and rollback.

---

# Appendix B — Suggested Repository Documentation Tree

```text
docs/
├── audit/
│   ├── post-sprint13-baseline-audit.md
│   ├── feature-integration-matrix.md
│   ├── test-gap-register.md
│   └── migration-status.md
├── identity/
│   ├── identity-anchor.md
│   ├── candidate-profile-semantics.md
│   ├── identity-match-model-card.md
│   ├── collision-policy.md
│   └── evaluation.md
├── privacy/
│   └── identity-resolution-data-handling.md
├── operations/
│   └── identity-resolution-runbook.md
└── adr/
    ├── identity-resolution-boundary.md
    ├── maigret-integration.md
    └── optional-osintgram-boundary.md
```

---

**End of `MASTER_ENGINEERING_CONTEXT_2.md`**
