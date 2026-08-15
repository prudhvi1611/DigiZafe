# DigiZafe --- Pre-Sprint 12 Consolidation & Required Fixes

**Document version:** 1.0\
**Applies after:** Sprint 11\
**Must complete before:** Sprint 12 Optional Free Residual ML\
**Based on:** `MASTER_ENGINEERING_CONTEXT.md` v2.1 and Sprint 0--11
implementation guides\
**Purpose:** Resolve cross-sprint contract drift, security gaps, scoring
semantics, narrative-provider inconsistency, frontend auth persistence,
and generated-code artifacts before introducing any residual ML
component.

> This is a consolidation sprint / hardening gate, not an architecture
> redesign.\
> Frozen architecture remains authoritative. If the repository conflicts
> with a frozen document, file a Critical Blocker Note (CBN) rather than
> silently changing the architecture.

------------------------------------------------------------------------

# 1. Why This Gate Exists

Sprint 12 introduces an optional residual ML layer. ML must not be added
on top of inconsistent domain contracts, ambiguous provenance semantics,
insecure egress behavior, or unstable deterministic scoring.

Before Sprint 12 starts, DigiZafe must have:

-   one canonical exposure-layer type;
-   one canonical connector/provenance contract;
-   verified-only and consented egress enforced end-to-end;
-   DNS-rebinding-resistant outbound HTTP;
-   PDSS semantics where source layer is provenance, not automatic
    severity;
-   deterministic/local grounded narratives as the free core;
-   no browser storage of auth tokens;
-   clean scan state-machine code;
-   cumulative migrations and DTOs that work from a fresh database;
-   regression tests covering the complete Sprint 0--11 path.

------------------------------------------------------------------------

# 2. Required Fix Summary

  ----------------------------------------------------------------------------
  ID                Priority          Area               Required outcome
  ----------------- ----------------- ------------------ ---------------------
  FIX-01            P0                Domain contracts   One canonical
                                                         exposure-layer enum
                                                         across Sprint 3--11

  FIX-02            P0                Egress security    DNS rebinding,
                                                         redirects, IP
                                                         validation, size
                                                         limits, and host
                                                         policy hardened

  FIX-03            P0                PDSS               Layer is
                                                         provenance/context,
                                                         not an unconditional
                                                         severity multiplier

  FIX-04            P0                Consent/G1         Unverified or
                                                         unconsented scans
                                                         produce zero
                                                         connector calls and
                                                         zero egress

  FIX-05            P1                Narrative          Deterministic
                                                         fallback always
                                                         works; local Ollama
                                                         is preferred free
                                                         enhancement

  FIX-06            P1                Frontend auth      No access/refresh
                                                         tokens in
                                                         `localStorage` or
                                                         `sessionStorage`

  FIX-07            P1                Scan state machine Remove generated
                                                         enum/transition
                                                         artifacts; define
                                                         cancellation
                                                         explicitly

  FIX-08            P1                Canonicalization   Preserve user-entered
                                                         identifier semantics;
                                                         isolate
                                                         provider-specific
                                                         aliases

  FIX-09            P1                Contracts/DTOs     Remove duplicate
                                                         enums and
                                                         incompatible DTO
                                                         definitions

  FIX-10            P1                Migrations         Fresh install and
                                                         sequential upgrade
                                                         from Sprint 0 to
                                                         current head both
                                                         work

  FIX-11            P1                Tests              Add cross-sprint
                                                         invariant, security,
                                                         migration, and
                                                         contract tests

  FIX-12            P2                Cleanup            Remove dead code,
                                                         stale config,
                                                         duplicate Sprint-era
                                                         definitions, and
                                                         misleading comments
  ----------------------------------------------------------------------------

------------------------------------------------------------------------

# 3. FIX-01 --- Canonical Exposure Layer

## Problem

Sprint 3 already introduces a connector layer concept:

``` python
class ConnectorLayer(str, Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CONSTRAINED_DARK = "constrained_dark"
```

