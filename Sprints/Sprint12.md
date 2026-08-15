# DigiZafe --- Sprint 12 Implementation Guide

**Sprint:** 12 --- Optional Free Residual ML\
**Document version:** 1.0\
**Prerequisite:** Pre-Sprint 12 Consolidation & Required Fixes completed
and green\
**Architecture baseline:** Sprint 0--11 hardened baseline\
**AI narrative provider:** Groq API with mandatory deterministic
grounded fallback\
**ML role:** Optional, bounded, explainable auxiliary signal only

> Sprint 12 must not begin until all Pre-Sprint 12 P0/P1 gates,
> migration checks, security tests, contract tests, frontend build, and
> Sprint 0--11 regression tests pass.
>
> The deterministic DigiZafe system remains authoritative. Residual ML
> must be removable without breaking verification, discovery, evidence,
> PDSS, recommendations, remediation, privacy, or explainability.

------------------------------------------------------------------------

# 1. Sprint Goal

Add an **optional residual ML component** that evaluates whether a
small, free, reproducible model can improve risk prioritization beyond
the deterministic PDSS baseline.

The model must not replace PDSS.

The intended architecture is:

``` text
Verified identity
      ↓
Consented discovery
      ↓
Normalized evidence + provenance
      ↓
Deterministic PDSS v1.1+
      ↓
Deterministic explanation
      ↓
Optional residual ML feature extraction
      ↓
Optional bounded residual signal
      ↓
Side-by-side evaluation / auxiliary flag
      ↓
Human-readable explanation
```

Not:

``` text
raw evidence
→ opaque model
→ authoritative risk score
```

------------------------------------------------------------------------

# 2. Non-Negotiable Constraints

Sprint 12 must preserve:

-   G1 self-only scanning;
-   verified identifiers only;
-   explicit consent before consent-gated egress;
-   centralized egress security;
-   deterministic PDSS as the authoritative score;
-   Confirmed and Possible risk tracks;
-   provenance and evidence-quality semantics;
-   user-directed remediation;
-   privacy controls and deletion;
-   no paid dependency required for residual ML;
-   no raw evidence dumps as model features;
-   no secrets, passwords, tokens, MFA secrets, or verification secrets
    in training data;
-   no automatic retraining from production user data;
-   no silent model downloads;
-   no hidden remote inference;
-   no model output that bypasses explanation or audit;
-   no ML output that directly triggers remediation.

Groq remains the configured **narrative AI provider** only. Groq is not
the Sprint 12 residual-risk model and is not required to train or
execute the residual model.

------------------------------------------------------------------------

# 3. Sprint 12 Scope

## Included

-   versioned deterministic feature extraction;
-   optional residual model interface;
-   free local CPU inference;
-   reproducible training/evaluation pipeline;
-   baseline comparison against deterministic PDSS;
-   bounded residual output;
-   abstention / low-confidence behavior;
-   model registry and model card;
-   evaluation report;
-   API exposure of auxiliary ML status;
-   privacy-safe audit metadata;
-   tests for determinism, isolation, boundedness, and fallback;
-   feature flag to disable the entire ML component.

## Excluded

-   replacing PDSS with ML;
-   LLM-based scoring;
-   Groq-based risk scoring;
-   automatic online learning;
-   training directly on live production user data;
-   scraping new sources for model training;
-   paid ML APIs;
-   GPU requirement;
-   autonomous remediation;
-   hidden user profiling;
-   cross-user feature leakage;
-   use of protected/sensitive personal traits;
-   unbounded score modification;
-   silent model updates;
-   remote telemetry required for inference.

------------------------------------------------------------------------

# 4. Feature Flags and Configuration

Add or extend canonical settings only after repository preflight.

