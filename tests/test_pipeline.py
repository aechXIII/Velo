"""Tests for velo.pipeline."""

from __future__ import annotations

import math

from velo.constants import (
    IDLE_DECAY_FACTOR,
    IDLE_THRESHOLD,
    MIN_MOVE_DISTANCE,
    SMOOTHING_WEIGHT_NEW,
    SMOOTHING_WEIGHT_OLD,
)
from velo.pipeline import EventPipeline


def test_smoothing_weights_are_valid():
    assert 0 < SMOOTHING_WEIGHT_NEW < 1
    assert 0 < SMOOTHING_WEIGHT_OLD < 1
    assert abs(SMOOTHING_WEIGHT_NEW + SMOOTHING_WEIGHT_OLD - 1.0) < 1e-9


def test_calculate_speed():
    dist = 100.0
    dt = 0.016
    speed = dist / dt
    expected = speed
    assert speed > 0
    assert math.isclose(speed, expected, rel_tol=1e-9)


def test_apply_smoothing():
    prev_speed = 500.0
    new_speed = 1000.0
    smoothed = prev_speed * SMOOTHING_WEIGHT_NEW + new_speed * SMOOTHING_WEIGHT_OLD
    assert smoothed > prev_speed
    assert smoothed < new_speed


def test_idle_threshold_is_reasonable():
    assert 0 < IDLE_THRESHOLD < 1.0


def test_idle_decay_factor_is_reasonable():
    assert 0 < IDLE_DECAY_FACTOR < 1.0


def test_min_move_distance_is_small():
    assert 0 < MIN_MOVE_DISTANCE < 0.1


def test_pipeline_initializes(tmp_path):
    from velo.config import ConfigStore
    from velo.mouse_capture import MouseCapture
    from velo.server import VeloServer

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    capture = MouseCapture()
    server = VeloServer(config)

    pipeline = EventPipeline(config, capture, server)
    assert pipeline.config is config
    assert pipeline.capture is capture
    assert pipeline.server is server

    stats = pipeline.stats_snapshot()
    assert "speed" in stats
    assert stats["speed"] == 0.0
    assert stats["clicks"] == 0


def test_reset_stats(tmp_path):
    from velo.config import ConfigStore
    from velo.mouse_capture import MouseCapture
    from velo.server import VeloServer

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    capture = MouseCapture()
    server = VeloServer(config)

    pipeline = EventPipeline(config, capture, server)
    stats = pipeline.reset_stats()
    assert stats["speed"] == 0.0
    assert stats["peak_speed"] == 0.0
    assert stats["distance"] == 0.0
    assert stats["cps"] == 0.0
    assert stats["clicks"] == 0


def test_capture_configuration_applies_sensitivity(tmp_path):
    from velo.config import ConfigStore

    class Capture:
        def configure(self, **kwargs):
            self.options = kwargs

    class Server:
        client_count = 0

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    config.update({"sensitivity": 2.5}, persist=False)
    capture = Capture()
    pipeline = EventPipeline(config, capture, Server())
    pipeline._apply_capture_config()
    assert capture.options["sensitivity"] == 2.5