Sprint 11 must not introduce a competing `ExposureLayer` with identical
or near-identical values unless the repository has a deliberate,
documented distinction.

Duplicate enums create subtle failures in:

-   connector capability registration;
-   scan layer selection;
-   observation normalization;
-   finding provenance;
-   PDSS inputs;
-   API serialization;
-   frontend filters.

## Required implementation

Create or retain exactly one canonical enum in a pure domain module,
preferably:

``` text
backend/app/domain/exposure_layers.py
```

Recommended content:

``` python
from enum import Enum


class ExposureLayer(str, Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CONSTRAINED_DARK = "constrained_dark"
```

Then update all references so the canonical type is used by:

``` text
ConnectorCapability.layer
ConnectorObservation.layer
Scan requested_layers
ConnectorRun layer metadata
Finding provenance
Evidence metadata
PDSS input DTOs
API response DTOs
Frontend API types
```

If `ConnectorLayer` already exists in production code, either:

1.  rename it to `ExposureLayer` in one controlled migration/refactor;
    or
2.  keep `ConnectorLayer` as the canonical name and make Sprint 11
    import it.

Do **not** keep two independent enums with the same values.

## Acceptance criteria

-   `grep`/repository search finds only one authoritative enum
    definition.
-   Serialization values remain exactly:
    -   `surface`
    -   `deep`
    -   `constrained_dark`
-   Existing Sprint 3--10 data remains readable.
-   Sprint 11 scans can select layers without adapter conversion hacks.
-   Unit tests verify round-trip serialization.

------------------------------------------------------------------------

# 4. FIX-02 --- Harden `EgressFetcher`

## Security invariant

All external HTTP initiated by DigiZafe connectors, verification flows,
archive adapters, remediation verification, and optional narrative
providers must pass through the approved egress boundary unless a frozen
design explicitly defines another controlled boundary.

The implementation must protect against:

-   localhost access;
-   RFC1918/private ranges;
-   loopback;
-   link-local;
-   multicast;
-   unspecified addresses;
-   IPv6 local/private ranges;
-   cloud metadata endpoints;
-   DNS rebinding;
-   redirect-based SSRF;
-   oversized responses;
-   unsupported schemes;
-   ambiguous hostnames;
-   host allowlist bypass.

## Required request flow

``` text
Parse URL
→ validate scheme
→ normalize hostname
→ enforce destination/host policy
→ resolve hostname
→ inspect every returned IP
→ reject request if any selected destination is forbidden
→ connect using an approved/pinned resolution strategy
→ preserve TLS hostname verification
→ do not automatically follow redirects
→ stream response with hard byte limit
→ record egress result
```

## Required rules

### Schemes

Allow only:

``` text
http
https
```

Reject:

``` text
file:
ftp:
gopher:
data:
javascript:
unix:
```

### Address policy

Reject at minimum:

-   `127.0.0.0/8`
-   `10.0.0.0/8`
-   `172.16.0.0/12`
-   `192.168.0.0/16`
-   `169.254.0.0/16`
-   `0.0.0.0/8`
-   IPv6 loopback
-   IPv6 link-local
-   IPv6 unique-local
-   multicast
-   unspecified addresses

Explicitly block known metadata destinations such as link-local metadata
IPs.

### DNS

Do not merely:

``` text
resolve → validate → ask HTTP client to resolve hostname again
```

Use a design that prevents a second uncontrolled DNS resolution from
selecting a different address.

If the current HTTP stack cannot safely pin the validated address while
preserving TLS/SNI/Host behavior, file a security ADR/CBN and implement
the approved transport strategy before enabling Amber connectors.

### Redirects

Default:

``` text
follow_redirects = false
```

If a connector requires redirects, each redirect target must be
revalidated through the same egress policy.

### Response size

Read responses incrementally and stop once:

``` text
EGRESS_MAX_RESPONSE_BYTES
```

is exceeded.

