"""Tests for velo.config."""

from __future__ import annotations

import base64
import json
import zlib
from types import SimpleNamespace

import pytest
from PIL import Image

from velo.config import ConfigStore, config_dir, config_path, presets_dir


def test_config_store_initializes_with_defaults(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    snap = store.snapshot()
    assert isinstance(snap, dict)
    assert "host" in snap
    assert "port" in snap
    assert "auth_token" in snap


def test_config_store_get_set(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    assert store.get("sensitivity") == 1.0
    store.update({"sensitivity": 2.0}, persist=True)
    assert store.get("sensitivity") == 2.0


def test_config_store_persistence(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path=path, presets_path=tmp_path / "presets")
    store.update({"sensitivity": 3.0}, persist=True)

    store2 = ConfigStore(path=path, presets_path=tmp_path / "presets")
    assert store2.get("sensitivity") == 3.0


def test_config_store_snapshot_is_independent(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    snap = store.snapshot()
    snap["sensitivity"] = 999.0
    assert store.get("sensitivity") == 1.0


def test_config_store_reset_defaults(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"sensitivity": 5.0}, persist=True)
    store.reset_defaults(keep_auth=True)
    assert store.get("sensitivity") == 1.0


def test_config_store_reset_visuals(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"trail_width": 10.0, "host": "custom"}, persist=True)
    store.reset_visuals()
    assert store.get("trail_width") == 2.4
    assert store.get("host") == "custom"


def test_config_store_export_import_bundle(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"sensitivity": 2.5}, persist=True)
    bundle = store.export_bundle(include_connection=False)
    assert bundle["app"] == "Velo"
    assert bundle["config"]["sensitivity"] == 2.5
    assert "auth_token" not in bundle["config"]

    store2 = ConfigStore(path=tmp_path / "config2.json", presets_path=tmp_path / "presets2")
    store2.import_bundle(bundle, include_connection=False)
    assert store2.get("sensitivity") == 2.5


def test_config_store_export_is_safe_by_default(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"host": "0.0.0.0", "port": 30000, "auth_token": "private-token"})
    exported = store.export_bundle()["config"]
    assert "host" not in exported
    assert "port" not in exported
    assert "auth_token" not in exported


