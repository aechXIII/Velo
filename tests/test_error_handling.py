"""Tests for velo.error_handling."""

from __future__ import annotations

import logging

import pytest

from velo.error_handling import safe_call, safe_thread


class TestSafeThread:
    def test_catches_exception_and_logs(self, caplog):
        @safe_thread("test-thread")
        def run():
            raise ValueError("boom")

        with caplog.at_level(logging.ERROR):
            result = run()

        assert result is None
        assert "Thread 'test-thread' crashed" in caplog.text
        assert "ValueError" in caplog.text

    def test_passes_through_normal_return(self):
        @safe_thread("test-thread")
        def run():
            return 42

        result = run()
        assert result == 42

    def test_preserves_function_name(self):
        @safe_thread("test-thread")
        def my_func():
            pass

        assert my_func.__name__ == "my_func"

    def test_uses_func_name_when_no_name_given(self, caplog):
        @safe_thread()
        def my_func():
            raise RuntimeError("fail")

        with caplog.at_level(logging.ERROR):
            my_func()

        assert "Thread 'my_func' crashed" in caplog.text


class TestSafeCall:
    def test_returns_default_on_exception(self, caplog):
        wrapped = safe_call(lambda: 1 / 0, default=99)

        with caplog.at_level(logging.ERROR):
            result = wrapped()

        assert result == 99
        assert "Error in" in caplog.text

    def test_passes_through_normal_return(self):
        wrapped = safe_call(lambda: "hello", default="fallback")
        result = wrapped()
        assert result == "hello"

    def test_preserves_function_name(self):
        def original():
            pass

        wrapped = safe_call(original)
        assert wrapped.__name__ == "original"

    def test_log_level_custom(self, caplog):
        wrapped = safe_call(lambda: 1 / 0, default=None, log_level="warning")

        with caplog.at_level(logging.WARNING):
            wrapped()

        assert "Error in" in caplog.text

    def test_passes_through_args(self):
        wrapped = safe_call(lambda a, b: a + b, default=0)
        result = wrapped(3, 4)
        assert result == 7