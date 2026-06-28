---
applyTo: "backend/tests/**"
---

## Testing — pytest + FastAPI TestClient

- Use fixtures from `backend/tests/conftest.py`.
- Prefer `client_user_1` for unit tests.
- Use `client_unauth` only for real cookie/JWT auth-flow tests.
- NEVER hand-write tokens or override dependencies in individual test files.
- After any `models.py` change, verify existing tests and cover: response fields, create/update acceptance, and validation behavior.
- Run the narrowest scope: `pytest backend/tests/<touched_area>/`.
