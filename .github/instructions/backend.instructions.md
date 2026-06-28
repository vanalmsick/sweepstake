---
applyTo: "backend/**"
---

## Backend — FastAPI + SQLModel

- Domain layout MUST be `backend/src/<domain>/{models.py,crud.py,routers.py}`.
- API docs MUST live only in `routers.py` (endpoint docstrings + field `description=`).
- Auth MUST use HttpOnly cookie JWT with `Depends(verify_access_token)` and `token_payload["uid"]`; NEVER use Authorization headers or redesign auth.
- DB access MUST stay async with `Depends(get_db)`; use `selectinload`, call `db.flush()` before generated IDs, and prefer reusable `_query_x()` filters.
- Keep SQLModel `table=True` models separate from `XCreate`/`XRead`/`XUpdate` schemas.
- NEVER hand-write Alembic migrations; edit SQLModel definitions and rely on startup autogen from `/app/data/db_migrations`.
- Runtime config MUST be in `backend/src/config.py` with load order env -> `data/.env.local` -> `data/.env` -> `data/settings.yaml`; env names MUST match uppercase fields; no hardcoded runtime config.
- If config fields change, update the README env-var table.
- Router tags MUST be from `main.py` `tags_metadata` only: `auth`, `tournament`, `team`, `group`, `match`, `stage`, `predictions`, `stats`, `general`.
- Model cascade (required): when `models.py` fields/types/relationships change, update `crud.py`, `routers.py`, `frontend/src/types/`, then `frontend/src/api/`.
