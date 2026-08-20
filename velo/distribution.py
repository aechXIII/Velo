"""Distribution-channel detection for installed and portable builds."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from velo.logging import get_logger

logger = get_logger()


def executable_root() -> Path:
    """Return the user-visible directory containing the Velo executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


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


def updates_managed_externally() -> bool:
    return distribution_channel() == "itch"


def autostart_supported() -> bool:
    """Portable itch installs must not leave registry state after removal."""
    return distribution_channel() != "itch"


def distribution_label() -> str:
    channel = distribution_channel()
    return {
        "itch": "itch.io",
        "standard": "Standard installer / portable",
        "development": "Development",
    }.get(channel, channel)