def test_new_config_uses_24_hz_hud_rate(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")

    assert store.get("stats_update_rate") == 24


def test_hud_background_color_is_saved(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")

    store.update({"stats_bg_color": "#123456"}, persist=False)

    assert store.get("stats_bg_color") == "#123456"


def test_import_migrates_legacy_stats_update_rate(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")

    store.import_bundle({"config": {"stats_update_rate": "fast"}})

    assert store.get("stats_update_rate") == 10


def test_malformed_config_is_quarantined_and_backup_is_restored(tmp_path):
    path = tmp_path / "config.json"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    path.write_text("{not valid json", encoding="utf-8")
    (backup_dir / "config_20260819_120000.json").write_text(
        json.dumps({"sensitivity": 3.5}), encoding="utf-8"
    )

    store = ConfigStore(path=path, presets_path=tmp_path / "presets")

    assert store.get("sensitivity") == 3.5
    assert store.recovery_notice and "Recovered settings" in store.recovery_notice
    quarantined = list((tmp_path / "recovery").glob("config.invalid-*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == "{not valid json"
    assert json.loads(path.read_text(encoding="utf-8"))["sensitivity"] == 3.5


def test_malformed_config_without_backup_resets_safely(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[]", encoding="utf-8")

    store = ConfigStore(path=path, presets_path=tmp_path / "presets")

    assert store.get("sensitivity") == 1.0
    assert store.get("auth_token")
    assert store.recovery_notice and "Reset settings" in store.recovery_notice
    assert list((tmp_path / "recovery").glob("config.invalid-*.json"))


def test_config_store_preset_save_load_delete(tmp_path):
    presets = tmp_path / "presets"
    store = ConfigStore(path=tmp_path / "config.json", presets_path=presets)
    store.update({"sensitivity": 1.5, "trail_width": 3.0}, persist=True)

    store.save_user_preset("test-preset", overwrite=False)
    info = store.list_presets()
    user_names = [p["name"] for p in info["user"]]
    assert "test-preset" in user_names

    store.update({"sensitivity": 1.0}, persist=True)
    store.apply_preset("test-preset", kind="user")
    assert store.get("sensitivity") == 1.5

    store.delete_user_preset("test-preset")
    info = store.list_presets()
    user_names = [p["name"] for p in info["user"]]
    assert "test-preset" not in user_names


def test_config_store_rename_preset(tmp_path):
    presets = tmp_path / "presets"
    store = ConfigStore(path=tmp_path / "config.json", presets_path=presets)
    store.update({"sensitivity": 2.0}, persist=True)
    store.save_user_preset("old-name", overwrite=False)

    store.rename_user_preset("old-name", "new-name")
    info = store.list_presets()
    user_names = [p["name"] for p in info["user"]]
    assert "old-name" not in user_names
    assert "new-name" in user_names


def test_preset_share_round_trips_background_presentation_settings(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update(
        {
            "pad_bg_image": "/user-assets/background-local.png",
            "pad_bg_image_enabled": True,
            "pad_bg_image_opacity": 0.42,
            "pad_bg_image_size": "contain",
            "pad_bg_image_zoom": 2.5,
            "pad_bg_image_pos_x": 20.0,
            "pad_bg_image_pos_y": 80.0,
            "stats_bg_color": "#123456",
            "stats_opacity": 0.35,
            "stats_update_rate": 240,
        },
        persist=False,
    )
    store.save_user_preset("Presentation")

    _, saved = store.get_preset_settings("Presentation", "user")
    assert "pad_bg_image" not in saved
    assert "stats_update_rate" not in saved

    decoded = store.decode_preset_share(
        store.encode_preset_share("Presentation", "user")
    )["settings"]

    assert decoded["pad_bg_image_enabled"] is True
    assert decoded["pad_bg_image_opacity"] == 0.42
    assert decoded["pad_bg_image_size"] == "contain"
    assert decoded["pad_bg_image_zoom"] == 2.5
    assert decoded["pad_bg_image_pos_x"] == 20.0
    assert decoded["pad_bg_image_pos_y"] == 80.0
    assert decoded["stats_bg_color"] == "#123456"
    assert decoded["stats_opacity"] == 0.35


def test_preset_saves_and_shares_hud_speed_chart_setting(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"hud_show_sparkline": False}, persist=False)
    store.save_user_preset("HUD")

    _, saved = store.get_preset_settings("HUD", "user")
    decoded = store.decode_preset_share(store.encode_preset_share("HUD", "user"))[
        "settings"
    ]

    assert saved["hud_show_sparkline"] is False
    assert decoded["hud_show_sparkline"] is False


def test_preset_share_round_trips_fade_style_and_target_fps(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"fade_style": "linear", "target_fps": 144}, persist=False)
    store.save_user_preset("Timing")

    decoded = store.decode_preset_share(
        store.encode_preset_share("Timing", "user")
    )["settings"]

    assert decoded["fade_style"] == "linear"
    assert decoded["target_fps"] == 144


def test_preset_share_decodes_legacy_fade_style_alias(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    payload = json.dumps({"v": 1, "n": "Legacy", "tf": "linear"}).encode("utf-8")
    code = "VELO2." + base64.urlsafe_b64encode(zlib.compress(payload)).decode().rstrip("=")

    decoded = store.decode_preset_share(code)["settings"]

    assert decoded["fade_style"] == "linear"
    assert decoded["target_fps"] == 60


def test_config_store_apply_builtin_preset(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.apply_preset("16:9 pad", kind="builtin")
    assert store.get("canvas_aspect") == "16:9"


def test_config_store_on_change_callback(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    calls = []

    def cb(snap):
        calls.append(snap)

    store.on_change(cb)
    store.update({"sensitivity": 4.0}, persist=True)
    assert len(calls) >= 1
    assert calls[-1]["sensitivity"] == 4.0


def test_invalid_patch_is_rejected_without_mutating_state(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    before = store.snapshot()
    with pytest.raises(ValueError):
        store.update({"port": "oops"})
    assert store.snapshot() == before


def test_invalid_values_on_disk_fall_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"port": "oops", "sensitivity": 2.0}), encoding="utf-8")
    store = ConfigStore(path=path, presets_path=tmp_path / "presets")
    assert store.get("port") == 27180
    assert store.get("sensitivity") == 2.0
    assert json.loads(path.read_text(encoding="utf-8"))["port"] == 27180


@pytest.mark.parametrize(
    ("legacy_rate", "expected_hz"),
    [("slow", 2), ("normal", 4), ("fast", 10)],
)
def test_legacy_stats_update_rate_is_migrated(tmp_path, legacy_rate, expected_hz):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"stats_update_rate": legacy_rate}), encoding="utf-8")

    store = ConfigStore(path=path, presets_path=tmp_path / "presets")

    assert store.get("stats_update_rate") == expected_hz
    assert json.loads(path.read_text(encoding="utf-8"))["stats_update_rate"] == expected_hz


def test_invalid_bundle_is_rejected(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    with pytest.raises(ValueError):
        store.import_bundle({"config": {"preset_hotkeys": "not-a-list"}})


def test_background_image_accepts_files_larger_than_2_mb(tmp_path):
    image_path = tmp_path / "background.png"
    with Image.new("RGB", (1024, 1024), (1, 2, 3)) as image:
        image.save(image_path, format="PNG", compress_level=0)
    assert image_path.stat().st_size > 2 * 1024 * 1024
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")

    asset_url = store.store_background_image(image_path)

    assert asset_url.startswith("/user-assets/background-")
    assert list((tmp_path / "assets").glob("background-*.png"))


@pytest.mark.parametrize(
    ("reported_size", "accepted"),
    [(100 * 1024 * 1024, True), ((100 * 1024 * 1024) + 1, False)],
)
def test_background_image_uses_100_mb_file_size_limit(
    tmp_path, monkeypatch, reported_size, accepted
):
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    image_path = tmp_path / "background.png"
    image_path.write_bytes(png)
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    original_stat = type(image_path).stat

    def stat_with_reported_size(path, *args, **kwargs):
        if path == image_path:
            return SimpleNamespace(st_size=reported_size)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(type(image_path), "stat", stat_with_reported_size)

    if accepted:
        assert store.store_background_image(image_path).startswith(
            "/user-assets/background-"
        )
    else:
        with pytest.raises(ValueError, match="max 100 MB"):
            store.store_background_image(image_path)


def test_background_data_url_is_externalized(tmp_path):
    # Valid 1x1 PNG.
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"pad_bg_image": data_url}), encoding="utf-8")
    store = ConfigStore(path=path, presets_path=tmp_path / "presets")
    value = store.get("pad_bg_image")
    assert value.startswith("/user-assets/background-")
    assert list((tmp_path / "assets").glob("background-*.png"))
    assert "data:image" not in path.read_text(encoding="utf-8")


def test_reset_visuals_preserves_preset_hotkeys(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    hotkeys = [{"key": "Ctrl+1", "target": "16:9 pad"}]
    store.update({"preset_hotkeys": hotkeys})
    store.reset_visuals()
    assert store.get("preset_hotkeys") == hotkeys


def test_preset_files_do_not_capture_global_hotkeys(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    store.update({"preset_hotkeys": [{"key": "Ctrl+1", "target": "16:9 pad"}]})
    store.save_user_preset("No global state")
    payload = json.loads(next((tmp_path / "presets").glob("*.json")).read_text(encoding="utf-8"))
    assert "preset_hotkeys" not in payload["settings"]


def test_custom_config_backups_stay_with_custom_path(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path=path, presets_path=tmp_path / "presets")
    store.update({"sensitivity": 2.0})
    assert (tmp_path / "backups").is_dir()


def test_config_dir_returns_path():
    d = config_dir()
    assert d.name == "Velo"


def test_config_path_returns_path():
    p = config_path()
    assert p.name == "config.json"


def test_presets_dir_returns_path():
    d = presets_dir()
    assert d.name == "presets"