``` bash
FEATURE_RESIDUAL_ML=false

RESIDUAL_ML_MODEL_VERSION=residual-risk-v1
RESIDUAL_ML_MODEL_PATH=/app/models/residual-risk-v1.joblib
RESIDUAL_ML_FEATURE_SCHEMA_VERSION=residual-features-v1

RESIDUAL_ML_MAX_ABS_DELTA=5.0
RESIDUAL_ML_MIN_CONFIDENCE=0.70
RESIDUAL_ML_TIMEOUT_MS=250
RESIDUAL_ML_FAIL_OPEN_TO_DETERMINISTIC=true
```

Default behavior:

``` text
FEATURE_RESIDUAL_ML=false
→ no model load required
→ no ML inference required
→ deterministic product works normally
```

If the model file is missing, corrupt, incompatible, or times out:

``` text
deterministic PDSS remains available
ML auxiliary result = unavailable/abstained
core workflow continues
```

------------------------------------------------------------------------

# 5. Mandatory Repository Preflight

Before creating new files:

1.  Search for existing ML placeholders from Sprint 0.
2.  Search for existing score DTOs and model-version fields.
3.  Search for an existing model registry.
4.  Search for canonical `ExposureLayer`, finding status, confidence,
    and PDSS contracts.
5.  Reuse existing shared contracts rather than duplicating them.
6.  Confirm the hardened PDSS model version and layer-neutral semantics.
7.  Confirm the Groq narrative service remains separate from residual
    ML.
8.  Confirm no Sprint 12 code requires a Groq API key.

If a proposed implementation conflicts with frozen architecture, file a
CBN.

------------------------------------------------------------------------

# 6. Recommended File Layout

Adapt to the existing repository rather than duplicating equivalent
modules.

``` text
ml/
├── README.md
├── features/
│   ├── __init__.py
│   └── residual_features.py
├── training/
│   ├── __init__.py
│   ├── build_dataset.py
│   ├── train_residual.py
│   └── evaluate_residual.py
├── models/
│   └── .gitkeep
└── reports/
    └── .gitkeep

backend/app/ml/
├── __init__.py
├── contracts.py
├── feature_adapter.py
├── model_loader.py
├── residual_service.py
└── registry.py

backend/tests/ml/
├── test_feature_schema.py
├── test_model_loader.py
├── test_residual_service.py
├── test_bounded_output.py
├── test_abstention.py
├── test_cross_user_isolation.py
└── test_deterministic_fallback.py

docs/model-cards/
└── residual-risk-v1.md

docs/evaluation/
└── residual-risk-v1-evaluation.md
```

------------------------------------------------------------------------

# 7. Feature Contract

Create one versioned feature schema.

Recommended categories:

``` text
finding counts by canonical finding kind
confirmed finding count
possible finding count
confidence distribution summaries
sensitivity summaries
discoverability summaries
linkability summaries
impact summaries
temporal summaries
credential-risk indicators
source diversity count
evidence-quality summaries
remediation-status summaries
deterministic PDSS component summaries
```

## Prohibited features

Do not use:

-   raw email addresses;
-   raw usernames;
-   raw domains unless transformed into a non-identifying structural
    feature explicitly justified;
-   names;
-   passwords;
-   password hashes;
-   access tokens;
-   refresh tokens;
-   MFA secrets;
-   verification tokens;
-   raw page bodies;
-   raw breach dumps;
-   raw evidence blobs;
-   Groq prompts or responses;
-   user IDs as predictive features;
-   protected or sensitive personal traits.

## Layer rule

Exposure layer may be retained for evaluation/provenance features only
if justified, but the model must not learn a simplistic rule equivalent
to:

``` text
constrained_dark = automatically worse
```

Evaluate for layer-driven shortcut learning.

Preferred initial model:

``` text
exclude layer as a predictive feature
```

or encode only carefully justified aggregate provenance features and
report ablation results.

------------------------------------------------------------------------

# 8. Feature Schema Versioning

Define a contract similar to:

``` python
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResidualFeatureVector:
    schema_version: str
    values: Mapping[str, float]
```

Requirements:

-   stable feature names;
-   deterministic ordering before model input;
-   explicit missing-value policy;
-   no silent feature addition;
-   schema version stored with every inference record;
-   model declares compatible schema version;
-   incompatible schema causes abstention, not guessed inference.

