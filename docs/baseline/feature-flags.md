# Feature Flags Inventory

| Flag / Setting | Default | Production Rec | Owner | Failure Behavior |
|---|---|---|---|---|
| `FEATURE_DEEP_AMBER` | `True` | ENABLED | Privacy Team | Safe fallback to Surface only. Blocks on missing consent. |
| `FEATURE_CONSTRAINED_DARK` | `False` | DISABLED | Privacy Team | Fails closed if missing specific allowed policies. |
| `FEATURE_GROQ_NARRATIVE` | `False` | ENABLED | Product | Produces deterministic `GroundedFallback` string. |
| `FEATURE_RESIDUAL_ML` | `False` | DISABLED | Data Science | Falls back entirely to authoritative PDSS score. |
| `AMBER_SCAN_REQUIRES_CONSENT` | `True` | ENABLED | Security | Explicit 403 / Egress block on missing consent grant. |
