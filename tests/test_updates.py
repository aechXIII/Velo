"""Tests for velo.updates."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from velo.updates import UpdateService, parse_version, version_gt


def test_parse_version_simple():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_with_v_prefix():
    assert parse_version("v1.2.3") == (1, 2, 3)


def test_parse_version_single():
    assert parse_version("1") == (1,)


def test_parse_version_invalid():
    assert parse_version("abc") is None
    assert parse_version("") is None
    assert parse_version("1.2.3-beta") is None


def test_version_gt_basic():
    assert version_gt("2.0.0", "1.0.0") is True
    assert version_gt("1.0.0", "2.0.0") is False


def test_version_gt_equal():
    assert version_gt("1.0.0", "1.0.0") is False


def test_version_gt_different_lengths():
    assert version_gt("1.2", "1.2.0") is False
    assert version_gt("1.2.1", "1.2") is True


def test_version_gt_with_v_prefix():
    assert version_gt("v2.0.0", "v1.0.0") is True


def test_update_service_initializes(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    status = svc.status()
    assert status["ok"] is True
    assert status["current_version"] == "1.0.0"
    assert status["available"] is False
    assert status["checking"] is False


def test_update_service_state_persistence(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    svc.skip_version("2.0.0")
    assert svc.status()["skipped_version"] == "2.0.0"

    svc2 = UpdateService(current_version="1.0.0")
    assert svc2.status()["skipped_version"] == "2.0.0"


def test_update_service_remind_later(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    status = svc.remind_later(3600)
    assert status["remind_after"] is not None
    assert status["remind_after"] > time.time()


def test_update_service_clear_skip(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    svc.skip_version("2.0.0")
    assert svc.status()["skipped_version"] == "2.0.0"
    svc.clear_skip()
    assert svc.status()["skipped_version"] is None


def test_update_service_should_auto_check_disabled(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    assert svc.should_auto_check(enabled=False) is False


def test_update_service_should_auto_check_first_time(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    assert svc.should_auto_check(enabled=True, force_interval=True) is True


def test_update_service_pending_version_none(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)

    svc = UpdateService(current_version="1.0.0")
    assert svc.pending_version() is None