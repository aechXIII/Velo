"""Tests for velo.config."""

from __future__ import annotations

import base64
import json

import pytest

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


def test_invalid_bundle_is_rejected(tmp_path):
    store = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
    with pytest.raises(ValueError):
        store.import_bundle({"config": {"preset_hotkeys": "not-a-list"}})


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
