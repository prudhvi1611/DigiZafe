# DigiZafe Repository Reconnaissance Map

This document serves as the master knowledge base foundation for the DigiZafe platform. It provides a comprehensive map of the repository structure, architecture, and technology stack.

---

## STEP 1 — MAP THE ENTIRE REPOSITORY

```text
DigiZafe/
├── backend/               # Python/FastAPI backend application source code
│   ├── app/               # Main application logic
│   │   ├── alembic/       # Database migrations
│   │   ├── api/           # REST API endpoints (v1)
│   │   ├── connectors/    # External OSINT & data source integrations
│   │   ├── core/          # Core configuration, logging, database setup
│   │   ├── domain/        # Domain logic, canonicalization, linkage
│   │   ├── ml/            # ML feature adapters and registry
│   │   ├── models/        # SQLAlchemy database models
│   │   ├── remediation/   # Playwright-based automated remediation runners
│   │   ├── repositories/  # Data access layer
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── security/      # Authentication, cryptography, keys
│   │   ├── services/      # Business logic services
│   │   ├── tasks/         # Celery asynchronous background tasks
│   │   └── worker.py      # Celery worker entry point
│   ├── tests/             # Pytest suite (unit, integration, e2e, security)
│   └── main.py            # FastAPI application entry point
├── docs/                  # Comprehensive architecture, audit, privacy docs and runbooks
├── frontend/              # React/Vite Single Page Application
│   ├── e2e/               # Playwright end-to-end tests
│   ├── public/            # Static assets
│   ├── src/               # React source code (components, features, hooks)
│   └── package.json       # Node.js dependencies
├── infrastructure/        # Deployment configuration (Docker, Caddy, Postgres, Redis)
├── ml/                    # Machine Learning pipeline, datasets, and pre-trained models
│   ├── features/          # Feature extraction logic
│   ├── models/            # Serialized models (.joblib)
│   └── training/          # Training and evaluation scripts
├── scripts/               # Operational utility scripts (smoke tests, release)
├── shared/                # Shared configuration, catalogs (e.g., JSON weight definitions)
├── pyproject.toml         # Python dependency management and build configuration
└── docker-compose.yml     # Multi-container orchestration configuration
```

### Important Directory Purposes
* **`backend/app/services/`**: The core brain of the platform. Handles business logic for everything from identity correlation to automated remediation.
* **`backend/app/connectors/`**: The OSINT gathering engine. Integrates with surface, deep, and dark web data sources.
* **`backend/app/remediation/`**: The action engine. Uses Playwright to execute automated privacy opt-outs and data deletion requests.
* **`frontend/src/features/`**: The modular UI architecture, grouping React components by business domain (e.g., identity, privacy, remediation).
* **`ml/`**: Dedicated pipeline for building the "Residual Risk" ML models used to score user digital exposure.

---

## STEP 2 — INVENTORY EVERY IMPORTANT FILE

| File | Type | Purpose | Important Classes/Functions | Dependencies | Importance |
| ---- | ---- | ------- | --------------------------- | ------------ | ---------- |
| `backend/app/main.py` | 🔴 Critical | Application Entry Point | `create_app()` | FastAPI, Uvicorn | High |
| `backend/app/worker.py` | 🔴 Critical | Task Execution | `celery_app` | Celery, Redis | High |
| `backend/app/models/*.py` | 🔴 Critical | DB Schemas | `User`, `Identity`, `Score` | SQLAlchemy | High |
| `docker-compose.yml` | 🔴 Critical | Infrastructure | Defines API, Workers, DB, Redis | Docker | High |
| `ml/models/residual-risk-v1.joblib` | 🔴 Critical | ML Artifact | Serialized predictive model | Scikit-learn | High |
| `frontend/src/main.tsx` | 🔴 Critical | UI Entry Point | React DOM Render | React, React-Router | High |
| `backend/app/core/config.py` | 🟠 Important | Settings | `Settings` | Pydantic | High |
| `pyproject.toml` / `package.json` | 🟠 Important | Dependencies | N/A | setuptools, npm | High |
| `backend/app/api/v1/endpoints/` | 🟠 Important | API Routes | Routers for various domains | FastAPI | High |
| `shared/config/pdss_catalog.json`| 🟡 Supporting| Config | Static risk definitions | N/A | Medium |

---

## STEP 3 — IDENTIFY THE TECHNOLOGY STACK

| Layer | Technology | Evidence | Purpose |
| --- | --- | --- | --- |
| Frontend | React, Vite, Tailwind CSS | `package.json`, `vite.config.ts` | UI rendering, styling, and bundling. |
| Backend | FastAPI, Python 3.11+ | `pyproject.toml` | High-performance async REST API. |
| Database | PostgreSQL 16 (asyncpg) | `docker-compose.yml`, `pyproject.toml` | Primary relational data store. |
| Cache | Redis | `docker-compose.yml` | Application caching and rate limiting. |
| ML | Scikit-Learn, pandas, joblib | `pyproject.toml`, `ml/models/` | Training and serving risk assessment models. |
| Queue | Celery (backed by Redis) | `pyproject.toml`, `backend/app/worker.py` | Asynchronous task orchestration (OSINT, Remediation). |
| Deployment | Docker, Docker Compose | `docker-compose.yml` | Containerization and local/prod orchestration. |
| Testing | Pytest, Playwright | `tests/`, `frontend/e2e/` | Backend unit/integration and Frontend/Remediation E2E testing. |

