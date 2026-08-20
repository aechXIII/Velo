"""Tests for the pinned Butler installer script."""

from __future__ import annotations

import hashlib
import subprocess
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install-butler.ps1"


def _make_archive(path: Path) -> str:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("butler.exe", b"test-butler")
        archive.writestr("7z.dll", b"test-library")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_installer(archive: Path, destination: Path, expected_hash: str):
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ArchivePath",
            str(archive),
            "-Destination",
            str(destination),
            "-ExpectedSha256",
            expected_hash,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_install_butler_extracts_archive_after_hash_verification(tmp_path):
    archive = tmp_path / "butler.zip"
    expected_hash = _make_archive(archive)
    destination = tmp_path / "butler"

    result = _run_installer(archive, destination, expected_hash)

    assert result.returncode == 0, result.stderr
    assert (destination / "butler.exe").read_bytes() == b"test-butler"
    assert (destination / "7z.dll").read_bytes() == b"test-library"


def test_install_butler_rejects_archive_with_wrong_hash(tmp_path):
    archive = tmp_path / "butler.zip"
    _make_archive(archive)
    destination = tmp_path / "butler"

    result = _run_installer(archive, destination, "0" * 64)

    assert result.returncode != 0
    assert "Butler archive SHA-256 mismatch" in (result.stdout + result.stderr)
    assert not destination.exists()