------------------------------------------------------------------------

# 9. Residual Target Design

The residual model must predict an **auxiliary residual or review
signal**, not the authoritative PDSS.

Preferred research formulation:

``` text
target residual
=
observed/evaluated risk target
-
deterministic PDSS baseline estimate
```

If no defensible labeled target exists, do not fabricate one.

In that case Sprint 12 may implement:

``` text
feature pipeline
+ model interface
+ synthetic/test fixtures
+ offline evaluation harness
```

while keeping production ML disabled.

The project must not claim ML improvement without evaluation evidence.

------------------------------------------------------------------------

# 10. Training Data Policy

## Allowed

-   synthetic fixtures;
-   manually curated research fixtures;
-   de-identified approved benchmark data;
-   explicitly consented research data if the governing architecture
    permits it;
-   deterministic generated test cases.

## Not allowed by default

-   automatic export of production user records into training data;
-   raw evidence;
-   secrets;
-   direct identifiers;
-   cross-user aggregation without an approved privacy design;
-   third-party datasets with unclear legal provenance.

## Required dataset manifest

Every training dataset must have:

``` text
dataset name
dataset version
source/provenance
license or usage basis
creation date
feature schema version
row count
label definition
known limitations
privacy review status
```

------------------------------------------------------------------------

# 11. Initial Model Choice

Use a small free CPU model.

Preferred starting point:

``` text
scikit-learn HistGradientBoostingRegressor
```

or, if evaluation supports a simpler model:

``` text
Ridge
LogisticRegression
RandomForest
```

Choose the simplest model that performs adequately.

Do not add a large deep-learning framework unless evaluation proves it
necessary.

Model selection criteria:

-   free;
-   CPU-friendly;
-   reproducible;
-   serializable;
-   bounded operational cost;
-   explainable enough for auxiliary use;
-   compatible with the project license and deployment environment.

------------------------------------------------------------------------

# 12. Training Reproducibility

Training must use:

-   pinned dependencies;
-   fixed random seed;
-   versioned feature schema;
-   versioned dataset manifest;
-   versioned hyperparameters;
-   saved evaluation metrics;
-   model checksum;
-   model card.

Example metadata:

``` json
{
  "model_version": "residual-risk-v1",
  "feature_schema_version": "residual-features-v1",
  "random_seed": 42,
  "training_dataset_version": "research-fixtures-v1",
  "library": "scikit-learn",
  "model_sha256": "..."
}
```

Do not overwrite a released model artifact in place.

------------------------------------------------------------------------

# 13. Model Registry

Create or extend a canonical registry.

Example:

``` python
@dataclass(frozen=True)
class ResidualModelMetadata:
    model_version: str
    feature_schema_version: str
    model_path: str
    sha256: str
    enabled: bool
    max_abs_delta: float
    min_confidence: float
```

The loader must verify:

-   expected model version;
-   feature schema compatibility;
-   checksum;
-   supported artifact type.

Failure:

``` text
model unavailable
→ log safe diagnostic
→ return abstention
→ deterministic PDSS unaffected
```

------------------------------------------------------------------------

# 14. Inference Contract

Recommended output:

``` python
@dataclass(frozen=True)
class ResidualInference:
    status: str
    model_version: str | None
    feature_schema_version: str
    residual_delta: float | None
    bounded_delta: float | None
    confidence: float | None
    abstained: bool
    reason: str | None
```

Allowed statuses:

``` text
disabled
unavailable
abstained
evaluated
```

The model must never return an authoritative replacement score.

------------------------------------------------------------------------

# 15. Bounded Output

Even when evaluated, residual output must be bounded.

Example:

``` text
raw residual = model output

bounded residual
=
clamp(
  raw residual,
  -RESIDUAL_ML_MAX_ABS_DELTA,
  +RESIDUAL_ML_MAX_ABS_DELTA
)
```

The primary API should continue to expose:

``` text
authoritative_score = deterministic PDSS
```

