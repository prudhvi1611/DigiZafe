# Frontend Core (Sprint 9)

## Stack
React 18 + TS + Vite + Tailwind + Radix/shadcn-style + TanStack Query + React Router + Recharts + Cytoscape

## Routes
| Path | Purpose |
|------|---------|
| /login, /register | Auth |
| /app | Dashboard + PDSS gauge |
| /app/identifiers | CRUD + verify |
| /app/scans | Start scan + SSE live progress |
| /app/findings | Findings list |
| /app/scores | PDSS breakdown + vector + history |
| /app/recommendations | Two-lane plan |
| /app/identity | Graph |

## Auth
- Access token in memory (Zustand)
- Refresh token in sessionStorage
- Auto-refresh on 401 via `/auth/refresh`

## SSE
Fetch stream with `Authorization` header (not native EventSource).

## Free path UX
Footer attribution for XposedOrNot. Unverified identifiers cannot start scans (API enforces G1).
