# DigiZafe: Security, Integrations & Infrastructure

## 1. SECURITY POSTURE

The platform operates under a zero-trust model internally. Because DigiZafe handles extremely sensitive PII (Personal Identifiable Information) and acts as an outbound actor against the web, its threat model focuses heavily on SSRF, Data Leakage, and Account Takeover.

### Authentication & Authorization
* **Threat**: Account Takeover / Horizontal Privilege Escalation.
* **Protection**: Cryptographically signed tokens and database-level isolation.
* **Implementation**: Uses JWT (JSON Web Tokens) encoded with RS256/HS256 (via `python-jose`). Authorization is handled dynamically via FastAPI Dependency Injection (`Depends(CurrentUser)`). Additionally, Sprint 25 introduced Postgres Row-Level Security (RLS) ensuring that even if an application-layer bug occurs, the DB will physically reject queries fetching another user's `IdentityAnchor`.
* **Source**: `backend/app/security/jwt.py`, `backend/app/api/deps.py`.

### Cryptography (Hashing & Encryption)
* **Threat**: Database breach leading to mass credential and PII theft.
* **Protection**: State-of-the-art memory-hard hashing and envelope encryption.
* **Implementation**:
  * *Passwords*: Hashed using Argon2id (`passlib[argon2]`), defending against GPU brute-forcing.
  * *PII Encryption*: Sensitive data (e.g., precise birth dates, SSN hints) is encrypted at rest using AES-GCM-256. 
  * *Blind Indexing*: To allow searching of encrypted emails without decrypting the whole database, the system uses HMAC-SHA256 blind indexing.
* **Source**: `backend/app/security/password.py`, `backend/app/security/keys.py`.

### SSRF Protection (Server-Side Request Forgery)
* **Threat**: A malicious OSINT candidate URL forces the backend to scan internal AWS metadata endpoints (`169.254.169.254`) or internal Redis clusters.
* **Protection**: Custom Egress layer enforcing strict IP routing rules.
* **Implementation**: The `EgressFetcher` class monkey-patches the `httpcore` network backend. It resolves the DNS *first*, checks the resulting IP against a hardcoded list of `_BLOCKED_NETWORKS` (private, CGNAT, loopback, metadata), and pins the TCP connection directly to that validated IP. It also explicitly disables HTTP redirects to prevent DNS rebinding TOCTOU attacks.
* **Source**: `backend/app/security/egress.py`.

### Injection, XSS, CSRF & CORS
* **Injection**: Prevented entirely by using SQLAlchemy's async ORM parameter binding. No raw SQL concatenation exists.
* **XSS**: Mitigated by the React frontend which inherently escapes string variables before DOM rendering.
* **CSRF**: Mitigated by relying on HTTP `Authorization: Bearer` headers rather than ambient browser cookies.
* **CORS**: `CORSMiddleware` in FastAPI explicitly limits origins based on `settings.cors_origins`, rejecting cross-origin requests from unknown domains.

### Vulnerabilities That Remain (Accepted Risk)
* **Playwright Sandbox Escape**: If a data broker site serves a highly sophisticated browser zero-day payload, the Chromium instance running inside the Celery worker could be compromised. While the Docker container provides isolation, egress restrictions are the primary defense.
* **Memory Exhaustion DoS**: A malicious user submitting thousands of remediation requests could theoretically exhaust the Celery queue. Currently mitigated by strict rate-limiting, but queue-flooding remains a risk.

---

## 2. EXTERNAL SERVICES & INTEGRATIONS

### Groq API (LLM Privacy Narratives)
* **Purpose**: Generates human-readable summaries of JSON data leaks.
* **Request/Response**: Standard HTTPX async POST to `api.groq.com/openai/v1/chat/completions`. Returns JSON string choices.
* **Authentication**: `Bearer` token via `GROQ_API_KEY`.
* **Failure Handling & Fallback**: Wrapped in `try/except`. If Groq times out or returns 503, the system catches `GroqError` and falls back to a deterministic, rule-based text summary. It never blocks the core UI.
* **Security Risk**: Prompt injection. (Mitigated by strictly defining the `system` prompt).

