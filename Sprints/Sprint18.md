# DigiZafe — Sprint 18 Implementation Guide

**Sprint:** 18 — Cross-Link Evidence, Safe Avatar Similarity & Identity Clustering  
**Applies after:** Sprint 17 — Evidence-Integrity-Aware Identity Match Engine  
**Primary goal:** Add bounded cross-link evidence, privacy-preserving non-biometric avatar similarity, and conservative user-scoped identity clustering without turning similarity into identity proof.

> Core invariants:
>
> `avatar similarity ≠ face recognition`
>
> `visual similarity ≠ identity proof`
>
> `cross-link ≠ ownership proof`
>
> `cluster membership ≠ confirmed identity`
>
> `correlated evidence ≠ independent evidence`

## 1. Mandatory Sprint 17 Preflight

Before implementation, verify the actual Sprint 17 repository state.

The Sprint 17 walkthrough mentions two integration flakes related to missing JWT/token imports. Do not dismiss unexplained failing tests merely because the new match-engine tests pass.

Required preflight:

- Identify the exact failing tests and errors.
- Classify each as a deterministic test defect, environment/configuration defect, or product defect.
- Fix deterministic broken imports/test defects.
- Re-run affected tests and report exact pass/fail counts.
- Verify the actual Sprint 17 migration ID and current Alembic head.
- Verify the actual Identity Match Engine version and policy version.
- Confirm CandidateProfile deduplication remains strictly user-scoped.
- Confirm assessment history uses the intended immutable/current-versioned pattern.

Do not claim a fully green regression suite while deterministic tests remain failing.

## 2. Sprint Goal

Extend the Sprint 17 identity evidence pipeline with three bounded capabilities:

1. Public cross-link evidence.
2. Non-biometric avatar image reuse/perceptual similarity.
3. Conservative identity clustering.

Target flow:

```text
Verified Identity Anchor
        ↓
Candidate Profiles
        ↓
Existing Sprint 17 Evidence
   + Cross-Link Evidence
   + Non-Biometric Avatar Evidence
        ↓
Canonical Facts
        ↓
Independence Groups
        ↓
Source Reliability + Positive/Negative Evidence
        ↓
Existing Deterministic Match Engine
        ↓
IdentityMatchAssessment
        ↓
Conservative User-Scoped Identity Clusters
        ↓
Human Review
```

Sprint 18 must extend the existing evidence engine, not create a second scoring engine.

## 3. Strict Non-Biometric Boundary

Sprint 18 may use image-level similarity techniques such as:

- SHA-256 or equivalent exact-byte hashing.
- pHash.
- dHash.
- aHash.
- Bounded image metadata comparison.

Sprint 18 must not implement:

- Face recognition.
- Facial embeddings.
- FaceNet.
- ArcFace.
- DeepFace identity matching.
- Facial landmark identity matching.
- Biometric templates.
- Person search from a face.
- Age, gender, race, ethnicity, emotion, or other sensitive-trait inference.

The system compares images, not faces or biometric identities.

Allowed language:

```text
These profiles appear to reuse the same or a visually similar avatar image.
```

Disallowed language:

```text
The faces belong to the same person.
```

## 4. Feature Flags

Add or reuse bounded feature flags:

```text
FEATURE_IDENTITY_CROSS_LINKS=false
FEATURE_AVATAR_SIMILARITY=false
FEATURE_IDENTITY_CLUSTERING=false
```

Safe defaults must be `false`.

Local development may explicitly override them to `true`.

When disabled:

```text
cross-link feature disabled
→ no new cross-link retrieval

avatar feature disabled
→ no new avatar fetch or processing

clustering disabled
→ no cluster creation/rebuild
```

Existing stored data may remain viewable according to policy.

## 5. Consent and Egress Boundary

Any new external retrieval must reuse the canonical consent and centralized egress/SSRF architecture.

Required flow:

```text
authenticated user
→ own eligible candidate/profile
→ feature enabled
→ required consent
→ rate/quota policy
→ approved worker task
→ centralized egress validation
→ bounded retrieval
```

