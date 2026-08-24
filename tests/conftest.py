"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_config_map() -> dict:
    return {
        "host": "127.0.0.1",
        "port": 27180,
        "auth_token": "test-token",
        "auth_enabled": True,
        "capture_mode": "relative",
        "invert_y": False,
        "sensitivity": 1.0,
        "view_mode": "infinite",
        "camera_lag": 0.15,
        "motion_scale": 1.0,
        "motion_ease": 0.2,
        "trail_enabled": True,
        "trail_lifetime_ms": 1100,
        "trail_max_points": 120,
        "trail_width": 2.4,
        "canvas_width": 640,
        "canvas_height": 360,
        "show_stats": False,
        "stats_dpi": 800,
        "stats_update_rate": 24,
        "update_check_mode": "launch",
    }
