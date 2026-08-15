# DigiZafe: Code Knowledge Base & API Deep Dive

## 1. IMPORTANT FILES

### 🔴 `backend/app/services/identity_match_engine.py`
* **Purpose**: Core algorithm for correlating disconnected OSINT data into unified user profiles.
* **Classes**: `IdentityMatchEngine`
* **Functions**: `assess_candidate`, `_generate_fingerprint`, `_map_explanation`, `_calculate_provenance_fingerprint`.
* **Inputs**: `user_id`, `candidate_id` (representing raw OSINT data).
* **Outputs**: `IdentityMatchAssessment` object detailing score and confidence band.
* **Dependencies**: `IdentityEvidenceService`, `IdentityCollisionPolicy`, PostgreSQL.
* **Callers**: `candidate_discovery_service.py`, Celery enrichment tasks.
* **Important Logic**: Uses cryptographic hashing (`hashlib.sha256`) of provenance data to skip redundant calculations. Implements an evidence strength-capping mechanism (`username_cap`) based on collision risk (e.g., John Smith vs rare username).

### 🔴 `backend/app/remediation/runners/playwright_runner.py`
* **Purpose**: Executes automated privacy opt-out requests using a headless Chromium browser.
* **Classes**: `RunnerResult`, `PlaywrightBrokerRunner`
* **Functions**: `run_broker`, `_playwright_direct_form`, `_try_capsolver`, `verify_not_listed`.
* **Inputs**: `broker` (dict with selector mappings), `profile` (User PII object).
* **Outputs**: `RunnerResult` indicating `SUBMITTED`, `CAPTCHA_NEEDED`, or `MANUAL_NEEDED`.
* **Dependencies**: `playwright`, Target DOMs.
* **Callers**: `app.tasks.remediation_tasks.execute_job`.
* **Important Logic**: Scans DOM content for `recaptcha`, `hcaptcha`, or `cf-turnstile`. Best-effort JavaScript injection to bypass basic text areas if a solver token is available. Heavily utilizes hard timeout limits to prevent stuck worker nodes.

### 🔴 `backend/app/main.py`
* **Purpose**: FastAPI Application initialization and routing.
* **Classes**: None.
* **Functions**: `lifespan`, `root`, `metrics`.
* **Inputs**: HTTP requests.
* **Outputs**: JSON HTTP responses.
* **Dependencies**: `FastAPI`, `structlog`, `CORSMiddleware`.
* **Callers**: Uvicorn ASGI server.
* **Important Logic**: Uses Python 3.11+ `@asynccontextmanager` for lifespan events (loading static catalogs into memory on startup). Configures global exception handlers for `RequestValidationError` to standardize error shapes.

---

## 2. CORE CLASSES

### `IdentityMatchEngine`
* **Responsibility**: Calculates whether raw OSINT findings actually belong to the authenticated user.
* **Attributes**: `ENGINE_VERSION` (int), `POLICY_VERSION` (int).
* **Methods**: 
  * `assess_candidate`: Orchestrates DB lookups and executes scoring.
  * `_map_explanation`: Generates human-readable localized text explaining *why* a score was given (e.g. "You previously dismissed this candidate").
* **Lifecycle**: Instantiated per-request or per-task. Uses dependency-injected `AsyncSession`.
* **Dependencies**: `IdentityCollisionPolicy` (static methods), `IdentityEvidenceService`.
* **Consumers**: The `/api/v1/identity` routes, asynchronous background OSINT ingestion tasks.

### `PlaywrightBrokerRunner`
* **Responsibility**: "Action Engine" for data removal.
* **Attributes**: `settings` (Pydantic BaseSettings).
* **Methods**: 
  * `run_broker`: Decides if a site needs manual intervention, CAPTCHA, or can be auto-filled.
  * `verify_not_listed`: Boots Chromium to search a site to ensure data is actually removed.
* **Lifecycle**: Ephemeral. Created inside a Celery task context. Tears down the Chromium context in a `finally` block to prevent zombie processes.
* **Dependencies**: `async_playwright`.
* **Consumers**: Remediation Celery Workers.

---

## 3. CORE FUNCTIONS

### `assess_candidate(self, user_id: UUID, candidate_id: UUID)`
* **Purpose**: Evaluate a newly discovered data profile against a user's verified identity.
* **Parameters**: `user_id`, `candidate_id`.
* **Return value**: `IdentityMatchAssessment` SQLAlchemy Model.
* **Algorithm**:
  1. Hashing provenance to check cache (fingerprint).
  2. Loading User Anchor, Aliases, and Candidate DB rows.
  3. Scoring positive evidence (e.g. Strong = 70pts, Moderate = 40pts).
  4. Capping username-only evidence to prevent false positives.
  5. Applying overrides (Explicit User Dismissal sets score to 0).
  6. Saving explanation and returning.
* **Side effects**: Writes a new `IdentityMatchAssessment` row to PostgreSQL. Modifies `is_current=False` on old assessments.
* **Errors**: Raises `ValueError` if candidate or anchor is missing.
* **Called by**: Background scan processors.
* **Calls**: `self._calculate_provenance_fingerprint`, `evidence_service.collect_evidence`.