---

## STEP 4 — IDENTIFY MAJOR SYSTEM COMPONENTS

```text
Component: REST API Server
Location: backend/app/
Purpose: Serves frontend requests, orchestrates business logic.
Inputs: HTTP Requests (JSON)
Outputs: HTTP Responses (JSON)
Dependencies: PostgreSQL, Redis, Celery
Used by: Frontend App
Importance: 🔴 Critical

Component: Background Task Workers
Location: backend/app/tasks/, backend/app/worker.py
Purpose: Executes long-running OSINT discovery and privacy checks asynchronously.
Inputs: Celery Messages (Redis)
Outputs: Database updates, logs
Dependencies: Redis, PostgreSQL, External APIs
Used by: REST API Server
Importance: 🔴 Critical

Component: Automated Remediation Engine
Location: backend/app/remediation/
Purpose: Automates interactions with websites to submit privacy opt-outs.
Inputs: Remediation Tasks
Outputs: Browser Automation Scripts, Status Updates
Dependencies: Playwright, Celery
Used by: Task Workers
Importance: 🔴 Critical

Component: Predictive ML Engine
Location: ml/ and backend/app/ml/
Purpose: Calculates residual risk scores based on user exposure features.
Inputs: User Features
Outputs: Risk Scores
Dependencies: Scikit-learn
Used by: REST API (Scoring Service)
Importance: 🟠 Important

Component: Frontend Dashboard
Location: frontend/
Purpose: User interface for data interaction and visualization.
Inputs: User interactions
Outputs: HTTP Requests to API
Dependencies: React, Zustand, React-Query
Used by: End Users
Importance: 🔴 Critical
```

---

## STEP 5 — TRACE DEPENDENCIES

**High-Level Architecture Flow:**
1. **Frontend Dashboard** calls endpoints in the **REST API Server**.
2. The **REST API Server** reads/writes immediate data to **PostgreSQL**.
3. For intensive tasks (e.g., scanning, OSINT, remediation), the **REST API** pushes messages to the **Redis Broker**.
4. The **Celery Worker(s)** consume these messages.
5. The **Workers** invoke **Connectors** (to fetch external data) or the **Remediation Engine** (Playwright).
6. The **API Server** uses the **ML Engine** (`residual-risk-v1.joblib`) for scoring risk profiles on the fly.
7. Both **API** and **Workers** utilize **Redis Cache** for fast retrieval and rate-limiting.

---

## STEP 6 — IDENTIFY DATABASE STRUCTURE

**Database Technology**: PostgreSQL (accessed asynchronously via SQLAlchemy + asyncpg).
**Migrations**: Alembic (`backend/app/alembic/`).

**Key Domains & Models:**
* **Authentication/User**: `user`
* **Identity & Assets**: `identity`, `identifier`, `identity_anchor`, `identity_cluster`, `identity_cross_link`, `identity_match_assessment`
* **OSINT Findings**: `observation_finding`, `alert`, `profile_visual_fingerprint`
* **Risk & Scoring**: `score`, `recommendation`, `scan`
* **Action & Remediation**: `remediation`, `privacy`, `consent_egress`
* **System**: `audit`, `temporal`, `orchestration`, `connector_certification`, `candidate_profile`, `candidate_provenance`

*(Relationships generally center around `user_id` mapping to identities, which map to identifiers, which yield findings and scores.)*

---

## STEP 7 — IDENTIFY APIs

Found within `backend/app/api/v1/endpoints/`:

| Method | Endpoint Domain | File | Purpose |
| ------ | -------- | ---- | ------- |
| GET/POST | `/api/v1/auth/*` | `auth.py` | JWT Login, Registration, MFA |
| GET/POST | `/api/v1/identity/*` | `identity.py` | Managing core personal profiles |
| GET/POST | `/api/v1/identifiers/*`| `identifiers.py` | Managing emails, phones, aliases |
| GET | `/api/v1/scans/*` | `scans.py` | Initiating & checking OSINT scans |
| GET | `/api/v1/alerts/*` | `alerts.py` | Fetching security/privacy alerts |
| GET | `/api/v1/scores/*` | `scores.py` | Fetching PDSS and Residual Risk scores |
| GET/POST | `/api/v1/remediation/*`| `remediation.py` | Triggering automated opt-outs |
| GET | `/api/v1/connectors/*`| `connectors.py` | Checking status of OSINT data sources |
| GET/POST | `/api/v1/privacy/*` | `privacy.py` | Managing data rights and exports |
| GET | `/api/v1/health` | `health.py` | System health check |

---

