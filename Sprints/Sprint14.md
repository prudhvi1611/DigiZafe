# DigiZafe --- Sprint 14 Implementation Guide

**Sprint:** 14 --- Baseline Verification, Consolidation & Gap Closure  
**Document version:** 1.0  
**Applies after:** Sprint 13 --- Production Readiness, Observability, Reliability & Release Hardening  
**Architecture baseline:** Verified and working Sprint 0--13 system  
**Master context:** `MASTER_ENGINEERING_CONTEXT_2.md`  
**Primary goal:** Establish a measured, reproducible, documented Sprint 0--13 baseline before Sprint 15 introduces the Verified Identity Anchor.

> Sprint 0--13 is considered working. Sprint 14 must not rebuild or redesign the product.
>
> Sprint 14 verifies the real repository, freezes canonical contracts, closes genuine gaps only when evidence requires it, and documents the safe extension points for Sprint 15.
>
> `file exists ≠ integrated ≠ tested`, but equally, `working code ≠ code that should be rewritten`.

---

# 1. Sprint Goal

Convert the working Sprint 0--13 repository into a **verified continuation baseline** for Master Engineering Context 2.

Sprint 14 must answer:

```text
What is implemented?
What is canonical?
What is wired at runtime?
What is tested?
What is optional?
What is deprecated?
What must Sprint 15 reuse?
```

Expected flow:

```text
Working Sprint 0–13
→ Repository inventory
→ Automated verification
→ Migration/contract verification
→ Security/privacy regression
→ End-to-end journey verification
→ Gap classification
→ Minimal fixes if required
→ Baseline freeze
→ Sprint 15 readiness
```

Sprint 14 is a verification, consolidation, documentation, and regression-protection sprint. It is not a feature-expansion sprint.

---

# 2. Non-Negotiable Constraints

Preserve all Sprint 0--13 invariants:

- G1 self-only scanning.
- Verified identifiers only for protected discovery.
- Explicit consent before consent-gated egress.
- Centralized outbound request enforcement.
- No unrestricted dark-web crawling.
- No raw breach-dump storage.
- No credential stuffing or password-reset probing.
- User-directed remediation.
- Deterministic PDSS remains authoritative.
- Confirmed and Possible risk tracks remain separate.
- Provenance and evidence-quality semantics remain intact.
- RLS and cross-user isolation remain enforced.
- Evidence TTL, privacy export, deletion, and crypto-shred remain intact.
- Groq remains only within the approved grounded narrative boundary.
- Deterministic narrative fallback remains mandatory.
- Residual ML remains optional, bounded, auxiliary, and non-authoritative.
- Constrained-Dark remains feature-gated and fail-closed.
- Production configuration, observability, release, and rollback discipline remain intact.

Sprint 14 must not introduce:

```text
Maigret
OSINTgram
CandidateProfile
Verified Identity Anchor
identity-match scoring
avatar matching
identity clusters
new PDSS dimensions
new discovery sources
identity drift detection
impersonation detection
remediation-effectiveness scoring
```

Those belong to later sprints.

---

# 3. Sprint 14 Scope

## Included

- repository and architecture inventory;
- configuration and feature-flag inventory;
- database/migration verification;
- model/table/RLS inventory;
- API/DTO inventory;
- worker/task/scheduler inventory;
- connector and egress-path inventory;
- frontend route/API-client inventory;
- test-suite inventory and execution;
- security/privacy regression;
- end-to-end workflow verification;
- optional-feature fallback verification;
- observability verification;
- backup/restore and release-runbook review;
- duplicate abstraction detection;
- dead/disconnected code identification;
- minimal evidence-driven fixes;
- regression tests for critical fixes;
- baseline manifests;
- canonical contract freeze;
- Sprint 15 extension-point documentation.

## Excluded

- new self-OSINT features;
- new connectors;
- identity candidate discovery;
- identity matching or clustering;
- PDSS semantic changes;
- new ML architecture;
- major UI redesign;
- microservice decomposition;
- unrelated framework upgrades.

---

# 4. Verification States

Use only:

```text
VERIFIED
PARTIALLY_VERIFIED
PRESENT_NOT_INTEGRATED
OPTIONAL_DISABLED
DEPRECATED
BROKEN
MISSING
BLOCKED
NOT_APPLICABLE
```

