# MASTER_ENGINEERING_CONTEXT.md
### DigiZafe — Personal Digital Exposure Intelligence & Remediation Platform
**Single persistent engineering memory. Include this file in every AI coding session before writing any code.**
> This is a *context* file, not a design file. It summarizes the frozen engineering baseline for DigiZafe (SAD, Architecture Review, SRS, SDD, Developer Implementation Playbook — produced and frozen in Sprint 0). If this file and a frozen document ever conflict, **the frozen document wins** and you file a Critical Blocker Note (CBN). Never modify frozen documents automatically. Never redesign the architecture. You implement; you do not re-decide.
**Document version:** 2.1 (Final free-first + XposedOrNot primary + full AIDR integration)  
**Project name:** DigiZafe  
**Primary repository strategy:** New DigiZafe monorepo. AIDR (https://github.com/stephenlthorn/auto-identity-remove) is the primary prior-art source for the remediation engine — vendored concepts, mapped tables/state, re-implemented under DigiZafe layering/privacy rules (or hybrid Node worker if justified by ADR). Always attribute and respect its license.
---
## 1. Product Vision
**DigiZafe** lets an individual **discover, understand, quantify, and reduce** their own online exposure — across the **surface web**, **deep web** (legal public/authenticated sources), and **carefully constrained public dark-web / leak indexes** — **safely, explainably, with zero paid API keys required for MVP**, and with **actionable closed-loop remediation**.
A user proves ownership of identifiers (emails, phones, usernames, domains…). DigiZafe builds a verified identity graph, discovers exposures (breaches via **XposedOrNot** primary + others, data brokers, SERP footprints, public records, certificate logs, paste/leak indexes, constrained dark signals), computes a transparent **Personal Data Severity Score (PDSS)** with full explainability and industry-standard vector style, and produces a prioritized remediation plan — including guided steps **and** semi-automated opt-outs (AIDR-inspired) — then monitors change over time.
**Positioning:**  
*"HIBP tells you if you were breached. Broker removers help you opt out of one class of sites. DigiZafe tells you how exposed you are overall (surface → deep → constrained dark), why the score is what it is (explainable PDSS), what to fix first, and helps you close the loop with free tools — for your own verified identity only."*
**Research & innovation:** Versioned scoring models + model cards, reproducible evaluation harness, synthetic benchmarks, publishable PDSS formulation, multi-layer personal exposure methods, explainable remediation ROI, identity-graph fusion. Creative UX: risk autopsy graph, grounded narrative briefings, what-if simulator, privacy streaks/badges.
**Cost posture (non-negotiable for MVP):** Entire core loop runs with **entirely free APIs, free public sources, self-hosted components, and optional user-provided free tokens**. Paid services (HIBP Breach API key, CapSolver, commercial dark intel, XposedOrNot higher tiers) are **feature-flagged optional enhancements only** and never load-bearing.
---
## 2. Core Objectives
| ID | Objective | Measured by |
|----|-----------|-------------|
| G1 | **Self-only safety** | 0 scans against unverified identifiers (DB trigger + RLS + audit) |
| G2 | **Multi-layer coverage** | Findings tagged Surface / Deep / Constrained-Dark with full provenance |
| G3 | **Explainable risk** | 100% of score contribution traceable via durable explanation records + PDSS vector |
| G4 | **Actionable free remediation** | Prioritized plan + guided + semi-automated Green-broker opt-outs (AIDR lineage) + DSAR/freeze generators |
| G5 | **Closed loop** | Remediate → re-verify → re-score; durable history/trends |
| G6 | **Privacy by design** | No raw dumps; short-TTL evidence; crypto-shred; consented egress only |
| G7 | **Zero paid keys for MVP** | Core path functions with free sources (XposedOrNot primary, Pwned Passwords, etc.) + local components only |
| G8 | **Research readiness** | Versioned models, model cards, eval harness, synthetic data |
| G9 | **Solo-buildable** | Core MVP (verify → free surface discover → PDSS score → recommend → AIDR-style remediate → re-score) in ~16–20 weeks |
---
## 3. Non-Goals (do NOT build in MVP / without ADR + legal review)
- Scanning identifiers of other / non-consenting people.
- People-search / OSINT-on-anyone product.
- Unrestricted dark-web crawling, marketplace login/purchase, dump buying, or illegal access.
- holehe-style reset-flow abuse, credential stuffing, or any offensive tooling.
- Real-time heavy scraping of Google/Facebook/Instagram/LinkedIn (legal public APIs / free SERP only).
- Fully autonomous removal that violates ToS or law.
- Microservices, Kafka, Elasticsearch, Kubernetes for MVP.
- Mobile native, multi-tenant org plans, browser extension as MVP.
- Opaque black-box score with no explanation path.
- Storing raw breach dumps or full HTML indefinitely.
- Any paid API as a hard dependency for core function.
- “Pollute / noise” broker modes without separate ADR + legal review (default: out of scope).
---
## 4. Architecture Summary
**Style:** Modular monolith + async workers. One codebase, entrypoints: API / discovery-worker / remediation-worker / beat / optional scoring worker.
- **API (FastAPI):** thin routers → services. No long-running discovery or Playwright in request path.
- **Workers (Celery or equivalent):** rate-limited connectors, scoring, Playwright remediation runners, purge/reconcile.
- **Orchestration:** **Postgres-backed state machine + reconciliation sweep** (self-healing; not fragile chords). Deadline + terminal states finalize scans/jobs.
- **Data:** PostgreSQL 16 (JSONB + FTS + relational + **RLS**) + **split Redis** (broker: noeviction+AOF; cache: allkeys-lru).
- **Discovery:** Connector plugin framework with **Green / Amber / Red** legality-feasibility gate. All egress via one SSRF-guarded `EgressFetcher`. Surface-first; Deep and Constrained-Dark gated.
- **Intelligence:**  
  - Identity: deciban / Fellegi–Sunter linkage + identity graph.  
  - Scoring: **hybrid PDSS** (CVSS-inspired Base/Temporal/Environmental vector) + surprisal (non-saturating) + optional free/local ONNX residual. Two-track (Confirmed / Possible).  
  - Explainability: durable redacted records + drivers + counterfactuals + grounded narrative (local Ollama preferred).  
  - Recommendations: urgency + ROI + dependency DAG.
- **Remediation (AIDR core):** Guided always; semi-automated Green brokers via Playwright runners + persistent state + verify loop (directly evolved from AIDR). DSAR/complaint/freeze generators. Closed-loop re-verify → re-score.
**Primary free breach source:** XposedOrNot (keyless for personal email checks).  
**Rejected without ADR:** unrestricted dark crawl, pure black-box ML, name-only third-party scanning, single Redis, Celery-chords-only orchestration, paid-API-hard-dependency.
---
## 5. Technology Stack (Free-First)
| Layer | Choice | Cost notes |
|-------|--------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic v2, Uvicorn/Gunicorn | Free |
| ORM/migrations | SQLAlchemy 2.0 + Alembic | Free |
| Queue/scheduler | Celery + Beat + Flower on redis-broker | Free |
| HTTP | httpx (async) + timeouts + per-host semaphores | Free |
| Browser automation | Playwright (Python preferred; Node hybrid possible for AIDR port) | Free |
| DB | PostgreSQL 16 + RLS | Free (self-host / free tiers) |
| Redis | 7 — two instances (broker + cache) | Free (self-host) |
| Auth | Argon2id + short JWT + rotating refresh + TOTP MFA | Free |
| Crypto | cryptography (AES-GCM envelope), HMAC blind indexes, separate MFA DEK | Free |
| Scoring core | Pure Python PDSS + surprisal | Free |
| Optional residual | sklearn/LightGBM → ONNX Runtime (local inference) | Free |
| Graph | NetworkX or Postgres adjacency | Free |
| Frontend | React 18 + TS + Vite + Tailwind + shadcn/ui + Recharts + TanStack Query + Cytoscape/D3 | Free |
| Proxy | Caddy (auto TLS) | Free |
| Containers | Docker + docker-compose | Free |
| CI/CD | GitHub Actions (free tier) | Free |
| Local LLM narrative | Ollama / llama.cpp (grounded only) | Free |
| **Breach (primary free)** | **XposedOrNot** (api.xposedornot.com, keyless for email checks; official `xposedornot` Python client) | **Free** (personal/low-volume; respect rate limits + attribute) |
| Password checks | Pwned Passwords (HIBP k-anonymous, free, no key) | Free |
| Optional paid | HIBP full Breach API key, CapSolver, XposedOrNot Plus / commercial tiers, commercial threat feeds | Never required for core |
| Other free connectors | crt.sh, RDAP/DNS, GitHub API (free token), Gravatar, curated username presence, DuckDuckGo / free SERP or self-hosted Searx, public broker registries (CA SB 362, Vermont…), public paste/leak indexes, archive.org | All free |
| Remediation | AIDR-inspired Playwright runners + free CAPTCHA path (manual / user-in-loop first) | Free core |
**Zero-cost MVP guarantee:** Core path works with **no paid keys**. XposedOrNot is the default breach source.
---
## 6. Folder Structure (canonical)
digizafe/
├─ backend/app/
│ ├─ main.py worker.py beat.py remediation_worker.py
│ ├─ api/ ... (v1: auth, identifiers, verification, identity, scans, findings,
│ │ scores, recommendations, remediation, alerts, privacy, consent,
│ │ audit, admin, health, research)
│ ├─ services/
│ ├─ domain/ # pure: linkage, scoring/pdss, recommendation, graph, evidence, canonicalize
│ ├─ connectors/ # base + sdk + impl/{surface, deep, dark_constrained}
│ │ # including xposedornot.py, pwned_passwords.py, ...
│ ├─ remediation/ # AIDR-inspired: runners, playbooks, verify loops, state adapters
│ ├─ repositories/ models/ schemas/ security/ tasks/ core/ constants/
│ ├─ alembic/ tests/{unit,integration,security,e2e,fixtures,factories}/
├─ frontend/src/{app,features,components,lib,hooks,styles}/
├─ ml/ # offline only: datasets, training, export ONNX, eval
├─ infrastructure/{docker,compose,caddy,redis,postgres,monitoring}/
├─ shared/{contracts,config,types}/
│ score_model/ pdss_catalog.json severity_catalog.json
│ deciban-weights.json playbook/ broker_registry/
├─ vendor/ or docs/prior-art/ # AIDR reference + XposedOrNot notes
├─ scripts/ docs/{adr,runbooks,model-cards,ethics,aidr-mapping}/ .github/workflows/
├─ MASTER_ENGINEERING_CONTEXT.md # THIS FILE

Dependency direction is strictly one-way. Domain is pure. Connectors never touch DB. ml/ is offline only.
---
## 7. Module Responsibilities & Service Boundaries
(Same as previous version — services use DTOs only. RemediationService owns AIDR-style jobs. DiscoveryService dispatches connectors including the new primary `xposedornot` connector.)
**Connector SDK:** `Connector` ABC + injected EgressFetcher / Cache / RateLimiter / Clock / logger. Never DB, never raw HTTP.  
All free APIs (especially XposedOrNot) **must** use the RateLimiter + Cache aggressively.
---
## 8. Database Principles
(Unchanged core: RLS, three-layer evidence, verified-only DB trigger, encryption, versioned catalogs, broker_optout_state for AIDR lineage.)
Findings from XposedOrNot are normalized into the same `observations` → `findings` pipeline with source = "xposedornot", confidence, recency, and exposed-data types when available.
---
## 9. Security Principles
(Unchanged: Argon2id, short JWT + rotating refresh, RLS, single SSRF resolve-pin-connect EgressFetcher, envelope crypto + crypto-shred, Playwright isolation, no exploit code.)
---
## 10. Privacy Principles
(Unchanged core.)  
**Important for XposedOrNot:** The free email check sends the identifier. Therefore it **must** go through ConsentService + egress_ledger, and the UI must honestly disclose that the email is sent to XposedOrNot. Same rule as any non-k-anonymous service. Only Pwned Passwords is k-anonymous among the common free options.
---
## 11. Identity, Scoring, Recommendation, Remediation (correctness-critical)
### 11.1–11.3
(Unchanged: deciban linkage, hybrid PDSS + surprisal two-track, recommendations with surprisal marginal impact, explainability mandatory.)
Breach findings (from XposedOrNot primary) feed Sensitivity, Discoverability, Linkability, Impact, and the reuse/criticality logic. Richer fields (risk_label, exposed data types, pastes, year-wise) improve PDSS Environmental/Temporal signals and explanation records.
### 11.4 Remediation Engine (full AIDR integration)
**Source of truth for design:** https://github.com/stephenlthorn/auto-identity-remove (AIDR).
**Mapping highlights (updated):**
- AIDR `lib/hibp.js` / `aidr breach` / breachCount signal → DigiZafe **XposedOrNot primary connector** + free Pwned Passwords + optional HIBP fallback.  
  `breachCount` and detailed breach list now come primarily from XposedOrNot (free).  
- Everything else (brokers.js, state.json → broker_optout_state, verify, serp, freeze, know, complaints, CapSolver optional, multi-person, etc.) remains as previously mapped.
- Free CAPTCHA / manual path preferred; CapSolver optional only.
- Closed loop: remediation → re-verify → re-score (now with better free breach data).
Detailed mapping lives in `docs/aidr-mapping/`. Always attribute AIDR.
---
## 12. Free Sources & Zero-Paid Policy (detailed) — **PRIMARY EDIT LOCATION**
**Mandatory free core connectors / signals (MVP):**
- **Breach (primary):** **XposedOrNot** — `https://api.xposedornot.com/v1/check-email/{email}` (and analytics endpoints).  
  - No API key for personal email checks.  
  - Official Python client: `pip install xposedornot`.  
  - Free-tier rate limits (approx.): 2/sec, 25/hour, 100/day per IP on check-email — enforce via Connector SDK RateLimiter + Redis cache (long TTL for negative results, medium for positive).  
  - Respect ToS: personal/low-volume use, clear attribution to XposedOrNot when displaying their data, no resale of raw data, no circumvention of limits. Higher commercial volume → their paid tiers (optional flag).  
  - Returns breach names, analytics, pastes, risk labels, exposed data types — map into findings + PDSS + explanations.
- **Passwords:** Pwned Passwords (HIBP) — free, k-anonymous, high volume, no key. Keep as first-class.
- Certificate Transparency: crt.sh — free.
- RDAP / public DNS.
- GitHub API (free personal access token, rate-limited).
- Gravatar (public).
- Public / curated ethical username-presence checkers.
- Free SERP: DuckDuckGo HTML/lite adapters + optional self-hosted Searx (fully free, no key).
- Official free broker registries (California SB 362, Vermont, etc.) via update-brokers equivalent.
- Public paste sites / leak indexes that allow free public search (ethical, rate-limited, consented).
- archive.org / public web archives.
- Credit freeze checklist links (public free).
- Local Ollama for grounded narratives.
- Local known-breach metadata (carefully licensed public lists) + user-supplied “I was in X”.
**Fallback chain for breaches (free-first):**  
XposedOrNot (primary) → other free public checkers (rate-limited) → local/public breach name cache → user-reported → **optional paid HIBP Breach API** (feature-flagged only).
**HIBP full email Breach API:** Paid → optional feature flag only. Never required. Never block scoring if absent.
**CAPTCHA:** Free-first = manual queue + “open in browser” + user-solve. CapSolver optional paid. AIDR already optional — preserve and strengthen.
**Dark / deep free path:** Public free indexes, free research feeds, Tor-accessible public pages (read-only, rate-limited, ethical). No paid dark intel required. Honest UI about limitations.
**Infra:** Self-host Postgres/Redis/Caddy or free-tier. GitHub Actions free. No paid SaaS required for MVP.
**Implementation rules for free APIs:**
- Always use SDK RateLimiter + Cache.
- Surface skips / rate-limit hits honestly in scan status (never silent).
- Per-user scan quotas so one user cannot burn the shared free tier.
- Consent + egress_ledger for every call that sends an identifier.
- Attribution in UI/docs for XposedOrNot (and AIDR).
Any new connector must declare Green/Amber/Red and free/paid status. Red excluded. Paid-only stay behind flags.
---
## 13. AI Coding Rules (ABSOLUTE)
(Previous 19 rules +)  
20. Prefer XposedOrNot as the default breach source. Never make HIBP or any paid key required for core path.  
21. When implementing breach connectors, implement caching + rate-limit handling + fallback chain + attribution.  
22. Consult AIDR mapping for remediation; map old HIBP usage to XposedOrNot primary.
---
## 14–23. Coding Standards, Layering, API, DTOs, Testing, Git, Sprint, Quality Gates, DoR/DoD, AC Philosophy
(Unchanged in substance. All tests must cover the free path including XposedOrNot success, rate-limit, cache-hit, and fallback behavior with synthetic data.)
---
## 24. Permanent Engineering Decisions
1–12 as before.  
13. **Core path never requires paid API keys.** XposedOrNot (free/keyless personal) + Pwned Passwords + other free sources are sufficient.  
14. AIDR concepts remapped and improved under DigiZafe rules with attribution.  
15. Free-API rate limits and caching are first-class (not afterthoughts).  
16. Honest attribution and ToS respect for XposedOrNot (and all free providers).
---
## 25. Common Implementation Mistakes to Avoid
(Previous list +)  
- Making HIBP Breach key or CapSolver or XposedOrNot paid tier required.  
- Ignoring XposedOrNot free-tier rate limits or failing to cache.  
- Forgetting attribution or consent/egress for XposedOrNot.  
- Claiming “full HIBP coverage” when using free alternatives.  
- Silent free-source failures.  
- Porting AIDR HIBP client without switching primary to XposedOrNot + free path.
---
## 26. AI Agent Operating Loop
(Unchanged + prefer free path; when touching breach code, default to XposedOrNot.)
---
## 27. Current Project Status
- Vision, free-first policy (XposedOrNot primary), full AIDR integration, and this master context: **COMPLETE (v2.1)**.  
- Formal freeze set (SAD / Architecture Review / SRS / SDD / DIP): complete in Sprint 0 then freeze.  
- Implementation: start at Sprint 0.  
- Next action: Sprint 0 Foundations + produce/freeze the five documents + create `docs/aidr-mapping/` (include XposedOrNot mapping) + free-source inventory.  
- Load **this file** at the start of every session.
---
## 28. Implementation Roadmap (Free-First + AIDR + XposedOrNot)
| Sprint | Scope | Effort | Depends |
|--------|-------|--------|---------|
| **0 Foundations** | Repo, Docker, config, logging, Alembic, health, CI, ADR stubs, model-card template, AIDR mapping skeleton, free-source inventory (XposedOrNot first) | 5 | — |
| **1 Auth & Crypto** | Argon2, JWT+refresh/reuse, MFA, KeyService, Audit, RLS | 8 | 0 |
| **2 Identifiers & Verification** | Canonicalization, EgressFetcher (SSRF), email/DNS/GitHub verify, revalidation, verified-only trigger design | 9 | 1 |
| **3 Connector SDK & Free Surface Green** | SDK (RateLimiter+Cache mandatory), **xposedornot (primary)**, pwned_passwords, crt.sh, RDAP/DNS, GitHub, Gravatar, username presence, consent+egress ledger, admin toggle, free SERP (DDG/Searx) | 11 | 2 |
| **4 Discovery & Evidence** | Postgres scan state machine + reconcile, 3-layer evidence, TTL, SSE, activate verified-only trigger, XposedOrNot → findings normalization | 10 | 3 |
| **5 Identity Graph & PDSS Scoring** | Deciban + review + collision, full PDSS vector + surprisal two-track, reuse, explanation records (incl. XposedOrNot drivers), model card v1, history, what-if | 12 | 4 |
| **6 Recommendations & Alerts** | Two-lane + DAG, dispute→rescore, deltas, alerts, quota rescans | 8 | 5 |
| **7 Remediation Engine (AIDR core)** | Playbooks, Playwright runners, broker_optout_state, verify loop, free CAPTCHA/manual path, freeze/know/complaints, closed-loop re-score (now fed by free XposedOrNot), update-brokers | 14 | 5–6 |
| **8 Privacy, Rights, Explain backend** | Export, crypto-shred+purge, consent center, audit, counterfactual + grounded narrative (Ollama) | 8 | 6–7 |
| **9 Frontend Core** | Auth, identifiers, scan SSE, findings, PDSS breakdown + vector, recommendations, basic graph | 10 | 4–8 |
| **10 Frontend Creative + Remediation UX** | Risk autopsy, what-if, narrative briefing, remediation console, privacy center, a11y, onboarding | 10 | 9 |
| **11 Deep + Constrained-Dark free Amber** | Gated free public adapters, layer tags, honest copy, extra consent | 8 | 4,10 |
| **12 Optional free residual ML** | Synthetic features, train, ONNX, residual flag, SHAP, eval harness | 10 | 5,11 |
| **13 Hardening, Load, Deploy, Docs** | Security suite, load, CI/CD, backup drill, monitoring, runbooks, ethics, AIDR + XposedOrNot attribution final, release v1.0.0 | 8 | all core |
**Critical path:** 0→1→2→3→4→5→6→7→9.  
**MVP (100% free path with strong AIDR remediation + XposedOrNot):** ~16–20 weeks.  
**Cut order if slipping:** 12 → advanced narrative → 11; never cut verify / free surface (incl. XposedOrNot) / PDSS / explain records / AIDR-style remediate with free CAPTCHA path / privacy rights.
---
## 29. Relationship to AIDR (auto-identity-remove) — Explicit
- **Repo:** https://github.com/stephenlthorn/auto-identity-remove  
- **Role:** Primary prior art for remediation + broker + verify + SERP + freeze + know + complaints + state + scoring-signal subsystem.  
- **Breach signal update:** AIDR’s HIBP client / breachCount → DigiZafe **XposedOrNot primary** (free) + Pwned Passwords + optional HIBP. All other AIDR strengths kept and improved under DigiZafe rules (RLS, DTOs, consent, crypto-shred, free CAPTCHA path, closed loop into PDSS).  
- Detailed mapping in `docs/aidr-mapping/`. Attribution required. License compliance required.
---
## 30. Ethics & Research Notes
- Constrained-Dark = public free indexes only.  
- Honest limitation copy.  
- Synthetic + user studies preferred.  
- **XposedOrNot:** Use free tier for personal/low-volume self-only checks; attribute clearly; respect rate limits and ToS; do not resell their data; contact them for higher commercial needs. Same honesty for every free provider.  
- Publish methods, not people’s data.  
- Free and open by default.
---
*End of MASTER_ENGINEERING_CONTEXT.md (v2.1 Final)*  