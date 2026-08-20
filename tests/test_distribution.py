"""Tests for distribution-channel behavior."""

from __future__ import annotations

import json

from velo import distribution


def test_distribution_override(monkeypatch):
    monkeypatch.setenv("VELO_DISTRIBUTION", "itch")
    assert distribution.distribution_channel() == "itch"
    assert distribution.updates_managed_externally() is True
    assert distribution.autostart_supported() is False


def test_distribution_marker(monkeypatch, tmp_path):
    monkeypatch.delenv("VELO_DISTRIBUTION", raising=False)
    monkeypatch.setattr(distribution, "executable_root", lambda: tmp_path)
    (tmp_path / "distribution.json").write_text(
        json.dumps({"channel": "itch"}), encoding="utf-8"
    )
    assert distribution.distribution_channel() == "itch"


def test_invalid_marker_falls_back_to_development(monkeypatch, tmp_path):
    monkeypatch.delenv("VELO_DISTRIBUTION", raising=False)
    monkeypatch.setattr(distribution, "executable_root", lambda: tmp_path)
    monkeypatch.setattr(distribution.sys, "frozen", False, raising=False)
    (tmp_path / "distribution.json").write_text("invalid", encoding="utf-8")
    assert distribution.distribution_channel() == "development"