Do not rely only on `Content-Length`.

### Logging

Never log:

-   verification secrets;
-   full authorization headers;
-   raw personal identifiers when a blind index or redacted form is
    sufficient;
-   complete sensitive query strings.

## Required tests

Add security tests for:

``` text
localhost
127.0.0.1
private IPv4
IPv6 loopback
IPv6 unique-local
link-local metadata
decimal/hex/octal IP tricks where parser permits them
hostname resolving to private IP
mixed public/private DNS answers
redirect from public host to private host
oversized chunked response
unsupported schemes
allowlist mismatch
```

## Acceptance criteria

-   No connector performs raw user-influenced HTTP outside the approved
    boundary.
-   Security tests pass.
-   Sprint 11 Common Crawl, Wayback, and configured Amber index all use
    the same egress policy.
-   Redirect behavior is explicit and tested.

------------------------------------------------------------------------

# 5. FIX-03 --- Correct PDSS Layer Semantics

## Problem

Earlier PDSS configuration may contain unconditional layer multipliers
such as:

``` json
{
  "surface": 1.0,
  "deep": 1.1,
  "constrained_dark": 1.2
}
```

This can incorrectly imply:

``` text
constrained-dark finding > deep finding > surface finding
```

regardless of evidence quality or actual harm.

That is not a safe default.

A confirmed surface-web plaintext credential exposure may be more severe
than a low-confidence metadata mention from an Amber source.

## Required rule

**Exposure layer is provenance/context. It is not automatically
severity.**

The deterministic PDSS core should derive risk from factors such as:

-   sensitivity;
-   discoverability;
-   linkability;
-   impact;
-   temporal relevance;
-   confidence/evidence quality;
-   exposed attributes;
-   credential risk;
-   confirmation status.

## Required implementation

Preferred option:

-   remove unconditional layer multipliers from score calculation;
-   retain `layer` in provenance and explanations.

If backward compatibility requires the catalog field to remain, set all
multipliers to neutral:

``` json
{
  "surface": 1.0,
  "deep": 1.0,
  "constrained_dark": 1.0
}
```

and mark the field deprecated.

Any future non-neutral layer effect requires:

-   model-card justification;
-   evaluation evidence;
-   bounded effect;
-   version bump;
-   regression analysis.

## Required model-card update

Update:

``` text
docs/model-cards/pdss-v1.md
```

to state:

> Source layer describes where evidence was discovered. It does not, by
> itself, determine severity. Severity is driven by the nature,
> sensitivity, confidence, exploitability/discoverability, linkability,
> impact, and temporal relevance of the evidence.

## Migration/versioning

If current production score outputs change:

-   bump the PDSS model version;
-   retain prior score history;
-   recompute only according to the documented rescore policy;
-   never silently rewrite historical score records.

Recommended version:

``` text
pdss-v1.1.0
```

## Acceptance criteria

-   Identical findings differing only in layer do not receive different
    severity solely because of layer.
-   Layer remains visible in provenance and explanations.
-   Confirmed/Possible tracks continue to work.
-   Model card documents the change.
-   Golden-vector scoring tests pass.

------------------------------------------------------------------------

# 6. FIX-04 --- Enforce Verified-Only + Consent Before Egress

## Required invariant

For any discovery connector:

``` text
unverified identifier
→ no scan execution
→ no connector invocation
→ no external request
→ no egress ledger destination call
```

For any consent-gated layer:

``` text
missing/revoked consent
→ no connector invocation
→ no external request
```

This must be enforced in depth.

## Required enforcement layers

``` text
API validation
+
service-layer authorization
+
scan orchestration gate
+
database verified-identifier enforcement
+
connector dispatch policy
+
egress destination consent check where applicable
```

## Amber-specific requirement

Sprint 11 Deep and Constrained-Dark scans must require explicit Amber
consent when configured by policy.

Consent must identify at least:

-   user;
-   purpose;
-   layer;
-   destination/source class where required;
-   grant timestamp;
-   revocation state.