## STEP 8 — IDENTIFY ML / AI COMPONENTS

**Standard Machine Learning (Deterministic):**
* **Residual Risk Scoring:** Scikit-Learn (HistGradientBoostingRegressor) stored at `ml/models/residual-risk-v1.joblib`.
* **Training Code**: `ml/training/train_residual.py`, `evaluate_residual.py`.
* **Datasets**: `ml/training/residual-dataset.csv`.
* **Feature Engineering**: `ml/features/residual_features.py` (extracts vectors from user profiles to feed into the model).

**Generative AI (LLMs):**
* **Integrations**: `backend/app/services/privacy/groq_client.py`.
* **Groq API:** Generates human-readable privacy narratives from raw JSON data (via `groq_client.py`).

---

## STEP 9 — IDENTIFY EXTERNAL INTEGRATIONS

**OSINT Sources (Connectors):**
* `crt.sh` (Certificate transparency)
* `HaveIBeenPwned` (Passwords)
* `Gravatar` (Avatars)
* `Github` (Developer footprint)
* `RDAP` (Domain WHOIS)
* `DuckDuckGo / SERP` (Search engine scraping)
* `Common Crawl / Wayback Machine` (Deep web historical data)

**Third-Party Services:**
* `Groq` (LLM Inference)
* `Maigret / Osintgram` (Username / Social Media reconnaissance adapters)

*(Note: Some of these integrations, particularly Deep Web and Osintgram, appear to be mocked or optionally stubbed in testing environments based on code analysis).*

---

## STEP 10 — IDENTIFY BACKGROUND PROCESSING

**Technology**: Celery backed by Redis.
**Worker Queues**:
* `celery` (default tasks, remediation)
* `identity_enrichment` (heavy data processing)
* `osint_connectors` (rate-limited external API calls)

**Scheduled Tasks (Celery Beat):**
* Revalidation of identities.
* Automated alert generation.
* Connector health checks.

---

## STEP 11 — IDENTIFY TESTS

* **Backend Unit Tests**: `backend/tests/unit/` (Connectors, Domain Logic, Services)
* **Backend Integration Tests**: `backend/tests/integration/` (Database, API endpoints)
* **Backend Security Tests**: `backend/tests/security/`
* **Frontend E2E Tests**: `frontend/e2e/` (Playwright tests covering Auth, Remediation, Scans, Privacy)

---

## STEP 12 — IDENTIFY CONFIGURATION

* **Environment Variables**: `.env` and `.env.example`
* **Backend Config Manager**: `backend/app/core/config.py` (Pydantic BaseSettings)
* **Infrastructure**: `docker-compose.yml`
* **Database Migrations**: `alembic.ini`
* **Static Catalogs**: `shared/config/pdss_catalog.json`, `shared/config/amber_sources.json`
* **Frontend Config**: `vite.config.ts`, `tailwind.config.js`

---

## STEP 13 — IDENTIFY IMPLEMENTATION STATUS

| Feature | Status | Evidence |
| ------- | ------ | -------- |
| User Auth & JWT | Implemented | `auth_service.py`, `backend/app/api/v1/auth.py` |
| OSINT Surface Connectors | Implemented | Multiple files in `connectors/impl/surface/` |
| Automated Remediation | Implemented | `playwright_runner.py` and Celery config |
| ML Risk Scoring | Implemented | `residual_service.py`, `.joblib` model file |
| Playwright E2E Tests | Implemented | Extensive suite in `frontend/e2e/` |
| Deep Web Scanning | Partial/Mocked | Present but likely stubbed given high latency constraints. |
| Advanced Candidate Discovery | Mocked | `test_candidate_discovery.py` and service implementations indicate reliance on mocked stubs for consistent testability. |

---

## CRITICAL FILES TO STUDY
Before presenting this project, ensure deep understanding of:
1. `backend/app/core/config.py` - Understands how the app is dynamically configured.
2. `backend/app/worker.py` & `docker-compose.yml` - Explains the distributed architecture.
3. `backend/app/services/identity_match_engine.py` - Core logic mapping found data to users.
4. `backend/app/remediation/runners/playwright_runner.py` - Showcases the unique automated takedown capability.
5. `ml/training/train_residual.py` - Explains how risk is calculated mathematically.

## UNKNOWN AREAS
* Specific runtime constraints on Playwright concurrency.
* Exact prompt definitions sent to the Groq API for narrative generation.
* Extent of actual rate-limiting applied to live OSINT sources versus mocked behavior in production.

## QUESTIONS FOR PHASE 2
1. **Remediation State Machine**: How does the system handle multi-step CAPTCHAs during automated Playwright remediation?
2. **Data Consistency**: How does the `identity_match_engine` resolve conflicts when two data sources report contradicting identity anchors?
3. **ML Lifecycle**: Is the `.joblib` model updated dynamically via online learning, or does it require manual retraining and redeployment?
4. **Data Privacy**: How is the `master.key` (in `/secrets/`) utilized for encrypting PII at rest within the Postgres database?
