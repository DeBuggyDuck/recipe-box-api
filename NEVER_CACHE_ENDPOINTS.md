# Endpoints That Must Never Be Cached

- `/login` — Issues sensitive authentication tokens and session credentials; caching would leak valid JWTs across callers or authenticate wrong identities.
- `/register` — Security-critical account creation handling credentials; responses and mutations must never be shared or served from cache.
- `/recipes/<id>` (Private Recipes) — Returns user-specific protected data guarded by ownership checks; caching could serve private recipes to unauthorized callers.
- `POST /recipes`, `PATCH /recipes/<id>`, `DELETE /recipes/<id>` — State-mutating write operations; caching writes violates HTTP semantics and causes silent data corruption.