Optional auxiliary presentation:

``` text
deterministic PDSS: 67
ML residual signal: +2.1
ML status: evaluated
```

Do not silently publish:

``` text
final score = 69.1
```

as if it were the deterministic PDSS.

Any future combined score requires a separate reviewed scoring-model
version and model card.

------------------------------------------------------------------------

# 16. Abstention

The residual model must abstain when:

-   feature schema is incompatible;
-   model file is missing;
-   checksum fails;
-   inference errors;
-   inference times out;
-   confidence is below threshold;
-   required features are unavailable;
-   feature values are outside approved validity bounds.

Abstention is a valid result.

``` text
ML abstained
≠ product failure
```

------------------------------------------------------------------------

# 17. Backend Residual Service

Recommended behavior:

``` text
request auxiliary ML evaluation
        ↓
feature flag enabled?
        ├─ no → disabled
        ↓ yes
load verified model
        ├─ fail → unavailable
        ↓
build feature vector from durable approved facts
        ├─ invalid → abstained
        ↓
run local CPU inference with timeout
        ├─ fail → abstained/unavailable
        ↓
bound output
        ↓
return auxiliary result
```

The service must not:

-   call Groq;
-   call external ML APIs;
-   perform connector discovery;
-   read another user's records;
-   mutate PDSS history;
-   trigger remediation.

------------------------------------------------------------------------

# 18. Persistence

Persist only what is necessary for reproducibility and audit.

Recommended inference record fields:

``` text
id
user_id
score_record_id
model_version
feature_schema_version
status
raw_delta
bounded_delta
confidence
abstention_reason
created_at
```

Do not persist the full raw feature vector unless explicitly required
and privacy-reviewed.

Prefer:

``` text
feature_vector_hash
+ schema version
+ source score/finding snapshot references
```

where reproducibility requirements permit.

Apply existing RLS/user-isolation policy.

------------------------------------------------------------------------

# 19. API

Extend existing versioned API contracts rather than creating a parallel
scoring API.

Possible endpoint:

``` text
POST /api/v1/scores/{score_id}/residual-evaluation
GET  /api/v1/scores/{score_id}/residual-evaluation
```

Or include the optional result in the existing score detail DTO.

Recommended response:

``` json
{
  "authoritative_score": 67.0,
  "authoritative_model_version": "pdss-v1.1.0",
  "residual_ml": {
    "status": "evaluated",
    "model_version": "residual-risk-v1",
    "feature_schema_version": "residual-features-v1",
    "bounded_delta": 2.1,
    "confidence": 0.82,
    "abstained": false
  }
}
```

The API must make clear that the residual result is auxiliary.

------------------------------------------------------------------------

# 20. Frontend UX

Only show residual ML when:

``` text
FEATURE_RESIDUAL_ML=true
and
the backend exposes a result
```

Recommended copy:

``` text
Experimental ML signal

DigiZafe's main risk score remains deterministic and explainable.
This optional model estimates whether the deterministic score may
understate or overstate risk based on the current feature pattern.
```

Display:

-   status;
-   bounded residual direction/magnitude;
-   confidence if meaningful;
-   model version;
-   experimental label;
-   explanation of abstention.

Do not:

-   replace the main PDSS gauge;
-   hide deterministic explanations;
-   imply certainty;
-   label ML as "AI truth";
-   use Groq branding for residual scoring.

------------------------------------------------------------------------

# 21. Explainability

At minimum, provide model-level and inference-level explanation
appropriate to the selected model.

Possible methods:

-   coefficients for linear models;
-   permutation importance for offline evaluation;
-   bounded feature contribution summaries where technically valid;
-   simple reason codes for abstention.

Avoid explanations that overclaim causal meaning.

The user-facing explanation must distinguish:

``` text
deterministic PDSS explanation
```

from:

``` text
experimental residual ML explanation
```

Groq may optionally turn already-approved structured explanation facts
into natural language through the existing narrative service, but:

