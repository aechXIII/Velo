from __future__ import annotations

import ctypes
import json
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from typing import Any, Optional

_MUTEX_NAME = "Local\\VeloSingleInstance"
_ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

_mutex_handle: Optional[wintypes.HANDLE] = None


def try_acquire() -> bool:
    global _mutex_handle
    if _mutex_handle:
        return True

    ctypes.set_last_error(0)
    handle = _kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if not handle:
        return True

    last = ctypes.get_last_error()
    if last == _ERROR_ALREADY_EXISTS:
        _kernel32.CloseHandle(handle)
        return False

    _mutex_handle = handle
    return True


def _api_origin(config: Any) -> str:
    host = str(config.get("host") or "127.0.0.1")
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    port = int(config.get("port") or 27180)
    return f"http://{host}:{port}"


def request_show_settings(config: Any, *, attempts: int = 12, delay_s: float = 0.12) -> bool:
    origin = _api_origin(config)
    url = origin + "/api/app/show"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    token = str(config.get("auth_token") or "")
    if config.get("auth_enabled") and token:
        headers["Authorization"] = "Bearer " + token

    body = json.dumps({"action": "show_settings"}).encode("utf-8")

    for _ in range(max(1, attempts)):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if 200 <= getattr(resp, "status", 200) < 300:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            pass
        time.sleep(delay_s)
    return False