No consent must mean:

```text
no external fetch
no egress-performing worker execution
```

Do not create a parallel consent implementation.

## 6. Safe Avatar Acquisition

Avatar URLs must originate from approved evidence sources such as:

- Approved connector output.
- Existing normalized candidate metadata.
- Existing confirmed-profile metadata.
- Approved bounded profile metadata extraction.

Do not expose an arbitrary backend image-fetch endpoint accepting unrestricted user URLs.

Every fetch must enforce:

- HTTP/HTTPS scheme policy.
- DNS/IP validation.
- Loopback blocking.
- Private network blocking.
- Link-local blocking.
- Metadata-service blocking.
- Redirect revalidation.
- Content-type validation.
- Maximum response bytes.
- Timeout.
- Maximum redirects.
- Safe image decoding.
- Maximum decoded pixel count.
- Maximum width/height.

Never bypass the centralized egress service with direct unrestricted `requests.get()` or `httpx.get()` calls.

## 7. Image Resource Limits

Define and document explicit limits for:

```text
maximum download bytes
maximum decoded pixels
maximum image width
maximum image height
supported MIME types
network timeout
processing timeout
temporary-file lifetime
```

Protect against:

- Decompression bombs.
- Malformed images.
- Oversized images.
- Content-type spoofing.
- Redirect abuse.
- Resource exhaustion.

## 8. Avatar Storage Policy

Prefer storing:

```text
exact hash
perceptual fingerprint
safe dimensions/MIME metadata
source provenance
observation timestamps
```

rather than permanent raw image copies.

If raw images are temporarily retained:

```text
short TTL
bounded size
user-scoped access
encrypted according to existing storage policy
automatic purge
```

Do not persist biometric embeddings because none should exist.

## 9. ProfileVisualFingerprint

Create a durable model only if required by the architecture.

Possible fields:

```text
id
user_id
candidate_profile_id or confirmed_profile_reference_id
source_type
source_url_reference
exact_hash
perceptual_hash
image_width
image_height
mime_type
observed_at
expires_at
status
created_at
```

All records must be user-scoped.

## 10. Deterministic Avatar Comparison

Use deterministic comparisons.

Conceptual policy:

```text
same exact cryptographic hash
→ exact image reuse evidence

pHash Hamming distance within strict threshold
→ strong perceptual similarity

distance within broader bounded threshold
→ weak perceptual similarity

outside threshold
→ no supporting visual evidence
```

Exact thresholds must be documented, versioned, and tested with fixtures.

Do not expose the result as a probability unless it is genuinely calibrated.

## 11. Avatar Evidence Types

Possible evidence types:

```text
avatar_exact_hash_match
avatar_perceptual_near_match
avatar_perceptual_weak_match
avatar_mismatch
avatar_unavailable
avatar_fetch_failed
```

Required semantics:

```text
avatar_unavailable
→ unknown

avatar_fetch_failed
→ unknown
```

A different avatar should normally be neutral or weak negative evidence because the same person may use different avatars.

## 12. Visual Evidence Independence

For the same image pair:

```text
exact hash match
+
pHash similarity
```

must not count as two independent signals.

Use one canonical visual fact and one independence group, such as:

```text
visual_image_pair:<canonical_pair>
```

Apply one bounded contribution.

Repeated rediscovery of the same image must not increase confidence indefinitely.

## 13. Visual Evidence Cap

Required invariant:

```text
avatar evidence alone
→ cannot produce likely_match
```

Even exact avatar reuse may occur because of:

- Default avatars.
- Logos.
- Memes.
- Shared organization branding.
- Reposted images.

Visual evidence requires independent corroboration for the highest algorithmic assessment band.

## 14. Default/Common Avatar Handling

Where practical, downgrade known or locally repeated common/default images.

Possible signals:

```text
known maintained default-image hash
same image reused across many candidates in the user's own candidate set
```