Workers must never auto-grant consent.

## Required tests

Add integration tests:

``` text
unverified identifier cannot create scan
unverified identifier cannot be dispatched by worker
revoked consent prevents Amber connector call
missing Amber consent prevents Amber connector call
surface-only scan does not invoke Amber connectors
deep-only selection invokes only approved deep connectors
constrained-dark disabled flag prevents connector registration/execution
```

Use fake connectors/fetchers and assert exact call counts.

## Acceptance criteria

The strongest test must prove:

``` text
forbidden request path → outbound request count == 0
```

------------------------------------------------------------------------

# 7. FIX-05 --- Narrative Provider Architecture

## Required provider order

The free core must be:

``` text
1. Deterministic grounded narrative — always available
2. Local Ollama / llama.cpp — optional enhancement
3. External hosted LLM — optional, non-core, separately consented
```

Do not make a hosted provider required for the normal product loop.

## Required configuration

Canonical settings should prefer local inference:

``` bash
FEATURE_GROUNDED_NARRATIVE=true
NARRATIVE_PROVIDER=deterministic
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
NARRATIVE_TIMEOUT_SECONDS=60
NARRATIVE_MAX_FINDINGS=15
NARRATIVE_MAX_TOKENS=800
NARRATIVE_TEMPERATURE=0.2
```

Optional hosted providers may remain behind explicit feature flags.

## Grounding rule

Narratives may use only approved durable facts such as:

-   finding metadata;
-   score explanation records;
-   recommendation metadata;
-   remediation status;
-   counterfactual outputs.

Narratives must not invent:

-   breaches;
-   exposed attributes;
-   identities;
-   source confirmation;
-   remediation success.

## External-provider privacy rule

If an external LLM is enabled:

-   explicit user/operator disclosure is required;
-   send minimum necessary data;
-   redact direct identifiers where possible;
-   write an egress ledger record;
-   apply consent policy;
-   do not send raw evidence dumps.

## Acceptance criteria

-   Narrative endpoint works with no API key and no Ollama service.
-   Deterministic fallback always returns a valid grounded response.
-   Local Ollama can be enabled without code changes.
-   Hosted provider failure never breaks the core explainability path.

------------------------------------------------------------------------

# 8. FIX-06 --- Frontend Auth Storage

## Canonical Sprint 10+ rule

Do not store access or refresh tokens in:

``` text
localStorage
sessionStorage
IndexedDB
```

Current baseline:

``` text
access token → memory only
refresh token → memory only
```

A browser refresh may require reauthentication until a future
HttpOnly-cookie architecture is deliberately implemented.

## Required cleanup

Remove or neutralize:

``` text
sessionStorage.setItem(...)
sessionStorage.getItem(...)
localStorage.setItem(...)
localStorage.getItem(...)
```

for authentication secrets.

Remove stale comments from Sprint 9 that describe sessionStorage
refresh-token persistence as current behavior.

## Acceptance criteria

-   Repository search finds no browser-storage write of access/refresh
    tokens.
-   Logout clears in-memory auth state.
-   401 handling does not create an infinite refresh loop.
-   Token values are not printed to console.
-   Frontend tests verify memory-only behavior.

------------------------------------------------------------------------

# 9. FIX-07 --- Clean Scan State Machine

## Problem

Generated artifacts such as:

``` python
ConnectorRunStatus.CANCELLED if False else ConnectorRunStatus.FAILED
```

must not remain in production code.

## Required decision

Choose one explicit model.

### Option A --- Support connector-run cancellation

Add:

``` python
CANCELLED = "cancelled"
```

and define valid transitions.

### Option B --- Scan cancellation only

Do not add run-level `CANCELLED`; when a scan is cancelled:

-   pending runs are marked `SKIPPED` with a cancellation reason; or
-   a clearly documented terminal status is used.

Preferred for clarity: **Option A**, if workers can actually observe and
honor cancellation.

