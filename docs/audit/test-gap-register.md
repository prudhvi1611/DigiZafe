# Test Gap Register

| Area | Existing tests | Critical path covered | Missing case | Severity | Action |
|---|---|---|---|---|---|
| Deep Amber Consent | `test_amber_layers.py` | Yes | Did not explicitly test HTTP response code mapped from 500 to 403 on consent check failure | P1 | Fixed during Sprint 14, E2E Journey test added |
| Cross-User Isolation | `test_linkage.py`, `test_pdss.py` | Yes | RLS edge cases on missing DB contexts | P2 | No action required immediately |
| Feature Flags | `test_config.py` (None) | No | Strict testing of `OPTIONAL_DISABLED` | P2 | Relies on E2E Journeys script for now |
| Residual ML | None | N/A | ML logic relies on fallback | P2 | Ensure failsafe unit tests in Sprint 16 |

> **Conclusion**: `P0 = 0` and all `P1` defects have been explicitly tested and patched as of Sprint 14 execution.