Do not claim global default-image knowledge without a maintained source.

## 15. Cross-Link Evidence

A cross-link is an explicit public reference from one profile/resource to another.

Examples:

```text
candidate profile → confirmed profile
confirmed profile → candidate profile
candidate profile → another candidate
profile → known anchor-controlled domain
```

A cross-link supports an identity hypothesis but does not prove ownership.

## 16. Cross-Link Acquisition

Prefer cross-links already available from:

- Approved connector output.
- Existing normalized profile metadata.
- Bounded approved profile retrieval.

Do not introduce an unrestricted crawler.

If profile retrieval is required:

```text
approved source
→ consent/feature gate
→ centralized egress
→ bounded response
→ content validation
→ link extraction only
```

Do not automatically follow every extracted link.

Separate:

```text
link observation
```

from:

```text
approved follow-up retrieval
```

Every follow-up retrieval must independently pass egress validation.

## 17. Cross-Link Normalization and Provenance

For each observed link preserve:

```text
source profile/candidate
target URL reference
canonical target URL
direction
observation timestamp
source connector/fetch
derived_from
canonical fact key
independence group
```

Use existing platform-aware canonical URL normalization.

## 18. Cross-Link Evidence Types

Possible:

```text
candidate_links_to_confirmed_profile
confirmed_profile_links_to_candidate
mutual_cross_link
candidate_links_to_known_anchor_domain
candidate_links_to_other_candidate
cross_link_conflict
```

Only implement evidence supported by actual data.

## 19. Cross-Link Independence

Multiple representations of the same underlying link must not multiply confidence.

Example:

```text
website field
bio link
same URL in page HTML
```

may be one canonical cross-link fact.

Mutual links may be stronger than one-way links, but must still be evaluated for source dependence.

## 20. Sprint 17 Evidence Integration

All new evidence must enter the existing pipeline:

```text
raw observation
→ normalized evidence
→ canonical fact deduplication
→ independence grouping
→ source reliability
→ direction
→ bounded scoring
→ explanation mapping
```

Extend:

```text
IdentityEvidenceService
IdentityMatchEngine policy
```

Do not create an independent avatar score that bypasses Sprint 17 evidence integrity.

## 21. Engine and Policy Versioning

Adding cross-link and avatar evidence changes assessment behavior.

Increment the appropriate:

```text
IDENTITY_MATCH_POLICY_VERSION
```

and, if engine behavior changes materially:

```text
IDENTITY_MATCH_ENGINE_VERSION
```

Record versions on every new assessment.

Existing assessments must become stale when their relevant policy/input state changes.

## 22. Assessment Recalculation

When new evidence appears:

```text
new avatar evidence
or new cross-link evidence
→ current assessment becomes stale
→ bounded deterministic recalculation
```

Do not synchronously fan out recalculation across an unbounded candidate set.

Use the existing worker architecture where appropriate.

## 23. Identity Clustering Goal

An IdentityCluster groups profiles that may represent the same online identity hypothesis.

A cluster is not a verified person.

Use terminology such as:

```text
Identity Cluster
Possible Identity Group
Candidate Cluster
```

Avoid:

```text
Verified Person
Confirmed Human
```

unless separately established by existing verification mechanisms.

## 24. Cluster Scope

All clusters must be strictly:

```text
user-scoped
```

Never create global cross-user identity clusters.

User A's profile graph and cluster data must remain inaccessible to User B.

## 25. Cluster Inputs

Clusters may consume:

```text
CandidateProfile
ConfirmedProfileReference
IdentityMatchAssessment
username evidence
cross-link evidence
non-biometric avatar evidence
explicit user confirmation
explicit user dismissal
```

Every cluster member must preserve provenance and membership basis.

## 26. Conservative Cluster Rules

Do not merge profiles solely because they share:

```text
a common username
a similar avatar
one weak cross-link
```

Recommended minimum:

```text
strong pairwise assessment
+
sufficient independent evidence
```

or:

```text
explicit user-confirmed relationship
```

