"""Integration tests for the release metadata verifier."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


def test_installer_smoke_test_handles_missing_autostart_value() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "Get-ItemPropertyValue" not in workflow
    assert "$runKey = Get-ItemProperty" in workflow
    assert '$runKey.PSObject.Properties["Velo"]' in workflow


def test_itch_release_separates_beta_and_stable_channels() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert (
        '$channel = if ("${{ github.event_name }}" -eq "push") '
        '{ "windows" } else { "windows-beta" }'
    ) in workflow
    assert "${{ vars.ITCH_CHANNEL }}" not in workflow


def test_verify_release_accepts_crlf_changelog(tmp_path: Path) -> None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is required to run the release verifier")

    (tmp_path / "scripts").mkdir()
    (tmp_path / "velo").mkdir()
    (tmp_path / "installer").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "verify-release.ps1",
        tmp_path / "scripts" / "verify-release.ps1",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "2.3.1"\n', encoding="utf-8"
    )
    (tmp_path / "velo" / "__init__.py").write_text(
        '__version__ = "2.3.1"\n', encoding="utf-8"
    )
    (tmp_path / "velo" / "defaults.py").write_text(
        'APP_VERSION = "2.3.1"\n', encoding="utf-8"
    )
    (tmp_path / "installer" / "Velo.iss").write_text(
        '#define AppVersion "2.3.1"\n', encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_bytes(
        b"# Changelog\r\n\r\n## [2.3.1] - 2026-08-20\r\n"
    )
    (tmp_path / "requirements-lock.txt").write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tmp_path / "scripts" / "verify-release.ps1"),
            "-Version",
            "2.3.1",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
