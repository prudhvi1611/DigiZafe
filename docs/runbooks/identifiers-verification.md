# Identifiers & Verification (Sprint 2)

## G1 Self-only
- Discovery/remediation must call `IdentifierService.require_verified`.
- DB function `digizafe_enforce_verified_identifier()` is installed; attach trigger on scans/findings in Sprint 4.

## Methods
| Type | Method | How |
|------|--------|-----|
| email | email_code | Dev exposes code; prod SMTP later |
| domain | dns_txt | TXT `_digizafe-verify.<domain>` = digizafe-verification=&lt;token&gt; |
| github_username | github_proof | Public gist `digizafe-verify.txt` with token |

## Egress
- All external HTTP via `app.security.egress.EgressFetcher` only.
- Consent + `egress_ledger` for GitHub (and later XposedOrNot).

## API
- `POST /api/v1/identifiers`
- `POST /api/v1/identifiers/{id}/verify/start?method=`
- `POST /api/v1/identifiers/{id}/verify/confirm?challenge_id=`
- `POST /api/v1/identifiers/{id}/revalidate`