Exact merge rules must be deterministic, documented, and versioned.

## 27. Cluster Status

Recommended:

```text
supported
ambiguous
conflicting
```

If an explicit user-confirmed cluster state is introduced, keep it semantically separate from algorithmic support.

## 28. Cluster Contradictions

Contradictions must be surfaced, not averaged away.

Examples:

```text
one member explicitly dismissed
strong incompatible evidence between members
conflicting confirmed-profile relationships
```

Possible result:

```text
cluster_status = conflicting
```

## 29. Cluster Models

Possible:

```text
IdentityCluster
IdentityClusterMember
```

Conceptual fields:

```text
IdentityCluster:
- id
- user_id
- anchor_id
- anchor_version
- cluster_status
- cluster_version
- policy_version
- input_fingerprint
- explanation_summary
- created_at
- updated_at

IdentityClusterMember:
- cluster_id
- candidate_profile_id or confirmed_profile_reference_id
- membership_status
- membership_basis
- assessment_reference
- created_at
```

Adapt to existing graph/model conventions.

## 30. Cluster Merge Safety

Do not use blind transitive merging.

Mandatory test:

```text
A strongly supports B
B strongly supports C
A conflicts with C
→ do not automatically merge A, B, and C into one supported cluster
```

Contradiction checks must run before cluster merge.

## 31. Cluster Rebuild and Reversibility

Clusters must be rebuildable when:

```text
candidate dismissed
candidate confirmed
evidence revoked
anchor changes
assessment changes
cross-link becomes stale
visual evidence becomes stale
policy version changes
```

Do not make algorithmic cluster membership irreversible.

## 32. Cluster Versioning and Idempotency

Record:

```text
cluster_version
policy_version
input_fingerprint
```

Same inputs and same policy must produce the same deterministic cluster result.

Repeated task delivery must not create uncontrolled duplicate clusters.

## 33. Identity Graph Integration

Reuse the existing identity graph where appropriate.

Possible semantics:

```text
IdentityAnchor
→ HAS_CANDIDATE_CLUSTER
→ IdentityCluster

IdentityCluster
→ HAS_MEMBER
→ CandidateProfile
```

Do not create confirmed identity edges from algorithmic clustering.

## 34. PDSS Boundary

Sprint 18 must not silently convert:

```text
avatar similarity
cross-link evidence
cluster membership
```

into authoritative Confirmed PDSS exposure.

Default:

```text
identity enrichment
→ assessment/review only
→ no automatic authoritative PDSS change
```

Preserve existing Confirmed/Possible semantics.

## 35. API Design

Adapt routes to repository conventions.

Possible endpoints:

```text
GET  /api/v1/identity/candidates/{id}/visual-evidence
POST /api/v1/identity/candidates/{id}/visual-evidence/refresh

GET  /api/v1/identity/candidates/{id}/cross-links
POST /api/v1/identity/candidates/{id}/cross-links/refresh

GET  /api/v1/identity/clusters
GET  /api/v1/identity/clusters/{cluster_id}
POST /api/v1/identity/clusters/rebuild
```

All refresh/rebuild operations must be authenticated, user-scoped, bounded, rate-limited, and feature/consent-gated where external retrieval occurs.

## 36. Worker Architecture

External retrieval and image processing should not block synchronous API requests.

Preferred:

```text
API
→ durable refresh/rebuild request
→ Celery task
→ approved egress
→ bounded processing
→ evidence persistence/snapshot
→ assessment recalculation
→ cluster rebuild if needed
```

Consider dedicated bounded queues such as:

```text
identity_enrichment
identity_visual
```

if necessary to avoid worker starvation.

Document task names, queues, timeouts, retries, and concurrency.

## 37. Retry Policy

Do not blindly retry permanent failures.

Examples:

```text
invalid URL → no retry
blocked private IP → no retry
unsupported MIME → no retry
decode failure → no retry or tightly bounded retry
temporary network timeout → bounded retry
```

