# Repository Instructions

## Stack
- Backend: FastAPI + SQLModel + Alembic + pytest
- Frontend: React + TypeScript + Vite + RTK Query + Tailwind
- Deploy: `db` (PostgreSQL) + `app` (nginx + gunicorn + React)

## Global Rules
- Keep changes narrow and in-pattern.
- Reuse existing naming/layout; avoid new dependencies unless clearly needed.
- Follow scoped instruction files; do not restate defaults from `general.instructions.md`.
- Run the smallest relevant validation and report only commands actually run.

## Scoped Files
- Backend rules: `.github/instructions/backend.instructions.md`
- Frontend rules: `.github/instructions/frontend.instructions.md`
- Test rules: `.github/instructions/tests.instructions.md`

## Validation Commands
- Backend: `pytest backend/tests/<touched_area>/`
- Frontend: `cd frontend && npm run lint && npm run build`
- Deploy config: `docker compose config` (or full `docker compose up --build`)