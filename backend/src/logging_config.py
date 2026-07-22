import logging
from http import HTTPStatus

try:
    from sentry_sdk.integrations.logging import BreadcrumbHandler, EventHandler as SentryEventHandler
    _SENTRY_LOGGING_AVAILABLE = True
except ImportError:
    _SENTRY_LOGGING_AVAILABLE = False

# ANSI color codes
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"

_LEVEL_COLORS = {
    logging.DEBUG: CYAN,
    logging.INFO: GREEN,
    logging.WARNING: YELLOW,
    logging.ERROR: RED,
    logging.CRITICAL: f"{BOLD}{RED}",
}


class ColorFormatter(logging.Formatter):
    """Logging formatter that colorizes the level name."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


class SkipSentryFilter(logging.Filter):
    """Suppress records marked to skip Sentry while leaving them in normal logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "skip_sentry", False)


def setup_logging() -> None:
    """Configure root and application loggers."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_access_logger() -> logging.Logger:
    """Return the api.access logger with its own colored stream handler."""
    return get_logger("api.access")


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with a colored stream handler."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ColorFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
        logger.addHandler(handler)
        if _SENTRY_LOGGING_AVAILABLE:
            breadcrumb_handler = BreadcrumbHandler(level=logging.DEBUG)
            breadcrumb_handler.addFilter(SkipSentryFilter())
            logger.addHandler(breadcrumb_handler)

            sentry_handler = SentryEventHandler(level=logging.WARNING)
            sentry_handler.addFilter(SkipSentryFilter())
            logger.addHandler(sentry_handler)
        logger.propagate = False
    return logger


def disable_uvicorn_access_log() -> None:
    """Disable Uvicorn's default access log after it has been configured."""
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False


def color_status(status_code: int) -> str:
    """Return ANSI-colored HTTP status code with reason phrase."""
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        phrase = ""
    label = f"{status_code} {phrase}" if phrase else str(status_code)
    if status_code < 300:
        return f"{GREEN}{label}{RESET}"
    elif status_code < 400:
        return f"{CYAN}{label}{RESET}"
    elif status_code < 500:
        return f"{YELLOW}{label}{RESET}"
    else:
        return f"{RED}{label}{RESET}"
