# DigiZafe --- Complete System Validation, Test, Error-Checking & Fix Verification Guide

**Document version:** 1.0\
**Applies to:** Sprint 0 through Sprint 13\
**Purpose:** Provide one authoritative end-to-end quality gate for
detecting integration errors, security regressions, migration problems,
contract drift, privacy failures, operational defects, and incomplete
fixes before a release candidate is approved.

> This document is a validation and verification gate. It does not
> replace sprint-specific tests.
>
> A release is not approved merely because the application starts or
> individual sprint tests pass. The complete Sprint 0--13 system must
> pass the applicable gates in this document.

------------------------------------------------------------------------

# 1. Validation Objective

The complete DigiZafe system must prove that it can safely execute the
intended lifecycle:

``` text
Register / Login
→ Verify identity ownership
→ Grant required consent
→ Discover through approved connectors
→ Preserve provenance
→ Normalize observations/findings
→ Compute deterministic PDSS
→ Explain risk
→ Prioritize recommendations
→ Perform user-directed remediation
→ Re-verify
→ Re-score
→ Export / delete / audit
```

Optional paths must remain isolated:

``` text
Groq unavailable
→ deterministic grounded narrative

Residual ML disabled / unavailable / abstained
→ deterministic PDSS and core product continue

Constrained-Dark disabled
→ zero constrained-dark connector execution
```

------------------------------------------------------------------------

# 2. Release Severity Classification

Every discovered issue must be classified.

## P0 --- Release Blocker

Examples:

-   authentication bypass;
-   cross-user data access;
-   unverified identifier can trigger discovery;
-   consent bypass;
-   SSRF or DNS-rebinding path;
-   secret exposure;
-   destructive migration/data loss;
-   deterministic PDSS replaced or silently altered;
-   raw sensitive evidence retained contrary to policy;
-   arbitrary model deserialization;
-   remediation executes without required user authorization.

**Action:** stop release immediately.

## P1 --- High Priority

Examples:

-   major workflow broken;
-   migration fails on fresh install or supported upgrade;
-   scan state corruption;
-   duplicate durable side effects;
-   privacy export/delete incorrect;
-   Groq failure breaks explainability;
-   optional ML failure breaks scoring;
-   incorrect RLS policy;
-   production unsafe configuration accepted.

**Action:** fix before release.

## P2 --- Medium Priority

Examples:

-   non-critical UI inconsistency;
-   degraded performance;
-   incomplete operational metrics;
-   recoverable connector error handling problem.

**Action:** fix before release where practical or document with owner
and deadline.

## P3 --- Low Priority

Examples:

-   minor copy;
-   non-blocking developer-experience issue;
-   cosmetic inconsistency.

**Action:** backlog with documentation.

------------------------------------------------------------------------

# 3. Required Test Environments

Validate in at least:

``` text
unit/in-process test environment
integration environment with PostgreSQL + Redis
fresh-install environment
supported-upgrade environment
production-like release-candidate environment
```

Use synthetic/test identities and controlled fixtures. Never use real
secrets or production user data in automated tests.

------------------------------------------------------------------------

# 4. Gate A --- Repository and Static Integrity

## Required checks

-   [ ] Repository contains no unresolved merge-conflict markers.
-   [ ] No placeholder `pass`, `TODO`, `FIXME`, or fake conditional
    remains in critical production paths without an approved issue.
-   [ ] No duplicate canonical exposure-layer enum exists.
-   [ ] Canonical contract inventory matches code.
-   [ ] No direct HTTP client bypasses approved egress policy for
    user-influenced external requests.
-   [ ] No browser token persistence remains.
-   [ ] No Groq API key is referenced in frontend code.
-   [ ] No user-controlled residual ML model path exists.
-   [ ] No secrets are committed.
-   [ ] No obsolete Sprint-era duplicate modules remain active.

Suggested searches:

``` bash
git grep -n "<<<<<<<\|=======\|>>>>>>>"
git grep -n "TODO\|FIXME"
git grep -n "localStorage\|sessionStorage" -- frontend
git grep -n "GROQ_API_KEY" -- frontend
git grep -n "httpx.AsyncClient\|requests\." -- backend
git grep -n "ConnectorLayer\|ExposureLayer"
```

