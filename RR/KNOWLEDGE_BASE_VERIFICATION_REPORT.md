# Phase 9: Truth & Consistency Audit Report

This document audits all major technical claims made in the Phase 1–8 master knowledge base against the definitive source of truth: the actual repository implementation. 

## Claim Verification Matrix

| Claim | Document | Actual Code Evidence | Status |
|-------|----------|----------------------|--------|
| **Residual Risk Model is HistGradientBoostingRegressor** | ML | `ml/training/train_residual.py` | 🟢 VERIFIED |
| **Residual Risk Ground Truth is strictly empirical** | ML | Found synthetic derivation | 🔴 UNSUPPORTED (Reworded to synthetic/heuristic proxy) |
| **Identity Matching uses deterministic point scoring** | Algorithms | `backend/app/services/identity_match_engine.py` | 🟢 VERIFIED |
| **SHAP is used for ML Explainability** | ML | No `shap` library usage in Python backend | 🔴 UNSUPPORTED (Moved to Planned/Proposed) |
| **Remediation executes CAPTCHA bypass natively** | Architecture | `playwright_runner.py` uses best-effort JS token injection | 🟠 PARTIAL (Requires manual fallback on failure) |
| **Zero-trust data processing guarantee** | Security | Multiple controls (JWT, RLS, Egress) but sandbox escapes remain possible | 🟠 PARTIAL (Toned down to "Zero-trust architecture approach") |
| **Row-Level Security (RLS) isolates tenants** | Security | `backend/app/alembic/versions/c7d13d94607b_sprint25_rls_integrity.py` | 🟢 VERIFIED |
| **Multi-threaded OSINT gathering** | Architecture | `worker.py` utilizes Celery multi-processing, not raw threading | ❌ REWRITTEN (Now "Asynchronous distributed processing") |
| **Deep Web Scraping (Wayback/CommonCrawl)** | Architecture | Mocked in `test_candidate_discovery.py` | 🟠 PARTIAL (Mocked for MVP) |
| **SSRF Protection blocks internal IPs** | Security | `backend/app/security/egress.py` | 🟢 VERIFIED |
| **AES-GCM Envelope Encryption for PII** | Security | `backend/app/security/keys.py` | 🟢 VERIFIED |
| **FastAPI easily handles thousands of concurrent users** | Architecture | Standard `asyncio` behavior, but untested here | 🟡 INFERRED (Toned down to "architecturally designed for") |

---

## PRESENTATION SAFETY CHECK

The following section translates highly technical implementation realities into safe, defensible statements for academic presentation.

### 1. Identity Correlation Engine
* **Exact Source:** `backend/app/services/identity_match_engine.py -> assess_candidate()`
* **Evidence Summary:** Deterministic logic summing points for independent evidence groups, explicitly capped by a `username_cap`.
* **Verification Status:** 🟢 VERIFIED
* ❌ **DO NOT SAY:** "Our AI correlates user identities flawlessly."
* ✅ **SAY:** "We use a deterministic, rule-based matching engine to correlate OSINT data, prioritizing legal explainability over black-box AI."
* 🎓 **PROFESSOR MAY ASK:** "Why didn't you use Graph Neural Networks?"
* 💡 **ANSWER:** "GDPR and CCPA regulations require 'Right to Explanation'. GNNs are opaque, whereas our point-based engine allows us to explain exactly which evidence triggered the match."

### 2. Machine Learning Ground Truth
* **Exact Source:** `ml/training/train_residual.py -> model.fit(X, y)`
* **Evidence Summary:** Trains on `residual-dataset.csv` targeting `target_delta`.
* **Verification Status:** 🟠 PARTIAL (Implementation exists, but ground truth is heuristic).
* ❌ **DO NOT SAY:** "Our ML model accurately predicts real-world data breaches."
* ✅ **SAY:** "Our MVP trains a HistGradientBoostingRegressor on a combination of synthetic data and cybersecurity heuristics to demonstrate the relative risk estimation pipeline."
* 🎓 **PROFESSOR MAY ASK:** "How do you know the prediction is reliable if the dataset is synthetic?"
* 💡 **ANSWER:** "Currently, it acts as a baseline proxy. True predictive validity requires transitioning to a fully empirical dataset of verified user breaches over time."

### 3. Automated Remediation Engine
* **Exact Source:** `backend/app/remediation/runners/playwright_runner.py -> run_broker()`
* **Evidence Summary:** Playwright script automates DOM filling and best-effort JavaScript CAPTCHA injection, catching timeouts to fallback.
* **Verification Status:** 🟢 VERIFIED (As a heuristic tool).
* ❌ **DO NOT SAY:** "We fully bypass CAPTCHAs and guarantee data removal."
* ✅ **SAY:** "We built a heuristic remediation engine that automates form completion and handles supported anti-bot measures, safely falling back to manual intervention when the DOM changes."
* 🎓 **PROFESSOR MAY ASK:** "What happens if a data broker completely redesigns their website?"
* 💡 **ANSWER:** "The Playwright locator will hit its hard timeout. The system catches the error, marks the job as `MANUAL_NEEDED`, and alerts the user. The automation is inherently brittle to DOM changes."

