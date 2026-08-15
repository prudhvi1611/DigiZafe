# DigiZafe — Sprint 19 Implementation Guide

**Sprint:** 19 — OSINTgram Optional Connector, Secure Session Boundary & Provenance-Preserving Instagram Candidate Discovery  
**Applies after:** Sprint 18 — Identity Enrichment & Clustering  
**Primary goal:** Add OSINTgram as an isolated, optional, authenticated OSINT connector that produces bounded, provenance-preserving candidate observations without bypassing platform controls, leaking session secrets, or converting connector output into automatic identity proof.

> Core invariants:
>
> `OSINTgram observation ≠ verified identity`
>
> `Instagram username match ≠ ownership proof`
>
> `authenticated connector ≠ permission to bypass platform controls`
>
> `session secret ≠ ordinary application data`
>
> `connector failure ≠ negative identity evidence`
>
> `connector output must enter the existing evidence-integrity pipeline`

---

# 1. Mandatory Sprint 18 Preflight

Before implementing Sprint 19, verify the actual repository state rather than relying only on the Sprint 18 summary.

The Sprint 18 walkthrough states that:

```text
tests/integration/test_candidate_discovery.py passed at 100%
```

but also claims:

```text
the integration regression test suite has passed
```

Those statements are not necessarily equivalent to a full Sprint 14–18 regression pass.

Required preflight:

```text
1. Run the complete backend test suite.
2. Report exact collected / passed / failed / skipped counts.
3. Run the frontend production build.
4. Verify the actual Alembic current/head state.
5. Verify Sprint 18 migration d32f5f3ebc79 is the actual current head.
6. Verify ENGINE_VERSION = 5 and POLICY_VERSION = 5 in runtime code.
7. Verify identity_enrichment queue routing exists and is consumed by an actual worker in the deployment configuration.
8. Verify Sprint 18 feature-flag defaults.
9. Verify privacy export actually includes the new Sprint 18 records, not only that deletion cascades exist.
10. Verify cluster and enrichment RLS/cross-user isolation tests.
```

Do not proceed on the assumption that one candidate-discovery integration test proves the entire Sprint 18 architecture.

If missing Sprint 18 verification coverage is discovered, add the smallest required tests before building Sprint 19.

---

# 2. Sprint Goal

Add OSINTgram as an optional source-specific connector for bounded Instagram-oriented candidate discovery and evidence collection.

Target architecture:

```text
Verified Identity Anchor
        │
        ├── active aliases
        └── user-approved discovery input
        │
        ▼
Connector Eligibility Policy
        │
        ├── feature flag
        ├── explicit connector enablement
        ├── consent
        ├── account/session availability
        ├── rate/quota policy
        └── connector capability policy
        │
        ▼
OSINTgram Connector Boundary
        │
        ├── isolated subprocess/container execution
        ├── no shell injection
        ├── bounded command allowlist
        ├── bounded timeout
        ├── bounded output
        └── secret-safe environment
        │
        ▼
Raw Connector Result
        │
        ▼
Normalization + Provenance
        │
        ├── connector = osintgram
        ├── connector version
        ├── capability
        ├── source username/profile
        ├── observed_at
        ├── raw-result fingerprint
        └── derived_from lineage
        │
        ▼
Candidate / Evidence Pipeline
        │
        ├── CandidateProfile
        ├── Cross-Link Evidence
        ├── Safe Avatar Observation
        └── IdentityEvidence
        │
        ▼
Sprint 17–18 Deterministic Match Engine
        │
        ▼
Human Review
```

OSINTgram must be an input source to the existing architecture, not a parallel identity-resolution system.

---

# 3. Scope

Sprint 19 may implement:

```text
optional OSINTgram connector
connector capability registry
secure connector session-reference architecture
bounded username/profile observations
bounded public metadata observations
bounded follower/following relationship observations if operationally supported and approved
bounded external-link observations
bounded avatar URL observations
candidate generation
cross-link evidence generation
provenance
connector health/status
rate/quota controls
privacy lifecycle
```

Sprint 19 must not implement:

```text
credential theft
password collection from arbitrary users
plaintext credential storage
session-cookie exposure to frontend
automatic login bypass
CAPTCHA bypass
MFA bypass
rate-limit bypass
private-account access without legitimate authorization
platform access-control circumvention
mass scraping
unbounded follower graph crawling
automatic identity confirmation
automatic PDSS confirmation
```

---

# 4. OSINTgram Is an Optional Connector

OSINTgram must not become a mandatory dependency for DigiZafe startup.

Required behavior:

```text
OSINTgram unavailable
→ DigiZafe core remains operational

OSINTgram feature disabled
→ no OSINTgram execution

OSINTgram session unavailable
→ connector reports unavailable/configuration-required
→ no application crash
```

