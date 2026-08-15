# Privacy, Rights, Explain (Sprint 8)

## Export
`POST /api/v1/privacy/export` → `GET /api/v1/privacy/export/{id}`  
JSON package: identifiers, findings, scores, consent, audit/egress (optional).  
No password hashes, MFA secrets, or refresh tokens.

## Consent center
`GET/POST /privacy/consent`, `POST /privacy/consent/revoke`  
Purposes e.g. `discovery.xposedornot`, `remediation.broker_optout`, `verification.github`.

## Audit + egress transparency
`GET /privacy/audit`, `GET /privacy/egress`

## Erasure (crypto-shred)
Confirm phrase: `DELETE MY DIGIZAFE ACCOUNT`  
`POST /privacy/account/delete` → grace (or immediate in dev) → shred secrets + purge PII tables.

## Grounded narrative
`POST /privacy/narrative` — Ollama if up, else deterministic template from PDSS facts only.  
`GET /privacy/counterfactuals` — durable what-if from score snapshot.

## Ollama (optional)
