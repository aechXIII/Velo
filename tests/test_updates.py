"""Tests for velo.updates."""

from __future__ import annotations

import hashlib
import io
import json
import time

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


def test_pending_update_checksum_state_survives_restart(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)
    setup_url = "https://github.com/aechXIII/Velo/releases/download/v2/Velo-Setup-2.exe"
    service = UpdateService(current_version="1.0.0")
    service._pending = {
        "version": "2.0.0",
        "tag": "v2.0.0",
        "notes": "Stable",
        "release_url": "https://github.com/aechXIII/Velo/releases/tag/v2.0.0",
        "download_url": setup_url,
        "asset_name": "Velo-Setup-2.exe",
        "checksum_url": setup_url + ".sha256",
        "checksum_name": "Velo-Setup-2.exe.sha256",
    }
    service._save_state()

    restored = UpdateService(current_version="1.0.0").status()["pending"]
    assert restored["checksum_url"] == setup_url + ".sha256"
    assert restored["checksum_name"] == "Velo-Setup-2.exe.sha256"


def test_external_update_manager_disables_checks_and_installs(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)
    service = UpdateService(current_version="1.0.0", managed_externally=True)

    assert service.should_auto_check(enabled=True) is False
    assert service.check_async() is False
    assert service.check_now()["managed_externally"] is True
    result = service.install_async()
    assert result["ok"] is False
    assert "itch.io" in result["error"]


def test_pending_state_with_untrusted_url_is_discarded(tmp_path, monkeypatch):
    import velo.updates as updates_module

    monkeypatch.setattr(updates_module, "config_dir", lambda: tmp_path)
    (tmp_path / "update_state.json").write_text(
        json.dumps(
            {
                "pending": {
                    "version": "99.0.0",
                    "download_url": "https://example.com/Velo-Setup.exe",
                    "checksum_url": "https://example.com/Velo-Setup.exe.sha256",
                }
            }
        ),
        encoding="utf-8",
    )
    assert UpdateService(current_version="1.0.0").status()["pending"] is None


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


def test_update_url_validation_blocks_untrusted_hosts():
    with pytest.raises(RuntimeError):
        UpdateService._validate_release_url("http://github.com/file.exe")
    with pytest.raises(RuntimeError):
        UpdateService._validate_release_url("https://example.com/file.exe")
    UpdateService._validate_release_url("https://release-assets.githubusercontent.com/file.exe")


def test_download_verifies_published_checksum(tmp_path, monkeypatch):
    import velo.updates as updates_module

    payload = b"verified-installer" * 100
    expected = hashlib.sha256(payload).hexdigest()
    setup_url = "https://github.com/aechXIII/Velo/releases/download/v3/Velo-Setup-3.exe"
    checksum_url = setup_url + ".sha256"

    class Response(io.BytesIO):
        def __init__(self, data, url):
            super().__init__(data)
            self._url = url
            self.headers = {"Content-Length": str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

        def geturl(self):
            return self._url

    def fake_urlopen(request, timeout=0):
        url = request.full_url
        if url == checksum_url:
            line = f"{expected}  Velo-Setup-3.exe\n".encode()
            return Response(line, checksum_url)
        return Response(payload, setup_url)

    monkeypatch.setattr(updates_module, "_updates_dir", lambda: tmp_path)
    monkeypatch.setattr(updates_module.urllib.request, "urlopen", fake_urlopen)
    service = UpdateService(current_version="2.0.0")
    result = service._download_setup(
        {
            "version": "3.0.0",
            "asset_name": "Velo-Setup-3.exe",
            "download_url": setup_url,
            "checksum_url": checksum_url,
        }
    )
    assert result.read_bytes() == payload


def test_download_rejects_checksum_mismatch(tmp_path, monkeypatch):
    import velo.updates as updates_module

    setup_url = "https://github.com/aechXIII/Velo/releases/download/v3/Velo-Setup-3.exe"
    checksum_url = setup_url + ".sha256"

    class Response(io.BytesIO):
        headers = {"Content-Length": "2048"}

        def __init__(self, data, url):
            super().__init__(data)
            self._url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

        def geturl(self):
            return self._url

    def fake_urlopen(request, timeout=0):
        if request.full_url == checksum_url:
            return Response(("0" * 64 + "  Velo-Setup-3.exe\n").encode(), checksum_url)
        return Response(b"x" * 2048, setup_url)

    monkeypatch.setattr(updates_module, "_updates_dir", lambda: tmp_path)
    monkeypatch.setattr(updates_module.urllib.request, "urlopen", fake_urlopen)
    service = UpdateService(current_version="2.0.0")
    with pytest.raises(RuntimeError, match="SHA-256"):
        service._download_setup(
            {
                "version": "3.0.0",
                "asset_name": "Velo-Setup-3.exe",
                "download_url": setup_url,
                "checksum_url": checksum_url,
            }
        )
    assert not (tmp_path / "Velo-Setup-3.exe").exists()