Use an optional dependency or isolated runtime boundary.

---

# 5. Feature Flag

Add:

```text
FEATURE_OSINTGRAM_DISCOVERY=false
```

Safe default:

```text
false
```

Optional additional flags:

```text
FEATURE_OSINTGRAM_RELATIONSHIPS=false
FEATURE_OSINTGRAM_AVATAR_ENRICHMENT=false
```

Do not expose high-cost capabilities merely because the base connector is enabled.

---

# 6. Connector Capability Policy

Create a canonical capability registry.

Example:

```text
profile_lookup
public_profile_metadata
external_links
avatar_observation
relationship_observation
```

Each capability should define:

```text
enabled
requires_session
requires_explicit_consent
max_targets_per_run
timeout
output_limit
rate/quota policy
evidence types allowed
```

Do not allow arbitrary OSINTgram commands or flags from API input.

---

# 7. No Arbitrary Command Execution

The API must never accept:

```text
command
flags
raw CLI arguments
shell fragment
```

from the user.

Required architecture:

```text
API capability enum
        ↓
internal capability mapping
        ↓
fixed argument builder
        ↓
subprocess with shell=False
```

Example:

```text
"profile_lookup"
→ internally mapped approved OSINTgram operation
```

not:

```text
POST {
  "command": "...",
  "args": ["..."]
}
```

---

# 8. Execution Boundary

Prefer an isolated connector runtime.

Recommended order of preference:

```text
1. Dedicated connector container/worker
2. Dedicated Celery queue with isolated subprocess
3. Existing worker with strict subprocess boundary only as temporary fallback
```

Recommended logical queue:

```text
osint_connectors
```

Do not run OSINTgram inside synchronous API request handling.

---

# 9. Subprocess Security

If OSINTgram is invoked as a subprocess:

```text
shell=False
explicit argument array
fixed executable path
strict capability allowlist
strict username/input validation
clean temporary working directory
minimal environment
hard timeout
bounded stdout/stderr capture
process-tree termination
no user-controlled output path
```

Do not rely only on regex sanitization when fixed argument construction can remove the injection surface.

---

# 10. Dedicated Runtime Recommendation

If practical, provision:

```text
osintgram-worker
```

or equivalent.

Recommended properties:

```text
no inbound public port
restricted filesystem
read-only application image where practical
temporary writable workspace
session secret injected only at runtime
resource limits
network access only as required
separate queue
```

Do not describe the runtime as a sandbox unless the deployment actually provides meaningful isolation.

---

# 11. Session and Credential Boundary

OSINTgram may require authenticated platform state.

Treat session material as high-sensitivity secret data.

Never store in ordinary application tables:

```text
plaintext password
plaintext session cookie
plaintext authentication token
raw credential file
```

Never return session secrets through:

```text
API responses
frontend state
logs
privacy export in plaintext
debug output
Celery task arguments
```

---

# 12. Preferred Session Architecture

Prefer one of these patterns:

```text
A. Operator-managed connector session
B. External secret-manager reference
C. Encrypted secret reference using the existing key-management boundary
```

The application database should store, at most:

```text
connector_session_id
user_id or operator scope
connector_type
secret_reference
status
created_at
last_validated_at
expires_at
revoked_at
```

The actual secret should be resolved only inside the authorized connector worker.

---

# 13. Session Ownership Model

Choose and document one explicit model.

Possible:

```text
operator-managed shared connector account
```

or:

```text
per-user connector session
```

Do not accidentally mix the two.

If using a shared operator-managed account:

```text
do not imply the Instagram account belongs to the DigiZafe user
```

If using per-user sessions:

```text
require explicit user action
strict ownership
revocation
secret isolation
```

---

# 14. No Password-Based UI in Sprint 19 by Default

Do not build a frontend form asking users to submit an Instagram password unless there is a separately approved, carefully designed authentication architecture.

Preferred Sprint 19 UX:

```text
connector unavailable
connector configured by deployment/operator
connector connected through an approved session-reference flow
```

Avoid collecting reusable platform passwords.

---

# 15. Secret Redaction

Add connector-specific redaction tests.

Logs must redact:

```text
passwords
cookies
session IDs
authorization headers
CSRF tokens
connector secret paths
raw environment secret values
```

Test both:

```text
successful execution
failed execution
exception traceback
```

---

# 16. Celery Task Secret Safety

Do not place raw secrets in Celery messages.

Required:

```text
task payload
→ connector_session_id / secret reference only
```

Worker:

```text
receives reference
→ authorizes ownership/scope
→ resolves secret at execution time
→ executes connector
```

---

