from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from velo.config import config_dir
from velo.constants import CHECK_INTERVAL_DAYS, RELEASE_NOTES_MAX_LENGTH, REMIND_LATER_HOURS
from velo.defaults import APP_NAME, APP_VERSION
from velo.logging import get_logger

logger = get_logger()

GITHUB_OWNER = "aechXIII"
GITHUB_REPO = "Velo"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
USER_AGENT = f"{APP_NAME}-Updater/{APP_VERSION}"
CHECK_INTERVAL_S = CHECK_INTERVAL_DAYS * 24 * 3600
REMIND_LATER_S = REMIND_LATER_HOURS * 3600
SETUP_ASSET_RE = re.compile(r"^Velo-Setup-.*\.exe$", re.IGNORECASE)
MAX_UPDATE_BYTES = 200 * 1024 * 1024
MAX_CHECKSUM_BYTES = 64 * 1024

OnAvailableCallback = Callable[[Dict[str, Any]], None]
OnInstallReadyCallback = Callable[[Path], None]


def _state_path() -> Path:
    return config_dir() / "update_state.json"


def _updates_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    d = base / APP_NAME / "updates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_version(text: str) -> Optional[Tuple[int, ...]]:
    raw = str(text or "").strip()
    if raw.lower().startswith("v"):
        raw = raw[1:]
    parts = raw.split(".")
    if not parts or any(not p.isdigit() for p in parts):
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def version_gt(a: str, b: str) -> bool:
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        return str(a).strip().lstrip("vV") > str(b).strip().lstrip("vV")
    n = max(len(pa), len(pb))
    pa = pa + (0,) * (n - len(pa))
    pb = pb + (0,) * (n - len(pb))
    return pa > pb


def _normalize_tag(tag: str) -> str:
    t = str(tag or "").strip()
    if t.lower().startswith("v"):
        return t[1:]
    return t


@dataclass
class ReleaseInfo:
    version: str
    tag: str
    notes: str
    release_url: str
    download_url: str
    asset_name: str
    checksum_url: str
    checksum_name: str
    published_at: str


