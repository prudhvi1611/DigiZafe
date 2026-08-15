# Identity Graph & PDSS (Sprint 5)

## After a scan
1. `POST /api/v1/scores/compute` `{"identifier_id":"...","persist":true}`
2. Or rely on post_scan hook if enabled
3. `GET /api/v1/scores/latest?identifier_id=`
4. `GET /api/v1/scores/{id}/explanations`

## Identity graph
1. Add & verify multiple identifiers
2. `POST /api/v1/identity/graph/rebuild`
3. Review collisions: `POST /api/v1/identity/edges/{id}/review` `{"review_status":"accepted"}`
4. Re-score — environmental boost applies for accepted edges

## What-if
`POST /api/v1/scores/whatif`  
`{"identifier_id":"...","exclude_finding_ids":["..."],"exclude_sources":["serp_ddg"]}`

## Catalogs
- `shared/score_model/pdss_catalog.json`
- `shared/score_model/deciban-weights.json`
