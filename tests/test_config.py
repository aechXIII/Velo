"""Tests for velo.config."""

from __future__ import annotations

import json

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


def test_config_dir_returns_path():
    d = config_dir()
    assert d.name == "Velo"


def test_config_path_returns_path():
    p = config_path()
    assert p.name == "config.json"


def test_presets_dir_returns_path():
    d = presets_dir()
    assert d.name == "presets"