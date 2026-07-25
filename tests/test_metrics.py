"""Tests for velo.metrics."""

from __future__ import annotations

import time

from velo.metrics import Counter, Metrics, Timer


class TestTimer:
    def test_elapsed_ms_positive_after_start(self):
        t = Timer()
        t.start()
        time.sleep(0.01)
        elapsed = t.elapsed_ms()
        assert elapsed > 0

    def test_elapsed_ms_returns_number_before_start(self):
        t = Timer()
        elapsed = t.elapsed_ms()
        assert isinstance(elapsed, float)
        assert elapsed >= 0


class TestCounter:
    def test_increment(self):
        c = Counter()
        c.increment()
        assert c.value == 1
        c.increment(5)
        assert c.value == 6

    def test_rate_per_second_positive(self):
        c = Counter()
        c.increment(10)
        time.sleep(0.01)
        rate = c.rate_per_second()
        assert rate > 0

    def test_rate_per_second_zero_when_empty(self):
        c = Counter()
        assert c.rate_per_second() == 0.0


class TestMetrics:
    def test_increment_and_snapshot(self):
        m = Metrics()
        m.increment("events", 5)
        m.increment("errors", 2)
        snap = m.snapshot()
        assert snap == {"events": 5, "errors": 2}

    def test_snapshot_empty(self):
        m = Metrics()
        assert m.snapshot() == {}

    def test_reset_clears_counters(self):
        m = Metrics()
        m.increment("events", 10)
        m.reset()
        assert m.snapshot() == {}

    def test_reset_clears_timers(self):
        m = Metrics()
        m.timer_start("render")
        m.reset()
        assert m.timer_elapsed("render") == 0.0

    def test_timer_elapsed_unknown_returns_zero(self):
        m = Metrics()
        assert m.timer_elapsed("nonexistent") == 0.0

    def test_timer_measures_elapsed(self):
        m = Metrics()
        m.timer_start("test")
        time.sleep(0.01)
        elapsed = m.timer_elapsed("test")
        assert elapsed > 0