## Required properties

-   terminal states have no outgoing transitions;
-   idempotent same-state transitions are explicitly documented;
-   reconciliation cannot move a terminal scan back to running;
-   timeout and cancellation are distinct;
-   every terminal connector run has a reason/result summary.

## Acceptance criteria

-   No fake conditional enum expressions remain.
-   Transition tables are exhaustive.
-   Unit tests cover every allowed and forbidden transition.
-   Reconcile tests cover stale running jobs and terminal-state
    preservation.

------------------------------------------------------------------------

# 10. FIX-08 --- Identifier Canonicalization Semantics

## Required rule

Do not destructively collapse provider-specific aliases into the only
stored representation of a user identifier.

Recommended model:

``` text
original/display value
canonical application value
blind index
optional provider-specific comparison alias
```

For example, provider-specific Gmail transformations should not erase
what the user entered.

## Required behavior

-   Unicode normalization remains deterministic.
-   Domain normalization uses IDNA safely.
-   Email comparison rules are documented.
-   Provider-specific aliasing is isolated and optional.
-   Verification is tied to the actual identifier ownership flow.
-   Existing blind indexes remain migration-safe.

## Acceptance criteria

-   Canonicalization tests cover Unicode, IDNA, plus tags, dots, case,
    invalid domains, and maximum lengths.
-   User-facing display value remains stable.
-   No cross-provider assumptions are applied globally.

------------------------------------------------------------------------

# 11. FIX-09 --- Canonical Contract Inventory

Create:

``` text
docs/architecture/canonical-contract-inventory.md
```

It must list the single authoritative definition for:

  Concept                Canonical location
  ---------------------- ---------------------------------------------------
  Identifier type        one domain module
  Exposure layer         one domain module
  Legality tier          connector/domain contract
  Observation kind       connector SDK contract
  Finding kind           domain/model contract
  Scan status            scan state module
  Connector-run status   scan state module
  Consent purpose        consent domain contract
  Connector capability   connector SDK
  Observation DTO        connector SDK
  Finding provenance     finding/domain DTO
  PDSS input/output      scoring domain
  API DTOs               schemas, importing domain enums where appropriate

## Required rule

Do not duplicate business enums separately in:

``` text
models
schemas
connectors
frontend
```

when generated/derived representations can reference the canonical wire
values.

The frontend may define TypeScript unions for API consumption, but their
values must be contract-tested against backend OpenAPI or shared
generated types.

## Acceptance criteria

-   Inventory document exists.
-   Duplicate authoritative definitions are removed.
-   OpenAPI schema exposes stable values.
-   Contract tests detect drift.

------------------------------------------------------------------------

# 12. FIX-10 --- Migration Integrity

Before Sprint 12, validate both paths.

## Path A --- Fresh database

``` bash
drop/recreate test database
alembic upgrade head
run full test suite
```

## Path B --- Sequential historical upgrade

Using a database at the earliest retained migration:

``` text
upgrade through every migration
→ current head
→ run integrity checks
```

## Required checks

-   exactly one Alembic head unless a documented merge migration exists;
-   no placeholder `down_revision`;
-   no migration imports application runtime services;
-   enum changes are migration-safe;
-   RLS policies exist after fresh install;
-   verified-only trigger/function exists;
-   indexes and uniqueness constraints match repository assumptions;
-   downgrade behavior is documented even if production downgrades are
    not supported.

## Acceptance criteria

``` bash
alembic heads
```

returns the expected single head.

Fresh and sequential upgrade tests pass in CI.

------------------------------------------------------------------------

# 13. FIX-11 --- Cross-Sprint Regression Test Matrix

Create a dedicated test suite for system invariants.

Recommended directory:

``` text
backend/tests/regression/
```

## Required scenarios

### Identity and G1

``` text
register
→ login
→ add identifier
→ scan denied before verification
→ verify
→ scan allowed
```

### Egress

