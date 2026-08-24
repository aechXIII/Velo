"""Tests for the authoritative Velo configuration schema."""

from __future__ import annotations

from copy import deepcopy

from velo.config_schema import SCHEMA, ValidationError, validate_config, validate_preset_name
from velo.defaults import DEFAULTS


def test_all_defaults_are_valid_and_covered():
    assert set(SCHEMA) == set(DEFAULTS)
    assert validate_config(deepcopy(DEFAULTS), strict=True) == []


def test_valid_patch_passes():
    assert validate_config(
        {
            "canvas_width": 800,
            "canvas_height": 600,
            "pad_shape": "rounded",
            "trail_width": 3.0,
            "motion_scale": 1.0,
            "target_fps": 60,
            "port": 27180,
        },
        strict=True,
    ) == []


def test_invalid_type_is_caught():
    errors = validate_config({"port": "not-an-int"}, strict=True)
    assert len(errors) == 1
    assert "port" in errors[0]


def test_bool_is_not_accepted_as_integer():
    assert validate_config({"port": True}, strict=True)


def test_out_of_range_value_is_caught():
    errors = validate_config({"canvas_width": 0}, strict=True)
    assert len(errors) == 1
    assert "out of range" in errors[0]


def test_stats_update_rate_accepts_hz_range():
    assert validate_config({"stats_update_rate": 1}, strict=True) == []
    assert validate_config({"stats_update_rate": 240}, strict=True) == []
    assert validate_config({"stats_update_rate": 0}, strict=True)
    assert validate_config({"stats_update_rate": 241}, strict=True)


def test_hud_background_color_must_be_hex():
    assert validate_config({"stats_bg_color": "#123456"}, strict=True) == []
    assert validate_config({"stats_bg_color": "blue"}, strict=True)


def test_float_range_validation():
    assert validate_config({"pad_bg_opacity": 1.5}, strict=True)


def test_unknown_keys_are_caught_in_strict_mode():
    assert validate_config({"unknown_key": "value"}, strict=True)


def test_unknown_keys_can_be_ignored_for_compatibility():
    assert validate_config({"unknown_key": "value"}) == []


def test_none_is_rejected():
    assert validate_config({"canvas_width": None}, strict=True)


def test_invalid_enum_is_rejected():
    assert validate_config({"capture_mode": "telepathy"}, strict=True)


def test_invalid_nested_click_map_is_rejected():
    assert validate_config({"click_show": {"left": "yes"}}, strict=True)


def test_invalid_speed_stops_are_rejected():
    assert validate_config(
        {"speed_stops": [{"t": 1.0, "color": "red"}, {"t": 0.0, "color": "#fff"}]},
        strict=True,
    )


def test_invalid_preset_hotkey_markup_is_rejected():
    errors = validate_config(
        {"preset_hotkeys": [{"key": "<img onerror=alert(1)>", "target": "Preset"}]},
        strict=True,
    )
    assert errors


def test_duplicate_preset_hotkeys_are_rejected():
    errors = validate_config(
        {
            "preset_hotkeys": [
                {"key": "Ctrl+1", "target": "A"},
                {"key": "ctrl+1", "target": "B"},
            ]
        },
        strict=True,
    )
    assert errors


def test_background_image_must_be_managed_asset():
    assert validate_config({"pad_bg_image": "https://example.test/a.png"}, strict=True)
    assert validate_config({"pad_bg_image": "/user-assets/background-abc.png"}, strict=True) == []


def test_background_image_position_uses_pad_percent_bounds():
    assert validate_config(
        {"pad_bg_image_pos_x": 0.0, "pad_bg_image_pos_y": 100.0}, strict=True
    ) == []
    assert validate_config({"pad_bg_image_pos_x": -0.1}, strict=True)
    assert validate_config({"pad_bg_image_pos_y": 100.1}, strict=True)


def test_background_image_zoom_uses_safe_bounds():
    assert validate_config({"pad_bg_image_zoom": 0.1}, strict=True) == []
    assert validate_config({"pad_bg_image_zoom": 8.0}, strict=True) == []
    assert validate_config({"pad_bg_image_zoom": 0.09}, strict=True)
    assert validate_config({"pad_bg_image_zoom": 8.01}, strict=True)


def test_validate_preset_name():
    assert validate_preset_name("My Preset") is None
    assert validate_preset_name("") is not None
    assert validate_preset_name("x" * 65) is not None
    assert validate_preset_name("bad\x00name") is not None


def test_validation_error_is_value_error():
    assert issubclass(ValidationError, ValueError)