## 38. Raw Content Retention

Do not retain fetched HTML indefinitely.

Prefer:

```text
normalized cross-links
safe fetch metadata
provenance
```

For images prefer:

```text
fingerprints
safe metadata
```

Temporary raw content must have a short bounded lifecycle.

## 39. Staleness

Cross-link and avatar observations can become stale.

Define and document TTL/staleness rules.

Examples:

```text
old avatar fingerprint → stale visual evidence
old cross-link observation → stale cross-link evidence
```

Stale evidence must not silently retain full current weight forever.

## 40. Frontend Scope

Extend `/app/identity`.

Candidate details may show:

```text
Username evidence
Cross-link evidence
Avatar reuse evidence
Why Matched
Why Not Matched
```

Cluster UI may show:

```text
Possible identity group
members
supporting evidence
conflicting evidence
user-confirmed members
algorithmically assessed members
```

Do not visually present a cluster as a single verified identity.

## 41. Frontend Language

Use:

```text
Similar avatar image
Exact image reuse
Cross-linked profile
Possible identity group
Supporting evidence
Conflicting evidence
```

Avoid:

```text
Face match
Same person detected
Biometrically verified
100% identity cluster
```

## 42. Privacy Export

Extend export with appropriate:

```text
visual fingerprint metadata
cross-link evidence
cluster records
cluster membership
cluster explanations
engine/policy versions
```

Do not export transient raw images unless required by established policy.

## 43. Deletion and Shredding

Verify:

```text
visual fingerprints deleted/inaccessible
temporary images purged
cross-link evidence deleted/inaccessible
clusters deleted/inaccessible
cluster graph edges cleaned
caches invalidated
```

No orphaned identity-enrichment data may remain.

## 44. Audit Events

Recommended:

```text
identity_visual_refresh_requested
identity_visual_evidence_created
identity_cross_link_refresh_requested
identity_cross_link_evidence_created
identity_cluster_built
identity_cluster_rebuilt
identity_cluster_conflict_detected
```

Do not log raw image bytes or unnecessary sensitive URLs.

## 45. Security Tests — Egress

Required:

```text
localhost blocked
127.0.0.1 blocked
::1 blocked
private RFC1918 blocked
link-local blocked
metadata-service targets blocked
redirect to private target blocked
DNS/IP revalidation preserved
unsupported scheme blocked
oversized response blocked
```

Reuse existing SSRF test infrastructure.

## 46. Security Tests — Images

Required:

```text
oversized image blocked
decompression bomb bounded
invalid MIME rejected
content-type spoof handled safely
malformed image does not crash worker
processing timeout works
temporary raw-image retention policy enforced
```

## 47. Security Tests — Ownership

Required:

```text
User A cannot enrich User B candidate
User A cannot read User B visual evidence
User A cannot read User B cross-links
User A cannot read User B clusters
User A cannot rebuild User B clusters
```

Any cross-user failure is P0.

## 48. Avatar Fixture Tests

Use local fixtures only.

Test:

```text
exact same image
resized same image
recompressed same image
slightly modified image
cropped image
different image
common/default image
malformed image
```

Do not depend on live websites in the normal automated test suite.

## 49. Cross-Link Tests

Test:

```text
one-way link
mutual link
duplicate links
tracking parameters
canonical URL normalization
same link represented in multiple fields
unsafe link observation
```

Verify canonical fact deduplication.

## 50. Independence Tests

Mandatory:

```text
exact hash + pHash on same image pair
→ one visual independence group

same cross-link from multiple fields
→ one canonical fact

same image rediscovered repeatedly
→ confidence does not increase indefinitely
```

## 51. Cluster Tests

Test:

```text
strongly supported pair
ambiguous pair
conflicting pair
dismissed member
cluster rebuild
unchanged-input idempotency
policy-version change
three-node transitive trap
```

The transitive trap test is mandatory.

## 52. Sprint 17 Regression

Re-run:

```text
deterministic scoring
no double counting
negative evidence
collision caps
abstention
contradiction handling
structured explanations
assessment history
assessment staleness
RLS isolation
```

Resolve and report the JWT/token integration-test flakes before final GO.

## 53. Sprint 16 Regression

Re-run:

```text
Maigret feature disabled → zero execution
consent denied → zero execution
eligible input enforcement
command-injection resistance
timeout behavior
candidate deduplication is user-scoped
candidate confirmation/dismissal
privacy lifecycle
```

## 54. Sprint 15 Regression

Re-run:

```text
Identity Anchor
alias add/revoke
confirmed profile add/revoke
anchor versioning
privacy lifecycle
cross-user isolation
```

## 55. Sprint 14 Critical Regression

Re-run:

```text
Deep scan without consent → 403 + zero egress
Surface scan functional
PDSS deterministic
Confirmed/Possible semantics unchanged
Groq fallback
Residual ML disabled path
```

## 56. Migration Strategy

First verify the actual Sprint 17 migration head.

Possible new tables:

```text
profile_visual_fingerprints
identity_cross_link_observations
identity_clusters
identity_cluster_members
```

Create only what is necessary.

Verify:

```text
actual Sprint 17 head
→ Sprint 18 migration
→ one intended final head

fresh database
→ Sprint 18 head

application startup
→ successful
```

## 57. Suggested Backend Layout

Adapt to the repository:

```text
backend/app/
├── models/
│   ├── profile_visual_fingerprint.py
│   ├── identity_cross_link.py
│   └── identity_cluster.py
├── services/
│   ├── avatar_similarity_service.py
│   ├── cross_link_evidence_service.py
│   ├── identity_cluster_service.py
│   └── existing identity_evidence_service.py
├── tasks/
│   └── identity_enrichment_tasks.py
└── api/v1/
    └── identity_enrichment.py
```

Reuse existing abstractions wherever possible.

## 58. Documentation

Create or update:

```text
docs/identity/avatar-similarity.md
docs/identity/cross-link-evidence.md
docs/identity/identity-clustering.md
docs/security/identity-enrichment-egress.md
docs/privacy/identity-enrichment-data.md
```

Document:

```text
non-biometric boundary
algorithms
thresholds
cross-link semantics
evidence caps
independence rules
cluster merge rules
cluster contradiction rules
staleness
retention
known limitations
```

## 59. Known Limitations

Document explicitly:

```text
same avatar can be reused by different people
different avatars can belong to the same person
default avatars create collisions
cross-links can be stale or copied
profiles can be compromised
cluster inference can be wrong
transitive relationships can create false merges
```

These limitations must influence scoring and UX.

## 60. Implementation Order

### Phase A — Preflight

```text
verify Sprint 17 migration head
resolve JWT/token test flakes
verify candidate deduplication is user-scoped
verify Sprint 17 engine/policy versions
```

### Phase B — Safe Enrichment Boundary

```text
feature flags
→ consent
→ egress
→ worker limits
→ retention
```

### Phase C — Cross-Links

```text
observation
→ canonicalization
→ provenance
→ independence
→ evidence integration
```

### Phase D — Avatar Similarity

```text
approved image source
→ bounded fetch
→ safe decode
→ fingerprint
→ deterministic comparison
→ visual evidence
```

### Phase E — Match Engine Integration

```text
new evidence
→ policy version increment
→ stale assessments
→ deterministic recalculation
```

### Phase F — Clustering

```text
candidate relationships
→ conservative merge
→ contradiction checks
→ cluster versioning
```

### Phase G — Privacy and Graph

```text
export
→ deletion
→ graph integration
→ cache cleanup
```

### Phase H — Frontend

```text
visual evidence
→ cross-links
→ clusters
→ limitations
```

### Phase I — Verification

```text
security
→ image fixtures
→ cross-links
→ independence
→ clustering
→ RLS
→ privacy
→ Sprint 14–17 regression
```

## 61. P0/P1 Defect Policy

For defects discovered during implementation:

```text
reproduce
→ classify
→ regression test
→ smallest safe fix
→ affected tests
→ document
```

Stop for approval if a fix would:

```text
introduce biometric identification
change frozen security/privacy invariants
change authoritative PDSS semantics
require major architecture redesign
introduce breaking API changes
```

## 62. Required Final Walkthrough

At completion provide:

1. Actual Sprint 17 starting migration head.
2. Sprint 18 migration ID and final head.
3. Sprint 17 JWT/token integration-flake root cause and resolution.
4. Exact full regression test counts.
5. Feature flags and defaults.
6. Consent behavior.
7. Egress/SSRF boundary.
8. Avatar acquisition boundary.
9. Image resource limits.
10. Raw image retention policy.
11. Avatar fingerprint algorithms.
12. Exact similarity thresholds.
13. Confirmation that no biometric/face-recognition system was introduced.
14. Visual evidence types and caps.
15. Cross-link acquisition strategy.
16. Cross-link canonicalization.
17. Cross-link evidence types and caps.
18. Independence-group rules.
19. Match engine/policy version changes.
20. Assessment staleness/recalculation behavior.
21. Cluster models.
22. Cluster merge rules.
23. Cluster contradiction rules.
24. Cluster versioning/idempotency.
25. API endpoints.
26. Worker tasks, queues, timeouts, retries, and concurrency.
27. Frontend changes.
28. RLS/cross-user isolation results.
29. SSRF/egress test results.
30. Image safety test results.
31. Avatar fixture test results.
32. Cross-link tests.
33. No-double-counting tests.
34. Transitive cluster-trap test.
35. Privacy export/deletion results.
36. Identity graph integration.
37. PDSS regression result.
38. Sprint 17 regression results.
39. Sprint 16 regression results.
40. Sprint 15 regression results.
41. Sprint 14 critical regression results.
42. P0–P3 issues found.
43. Minimal fixes applied.
44. Files created/modified.
45. Remaining limitations.
46. GO / CONDITIONAL GO / NO-GO for Sprint 19.

Do not predetermine GO.

## 63. Definition of Done

### Preflight

- [ ] Actual Sprint 17 migration head verified.
- [ ] Sprint 17 engine/policy versions verified.
- [ ] JWT/token integration flakes classified and resolved or explicitly documented.
- [ ] Candidate deduplication confirmed user-scoped.

### Avatar similarity

- [ ] No face recognition.
- [ ] No facial embeddings.
- [ ] No biometric identification.
- [ ] Approved image sources only.
- [ ] Centralized egress used.
- [ ] SSRF protections pass.
- [ ] Download size bounded.
- [ ] Pixel count bounded.
- [ ] Decode safety tested.
- [ ] Exact hash supported.
- [ ] Perceptual hash supported.
- [ ] Thresholds versioned.
- [ ] Same-image evidence grouped.
- [ ] Visual evidence alone cannot reach `likely_match`.
- [ ] Raw image retention minimized.

### Cross-links

- [ ] Cross-links canonicalized.
- [ ] Direction preserved.
- [ ] Provenance preserved.
- [ ] Duplicate links deduplicated.
- [ ] Follow-up fetches independently egress-validated.
- [ ] Cross-link evidence capped.
- [ ] Cross-link evidence does not auto-confirm identity.

### Evidence engine

- [ ] Sprint 17 canonical fact rules preserved.
- [ ] Independence groups preserved.
- [ ] New evidence types documented.
- [ ] Policy version incremented.
- [ ] Existing assessments become stale when appropriate.
- [ ] Recalculation deterministic.
- [ ] No double counting.

### Clustering

- [ ] Clusters are user-scoped.
- [ ] Cluster membership is explainable.
- [ ] Weak username-only similarity cannot merge clusters.
- [ ] Contradictions are surfaced.
- [ ] Transitive trap test passes.
- [ ] Dismissed candidates handled correctly.
- [ ] Cluster rebuild is deterministic.
- [ ] Cluster versioning exists.
- [ ] Cluster membership does not mean confirmed identity.