-   Groq must not calculate the residual score;
-   the structured deterministic/ML facts remain authoritative;
-   deterministic narrative fallback must remain available.

------------------------------------------------------------------------

# 22. Evaluation Plan

Sprint 12 is successful only if it evaluates whether ML adds value.

Compare:

``` text
deterministic baseline
vs
deterministic baseline + residual signal
```

Use appropriate metrics for the actual target.

Possible metrics:

-   MAE;
-   RMSE;
-   calibration error;
-   precision/recall for review flags;
-   AUROC only where the target is genuinely binary;
-   abstention coverage;
-   error by confidence band.

Also evaluate:

-   performance by finding category;
-   Confirmed vs Possible track;
-   sparse vs dense evidence;
-   source diversity;
-   layer groups for shortcut/bias analysis;
-   temporal slices where available.

Do not report only one aggregate metric.

------------------------------------------------------------------------

# 23. Required Baselines

At minimum compare against:

``` text
Baseline A: deterministic PDSS only
Baseline B: mean/constant residual
Baseline C: simple linear residual model
Candidate: selected residual model
```

A complex model must beat simpler baselines meaningfully before
adoption.

If it does not:

``` text
keep FEATURE_RESIDUAL_ML=false
document negative result
Sprint 12 can still be considered a valid research outcome
```

------------------------------------------------------------------------

# 24. Leakage Prevention

Training/evaluation splits must prevent leakage.

Do not randomly split rows if multiple rows can represent the same:

-   user;
-   identity cluster;
-   finding family;
-   source event;
-   synthetic scenario template.

Prefer grouped splitting by the highest-risk leakage unit.

Document the split strategy.

------------------------------------------------------------------------

# 25. Confidence and Calibration

Do not invent a confidence value.

If the selected model does not naturally provide a defensible confidence
estimate:

-   use `confidence = null`; or
-   implement a separately evaluated uncertainty method.

The absence of confidence is better than fake precision.

`RESIDUAL_ML_MIN_CONFIDENCE` applies only when a calibrated/defensible
confidence measure exists.

------------------------------------------------------------------------

# 26. Groq Narrative Integration Boundary

The existing Groq integration remains separate.

Allowed flow:

``` text
PDSS structured explanation
+
optional residual structured result
        ↓
privacy-minimized narrative payload
        ↓
Groq, when configured/authorized
        ↓
validated narrative
```

Fallback:

``` text
Groq unavailable / disabled / rate-limited / invalid
        ↓
deterministic grounded narrative
```

Never send to Groq:

-   model artifact;
-   training dataset;
-   raw evidence dump;
-   passwords;
-   tokens;
-   MFA secrets;
-   verification secrets;
-   unnecessary direct identifiers.

The Groq API key remains backend-only.

------------------------------------------------------------------------

# 27. Security Requirements

Residual ML must preserve:

-   per-user isolation;
-   RLS where persisted;
-   no arbitrary model-path loading from user input;
-   no user-supplied pickle/joblib artifacts;
-   checksum verification for trusted model artifacts;
-   fixed model registry;
-   bounded CPU/time use;
-   no shell execution;
-   no network requirement for local inference.

Because Python pickle/joblib-style formats can execute code during
deserialization, only load model artifacts produced by the trusted
project pipeline and matched against the configured checksum/registry.

Never accept uploaded model files through the public API.

------------------------------------------------------------------------

# 28. Required Tests

## Unit tests

``` text
feature extraction is deterministic
feature names/order are stable
schema mismatch abstains
missing model returns unavailable
checksum mismatch returns unavailable
disabled feature does not load model
output is bounded
low confidence abstains when confidence is supported
invalid values abstain
```

## Security tests

``` text
user A cannot evaluate user B's score
user-controlled model path is impossible
untrusted uploaded model cannot be loaded
model failure does not expose filesystem paths/secrets
Groq API key is not used by residual service
```

## Regression tests

