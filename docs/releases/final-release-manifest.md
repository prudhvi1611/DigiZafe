# Final Release Manifest

## Version
- **Release Version:** v1.0.0-rc1
- **Git Commit SHA:** (unavailable in current environment)
- **Build Timestamp:** 2026-07-15

## Database & Migrations
- **Migration Head:** `c7d13d94607b` (Sprint 25 corrective migration)
- **Historical Migration Integrity:** Verified. RLS enforcement is contained in forward-only migration to preserve canonical history.

## Infrastructure & Runtimes
- **PostgreSQL:** 16-alpine
- **Redis:** 7-alpine
- **Python:** 3.12-slim
- **Node:** 20 (via Vite build)

## Verification Results
- **Backend Tests:** 101 collected, 101 passed, 0 failures, 0 skipped.
- **Frontend Build:** Passed. Route-level lazy loading and Connector Status Panel verified.
- **CI/CD Result:** Local equivalent (clean-room rehearsal) passed successfully.
- **Performance Baseline:** Bounded and completed successfully.
- **Resilience / Soak Test:** Celery fail-over verified.
- **Backup & Restore:** Runbook verified with disposable schema test.
- **Privacy Export & Crypto-Shred:** Passed. Cross-user isolation verified with PostgreSQL RLS.

## Connector States
- **Maigret:** 
  - Availability: `TEST_ONLY`
  - Runtime: None
  - Adapter Version: `0.4.4-adapter`
- **OSINTgram:**
  - Availability: `TEST_ONLY`
  - Runtime: None
  - Adapter Version: `1.1.0-mock`

## Security Audit
- **P0/P1 Findings:** 0
- **Secret Scan:** Clean. No raw secrets exposed in logs, configuration, or telemetry.
- **Dependency Audit:** Passed.

## Known Limitations
- OSINTgram and Maigret runtimes are not installed by default and operate in safe/mock test mode.
- Avatar similarity relies on simple image hashing (not biometric) and is scored as low/moderate evidence.

## Final Decision
**FINAL GO**
The core platform is fully verified and stable as a production release candidate. External connector availability is explicitly documented and appropriately restricted to prevent false production claims.