Review matches manually; some legitimate uses may exist.

------------------------------------------------------------------------

# 5. Gate B --- Python Quality

Run the repository's configured tools. If present:

``` bash
ruff check backend ml
black --check backend ml
mypy backend
```

Requirements:

-   [ ] no syntax errors;
-   [ ] no unresolved imports;
-   [ ] no circular import introduced by contract consolidation;
-   [ ] no critical type errors in security/scoring/ML paths;
-   [ ] no dead production module required only by stale sprint code.

Run:

``` bash
python -m compileall backend ml
```

------------------------------------------------------------------------

# 6. Gate C --- Frontend Quality

Run the configured frontend commands, typically:

``` bash
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Requirements:

-   [ ] TypeScript contracts compile;
-   [ ] production build succeeds;
-   [ ] no access/refresh token storage in browser storage;
-   [ ] no server secret appears in generated bundle;
-   [ ] residual ML UI does not replace PDSS;
-   [ ] Amber labels/copy do not imply unrestricted dark-web access;
-   [ ] all API status unions are handled.

------------------------------------------------------------------------

# 7. Gate D --- Dependency and Secret Scanning

Use the repository-approved tools.

Check:

``` text
Python dependencies
Node dependencies
container base images
CI actions
committed secrets
```

Requirements:

-   [ ] no known reachable critical vulnerability remains unresolved;
-   [ ] no Groq key, JWT secret, database password, token, or private
    key is committed;
-   [ ] production images do not contain `.env` secrets;
-   [ ] dependency findings are triaged and documented.

------------------------------------------------------------------------

# 8. Gate E --- Alembic and Database Integrity

## Fresh install

``` bash
alembic heads
alembic upgrade head
```

Verify:

-   [ ] expected single head;
-   [ ] all tables created;
-   [ ] indexes created;
-   [ ] foreign keys valid;
-   [ ] RLS policies installed;
-   [ ] verified-only database protections installed;
-   [ ] consent/audit tables valid;
-   [ ] score/model-version fields valid;
-   [ ] residual ML tables, if implemented, migrate cleanly.

## Supported upgrade

Start from the supported historical baseline and upgrade through every
migration.

Verify:

-   [ ] no broken `down_revision`;
-   [ ] no duplicate enum creation;
-   [ ] no destructive silent data conversion;
-   [ ] historical PDSS model versions remain preserved;
-   [ ] old records remain readable.

## Migration failure test

Simulate a migration failure in an isolated environment.

Verify:

-   [ ] release procedure stops;
-   [ ] application is not marked ready with incompatible schema;
-   [ ] recovery/forward-fix procedure is documented.

------------------------------------------------------------------------

# 9. Gate F --- Authentication and Session Security

Test:

``` text
registration
login success/failure
password hashing
access token expiry
refresh rotation
refresh reuse detection
logout/revocation
MFA enrollment/verification where enabled
```

Required assertions:

-   [ ] passwords use approved Argon2id settings;
-   [ ] refresh tokens are stored hashed;
-   [ ] reuse detection revokes the intended token family;
-   [ ] concurrent refresh attempts cannot both succeed incorrectly;
-   [ ] revoked tokens cannot be reused;
-   [ ] MFA secrets are protected;
-   [ ] tokens never appear in logs;
-   [ ] frontend stores auth tokens in memory only.

Negative tests:

``` text
invalid password
expired access token
expired refresh token
reused refresh token
revoked refresh token
invalid MFA code
cross-user session access
```

------------------------------------------------------------------------

# 10. Gate G --- Identifier Canonicalization and Verification

Test all supported identifier types.

Required cases:

``` text
Unicode normalization
IDNA domains
case behavior
maximum length
invalid syntax
provider-specific aliases
display value preservation
blind-index consistency
```

Verification tests:

-   [ ] unverified identifier cannot scan;
-   [ ] expired challenge fails;
-   [ ] wrong challenge fails;
-   [ ] verification cannot be transferred to another user;
-   [ ] verification events are auditable;
-   [ ] provider-specific canonicalization does not destroy display
    semantics.

Strong invariant:

``` text
unverified identifier
→ scan creation denied
→ connector calls = 0
→ egress calls = 0
```

------------------------------------------------------------------------

# 11. Gate H --- Consent

Test:

``` text
grant
read
revoke
expired/invalid consent where supported
purpose mismatch
layer mismatch
destination mismatch
```

Amber invariant:

``` text
missing or revoked required consent
→ connector calls = 0
→ outbound requests = 0
```

Verify a generic historical layer grant does not silently authorize a
newly configured constrained-dark destination if destination-aware
authorization is required.

------------------------------------------------------------------------

# 12. Gate I --- EgressFetcher Security

This is a P0 security gate.

Test blocking of:

``` text
localhost
127.0.0.1
private IPv4
IPv6 loopback
IPv6 unique-local
link-local
metadata destinations
multicast
unspecified addresses
unsupported schemes
hostname resolving to forbidden IP
mixed public/private DNS answers
public URL redirecting to private destination
unapproved allowlist host
oversized chunked response
```

DNS pinning tests must verify:

-   [ ] all selected destination IPs are validated;
-   [ ] connection uses an approved/pinned destination strategy;
-   [ ] original hostname is preserved correctly for TLS SNI/certificate
    verification;
-   [ ] TLS verification is never disabled;
-   [ ] redirect targets are not trusted automatically;
-   [ ] response size is enforced while streaming.

Any SSRF/DNS-rebinding bypass is P0.

------------------------------------------------------------------------

# 13. Gate J --- Connector SDK

For each connector test:

``` text
capability metadata
identifier support
legality tier
exposure layer
consent requirement
rate limiting
cache behavior
negative cache
timeouts
normalization
attribution
failure isolation
```

Required invariants:

-   [ ] connectors do not write directly to database unless architecture
    explicitly allows it;
-   [ ] user-influenced HTTP goes through EgressFetcher;
-   [ ] disabled connector cannot execute;
-   [ ] unsupported identifier type cannot dispatch;
-   [ ] attribution is retained.

------------------------------------------------------------------------

# 14. Gate K --- Surface Discovery

Test configured Surface connectors using controlled fixtures/mocks.

Verify:

-   [ ] verified-only gate;
-   [ ] correct connector selection;
-   [ ] partial failure handling;
-   [ ] cache and rate-limit behavior;
-   [ ] normalized observations;
-   [ ] durable provenance;
-   [ ] no raw dump retention.

------------------------------------------------------------------------

# 15. Gate L --- Deep and Constrained-Dark Amber Discovery

## Deep

Verify:

-   [ ] explicit required consent;
-   [ ] verified identifier;
-   [ ] Common Crawl collection selection deterministic;
-   [ ] collection/version retained in provenance;
-   [ ] Wayback availability alone is not confirmed sensitive exposure;
-   [ ] metadata-first behavior;
-   [ ] no archived page-body retention.

## Constrained-Dark

Verify:

``` text
feature disabled → 0 outbound calls
endpoint blank → 0 outbound calls
host not allowlisted → 0 outbound calls
consent missing/revoked → 0 outbound calls
identifier unverified → 0 outbound calls
```

Verify no Tor, `.onion`, marketplace, credentialed, CAPTCHA-bypass, or
raw-dump behavior exists.

------------------------------------------------------------------------

# 16. Gate M --- Scan State Machine

Test every allowed and forbidden transition.

Verify:

-   [ ] no generated fake enum expression remains;
-   [ ] terminal states cannot return to running;
-   [ ] cancellation semantics are explicit;
-   [ ] timeout and cancellation are distinct;
-   [ ] reconciliation is idempotent;
-   [ ] duplicate worker delivery does not duplicate durable results;
-   [ ] stale running jobs recover according to policy;
-   [ ] SSE emits correct terminal state.

Test:

``` text
all connectors succeed
one connector fails
all connectors fail
worker crashes
task retries
scan cancelled
scan times out
reconciliation runs twice
```

------------------------------------------------------------------------

# 17. Gate N --- Evidence Lifecycle

Verify three-layer evidence behavior.

Test:

-   [ ] raw evidence expires at configured TTL;
-   [ ] summary evidence expires at configured TTL;
-   [ ] durable redacted finding/provenance remains according to policy;
-   [ ] purge is idempotent;
-   [ ] retries do not resurrect expired raw evidence;
-   [ ] raw breach dumps are never stored;
-   [ ] logs do not contain purged sensitive content.

------------------------------------------------------------------------

# 18. Gate O --- Identity Graph and Linkage

Test:

``` text
strong match
weak match
collision
ambiguous identity
confirmed linkage
possible linkage
```

Verify:

-   [ ] ambiguous username occurrence is not identity proof;
-   [ ] candidate/possible evidence does not become confirmed without
    linkage evidence;
-   [ ] cross-user graph data is isolated;
-   [ ] deterministic linkage inputs produce deterministic output where
    expected.

------------------------------------------------------------------------

# 19. Gate P --- PDSS

This is a release-critical deterministic gate.

Test golden vectors for:

``` text
sensitivity
discoverability
linkability
impact
temporal factors
confidence/evidence quality
Confirmed track
Possible track
```

Required assertions:

-   [ ] same input + same model version = same score;
-   [ ] historical model versions preserved;
-   [ ] `pdss-v1.1.0` or current corrected version uses layer-neutral
    semantics;
-   [ ] identical findings differing only by layer do not change
    severity solely due to layer;
-   [ ] score explanations reconcile with score components;
-   [ ] counterfactual simulation is deterministic;
-   [ ] score history is append/version aware rather than silently
    overwritten.

------------------------------------------------------------------------

# 20. Gate Q --- Recommendations

Test:

-   [ ] generation is idempotent;
-   [ ] dependency DAG valid;
-   [ ] no circular dependency;
-   [ ] recommendation ordering deterministic where expected;
-   [ ] dismissed/done lifecycle valid;
-   [ ] marginal remediation value uses approved scoring semantics;
-   [ ] duplicate rescoring does not create uncontrolled duplicates.

------------------------------------------------------------------------

# 21. Gate R --- Remediation

Test Green automation and manual paths.

Required cases:

``` text
dry run
submission
CAPTCHA/manual intervention
email confirmation required
site changed/stale playbook
verification pending
verified removed
failure
retry
```

Required assertions:

-   [ ] no action executes without required user direction;
-   [ ] CAPTCHA bypass is not automated outside approved policy;
-   [ ] ambiguous success is not marked `verified_removed`;
-   [ ] verification loop is authoritative;
-   [ ] duplicate task delivery does not duplicate destructive action;
-   [ ] Playwright remains isolated from core API process.

------------------------------------------------------------------------

# 22. Gate S --- Privacy, Rights, Audit, and Deletion

Test:

``` text
machine-readable export
consent history
egress visibility
audit visibility
crypto-shred
purge/delete
```

Verify:

-   [ ] export excludes secrets;
-   [ ] export is scoped to requesting user;
-   [ ] audit records do not expose forbidden sensitive content;
-   [ ] deletion does not affect another user;
-   [ ] cryptographic deletion behavior matches design;
-   [ ] retention and deletion jobs are idempotent.

------------------------------------------------------------------------

# 23. Gate T --- Groq Narrative

Groq is narrative-only.

Test:

``` text
configured success
missing key
timeout
429
5xx
invalid response
malformed response
provider unavailable
```

Required behavior:

``` text
Groq failure
→ deterministic grounded fallback
→ no core workflow failure
```

Verify:

-   [ ] Groq API key backend-only;
-   [ ] key absent from frontend bundle/API/logs;
-   [ ] no raw evidence dumps sent;
-   [ ] no passwords/tokens/MFA/verification secrets sent;
-   [ ] minimum necessary grounded data used;
-   [ ] narrative cannot invent unsupported findings;
-   [ ] residual ML service never calls Groq.

------------------------------------------------------------------------

# 24. Gate U --- Residual ML

If `FEATURE_RESIDUAL_ML=false`:

-   [ ] model is not required;
-   [ ] model is not loaded;
-   [ ] core behavior unchanged.

If enabled in an approved test environment:

Test:

``` text
trusted model
missing model
corrupt model
checksum mismatch
schema mismatch
feature order mismatch
invalid feature value
inference failure
abstention
bounded output
```

Required assertions:

-   [ ] checksum verified before deserialization;
-   [ ] no user-controlled model path;
-   [ ] no uploaded arbitrary joblib/pickle accepted;
-   [ ] deterministic PDSS never overwritten;
-   [ ] residual result stored/versioned reproducibly;
-   [ ] read endpoints do not silently recompute changing results;
-   [ ] confidence remains null unless defensibly implemented;
-   [ ] layer alone cannot force residual direction;
-   [ ] user A cannot evaluate user B's score;
-   [ ] Groq is never used for residual scoring.

Synthetic-data tests:

-   [ ] fixed seed reproduces dataset;
-   [ ] generator/version manifest exists;
-   [ ] scenario-family split reduces leakage;
-   [ ] evaluation report states synthetic performance is not real-world
    validation.

------------------------------------------------------------------------

# 25. Gate V --- API Contract and OpenAPI Drift

Test:

-   [ ] API version remains `/api/v1`;
-   [ ] typed DTOs used instead of arbitrary dictionaries for stable
    public contracts;
-   [ ] enums serialize consistently;
-   [ ] frontend types match backend contract;
-   [ ] residual ML public DTO is typed;
-   [ ] error schema stable;
-   [ ] pagination contracts stable.

Generate/compare OpenAPI where supported and fail CI on unintended
contract drift.

------------------------------------------------------------------------

# 26. Gate W --- RLS and Cross-User Isolation

Create at least two test users.

Attempt cross-user access to:

``` text
identifiers
verification records
scans
connector runs
findings
evidence metadata
scores
recommendations
remediation jobs
consent
audit
privacy exports
residual ML evaluations
```

Every unauthorized cross-user read/write must fail.

This is a P0 gate.

------------------------------------------------------------------------

# 27. Gate X --- Logging and Secret Leakage

Capture logs during:

``` text
login
refresh
verification
scan
connector egress
Groq request
ML load failure
remediation
privacy export
```

Search for:

``` text
passwords
JWTs
refresh tokens
authorization headers
MFA secrets
verification tokens
Groq API key
database password
raw evidence
```

Any secret leakage is P0/P1 depending on exposure.

------------------------------------------------------------------------

# 28. Gate Y --- Health, Readiness, and Dependency Failure

Test:

``` text
healthy system
PostgreSQL unavailable
Redis broker unavailable
Redis cache unavailable
Groq unavailable
optional ML unavailable
external connector unavailable
```

Verify:

-   [ ] liveness answers process health;
-   [ ] readiness fails for required dependencies;
-   [ ] optional Groq/ML outages do not make core API unready;
-   [ ] health endpoints expose no secrets.

------------------------------------------------------------------------

# 29. Gate Z --- Worker Reliability and Idempotency

Test duplicate delivery and retries for:

``` text
connector task
scan reconciliation
score computation
recommendation generation
remediation task
residual evaluation
retention purge
```

Verify no duplicate durable side effect beyond explicitly
versioned/history records.

------------------------------------------------------------------------

# 30. Performance and Load Validation

Use controlled local/mock dependencies.

Measure:

``` text
login
identifier list
scan creation
scan status/SSE
score retrieval
recommendations
privacy endpoints
```

Check:

-   [ ] no critical N+1 query;
-   [ ] list endpoints bounded/paginated;
-   [ ] no unbounded response body;
-   [ ] queue age observable;
-   [ ] load does not bypass rate limits;
-   [ ] external public services are not load-tested without permission.

Record results in:

``` text
docs/performance/sprint13-baseline.md
```

------------------------------------------------------------------------

# 31. Backup and Restore Test

In an isolated environment:

``` text
seed representative data
→ backup PostgreSQL
→ destroy database
→ restore
→ migrate if required
→ run integrity checks
```

Verify:

-   [ ] users isolated;
-   [ ] verified identifiers preserved;
-   [ ] findings/provenance preserved;
-   [ ] score/model versions preserved;
-   [ ] audit history preserved;
-   [ ] optional ML records preserved if in scope;
-   [ ] Redis loss does not destroy authoritative data.

------------------------------------------------------------------------

# 32. Graceful Shutdown and Recovery

Terminate API/workers during:

``` text
connector execution
scan reconciliation
score computation
remediation
ML evaluation
```

Verify:

-   [ ] unfinished work not marked successful;
-   [ ] durable state remains valid;
-   [ ] reconciliation recovers stale operations;
-   [ ] retry does not duplicate side effects.

------------------------------------------------------------------------

# 33. Production Configuration Negative Tests

Verify startup rejects:

``` text
production + DEBUG=true
unsafe wildcard credentialed CORS
invalid signing configuration
unsafe constrained-dark enablement
invalid Amber allowlist
invalid ML artifact when policy requires enabled model
missing required DB/Redis configuration
```

Verify optional provider absence does not block startup when optional.

------------------------------------------------------------------------

# 34. Container Validation

Check:

-   [ ] API image uses production server;
-   [ ] non-root where practical;
-   [ ] no secrets baked into layers;
-   [ ] Playwright isolated from API image/process;
-   [ ] health checks valid;
-   [ ] images build reproducibly;
-   [ ] writable paths intentionally scoped.

------------------------------------------------------------------------

# 35. Release Candidate End-to-End Journey

Run the complete user journey:

``` text
1. Register
2. Login
3. Complete MFA path if enabled
4. Add identifier
5. Attempt scan before verification → denied
6. Verify identifier ownership
7. Run Surface scan
8. Inspect findings and provenance
9. Compute/read deterministic PDSS
10. Inspect explanation
11. Generate recommendations
12. Execute approved remediation path
13. Re-verify
14. Re-score
15. Inspect audit/egress history
16. Export privacy data
```

Amber checks:

``` text
Deep without consent → denied with zero egress
Deep with consent → approved connectors only
Constrained-Dark disabled → zero execution
```

Optional checks:

``` text
Groq unavailable → deterministic narrative
Residual ML disabled → core unchanged
Residual ML enabled in approved test env → auxiliary only
```

------------------------------------------------------------------------

# 36. Failure Injection Matrix

Inject controlled failures:

  -----------------------------------------------------------------------
  Failure                             Expected result
  ----------------------------------- -----------------------------------
  PostgreSQL unavailable              readiness fails; no false success

  Redis broker unavailable            queued work unavailable/degraded;
                                      durable DB state safe

  Redis cache unavailable             cache degradation; authoritative
                                      data safe

  connector timeout                   isolated failure/retry policy

  connector 429                       bounded retry/rate-limit handling

  connector malformed response        normalization failure isolated

  Groq timeout/429/5xx                deterministic narrative fallback

  ML model missing                    unavailable/abstained; PDSS works

  ML checksum mismatch                no deserialization; unavailable

  worker killed                       reconciliation recovers

  browser refresh                     re-authentication under memory-only
                                      token policy

  constrained-dark endpoint blank     zero outbound requests

  consent revoked                     zero consent-gated outbound
                                      requests
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 37. Fix Verification Template

For every P0/P1 bug fixed, record:

``` text
Issue ID:
Severity:
Affected sprint/module:
Root cause:
Security/privacy impact:
Code fix:
Migration required:
Regression test added:
Negative test added:
Manual verification:
Reviewer:
Status:
```

A fix is not complete until a regression test exists where technically
feasible.

------------------------------------------------------------------------

# 38. Test Result Record

Create:

``` text
docs/validation/system-validation-report.md
```

Record:

``` text
commit SHA
build/image version
date
environment
database migration head
PDSS model version
residual ML model version if enabled
feature schema version
Groq narrative configuration state
test suite results
known failures
waivers
release decision
```

Do not include secrets.

------------------------------------------------------------------------

# 39. Release Decision Rules

## PASS

Allowed only when:

-   all P0 tests pass;
-   all P1 tests pass;
-   migrations pass;
-   security gates pass;
-   cross-user isolation passes;
-   verified-only/consent zero-egress tests pass;
-   full regression suite passes;
-   release journey passes;
-   backup/restore test passes.

## CONDITIONAL PASS

Only for documented P2/P3 issues with:

-   owner;
-   impact;
-   workaround;
-   deadline;
-   explicit approval.

## FAIL

Any open P0 or P1 issue means release fails.

------------------------------------------------------------------------

# 40. Recommended CI Test Groups

``` text
ci-fast
├── lint
├── typecheck
├── unit
└── contract

