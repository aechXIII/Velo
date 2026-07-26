"""Config schema validation for Velo."""

from __future__ import annotations

from typing import Any

from velo.config_types import ConfigMap


class ValidationError(ValueError):
    """Raised when config validation fails."""


SCHEMA: dict[str, tuple[type, Any | None, Any | None, str]] = {
    "window_width": (int, 1, 3840, "Window width in pixels"),
    "window_height": (int, 1, 2160, "Window height in pixels"),

    "pad_shape": (str, None, None, "Pad shape: rounded, rect, pill, circle, stadium"),
    "pad_width": (int, 1, 5000, "Pad width in pixels"),
    "pad_height": (int, 1, 5000, "Pad height in pixels"),
    "pad_radius": (int, 0, 500, "Pad corner radius"),
    "pad_fill": (str, None, None, "Pad fill color as hex string"),
    "pad_fill_opacity": (float, 0.0, 1.0, "Pad fill opacity"),
    "pad_border": (bool, None, None, "Show pad border"),
    "pad_border_color": (str, None, None, "Pad border color"),
    "pad_border_width": (int, 0, 50, "Pad border width"),
    "pad_grid": (bool, None, None, "Show grid on pad"),
    "pad_grid_size": (int, 1, 200, "Grid cell size"),
    "pad_grid_opacity": (float, 0.0, 1.0, "Grid opacity"),
    "pad_grid_color": (str, None, None, "Grid color"),
    "pad_crosshair_size": (int, 4, 64, "Crosshair size in pixels"),
    "pad_vignette": (bool, None, None, "Show vignette"),
    "pad_vignette_opacity": (float, 0.0, 1.0, "Vignette opacity"),
    "pad_shadow": (bool, None, None, "Show pad shadow"),
    "pad_shadow_blur": (int, 0, 100, "Shadow blur radius"),
    "pad_shadow_offset_x": (int, -100, 100, "Shadow X offset"),
    "pad_shadow_offset_y": (int, -100, 100, "Shadow Y offset"),

    "trail_show": (bool, None, None, "Show mouse trail"),
    "trail_length": (int, 1, 500, "Trail length in points"),
    "trail_color": (str, None, None, "Trail color"),
    "trail_color_by_speed": (bool, None, None, "Color trail by speed"),
    "trail_low_speed_color": (str, None, None, "Low speed color"),
    "trail_high_speed_color": (str, None, None, "High speed color"),
    "trail_low_speed_threshold": (float, 0.0, 1000.0, "Low speed threshold"),
    "trail_high_speed_threshold": (float, 0.0, 5000.0, "High speed threshold"),
    "trail_width": (int, 1, 50, "Trail line width"),
    "trail_glow": (bool, None, None, "Show trail glow"),
    "trail_glow_blur": (int, 0, 50, "Glow blur radius"),
    "trail_glow_opacity": (float, 0.05, 1.0, "Glow opacity"),
    "trail_glow_width": (float, 0.5, 3.0, "Glow width multiplier"),
    "trail_glow_custom_color": (bool, None, None, "Use fixed glow color"),
    "trail_glow_custom_color_val": (str, None, None, "Glow color when custom is on"),
    "trail_fade_style": (str, None, None, "Fade style: smooth, ease-in, ease-out, linear, snap, hard"),
    "trail_curve_smoothing": (float, 0.0, 1.0, "Curve smoothing amount"),
    "trail_min_segment": (int, 1, 50, "Min segment length"),

    "cursor_show": (bool, None, None, "Show cursor dot"),
    "cursor_color": (str, None, None, "Cursor color"),
    "cursor_size": (int, 1, 50, "Cursor dot size"),
    "cursor_opacity": (float, 0.0, 1.0, "Cursor opacity"),
    "click_show_lmb": (bool, None, None, "Show left click"),
    "click_show_rmb": (bool, None, None, "Show right click"),
    "click_show_mmb": (bool, None, None, "Show middle click"),
    "click_show_extra1": (bool, None, None, "Show extra button 1"),
    "click_show_extra2": (bool, None, None, "Show extra button 2"),
    "click_style": (str, None, None, "Click style: ring, fill, double, cross"),
    "click_duration": (float, 0.05, 2.0, "Click animation duration"),
    "click_size": (int, 1, 100, "Click indicator size"),
    "click_color_lmb": (str, None, None, "Left click color"),
    "click_color_rmb": (str, None, None, "Right click color"),
    "click_color_mmb": (str, None, None, "Middle click color"),
    "click_color_extra1": (str, None, None, "Extra button 1 color"),
    "click_color_extra2": (str, None, None, "Extra button 2 color"),
    "click_opacity": (float, 0.0, 1.0, "Click opacity"),

    "motion_scale": (float, 0.01, 10.0, "Motion scale multiplier"),
    "motion_smoothing": (float, 0.0, 1.0, "Motion smoothing amount"),
    "motion_sensitivity": (float, 0.01, 10.0, "Motion sensitivity"),
    "motion_view_zoom": (float, 0.1, 5.0, "View zoom level"),
    "motion_camera_lag": (float, 0.0, 1.0, "Camera lag amount"),
    "view_mode": (str, None, None, "View mode: infinite, fixed"),

    "stats_dpi": (int, 100, 32000, "Mouse DPI for stats conversion"),

    "hud_show": (bool, None, None, "Show HUD"),
    "hud_position_x": (int, 0, 10000, "HUD X position"),
    "hud_position_y": (int, 0, 10000, "HUD Y position"),
    "hud_opacity": (float, 0.0, 1.0, "HUD opacity"),
    "hud_font_size": (int, 8, 72, "HUD font size"),
    "hud_color": (str, None, None, "HUD text color"),
    "hud_units": (str, None, None, "HUD units: cm, m, raw"),
    "hud_show_speed": (bool, None, None, "Show speed stat"),
    "hud_show_peak_speed": (bool, None, None, "Show peak speed stat"),
    "hud_show_distance": (bool, None, None, "Show distance stat"),
    "hud_show_clicks": (bool, None, None, "Show click count"),
    "hud_show_cps": (bool, None, None, "Show clicks per second"),
    "hud_show_sparkline": (bool, None, None, "Show speed sparkline chart"),
    "chart_color": (str, None, None, "Speed chart line color"),
    "hud_update_rate": (float, 0.016, 1.0, "HUD update rate in seconds"),

    "fps_limit": (int, 15, 240, "FPS limit for overlay"),
    "show_in_preview": (bool, None, None, "Show in preview mode"),

    "obs_url": (str, None, None, "OBS browser source URL"),
    "obs_width": (int, 1, 3840, "OBS source width"),
    "obs_height": (int, 1, 2160, "OBS source height"),

    "auth_token": (str, None, None, "WebSocket auth token"),
    "server_port": (int, 1024, 65535, "Server port number"),
    "minimize_to_tray": (bool, None, None, "Minimize to tray"),
    "start_minimized": (bool, None, None, "Start minimized"),
    "autostart_enabled": (bool, None, None, "Auto-start with Windows"),
    "check_updates": (bool, None, None, "Check for updates"),
    "last_preset": (str, None, None, "Last used preset name"),
    "language": (str, None, None, "UI language code"),
    "theme": (str, None, None, "UI theme"),

    "backup_enabled": (bool, None, None, "Enable automatic config backups"),
    "backup_max_count": (int, 1, 50, "Maximum number of backup files to keep"),
}


def validate_config(config: ConfigMap, strict: bool = False) -> list[str]:
    """Validate a config map against the schema.

    Returns a list of validation error messages (empty if valid).
    """
    errors: list[str] = []

    for key, value in config.items():
        if key not in SCHEMA:
            if strict:
                errors.append("Unknown config key: %s" % key)
            continue

        expected_type, min_val, max_val, _desc = SCHEMA[key]

        if value is not None and not isinstance(value, (int, float) if expected_type is float else expected_type):
            errors.append(
                "%s: expected %s, got %s" % (key, expected_type.__name__, type(value).__name__)
            )
            continue

        if value is not None and min_val is not None and max_val is not None:
            if isinstance(value, (int, float)):
                if value < min_val or value > max_val:
                    errors.append(
                        "%s: value %s out of range [%s, %s]" % (key, value, min_val, max_val)
                    )

    return errors


def validate_preset_name(name: str) -> str | None:
    """Validate a preset name. Returns error message or None."""
    if not name or not name.strip():
        return "Preset name cannot be empty"
    if len(name) > 64:
        return "Preset name too long (max 64 characters)"
    if not all(c.isprintable() or c in ' -_' for c in name):
        return "Preset name contains invalid characters"
    return None