Do not use “probably works” or “file exists” as verification states.

A feature becomes `VERIFIED` only through appropriate evidence such as:

```text
automated test
controlled runtime check
migration verification
API contract check
worker execution check
frontend production build
documented operational exercise
```

---

# 5. Mandatory Repository Preflight

Before editing code:

1. Read `MASTER_ENGINEERING_CONTEXT_2.md`.
2. Read the original master engineering context.
3. Read Sprint 11, 12, and 13 guides.
4. Inspect the actual repository tree.
5. Inspect Git status, branch, and commit.
6. Record dependency lockfiles.
7. Record migration heads.
8. Record enabled/disabled feature flags without exposing secrets.
9. Run existing startup and test commands before modifications.

Adapt commands to the repository:

```bash
git status
git branch --show-current
git rev-parse HEAD

docker compose config
alembic heads
alembic current

pytest --collect-only
```

Never print secret environment values into reports or CI logs.

---

# 6. Required Deliverables

Create or update canonical equivalents:

```text
docs/audit/
├── post-sprint13-baseline-audit.md
├── feature-integration-matrix.md
├── test-gap-register.md
├── migration-status.md
├── canonical-contracts.md
├── extension-points-for-sprint15.md
└── sprint14-final-verification.md

docs/baseline/
├── sprint0-13-baseline-manifest.md
├── feature-flags.md
├── runtime-components.md
└── optional-dependency-behavior.md
```

Do not duplicate existing canonical documentation.

---

# 7. Feature Integration Matrix

Create `docs/audit/feature-integration-matrix.md`.

Recommended columns:

| Capability | Sprint | Canonical module | API/UI entry point | Persistence | Tests | Runtime verified | Status | Notes |
|---|---:|---|---|---|---|---|---|---|

Cover at minimum:

```text
authentication
token lifecycle
password hashing
MFA if enabled
verified identifiers
verification challenges
consent
egress enforcement
connector SDK
Surface connectors
Deep Amber
Constrained-Dark boundary
scan state machine
Celery tasks
reconciliation
SSE/progress
evidence storage
TTL/purge
finding normalization
identity graph
PDSS
Confirmed/Possible tracks
score history
what-if
recommendations
alerts
remediation
re-verification
privacy export
deletion/crypto-shred
audit trail
frontend journeys
Groq narrative
deterministic fallback
residual ML disabled path
health/readiness
metrics/logging
backup/restore
release/rollback
```

---

# 8. Canonical Contract Inventory

Create `docs/audit/canonical-contracts.md`.

Identify one canonical definition for:

```text
IdentifierType
ExposureLayer
finding kind/type
finding status
confidence semantics
source/provenance
scan status
connector-run status
consent state
verification state
PDSS score DTO
Confirmed/Possible semantics
recommendation status
remediation status
audit event
error DTO
user ownership scope
```

For each record:

```text
name
canonical file
database representation
API representation
frontend representation
known adapters
deprecated duplicates
future extension notes
```

If duplicate definitions exist, do not delete them immediately. First determine runtime imports, persistence use, API use, tests, and historical compatibility.

---

# 9. Database and Migration Verification

Create `docs/audit/migration-status.md`.

Run:

```bash
alembic heads
alembic current
alembic upgrade head
```

Verify:

```text
fresh database → upgrade head → application startup
supported historical baseline → upgrade head → application startup
```

Inventory major domains:

```text
users/auth
verification
consent
identifiers
scans
connector runs
evidence/findings
identity graph
scores
recommendations
remediation
audit/privacy
residual ML metadata if present
```

Verify:

- foreign keys;
- indexes;
- unique/check constraints;
- cascade behavior;
- RLS;
- user ownership;
- timestamps;
- deletion semantics;
- encryption metadata;
- crypto-shred compatibility.

Do not add future identity-resolution tables in Sprint 14 unless they already exist canonically.

---

# 10. RLS and Cross-User Isolation

Prove that User A cannot read or mutate User B:

```text
identifiers
scans
findings
scores
recommendations
remediation records
audit/privacy data
```

Test:

- direct object-ID guessing;
- list endpoints;
- nested resources;
- service-layer queries;
- background tasks;
- exports;
- deleted-user behavior;
- service/admin boundaries where applicable.

Any cross-user leak is a **P0 release blocker**.

---

