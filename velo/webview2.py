"""Microsoft Edge WebView2 Runtime detection."""

from __future__ import annotations

import sys
from typing import Optional

WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
_CLIENT_KEY = (
    r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
)


def installed_version() -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:
        return None

    locations = (
        (winreg.HKEY_CURRENT_USER, 0),
        (winreg.HKEY_LOCAL_MACHINE, getattr(winreg, "KEY_WOW64_32KEY", 0)),
        (winreg.HKEY_LOCAL_MACHINE, getattr(winreg, "KEY_WOW64_64KEY", 0)),
    )
    for hive, view in locations:
        try:
            with winreg.OpenKey(hive, _CLIENT_KEY, 0, winreg.KEY_READ | view) as key:
                value, _kind = winreg.QueryValueEx(key, "pv")
        except OSError:
            continue
        version = str(value or "").strip()
        if version and version != "0.0.0.0":
            return version
    return None


def is_installed() -> bool:
    return installed_version() is not None
