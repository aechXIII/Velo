"""Persistent configuration store for Velo."""

from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
import io
import json
import os
import secrets
import shutil
import threading
import time
import zlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from velo.config_types import ConfigMap
from velo.config_schema import ValidationError, require_valid_config, validate_config
from velo.constants import MAX_PRESET_NAME_LENGTH
from velo.logging import get_logger
from velo.defaults import (
    APP_NAME,
    APP_VERSION,
    DEFAULTS,
    FEEL_PRESETS,
    PRESET_CLIP_PREFIX,
    PRESET_CLIP_PREFIX_V2,
    PRESET_EXCLUDE,
    PRESETS,
    QUALITY_PRESETS,
    REVERSE_SHARE_ALIASES,
    SHARE_ALIASES,
    SHELL_KEYS,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULTS",
    "FEEL_PRESETS",
    "PRESET_CLIP_PREFIX",
    "PRESET_CLIP_PREFIX_V2",
    "PRESET_EXCLUDE",
    "PRESETS",
    "QUALITY_PRESETS",
    "REVERSE_SHARE_ALIASES",
    "SHARE_ALIASES",
    "SHELL_KEYS",
    "ConfigMap",
    "ConfigStore",
    "config_dir",
    "config_path",
    "presets_dir",
    "list_presets",
    "list_builtin_preset_names",
]

logger = get_logger()


def config_dir() -> Path:
    roaming = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    base = roaming / APP_NAME
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
    return stem[:MAX_PRESET_NAME_LENGTH]


def _preset_file_for_name(name: str, directory: Optional[Path] = None) -> Path:
    return (directory or presets_dir()) / f"{_preset_stem(name)}.json"


MAX_BACKGROUND_IMAGE_BYTES = 2 * 1024 * 1024
MAX_PRESET_CODE_BYTES = 1024 * 1024
_IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}


