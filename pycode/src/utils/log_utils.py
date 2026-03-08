"""
LOG UTILITIES
Centralized logging utility for all PyCode scripts.
Creates date-based log directories, handles log file management,
and configures project-wide logging defaults.

Console philosophy:
  - Our loggers  (aeo_reports, intelliwrite, config, agents, aeo_audit)
                  → INFO+ on console, DEBUG+ in file
  - 3rd-party libs (scrapy, httpx, agno, playwright, advertools, etc.)
                  → WARNING+ on console only, DEBUG+ in file
  - Root logger   → WARNING+ on console, DEBUG+ in file

Created by: Aman Mundra
Date: 2026-02-04
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_FORMAT = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
_CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_DEFAULT_PROJECT_LOGGER = "aeo_blog_engine"

# Loggers that should be visible on the console at INFO level
_OUR_LOGGER_PREFIXES = (
    "aeo_reports",
    "aeo_audit",
    "intelliwrite",
    "config",
    "agents",
    "database",
    "utils",
    "__main__",
)

# 3rd-party loggers that are very noisy — console silenced to WARNING
_SILENT_LOGGERS = [
    "scrapy",
    "advertools",
    "httpx",
    "httpcore",
    "agno",
    "playwright",
    "asyncio",
    "urllib3",
    "requests",
    "openai",
    "anthropic",
    "google",
    "grpc",
    "PIL",
    "filelock",
    "charset_normalizer",
    "py.warnings",
    "werkzeug",          # Flask internal request logs
    "multipart",
    "hpack",
    "h11",
    "h2",
    "twisted",
]

_logging_configured = False


def _coerce_level(level_name: Optional[str]) -> int:
    if not level_name:
        return logging.INFO
    return getattr(logging, level_name.upper(), logging.INFO)


# ---------------------------------------------------------------------------
# Global shared file handler (all logs go here)
# ---------------------------------------------------------------------------
_shared_file_handler: Optional[logging.FileHandler] = None


def _get_shared_file_handler() -> logging.FileHandler:
    global _shared_file_handler
    if _shared_file_handler is None:
        log_path = _build_log_path("pycode_app")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        _shared_file_handler = fh
    return _shared_file_handler


def _build_log_path(name: str) -> str:
    now = datetime.now()
    clean = name.replace(".", "_").replace("/", "_").replace("\\", "_").lstrip("_")
    current_file = Path(__file__)
    pycode_root = current_file.parent.parent.parent
    logs_dir = pycode_root / "logs" / now.strftime("%d-%m-%Y")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir / f"{clean}_{now.strftime('%Y-%m-%d_%H-%M-%S')}.log")


# ---------------------------------------------------------------------------
# Console handler (shared, with our custom filter)
# ---------------------------------------------------------------------------
class _OurLoggersFilter(logging.Filter):
    """Allow only our own loggers through at INFO level on console."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Always show ERROR+ from anyone
        if record.levelno >= logging.ERROR:
            return True
        # Show WARNING+ from anyone
        if record.levelno >= logging.WARNING:
            return True
        # Show INFO from our own loggers only
        return any(record.name.startswith(p) for p in _OUR_LOGGER_PREFIXES)


def setup_logging() -> None:
    """Configure root logger once for the entire application."""
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything at root, filter at handlers

    # Remove any existing handlers (Flask/basicConfig may have added one)
    root.handlers.clear()

    console_fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # === Console handler — filtered to our loggers + warnings ===
    console_h = logging.StreamHandler()
    console_h.setLevel(logging.DEBUG)  # let filter decide
    console_h.setFormatter(console_fmt)
    console_h.addFilter(_OurLoggersFilter())
    root.addHandler(console_h)

    # === File handler — everything ===
    root.addHandler(_get_shared_file_handler())

    # --- Silence the noisiest 3rd-party libs on console ---
    for lib in _SILENT_LOGGERS:
        lib_logger = logging.getLogger(lib)
        # They still go to file (via root propagation), but we cap their
        # effective level so they don't pass INFO/DEBUG to our console filter
        lib_logger.setLevel(logging.WARNING)

    logging.captureWarnings(True)


# Run once at import time
setup_logging()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_logger(
    name: Optional[str] = None,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Get a named logger.
    Logs always go to the shared log file (DEBUG+).
    Console output is controlled by setup_logging() filters.
    """
    setup_logging()
    logger_name = name or _DEFAULT_PROJECT_LOGGER
    logger = logging.getLogger(logger_name)
    # Let propagation handle file + console via root handlers
    logger.propagate = True
    return logger


def get_log_file_path(logger_name: str) -> str:
    """Generate log file path with date-based directory structure."""
    return _build_log_path(logger_name)


def get_daily_log_dir() -> str:
    """Get the current date's log directory path."""
    current_date = datetime.now().strftime("%d-%m-%Y")
    current_file = Path(__file__)
    pycode_root = current_file.parent.parent.parent
    logs_dir = pycode_root / "logs" / current_date
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir)


def log_separator(logger: logging.Logger, char: str = "=", length: int = 60):
    logger.info(char * length)


def log_section(logger: logging.Logger, title: str):
    logger.info("=" * 60)
    logger.info(title)
    logger.info("=" * 60)
