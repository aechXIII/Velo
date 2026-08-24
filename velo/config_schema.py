"""Authoritative validation for Velo configuration values."""

from __future__ import annotations

import math
import re
from typing import Any

from velo.config_types import ConfigMap
from velo.constants import MAX_STATS_UPDATE_HZ, MIN_STATS_UPDATE_HZ
from velo.defaults import DEFAULTS


class ValidationError(ValueError):
    """Raised when configuration validation fails."""


_RANGES: dict[str, tuple[float, float]] = {
    "port": (1, 65535),
    "sensitivity": (0.01, 10.0),
    "camera_lag": (0.0, 1.0),
    "camera_look_ahead": (0.0, 5.0),
    "camera_follow": (0.0, 5.0),
    "view_zoom": (0.1, 5.0),
    "motion_scale": (0.01, 10.0),
    "motion_ease": (0.0, 1.0),
    "target_fps": (0, 240),
    "ws_send_hz": (30, 240),
    "trail_lifetime_ms": (50, 10000),
    "trail_max_points": (2, 2000),
    "trail_width": (0.1, 100.0),
    "trail_glow_blur": (0, 100),
    "trail_glow_opacity": (0.0, 1.0),
    "trail_glow_width": (0.5, 3.0),
    "trail_min_distance": (0.0, 100.0),
    "trail_smoothing": (0.0, 1.0),
    "trail_curve": (0.0, 1.0),
    "trail_samples": (1, 20),
    "speed_min": (0.0, 100000.0),
    "speed_max": (0.0, 100000.0),
    "cursor_dot_size": (0.1, 100.0),
    "cursor_dot_opacity": (0.0, 1.0),
    "click_lifetime_ms": (10, 10000),
    "click_radius": (0.1, 500.0),
    "click_line_width": (0.1, 100.0),
    "click_opacity": (0.0, 1.0),
    "pad_width_pct": (1.0, 100.0),
    "pad_height_pct": (1.0, 100.0),
    "pad_x_pct": (0.0, 100.0),
    "pad_y_pct": (0.0, 100.0),
    "pad_radius": (0, 500),
    "pad_bg_opacity": (0.0, 1.0),
    "pad_border_opacity": (0.0, 1.0),
    "pad_border_width": (0.0, 50.0),
    "pad_shadow_opacity": (0.0, 1.0),
    "pad_grid_size": (1, 500),
    "pad_grid_thickness": (0.1, 20.0),
    "pad_grid_opacity": (0.0, 1.0),
    "pad_crosshair_opacity": (0.0, 1.0),
    "pad_crosshair_size": (1, 500),
    "pad_vignette_opacity": (0.0, 1.0),
    "pad_glow_opacity": (0.0, 1.0),
    "pad_glow_blur": (0, 100),
    "canvas_width": (1, 3840),
    "canvas_height": (1, 2160),
    "source_bg_opacity": (0.0, 1.0),
    "overlay_opacity": (0.0, 1.0),
    "stats_opacity": (0.0, 1.0),
    "stats_x_pct": (0.0, 100.0),
    "stats_y_pct": (0.0, 100.0),
    "stats_dpi": (100, 32000),
    "stats_update_rate": (MIN_STATS_UPDATE_HZ, MAX_STATS_UPDATE_HZ),
    "backup_max_count": (1, 50),
    "pad_bg_image_opacity": (0.0, 1.0),
    "pad_bg_image_zoom": (0.1, 8.0),
    "pad_bg_image_pos_x": (0.0, 100.0),
    "pad_bg_image_pos_y": (0.0, 100.0),
}