---

## 4. API DEEP DIVE

### `POST /api/v1/identity/graph/rebuild`
* **Route**: `/api/v1/identity/graph/rebuild`
* **Method**: `POST`
* **Request**: Empty body. Relies entirely on `Authorization: Bearer <token>`.
* **Validation**: Fastapi `Depends(CurrentUser)` validates JWT and ensures the user exists.
* **Execution Flow**: 
  1. Router injects `IdentityService`.
  2. Service fetches all verified `IdentityAnchor` details for the user.
  3. Service queries all OSINT data.
  4. Recalculates pairwise deciban/F-S linkages.
  5. Constructs node/edge JSON graph.
* **Database Operations**: Heavily read-intensive (multiple JOINs on anchors and findings).
* **External Calls**: None (purely mathematical DB operation).
* **Response**: `IdentityGraphPublic` (Pydantic model containing nodes and edges).
* **Security**: Enforced via `CurrentUser` dependency (Row-Level Security boundary).

---

## 5. DATABASE DEEP DIVE

### Table: `observation_finding`
* **Fields**:
  * `id` (UUID, Primary Key)
  * `scan_id` (UUID, FK to `scan.id`) - Associates finding with the chronological event.
  * `connector_id` (String) - E.g. "have_i_been_pwned".
  * `raw_data` (JSONB) - Crucial field. OSINT data is unstructured and changes schemas often; JSONB allows flexible storage without DB migrations.
  * `severity` (String) - High, Medium, Low.
* **Relationships**: Belongs to `Scan`. Has many `RemediationJob`.
* **Constraints**: Unique constraint likely on `(scan_id, raw_data_hash)` to prevent duplicate ingestion.
* **Indexes**: GIN Index heavily recommended on `raw_data` for querying specific JSON keys. B-Tree on `scan_id`.
* **Lifecycle**: Created by Celery workers upon OSINT discovery. Rarely modified. Soft-deleted or dropped via data retention policies.

### Table: `identity_match_assessment`
* **Fields**:
  * `id`, `user_id`, `anchor_id`, `candidate_profile_id`
  * `assessment_input_fingerprint` (String) - SHA256 hash. Exists to short-circuit expensive recalculations.
  * `score` (Integer) - The quantified confidence of the match.
  * `assessment_status` (String) - `likely_match`, `insufficient_evidence`, etc.
  * `evidence_snapshot` (JSONB) - Exists for Auditability. If the algorithm changes, we can prove *why* the user was shown this data historically.
* **Relationships**: Maps Candidate Profiles to Verified Identity Anchors.
* **Lifecycle**: Insert-only with `is_current` flagging. Older records are kept for temporal timelines but flagged `is_current=False`.

---

## 6. MIGRATIONS

Located in `backend/app/alembic/versions/`:
* **Schema Evolution**:
  * `001_sprint1_auth.py` -> `002_sprint2_identifiers.py` -> `003_sprint3_connectors.py`.
  * The schema evolved modularly sprint-by-sprint.
* **Major Architectural Changes**:
  * `2ec027d8be5b_add_execution_mode_to_provenance_.py`: Indicates a shift towards tracking *how* data was found (e.g. manual vs automated execution).
  * `c7d13d94607b_sprint25_rls_integrity.py`: Massive architectural security change. Moving from application-layer tenant isolation to Postgres Row-Level Security (RLS) policies.
  * `a5857207f85b_sprint_21_temporal_evidence_and_review_.py`: Shifted the system from a stateless snapshot tool to a temporal state machine (tracking exposure across time).

---

## 7. CODE-TO-CONCEPT MAP

| Concept | File | Class/Function | Explanation |
| ------- | ---- | -------------- | ----------- |
| Auto-Takedown | `playwright_runner.py` | `_playwright_direct_form` | Uses headless Chrome to fill PII into broker forms. |
| Identity Correlation | `identity_match_engine.py` | `assess_candidate` | The math deciding if leaked data belongs to the user. |
| Background Jobs | `worker.py` | `celery_app` | The distributed task engine initialization. |
| Schema Evolution | `alembic/env.py` | `run_migrations_online` | Where SQLAlchemy metadata applies to Postgres. |
| ML Feature Extraction| `residual_features.py` | (Implicit) | Translates DB rows into vectors for `.joblib`. |
| Privacy Narrative | `groq_client.py` | (Implicit API calls) | Summarizes legal risk using an LLM. |

---

## 8. TRACE CRITICAL FLOWS TO SOURCE

**Feature: Submitting an Automated Data Removal Request**
```text
Remediation Feature
→ frontend/src/features/remediation/RemediationPage.tsx (User clicks "Remove")
→ frontend/src/features/remediation/api.ts (React Query mutation)
→ backend/app/api/v1/remediation.py (FastAPI POST route receives request)
→ backend/app/services/remediation_service.py (Validates target & creates job)
→ backend/app/models/remediation.py (Inserts RemediationJob into DB)
→ backend/app/worker.py (Redis queues the job to celery)
→ backend/app/tasks/remediation_tasks.py (Celery executes task)
→ backend/app/remediation/runners/playwright_runner.py (Boots Chromium)
→ Data Broker Website (HTML DOM Interaction)
→ PostgreSQL (Updates job status to SUCCESS/FAILED)
→ frontend/src/features/remediation/RemediationPage.tsx (Polls and shows Success badge)
```