### Have I Been Pwned (HIBP)
* **Purpose**: Identifies exposed credentials.
* **Request/Response**: K-Anonymity model. The backend hashes the user's password/email locally (SHA1), sends *only* the first 5 characters, and downloads a list of matching suffixes.
* **Security Risk**: Negligible, as the full hash never leaves the system.

### Deep Web Scrapers (Wayback / Common Crawl)
* **Status**: **MOCKED / PARTIAL**
* **Purpose**: Searches historical archives for deleted data.
* **Limits & Retries**: These APIs are notoriously slow. The current implementation heavily stubs these responses during testing and uses aggressive timeouts (e.g., 5 seconds) to prevent worker starvation in production.

---

## 3. INFRASTRUCTURE

The platform utilizes a modern containerized stack orchestrated via Docker Compose (`docker-compose.yml`), optimized for both local development and easy translation to Kubernetes.

* **API Server (`api`)**: Runs Uvicorn/FastAPI mapped to port 8000. Re-loads dynamically in dev.
* **Database (`postgres`)**: PostgreSQL 16 Alpine. Mounts a persistent volume for state.
* **Redis (`redis-broker` & `redis-cache`)**: Split into two distinct containers. 
  * `broker` handles Celery queues (persistent, requiring durability).
  * `cache` handles ephemeral data (rate limits, connector health).
* **Workers (`worker` & `remediation-worker`)**: 
  * Standard `worker` handles OSINT and Enrichment with `--concurrency=2`.
  * `remediation-worker` is strictly limited to `--concurrency=1` due to the massive RAM overhead of running headless Chromium for Playwright.
* **Scheduler (`beat`)**: Celery Beat instance firing chronological reconciliation tasks.
* **Reverse Proxy (`caddy`)**: Optional profile that provides automatic HTTPS and static routing.
* **Frontend (`frontend`)**: Vite development server or Nginx production build serving the React SPA.
* **Secrets Management**: Master encryption key injected via `./secrets/master.key` volume mount, preventing the key from living in environment variables or source control.

---

## 4. PERFORMANCE ANALYSIS

* **Bottlenecks**: 
  * *Automated Remediation*: Launching Chromium takes ~1-2 seconds, and navigating highly obfuscated data broker sites takes 10-30 seconds. This is the ultimate system bottleneck.
* **Caching**: The backend uses Redis aggressively for OSINT connector responses. If two users search for the exact same public data parameter within 24 hours, the second request hits Redis in < 2ms instead of making a 5-second outbound HTTP call.
* **Database Performance**: 
  * Utilizes `asyncpg`, the fastest asynchronous Python Postgres driver.
  * The `raw_data` column in `observation_finding` relies on Postgres `JSONB` with GIN indexing, allowing lightning-fast key lookups across millions of un-normalized JSON payloads.
* **Concurrency**: FastAPI handles thousands of concurrent socket connections effortlessly via `asyncio`. Celery workers scale horizontally to handle CPU-bound ML scoring and network-bound scraping.
* **ML Inference**: `HistGradientBoostingRegressor` is a tree-based algorithm. Inference takes microseconds, creating virtually zero overhead on the API layer.

---

## 5. PROFESSOR QUESTIONS (Security & Infrastructure Defense)

*(40 Rigorous Security, Architecture, and DevOps Questions)*