_ENUMS: dict[str, frozenset[str]] = {
    "capture_mode": frozenset({"relative", "absolute"}),
    "view_mode": frozenset({"infinite", "fixed", "wrap"}),
    "motion_feel": frozenset({"tight", "normal", "soft", "custom"}),
    "render_quality": frozenset({"performance", "balanced", "pretty", "custom"}),
    "ui_preview_mode": frozenset({"off", "lite", "live", "auto"}),
    "fade_style": frozenset({"smooth", "ease-in", "ease-out", "linear", "snap", "hard"}),
    "click_style": frozenset({"ring", "fill", "double", "cross"}),
    "pad_shape": frozenset({"rounded", "rect", "pill", "circle", "stadium"}),
    "canvas_aspect": frozenset({"16:9", "4:3", "1:1", "21:9", "custom"}),
    "stats_units": frozenset({"cm", "m", "raw"}),
    "update_check_mode": frozenset({"launch", "daily", "off"}),
    "active_preset_kind": frozenset({"builtin", "user"}),
    "pad_bg_image_size": frozenset({"cover", "contain", "100% 100%"}),
}

_COLOR_KEYS = frozenset(
    key
    for key, default in DEFAULTS.items()
    if isinstance(default, str)
    and ("color" in key or key in {"pad_bg_color", "pad_border_color", "chart_color"})
)
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?$")
_HOTKEY_RE = re.compile(
    r"^(?:(?:Ctrl|Shift|Alt|Win)\+)*(?:F(?:[1-9]|1[0-9]|2[0-4])|[A-Z0-9]|Space|Tab|Esc|Escape|Enter|Return|Backspace|Delete|Insert|Home|End|PageUp|PageDown|Up|Down|Left|Right|Plus|Minus)$",
    re.IGNORECASE,
)


def _schema_entry(key: str, default: Any) -> tuple[type, Any | None, Any | None, str]:
    value_type = type(default)
    low, high = _RANGES.get(key, (None, None))
    return value_type, low, high, f"Velo setting: {key}"