# 11. Authentication and Security Regression

Run the existing security suite and verify the implemented equivalents of:

```text
JWT/token validation
refresh rotation/revocation
Argon2
MFA boundary if enabled
CSRF where applicable
SSRF controls
centralized egress
rate limiting
SQL injection resistance
RLS
encryption
key management
crypto-shred
security headers
CORS/trusted hosts
secret handling
safe error responses
```

For every critical defect:

```text
reproduce
→ failing regression test
→ minimal fix
→ targeted test
→ affected regression suite
```

Do not redesign working controls without evidence.

---

# 12. Verified Identifier Workflow

Verify:

```text
create identifier
→ unverified
→ challenge
→ successful verification
→ verified
→ eligible for protected discovery
```

Negative paths:

```text
unverified identifier → protected scan blocked
expired challenge → rejected
invalid challenge → rejected
cross-user challenge access → rejected
replay → rejected or safely idempotent per canonical contract
```

Document the canonical verification service and state transitions.

---

# 13. Consent and Zero-Egress Verification

Verify actual zero egress:

```text
Deep Amber without consent
→ blocked
→ zero connector execution
→ zero outbound request

Constrained-Dark disabled
→ zero constrained-dark execution

Constrained-Dark enabled with invalid policy/allowlist
→ fail closed
```

Do not verify this only by checking an API error. Use controlled mocks, instrumentation, or the canonical egress audit mechanism.

---

# 14. Centralized Egress Audit

Search production backend/worker code for direct use of:

```text
requests
httpx
aiohttp
urllib
Playwright navigation
network-capable subprocesses
raw sockets
```

Classify:

```text
approved centralized egress
approved specialized controlled path
test-only
local-only
violation
```

Document the outbound-request map.

---

# 15. Connector Inventory

Create a table:

| Connector | Layer | Purpose | Input | Consent | Egress path | Rate limit | Cache | Failure isolation | Status |
|---|---|---|---|---|---|---|---|---|---|

Verify:

- registration;
- canonical connector ID;
- configuration;
- timeout/retry;
- rate-limit handling;
- cache;
- provenance;
- normalization;
- feature flags;
- failure isolation;
- optional dependency behavior.

One connector failure must not corrupt durable scan state.

---

# 16. Scan State Machine

Document actual canonical states and legal transitions.

Verify:

- legal transitions;
- illegal transition rejection;
- idempotency;
- duplicate task delivery;
- stale scan reconciliation;
- partial connector failure;
- cancellation;
- worker restart;
- API restart;
- SSE/progress behavior.

PostgreSQL remains authoritative for durable scan state.

---

# 17. Worker and Scheduler Verification

Inventory:

```text
Celery apps
queues
task names
scheduled tasks
reconciliation jobs
retention jobs
remediation verification jobs
alert jobs
optional ML tasks
```

Verify:

- task registration;
- queue routing;
- retries;
- idempotency;
- graceful shutdown;
- duplicate delivery;
- stale recovery;
- scheduled registration.

Document in `docs/baseline/runtime-components.md`.

---

# 18. Evidence and Finding Pipeline

Verify:

```text
connector result
→ source observation
→ normalized evidence
→ finding
→ provenance
→ score eligibility
```

Confirm:

- attribution;
- confidence;
- exposure layer;
- historical/current semantics;
- raw/summary TTL;
- purge behavior;
- no unnecessary raw breach data;
- no secrets in evidence;
- deterministic normalization.

Document current deduplication behavior. Sprint 17 will later add evidence-independence and canonical-fact correlation.

---

# 19. Identity Graph Baseline

Document:

```text
node types
edge types
ownership model
confidence fields
provenance fields
status fields
graph construction service
graph query API
frontend representation
```

Verify:

- user isolation;
- deterministic graph construction;
- no unsupported identity claims;
- score integration;
- deletion behavior.

Document safe future extension points for:

```text
claims_profile
links_to
same_username_candidate
avatar_similar_to
confirmed_same_identity
rejected_same_identity
alias_of
```

Do not add them in Sprint 14 unless already canonical.

---

# 20. PDSS Baseline Freeze

Document:

```text
model/version
input contract
Confirmed track
Possible track
component calculations
confidence handling
historical/current handling
score persistence/history
explanation generation
what-if behavior
```

Verify:

