"""Privacy-conscious diagnostics for support requests."""

from __future__ import annotations

import os
import platform
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from velo import __version__
from velo.config import config_dir
from velo.distribution import distribution_channel, distribution_label, executable_root
from velo.logging import log_dir
from velo.webview2 import installed_version

GITHUB_URL = "https://github.com/aechXIII/Velo"
ISSUES_URL = f"{GITHUB_URL}/issues/new/choose"


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    aliases = (
        ("%LOCALAPPDATA%", os.environ.get("LOCALAPPDATA")),
        ("%APPDATA%", os.environ.get("APPDATA")),
    )
    for label, raw_base in aliases:
        if not raw_base:
            continue
        try:
            relative = resolved.relative_to(Path(raw_base).resolve())
            return str(Path(label) / relative)
        except ValueError:
            continue
    return f"<custom>\\{resolved.name}"


def collect_diagnostics(
    *,
    server_status: Optional[Mapping[str, Any]] = None,
    capture_running: Optional[bool] = None,
    capture_error: Optional[str] = None,
    recovery_notice: Optional[str] = None,
) -> dict[str, Any]:
    win_version = platform.win32_ver()
    data: dict[str, Any] = {
        "velo_version": __version__,
        "distribution": distribution_channel(),
        "distribution_label": distribution_label(),
        "windows": " ".join(part for part in win_version if part).strip()
        or platform.platform(),
        "architecture": platform.machine() or "unknown",
        "python": platform.python_version(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "webview2": installed_version() or "not detected",
        "install_location": _display_path(executable_root()),
        "config_location": _display_path(config_dir()),
        "log_location": _display_path(log_dir()),
    }
    if server_status:
        data["server_running"] = bool(server_status.get("running"))
        data["server_clients"] = int(server_status.get("clients") or 0)
        data["server_error"] = str(server_status.get("error") or "")
    if capture_running is not None:
        data["capture_running"] = bool(capture_running)
    if capture_error:
        data["capture_error"] = str(capture_error)
    if recovery_notice:
        data["recovery_notice"] = str(recovery_notice)
    return data


def format_diagnostics(data: Mapping[str, Any]) -> str:
    labels = {
        "velo_version": "Velo",
        "distribution_label": "Distribution",
        "windows": "Windows",
        "architecture": "Architecture",
        "python": "Python runtime",
        "webview2": "WebView2",
        "frozen": "Packaged build",
        "install_location": "Install location",
        "config_location": "Config location",
        "log_location": "Log location",
        "server_running": "Server running",
        "server_clients": "OBS/browser clients",
        "server_error": "Server error",
        "capture_running": "Capture running",
        "capture_error": "Capture error",
        "recovery_notice": "Recovery",
    }
    order = tuple(labels)
    lines = ["Velo diagnostics", ""]
    for key in order:
        if key not in data or data[key] in (None, ""):
            continue
        value = data[key]
        if key == "velo_version":
            value = f"{value}"
        elif isinstance(value, bool):
            value = "yes" if value else "no"
        lines.append(f"{labels[key]}: {value}")
    lines.extend(("", "No authentication tokens, OBS URLs, or personal files are included."))
    return "\n".join(lines)


def open_folder(path: Path) -> None:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        raise RuntimeError("Opening folders is only supported on Windows")
    os.startfile(str(target))  # type: ignore[attr-defined]


def open_file(path: Path) -> None:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target.name}")
    if os.name != "nt":
        raise RuntimeError("Opening files is only supported on Windows")
    os.startfile(str(target))  # type: ignore[attr-defined]