# 17. Discovery Input Eligibility

OSINTgram discovery should use eligible Sprint 15 Identity Anchor inputs.

Default eligible inputs:

```text
active username/handle aliases
explicitly user-selected candidate username
```

Do not automatically send:

```text
email addresses
phone numbers
private identifiers
```

unless a future capability explicitly requires and approves them.

---

# 18. Explicit User Intent

Because authenticated social-platform querying can be more sensitive than passive username enumeration, require explicit user action to launch an OSINTgram run.

Example:

```text
Run Instagram discovery
```

Do not silently trigger OSINTgram for every alias on account creation.

---

# 19. Discovery Run Model

Reuse the existing candidate discovery architecture if it can safely represent connector-specific runs.

Preferred:

```text
CandidateDiscoveryRun
```

extended with:

```text
connector_type = osintgram
connector_version
capability
input_alias_ids
session_reference_id if applicable
policy_version
```

Do not create a parallel run model unless the existing model cannot preserve required semantics.

---

# 20. CandidateProfile Reuse

OSINTgram-discovered profiles should become:

```text
CandidateProfile
```

with connector-specific provenance.

Do not create:

```text
OSINTgramCandidateProfile
```

as a separate identity silo unless strictly necessary.

The existing candidate review states remain:

```text
unreviewed
confirmed_by_user
dismissed
```

---

# 21. User-Scoped Deduplication

Candidate deduplication must remain:

```text
user-scoped
```

Required conceptual uniqueness:

```text
user_id
+
canonical_profile_url
```

OSINTgram and Maigret may discover the same profile.

Required:

```text
same user
+ same canonical profile
+ multiple connectors
→ one CandidateProfile
+ multiple provenance observations
```

Do not overwrite Maigret provenance with OSINTgram provenance.

---

# 22. Multi-Connector Provenance

Introduce or reuse a provenance structure capable of representing:

```text
CandidateProfile
        ├── discovered_by Maigret
        ├── discovered_by OSINTgram
        └── enriched by Sprint 18 services
```

Each observation must preserve:

```text
connector
connector_version
capability
run_id
input alias
observed_at
source reference
raw-result fingerprint
derived_from
```

---

# 23. Connector Observation Model

If the existing provenance model is insufficient, add a generic model such as:

```text
ConnectorObservation
```

Conceptual fields:

```text
id
user_id
connector_type
connector_version
capability
run_id
candidate_profile_id
source_identifier_reference
observation_type
canonical_fact_key
normalized_payload
raw_result_fingerprint
observed_at
expires_at
status
created_at
```

Do not store unnecessary raw connector dumps indefinitely.

---

# 24. Raw Output Policy

Prefer:

```text
parse
normalize
fingerprint
discard raw output
```

If temporary raw output is needed for debugging:

```text
short TTL
encrypted/bounded
access controlled
disabled by default in production
```

Do not store entire OSINTgram outputs indefinitely without a defined purpose.

---

# 25. Supported Observation Types

Only emit observations that the connector actually returns reliably.

Possible:

```text
instagram_profile_observed
instagram_username_observed
instagram_display_name_observed
instagram_bio_link_observed
instagram_external_link_observed
instagram_avatar_url_observed
instagram_relationship_observed
```

Do not infer facts that were not observed.

---

# 26. Candidate Discovery Semantics

OSINTgram output remains candidate-level.

Required:

```text
OSINTgram found profile
→ CandidateProfile / observation
```

not:

```text
OSINTgram found profile
→ ConfirmedProfileReference
```

Only explicit user confirmation may promote the candidate according to existing Sprint 16–18 flows.

---

# 27. Identity Evidence Integration

OSINTgram-derived facts must enter:

```text
Connector Observation
        ↓
IdentityEvidenceService
        ↓
canonical fact deduplication
        ↓
independence grouping
        ↓
source reliability
        ↓
Sprint 17–18 deterministic Match Engine
```

Do not assign an arbitrary:

```text
OSINTgram score
```

that bypasses the canonical match policy.

---

# 28. Connector Reliability Is Not Identity Confidence

Required distinction:

```text
connector reliably observed a profile
≠
profile reliably belongs to the user
```

OSINTgram source reliability may describe confidence in the observation itself.

Ownership confidence remains the responsibility of the deterministic identity evidence engine.

---

# 29. Cross-Connector Independence

Maigret and OSINTgram discovering the same public profile may not represent two independent identity facts.

Example:

```text
Maigret found instagram.com/example
OSINTgram found instagram.com/example
```

This may strengthen:

```text
observation persistence / source corroboration
```

but must not be blindly counted as two independent ownership signals.

Use canonical fact deduplication.

---

# 30. Independence Group Policy