```text
same approved input snapshot
+ same model version
→ same deterministic score/components
```

Residual ML must not alter the authoritative deterministic PDSS.

Create stable baseline fixtures for future regression.

---

# 21. Recommendations and Remediation

Verify:

```text
findings/score
→ recommendations
→ priority/dependencies
→ user-directed action
→ remediation state
→ verification
→ re-score
```

Check:

- recommendation determinism;
- ownership;
- authorization;
- dry-run/manual boundaries;
- retries/idempotency;
- verification;
- audit trail.

Sprint 25 later adds formal remediation-effectiveness analytics. Sprint 14 freezes the current baseline.

---

# 22. Privacy Export and Deletion

## Export

Verify intended user-owned durable data is included and excludes:

```text
secrets
server-only keys
other users' data
unnecessary internal credentials
```

## Deletion

Verify:

```text
authorized deletion
→ deletion workflow
→ crypto-shred where designed
→ user data inaccessible
→ caches invalidated
→ cleanup remains compatible
```

A failure of the frozen deletion design is a release blocker.

---

# 23. Groq Narrative Boundary

Verify:

```text
approved structured facts
→ grounded narrative
```

Failure paths:

```text
missing API key
timeout
429
5xx
invalid response
provider disabled
```

must produce deterministic grounded fallback.

The core product must work without Groq.

Never log API keys or unnecessary sensitive prompt/response content.

---

# 24. Residual ML Boundary

Verify default behavior:

```text
FEATURE_RESIDUAL_ML=false
→ application starts
→ no model required
→ PDSS works normally
```

If an approved artifact exists, verify:

```text
checksum
schema compatibility
safe loading
timeout
abstention
bounded output
cross-user isolation
```

Do not enable residual ML merely because an artifact exists.

---

# 25. Frontend Verification

Run the repository's actual package-manager commands, including the production build.

Verify critical routes:

```text
authentication
identifiers
verification
scan creation/progress
findings
PDSS
recommendations
identity graph
remediation
privacy center
audit/egress transparency
```

Check:

- production build;
- type checks;
- API compatibility;
- loading/empty/error states;
- authorization handling;
- feature flags;
- no secrets in frontend bundle.

Do not redesign the frontend.

---

# 26. Health, Readiness and Observability

Verify canonical liveness/readiness endpoints.

Required dependencies should affect readiness; optional systems should degrade according to Sprint 13 policy.

Verify correlation across:

```text
HTTP
→ scan
→ task
→ connector
→ egress
→ finding
→ score
→ remediation
```

Never use personal or high-cardinality values as metric labels:

```text
user ID
email
username
profile URL
raw URL
prompt
response
evidence body
```

---

# 27. Backup, Restore and Disaster Recovery

Review Sprint 13 operational evidence.

Confirm:

```text
backup procedure exists
restore procedure exists
restore is tested or accurately marked unverified
Redis is not authoritative backup
secrets are not embedded in backups
optional ML artifacts have a recovery policy
```

A runbook alone is not proof of a successful restore.

---

# 28. Release and Rollback

Review:

```text
release runbook
rollback runbook
incident response
SLOs
performance baseline
```

Verify coverage of:

```text
CI
backup
migration head
immutable build
deployment
readiness
smoke test
monitoring
rollback/forward-fix
feature-flag disable
```

---

# 29. Test Gap Register

Create `docs/audit/test-gap-register.md`.

| Area | Existing tests | Critical path covered | Missing case | Severity | Action |
|---|---|---|---|---|---|

Severity:

```text
P0 = security/privacy/isolation/release blocker
P1 = critical workflow/reliability gap
P2 = important non-blocking gap
P3 = quality/documentation improvement
```

Sprint 14 exit requires `P0 = 0`.

P1 must be fixed or explicitly accepted through a documented engineering decision.

---

# 30. Required Logical Test Groups

Use the repository's real tests:

```text
unit
integration
security
migration
contract/OpenAPI
worker/task
connector
privacy
frontend
release smoke
```

Do not create empty test groups merely to satisfy this guide.

---

# 31. End-to-End Baseline Journey

Verify one controlled journey:

```text
register/login
→ create identifier
→ verification required
→ verify ownership
→ Surface scan
→ connector execution
→ findings/provenance
→ deterministic PDSS
→ explanation
→ recommendations
→ remediation
→ re-verification
→ re-score
→ privacy export
```

