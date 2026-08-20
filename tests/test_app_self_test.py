"""Integration tests for the packaged application self-test."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "win32", reason="pywebview uses pythonnet on Windows")
def test_self_test_fails_when_settings_backend_cannot_initialize(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["APPDATA"] = str(tmp_path / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(tmp_path / "AppData" / "Local")
    env["PYTHONNET_RUNTIME"] = "invalid"

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "main.py"), "--self-test"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
