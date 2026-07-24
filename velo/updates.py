from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from velo.config import config_dir
from velo.defaults import APP_NAME, APP_VERSION

GITHUB_OWNER = "aechXIII"
GITHUB_REPO = "Velo"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
USER_AGENT = f"{APP_NAME}-Updater/{APP_VERSION}"
CHECK_INTERVAL_S = 24 * 3600
REMIND_LATER_S = 24 * 3600
SETUP_ASSET_RE = re.compile(r"^Velo-Setup-.*\.exe$", re.IGNORECASE)

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
    published_at: str


class UpdateService:
    def __init__(
        self,
        *,
        current_version: str = APP_VERSION,
        on_available: Optional[OnAvailableCallback] = None,
        on_install_ready: Optional[OnInstallReadyCallback] = None,
    ) -> None:
        self.current_version = str(current_version or APP_VERSION).strip()
        self._on_available = on_available
        self._on_install_ready = on_install_ready
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
        remind = raw.get("remind_after")
        try:
            self._remind_after = float(remind) if remind is not None else None
        except (TypeError, ValueError):
            self._remind_after = None
        last = raw.get("last_check_at")
        try:
            self._last_check_at = float(last) if last is not None else None
        except (TypeError, ValueError):
            self._last_check_at = None
        pending = raw.get("pending")
        if isinstance(pending, dict) and pending.get("version") and pending.get("download_url"):
            self._pending = {
                "version": str(pending.get("version") or ""),
                "tag": str(pending.get("tag") or ""),
                "notes": str(pending.get("notes") or ""),
                "release_url": str(pending.get("release_url") or ""),
                "download_url": str(pending.get("download_url") or ""),
                "asset_name": str(pending.get("asset_name") or ""),
            }
            if not version_gt(self._pending["version"], self.current_version):
                self._pending = None

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

    def status(self) -> Dict[str, Any]:
        with self._lock:
            pending = dict(self._pending) if self._pending else None
            has_newer = bool(
                pending
                and version_gt(str(pending.get("version") or ""), self.current_version)
            )
            actionable = self._is_actionable_unlocked()
            skipped = False
            if has_newer and pending and self._skipped_version:
                skipped = not version_gt(
                    str(pending.get("version") or ""), self._skipped_version
                )
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
            }

    def pending_version(self) -> Optional[str]:
        with self._lock:
            if self._is_actionable_unlocked() and self._pending:
                return str(self._pending.get("version") or "") or None
            return None

    def _is_actionable_unlocked(self) -> bool:
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
        if not enabled:
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
                except Exception:
                    pass

        threading.Thread(target=_run, name="velo-update-check", daemon=True).start()
        return True

    def check_now(self, *, manual: bool = False, notify: bool = True) -> Dict[str, Any]:
        with self._lock:
            self._checking = True
            self._last_error = None
        try:
            releases = self._fetch_releases()
            latest, notes = self._pick_latest(releases)
            with self._lock:
                self._last_check_at = time.time()
                if latest is None:
                    self._pending = None
                else:
                    self._pending = {
                        "version": latest.version,
                        "tag": latest.tag,
                        "notes": notes,
                        "release_url": latest.release_url,
                        "download_url": latest.download_url,
                        "asset_name": latest.asset_name,
                    }
                    if manual:
                        self._remind_after = None
                self._save_state()
                status = self.status()
            if notify and status.get("should_prompt") and self._on_available:
                try:
                    self._on_available(status)
                except Exception:
                    pass
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

    def install_async(self) -> Dict[str, Any]:
        with self._lock:
            if self._installing:
                return {**self.status(), "ok": False, "error": "Install already in progress"}
            if not self._pending or not self._pending.get("download_url"):
                return {**self.status(), "ok": False, "error": "No update available to install"}
            pending = dict(self._pending)
            if not version_gt(str(pending.get("version") or ""), self.current_version):
                return {**self.status(), "ok": False, "error": "Already up to date"}
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
            except Exception:
                pass
            raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
        data = json.loads(body)
        if not isinstance(data, list):
            raise RuntimeError("Unexpected GitHub API response")
        return data

    def _pick_latest(
        self, releases: List[Dict[str, Any]]
    ) -> Tuple[Optional[ReleaseInfo], str]:
        newer: List[ReleaseInfo] = []
        for item in releases:
            if not isinstance(item, dict):
                continue
            if item.get("draft") or item.get("prerelease"):
                continue
            tag = str(item.get("tag_name") or "").strip()
            ver = _normalize_tag(tag)
            if not parse_version(ver):
                continue
            if not version_gt(ver, self.current_version):
                continue
            asset = self._find_setup_asset(item.get("assets") or [])
            if not asset:
                continue
            notes = str(item.get("body") or "").strip()
            newer.append(
                ReleaseInfo(
                    version=ver,
                    tag=tag or f"v{ver}",
                    notes=notes,
                    release_url=str(item.get("html_url") or ""),
                    download_url=str(asset.get("browser_download_url") or ""),
                    asset_name=str(asset.get("name") or ""),
                    published_at=str(item.get("published_at") or ""),
                )
            )
        if not newer:
            return None, ""
        newer.sort(key=lambda r: parse_version(r.version) or (0,))
        latest = newer[-1]
        notes = self._aggregate_notes(newer)
        return latest, notes

    @staticmethod
    def _find_setup_asset(assets: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(assets, list):
            return None
        candidates: List[Dict[str, Any]] = []
        for a in assets:
            if not isinstance(a, dict):
                continue
            name = str(a.get("name") or "")
            url = str(a.get("browser_download_url") or "")
            if not url:
                continue
            if SETUP_ASSET_RE.match(name):
                candidates.append(a)
        if not candidates:
            for a in assets:
                if not isinstance(a, dict):
                    continue
                name = str(a.get("name") or "").lower()
                url = str(a.get("browser_download_url") or "")
                if url and name.endswith(".exe") and "setup" in name:
                    candidates.append(a)
        if not candidates:
            return None
        return candidates[0]

    @staticmethod
    def _aggregate_notes(releases_asc: List[ReleaseInfo]) -> str:
        parts: List[str] = []
        for rel in reversed(releases_asc):
            body = (rel.notes or "").strip()
            header = f"## {rel.version}"
            if body:
                if body.lstrip().lower().startswith("## "):
                    parts.append(body)
                else:
                    parts.append(f"{header}\n\n{body}")
            else:
                parts.append(f"{header}\n\n(No release notes)")
        text = "\n\n".join(parts).strip()
        if len(text) > 8000:
            text = text[:8000].rstrip() + "\n\n..."
        return text

    def _download_setup(self, pending: Dict[str, Any]) -> Path:
        url = str(pending.get("download_url") or "")
        version = str(pending.get("version") or "update")
        name = str(pending.get("asset_name") or f"Velo-Setup-{version}.exe")
        name = re.sub(r"[^\w.\-]+", "_", name) or f"Velo-Setup-{version}.exe"
        dest = _updates_dir() / name
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = resp.headers.get("Content-Length")
                try:
                    total_n = int(total) if total else 0
                except ValueError:
                    total_n = 0
                tmp = dest.with_suffix(dest.suffix + ".part")
                read = 0
                with open(tmp, "wb") as out:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        read += len(chunk)
                        if total_n > 0:
                            with self._lock:
                                self._download_progress = min(0.99, read / total_n)
                tmp.replace(dest)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Download failed (HTTP {exc.code})") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Download failed: {exc.reason}") from exc
        if not dest.exists() or dest.stat().st_size < 1024:
            raise RuntimeError("Downloaded installer is missing or too small")
        return dest


def launch_installer(setup_path: Path) -> None:
    path = Path(setup_path)
    if not path.is_file():
        raise RuntimeError(f"Installer not found: {path}")
    if os.name == "nt":
        getattr(os, "startfile")(str(path))
        return
    subprocess.Popen([str(path)], cwd=str(path.parent), close_fds=True)


def _clean_opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