# Kept as a public mapping for API documentation and compatibility, but generated
# directly from DEFAULTS so the schema cannot silently lose current settings.
SCHEMA: dict[str, tuple[type, Any | None, Any | None, str]] = {
    key: _schema_entry(key, value) for key, value in DEFAULTS.items()
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_color(key: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, str) or not _HEX_COLOR_RE.fullmatch(value):
        errors.append(f"{key}: expected a hex color")


def _validate_speed_stops(value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or not 2 <= len(value) <= 16:
        errors.append("speed_stops: expected a list containing 2-16 stops")
        return
    previous = -1.0
    for index, stop in enumerate(value):
        if not isinstance(stop, dict):
            errors.append(f"speed_stops[{index}]: expected object")
            continue
        t = stop.get("t")
        color = stop.get("color")
        if not _is_number(t) or not math.isfinite(float(t)) or not 0.0 <= float(t) <= 1.0:
            errors.append(f"speed_stops[{index}].t: expected number in [0, 1]")
        elif float(t) < previous:
            errors.append("speed_stops: stop positions must be ordered")
        else:
            previous = float(t)
        _validate_color(f"speed_stops[{index}].color", color, errors)


def _validate_click_map(key: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{key}: expected object")
        return
    allowed = {"left", "right", "middle", "side"} if key == "click_show" else {
        "left", "right", "middle", "x1", "x2"
    }
    unknown = set(value) - allowed
    if unknown:
        errors.append(f"{key}: unknown keys: {', '.join(sorted(unknown))}")
    for subkey, item in value.items():
        if key == "click_show":
            if type(item) is not bool:
                errors.append(f"{key}.{subkey}: expected bool")
        else:
            _validate_color(f"{key}.{subkey}", item, errors)


def _validate_string_list(key: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) > 100:
        errors.append(f"{key}: expected a list with at most 100 items")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or len(item) > 128:
            errors.append(f"{key}[{index}]: expected a short string")


def _validate_hotkey_entry(index: int, item: Any, seen: set[str], errors: list[str]) -> None:
    if not isinstance(item, dict) or set(item) - {"key", "target"}:
        errors.append(f"preset_hotkeys[{index}]: expected key/target object")
        return
    key = item.get("key")
    target = item.get("target")
    if not isinstance(key, str) or len(key) > 64 or (key and not _HOTKEY_RE.fullmatch(key)):
        errors.append(f"preset_hotkeys[{index}].key: invalid hotkey")
    if not isinstance(target, str) or len(target) > 128:
        errors.append(f"preset_hotkeys[{index}].target: expected a short string")
    normalized = str(key or "").casefold()
    if normalized and normalized in seen:
        errors.append(f"preset_hotkeys[{index}].key: duplicate hotkey")
    seen.add(normalized)


def _validate_hotkeys(value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) > 20:
        errors.append("preset_hotkeys: expected a list with at most 20 bindings")
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        _validate_hotkey_entry(index, item, seen, errors)


def _type_matches(expected_type: type, value: Any) -> bool:
    if expected_type is bool:
        return type(value) is bool
    if expected_type is int:
        return type(value) is int
    if expected_type is float:
        return _is_number(value)
    return isinstance(value, expected_type)


def _validate_numeric_range(key: str, value: Any, errors: list[str]) -> bool:
    """Check range for numeric values. Returns False if the caller must stop (non-finite)."""
    if not _is_number(value):
        return True
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"{key}: expected a finite number")
        return False
    if key in _RANGES:
        low, high = _RANGES[key]
        if number < low or number > high:
            errors.append(f"{key}: value {value} out of range [{low}, {high}]")
    return True


def _validate_value_shape(key: str, value: Any, errors: list[str]) -> None:
    if key in _ENUMS and value not in _ENUMS[key]:
        errors.append(f"{key}: unsupported value {value!r}")
    elif key in _COLOR_KEYS:
        _validate_color(key, value, errors)
    elif key == "speed_stops":
        _validate_speed_stops(value, errors)
    elif key in {"click_show", "click_colors"}:
        _validate_click_map(key, value, errors)
    elif key == "hidden_presets":
        _validate_string_list(key, value, errors)
    elif key == "preset_hotkeys":
        _validate_hotkeys(value, errors)
    elif key == "pad_bg_image":
        if len(value) > 512 or (value and not value.startswith("/user-assets/")):
            errors.append("pad_bg_image: expected an application-managed asset URL")
    elif isinstance(value, str) and len(value) > 512:
        errors.append(f"{key}: string is too long")


def _validate_config_entry(key: str, value: Any, errors: list[str], *, strict: bool) -> None:
    if key not in SCHEMA:
        if strict:
            errors.append(f"Unknown config key: {key}")
        return

    expected_type = type(DEFAULTS[key])
    if not _type_matches(expected_type, value):
        errors.append(f"{key}: expected {expected_type.__name__}, got {type(value).__name__}")
        return

    if not _validate_numeric_range(key, value, errors):
        return

    _validate_value_shape(key, value, errors)


def _validate_speed_bounds(config: ConfigMap, errors: list[str]) -> None:
    if "speed_min" in config and "speed_max" in config:
        low = config.get("speed_min")
        high = config.get("speed_max")
        if _is_number(low) and _is_number(high) and float(low) >= float(high):
            errors.append("speed_min: must be lower than speed_max")


def validate_config(config: ConfigMap, strict: bool = False) -> list[str]:
    """Validate a full configuration or patch against the current defaults."""
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["config: expected object"]

    for key, value in config.items():
        _validate_config_entry(key, value, errors, strict=strict)

    _validate_speed_bounds(config, errors)
    return errors


def require_valid_config(config: ConfigMap, *, strict: bool = True) -> None:
    errors = validate_config(config, strict=strict)
    if errors:
        raise ValidationError("; ".join(errors))


def validate_preset_name(name: str) -> str | None:
    if not name or not name.strip():
        return "Preset name cannot be empty"
    if len(name) > 64:
        return "Preset name too long (max 64 characters)"
    if not all(c.isprintable() for c in name):
        return "Preset name contains invalid characters"
    return None