ci-integration
├── postgres
├── redis
├── migrations
├── api
└── workers

ci-security
├── auth
├── RLS
├── egress/SSRF
├── consent
├── secret leakage
└── model artifact safety

ci-regression
└── Sprint 0–13 complete regression suite

release-validation
├── fresh install
├── supported upgrade
├── production build
├── smoke test
├── backup/restore
└── release-candidate journey
```

------------------------------------------------------------------------

# 41. Suggested Test Commands

Adapt to actual repository tooling:

``` bash
# Backend
pytest backend/tests -q

# Security-focused
pytest backend/tests/security -q

# Regression
pytest backend/tests/regression -q

# ML
pytest backend/tests/ml -q

# Migrations
alembic heads
alembic upgrade head

# Python syntax
python -m compileall backend ml

# Frontend
cd frontend
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Do not invent commands in CI if the repository uses different scripts;
map this guide to the actual package configuration.

------------------------------------------------------------------------

# 42. Final Master Checklist

## Architecture

-   [ ] Canonical contracts are unique.
-   [ ] No cross-sprint duplicate authoritative enum/model exists.
-   [ ] Frozen architecture invariants preserved.

## Security

-   [ ] Authentication tests pass.
-   [ ] RLS/cross-user isolation passes.
-   [ ] Verified-only G1 tests pass.
-   [ ] Consent zero-egress tests pass.
-   [ ] SSRF/DNS-rebinding tests pass.
-   [ ] No secrets leak.
-   [ ] Model artifact loading is trusted/checksummed.

