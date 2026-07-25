"""Tests for velo.logging."""

from __future__ import annotations

import logging

import pytest

from velo.logging import get_logger, setup_logging


@pytest.fixture(autouse=True)
def _reset_logger():
    import velo.logging as log_mod
    log_mod._logger = None
    yield
    log_mod._logger = None


def test_setup_logging_returns_logger():
    logger = setup_logging()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "velo"


def test_get_logger_returns_same_instance():
    logger1 = setup_logging()
    logger2 = get_logger()
    assert logger1 is logger2


def test_setup_logging_is_idempotent():
    logger1 = setup_logging()
    logger2 = setup_logging()
    assert logger1 is logger2


def test_logger_has_console_handler():
    logger = setup_logging()
    handlers = logger.handlers
    console_handlers = [
        h for h in handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    ]
    assert len(console_handlers) >= 1


def test_logger_level_defaults_to_info():
    logger = setup_logging()
    assert logger.level == logging.INFO


def test_logger_level_custom():
    logger = setup_logging(level="DEBUG")
    assert logger.level == logging.DEBUG


def test_logger_with_file_handler(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    logger = setup_logging(level="DEBUG", log_dir=str(log_dir))
    log_file = log_dir / "velo.log"
    assert log_file.exists()

    logger.handlers.clear()


def test_log_messages_are_formatted(tmp_path):
    log_file = tmp_path / "velo.log"
    logger = setup_logging(log_dir=str(tmp_path))
    logger.info("test message %d", 42)
    for h in logger.handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "test message 42" in content
    assert "INFO" in content


def test_get_logger_without_setup_returns_logger():
    logger = get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "velo"