def _decompress_preset(blob: bytes) -> bytes:
    if len(blob) > MAX_PRESET_CODE_BYTES:
        raise ValueError("preset code is too large")
    inflater = zlib.decompressobj()
    raw = inflater.decompress(blob, MAX_PRESET_CODE_BYTES + 1)
    if inflater.unconsumed_tail or len(raw) > MAX_PRESET_CODE_BYTES:
        raise ValueError("preset data is too large")
    raw += inflater.flush()
    if len(raw) > MAX_PRESET_CODE_BYTES:
        raise ValueError("preset data is too large")
    return raw


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
        self._last_backup_at = 0.0
        self._recovery_notice: Optional[str] = None
        self.load()
        self._load_user_presets()
        self._last_active = ("", "builtin")

    def _load_from_disk_unlocked(self) -> bool:
        if not self._path.exists():
            return False
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root is not an object")
            self._data, normalized = self._merge_loaded_config_unlocked(raw)
            return normalized
        except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
            self._data = self._recover_invalid_config_unlocked(exc)
            return True

    def _normalize_background_image_unlocked(self) -> bool:
        image_value = self._data.get("pad_bg_image")
        if not (isinstance(image_value, str) and image_value.startswith("data:image/")):
            return False
        try:
            self._data["pad_bg_image"] = self._store_background_data_url_unlocked(image_value)
        except ValueError:
            self._data["pad_bg_image"] = ""
            self._data["pad_bg_image_enabled"] = False
        return True

    def _ensure_auth_token_unlocked(self) -> bool:
        if self._data.get("auth_token"):
            return False
        self._data["auth_token"] = secrets.token_urlsafe(18)
        return True

    def load(self) -> None:
        with self._lock:
            dirty = self._load_from_disk_unlocked()
            dirty = self._normalize_background_image_unlocked() or dirty
            dirty = self._ensure_auth_token_unlocked() or dirty
            if dirty:
                self._write_unlocked()

    def _merge_raw_keys_unlocked(self, raw: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        merged = deepcopy(DEFAULTS)
        dirty = False
        for key, value in raw.items():
            if key == "pad_bg_image" and isinstance(value, str) and value.startswith("data:image/"):
                merged[key] = value
            elif key in DEFAULTS:
                if validate_config({key: value}, strict=True):
                    dirty = True
                else:
                    merged[key] = value
            else:
                dirty = True
        return merged, dirty

    def _migrate_legacy_config_keys_unlocked(
        self, merged: Dict[str, Any], raw: Dict[str, Any]
    ) -> bool:
        """Backfill settings renamed/restructured in later versions. Mutates `merged`."""
        dirty = False
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
            dirty = True
        if "render_quality" not in raw and int(merged.get("trail_max_points") or 0) >= 250:
            for key, value in QUALITY_PRESETS["balanced"].items():
                merged[key] = deepcopy(value)
            merged["render_quality"] = "balanced"
            merged["ui_preview_mode"] = "lite"
            dirty = True
        if "update_check_mode" not in raw and "check_for_updates" in raw:
            merged["update_check_mode"] = (
                "off" if raw.get("check_for_updates") is False else "launch"
            )
            dirty = True
        if merged.get("view_mode") == "wrap":
            merged["view_mode"] = "infinite"
            dirty = True
        if merged.get("speed_min", 0) >= merged.get("speed_max", 1):
            merged["speed_min"] = deepcopy(DEFAULTS["speed_min"])
            merged["speed_max"] = deepcopy(DEFAULTS["speed_max"])
            dirty = True
        return dirty

    def _merge_loaded_config_unlocked(
        self, raw: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        merged, dirty = self._merge_raw_keys_unlocked(raw)
        dirty = self._migrate_legacy_config_keys_unlocked(merged, raw) or dirty
        return merged, dirty

    def _recover_invalid_config_unlocked(self, error: Exception) -> Dict[str, Any]:
        recovery_dir = self._path.parent / "recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        quarantined = recovery_dir / f"config.invalid-{timestamp}.json"
        try:
            self._path.replace(quarantined)
        except OSError as exc:
            raise OSError(
                f"Config is unreadable and could not be preserved for recovery: {exc}"
            ) from exc

        backup_dir = self._path.parent / "backups"
        for backup in sorted(backup_dir.glob("config_*.json"), reverse=True):
            try:
                raw = json.loads(backup.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    continue
                recovered, _dirty = self._merge_loaded_config_unlocked(raw)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                continue
            self._recovery_notice = (
                "Recovered settings from the newest valid backup after config.json "
                f"could not be read. The original was preserved as {quarantined.name}."
            )
            return recovered

        self._recovery_notice = (
            "Reset settings to defaults because config.json could not be read and no valid "
            f"backup was available. The original was preserved as {quarantined.name}. "
            f"Reason: {type(error).__name__}."
        )
        return deepcopy(DEFAULTS)

    @property
    def recovery_notice(self) -> Optional[str]:
        with self._lock:
            return self._recovery_notice

    @property
    def path(self) -> Path:
        return self._path

    def save(self) -> None:
        with self._lock:
            self._write_unlocked()

    def _commit_unlocked(self) -> Dict[str, Any]:
        """Persist the current state and return a snapshot. Caller must hold self._lock."""
        self._write_unlocked()
        return deepcopy(self._data)

    def _write_unlocked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_backups()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def _rotate_backups(self) -> None:
        if not self._data.get("backup_enabled", True):
            return
        if not self._path.is_file() or (time.monotonic() - self._last_backup_at) < 30.0:
            return
        backup_dir = self._path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"config_{timestamp}.json"
        shutil.copy2(str(self._path), str(backup_path))
        self._last_backup_at = time.monotonic()

        max_backups = int(self._data.get("backup_max_count", 10))
        backup_files = sorted(backup_dir.glob("config_*.json"), reverse=True)
        for old in backup_files[max_backups:]:
            old.unlink(missing_ok=True)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._data.get(key, default))

    def _apply_render_quality_preset_unlocked(
        self, candidate: Dict[str, Any], patch: Dict[str, Any]
    ) -> None:
        if "render_quality" not in patch:
            return
        qname = str(patch.get("render_quality") or "balanced")
        preset = QUALITY_PRESETS.get(qname)
        if not preset:
            return
        for k, v in preset.items():
            if k not in patch:
                candidate[k] = deepcopy(v)

    def _apply_motion_feel_preset_unlocked(
        self, candidate: Dict[str, Any], patch: Dict[str, Any]
    ) -> Dict[str, Any]:
        if "motion_feel" in patch:
            fname = str(patch.get("motion_feel") or "normal")
            feel = FEEL_PRESETS.get(fname) if fname != "custom" else None
            if feel:
                for k, v in feel.items():
                    if k not in patch:
                        candidate[k] = deepcopy(v)
        feel_keys = ("motion_scale", "motion_ease", "camera_lag")
        if any(k in patch for k in feel_keys) and "motion_feel" not in patch:
            patch = {**patch, "motion_feel": "custom"}
        return patch

    def _merge_patch_values_unlocked(
        self, candidate: Dict[str, Any], patch: Dict[str, Any]
    ) -> None:
        for key, value in patch.items():
            if key in ("click_colors", "click_show") and isinstance(value, dict):
                base = candidate.get(key) or {}
                if not isinstance(base, dict):
                    base = {}
                merged = deepcopy(base)
                merged.update(deepcopy(value))
                candidate[key] = merged
            elif key in DEFAULTS:
                candidate[key] = deepcopy(value)

    def update(self, patch: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
        if not isinstance(patch, dict):
            raise ValidationError("config patch must be an object")
        with self._lock:
            candidate = deepcopy(self._data)
            self._apply_render_quality_preset_unlocked(candidate, patch)
            patch = self._apply_motion_feel_preset_unlocked(candidate, patch)
            self._merge_patch_values_unlocked(candidate, patch)
            require_valid_config(candidate, strict=True)
            self._data = candidate
            if persist:
                self._write_unlocked()
            snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def user_assets_dir(self) -> Path:
        directory = self._path.parent / "assets"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def store_background_image(self, source: Path) -> str:
        """Validate and copy a selected image into Velo-managed storage."""
        path = Path(source)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ValueError(f"Could not read image: {exc}") from exc
        if size <= 0 or size > MAX_BACKGROUND_IMAGE_BYTES:
            raise ValueError("Image too large (max 2 MB)")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"Could not read image: {exc}") from exc
        with self._lock:
            return self._store_background_bytes_unlocked(raw)

    def store_background_data_url(self, value: str) -> str:
        with self._lock:
            return self._store_background_data_url_unlocked(value)

    def _store_background_data_url_unlocked(self, value: str) -> str:
        try:
            header, encoded = value.split(",", 1)
            if not header.startswith("data:image/") or ";base64" not in header:
                raise ValueError
            if len(encoded) > (MAX_BACKGROUND_IMAGE_BYTES * 4 // 3) + 16:
                raise ValueError
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid embedded background image") from exc
        return self._store_background_bytes_unlocked(raw)

    def _store_background_bytes_unlocked(self, raw: bytes) -> str:
        if not raw or len(raw) > MAX_BACKGROUND_IMAGE_BYTES:
            raise ValueError("Image too large (max 2 MB)")
        try:
            from PIL import Image

            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
                ext = _IMAGE_FORMATS.get(str(image.format or "").upper())
        except Exception as exc:
            raise ValueError("Unsupported or invalid image") from exc
        if not ext:
            raise ValueError("Supported image types: PNG, JPEG, GIF, WebP")
        digest = hashlib.sha256(raw).hexdigest()[:24]
        name = f"background-{digest}.{ext}"
        destination = self.user_assets_dir() / name
        if not destination.exists():
            tmp = destination.with_suffix(destination.suffix + ".tmp")
            tmp.write_bytes(raw)
            tmp.replace(destination)
        return f"/user-assets/{name}"

    def _load_user_preset_file_unlocked(self, path: Path) -> None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(raw, dict):
            return
        if isinstance(raw.get("settings"), dict):
            name = str(raw.get("name") or path.stem).strip()
            settings = raw["settings"]
        else:
            name = str(raw.get("name") or path.stem).strip()
            settings = {k: v for k, v in raw.items() if k != "name"}
        try:
            name = _sanitize_preset_name(name)
        except ValueError:
            return
        if not isinstance(settings, dict):
            return
        if name in self._user_presets:
            return
        clean = {
            k: deepcopy(v)
            for k, v in settings.items()
            if k in DEFAULTS and k not in PRESET_EXCLUDE
        }
        if validate_config(clean, strict=True):
            return
        self._user_presets[name] = clean
        self._user_preset_files[name] = path

    def _load_user_presets(self) -> None:
        with self._lock:
            self._user_presets = {}
            self._user_preset_files = {}
            self._presets_dir.mkdir(parents=True, exist_ok=True)
            self._migrate_legacy_user_presets_unlocked()
            for path in sorted(self._presets_dir.glob("*.json")):
                self._load_user_preset_file_unlocked(path)

    def _legacy_user_presets_file(self) -> Path:
        return self._path.parent / "user_presets.json"

    def _legacy_migration_candidates_unlocked(self) -> List[Path]:
        legacy = self._legacy_user_presets_file()
        candidates = [legacy]
        default_legacy = legacy_user_presets_path()
        if default_legacy.resolve() != legacy.resolve():
            try:
                if self._presets_dir.resolve() == presets_dir().resolve():
                    candidates.append(default_legacy)
            except OSError as exc:
                logger.debug("Could not resolve default presets dir: %s", exc)
        return candidates

    def _archive_legacy_file_unlocked(self, legacy_path: Path) -> None:
        try:
            bak = legacy_path.with_suffix(".json.bak")
            if not bak.exists():
                legacy_path.rename(bak)
        except OSError as exc:
            logger.debug("Could not archive legacy presets file %s: %s", legacy_path, exc)

    def _import_legacy_preset_entries_unlocked(self, raw: Dict[str, Any]) -> None:
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

    def _migrate_legacy_user_presets_unlocked(self) -> None:
        for legacy_path in self._legacy_migration_candidates_unlocked():
            if not legacy_path.is_file():
                continue
            if any(self._presets_dir.glob("*.json")):
                self._archive_legacy_file_unlocked(legacy_path)
                continue
            try:
                raw = json.loads(legacy_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(raw, dict):
                continue
            self._import_legacy_preset_entries_unlocked(raw)
            self._archive_legacy_file_unlocked(legacy_path)

    def _avoid_preset_name_collision_unlocked(self, name: str, path: Path) -> Path:
        """If path already holds a preset with a different name, pick a free sibling path."""
        if not path.exists():
            return path
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_name = str((existing or {}).get("name") or path.stem).strip()
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.debug("Could not inspect existing preset file %s: %s", path, exc)
            return path
        if not existing_name or existing_name == name:
            return path
        stem = _preset_stem(name)
        n = 2
        while True:
            candidate = self._presets_dir / f"{stem}_{n}.json"
            if not candidate.exists():
                return candidate
            n += 1

    def _write_preset_file_unlocked(self, name: str, settings: Dict[str, Any]) -> Path:
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        path = self._user_preset_files.get(name) or _preset_file_for_name(
            name, self._presets_dir
        )
        path = self._avoid_preset_name_collision_unlocked(name, path)

        payload = {
            "name": name,
            "settings": {
                k: deepcopy(v)
                for k, v in settings.items()
                if k in DEFAULTS and k not in PRESET_EXCLUDE
            },
        }
        require_valid_config(payload["settings"], strict=True)
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
        except OSError as exc:
            logger.debug("Could not delete preset file %s: %s", path, exc)

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

    def _resolve_preset_patch_unlocked(
        self, name: str, kind: Optional[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if kind in (None, "user") and name in self._user_presets:
            return deepcopy(self._user_presets[name]), "user"
        if kind in (None, "builtin") and name in PRESETS:
            return deepcopy(PRESETS[name]), "builtin"
        return None, None

    def apply_preset(self, name: str, kind: Optional[str] = None) -> Dict[str, Any]:
        name = str(name or "").strip()
        kind = (kind or "").strip().lower() or None
        with self._lock:
            if kind in (None, "user"):
                self._load_user_presets()
            patch, resolved = self._resolve_preset_patch_unlocked(name, kind)
            if patch is None:
                return self.snapshot()
            clean = {
                k: v for k, v in patch.items() if k in DEFAULTS and k not in PRESET_EXCLUDE
            }
            self._last_active = (self._data.get("active_preset", ""), self._data.get("active_preset_kind", "builtin"))
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
            self._last_active = (self._data.get("active_preset", ""), self._data.get("active_preset_kind", "builtin"))
            self._data["active_preset"] = name
            self._data["active_preset_kind"] = "user"
            snap = self._commit_unlocked()
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
                last_name, last_kind = self._last_active
                if last_kind == "user" and last_name and last_name in self._user_presets:
                    self._data["active_preset"] = last_name
                    self._data["active_preset_kind"] = "user"
                else:
                    self._data["active_preset"] = ""
                    self._data["active_preset_kind"] = "builtin"
                snap = self._commit_unlocked()
            else:
                snap = deepcopy(self._data)
        self._emit(snap)
        return snap

    def _replace_preset_file_unlocked(
        self,
        new_name: str,
        settings: Dict[str, Any],
        old_path: Optional[Path],
    ) -> None:
        self._write_preset_file_unlocked(new_name, settings)
        new_path = self._user_preset_files.get(new_name)
        if old_path is not None and (new_path is None or old_path.resolve() != new_path.resolve()):
            try:
                if old_path.is_file():
                    old_path.unlink()
            except OSError as exc:
                logger.debug("Could not remove old preset file %s: %s", old_path, exc)

    def _retarget_active_preset_unlocked(self, old_name: str, new_name: str) -> Dict[str, Any]:
        if (
            self._data.get("active_preset") == old_name
            and self._data.get("active_preset_kind") == "user"
        ):
            self._data["active_preset"] = new_name
            return self._commit_unlocked()
        return deepcopy(self._data)

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
            self._replace_preset_file_unlocked(new_name, settings, old_path)
            snap = self._retarget_active_preset_unlocked(old_name, new_name)
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
        return self.encode_preset_share_v2(name, kind)

    @staticmethod
    def _flatten_preset_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        for k, v in settings.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    flat[f"{k}|{sk}"] = sv
            else:
                flat[k] = v
        return flat

    @staticmethod
    def _is_default_share_value(key: str, value: Any, defaults: Dict[str, Any]) -> bool:
        if "|" in key:
            parent, sub = key.split("|", 1)
            default_parent = defaults.get(parent)
            return (
                isinstance(default_parent, dict)
                and sub in default_parent
                and value == default_parent[sub]
            )
        return key in defaults and value == defaults[key]

    @staticmethod
    def _share_alias_for_key(key: str) -> str:
        alias = SHARE_ALIASES.get(key)
        if alias is not None:
            return alias
        if "|" in key:
            parent, sub = key.split("|", 1)
            return f"{parent}.{sub}"
        return key

    def encode_preset_share_v2(self, name: str, kind: Optional[str] = None) -> str:
        """Encode a preset as a compact VELO2 share code.

        Builds a JSON object of alias:value pairs for keys that differ
        from defaults, then zlib-compresses and base64url-encodes it.
        """
        resolved, settings = self.get_preset_settings(name, kind)
        defaults = DEFAULTS
        obj: Dict[str, Any] = {"v": 1, "n": name}

        flat = self._flatten_preset_settings(settings)
        for key, value in flat.items():
            if key in PRESET_EXCLUDE or self._is_default_share_value(key, value, defaults):
                continue
            alias = self._share_alias_for_key(key)
            # Convert speed_stops to compact array format [[t, color], ...]
            if key == "speed_stops" and isinstance(value, list):
                value = [[s["t"], s["color"]] for s in value]
            obj[str(alias)] = value

        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(raw)
        payload = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
        return PRESET_CLIP_PREFIX_V2 + payload

    @staticmethod
    def _decode_share_v1_body(s: str, first: str) -> Any:
        if first.startswith(PRESET_CLIP_PREFIX) or s.startswith(PRESET_CLIP_PREFIX):
            blob = (
                first[len(PRESET_CLIP_PREFIX):].strip()
                if first.startswith(PRESET_CLIP_PREFIX)
                else s[len(PRESET_CLIP_PREFIX):].strip()
            )
            blob = "".join(blob.split())
            try:
                pad = "=" * (-len(blob) % 4)
                raw = _decompress_preset(base64.urlsafe_b64decode(blob + pad))
                return json.loads(raw.decode("utf-8"))
            except (ValueError, TypeError, zlib.error, json.JSONDecodeError, binascii.Error) as exc:
                raise ValueError("invalid preset code") from exc
        try:
            return json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid preset JSON") from exc

    @staticmethod
    def _extract_named_settings(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        name = str(data.get("name") or "Imported").strip()
        if data.get("type") == "preset" or "settings" in data:
            settings = data.get("settings")
            if not isinstance(settings, dict):
                raise ValueError("missing preset settings")
        else:
            settings = {k: v for k, v in data.items() if k != "name"}
        return name, settings

    def decode_preset_share(self, text: str) -> Dict[str, Any]:
        s = str(text or "").strip().strip("\ufeff")
        if not s:
            raise ValueError("empty preset data")
        first = s.splitlines()[0].strip()

        if first.startswith(PRESET_CLIP_PREFIX_V2):
            body = first[len(PRESET_CLIP_PREFIX_V2):].strip()
            if not body:
                raise ValueError("empty preset code")
            return self._decode_share_v2(body)

        data = self._decode_share_v1_body(s, first)
        if not isinstance(data, dict):
            raise ValueError("invalid preset data")
        name, settings = self._extract_named_settings(data)
        clean = {
            k: deepcopy(v)
            for k, v in settings.items()
            if k in DEFAULTS and k not in PRESET_EXCLUDE
        }
        if not clean:
            raise ValueError("no recognized preset settings")
        require_valid_config(clean, strict=True)
        try:
            name = _sanitize_preset_name(name)
        except ValueError:
            name = "Imported"
        return {"name": name, "settings": clean}

    @staticmethod
    def _apply_share_alias(settings: Dict[str, Any], alias: str, value: Any) -> None:
        full_key = REVERSE_SHARE_ALIASES.get(alias)
        if full_key is None:
            if "." in alias:
                full_key = alias
            else:
                return  # unknown alias, skip for forward compat

        # Reconstruct speed_stops from compact array format
        if full_key == "speed_stops" and isinstance(value, list):
            value = [{"t": s[0], "color": s[1]} for s in value]

        # Reconstruct nested dicts from flat keys
        if isinstance(full_key, str) and "|" in full_key:
            parent, sub = full_key.split("|", 1)
            settings.setdefault(parent, {})[sub] = value
        else:
            settings[full_key] = value

    @staticmethod
    def _fill_share_defaults(settings: Dict[str, Any]) -> None:
        for k, v in DEFAULTS.items():
            if k not in settings:
                if isinstance(v, dict):
                    merged = deepcopy(v)
                    if k in settings:
                        merged.update(settings[k])
                    settings[k] = merged
                else:
                    settings[k] = deepcopy(v)

    def _decode_share_v2(self, body: str) -> Dict[str, Any]:
        """Decode a compressed VELO2 share code into preset data."""
        try:
            padded = body + "=" * (-len(body) % 4)
            raw = _decompress_preset(base64.urlsafe_b64decode(padded))
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, TypeError, zlib.error, binascii.Error, json.JSONDecodeError) as exc:
            raise ValueError("invalid preset code") from exc

        if not isinstance(data, dict):
            raise ValueError("invalid preset data")

        settings: Dict[str, Any] = {}
        for alias, value in data.items():
            if alias == "v":
                continue  # schema version, not a config key
            self._apply_share_alias(settings, alias, value)

        self._fill_share_defaults(settings)

        if not settings:
            raise ValueError("no recognized preset settings")

        require_valid_config(settings, strict=True)

        preset_name = str(data.get("n", "Imported")).strip()
        if not preset_name:
            preset_name = "Imported"
        return {"name": preset_name, "settings": settings}

    @staticmethod
    def _extract_import_settings(
        data: Dict[str, Any], name: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        if "settings" in data and isinstance(data.get("settings"), dict):
            settings = data["settings"]
            base_name = str(data.get("name") or name or "Imported")
        else:
            settings = data
            base_name = str(name or "Imported")
        return base_name, settings

    def _dedupe_preset_name_unlocked(self, final_name: str, overwrite: bool) -> str:
        if overwrite or final_name not in self._user_presets:
            return final_name
        n = 2
        stem = final_name
        while f"{stem} {n}" in self._user_presets or f"{stem} {n}" in PRESETS:
            n += 1
            if n > 99:
                raise ValueError("preset already exists")
        return f"{stem} {n}"

    def import_preset_payload(
        self,
        data: Dict[str, Any],
        *,
        name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("invalid preset data")
        base_name, settings = self._extract_import_settings(data, name)
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
        require_valid_config(clean, strict=True)
        with self._lock:
            self._load_user_presets()
            final_name = self._dedupe_preset_name_unlocked(final_name, overwrite)
            candidate = deepcopy(self._data)
            candidate.update(deepcopy(clean))
            candidate["active_preset"] = final_name
            candidate["active_preset_kind"] = "user"
            require_valid_config(candidate, strict=True)
            self._write_preset_file_unlocked(final_name, clean)
            self._data = candidate
            snap = self._commit_unlocked()
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
            snap = self._commit_unlocked()
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
            snap = self._commit_unlocked()
        self._emit(snap)
        return snap

    def export_bundle(self, include_connection: bool = False) -> Dict[str, Any]:
        snap = self.snapshot()
        if not include_connection:
            for k in ("host", "port", "auth_token"):
                snap.pop(k, None)
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "config": snap,
        }

    @staticmethod
    def _filter_bundle_config(cfg: Dict[str, Any], include_connection: bool) -> Dict[str, Any]:
        patch: Dict[str, Any] = {}
        for k, v in cfg.items():
            if k not in DEFAULTS:
                continue
            if not include_connection and k in ("host", "port", "auth_token", "auth_enabled"):
                continue
            if k == "ui_obs_setup_done" and not include_connection:
                continue
            patch[k] = v
        return patch

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
        patch = self._filter_bundle_config(cfg, include_connection)
        if not patch:
            raise ValueError("no recognized settings in file")
        image_value = patch.get("pad_bg_image")
        if isinstance(image_value, str) and image_value.startswith("data:image/"):
            patch["pad_bg_image"] = self.store_background_data_url(image_value)
        require_valid_config(patch, strict=True)
        return self.update(patch, persist=True)

    def on_change(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners = [cb for cb in self._listeners if cb != callback]

    def _emit(self, snap: Dict[str, Any]) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(snap)
            except Exception:
                # Listeners (server/pipeline/shell) must not break config writes
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


def list_builtin_preset_names() -> List[str]:
    return list(PRESETS.keys())


def list_presets() -> List[str]:
    return list_builtin_preset_names()