### Application Security
1. **Explain the TOCTOU (Time-of-Check to Time-of-Use) vulnerability in SSRF and how `EgressFetcher` mitigates it.**
2. **If a user inputs `<script>alert(1)</script>` into their alias profile, where exactly is that neutralized?**
3. **Why did the architecture migrate to Postgres Row-Level Security (RLS) instead of relying purely on FastAPI dependencies?**
4. **How does AES-GCM provide authenticated encryption, and why is this vital for the `keys.py` implementation?**
5. **Describe the concept of "Blind Indexing" using HMAC-SHA256. Why is it used for searchable encrypted columns?**
6. **If the `master.key` is compromised, how would you rotate the encryption keys across a billion rows?**
7. **Why does `EgressFetcher` explicitly strip the `Host` header if a caller attempts to inject it?**
8. **What prevents a CSRF attack on the `/api/v1/identity/graph/rebuild` POST endpoint?**
9. **How does the system enforce rate limiting on the `/api/v1/auth/login` route to prevent credential stuffing?**
10. **Explain the security implications of `follow_redirects=False` in the Egress layer.**

### Infrastructure & Docker
11. **Why are there two separate Redis containers (`redis-broker` and `redis-cache`) instead of one?**
12. **What happens to queued Celery tasks if the `redis-broker` container is OOMKilled and restarts?**
13. **How does the Docker `healthcheck` for the `api` container coordinate with the `depends_on: condition: service_healthy` directives?**
14. **Why is the `remediation-worker` explicitly locked to `--concurrency=1`?**
15. **If deploying to Kubernetes, why would you use a `DaemonSet` vs a `Deployment` for the Celery workers?**
16. **How do you safely pass the `POSTGRES_PASSWORD` into the container without exposing it in `docker-compose.yml` logs?**
17. **What is the purpose of the `caddy` container, and how does it handle SSL termination?**
18. **Explain the Docker bridge network (`digizafe`). Can the host machine directly query the Postgres port by default?**
19. **If the `beat` container is scaled to 3 replicas accidentally, what happens to the scheduled tasks?**
20. **Why does the API Dockerfile use an unprivileged user rather than running as root?**

### External Integrations & Resilience
21. **How does the `groq_client.py` gracefully degrade if the LLM provider experiences an outage?**
22. **What is K-Anonymity, and how does the HaveIBeenPwned connector implement it to protect user passwords?**
23. **Why are the Deep Web APIs (Common Crawl) considered "Mocked/Partial" in this architecture?**
24. **If a data broker API implements a hard rate limit (429 Too Many Requests), how does Celery's `task_retry` handle it?**
25. **Describe the exponential backoff strategy for failing external API calls.**
26. **How does the `connector_budget_service` prevent runaway cloud computing costs?**
27. **What are the legal implications of scraping data broker sites using Playwright without an official API?**
28. **If an external API returns a 500MB JSON payload maliciously, how does `EgressFetcher` prevent memory exhaustion?**
29. **How do you handle API schema changes from third-party OSINT vendors over time?**
30. **Explain how the `RedisCache` utilizes TTL (Time To Live) to invalidate stale OSINT findings.**

### Performance & Bottlenecks
31. **Why is Playwright inherently the largest bottleneck in this system?**
32. **What is the algorithmic complexity (Big O) of inserting data into a Postgres JSONB GIN index?**
33. **Explain the difference between `psycopg2` and `asyncpg` regarding the Python GIL (Global Interpreter Lock).**
34. **If the ML model was swapped from Scikit-Learn to a 7-Billion parameter LLM, how would the infrastructure architecture have to change?**
35. **How does the React frontend utilize `@tanstack/react-query` to reduce redundant network calls to the FastAPI backend?**
36. **Describe the impact of database connection pooling when scaling FastAPI from 1 to 50 pods.**
37. **Why does the `IdentityMatchEngine` use `hashlib.sha256` to fingerprint inputs before executing the matching logic?**
38. **If the Celery queue backs up with 100,000 OSINT tasks, how does the user experience degrade on the frontend?**
39. **How would you implement a CDN (Content Delivery Network) in this architecture, and what assets would it serve?**
40. **What APM (Application Performance Monitoring) tools would you inject into the `structlog` pipeline to track cross-container request tracing?**
