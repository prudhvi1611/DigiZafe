# Auth Runbook (Sprint 1)

- Register: POST /api/v1/auth/register
- Login (JSON + MFA): POST /api/v1/auth/login/json
- Refresh: POST /api/v1/auth/refresh  (rotation + reuse detection)
- MFA setup → enable with TOTP code
- Master key: secrets/master.key (32 bytes). Never commit.
- Audit actions: auth.register, auth.login.*, auth.mfa.*, auth.refresh.*