``` text
unverified identifier → 0 outbound calls
revoked consent → 0 outbound calls
private destination → blocked
redirect to private destination → blocked
```

### Connector SDK

``` text
rate limit
cache hit
negative cache
disabled connector
source attribution
egress ledger
```

### Discovery

``` text
scan state transitions
connector partial failure
reconciliation
timeout
cancellation
SSE terminal event
```

### Evidence

``` text
raw TTL purge
summary TTL purge
durable finding metadata preserved
no raw dump retention
```

### PDSS

``` text
golden vectors
determinism
model versioning
confirmed/possible tracks
layer-neutral severity test
counterfactual consistency
```

### Recommendations

``` text
idempotent generation
dependency ordering
dismiss/done lifecycle
rescore delta
```

### Remediation

``` text
dry-run
manual CAPTCHA state
no false verified_removed
verify loop
per-user isolation
```

### Privacy

``` text
export excludes secrets
consent revoke
audit visibility
egress visibility
crypto-shred/purge
deterministic narrative fallback
```

### Frontend contract

``` text
OpenAPI/DTO compatibility
memory-only auth
scan SSE handling
layer labels
Amber consent UX
```

## Acceptance criteria

All Sprint 0--11 regression tests are green before Sprint 12 code is
merged.

------------------------------------------------------------------------

# 14. FIX-12 --- Repository Cleanup

Perform a controlled cleanup pass.

## Remove or resolve

-   duplicate Sprint-era enums;
-   obsolete config fields;
-   unused feature flags;
-   dead imports;
-   placeholder branches;
-   impossible conditional expressions;
-   stale comments describing superseded behavior;
-   duplicate Sprint 10 files/variants;
-   direct HTTP clients bypassing the approved egress architecture;
-   browser token persistence;
-   non-neutral PDSS layer multipliers;
-   hosted-LLM assumptions in the free core.

## Do not remove

-   historical migrations;
-   attribution;
-   model-card history;
-   score history;
-   audit records;
-   prior model versions needed to interpret stored results.

------------------------------------------------------------------------

# 15. Recommended Implementation Order

Execute the fixes in this order:

``` text
1. Freeze repository branch / create backup tag
2. Build canonical contract inventory
3. Unify exposure-layer type
4. Harden EgressFetcher
5. Add verified/consent zero-egress tests
6. Correct PDSS layer semantics + model card/version
7. Clean scan state machine
8. Correct narrative provider hierarchy
9. Remove browser auth persistence
10. Review identifier canonicalization
11. Consolidate migrations
12. Add full regression matrix
13. Run cleanup/static checks
14. Run fresh-install test
15. Run complete Sprint 0–11 user journey
16. Tag pre-Sprint-12 baseline
```

Recommended Git tag:

``` bash
git tag -a pre-sprint-12-hardened -m "DigiZafe Sprint 0-11 consolidated and hardened before residual ML"
```

------------------------------------------------------------------------

# 16. Suggested Commit Plan

Use small reviewable commits.

``` bash
git commit -m "refactor(domain): unify canonical exposure layer contract"
git commit -m "fix(security): harden egress fetcher against rebinding redirects and oversized responses"
git commit -m "fix(pdss): make exposure layer provenance-only and version scoring semantics"
git commit -m "fix(consent): enforce verified and consent gates before connector egress"
git commit -m "fix(scan): clean connector run state transitions and cancellation semantics"
git commit -m "fix(narrative): restore deterministic and local-first grounded narrative path"
git commit -m "fix(frontend): enforce memory-only authentication tokens"
git commit -m "fix(identity): preserve identifier display semantics and isolate provider aliases"
git commit -m "test(regression): add sprint 0-11 invariant and contract suite"
git commit -m "chore(pre-sprint-12): consolidate migrations contracts docs and cleanup"
```

------------------------------------------------------------------------

# 17. Pre-Sprint 12 Definition of Done

Sprint 12 must **not** start until every P0 and P1 item below is
complete.

## Architecture and contracts

