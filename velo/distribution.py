"""Distribution-channel detection for installed and portable builds."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from velo.logging import get_logger

logger = get_logger()

_SETTINGS_RUNTIME_ASSEMBLIES = (
    Path("_internal/pythonnet/runtime/Python.Runtime.dll"),
    Path("_internal/webview/lib/Microsoft.Web.WebView2.Core.dll"),
    Path("_internal/webview/lib/Microsoft.Web.WebView2.WinForms.dll"),
)


def executable_root() -> Path:
    """Return the user-visible directory containing the Velo executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def unblock_packaged_settings_runtime(root: Path | None = None) -> None:
    """Allow trusted bundled .NET assemblies to load after a ZIP download."""
    if sys.platform != "win32":
        return
    if root is None:
        if not getattr(sys, "frozen", False):
            return
        root = executable_root()

    for relative_path in _SETTINGS_RUNTIME_ASSEMBLIES:
        assembly = root / relative_path
        try:
            Path(f"{assembly}:Zone.Identifier").unlink()
        except FileNotFoundError:
            pass


def distribution_channel() -> str:
    """Return ``itch``, ``standard``, or ``development``."""
    override = str(os.environ.get("VELO_DISTRIBUTION") or "").strip().lower()
    if override in {"itch", "standard", "development"}:
        return override

    root = executable_root()
    marker = root / "distribution.json"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        channel = str(data.get("channel") or "").strip().lower()
        if channel in {"itch", "standard"}:
            return channel
    except (OSError, ValueError, TypeError) as exc:
        logger.debug("Could not read distribution marker %s: %s", marker, exc)

    if (root / ".itch.toml").is_file():
        return "itch"
    return "standard" if getattr(sys, "frozen", False) else "development"


def launched_by_itch_app() -> bool:
    """Return whether the itch desktop app launched this process."""
    return "--itch-app" in sys.argv[1:]


def updates_managed_externally() -> bool:
    return distribution_channel() == "itch" and launched_by_itch_app()


def autostart_supported() -> bool:
    """The itch app owns startup behavior for processes it launches."""
    return not updates_managed_externally()


def distribution_label() -> str:
    channel = distribution_channel()
    return {
        "itch": "itch.io",
        "standard": "Standard installer / portable",
        "development": "Development",
    }.get(channel, channel)
