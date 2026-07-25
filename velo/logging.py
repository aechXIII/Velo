"""Structured logging for Velo."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_logger: logging.Logger | None = None


def setup_logging(level: str = "INFO", log_dir: str | None = None) -> logging.Logger:
    """Configure structured logging with file + console output."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("velo")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(console)

    if log_dir:
        log_path = Path(log_dir) / "velo.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
        ))
        logger.addHandler(file_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger, setting up with defaults if not configured."""
    if _logger is None:
        return setup_logging()
    return _logger