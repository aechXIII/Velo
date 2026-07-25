"""Tests for velo.defaults."""

from __future__ import annotations

from velo.defaults import (
    APP_NAME,
    APP_VERSION,
    DEFAULTS,
    FEEL_PRESETS,
    PRESET_EXCLUDE,
    PRESETS,
    QUALITY_PRESETS,
    SHELL_KEYS,
    STATS_UPDATE_HZ,
)


def test_app_name_is_nonempty():
    assert isinstance(APP_NAME, str)
    assert len(APP_NAME) > 0


def test_app_version_is_nonempty():
    assert isinstance(APP_VERSION, str)
    assert len(APP_VERSION) > 0


def test_defaults_has_expected_keys():
    expected = {
        "host",
        "port",
        "auth_token",
        "auth_enabled",
        "capture_mode",
        "sensitivity",
        "view_mode",
        "camera_lag",
        "motion_scale",
        "motion_ease",
        "trail_enabled",
        "trail_max_points",
        "canvas_width",
        "canvas_height",
        "show_stats",
        "stats_dpi",
        "stats_update_rate",
        "update_check_mode",
        "active_preset",
    }
    for key in expected:
        assert key in DEFAULTS, f"Missing key: {key}"


def test_presets_have_valid_structure():
    assert isinstance(PRESETS, dict)
    assert len(PRESETS) > 0
    for name, settings in PRESETS.items():
        assert isinstance(name, str)
        assert isinstance(settings, dict)
        assert len(settings) > 0


def test_excluded_keys_contains_expected():
    expected = {"host", "port", "auth_token", "auth_enabled", "start_with_windows"}
    for key in expected:
        assert key in PRESET_EXCLUDE, f"Missing excluded key: {key}"


def test_shell_keys_contains_expected():
    expected = {"host", "port", "auth_token", "auth_enabled"}
    for key in expected:
        assert key in SHELL_KEYS, f"Missing shell key: {key}"


def test_feel_presets_have_required_fields():
    for name, settings in FEEL_PRESETS.items():
        assert "motion_scale" in settings, f"{name} missing motion_scale"
        assert "motion_ease" in settings, f"{name} missing motion_ease"
        assert "camera_lag" in settings, f"{name} missing camera_lag"


def test_quality_presets_have_required_fields():
    for name, settings in QUALITY_PRESETS.items():
        assert "target_fps" in settings, f"{name} missing target_fps"
        assert "trail_max_points" in settings, f"{name} missing trail_max_points"


def test_stats_update_hz_has_expected_rates():
    assert "slow" in STATS_UPDATE_HZ
    assert "normal" in STATS_UPDATE_HZ
    assert "fast" in STATS_UPDATE_HZ
    for rate in STATS_UPDATE_HZ.values():
        assert rate > 0