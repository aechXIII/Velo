"""Global keyboard hotkeys (Windows low-level hook).

The WH_KEYBOARD_LL hook is installed only while a hotkey is bound.
"""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Callable, Optional, Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
HC_ACTION = 0

LLKHF_UP = 0x80

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_NAMES = {
    **{f"F{i}": 0x70 + i - 1 for i in range(1, 25)},
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
    **{str(i): 0x30 + i for i in range(10)},
    "SPACE": 0x20,
    "TAB": 0x09,
    "ESCAPE": 0x1B,
    "ESC": 0x1B,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "BACKSPACE": 0x08,
    "DELETE": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "PLUS": 0xBB,
    "MINUS": 0xBD,
    "OEM_PLUS": 0xBB,
    "OEM_MINUS": 0xBD,
}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelKeyboardProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
        ("lPrivate", wintypes.DWORD),
    ]


user32.GetMessageW.argtypes = [
    ctypes.POINTER(MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = ctypes.c_ssize_t
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostThreadMessageW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

WM_QUIT = 0x0012


def parse_hotkey(spec: str) -> Optional[Tuple[int, int, str]]:
    raw = " ".join(str(spec or "").strip().split())
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace("-", "+").split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    key = None
    for part in parts:
        u = part.upper()
        if u in ("CTRL", "CONTROL", "CTL"):
            mods |= MOD_CONTROL
        elif u in ("SHIFT", "SHFT"):
            mods |= MOD_SHIFT
        elif u in ("ALT", "MENU"):
            mods |= MOD_ALT
        elif u in ("WIN", "WINDOWS", "META", "SUPER"):
            mods |= MOD_WIN
        else:
            key = u
    if not key:
        return None
    vk = VK_NAMES.get(key)
    if vk is None and len(key) == 1:
        vk = VK_NAMES.get(key.upper())
    if vk is None:
        return None
    label_parts = []
    if mods & MOD_CONTROL:
        label_parts.append("Ctrl")
    if mods & MOD_SHIFT:
        label_parts.append("Shift")
    if mods & MOD_ALT:
        label_parts.append("Alt")
    if mods & MOD_WIN:
        label_parts.append("Win")
    if key.startswith("F") and key[1:].isdigit():
        label_parts.append(key)
    elif len(key) == 1:
        label_parts.append(key.upper())
    else:
        label_parts.append(key)
    pretty = {
        "ESCAPE": "Esc",
        "ESC": "Esc",
        "RETURN": "Enter",
        "ENTER": "Enter",
        "PAGEUP": "PageUp",
        "PAGEDOWN": "PageDown",
        "BACKSPACE": "Backspace",
        "DELETE": "Delete",
        "INSERT": "Insert",
        "SPACE": "Space",
        "PLUS": "Plus",
        "MINUS": "Minus",
        "OEM_PLUS": "Plus",
        "OEM_MINUS": "Minus",
        "UP": "Up",
        "DOWN": "Down",
        "LEFT": "Left",
        "RIGHT": "Right",
        "TAB": "Tab",
        "HOME": "Home",
        "END": "End",
    }
    if key in pretty:
        label_parts[-1] = pretty[key]
    return mods, int(vk), "+".join(label_parts)


def _down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class GlobalHotkeys:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._hook = None
        self._proc = None
        self._mods = 0
        self._vk = 0
        self._label = ""
        self._callback: Optional[Callable[[], None]] = None
        self._last_fire = 0.0
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def active(self) -> bool:
        """True when a hotkey is bound and the hook thread is running."""
        with self._lock:
            bound = bool(self._callback and self._vk)
        return bound and bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        """No-op. Hook installs only when set_hotkey() binds a key."""
        return

    def stop(self) -> None:
        self.clear()

    def clear(self) -> None:
        with self._lock:
            self._callback = None
            self._vk = 0
            self._mods = 0
            self._label = ""
        self._last_error = None
        self._teardown_hook()

    def set_hotkey(self, spec: str, callback: Callable[[], None]) -> Optional[str]:
        parsed = parse_hotkey(spec)
        if not parsed:
            self.clear()
            return None
        mods, vk, label = parsed
        with self._lock:
            self._mods = mods
            self._vk = vk
            self._label = label
            self._callback = callback
        self._last_error = None
        self._ensure_hook()
        if self._last_error:
            return None
        return label

    def _ensure_hook(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._loop, name="velo-hotkeys", daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def _teardown_hook(self) -> None:
        if not self._thread:
            return
        self._stop.set()
        tid = self._thread_id
        if tid:
            user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
        self._hook = None
        self._proc = None

    def _matches(self, vk_code: int) -> bool:
        with self._lock:
            want_mods = self._mods
            want_vk = self._vk
            cb = self._callback
        if not cb or not want_vk:
            return False
        if int(vk_code) != want_vk:
            return False
        ctrl = _down(VK_CONTROL)
        shift = _down(VK_SHIFT)
        alt = _down(VK_MENU)
        win = _down(VK_LWIN) or _down(VK_RWIN)
        have = 0
        if ctrl:
            have |= MOD_CONTROL
        if shift:
            have |= MOD_SHIFT
        if alt:
            have |= MOD_ALT
        if win:
            have |= MOD_WIN
        return have == want_mods

    def _on_key(self, vk_code: int) -> None:
        if not self._matches(vk_code):
            return
        now = time.perf_counter()
        if now - self._last_fire < 0.25:
            return
        self._last_fire = now
        with self._lock:
            cb = self._callback
        if not cb:
            return
        cb()

    def _loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        @LowLevelKeyboardProc
        def _proc(nCode, wParam, lParam):
            # Keep the hook callback minimal; never raise into the OS chain.
            if nCode == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                try:
                    kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if (kb.flags & LLKHF_UP) == 0:
                        self._on_key(kb.vkCode)
                except (ValueError, OSError, ctypes.ArgumentError):
                    pass
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        self._proc = _proc
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, hmod, 0)
        if not self._hook:
            self._last_error = f"SetWindowsHookEx failed ({ctypes.get_last_error()})"
            self._ready.set()
            return

        self._ready.set()
        msg = MSG()
        while not self._stop.is_set():
            got = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if got == 0 or got == -1:
                break
            if msg.message == WM_QUIT:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
