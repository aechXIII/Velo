"""Persistent configuration store for Velo."""

from __future__ import annotations

import base64
import binascii
import json
import secrets
import threading
import zlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from velo.config_types import ConfigMap
from velo.defaults import (
    APP_NAME,
    APP_VERSION,
    DEFAULTS,
    FEEL_PRESETS,
    PRESET_CLIP_PREFIX,
    PRESET_EXCLUDE,
    PRESETS,
    QUALITY_PRESETS,
    SHELL_KEYS,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULTS",
    "FEEL_PRESETS",
    "PRESET_CLIP_PREFIX",
    "PRESET_EXCLUDE",
    "PRESETS",
    "QUALITY_PRESETS",
    "SHELL_KEYS",
    "ConfigMap",
    "ConfigStore",
    "config_dir",
    "config_path",
    "presets_dir",
    "list_presets",
    "list_builtin_preset_names",
]

def config_dir() -> Path:
    base = Path.home() / "AppData" / "Roaming" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    return config_dir() / "config.json"


def presets_dir() -> Path:
    d = config_dir() / "presets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def legacy_user_presets_path() -> Path:
    return config_dir() / "user_presets.json"


def _sanitize_preset_name(name: str) -> str:
    n = " ".join(str(name or "").strip().split())
    if not n:
        raise ValueError("empty name")
    if len(n) > 48:
        n = n[:48].rstrip()
    for ch in ("\\", "/", ":", "*", "?", '"', "<", ">", "|"):
        n = n.replace(ch, "")
    n = n.strip()
    if not n:
        raise ValueError("invalid name")
    return n


def _preset_stem(name: str) -> str:
    safe = _sanitize_preset_name(name)
    stem = "_".join(safe.split())
    stem = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in stem)
    stem = stem.strip("._") or "preset"
    return stem[:64]


def _preset_file_for_name(name: str, directory: Optional[Path] = None) -> Path:
    return (directory or presets_dir()) / f"{_preset_stem(name)}.json"