### Security

- [ ] Cross-user enrichment blocked.
- [ ] Cross-user visual evidence blocked.
- [ ] Cross-user clusters blocked.
- [ ] SSRF tests pass.
- [ ] Malformed image tests pass.
- [ ] Resource-exhaustion controls pass.

### Privacy

- [ ] Visual fingerprints exported appropriately.
- [ ] Cross-link evidence exported appropriately.
- [ ] Cluster data exported appropriately.
- [ ] Deletion/shredding covers all new data.
- [ ] Temporary raw content is purged.

### Regression

- [ ] Sprint 17 match engine remains deterministic.
- [ ] Sprint 16 Maigret boundaries remain intact.
- [ ] Sprint 15 Identity Anchor remains intact.
- [ ] Sprint 14 zero-egress consent boundary remains intact.
- [ ] PDSS semantics remain unchanged.
- [ ] Frontend production build passes.

Release gate:

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

## 64. GO / NO-GO Gate for Sprint 19

### GO

Proceed when:

```text
avatar comparison is strictly non-biometric
all image/network retrieval uses approved egress
visual evidence is bounded and non-authoritative
cross-links preserve provenance and independence
clusters are user-scoped and conservative
transitive false merges are prevented
new evidence integrates into Sprint 17 deterministically
privacy lifecycle passes
blocking deterministic test defects are resolved
Sprint 14–17 regressions remain green
```

### CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
biometric boundary
SSRF/egress
cross-user isolation
evidence integrity
cluster correctness
privacy
determinism
```

### NO-GO

Do not begin Sprint 19 with:

```text
face recognition
biometric embeddings
arbitrary image fetching
SSRF bypass
global cross-user clusters
visual evidence auto-confirming identity
blind transitive cluster merging
unresolved deterministic integration failures
broken privacy deletion
unresolved P0
unaccepted P1
```

## 65. Handoff to Sprint 19

Sprint 19 should consume:

```text
Verified Identity Anchor
CandidateProfile
IdentityMatchAssessment
canonical evidence
cross-links
visual reuse evidence
identity clusters
user confirmations
user dismissals
```

Recommended Sprint 19 direction:

```text
OSINTgram integration as an isolated optional connector
+
source-specific provenance
+
connector capability policy
+
safe account/session boundary
+
candidate discovery only
```

OSINTgram must be treated more cautiously than Maigret because some capabilities may require authenticated platform sessions and may have changing operational/platform constraints.

Sprint 19 must not:

```text
share user credentials with unrelated services
store plaintext session secrets
bypass platform access controls
turn connector output into automatic identity proof
```

## 66. Final Sprint 18 Principle

Sprint 18 adds richer evidence, not stronger claims than the evidence can support.

The system should be able to say:

```text
This candidate uses a visually similar avatar image.

This profile links to another profile you confirmed.

These observations are grouped according to their provenance and independence.

Together they may strengthen or weaken the deterministic assessment.

The result remains an identity assessment, not automatic identity verification.
```

Target architecture after Sprint 18:

```text
VERIFIED IDENTITY ANCHOR
        ↓
CANDIDATE DISCOVERY
        ↓
IDENTITY EVIDENCE
   ├── USERNAME
   ├── CROSS-LINK
   ├── NON-BIOMETRIC AVATAR REUSE
   ├── POSITIVE / NEGATIVE
   ├── RELIABILITY
   └── INDEPENDENCE
        ↓
DETERMINISTIC MATCH ENGINE
        ↓
CONSERVATIVE USER-SCOPED IDENTITY CLUSTERS
        ↓
HUMAN REVIEW
```

Sprint 18 is complete when DigiZafe can safely add cross-link and non-biometric visual-reuse evidence, integrate it without double counting, build conservative user-scoped identity clusters, surface contradictions, preserve privacy and provenance, and avoid turning similarity into identity proof.

---

**End of Sprint 18 Implementation Guide**
