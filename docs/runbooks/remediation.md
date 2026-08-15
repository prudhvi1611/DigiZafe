# Remediation Engine (Sprint 7) — AIDR core

## AIDR → DigiZafe map

| AIDR | DigiZafe |
|------|----------|
| state.json optOuts | `broker_optout_state` (+ RLS) |
| brokers.js | `shared/config/broker_registry/brokers_green.json` + Playwright runner |
| CapSolver | Optional FEATURE_CAPSOLVER; default **manual / open_in_browser** |
| aidr verify | `POST /remediation/verify` |
| aidr freeze | `GET/PATCH /remediation/freeze` |
| aidr know | `POST /remediation/know` |
| aidr complaints | `POST /remediation/complaints` |
| aidr update-brokers | beat `update_brokers_task` |
| aidr run / preview | `POST /remediation/jobs/broker-optout` (`dry_run=true` = preview) |
| Closed loop score | post-job PDSS + recommendations regenerate |

## Free CAPTCHA path
1. Job item → `captcha_needed`
2. `GET /remediation/captcha` for instructions + page_url
3. User completes form in browser OR posts token
4. `POST /remediation/captcha/{id}` `{ "action": "manual_done" }` or `solve`
5. Job resumes in worker

## Flow
1. Verify email (Sprint 2)
2. Generate plan (Sprint 6) → `broker_optout_green`
3. `POST /remediation/jobs/broker-optout` with verified `identifier_id` + profile name/state
4. Poll job; handle captcha/manual
5. `GET /remediation/state` for durable opt-out history (90-day fresh skip)
6. Auto re-score when job completes

## Safety
- G1 verified identifier only
- Green brokers only for automation
- Playwright only in worker
- Consent + egress ledger on broker runs
- CapSolver never required
