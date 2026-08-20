"""Structured logging for Velo."""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logger: logging.Logger | None = None

_TOKEN_PATTERNS = (
    re.compile(r"(?i)([?&]token=)[^&\s]+"),
    re.compile(r"(?i)(Authorization:\s*Bearer\s+)[^\s]+"),
    re.compile(r'(?i)([\"\']auth_token[\"\']\s*[:=]\s*[\"\'])[^\"\']+'),
)


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
            for pattern in _TOKEN_PATTERNS:
                rendered = pattern.sub(r"\1<redacted>", rendered)
            record.msg = rendered
            record.args = ()
        except (TypeError, ValueError):
            # Malformed log args must never crash logging or bypass redaction;
            # fall through and log the record as-is rather than raising here.
            pass
        return True


def log_dir() -> Path:
    base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    return base / "Velo" / "logs"


def log_path() -> Path:
    return log_dir() / "velo.log"


def setup_logging(level: str = "INFO", log_dir: str | None = None) -> logging.Logger:
    """Configure structured logging with file + console output."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("velo")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()

    redactor = _RedactingFilter()
    stream = sys.stdout or sys.stderr
    if stream is not None:
        console = logging.StreamHandler(stream)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        console.addFilter(redactor)
        logger.addHandler(console)

    if log_dir:
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / "velo.log"
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
        ))
        file_handler.addFilter(redactor)
        logger.addHandler(file_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger, setting up with defaults if not configured."""
    if _logger is None:
        return setup_logging(log_dir=str(log_dir()))
    return _logger


def install_exception_hooks() -> None:
    logger = get_logger()

    def _sys_hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Unhandled application exception", exc_info=(exc_type, exc_value, exc_traceback))

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        logger.critical(
            "Unhandled exception in thread %s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _sys_hook
    threading.excepthook = _thread_hook
