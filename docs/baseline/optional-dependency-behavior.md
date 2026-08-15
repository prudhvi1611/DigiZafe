# Optional Dependency Behavior

## 1. Groq Narrative Engine
If the Groq API key is missing, rate-limited (429), or returning a 500:
- The system catches the failure silently.
- It automatically reverts to a deterministic rule-based sentence generator.
- **Verification**: Verified via `test_narrative_fallback.py` in test suite.

## 2. Residual ML Scoring
If the PyTorch models are unavailable or `FEATURE_RESIDUAL_ML=False`:
- PDSS reverts purely to the authoritative graph summation.
- The UI gracefully removes ML labels without throwing 500s.
- **Verification**: Application defaults to False. PDSS logic relies strictly on baseline determinism in `test_pdss.py`.