Negative journeys:

```text
unverified identifier → protected scan blocked
Deep without consent → blocked with zero egress
Constrained-Dark disabled → zero connector execution
Groq unavailable → deterministic fallback
Residual ML disabled → core product unchanged
cross-user access → denied
```

---

# 32. Duplicate and Dead-Code Analysis

Search for:

```text
duplicate settings
duplicate enums
duplicate DTOs
duplicate repositories
duplicate score models
duplicate connector registries
unused migration branches
orphaned routes
unregistered tasks
frontend clients for missing endpoints
deprecated feature flags
```

Classify:

```text
canonical
adapter
deprecated
dead
uncertain
```

Do not remove `uncertain` code without dependency/runtime evidence.

---

# 33. Minimal Fix Policy

For a discovered defect:

```text
reproduce
→ classify severity
→ identify canonical layer
→ add/update regression test
→ smallest safe fix
→ targeted tests
→ affected integration tests
→ update audit
```

Avoid opportunistic refactoring.

---

# 34. Baseline Manifest

Create `docs/baseline/sprint0-13-baseline-manifest.md`.

Include:

```text
repository commit
date
migration head
backend runtime version
frontend runtime version
database version
Redis version
worker framework version
production-safe feature flags
disabled experimental flags
PDSS model version
residual ML status/version if applicable
canonical connector IDs
critical test summary
known accepted limitations
```

Never include secrets.

---

# 35. Feature-Flag Inventory

Create `docs/baseline/feature-flags.md`.

For every flag record:

```text
name
default
production recommendation
owner/domain
dependency
failure behavior
security/privacy impact
```

Cover at minimum:

```text
Deep/Amber
Constrained-Dark
Groq narrative
Residual ML
experimental connectors
```

---

# 36. Sprint 15 Extension Points

Create `docs/audit/extension-points-for-sprint15.md`.

Document:

```text
canonical User model
canonical Identifier model
verification service
consent service
identity graph service
finding/evidence contracts
RLS pattern
encryption pattern
audit event pattern
API router conventions
frontend state/API conventions
migration naming convention
test fixture conventions
```

Answer:

```text
Where should Identity Anchor live?
Should it extend or reference verified identifiers?
Where should user-confirmed aliases live?
How should deletion cascade?
How should graph edges reference anchor facts?
Which contracts must Sprint 15 reuse?
```

Do not implement Sprint 15 here.

---

# 37. Suggested Execution Order

## Phase A — Freeze starting state

```text
record Git state
record migration state
record environment shape
record feature flags
run baseline startup
```

## Phase B — Inventory

```text
repository
→ contracts
→ database
→ APIs
→ workers
→ connectors
→ frontend
→ tests
```

## Phase C — Verify critical invariants

```text
auth
→ verification
→ consent
→ zero egress
→ user isolation
→ privacy deletion
```

## Phase D — Verify product journey

```text
scan
→ evidence
→ finding
→ PDSS
→ recommendation
→ remediation
→ re-score
```

## Phase E — Verify optional boundaries

```text
Groq fallback
Residual ML disabled
Amber disabled/consent denied
```

## Phase F — Close genuine gaps

```text
reproduce
→ test
→ minimal fix
→ regression
```

## Phase G — Freeze continuation baseline

```text
baseline manifest
canonical contracts
Sprint 15 extension points
final verification report
```

---

# 38. CI Expectations

Preserve or strengthen the release gate:

```text
backend lint/static checks
backend unit tests
backend integration tests
security tests
migration tests
contract/OpenAPI drift tests
worker/task tests
frontend typecheck/tests
frontend production build
release smoke
```

Do not weaken existing gates to make Sprint 14 pass.

---

# 39. Failure Classification

## P0 — Blocker

Examples:

```text
cross-user leak
verification bypass
consent bypass with egress
RLS failure
secret exposure
broken deletion/crypto-shred
migration cannot reach head
core application cannot start
```

## P1 — Critical

Examples:

```text
major workflow broken
worker task not registered
PDSS nondeterminism
connector corrupts scan state
release rollback impossible
```

## P2 — Important

```text
missing edge-case test
incomplete documentation
non-critical duplicate abstraction
observability gap
```

## P3 — Improvement

```text
cleanup
naming consistency
test convenience
documentation polish
```