-   [ ] One canonical exposure-layer enum exists.
-   [ ] Canonical contract inventory is documented.
-   [ ] No conflicting business enum definitions remain.
-   [ ] Sprint 11 uses existing connector and provenance contracts
    rather than parallel types.

## Security and privacy

-   [ ] `EgressFetcher` passes SSRF and DNS-rebinding-focused security
    tests.
-   [ ] Redirect targets are blocked or revalidated.
-   [ ] Response byte limits are enforced while streaming.
-   [ ] Unverified identifiers produce zero outbound connector calls.
-   [ ] Missing/revoked Amber consent produces zero outbound connector
    calls.
-   [ ] No raw sensitive evidence is retained beyond approved TTL
    policy.
-   [ ] External narrative providers are not required for the free core.

## PDSS

-   [ ] Layer is not an unconditional severity multiplier.
-   [ ] PDSS model card documents provenance-vs-severity semantics.
-   [ ] Score model version is bumped if outputs change.
-   [ ] Golden-vector tests pass.
-   [ ] Confirmed/Possible tracks remain deterministic.

## Auth

-   [ ] No access or refresh token is persisted in browser storage.
-   [ ] 401/refresh/logout behavior is tested.
-   [ ] No auth secrets are logged.

## Discovery

-   [ ] Scan and connector-run state machines contain no generated
    artifacts.
-   [ ] Terminal-state behavior is explicit.
-   [ ] Reconciliation is idempotent.
-   [ ] Cancellation semantics are documented and tested.

## Data and migrations

-   [ ] Fresh `alembic upgrade head` succeeds.
-   [ ] Historical sequential upgrade succeeds.
-   [ ] Expected single Alembic head exists.
-   [ ] RLS and verified-only database protections exist after fresh
    install.

## End-to-end regression

-   [ ] Register/login works.
-   [ ] Identifier ownership verification works.
-   [ ] Surface scan works.
-   [ ] Deep Amber scan requires explicit consent.
-   [ ] Constrained-Dark remains disabled by default.
-   [ ] Findings retain source/layer/provenance.
-   [ ] PDSS computes deterministically.
-   [ ] Recommendations generate idempotently.
-   [ ] Remediation workflow preserves user control.
-   [ ] Privacy export excludes secrets.
-   [ ] Deterministic narrative works offline.
-   [ ] Frontend build passes.
-   [ ] Full backend test suite passes.
-   [ ] Security test suite passes.
-   [ ] Regression suite passes.

------------------------------------------------------------------------

# 18. Sprint 12 Entry Gate

Only after this document's Definition of Done is green may Sprint 12
begin.

Sprint 12 must remain:

``` text
optional residual ML
```

The deterministic system remains authoritative.

The ML component must:

-   consume stable, versioned features;
-   never bypass verified-only or consent rules;
-   never replace PDSS explanations;
-   never silently alter historical deterministic scores;
-   produce a residual/flag or bounded auxiliary signal;
-   have a model card;
-   be reproducible;
-   be removable without breaking the core product;
-   be evaluated against the hardened Sprint 0--11 baseline.

The intended architecture is:

``` text
Verified identity
      ↓
Consented discovery
      ↓
Normalized evidence + provenance
      ↓
Deterministic PDSS
      ↓
Explainable recommendations/remediation
      ↓
Optional residual ML signal
```

Not:

``` text
raw data
→ opaque model
→ unexplained risk score
```

------------------------------------------------------------------------

# 19. Completion Statement

When this hardening gate is complete, DigiZafe has a stable pre-ML
baseline:

``` text
Verify
→ Consent
→ Discover
→ Preserve provenance
→ Explain
→ Score deterministically
→ Prioritize
→ Remediate
→ Re-verify
→ Re-score
```

At that point, Sprint 12 can evaluate whether residual ML adds
measurable value without compensating for unresolved engineering
inconsistencies.

**Next:** Sprint 12 --- Optional Free Residual ML.
