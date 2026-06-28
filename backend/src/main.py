import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
from pathlib import Path

import sentry_sdk
from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.util import CommandError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine.url import make_url
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=settings.app_version or None,
        environment="backend",
        send_default_pii=False,  # No PII is sent to Sentry.io
        sample_rate=1.0,  # 100% of errors are sent to Sentry.io
        enable_tracing=True,  # Performance monitoring
        traces_sample_rate=0.25,  # 25% of transcations are perfromance monitored
        profiles_sample_rate=1.0,  # 100% of these monitored transactions will have profile
        enable_logs=True,  # Capture logs
    )
from src.logging_config import (
    setup_logging, get_access_logger, disable_uvicorn_access_log, color_status,
)

# Import models to register them with SQLModel
from src.users import models as user_models
from src.tournaments import models as tournament_models
from src.groups_stages import models as group_stage_models
from src.teams import models as team_models
from src.matches import models as match_models
from src.predictions import models as prediction_models

# routers and app-level exceptions
from src.tournaments.routers import router as tournaments_router
from src.teams.routers import router as teams_router
from src.matches.routers import router as matches_router
from src.groups_stages.routers import group_router, stage_router
from src.predictions.routers import (
    predict_tournament_router,
    predict_group_router,
    predict_stage_router,
    predict_match_router,
)
from src.users.routers import router as auth_router
from src.api_football_data.routers import router as football_data_org_router
from src.stats.routers import router as stats_router
from src.exceptions import CustomError, custom_error_handler
from src.scripts.load_test_data import load_test_data
from src.scheduler import build_scheduler, try_acquire_scheduler_lock, release_scheduler_lock


setup_logging()
logger = get_access_logger()