---

# 40. Definition of Done

## Repository

- [ ] Actual repository inventory completed.
- [ ] Canonical contracts documented.
- [ ] Duplicate abstractions classified.
- [ ] No unreviewed P0/P1 architecture conflict remains.

## Database

- [ ] Expected migration head verified.
- [ ] Upgrade to head succeeds.
- [ ] Fresh-install migration path succeeds.
- [ ] Supported upgrade path succeeds.
- [ ] RLS and ownership verified.

## Security and privacy

- [ ] Authentication regression passes.
- [ ] Verified-identifier enforcement passes.
- [ ] Consent enforcement passes.
- [ ] Zero-egress denial passes.
- [ ] Cross-user isolation passes.
- [ ] Privacy export verified.
- [ ] Deletion/crypto-shred verified.
- [ ] No secret leakage found.

## Product workflow

- [ ] Surface scan verified.
- [ ] Evidence/finding normalization verified.
- [ ] Deterministic PDSS verified.
- [ ] Confirmed/Possible tracks verified.
- [ ] Recommendations verified.
- [ ] Remediation/re-verification verified.
- [ ] Re-score verified.

## Optional boundaries

- [ ] Groq failure falls back deterministically.
- [ ] Residual ML disabled leaves core product unchanged.
- [ ] Amber/Constrained-Dark denial fails safely.

## Operations

- [ ] Health/readiness verified.
- [ ] Worker/task registration verified.
- [ ] Observability verified.
- [ ] Backup/restore evidence reviewed.
- [ ] Release/rollback runbooks reviewed.

## Frontend

- [ ] Production build passes.
- [ ] Critical routes verified.
- [ ] API contracts align.
- [ ] No secret-bearing frontend configuration found.

## Documentation

- [ ] Baseline audit completed.
- [ ] Feature matrix completed.
- [ ] Test gap register completed.
- [ ] Migration status completed.
- [ ] Baseline manifest completed.
- [ ] Sprint 15 extension points documented.
- [ ] Final Sprint 14 report completed.

## Blockers

```text
P0 = 0
P1 = 0 or explicitly accepted by documented engineering decision
```

---

# 41. Final Verification Report

Create `docs/audit/sprint14-final-verification.md`.

Recommended structure:

```text
1. Executive summary
2. Repository baseline
3. Migration status
4. Test summary
5. Security/privacy verification
6. Product workflow verification
7. Optional feature boundaries
8. Operational verification
9. Gaps found
10. Fixes applied
11. Accepted limitations
12. Canonical contracts
13. Sprint 15 extension readiness
14. GO / CONDITIONAL GO / NO-GO
```

---

# 42. GO / NO-GO Gate for Sprint 15

## GO

Proceed when:

```text
Sprint 0–13 is reproducibly verified
migration state is healthy
critical security/privacy invariants pass
core end-to-end workflow passes
canonical identity/identifier/graph extension points are documented
```

## CONDITIONAL GO

Only for documented non-blocking P2/P3 issues.

## NO-GO

Do not begin Sprint 15 with:

```text
cross-user isolation uncertainty
verification bypass
consent/egress uncertainty
migration instability
PDSS baseline uncertainty
privacy deletion failure
unresolved P0
unaccepted P1
```

---

# 43. Handoff to Sprint 15

Sprint 15 will introduce:

```text
Verified Identity Anchor
user-confirmed aliases
confirmed profile references
identity evidence foundation
identity assessment persistence foundation
```

It must consume Sprint 14 outputs:

```text
canonical User model
canonical Identifier model
verification service
consent service
identity graph extension points
RLS pattern
encryption pattern
audit pattern
migration baseline
API conventions
frontend conventions
```

Sprint 15 must not rediscover or duplicate these from scratch.

---

# 44. Final Sprint 14 Principle

The objective is not to produce more code.

The objective is to establish:

```text
a known-good
measured
documented
reproducible
secure
privacy-preserving
extension-ready
Sprint 0–13 baseline
```

Only then should DigiZafe expand into:

```text
Verified Identity Anchor
→ Maigret Candidate Discovery
→ Evidence Integrity
→ Identity Resolution
→ Identity Clusters
→ Profile Exposure Intelligence
→ PDSS Integration v2
```

---

**End of Sprint 14 Implementation Guide**