class ConfigStore:
    def __init__(
        self,
        path: Optional[Path] = None,
        presets_path: Optional[Path] = None,
    ) -> None:
        self._path = path or config_path()
        self._presets_dir = presets_path or presets_dir()
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = deepcopy(DEFAULTS)
        self._user_presets: Dict[str, Dict[str, Any]] = {}
        self._user_preset_files: Dict[str, Path] = {}
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.load()
        self._load_user_presets()

    def load(self) -> None:
        with self._lock:
            if self._path.exists():
                try:
                    raw = json.loads(self._path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        merged = deepcopy(DEFAULTS)
                        for k, v in raw.items():
                            if k in DEFAULTS:
                                merged[k] = v
                        if "stats_x_pct" not in raw and "stats_position" in raw:
                            pos = str(raw.get("stats_position") or "bottom-left")
                            corners = {
                                "top-left": (0.0, 0.0),
                                "top-right": (100.0, 0.0),
                                "bottom-left": (0.0, 100.0),
                                "bottom-right": (100.0, 100.0),
                            }
                            if pos in corners:
                                merged["stats_x_pct"], merged["stats_y_pct"] = corners[pos]
                        if "render_quality" not in raw and int(merged.get("trail_max_points") or 0) >= 250:
                            for k, v in QUALITY_PRESETS["balanced"].items():
                                merged[k] = deepcopy(v)
                            merged["render_quality"] = "balanced"
                            merged["ui_preview_mode"] = "lite"
                        self._data = merged
                except (json.JSONDecodeError, OSError):
                    self._data = deepcopy(DEFAULTS)
            if not self._data.get("auth_token"):
                self._data["auth_token"] = secrets.token_urlsafe(18)
                self._write_unlocked()

    def save(self) -> None:
        with self._lock:
            self._write_unlocked()

    def _write_unlocked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._data.get(key, default))

    def update(self, patch: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
        with self._lock:
            if "render_quality" in patch:
                qname = str(patch.get("render_quality") or "balanced")
                q = QUALITY_PRESETS.get(qname)
                if q:
                    for k, v in q.items():
                        if k not in patch:
                            self._data[k] = deepcopy(v)
            if "motion_feel" in patch:
                fname = str(patch.get("motion_feel") or "normal")
                if fname != "custom":
                    feel = FEEL_PRESETS.get(fname)
                    if feel:
                        for k, v in feel.items():
                            if k not in patch:
                                self._data[k] = deepcopy(v)
            feel_keys = ("motion_scale", "motion_ease", "camera_lag")
            if any(k in patch for k in feel_keys) and "motion_feel" not in patch:
                patch = {**patch, "motion_feel": "custom"}
            for key, value in patch.items():
                if key == "click_colors" and isinstance(value, dict):
                    base = self._data.get("click_colors") or {}
                    if not isinstance(base, dict):
                        base = {}
                    merged = deepcopy(base)
                    merged.update(deepcopy(value))
                    self._data["click_colors"] = merged
                elif key in DEFAULTS or key in self._data:
                    self._data[key] = deepcopy(value)
            if persist:
                self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def _load_user_presets(self) -> None:
        with self._lock:
            self._user_presets = {}
            self._user_preset_files = {}
            self._presets_dir.mkdir(parents=True, exist_ok=True)
            self._migrate_legacy_user_presets_unlocked()
            for path in sorted(self._presets_dir.glob("*.json")):
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if not isinstance(raw, dict):
                    continue
                if isinstance(raw.get("settings"), dict):
                    name = str(raw.get("name") or path.stem).strip()
                    settings = raw["settings"]
                else:
                    name = str(raw.get("name") or path.stem).strip()
                    settings = {k: v for k, v in raw.items() if k != "name"}
                try:
                    name = _sanitize_preset_name(name)
                except ValueError:
                    continue
                if not isinstance(settings, dict):
                    continue
                if name in self._user_presets:
                    continue
                clean = {
                    k: deepcopy(v)
                    for k, v in settings.items()
                    if k in DEFAULTS and k not in PRESET_EXCLUDE
                }
                self._user_presets[name] = clean
                self._user_preset_files[name] = path

    def _legacy_user_presets_file(self) -> Path:
        return self._path.parent / "user_presets.json"

    def _migrate_legacy_user_presets_unlocked(self) -> None:
        legacy = self._legacy_user_presets_file()
        candidates = [legacy]
        default_legacy = legacy_user_presets_path()
        if default_legacy.resolve() != legacy.resolve():
            try:
                if self._presets_dir.resolve() == presets_dir().resolve():
                    candidates.append(default_legacy)
            except OSError:
                pass

        for legacy_path in candidates:
            if not legacy_path.is_file():
                continue
            if any(self._presets_dir.glob("*.json")):
                if legacy_path == default_legacy or legacy_path == legacy:
                    try:
                        bak = legacy_path.with_suffix(".json.bak")
                        if not bak.exists():
                            legacy_path.rename(bak)
                    except OSError:
                        pass
                continue
            try:
                raw = json.loads(legacy_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(raw, dict):
                continue
            for name, patch in raw.items():
                if not isinstance(name, str) or not isinstance(patch, dict):
                    continue
                try:
                    clean_name = _sanitize_preset_name(name)
                except ValueError:
                    continue
                body = {
                    k: deepcopy(v)
                    for k, v in patch.items()
                    if k in DEFAULTS and k not in PRESET_EXCLUDE
                }
                try:
                    self._write_preset_file_unlocked(clean_name, body)
                except OSError:
                    continue
            try:
                bak = legacy_path.with_suffix(".json.bak")
                if not bak.exists():
                    legacy_path.rename(bak)
            except OSError:
                pass

    def _write_preset_file_unlocked(self, name: str, settings: Dict[str, Any]) -> Path:
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        path = self._user_preset_files.get(name) or _preset_file_for_name(
            name, self._presets_dir
        )
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                existing_name = str(
                    (existing or {}).get("name") or path.stem
                ).strip()
                if existing_name and existing_name != name:
                    stem = _preset_stem(name)
                    n = 2
                    while True:
                        candidate = self._presets_dir / f"{stem}_{n}.json"
                        if not candidate.exists():
                            path = candidate
                            break
                        n += 1
            except (json.JSONDecodeError, OSError, TypeError):
                pass

        payload = {
            "name": name,
            "settings": {
                k: deepcopy(v)
                for k, v in settings.items()
                if k in DEFAULTS and k not in PRESET_EXCLUDE
            },
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        self._user_presets[name] = deepcopy(payload["settings"])
        self._user_preset_files[name] = path
        return path

    def _delete_preset_file_unlocked(self, name: str) -> None:
        path = self._user_preset_files.pop(name, None)
        self._user_presets.pop(name, None)
        if path is None:
            path = _preset_file_for_name(name, self._presets_dir)
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    def preset_snapshot(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {k: v for k, v in snap.items() if k not in PRESET_EXCLUDE}

    def list_presets(self) -> Dict[str, Any]:
        with self._lock:
            self._load_user_presets()
            builtin = [{"name": n, "kind": "builtin"} for n in PRESETS.keys()]
            user = [{"name": n, "kind": "user"} for n in sorted(self._user_presets.keys())]
            return {
                "builtin": builtin,
                "user": user,
                "active": self._data.get("active_preset") or "",
                "active_kind": self._data.get("active_preset_kind") or "builtin",
                "presets_dir": str(self._presets_dir),
            }

    def apply_preset(self, name: str, kind: Optional[str] = None) -> Dict[str, Any]:
        name = str(name or "").strip()
        kind = (kind or "").strip().lower() or None
        with self._lock:
            if kind in (None, "user"):
                self._load_user_presets()
            patch: Optional[Dict[str, Any]] = None
            resolved = kind
            if resolved in (None, "user") and name in self._user_presets:
                patch = deepcopy(self._user_presets[name])
                resolved = "user"
            if patch is None and resolved in (None, "builtin") and name in PRESETS:
                patch = deepcopy(PRESETS[name])
                resolved = "builtin"
            if patch is None:
                return self.snapshot()
            clean = {
                k: v for k, v in patch.items() if k in DEFAULTS and k not in PRESET_EXCLUDE
            }
            clean["active_preset"] = name
            clean["active_preset_kind"] = resolved or "builtin"
        return self.update(clean, persist=True)

    def save_user_preset(self, name: str, overwrite: bool = False) -> Dict[str, Any]:
        name = _sanitize_preset_name(name)
        if name in PRESETS:
            raise ValueError("name conflicts with a built-in preset")
        with self._lock:
            self._load_user_presets()
            if name in self._user_presets and not overwrite:
                raise ValueError("preset already exists")
            body = {k: v for k, v in self.preset_snapshot().items() if k in DEFAULTS}
            self._write_preset_file_unlocked(name, body)
            self._data["active_preset"] = name
            self._data["active_preset_kind"] = "user"
            self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def update_user_preset(self, name: str) -> Dict[str, Any]:
        name = _sanitize_preset_name(name)
        with self._lock:
            self._load_user_presets()
            if name not in self._user_presets:
                raise ValueError("user preset not found")
        return self.save_user_preset(name, overwrite=True)

    def delete_user_preset(self, name: str) -> Dict[str, Any]:
        name = str(name or "").strip()
        with self._lock:
            self._load_user_presets()
            if name not in self._user_presets:
                raise ValueError("user preset not found")
            self._delete_preset_file_unlocked(name)
            if (
                self._data.get("active_preset") == name
                and self._data.get("active_preset_kind") == "user"
            ):
                self._data["active_preset"] = ""
                self._data["active_preset_kind"] = "builtin"
                self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def rename_user_preset(self, old_name: str, new_name: str) -> Dict[str, Any]:
        old_name = str(old_name or "").strip()
        new_name = _sanitize_preset_name(new_name)
        if new_name in PRESETS:
            raise ValueError("name conflicts with a built-in preset")
        with self._lock:
            self._load_user_presets()
            if old_name not in self._user_presets:
                raise ValueError("user preset not found")
            if new_name != old_name and new_name in self._user_presets:
                raise ValueError("preset already exists")
            if new_name == old_name:
                return self.snapshot()
            settings = deepcopy(self._user_presets[old_name])
            old_path = self._user_preset_files.get(old_name)
            self._user_presets.pop(old_name, None)
            self._user_preset_files.pop(old_name, None)
            self._write_preset_file_unlocked(new_name, settings)
            new_path = self._user_preset_files.get(new_name)
            if old_path is not None and (new_path is None or old_path.resolve() != new_path.resolve()):
                try:
                    if old_path.is_file():
                        old_path.unlink()
                except OSError:
                    pass
            if (
                self._data.get("active_preset") == old_name
                and self._data.get("active_preset_kind") == "user"
            ):
                self._data["active_preset"] = new_name
                self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def get_preset_settings(
        self, name: str, kind: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        name = str(name or "").strip()
        kind = (kind or "").strip().lower() or None
        with self._lock:
            if kind in (None, "user"):
                self._load_user_presets()
            if kind in (None, "user") and name in self._user_presets:
                return "user", deepcopy(self._user_presets[name])
            if kind in (None, "builtin") and name in PRESETS:
                clean = {
                    k: deepcopy(v)
                    for k, v in PRESETS[name].items()
                    if k in DEFAULTS and k not in PRESET_EXCLUDE
                }
                return "builtin", clean
        raise ValueError("preset not found")

    def export_preset_payload(
        self, name: str, kind: Optional[str] = None
    ) -> Dict[str, Any]:
        resolved, settings = self.get_preset_settings(name, kind)
        return {
            "app": APP_NAME,
            "type": "preset",
            "version": APP_VERSION,
            "name": name,
            "kind": resolved,
            "settings": settings,
        }

    def encode_preset_share(self, name: str, kind: Optional[str] = None) -> str:
        payload = self.export_preset_payload(name, kind)
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        token = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
        return PRESET_CLIP_PREFIX + token

    def decode_preset_share(self, text: str) -> Dict[str, Any]:
        s = str(text or "").strip().strip("\ufeff")
        if not s:
            raise ValueError("empty preset data")
        first = s.splitlines()[0].strip()
        data: Any
        if first.startswith(PRESET_CLIP_PREFIX) or s.startswith(PRESET_CLIP_PREFIX):
            blob = first[len(PRESET_CLIP_PREFIX) :].strip() if first.startswith(PRESET_CLIP_PREFIX) else s[len(PRESET_CLIP_PREFIX) :].strip()
            blob = "".join(blob.split())
            try:
                pad = "=" * (-len(blob) % 4)
                raw = zlib.decompress(base64.urlsafe_b64decode(blob + pad))
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, TypeError, zlib.error, json.JSONDecodeError, binascii.Error) as exc:
                raise ValueError("invalid preset code") from exc
        else:
            try:
                data = json.loads(s)
            except json.JSONDecodeError as exc:
                raise ValueError("invalid preset JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("invalid preset data")
        if data.get("type") == "preset" or "settings" in data:
            name = str(data.get("name") or "Imported").strip()
            settings = data.get("settings")
            if not isinstance(settings, dict):
                raise ValueError("missing preset settings")
        else:
            name = str(data.get("name") or "Imported").strip()
            settings = {k: v for k, v in data.items() if k != "name"}
        clean = {
            k: deepcopy(v)
            for k, v in settings.items()
            if k in DEFAULTS and k not in PRESET_EXCLUDE
        }
        if not clean:
            raise ValueError("no recognized preset settings")
        try:
            name = _sanitize_preset_name(name)
        except ValueError:
            name = "Imported"
        return {"name": name, "settings": clean}

    def import_preset_payload(
        self,
        data: Dict[str, Any],
        *,
        name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("invalid preset data")
        if "settings" in data and isinstance(data.get("settings"), dict):
            settings = data["settings"]
            base_name = str(data.get("name") or name or "Imported")
        else:
            settings = data
            base_name = str(name or "Imported")
        try:
            final_name = _sanitize_preset_name(name or base_name)
        except ValueError as exc:
            raise ValueError("invalid name") from exc
        if final_name in PRESETS:
            raise ValueError("name conflicts with a built-in preset")
        clean = {
            k: deepcopy(v)
            for k, v in settings.items()
            if k in DEFAULTS and k not in PRESET_EXCLUDE
        }
        if not clean:
            raise ValueError("no recognized preset settings")
        with self._lock:
            self._load_user_presets()
            if final_name in self._user_presets and not overwrite:
                n = 2
                stem = final_name
                while f"{stem} {n}" in self._user_presets or f"{stem} {n}" in PRESETS:
                    n += 1
                    if n > 99:
                        raise ValueError("preset already exists")
                final_name = f"{stem} {n}"
            self._write_preset_file_unlocked(final_name, clean)
            self._data["active_preset"] = final_name
            self._data["active_preset_kind"] = "user"
            for k, v in clean.items():
                self._data[k] = deepcopy(v)
            self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def reset_defaults(self, keep_auth: bool = True) -> Dict[str, Any]:
        with self._lock:
            token = self._data.get("auth_token", "")
            obs_done = bool(self._data.get("ui_obs_setup_done"))
            self._data = deepcopy(DEFAULTS)
            if keep_auth and token:
                self._data["auth_token"] = token
            elif not self._data.get("auth_token"):
                self._data["auth_token"] = secrets.token_urlsafe(18)
            self._data["ui_obs_setup_done"] = obs_done
            self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def reset_visuals(self) -> Dict[str, Any]:
        with self._lock:
            kept = {k: deepcopy(self._data.get(k, DEFAULTS.get(k))) for k in SHELL_KEYS}
            token = kept.get("auth_token") or ""
            self._data = deepcopy(DEFAULTS)
            for k, v in kept.items():
                if v is not None:
                    self._data[k] = v
            if not self._data.get("auth_token"):
                self._data["auth_token"] = token or secrets.token_urlsafe(18)
            self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def export_bundle(self, include_connection: bool = True) -> Dict[str, Any]:
        snap = self.snapshot()
        if not include_connection:
            for k in ("host", "port", "auth_token"):
                snap.pop(k, None)
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "config": snap,
        }

    def import_bundle(
        self,
        data: Dict[str, Any],
        *,
        include_connection: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("invalid bundle")
        cfg = data.get("config") if "config" in data else data
        if not isinstance(cfg, dict):
            raise ValueError("missing config object")
        patch: Dict[str, Any] = {}
        for k, v in cfg.items():
            if k not in DEFAULTS:
                continue
            if not include_connection and k in ("host", "port", "auth_token", "auth_enabled"):
                continue
            if k == "ui_obs_setup_done" and not include_connection:
                continue
            patch[k] = v
        if not patch:
            raise ValueError("no recognized settings in file")
        return self.update(patch, persist=True)

    def on_change(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners = [cb for cb in self._listeners if cb is not callback]

    def _emit(self, snap: Dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                cb(snap)
            except Exception:
                # Listeners (server/pipeline/shell) must not break config writes.
                continue

    def overlay_public(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {k: v for k, v in snap.items() if k != "auth_token"}

    def overlay_url(self, for_display_host: Optional[str] = None) -> str:
        host = for_display_host or self.get("host") or "127.0.0.1"
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        port = int(self.get("port") or 27180)
        token = self.get("auth_token") or ""
        auth = self.get("auth_enabled")
        if auth and token:
            return f"http://{host}:{port}/overlay?token={token}"
        return f"http://{host}:{port}/overlay"

    def config_url(self) -> str:
        host = self.get("host") or "127.0.0.1"
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        port = int(self.get("port") or 27180)
        token = self.get("auth_token") or ""
        if self.get("auth_enabled") and token:
            return f"http://{host}:{port}/config?token={token}"
        return f"http://{host}:{port}/config"

    def ws_url(self) -> str:
        host = self.get("host") or "127.0.0.1"
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        port = int(self.get("port") or 27180)
        return f"ws://{host}:{port}/ws"


def list_presets() -> List[str]:
    return list(PRESETS.keys())


def list_builtin_preset_names() -> List[str]:
    return list(PRESETS.keys())