# OpenAPI tags metadata for better documentation organization
tags_metadata = [
    {
        "name": "auth",
        "description": "User authentication and account management. Handles registration, login, logout, password changes, and profile retrieval.",
    },
    {
        "name": "tournament",
        "description": "Tournament management operations. Create, retrieve, update, and delete tournaments. Includes streaming support for large datasets.",
    },
    {
        "name": "team",
        "description": "Team management operations. Create, retrieve, update, and delete teams used in tournament matches.",
    },
    {
        "name": "group",
        "description": "Group management operations. Create, retrieve, update, and delete groups for team grouping within tournaments.",
    },
    {
        "name": "match",
        "description": "Match management operations. Create, retrieve, update, and delete matches within tournaments. Includes goal tracking.",
    },
    {
        "name": "stage",
        "description": "Stage management operations. Create, retrieve, update, and delete stages for match grouping within tournaments.",
    },
    {
        "name": "predictions",
        "description": "Prediction management operations. Create = update, retrieve, and delete predictions for tournaments, groups, stages, and matches.",
    },
    {
        "name": "stats",
        "description": "Statistics and leaderboard endpoints. View aggregated points leaderboard and all participants' predictions once an event has started.",
    },
    {
        "name": "general",
        "description": "General API endpoints including health checks.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(run_alembic_startup_workflow)
    except CommandError as exc:
        logger.error("Alembic command failed during startup: %s", exc)
        raise RuntimeError(f"Alembic migration failed: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected migration error during startup")
        raise RuntimeError(f"Alembic migration failed: {exc}") from exc

    # Disable Uvicorn's default access log; our log_requests middleware replaces it.
    disable_uvicorn_access_log()

    if settings.load_test_data:
        logger.info("--load_test_data flag set. Loading test data...")
        await load_test_data()
        logger.info("Test data loaded successfully.")

    _scheduler_lock = try_acquire_scheduler_lock()
    scheduler = None
    if _scheduler_lock is not None:
        scheduler = build_scheduler()
        scheduler.start()
        logger.info("APScheduler started: session cleanup scheduled daily at 05:00 %s", settings.tz)
    else:
        logger.info("APScheduler: scheduler lock held by another worker, skipping start")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    if _scheduler_lock is not None:
        release_scheduler_lock(_scheduler_lock)

app = FastAPI(
    root_path=settings.root_path,
    title="Sweepstake API",
    description="A secure, scalable API for tournament and user management. Features JWT-based authentication, user registration, tournament CRUD operations, and comprehensive API documentation.",
    version="1.0.0",
    docs_url=None,  # disabled so we can serve a custom version below
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


def _build_alembic_config() -> AlembicConfig:
    project_root = Path(__file__).resolve().parent.parent
    alembic_ini = project_root / "alembic.ini"
    alembic_script_location = project_root / "alembic"

    cfg = AlembicConfig(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_script_location))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _autogenerate_if_needed(cfg: AlembicConfig) -> bool:
    created = {"value": False}

    def _process_revision_directives(context, revision, directives):
        if not directives:
            return

        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            logger.info("No schema changes detected. Skipping migration autogeneration.")
            return

        created["value"] = True

    command.revision(
        cfg,
        message="auto: startup schema sync",
        autogenerate=True,
        process_revision_directives=_process_revision_directives,
    )
    return created["value"]


def _clear_alembic_version(conn) -> None:
    """Reset the alembic_version table after a broken migration chain is detected.

    The chain breaks when migration files are lost (e.g. empty Docker volume)
    while the DB still records their revision IDs.  Clearing the table lets the
    autogenerate step regenerate a single baseline migration from the current
    schema — tables already in place are left untouched.
    """
    logger.warning(
        "Broken migration chain detected (revision files missing from volume). "
        "Clearing alembic_version and regenerating baseline from current schema..."
    )
    conn.execute(text("DELETE FROM alembic_version"))
    conn.commit()


def run_alembic_startup_workflow() -> None:
    cfg = _build_alembic_config()

    url = make_url(settings.database_url)
    is_sqlite = url.drivername.split("+")[0] == "sqlite"

    if is_sqlite:
        # SQLite has no advisory locks and single-writer semantics, so run migrations directly.
        logger.info("Running Alembic upgrade to heads...")
        try:
            command.upgrade(cfg, "heads")
        except CommandError as exc:
            if "Can't locate revision" not in str(exc):
                raise
            sync_url = url.set(drivername="sqlite")
            sync_engine = create_engine(sync_url.render_as_string(hide_password=False))
            with sync_engine.connect() as conn:
                _clear_alembic_version(conn)
            sync_engine.dispose()
        except OperationalError as exc:
            if "already exists" not in str(exc):
                raise
            logger.warning(
                "Tables already exist but alembic_version is not in sync. "
                "Stamping DB at current heads and re-syncing..."
            )
            command.stamp(cfg, "heads")
        logger.info("Checking for schema changes and autogenerating migration if needed...")
        created = _autogenerate_if_needed(cfg)
        if created:
            logger.info("New migration was generated. Applying latest migrations...")
            command.upgrade(cfg, "heads")
        logger.info("Alembic startup migration workflow complete.")
        return

    # Build a synchronous database URL (strip the async driver suffix) so we
    # can hold a PostgreSQL session-level advisory lock for the duration of
    # the migration.  This prevents multiple gunicorn workers from racing to
    # create the same schema objects (e.g. enum types) on a fresh database.
    sync_driver = url.drivername.split("+")[0]  # "postgresql+asyncpg" → "postgresql"
    sync_url = url.set(drivername=sync_driver)
    # render_as_string(hide_password=False) is required — str(URL) redacts the
    # password as "***" for security logging, which breaks the actual connection.
    sync_engine = create_engine(sync_url.render_as_string(hide_password=False))

    # Arbitrary but unique integer key for this application.
    ADVISORY_LOCK_KEY = 20260509

    with sync_engine.connect() as conn:
        # Blocking advisory lock — first worker proceeds, all others wait.
        # Released automatically if the connection drops.
        conn.execute(text(f"SELECT pg_advisory_lock({ADVISORY_LOCK_KEY})"))
        try:
            logger.info("Running Alembic upgrade to heads...")
            try:
                command.upgrade(cfg, "heads")
            except CommandError as exc:
                if "Can't locate revision" not in str(exc):
                    raise
                _clear_alembic_version(conn)

            logger.info("Checking for schema changes and autogenerating migration if needed...")
            created = _autogenerate_if_needed(cfg)
            if created:
                logger.info("New migration was generated. Applying latest migrations...")
                command.upgrade(cfg, "heads")
        finally:
            conn.execute(text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_KEY})"))

    sync_engine.dispose()
    logger.info("Alembic startup migration workflow complete.")


# Add dark mode to API page
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    html = get_swagger_ui_html(openapi_url="openapi.json", title="Sweepstake API")
    dark_mode_css = """
<style>
@media (prefers-color-scheme: dark) {
  body { background-color: #1a1a1a; }
  .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
  .swagger-ui .highlight-code, .swagger-ui img { filter: invert(100%) hue-rotate(180deg); }
}
</style>
"""
    patched = html.body.decode().replace("</head>", dark_mode_css + "</head>")
    return HTMLResponse(patched)


# ============================================================================
# Security middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.hosts,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response



_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)

    # Skip logging healthcheck requests from localhost or Docker healthcheck probe
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    if request.url.path == "/healthcheck" and client_host in _LOCAL_HOSTS and user_agent.startswith("Docker-Healthcheck"):
        return response
    duration = perf_counter() - start

    # Try to extract user_id from access_token cookie
    user_id: str | None = None
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            from jose import jwt as _jwt
            payload = _jwt.decode(
                access_token, settings.secret_key, algorithms=["HS256"],
                options={"verify_exp": False},
            )
            user_id = payload.get("uid")
        except Exception:
            pass

    user_info = f"user_id={user_id}" if user_id is not None else "anonymous"
    status_colored = color_status(response.status_code)

    log_method = logger.info
    if response.status_code >= 500:
        log_method = logger.error
    elif response.status_code >= 400:
        log_method = logger.warning

    log_method(
        '%s:%s (%s) - "%s %s HTTP/%s" %s - %.2fs',
        request.client.host if request.client else "-",
        request.client.port if request.client else "-",
        user_info,
        request.method,
        request.url.path,
        request.scope.get("http_version", "1.1"),
        status_colored,
        duration,
    )
    return response


