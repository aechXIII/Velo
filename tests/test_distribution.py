"""Tests for distribution-channel behavior."""

from __future__ import annotations

import json
import sys

import pytest

from velo import distribution


def test_distribution_override(monkeypatch):
    monkeypatch.setenv("VELO_DISTRIBUTION", "itch")
    monkeypatch.setattr(distribution.sys, "argv", ["Velo.exe"])
    assert distribution.distribution_channel() == "itch"
    assert distribution.updates_managed_externally() is False
    assert distribution.autostart_supported() is True


def test_itch_app_launch_manages_updates_and_disables_autostart(monkeypatch):
    monkeypatch.setenv("VELO_DISTRIBUTION", "itch")
    monkeypatch.setattr(distribution.sys, "argv", ["Velo.exe", "--itch-app"])

    assert distribution.updates_managed_externally() is True
    assert distribution.autostart_supported() is False


def test_itch_app_flag_does_not_change_standard_distribution(monkeypatch):
    monkeypatch.setenv("VELO_DISTRIBUTION", "standard")
    monkeypatch.setattr(distribution.sys, "argv", ["Velo.exe", "--itch-app"])

    assert distribution.updates_managed_externally() is False
    assert distribution.autostart_supported() is True


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


@pytest.mark.skipif(sys.platform != "win32", reason="Zone.Identifier is Windows-only")
def test_unblock_packaged_settings_runtime_removes_internet_markers(tmp_path):
    relative_paths = (
        "_internal/pythonnet/runtime/Python.Runtime.dll",
        "_internal/webview/lib/Microsoft.Web.WebView2.Core.dll",
        "_internal/webview/lib/Microsoft.Web.WebView2.WinForms.dll",
    )
    assemblies = []
    for relative_path in relative_paths:
        assembly = tmp_path / relative_path
        assembly.parent.mkdir(parents=True, exist_ok=True)
        assembly.write_bytes(b"assembly")
        (assembly.parent / f"{assembly.name}:Zone.Identifier").write_text(
            "[ZoneTransfer]\nZoneId=3\n", encoding="ascii"
        )
        assemblies.append(assembly)

    distribution.unblock_packaged_settings_runtime(tmp_path)

    for assembly in assemblies:
        assert assembly.read_bytes() == b"assembly"
        assert not (assembly.parent / f"{assembly.name}:Zone.Identifier").exists()
