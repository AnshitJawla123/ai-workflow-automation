# 🏘 Multi-Tenant Workspace Model

## Why
The brief requires a hosted demo where evaluators can test the system. Without tenant isolation, every visitor sees every other visitor's uploads — confusing and unsafe.

## Model

Every request resolves to an **owner_id** (the tenant key) via one of two routes:

| Source | When | owner_id format |
|---|---|---|
| **JWT user** | Authenticated request (`Authorization: Bearer <jwt>`) | `user:<user_id>` |
| **Signed workspace cookie** | Anonymous request | `ws:<random_hex>` |

The cookie is **httpOnly + SameSite=Lax + Signed** with `APP_SECRET_KEY` (HMAC-SHA256). 90-day expiry. Set automatically on first response.

## Visibility rules

Every list/get endpoint filters with:
```sql
WHERE owner_id = :current_owner OR is_sample = TRUE
```

- **Your own docs** — full read + write
- **Samples** — read-only for everyone (admins can edit)
- **Other workspaces' docs** — invisible (also 403 on direct GET)

## Quotas (configurable via env)

| Setting | Default | Purpose |
|---|---|---|
| `WORKSPACE_DOC_LIMIT` | 50 | Max docs per workspace |
| `WORKSPACE_STORAGE_BYTES` | 50 MB | Max total storage per workspace |
| `WORKSPACE_COOKIE_DAYS` | 90 | Cookie lifetime |
| `ALLOW_ANONYMOUS` | true | Set false to force signup |

When a quota is hit, upload returns `429 Too Many Requests` with a friendly message in the response body.

## Workspace endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/workspace/me` | Returns current owner_id, anonymous flag, usage |
| `POST` | `/api/v1/workspace/reset` | Wipes ONLY your uploads (samples kept) |
| `POST` | `/api/v1/workspace/new` | Rotates your cookie → fresh workspace |

The UI sidebar shows:
- 🗂 Workspace ID (truncated)
- N/50 docs · KB used / 50 MB
- Anonymous badge (amber) when not signed in
- "↺ Reset" and "+ New" buttons

## Verified isolation

We ran a live two-browser test:

```
User1 cookie: ws:894d65b973b9417c
User2 cookie: ws:ef050a3370184854

User1 uploads Image1 → doc id 7 created
User1 sees 7 docs (6 samples + 1 private)  ✅
User2 sees 6 docs  (no leak)               ✅
User2 GET /documents/7 → 403 Forbidden    ✅
User2 reset wipes 0 docs (correctly own-scope) ✅
```

## What's NOT enforced (yet)

- No rate-limit on requests/sec — add Cloudflare or nginx limit_req if exposing publicly at scale
- No virus scan on uploads — wire ClamAV via webhook if accepting untrusted input
- No GDPR-grade deletion log — `workspace/reset` does hard-delete only; add audit retention if needed

## Migration path to full SSO

Replace `current_owner` dependency with an OIDC token resolver. All tenancy logic is centralized in `app/core/workspace.py` — single file change.