class UpdateService:
    def __init__(
        self,
        *,
        current_version: str = APP_VERSION,
        on_available: Optional[OnAvailableCallback] = None,
        on_install_ready: Optional[OnInstallReadyCallback] = None,
        managed_externally: bool = False,
    ) -> None:
        self.current_version = str(current_version or APP_VERSION).strip()
        self._on_available = on_available
        self._on_install_ready = on_install_ready
        self._managed_externally = bool(managed_externally)
        self._lock = threading.RLock()
        self._checking = False
        self._installing = False
        self._download_progress: Optional[float] = None
        self._last_error: Optional[str] = None
        self._pending: Optional[Dict[str, Any]] = None
        self._skipped_version: Optional[str] = None
        self._remind_after: Optional[float] = None
        self._last_check_at: Optional[float] = None
        self._load_state()

    @staticmethod
    def _pending_candidate_from_dict(pending: Dict[str, Any]) -> Dict[str, str]:
        return {
            "version": str(pending.get("version") or ""),
            "tag": str(pending.get("tag") or ""),
            "notes": str(pending.get("notes") or ""),
            "release_url": str(pending.get("release_url") or ""),
            "download_url": str(pending.get("download_url") or ""),
            "asset_name": str(pending.get("asset_name") or ""),
            "checksum_url": str(pending.get("checksum_url") or ""),
            "checksum_name": str(pending.get("checksum_name") or ""),
        }

    def _is_valid_pending_candidate(self, candidate: Dict[str, str]) -> bool:
        try:
            self._validate_release_url(candidate["download_url"])
            self._validate_release_url(candidate["checksum_url"])
        except RuntimeError:
            return False
        return version_gt(candidate["version"], self.current_version)

    def _parse_pending_from_state(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pending = raw.get("pending")
        if not (isinstance(pending, dict) and pending.get("version") and pending.get("download_url")):
            return None
        candidate = self._pending_candidate_from_dict(pending)
        return candidate if self._is_valid_pending_candidate(candidate) else None

    @staticmethod
    def _parse_optional_float(value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _load_state(self) -> None:
        path = _state_path()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(raw, dict):
            return
        self._skipped_version = _clean_opt_str(raw.get("skipped_version"))
        self._remind_after = self._parse_optional_float(raw.get("remind_after"))
        self._last_check_at = self._parse_optional_float(raw.get("last_check_at"))
        self._pending = self._parse_pending_from_state(raw)

    def _save_state(self) -> None:
        data = {
            "skipped_version": self._skipped_version,
            "remind_after": self._remind_after,
            "last_check_at": self._last_check_at,
            "pending": self._pending,
        }
        path = _state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            self._last_error = f"Could not save update state: {exc}"

    def _status_availability_unlocked(self) -> Tuple[Optional[Dict[str, Any]], bool, bool]:
        pending = dict(self._pending) if self._pending else None
        has_newer = bool(
            not self._managed_externally
            and pending
            and version_gt(str(pending.get("version") or ""), self.current_version)
        )
        skipped = False
        if has_newer and pending and self._skipped_version:
            skipped = not version_gt(str(pending.get("version") or ""), self._skipped_version)
        return pending, has_newer, skipped

    def status(self) -> Dict[str, Any]:
        with self._lock:
            pending, has_newer, skipped = self._status_availability_unlocked()
            actionable = self._is_actionable_unlocked()
            return {
                "ok": True,
                "current_version": self.current_version,
                "checking": self._checking,
                "installing": self._installing,
                "download_progress": self._download_progress,
                "available": has_newer,
                "pending": pending if has_newer else None,
                "latest_version": (pending or {}).get("version") if has_newer else None,
                "notes": (pending or {}).get("notes") if has_newer and pending else "",
                "release_url": (pending or {}).get("release_url") if has_newer else "",
                "download_url": (pending or {}).get("download_url") if has_newer else "",
                "skipped": skipped,
                "skipped_version": self._skipped_version,
                "remind_after": self._remind_after,
                "last_check_at": self._last_check_at,
                "last_error": self._last_error,
                "should_prompt": actionable,
                "managed_externally": self._managed_externally,
                "update_manager": "itch.io" if self._managed_externally else "Velo",
            }

    def pending_version(self) -> Optional[str]:
        with self._lock:
            if self._is_actionable_unlocked() and self._pending:
                return str(self._pending.get("version") or "") or None
            return None

    def _is_actionable_unlocked(self) -> bool:
        if self._managed_externally:
            return False
        if not self._pending:
            return False
        ver = str(self._pending.get("version") or "")
        if not ver or not version_gt(ver, self.current_version):
            return False
        if self._skipped_version and not version_gt(ver, self._skipped_version):
            return False
        if self._remind_after is not None and time.time() < float(self._remind_after):
            return False
        return True

    def should_auto_check(self, *, enabled: bool, force_interval: bool = True) -> bool:
        if not enabled or self._managed_externally:
            return False
        with self._lock:
            if self._checking or self._installing:
                return False
            if not force_interval:
                return True
            if self._last_check_at is None:
                return True
            return (time.time() - float(self._last_check_at)) >= CHECK_INTERVAL_S

    def check_async(
        self,
        *,
        manual: bool = False,
        notify: bool = True,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        with self._lock:
            if self._managed_externally:
                return False
            if self._checking or self._installing:
                return False
            self._checking = True
            self._last_error = None

        def _run() -> None:
            try:
                result = self.check_now(manual=manual, notify=notify)
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
                    self._checking = False
                    result = self.status()
            if on_done:
                try:
                    on_done(result)
                except Exception as exc:
                    logger.debug("Update check on_done callback failed: %s", exc)

        threading.Thread(target=_run, name="velo-update-check", daemon=True).start()
        return True

    def _apply_latest_release_unlocked(
        self, latest: Optional[ReleaseInfo], notes: str, manual: bool
    ) -> None:
        self._last_check_at = time.time()
        if latest is None:
            self._pending = None
            return
        self._pending = {
            "version": latest.version,
            "tag": latest.tag,
            "notes": notes,
            "release_url": latest.release_url,
            "download_url": latest.download_url,
            "asset_name": latest.asset_name,
            "checksum_url": latest.checksum_url,
            "checksum_name": latest.checksum_name,
        }
        if manual:
            self._remind_after = None

    def _notify_if_prompting(self, status: Dict[str, Any]) -> None:
        if status.get("should_prompt") and self._on_available:
            try:
                self._on_available(status)
            except Exception as exc:
                logger.debug("on_available callback failed: %s", exc)

    def check_now(self, *, manual: bool = False, notify: bool = True) -> Dict[str, Any]:
        if self._managed_externally:
            return {
                **self.status(),
                "message": "Updates are managed by the itch.io app",
            }
        with self._lock:
            self._checking = True
            self._last_error = None
        try:
            releases = self._fetch_releases()
            latest, notes = self._pick_latest(releases)
            with self._lock:
                self._apply_latest_release_unlocked(latest, notes, manual)
                self._save_state()
                status = self.status()
            if notify:
                self._notify_if_prompting(status)
            return status
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
                self._last_check_at = time.time()
                self._save_state()
                return self.status()
        finally:
            with self._lock:
                self._checking = False

    def remind_later(self, seconds: float = REMIND_LATER_S) -> Dict[str, Any]:
        with self._lock:
            self._remind_after = time.time() + max(60.0, float(seconds))
            self._save_state()
            return self.status()

    def skip_version(self, version: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            ver = (version or (self._pending or {}).get("version") or "").strip()
            if not ver:
                self._last_error = "No version to skip"
                return self.status()
            self._skipped_version = _normalize_tag(ver)
            self._remind_after = None
            self._save_state()
            return self.status()

    def clear_skip(self) -> Dict[str, Any]:
        with self._lock:
            self._skipped_version = None
            self._save_state()
            return self.status()

    def _install_precheck_unlocked(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if self._managed_externally:
            return None, "Updates are managed by the itch.io app"
        if self._installing:
            return None, "Install already in progress"
        if not self._pending or not self._pending.get("download_url"):
            return None, "No update available to install"
        pending = dict(self._pending)
        if not version_gt(str(pending.get("version") or ""), self.current_version):
            return None, "Already up to date"
        return pending, None

    def install_async(self) -> Dict[str, Any]:
        with self._lock:
            pending, error = self._install_precheck_unlocked()
            if error:
                return {**self.status(), "ok": False, "error": error}
            self._installing = True
            self._download_progress = 0.0
            self._last_error = None

        def _run() -> None:
            try:
                path = self._download_setup(pending)
                with self._lock:
                    self._download_progress = 1.0
                if self._on_install_ready:
                    self._on_install_ready(path)
                else:
                    launch_installer(path)
            except Exception as exc:
                self.fail_install(str(exc))

        threading.Thread(target=_run, name="velo-update-install", daemon=True).start()
        with self._lock:
            return {**self.status(), "ok": True, "message": "Downloading update..."}

    def fail_install(self, error: str) -> None:
        with self._lock:
            self._last_error = str(error or "Install failed")
            self._installing = False
            self._download_progress = None

    def _fetch_releases(self) -> List[Dict[str, Any]]:
        req = urllib.request.Request(
            GITHUB_API + "?per_page=30",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception as read_exc:
                logger.debug("Could not read GitHub API error body: %s", read_exc)
            raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
        data = json.loads(body)
        if not isinstance(data, list):
            raise RuntimeError("Unexpected GitHub API response")
        return data

    @staticmethod
    def _resolve_release_tag_version(item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        tag = str(item.get("tag_name") or "").strip()
        ver = _normalize_tag(tag)
        if not parse_version(ver):
            return None
        return tag, ver

    def _resolve_release_assets(
        self, item: Dict[str, Any]
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        asset = self._find_setup_asset(item.get("assets") or [])
        if not asset:
            return None
        checksum = self._find_checksum_asset(item.get("assets") or [], str(asset.get("name") or ""))
        if not checksum:
            return None
        return asset, checksum

    def _release_from_item(self, item: Any) -> Optional[ReleaseInfo]:
        if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
            return None
        tag_version = self._resolve_release_tag_version(item)
        if tag_version is None:
            return None
        tag, ver = tag_version
        if not version_gt(ver, self.current_version):
            return None
        assets = self._resolve_release_assets(item)
        if assets is None:
            return None
        asset, checksum = assets
        return ReleaseInfo(
            version=ver,
            tag=tag or f"v{ver}",
            notes=str(item.get("body") or "").strip(),
            release_url=str(item.get("html_url") or ""),
            download_url=str(asset.get("browser_download_url") or ""),
            asset_name=str(asset.get("name") or ""),
            checksum_url=str((checksum or {}).get("browser_download_url") or ""),
            checksum_name=str((checksum or {}).get("name") or ""),
            published_at=str(item.get("published_at") or ""),
        )

    def _pick_latest(
        self, releases: List[Dict[str, Any]]
    ) -> Tuple[Optional[ReleaseInfo], str]:
        newer = [info for item in releases if (info := self._release_from_item(item)) is not None]
        if not newer:
            return None, ""
        newer.sort(key=lambda r: parse_version(r.version) or (0,))
        latest = newer[-1]
        notes = self._aggregate_notes(newer)
        return latest, notes

    @staticmethod
    def _strict_setup_assets(assets: List[Any]) -> List[Dict[str, Any]]:
        return [
            a
            for a in assets
            if isinstance(a, dict)
            and str(a.get("browser_download_url") or "")
            and SETUP_ASSET_RE.match(str(a.get("name") or ""))
        ]

    @staticmethod
    def _fallback_setup_assets(assets: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for a in assets:
            if not isinstance(a, dict):
                continue
            name = str(a.get("name") or "").lower()
            url = str(a.get("browser_download_url") or "")
            if url and name.endswith(".exe") and "setup" in name:
                result.append(a)
        return result

    @staticmethod
    def _find_setup_asset(assets: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(assets, list):
            return None
        candidates = UpdateService._strict_setup_assets(assets) or UpdateService._fallback_setup_assets(assets)
        return candidates[0] if candidates else None

    @staticmethod
    def _find_checksum_asset(assets: Any, setup_name: str) -> Optional[Dict[str, Any]]:
        if not isinstance(assets, list) or not setup_name:
            return None
        exact = {f"{setup_name}.sha256".casefold(), f"{setup_name}.sha256.txt".casefold()}
        fallback = None
        for asset in assets:
            if not isinstance(asset, dict) or not asset.get("browser_download_url"):
                continue
            name = str(asset.get("name") or "")
            if name.casefold() in exact:
                return asset
            if name.casefold() in {"checksums.sha256", "sha256sums.txt"}:
                fallback = asset
        return fallback

    @staticmethod
    def _clean_release_notes(text: str) -> str:
        lines = []
        for raw in str(text or "").replace("\r\n", "\n").split("\n"):
            line = raw.rstrip()
            stripped = line.lstrip()
            if stripped.startswith("#"):
                line = stripped.lstrip("#").strip()
            line = line.replace("**", "").replace("__", "")
            lines.append(line)
        text = "\n".join(lines)
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

    @classmethod
    def _aggregate_notes(cls, releases_asc: List[ReleaseInfo]) -> str:
        parts: List[str] = []
        for rel in reversed(releases_asc):
            body = cls._clean_release_notes(rel.notes or "")
            if body:
                parts.append(body)
            else:
                parts.append(f"[{rel.version}]\n\n(No release notes)")
        text = "\n\n".join(parts).strip()
        if len(text) > RELEASE_NOTES_MAX_LENGTH:
            text = text[:RELEASE_NOTES_MAX_LENGTH].rstrip() + "\n\n..."
        return text

    @staticmethod
    def _setup_asset_filename(pending: Dict[str, Any], version: str) -> str:
        name = str(pending.get("asset_name") or f"Velo-Setup-{version}.exe")
        return re.sub(r"[^\w.\-]+", "_", name) or f"Velo-Setup-{version}.exe"

    def _write_download_body(self, resp: Any, tmp: Path, total_n: int) -> None:
        read = 0
        with open(tmp, "wb") as out:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                read += len(chunk)
                if read > MAX_UPDATE_BYTES:
                    raise RuntimeError("Update download exceeded the size limit")
                if total_n > 0:
                    with self._lock:
                        self._download_progress = min(0.99, read / total_n)

    def _stream_download(self, req: urllib.request.Request, tmp: Path, dest: Path) -> None:
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self._validate_release_url(resp.geturl())
                total = resp.headers.get("Content-Length")
                try:
                    total_n = int(total) if total else 0
                except ValueError:
                    total_n = 0
                if total_n > MAX_UPDATE_BYTES:
                    raise RuntimeError("Update download is unexpectedly large")
                self._write_download_body(resp, tmp, total_n)
                tmp.replace(dest)
        except urllib.error.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Download failed (HTTP {exc.code})") from exc
        except urllib.error.URLError as exc:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Download failed: {exc.reason}") from exc
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _verify_downloaded_installer(self, dest: Path, checksum_url: str, name: str) -> None:
        if not dest.exists() or dest.stat().st_size < 1024:
            raise RuntimeError("Downloaded installer is missing or too small")
        expected = self._fetch_checksum(checksum_url, name)
        digest = hashlib.sha256()
        with dest.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        actual = digest.hexdigest()
        if not hmac.compare_digest(actual.casefold(), expected.casefold()):
            dest.unlink(missing_ok=True)
            raise RuntimeError("Downloaded installer failed SHA-256 verification")

    def _download_setup(self, pending: Dict[str, Any]) -> Path:
        url = str(pending.get("download_url") or "")
        checksum_url = str(pending.get("checksum_url") or "")
        if not checksum_url:
            raise RuntimeError("Release is missing its SHA-256 checksum; installation was blocked")
        self._validate_release_url(url)
        self._validate_release_url(checksum_url)
        version = str(pending.get("version") or "update")
        name = self._setup_asset_filename(pending, version)
        dest = _updates_dir() / name
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
            method="GET",
        )
        tmp = dest.with_suffix(dest.suffix + ".part")
        self._stream_download(req, tmp, dest)
        self._verify_downloaded_installer(dest, checksum_url, name)
        return dest

    @staticmethod
    def _validate_release_url(url: str) -> None:
        parsed = urlparse(str(url or ""))
        host = (parsed.hostname or "").casefold()
        allowed = (
            host == "github.com"
            or host == "api.github.com"
            or host.endswith(".githubusercontent.com")
        )
        if parsed.scheme != "https" or not allowed:
            raise RuntimeError("Untrusted update download URL")

    def _fetch_checksum(self, url: str, asset_name: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                self._validate_release_url(resp.geturl())
                raw = resp.read(MAX_CHECKSUM_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Checksum download failed (HTTP {exc.code})") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Checksum download failed: {exc.reason}") from exc
        if len(raw) > MAX_CHECKSUM_BYTES:
            raise RuntimeError("Checksum file is unexpectedly large")
        text = raw.decode("utf-8", errors="replace")
        entries = re.findall(r"(?im)^([0-9a-f]{64})(?:\s+[*]?(.+?))?\s*$", text)
        for digest, filename in entries:
            if not filename or Path(filename.strip()).name.casefold() == asset_name.casefold():
                return digest.lower()
        raise RuntimeError("Checksum file does not contain the installer hash")


def launch_installer(setup_path: Path) -> None:
    path = Path(setup_path)
    if not path.is_file():
        raise RuntimeError(f"Installer not found: {path}")
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    subprocess.Popen([str(path)], cwd=str(path.parent), close_fds=True)


def _clean_opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
