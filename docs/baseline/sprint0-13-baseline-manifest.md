# Sprint 0-13 Baseline Manifest

## Repository State
- **Git Commit**: `untracked on main`
- **Migration Head**: `56863a2cf14f`

## Infrastructure
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Backend**: Python 3.12 (FastAPI, Celery)
- **Frontend**: Node 20 (React, Vite, TS)

## System Toggles
- `Deep Amber`: ENABLED (Requires active consent verification)
- `Constrained-Dark`: DISABLED (Requires environment variables and whitelist)
- `Groq Narrative`: OPTIONAL (Falls back to deterministic text)
- `Residual ML`: OPTIONAL (Disabled by default)

## Security Baseline
- **Zero Egress**: Verified via strict HTTP boundary blocking.
- **Cross-user Isolation**: Verified via RLS and middleware testing.
- **Crypto-Shred**: Present.
