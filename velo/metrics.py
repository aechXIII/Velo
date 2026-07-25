"""Lightweight performance metrics for Velo."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Timer:
    """Simple timer for measuring durations."""
    _start: float = 0.0

    def start(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000


@dataclass
class Counter:
    """Thread-safe counter for metrics."""
    value: int = 0
    _last_reset: float = field(default_factory=time.perf_counter)

    def increment(self, amount: int = 1) -> None:
        self.value += amount

    def rate_per_second(self) -> float:
        elapsed = time.perf_counter() - self._last_reset
        if elapsed <= 0:
            return 0.0
        return self.value / elapsed


class Metrics:
    """Simple metrics collector."""

    def __init__(self) -> None:
        self.counters: dict[str, Counter] = defaultdict(Counter)
        self.timers: dict[str, Timer] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name].increment(amount)

    def timer_start(self, name: str) -> None:
        t = Timer()
        t.start()
        self.timers[name] = t

    def timer_elapsed(self, name: str) -> float:
        t = self.timers.get(name)
        if t is None:
            return 0.0
        return t.elapsed_ms()

    def snapshot(self) -> dict[str, Any]:
        return {
            name: c.value for name, c in self.counters.items()
        }

    def reset(self) -> None:
        self.counters.clear()
        self.timers.clear()


# Global metrics instance
metrics = Metrics()
