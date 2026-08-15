# Free Sources Inventory (Sprint 3)

## Primary Breach
- **XposedOrNot** — `GET https://api.xposedornot.com/v1/check-email/{email}`  
  Free tier (approx): 2/sec, 25/hour, 100/day per IP.  
  Optional analytics: `/v1/breach-analytics?email=`  
  **Attribution required.** Consent + egress_ledger required (sends email).  
  DigiZafe enforces stricter internal limits + Redis cache (long negative TTL).

## Passwords
- **Pwned Passwords** — `https://api.pwnedpasswords.com/range/{prefix}`  
  k-anonymous (5-char SHA-1 prefix only). No key. No full password egress.

## Surface Green (Sprint 3)
| Connector | Host | Identifier | Notes |
|-----------|------|------------|-------|
| xposedornot | api.xposedornot.com | email | Primary breach |
| pwned_passwords | api.pwnedpasswords.com | password (in-memory) | k-anon |
| crtsh | crt.sh | domain | CT names |
| rdap | rdap.org | domain | Registration public |
| github | api.github.com | username | Optional free PAT |
| gravatar | gravatar.com | email→md5 | Existence only |
| username_presence | curated | username | github/gitlab/reddit only |
| serp_ddg | html.duckduckgo.com | multi | Best-effort HTML |

Paid HIBP Breach API remains **feature-flagged off** and non-load-bearing.
## Sprint 4 persistence
XposedOrNot observations normalize to `findings` with fingerprint dedupe.
Negative results are not findings; they are cached at connector layer only.

## Sprint 11 Amber Sources

### Common Crawl

- Public URL-index metadata adapter.
- Deep Amber only.
- No archived page body retrieval.
- Cache + Redis rate limiting required.
- Results are historical/index metadata and do not prove current exposure.
- Attribution: Common Crawl public index.

### Internet Archive Wayback

- Availability metadata adapter for verified domains.
- Deep Amber only.
- No archived page body retention.
- Historical captures do not prove current exposure.
- Attribution: Internet Archive Wayback Machine.

### Configured Public Index

- Constrained-Dark adapter is disabled by default.
- Requires `FEATURE_CONSTRAINED_DARK=true`.
- Requires `AMBER_PUBLIC_INDEX_URL`.
- Requires `AMBER_PUBLIC_INDEX_HOST_ALLOWLIST`.
- HTTPS only.
- No `.onion`, Tor, marketplace, credentialed, or raw dump access.
- Metadata-only JSON responses.

