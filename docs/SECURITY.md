# Security Notes

## Authentication
- JWT (HS256) with 12h default expiry.
- Bootstrap admin via `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`.
- Password hashing: bcrypt (12 rounds).

## Authorization
- Roles: `admin` · `reviewer` · `viewer`.
- Most read endpoints are open in prototype mode; production should add `Depends(require_role(...))`.

## Hardening for production
1. Set a strong `APP_SECRET_KEY` (32+ random chars).
2. Rotate the admin password immediately.
3. Front the app with nginx + HTTPS (Let's Encrypt).
4. Set `APP_ENV=production` (disables /docs in future when add-guard).
5. Run as non-root user inside Docker (already configured to run as the default uvicorn user).
6. Mount `./data` as a separate volume with restrictive permissions.

## SQL safety
- NL→SQL chat endpoint **strictly rejects** any non-SELECT statement and forbids `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/ATTACH/PRAGMA`.
- All ORM queries are parameterized.

## Validation expression sandbox
- Whitelisted builtins only: `abs, min, max, round, len, int, float, str, bool`.
- No file/network access from expressions.

## File handling
- Upload size cap: 25 MB.
- Allowed MIME types: JPEG/PNG/WebP/PDF.
- SHA-256 hashes stored for dedup.

## Secrets
- All AI provider keys are env-only and never returned by `/api/v1/settings` (which only exposes booleans).
