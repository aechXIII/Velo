"""Tests for velo.pipeline."""

from __future__ import annotations

import math
import threading
import time

from velo.constants import (
    IDLE_DECAY_FACTOR,
    IDLE_THRESHOLD,
    MIN_MOVE_DISTANCE,
    SMOOTHING_WEIGHT_NEW,
    SMOOTHING_WEIGHT_OLD,
)
from velo.mouse_capture import MouseEvent
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


def test_capture_configuration_applies_240_hz_stats_rate(tmp_path):
    from velo.config import ConfigStore

    class Capture:
        def configure(self, **kwargs):
            pass

    class Server:
        client_count = 0

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    config.update({"stats_update_rate": 240}, persist=False)
    pipeline = EventPipeline(config, Capture(), Server())

    pipeline._apply_capture_config()

    assert math.isclose(pipeline._stats_interval, 1.0 / 240.0, rel_tol=1e-9)


def test_stats_loop_broadcasts_near_240_hz(tmp_path):
    from velo.config import ConfigStore

    class Capture:
        def configure(self, **kwargs):
            pass

    class Server:
        client_count = 1

        def __init__(self):
            self.broadcast_times = []

        def broadcast_mouse(self, _payload):
            self.broadcast_times.append(time.perf_counter())
            if len(self.broadcast_times) >= 60:
                pipeline._stop.set()

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    config.update({"stats_update_rate": 240}, persist=False)
    server = Server()
    pipeline = EventPipeline(config, Capture(), server)
    pipeline._apply_capture_config()

    pipeline._stats_loop()

    elapsed = server.broadcast_times[-1] - server.broadcast_times[0]
    actual_hz = (len(server.broadcast_times) - 1) / elapsed
    assert 180 <= actual_hz <= 300


def test_stopping_pipeline_interrupts_one_hz_stats_wait(tmp_path):
    from velo.config import ConfigStore

    class Capture:
        def configure(self, **kwargs):
            pass

        def remove_listener(self, _listener):
            pass

        def stop(self):
            pass

    class Server:
        client_count = 0

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    config.update({"stats_update_rate": 1}, persist=False)
    pipeline = EventPipeline(config, Capture(), Server())
    pipeline._apply_capture_config()
    pipeline._stats_thread = threading.Thread(target=pipeline._stats_loop)
    pipeline._stats_thread.start()

    ready_deadline = time.perf_counter() + 1.0
    while pipeline._stats_waiter is None and time.perf_counter() < ready_deadline:
        time.sleep(0.001)
    assert pipeline._stats_waiter is not None

    started = time.perf_counter()
    pipeline.stop()

    assert time.perf_counter() - started < 0.2
    assert not pipeline._stats_thread.is_alive()
    assert pipeline._stats_waiter is None


def _motion_stats_pipeline(tmp_path):
    from velo.config import ConfigStore

    class Capture:
        def configure(self, **kwargs):
            pass

    class Server:
        client_count = 0

        def broadcast_mouse(self, _payload):
            pass

    config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    return EventPipeline(config, Capture(), Server())


def test_peak_speed_uses_unscaled_mouse_counts(tmp_path):
    pipeline = _motion_stats_pipeline(tmp_path)
    events = [
        MouseEvent(t=1.000, dx=20.0, raw_dx=8.0),
        MouseEvent(t=1.008, dx=20.0, raw_dx=8.0),
        MouseEvent(t=1.016, dx=20.0, raw_dx=8.0),
    ]

    for event in events:
        pipeline._handle_mouse(event)

    assert math.isclose(pipeline.stats_snapshot()["peak_speed"], 1000.0)


def test_distance_uses_unscaled_mouse_counts(tmp_path):
    pipeline = _motion_stats_pipeline(tmp_path)

    pipeline._handle_mouse(MouseEvent(t=1.000, dx=12.5, raw_dx=5.0))
    pipeline._handle_mouse(MouseEvent(t=1.010, dx=12.5, raw_dx=5.0))

    assert pipeline.stats_snapshot()["distance"] == 10.0


def test_peak_speed_ignores_sub_window_timing_spike(tmp_path):
    pipeline = _motion_stats_pipeline(tmp_path)

    pipeline._handle_mouse(MouseEvent(t=1.000000, dx=1.0, raw_dx=1.0))
    pipeline._handle_mouse(MouseEvent(t=1.000002, dx=1.0, raw_dx=1.0))

    assert pipeline.stats_snapshot()["peak_speed"] == 0.0

    pipeline._handle_mouse(MouseEvent(t=1.010000, dx=9.0, raw_dx=9.0))

    assert pipeline.stats_snapshot()["peak_speed"] == 0.0

    pipeline._handle_mouse(MouseEvent(t=1.016000, dx=6.0, raw_dx=6.0))

    assert math.isclose(pipeline.stats_snapshot()["peak_speed"], 1000.0)


def test_reset_stats_discards_partial_speed_window(tmp_path):
    pipeline = _motion_stats_pipeline(tmp_path)
    pipeline._handle_mouse(MouseEvent(t=1.000, dx=5.0, raw_dx=5.0))
    pipeline._handle_mouse(MouseEvent(t=1.005, dx=5.0, raw_dx=5.0))

    pipeline.reset_stats()
    pipeline._handle_mouse(MouseEvent(t=1.010, dx=5.0, raw_dx=5.0))

    assert pipeline.stats_snapshot()["peak_speed"] == 0.0