``` text
FEATURE_RESIDUAL_ML=false
→ Sprint 0–11 behavior unchanged

model missing
→ deterministic PDSS still works

model corrupt
→ deterministic PDSS still works

inference timeout
→ deterministic PDSS still works

ML abstains
→ recommendations/remediation still work
```

## Scoring semantics tests

``` text
residual result does not mutate historical PDSS
residual result does not replace authoritative score
layer alone cannot force a positive residual
identical deterministic inputs produce identical feature vectors
```

------------------------------------------------------------------------

# 29. Training Pipeline Commands

Provide repository commands similar to:

``` bash
python -m ml.training.build_dataset \
  --manifest ml/data/research-fixtures-v1.json \
  --output .artifacts/residual-dataset.parquet

python -m ml.training.train_residual \
  --dataset .artifacts/residual-dataset.parquet \
  --model-version residual-risk-v1 \
  --seed 42 \
  --output .artifacts/residual-risk-v1.joblib

python -m ml.training.evaluate_residual \
  --dataset .artifacts/residual-dataset.parquet \
  --model .artifacts/residual-risk-v1.joblib \
  --output docs/evaluation/residual-risk-v1-evaluation.md
```

Adapt formats to installed dependencies. Do not add a heavy dependency
solely for Parquet if the repository does not already support it; CSV or
another reproducible format is acceptable.

------------------------------------------------------------------------

# 30. Model Card

Create:

``` text
docs/model-cards/residual-risk-v1.md
```

Required sections:

``` text
Model name/version
Purpose
Non-purpose
Authoritative-system relationship
Feature schema
Training data provenance
Target definition
Algorithm
Hyperparameters
Evaluation metrics
Baseline comparison
Abstention behavior
Output bounds
Known limitations
Privacy considerations
Security considerations
Layer-shortcut analysis
Confirmed/Possible behavior
Deployment requirements
Rollback procedure
```

State prominently:

> This model does not replace DigiZafe's deterministic PDSS. It provides
> an optional bounded auxiliary residual signal.

------------------------------------------------------------------------

# 31. Evaluation Report

Create:

``` text
docs/evaluation/residual-risk-v1-evaluation.md
```

Include:

-   dataset manifest/version;
-   split methodology;
-   leakage controls;
-   baseline metrics;
-   candidate metrics;
-   confidence intervals where feasible;
-   subgroup/slice analysis;
-   error analysis;
-   abstention coverage;
-   layer shortcut analysis;
-   limitations;
-   go/no-go recommendation.

The report may conclude:

``` text
NO-GO for production enablement
```

That is an acceptable Sprint 12 outcome.

------------------------------------------------------------------------

# 32. Rollout Strategy

## Phase 1 --- Offline only

``` text
FEATURE_RESIDUAL_ML=false
```

Train and evaluate only.

## Phase 2 --- Shadow evaluation

If approved:

``` text
model runs internally
result not shown to user
deterministic PDSS remains authoritative
```

Measure stability and failure behavior.

## Phase 3 --- Experimental user-visible auxiliary signal

Only after evaluation and review:

``` text
explicit experimental label
bounded signal
deterministic score remains primary
```

Do not skip directly to user-visible production enablement.

------------------------------------------------------------------------

# 33. Rollback

Rollback must be immediate:

``` bash
FEATURE_RESIDUAL_ML=false
```

After disabling:

-   scoring still works;
-   explanations still work;
-   recommendations still work;
-   remediation still works;
-   Groq/deterministic narrative still works;
-   stored historical residual records may remain for audit but are not
    used.

------------------------------------------------------------------------

# 34. Suggested Commit Plan

``` bash
git commit -m "feat(ml): add versioned residual feature schema"
git commit -m "feat(ml): add trusted model registry and loader"
git commit -m "feat(ml): add bounded abstaining residual inference service"
git commit -m "feat(api): expose optional residual evaluation metadata"
git commit -m "feat(frontend): add experimental residual signal UX"
git commit -m "test(ml): add determinism boundedness isolation and fallback tests"
git commit -m "docs(ml): add residual model card and evaluation report"
```