Examples:

```text
profile_existence:<canonical_profile_url>
username_fact:<canonical_username>
external_link_fact:<source_profile>:<target>
relationship_fact:<source>:<target>
```

Connector provenance remains attached, but duplicated canonical facts remain capped.

---

# 31. Sprint 18 Avatar Integration

If OSINTgram returns an avatar URL:

```text
OSINTgram
→ avatar URL observation only
```

Then:

```text
approved avatar observation
→ Sprint 18 AvatarSimilarityService
→ centralized EgressFetcher
→ bounded download
→ SHA-256 + pHash
```

OSINTgram must not bypass the Sprint 18 image safety boundary.

---

# 32. Sprint 18 Cross-Link Integration

If OSINTgram returns:

```text
bio URL
external link
linked profile
```

normalize it through:

```text
CrossLinkEvidenceService
```

Do not create a second OSINTgram-specific cross-link scoring path.

---

# 33. Relationship Observations

Follower/following relationships are potentially high-volume and weak identity evidence.

If implemented:

```text
disabled by default
bounded target count
bounded depth = 1
no recursive graph crawl
explicit capability flag
explicit quota
```

A relationship observation should normally be:

```text
weak contextual evidence
```

not strong proof of identity.

---

# 34. No Recursive Social Graph Crawling

Sprint 19 must not implement:

```text
followers of followers
following of following
recursive graph expansion
unbounded breadth-first crawling
```

Maximum default graph depth:

```text
1
```

and only if the capability is explicitly enabled.

---

# 35. Rate and Quota Policy

Define bounded per-user and/or per-session limits.

At minimum:

```text
max runs per time window
max usernames per run
max relationship targets per run
max concurrent connector runs
cooldown after repeated failures
```

Do not rely only on upstream platform rate limits.

---

# 36. Connector Health State

Expose safe connector status:

```text
available
disabled
not_configured
session_expired
temporarily_rate_limited
degraded
unavailable
```

Do not expose raw authentication errors or secret values.

---

# 37. Failure Semantics

Normalize failures:

```text
tool_unavailable
session_unavailable
session_expired
rate_limited
timeout
invalid_input
capability_disabled
partial_result
connector_error
```

Connector failure must not create:

```text
negative identity evidence
```

Required:

```text
connector failed
→ unknown / operational failure
```

---

# 38. Partial Results

If OSINTgram returns partial usable output before failure:

```text
preserve valid normalized observations
mark run partial_result
preserve provenance
```

Do not mark the entire run completed successfully.

---

# 39. Timeouts and Process Termination

Define:

```text
soft timeout
hard timeout
process-tree termination
```

A timed-out connector must not leave orphan processes.

Test this behavior.

---

# 40. Output Limits

Bound:

```text
stdout bytes
stderr bytes
parsed record count
relationship count
link count
candidate count
```

Prevent connector output from exhausting worker memory or database storage.

---

# 41. Temporary Workspace

Each run should use:

```text
isolated TemporaryDirectory
```

or equivalent.

Required cleanup:

```text
success
failure
timeout
worker exception
```

No user-controlled persistent output paths.

---

# 42. Connector Version Pinning

Pin the exact OSINTgram revision/version used.

Do not depend on an unpinned moving branch in production.

Record:

```text
connector_name
connector_version/revision
adapter_version
```

on each run.

---

# 43. Adapter Contract

Create:

```text
OSINTgramAdapter
```

with a stable internal result contract.

Example:

```text
ConnectorExecutionResult:
- status
- connector
- connector_version
- capability
- observations
- warnings
- started_at
- completed_at
- error_code
```

Business logic must not parse raw CLI text throughout the application.

---

# 44. Parser Robustness

Treat connector output as untrusted input.

Required:

```text
schema validation
type validation
length limits
URL normalization
unexpected-field tolerance
malformed-record isolation
```

One malformed observation must not crash the entire run if safe partial processing is possible.

---

# 45. API Endpoints

Adapt to existing conventions.

Possible:

```text
POST /api/v1/identity/discovery/osintgram
GET  /api/v1/identity/discovery/osintgram/status
GET  /api/v1/identity/discovery/runs/{run_id}
```

Optional connector/session administration endpoints must not expose secrets.

Do not expose arbitrary command endpoints.

---

# 46. Discovery Request DTO

Possible request:

```text
alias_ids
capabilities
```

Do not accept:

```text
raw command
raw CLI flags
password
cookie
session token
arbitrary output path
```

unless a separately approved secure session-establishment flow explicitly requires a credential input.

---

# 47. Frontend

Extend the Identity Discovery UI.

Possible:

```text
Discover with Maigret
Discover Instagram profiles
```

Show:

```text
connector availability
required consent
selected aliases
run progress
partial/failure state
candidate provenance
```

Do not expose session secrets.

---

# 48. Candidate Provenance UI

A candidate may show:

```text
Discovered by:
- Maigret
- OSINTgram
```

This is provenance, not a confidence score.

Do not render:

```text
2 tools found this → verified
```

---

# 49. Connector Limitations UI

Display concise limitations:

```text
Results may be incomplete.
Platform access and connector behavior can change.
A discovered account is not automatically confirmed as yours.
```

---

# 50. Privacy Export

Extend export to include:

```text
OSINTgram discovery runs
normalized connector observations
candidate provenance
connector status metadata relevant to the user
```

Do not export:

```text
plaintext passwords
session cookies
raw secret values
operator-owned connector credentials
```

---

# 51. Account Deletion and Shredding

Verify deletion of:

```text
user-scoped OSINTgram runs
connector observations
candidate provenance links
user-scoped session references
temporary artifacts
caches
```

If a secret is stored in an external secret manager:

```text
delete/revoke the secret according to ownership policy
```

Do not delete a shared operator-managed credential merely because one user deletes their DigiZafe account.

---

# 52. Session Revocation

If per-user sessions exist, support:

```text
revoke
expire
disable
```

Revocation must prevent future connector execution.

Existing normalized historical observations may remain or be deleted according to privacy policy.

---

# 53. Audit Events

Recommended:

```text
osintgram_run_requested
osintgram_run_started
osintgram_run_completed
osintgram_run_partial
osintgram_run_failed
osintgram_session_reference_created
osintgram_session_revoked
osintgram_candidate_observed
```

Never log raw secrets.

---

# 54. Security Tests — Command Injection

Required inputs:

```text
name; whoami
name && whoami
name | cat /etc/passwd
`whoami`
$(whoami)
newline injection
option-like username beginning with -
very long username
Unicode edge cases
```

Required result:

```text
rejected safely
or passed only as a literal validated positional value
```

No shell execution.

---

# 55. Security Tests — Secret Leakage

Test that secrets do not appear in:

```text
application logs
worker logs
exception traces
API responses
Celery task payload inspection
privacy export
database observation payloads
```

Any secret leakage is P0/P1 depending on scope.

---

# 56. Security Tests — Cross-User Isolation

Required:

```text
User A cannot run OSINTgram using User B alias
User A cannot read User B run
User A cannot read User B connector observations
User A cannot access User B session reference
User A cannot infer User B connector configuration through differing unsafe errors
```

Any cross-user failure is P0.

---

# 57. Security Tests — Feature and Consent Gates

Required:

```text
feature disabled
→ zero connector execution

missing consent
→ zero connector execution

capability disabled
→ zero capability execution

session unavailable
→ zero authenticated connector execution
```

Verify zero execution, not merely an HTTP error.

---

# 58. Adapter Unit Tests

Use fixtures/mocks for normal automated tests.

Test:

```text
successful profile observation
no result
partial result
malformed output
timeout
tool unavailable
session expired
rate limited
oversized output
unexpected fields
```

Do not require live Instagram access for the core CI suite.

---

# 59. Integration Tests

Test:

```text
alias → OSINTgram run → normalized observation
observation → CandidateProfile
same profile already found by Maigret → no duplicate CandidateProfile
multiple connectors → multiple provenance records
avatar URL observation → Sprint 18 safe avatar pipeline
external link observation → Sprint 18 cross-link pipeline
candidate remains unreviewed
user confirmation still required
```

---

# 60. Independence Tests

Mandatory:

```text
Maigret and OSINTgram discover same profile
→ one canonical profile-existence fact

OSINTgram username field + canonical profile URL username
→ one bounded username fact where derived from same observation

OSINTgram avatar URL + processed pHash
→ provenance lineage preserved

repeated OSINTgram run with unchanged observation
→ confidence does not increase indefinitely
```

---

# 61. Match Engine Versioning

If Sprint 19 adds only new observations that map into existing evidence rules, a policy/engine increment may or may not be required.

Required decision:

```text
inspect actual scoring behavior
```

If new evidence types or weights are introduced:

```text
increment POLICY_VERSION
```

If engine mechanics change materially:

```text
increment ENGINE_VERSION
```

Document the decision.

Do not increment versions mechanically without semantic change.

---

# 62. Assessment Staleness

New material OSINTgram evidence should:

```text
mark affected current assessment stale
or trigger bounded deterministic recalculation
```

Repeated identical observations must not create meaningless assessment history.

Use fingerprints/idempotency.

---

# 63. Cluster Integration

New evidence may affect Sprint 18 clusters.

Required:

```text
material new evidence
→ affected cluster stale/rebuild
```

Do not rebuild all user clusters for every duplicate observation.

Use affected-candidate scoping.

---

# 64. PDSS Boundary

OSINTgram output must not automatically create:

```text
Confirmed PDSS exposure
```

Required:

```text
connector observation
→ candidate/evidence pipeline
→ identity assessment
→ human review
```

Any future PDSS integration must be separately specified.

---

# 65. Existing Maigret Boundary

Sprint 19 must not break Sprint 16.

Required:

```text
Maigret remains independently feature-gated
Maigret remains usable when OSINTgram is unavailable
OSINTgram remains usable only when its own requirements are satisfied
```

Do not create a hard dependency:

```text
Maigret → OSINTgram
```

or:

```text
OSINTgram → Maigret
```

---

# 66. Connector Abstraction

If practical, introduce a small generic interface:

```text
IdentityDiscoveryConnector
```

Possible contract:

```text
name
version
capabilities
availability()
validate_input()
execute()
normalize()
```

Do not over-generalize the entire system in Sprint 19.

The abstraction should support:

```text
Maigret
OSINTgram
future connectors
```

without rewriting existing stable code unnecessarily.

---

# 67. Dependency and Supply-Chain Review

Before pinning OSINTgram:

```text
record exact source/revision
review dependency installation impact
review container size
review startup behavior
review transitive dependencies
```

Do not execute install scripts dynamically at runtime.

Build dependencies into the connector image/environment.

---

# 68. Operational Kill Switch

Feature flag disablement must act as a kill switch.

Required:

```text
FEATURE_OSINTGRAM_DISCOVERY=false
→ new runs rejected
→ queued-but-not-started runs handled according to documented policy
```

Consider a runtime connector status override for emergency disablement.

---

# 69. Metrics

Recommended:

```text
osintgram_runs_total
osintgram_run_duration
osintgram_failures_total by normalized error
osintgram_partial_results_total
osintgram_candidates_observed_total
osintgram_rate_limit_events
```

Do not use high-cardinality usernames as metric labels.

---

# 70. Documentation

Create/update:

```text
docs/connectors/osintgram.md
docs/connectors/connector-capability-policy.md
docs/security/connector-session-boundary.md
docs/privacy/connector-observations.md
docs/operations/osintgram-runbook.md
```

Document:

```text
supported capabilities
unsupported capabilities
session model
secret handling
execution isolation
timeouts
quotas
provenance
privacy lifecycle
known limitations
```

---

# 71. Known Limitations

Document:

```text
platform behavior can change
authenticated sessions can expire
results can be incomplete
profile metadata can change
usernames can be reused
accounts can be impersonated
relationship observations are not identity proof
connector failures are operational unknowns
```

---

# 72. Implementation Order

## Phase A — Sprint 18 Verification

```text
full backend suite
frontend build
migration head
runtime versions
queue consumer verification
privacy export verification
RLS verification
```

## Phase B — Connector Architecture

```text
feature flag
capability registry
connector abstraction
availability/health
```

## Phase C — Secure Session Boundary

```text
choose session ownership model
secret reference
runtime resolution
redaction
revocation
```

## Phase D — OSINTgram Adapter

```text
pinned version
isolated execution
fixed command mapping
timeouts
output limits
normalized errors
```

## Phase E — Discovery Integration

```text
eligible aliases
CandidateDiscoveryRun
CandidateProfile reuse
multi-connector provenance
```

## Phase F — Sprint 18 Enrichment Integration

```text
avatar URL observation
→ AvatarSimilarityService

external link observation
→ CrossLinkEvidenceService
```

## Phase G — Match/Cluster Integration

```text
canonical facts
independence
assessment staleness
bounded recalculation
affected cluster rebuild
```

## Phase H — Privacy and Audit

```text
export
deletion
session revocation
audit events
```

## Phase I — Frontend

```text
connector availability
run action
progress
candidate provenance
limitations
```

## Phase J — Verification

```text
injection
secret leakage
RLS
feature/consent gates
adapter fixtures
multi-connector deduplication
Sprint 14–18 regression
```

---

# 73. P0/P1 Defect Policy

For discovered defects:

```text
reproduce
→ classify
→ regression test
→ smallest safe fix
→ re-run affected suite
→ document
```

Stop for approval if the required fix would:

```text
collect reusable user passwords
bypass platform access controls
weaken session-secret protections
weaken cross-user isolation
change PDSS semantics
introduce major breaking architecture
```

---

# 74. Required Final Walkthrough

At completion provide:

1. Actual Sprint 18 starting Alembic head.
2. Sprint 19 migration ID and final head, if a migration is added.
3. Full Sprint 18 preflight test counts.
4. Sprint 18 verification gaps found and fixes applied.
5. OSINTgram exact pinned version/revision.
6. OSINTgram adapter version.
7. Feature flags and defaults.
8. Supported capability list.
9. Disabled/unsupported capability list.
10. Session ownership model.
11. Secret storage/reference architecture.
12. Confirmation that no raw secrets enter Celery task payloads.
13. Secret-redaction test results.
14. Session revocation behavior.
15. Execution boundary.
16. Queue name and worker deployment.
17. Subprocess/container isolation details.
18. Command allowlist/mapping.
19. Input validation.
20. Timeout values.
21. Retry policy.
22. Output limits.
23. Temporary-workspace cleanup behavior.
24. Normalized connector error taxonomy.
25. Discovery input eligibility.
26. CandidateDiscoveryRun integration.
27. CandidateProfile deduplication behavior.
28. Multi-connector provenance schema.
29. Raw-output retention policy.
30. Observation types implemented.
31. Avatar pipeline integration.
32. Cross-link pipeline integration.
33. Relationship-observation policy, if implemented.
34. Rate/quota limits.
35. Connector health states.
36. Match engine/policy version decision.
37. Assessment staleness behavior.
38. Cluster rebuild behavior.
39. RLS/cross-user isolation results.
40. Command-injection test results.
41. Secret-leakage test results.
42. Feature-disabled zero-execution result.
43. Consent-denied zero-execution result.
44. Session-unavailable zero-execution result.
45. Adapter unit-test results.
46. Multi-connector deduplication test result.
47. Independence/no-double-counting test result.
48. Privacy export result.
49. Account deletion/shredding result.
50. PDSS regression result.
51. Sprint 18 regression result.
52. Sprint 17 regression result.
53. Sprint 16 regression result.
54. Sprint 15 regression result.
55. Sprint 14 critical regression result.
56. Frontend production build result.
57. P0–P3 issues found.
58. Minimal fixes applied.
59. Files created or modified.
60. Remaining limitations.
61. GO / CONDITIONAL GO / NO-GO decision for Sprint 20.

Do not predetermine GO.

---

# 75. Definition of Done

## Sprint 18 Preflight

- [ ] Complete backend suite executed.
- [ ] Exact pass/fail/skip counts reported.
- [ ] Frontend production build passes.
- [ ] Actual Alembic head verified.
- [ ] ENGINE_VERSION and POLICY_VERSION verified.
- [ ] `identity_enrichment` routing and worker consumption verified.
- [ ] Sprint 18 privacy export verified.
- [ ] Sprint 18 RLS isolation verified.

## Connector Boundary

- [ ] OSINTgram optional.
- [ ] Feature flag defaults to false.
- [ ] Exact connector revision pinned.
- [ ] No arbitrary command API.
- [ ] `shell=False`.
- [ ] Fixed capability mapping.
- [ ] Hard timeout.
- [ ] Output bounded.
- [ ] Temporary workspace cleaned.
- [ ] Process tree terminated on timeout.

## Session Security

- [ ] Session ownership model documented.
- [ ] No plaintext passwords in ordinary DB tables.
- [ ] No raw secrets in API responses.
- [ ] No raw secrets in frontend state.
- [ ] No raw secrets in logs.
- [ ] No raw secrets in Celery messages.
- [ ] Secret references resolved only in authorized worker.
- [ ] Revocation/expiry supported where applicable.
- [ ] Secret-leakage tests pass.

## Discovery

- [ ] Eligible active aliases only by default.
- [ ] Explicit user action required.
- [ ] CandidateDiscoveryRun reused or safely extended.
- [ ] CandidateProfile reused.
- [ ] Deduplication user-scoped.
- [ ] Maigret + OSINTgram same profile does not create duplicate candidate.
- [ ] Multi-connector provenance preserved.
- [ ] Connector output does not auto-confirm identity.

## Evidence Integrity

- [ ] Canonical facts deduplicated across connectors.
- [ ] Independence groups preserved.
- [ ] Repeated observations do not inflate confidence.
- [ ] Connector reliability separated from identity confidence.
- [ ] Avatar observations use Sprint 18 safe pipeline.
- [ ] Cross-links use Sprint 18 canonical pipeline.
- [ ] Connector failure creates no negative identity evidence.
- [ ] Match policy/version decision documented.

## Graph and Clustering

- [ ] Material new evidence scopes recalculation to affected candidates.
- [ ] Cluster rebuild is bounded.
- [ ] Duplicate observations do not rebuild everything.
- [ ] Cluster semantics remain non-authoritative.

## Security