### 4. Server-Side Request Forgery (SSRF) Protection
* **Exact Source:** `backend/app/security/egress.py -> _is_blocked_ip()`
* **Evidence Summary:** Monkey-patches HTTPX to resolve DNS first, blocks metadata/private IPs, and pins the TCP connection.
* **Verification Status:** 🟢 VERIFIED
* ❌ **DO NOT SAY:** "Our system is 100% immune to all network attacks."
* ✅ **SAY:** "We implemented strict egress controls that resolve DNS prior to connection and block internal IP ranges to mitigate SSRF."
* 🎓 **PROFESSOR MAY ASK:** "How do you handle DNS rebinding attacks?"
* 💡 **ANSWER:** "By disabling HTTP redirects in the EgressFetcher and pinning the TCP socket directly to the IP validated during the initial DNS resolution phase."

---

## TOP 20 CLAIMS I MUST BE CAREFUL ABOUT

*(Statements most likely to get challenged by a technical professor, and the safest way to explain them).*

1. **"The system is multi-threaded."**
   *Safe wording:* "The system is asynchronous and distributed. FastAPI uses `asyncio` for non-blocking I/O, and Celery distributes heavy CPU/Network tasks across separate worker processes."
2. **"We use AI to find user data."**
   *Safe wording:* "We use automated OSINT connectors to discover data. We use ML exclusively for risk scoring, and LLMs exclusively for narrative generation."
3. **"The model uses SHAP for explainability."**
   *Safe wording:* "Currently, the pipeline uses Gradient Boosting. SHAP is a planned extension to expose feature-level contributions."
4. **"We guarantee Zero-Trust Security."**
   *Safe wording:* "We adhere to zero-trust architecture principles, utilizing JWTs, Row-Level Security, and Egress restrictions."
5. **"FastAPI handles thousands of users easily."**
   *Safe wording:* "FastAPI's `asyncio` event loop is architecturally designed to handle high concurrency by not blocking on database or network calls."
6. **"The ML model predicts real breaches."**
   *Safe wording:* "The ML model currently optimizes toward a synthetic/heuristic ground truth to prove out the pipeline infrastructure."
7. **"We bypass CAPTCHAs."**
   *Safe wording:* "We attempt best-effort JavaScript token injection for supported CAPTCHAs, but fallback to manual human review when blocked."
8. **"Deep Web Scraping is fully implemented."**
   *Safe wording:* "The architectural adapters for Deep Web scraping exist, but they are mocked in the current MVP to prevent network starvation."
9. **"Playwright is highly scalable."**
   *Safe wording:* "Playwright is highly capable, but memory-intensive. Horizontal scaling is computationally expensive due to Chromium's overhead."
10. **"JSONB is faster than relational tables."**
   *Safe wording:* "JSONB with GIN indexing provides the necessary schema flexibility for unpredictable OSINT payloads while maintaining excellent read speeds."
11. **"Celery guarantees tasks are never lost."**
   *Safe wording:* "Celery with `task_acks_late=True` prevents task loss if a worker crashes, though Redis eviction policies must be managed carefully to avoid queue dropping."
12. **"We scrape Instagram."**
   *Safe wording:* "We utilize OSINT wrappers that query public surface web artifacts, honoring rate limits to prevent IP bans."
13. **"The Database is fully encrypted."**
   *Safe wording:* "Strict PII fields are encrypted at rest using AES-GCM envelope encryption. Non-sensitive relational metadata is unencrypted for querying."
14. **"JWTs prevent CSRF."**
   *Safe wording:* "Using `Authorization: Bearer` headers instead of ambient browser cookies neutralizes traditional CSRF attack vectors."
15. **"React Query speeds up the frontend."**
   *Safe wording:* "React Query caches server state locally, preventing redundant network calls to the FastAPI backend."
16. **"Postgres RLS is unhackable."**
   *Safe wording:* "RLS enforces isolation at the database engine level, meaning even if the application layer routes a bad ID, the query returns empty."
17. **"The LLM analyzes the data securely."**
   *Safe wording:* "The Groq LLM translates JSON into narratives. PII must be redacted prior to prompt injection to maintain privacy compliance."
18. **"We don't have SQL Injection vulnerabilities."**
   *Safe wording:* "SQLAlchemy's ORM uses parameterized queries exclusively, eliminating traditional SQL string-concatenation injection."
19. **"The Identity Match Engine is flawless."**
   *Safe wording:* "The engine is deterministic, but highly common usernames (collision risk) require users to supply secondary anchors (like phone numbers) to cross the match threshold."
20. **"This MVP is production-ready."**
   *Safe wording:* "The MVP demonstrates the complete end-to-end architecture. Moving to production requires empirical ML retraining and a horizontal Kubernetes scaling strategy for the Playwright workers."
