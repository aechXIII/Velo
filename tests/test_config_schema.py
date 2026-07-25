"""Tests for velo.config_schema."""

from __future__ import annotations

import pytest

from velo.config_schema import (
    SCHEMA,
    ValidationError,
    validate_config,
    validate_preset_name,
)


def test_valid_config_passes():
    config = {
        "window_width": 800,
        "window_height": 600,
        "pad_shape": "rounded",
        "pad_fill_opacity": 0.5,
        "trail_show": True,
        "trail_width": 3,
        "cursor_show": True,
        "cursor_size": 5,
        "motion_scale": 1.0,
        "fps_limit": 60,
        "server_port": 27180,
    }
    errors = validate_config(config)
    assert errors == []


def test_invalid_type_is_caught():
    config = {"window_width": "not_an_int"}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "window_width" in errors[0]
    assert "int" in errors[0]


def test_out_of_range_value_is_caught():
    config = {"window_width": 0}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "window_width" in errors[0]
    assert "out of range" in errors[0]


def test_out_of_range_high_value_is_caught():
    config = {"fps_limit": 500}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "fps_limit" in errors[0]


def test_float_range_validation():
    config = {"pad_fill_opacity": 1.5}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "pad_fill_opacity" in errors[0]


def test_negative_range_validation():
    config = {"pad_shadow_offset_x": -200}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "pad_shadow_offset_x" in errors[0]


def test_multiple_errors_reported():
    config = {
        "window_width": "bad",
        "fps_limit": 500,
        "pad_fill_opacity": 2.0,
    }
    errors = validate_config(config)
    assert len(errors) == 3


def test_unknown_keys_ignored_by_default():
    config = {"unknown_key": "value", "window_width": 800}
    errors = validate_config(config)
    assert errors == []


def test_unknown_keys_caught_in_strict_mode():
    config = {"unknown_key": "value", "window_width": 800}
    errors = validate_config(config, strict=True)
    assert len(errors) == 1
    assert "unknown_key" in errors[0]


def test_none_values_skip_validation():
    config = {"window_width": None}
    errors = validate_config(config)
    assert errors == []


def test_empty_config_passes():
    errors = validate_config({})
    assert errors == []


def test_bool_type_validation():
    config = {"trail_show": "not_bool"}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "trail_show" in errors[0]


def test_string_type_validation():
    config = {"pad_shape": 123}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "pad_shape" in errors[0]


def test_validate_preset_name_valid():
    assert validate_preset_name("My Preset") is None
    assert validate_preset_name("test-preset") is None
    assert validate_preset_name("a") is None


def test_validate_preset_name_empty():
    assert validate_preset_name("") is not None
    assert validate_preset_name("   ") is not None


def test_validate_preset_name_too_long():
    long_name = "x" * 65
    error = validate_preset_name(long_name)
    assert error is not None
    assert "64" in error


def test_validate_preset_name_invalid_chars():
    error = validate_preset_name("bad\x00name")
    assert error is not None


def test_schema_has_expected_keys():
    expected_keys = [
        "window_width", "window_height",
        "pad_shape", "pad_fill_opacity", "pad_border",
        "trail_show", "trail_width", "trail_color",
        "cursor_show", "cursor_size", "cursor_opacity",
        "click_style", "click_duration",
        "motion_scale", "motion_smoothing",
        "hud_show", "hud_opacity",
        "fps_limit",
        "server_port", "auth_token",
    ]
    for key in expected_keys:
        assert key in SCHEMA, f"Missing schema key: {key}"


def test_schema_entries_have_four_elements():
    for key, entry in SCHEMA.items():
        assert len(entry) == 4, f"Schema entry for {key} should have 4 elements"


def test_validation_error_is_value_error():
    assert issubclass(ValidationError, ValueError)


def test_edge_case_min_boundary():
    config = {"window_width": 1}
    errors = validate_config(config)
    assert errors == []


def test_edge_case_max_boundary():
    config = {"window_width": 3840}
    errors = validate_config(config)
    assert errors == []


def test_edge_case_float_min_boundary():
    config = {"pad_fill_opacity": 0.0}
    errors = validate_config(config)
    assert errors == []


def test_edge_case_float_max_boundary():
    config = {"pad_fill_opacity": 1.0}
    errors = validate_config(config)
    assert errors == []


def test_server_port_range():
    config = {"server_port": 80}
    errors = validate_config(config)
    assert len(errors) == 1
    assert "server_port" in errors[0]