- [ ] Command-injection tests pass.
- [ ] Cross-user run access blocked.
- [ ] Cross-user observation access blocked.
- [ ] Cross-user session-reference access blocked.
- [ ] Feature-disabled zero execution verified.
- [ ] Consent-denied zero execution verified.
- [ ] Session-unavailable zero execution verified.

## Privacy

- [ ] Runs exported appropriately.
- [ ] Observations exported appropriately.
- [ ] Secrets excluded from export.
- [ ] User-scoped connector data deleted/shredded.
- [ ] Temporary artifacts removed.
- [ ] Session revocation/deletion follows ownership model.

## Regression

- [ ] Sprint 18 enrichment/clustering intact.
- [ ] Sprint 17 match engine deterministic.
- [ ] Sprint 16 Maigret intact.
- [ ] Sprint 15 Identity Anchor intact.
- [ ] Sprint 14 zero-egress boundary intact.
- [ ] PDSS semantics unchanged.
- [ ] Frontend build passes.

Release gate:

```text
P0 = 0
P1 = 0 or explicitly accepted through documented engineering decision
```

---

# 76. GO / NO-GO Gate for Sprint 20

## GO

Proceed when:

```text
OSINTgram is optional and isolated
connector version is pinned
no arbitrary commands are exposed
session secrets are protected
no raw secrets enter queues/logs/APIs
connector execution is bounded
candidate deduplication remains user-scoped
multi-connector provenance is preserved
cross-connector double counting is prevented
OSINTgram output remains candidate/evidence level
avatar and cross-link observations reuse Sprint 18 safety boundaries
privacy lifecycle passes
full regression state is accurately reported
P0 = 0
P1 = 0 or explicitly accepted
```

## CONDITIONAL GO

Only for documented P2/P3 limitations that do not affect:

```text
secret security
cross-user isolation
platform access-control boundaries
evidence integrity
privacy
determinism
```

## NO-GO

Do not begin Sprint 20 with:

```text
plaintext session secrets in application tables
secrets in Celery messages
secrets in logs or API responses
arbitrary OSINTgram command execution
shell=True
platform access-control bypass
unbounded social graph crawling
global cross-user candidate correlation
connector output auto-confirming identity
broken privacy deletion
unresolved P0
unaccepted P1
```

---

# 77. Recommended Sprint 20 Direction

After Maigret, deterministic matching, cross-links, avatar reuse, clustering, and OSINTgram are stable, Sprint 20 should focus on:

```text
Unified Multi-Connector Orchestration
+
Evidence Freshness & Revalidation
+
Connector Health / Budget Policy
+
Incremental Identity Reassessment
```

Target:

```text
Identity Anchor
        ↓
Connector Planner
   ├── Maigret
   ├── OSINTgram
   └── future approved connectors
        ↓
Normalized Connector Observations
        ↓
Canonical Evidence Graph
        ↓
Freshness / Staleness Policy
        ↓
Incremental Deterministic Reassessment
        ↓
Human Review
```

Sprint 20 should not simply add more OSINT tools without first making connector orchestration, freshness, budgets, and evidence lifecycle canonical.

---

# 78. Final Sprint 19 Principle

OSINTgram is a source of observations, not a source of truth.

The system should be able to say:

```text
OSINTgram observed this Instagram profile.

Maigret may also have discovered the same canonical profile.

Those connector observations preserve separate provenance but do not become duplicate identity facts.

Any avatar or cross-link information is processed through the existing Sprint 18 safety boundaries.

The deterministic Match Engine evaluates the resulting canonical evidence.

The user still decides whether the profile is theirs.
```

Target architecture after Sprint 19:

```text
VERIFIED IDENTITY ANCHOR
        ↓
BOUNDED CONNECTOR DISCOVERY
   ├── MAIGRET
   └── OSINTGRAM
        ↓
MULTI-CONNECTOR PROVENANCE
        ↓
CANONICAL EVIDENCE
   ├── USERNAME
   ├── CROSS-LINK
   ├── NON-BIOMETRIC AVATAR REUSE
   ├── RELATIONSHIP CONTEXT
   ├── POSITIVE / NEGATIVE
   ├── RELIABILITY
   └── INDEPENDENCE
        ↓
DETERMINISTIC MATCH ENGINE
        ↓
CONSERVATIVE IDENTITY CLUSTERS
        ↓
HUMAN REVIEW
```

Sprint 19 is complete when DigiZafe can optionally execute OSINTgram through a secure, bounded, secret-safe connector boundary; normalize its observations into the existing candidate and evidence architecture; preserve multi-connector provenance without double counting; reuse Sprint 18 enrichment safety controls; maintain privacy and cross-user isolation; and never treat authenticated connector output as automatic identity verification.

---

**End of Sprint 19 Implementation Guide**