------------------------------------------------------------------------

# 35. Sprint 12 Definition of Done

## Prerequisite gate

-   [ ] All Pre-Sprint 12 P0/P1 fixes are complete.
-   [ ] Sprint 0--11 regression suite is green.
-   [ ] Fresh database migration succeeds.
-   [ ] Expected Alembic head state is verified.
-   [ ] Egress security tests are green.
-   [ ] Groq narrative fallback behavior is green.
-   [ ] Memory-only frontend auth behavior is green.

## ML architecture

-   [ ] Residual ML is disabled by default.
-   [ ] Deterministic PDSS remains authoritative.
-   [ ] Feature schema is versioned.
-   [ ] Model version is explicit.
-   [ ] Model artifact is trusted and checksum-verified.
-   [ ] Model loading does not accept user-controlled paths.
-   [ ] Inference requires no network.
-   [ ] Groq is not used for residual scoring.

## Privacy and security

-   [ ] No direct identifiers are required as predictive features.
-   [ ] No secrets/raw evidence are training features.
-   [ ] No automatic production-user training pipeline exists.
-   [ ] Per-user isolation is tested.
-   [ ] Model failure cannot break the deterministic workflow.

## Output semantics

-   [ ] Residual output is bounded.
-   [ ] Abstention is supported.
-   [ ] Missing/corrupt model falls back safely.
-   [ ] Historical PDSS is never overwritten.
-   [ ] API clearly distinguishes authoritative PDSS from experimental
    ML.
-   [ ] Layer alone cannot determine severity or force a residual
    result.

## Evaluation

-   [ ] Dataset manifest exists.
-   [ ] Leakage-resistant split is documented.
-   [ ] Deterministic and simple baselines are evaluated.
-   [ ] Candidate model is compared against baselines.
-   [ ] Slice analysis is completed.
-   [ ] Layer shortcut analysis is completed.
-   [ ] Model card exists.
-   [ ] Evaluation report includes a go/no-go recommendation.

## Product regression

-   [ ] Verification works.
-   [ ] Surface discovery works.
-   [ ] Amber consent gates work.
-   [ ] PDSS works with ML disabled.
-   [ ] Recommendations work with ML disabled.
-   [ ] Remediation works with ML disabled.
-   [ ] Privacy/export works with ML disabled.
-   [ ] Groq narrative works when configured.
-   [ ] Deterministic narrative works when Groq fails.
-   [ ] Frontend build passes.
-   [ ] Backend tests pass.
-   [ ] Security tests pass.
-   [ ] Regression tests pass.

------------------------------------------------------------------------

# 36. Sprint Completion Rule

Sprint 12 is complete when DigiZafe can demonstrate one of two valid
outcomes.

## Outcome A --- Residual ML adds measurable value

``` text
evaluation supports improvement
+ leakage controls pass
+ privacy/security gates pass
+ model remains bounded and auxiliary
→ eligible for controlled shadow rollout
```

## Outcome B --- Residual ML does not add sufficient value

``` text
evaluation does not justify enablement
→ keep FEATURE_RESIDUAL_ML=false
→ document the negative result
→ deterministic DigiZafe remains the production system
```

Both outcomes are scientifically and engineering-valid.

------------------------------------------------------------------------

# 37. Final Architecture After Sprint 12

``` text
User
  ↓
Authentication
  ↓
Verified identifier ownership
  ↓
Consent
  ↓
Surface / Deep / Constrained-Dark discovery
  ↓
Normalized evidence + provenance
  ↓
Confirmed / Possible risk tracks
  ↓
Deterministic PDSS v1.1+
  ↓
Explainable recommendations
  ↓
User-directed remediation
  ↓
Re-verification and re-scoring
  ↓
Optional bounded residual ML signal
  ↓
Grounded narrative
    ├─ Groq when configured and authorized
    └─ deterministic fallback always available
```

The authoritative safety boundary remains deterministic, consented,
explainable, and user-controlled.

**End of Sprint 12 Implementation Guide.**