---

## 9. CODE QUESTIONS

*(50 project-specific code-level questions covering deepest internals)*

### Identity Engine (`identity_match_engine.py`)
1. In `_generate_fingerprint`, why are the evidence objects sorted by `evidence_id` before hashing?
2. What happens to the `score` if `has_dismissal` is true? Why?
3. How many independent evidence groups are required to achieve a `likely_match` status if `authoritative_count == 0`?
4. What is the value in points for `strength_class == "strong"`?
5. How does the `IdentityCollisionPolicy` cap username evidence?
6. Why does the engine persist `evidence_snapshot` as JSONB on the Assessment model rather than relying on live joins?
7. How does `_calculate_provenance_fingerprint` determine which `CandidateProvenanceObservation` rows to include?
8. If `assessment_input_fingerprint` matches the cache, does the engine update the `is_current` flag?
9. What `explanation_mapping` rule is triggered when `collision_class == "high_collision"`?
10. Can a user's `explicit_user_confirmation` be overridden by an algorithmic contradiction?

### Remediation Runner (`playwright_runner.py`)
11. What is the exact User-Agent string injected into the Chromium context?
12. How does `run_broker` handle a broker where `method == "manual"`?
13. If `requires_captcha` is true, but `feature_capsolver` is false, what `BrokerOptOutStatus` is returned?
14. How does the system detect CAPTCHAs implicitly if they aren't marked in the broker config?
15. In `_playwright_direct_form`, what occurs if a target DOM element's tag name is `"select"`?
16. How is the `captcha_token` injected into the page DOM? Explain the JS evaluation.
17. If `dry_run=True`, does the code attempt to click the submit button?
18. How does `verify_not_listed` handle a missing `search_url_template`?
19. Why does `verify_not_listed` use a simple string inclusion check for the user's name rather than complex DOM parsing?
20. What specific Playwright error strings trigger a `BrokerOptOutStatus.DEAD` response?

### API & Routing
21. In `main.py`, which three catalog caches are eagerly loaded during the FastAPI `lifespan` event?
22. How is CORS configured, and what settings object governs it?
23. In `identity.py`, what is the HTTP method and status code returned for `/aliases/{alias_id}/revoke`?
24. How does dependency injection of `_svc(db: AsyncSession = Depends(get_db))` isolate tests?
25. What happens if a `RequestValidationError` is thrown in the FastAPI layer? Which file handles it?
26. Are the metrics exposed publicly or behind auth on the `/metrics` endpoint?
27. Why is the OSINTgram router specifically tagged with `tags=["osintgram"]` in `main.py`?
28. How does the `CurrentUser` dependency interact with async SQLAlchemy sessions?
29. If an endpoint requires fetching both an Anchor and Aliases, does the API route execute the SQL or the Service layer?
30. How is the API prefixed? (e.g., `/api/v1`) and where is this defined?

### Database & Models
31. In `models/scan.py`, what does `back_populates="connector_runs"` do in the SQLAlchemy relationship?
32. Why is `raw_data` in `observation_finding` JSONB rather than a structured relational table?
33. How does Alembic migration `c7d13d94607b` implement RLS (Row-Level Security)? Which Postgres features are utilized?
34. In the `RemediationJob` model, how are one-to-many items modeled?
35. What is the difference between `IdentityAnchor` and `IdentityAlias`?
36. Why does the `Score` model keep a history instead of updating a single integer column on the `User`?
37. Does asyncpg handle connection pooling natively, or is SQLAlchemy's pool manager utilized?
38. What cascade delete rules exist when a `User` is deleted?
39. How is the `master.key` file utilized at the ORM layer to encrypt/decrypt sensitive fields?
40. In `orchestration.py`, what is the relationship between an `OrchestrationRun` and a `ConnectorExecutionPlanItem`?

### Worker & Background Processing (`worker.py`)
41. Which Redis database number (`0`, `1`, etc.) is used for the `CELERY_RESULT_BACKEND`?
42. How does `celery_app.conf.task_routes` direct tasks to the `identity_enrichment` queue?
43. What happens if the broker connection fails on startup based on the Celery configuration in `worker.py`?
44. Explain the purpose of `worker_prefetch_multiplier=1`. Why is this critical for Playwright tasks?
45. How does `celerybeat-schedule` trigger `reconcile_scans_task`?
46. What Prometheus metrics are emitted by the `@task_failure.connect` signal?
47. If the `remediation-worker` runs out of memory and is OOMKilled by Docker, how does Celery handle the abandoned task?
48. Why is `task_acks_late=True` configured? How does this protect against unhandled OSINT API timeouts?
49. What timezone is enforced across all Celery tasks?
50. What is the execution concurrency limit on the `remediation-worker` defined in `docker-compose.yml`, and why?