## Discovery

-   [ ] Surface works.
-   [ ] Deep is consented and metadata-first.
-   [ ] Constrained-Dark is disabled by default and fail-closed.
-   [ ] Connector failures are isolated.

## Evidence and scoring

-   [ ] TTL/purge works.
-   [ ] Provenance preserved.
-   [ ] PDSS deterministic.
-   [ ] Layer is not automatic severity.
-   [ ] Historical score versions preserved.

## Recommendations and remediation

-   [ ] Recommendation generation idempotent.
-   [ ] Remediation remains user-directed.
-   [ ] Verification loop is authoritative.
-   [ ] Duplicate jobs do not duplicate destructive actions.

## AI and ML

-   [ ] Groq is narrative-only.
-   [ ] Deterministic narrative fallback works.
-   [ ] Residual ML is optional/auxiliary.
-   [ ] ML cannot overwrite PDSS.
-   [ ] Synthetic ML results are not claimed as real-world validation.

## Operations

-   [ ] Structured logs and correlation IDs work.
-   [ ] Health/readiness correct.
-   [ ] Metrics safe and low-cardinality.
-   [ ] Backup/restore tested.
-   [ ] Graceful shutdown/recovery tested.
-   [ ] Release/rollback runbooks exist.

## Build and release

-   [ ] Fresh migration passes.
-   [ ] Supported upgrade passes.
-   [ ] Backend tests pass.
-   [ ] Frontend build/tests pass.
-   [ ] Security tests pass.
-   [ ] Regression tests pass.
-   [ ] Release-candidate journey passes.
-   [ ] No open P0/P1 issues.

------------------------------------------------------------------------

# 43. Completion Statement

The DigiZafe system is ready for release-candidate approval only when
this validation guide is completed against a specific commit and
environment and the resulting validation report records a PASS decision.

The final safety model remains:

``` text
Verified identity
+ explicit consent
+ controlled egress
+ provenance
+ deterministic authoritative scoring
+ explainability
+ user-directed remediation
+ privacy controls
+ optional bounded ML
+ operational recovery
```

No single passing unit test, successful build, or working demo replaces
complete system validation.

**End of Complete System Validation, Test, Error-Checking & Fix
Verification Guide.**