@app.get("/healthcheck", tags=["general"], response_description="Service health status")
def healthcheck():
    """
    Health check endpoint.

    Use this endpoint to verify that the API is running and accessible.

    **Returns:** Status information (HTTP 200)
    """
    return {"status": 200, "message": "OK", "OK": True}


@app.get("/config", tags=["general"], response_description="Runtime client configuration")
def get_config():
    """
    Public runtime configuration for the frontend.

    Returns settings that the compiled React app cannot know at build time
    (e.g. the Sentry DSN injected as a container env var).
    Empty strings mean the feature is disabled.
    """
    return {"sentry_dsn": settings.sentry_dsn, "app_version": settings.app_version, "demo_mode": settings.demo_mode, "only_superusers_can_create_tournaments": settings.only_superusers_can_create_tournaments}

# include routers
app.include_router(auth_router)
app.include_router(football_data_org_router)
app.include_router(tournaments_router)
app.include_router(teams_router)
app.include_router(matches_router)
app.include_router(group_router)
app.include_router(stage_router)
app.include_router(predict_tournament_router)
app.include_router(predict_group_router)
app.include_router(predict_stage_router)
app.include_router(predict_match_router)
app.include_router(stats_router)

# register app-level exception handlers
app.add_exception_handler(CustomError, custom_error_handler)


if __name__ == "__main__":
    from argparse import ArgumentParser
    import uvicorn

    parser = ArgumentParser(description="Run the FastAPI server")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to run the server on")
    parser.add_argument("--load_test_data", action="store_true", default=False, help="Load test data on startup")
    args = parser.parse_args()

    settings.update(vars(args))

    if settings.port <= 0 or settings.port > 65535:
        raise SystemExit("Port number must be between 1 and 65535 - not {}".format(settings.port))

    uvicorn.run(app, port=settings.port)
