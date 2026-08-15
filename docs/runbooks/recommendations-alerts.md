# Recommendations & Alerts (Sprint 6)

## Two lanes
| Lane | Meaning | Sprint |
|------|---------|--------|
| guided | Always available user steps (password, MFA, freeze, know, SERP) | 6 |
| semi_automated | Green broker opt-outs | Planned 6, **executed 7** |

## Flow
1. Scan + PDSS (Sprint 4–5)
2. `POST /api/v1/recommendations/generate` `{ "identifier_id": "..." }`
3. Follow DAG order (`depends_on` / `dag_order`)
4. Mark done: `PATCH /api/v1/recommendations/{id}` `{ "status": "done" }`
5. Dispute FP: `POST /api/v1/recommendations/findings/{id}/dispute` → dismiss + rescore
6. Deltas: `GET /api/v1/alerts/deltas`
7. Rescan: `POST /api/v1/alerts/rescan` (quota + cooldown)

## AIDR mapping
| AIDR | DigiZafe Sprint 6 |
|------|-------------------|
| recommendFreeze | credit_freeze template + recommend_freeze() |
| freeze.js targets | recommendation links |
| right-to-know | right_to_know template (generator text Sprint 7/8 full) |
| diff.js | domain/deltas.py + alerts |
| breach severity | triggers on findings from XposedOrNot |

## Free path
No paid APIs. CapSolver not required. Semi-automated lane is queue-only until Sprint 7.
