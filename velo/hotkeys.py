"""Global keyboard hotkeys (Windows low-level hook).

The WH_KEYBOARD_LL hook is installed only while a hotkey is bound.
"""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Callable, Dict, Optional, Tuple

from velo.constants import HC_ACTION, HOTKEY_DEBOUNCE, WH_KEYBOARD_LL, WM_KEYDOWN, WM_SYSKEYDOWN
from velo.logging import get_logger

logger = get_logger()

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105

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


_MOD_ALIASES = {
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "CTL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "SHFT": MOD_SHIFT,
    "ALT": MOD_ALT,
    "MENU": MOD_ALT,
    "WIN": MOD_WIN,
    "WINDOWS": MOD_WIN,
    "META": MOD_WIN,
    "SUPER": MOD_WIN,
}

_PRETTY_KEY_NAMES = {
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


def _split_hotkey_mods_and_key(parts: list[str]) -> Tuple[int, Optional[str]]:
    mods = 0
    key = None
    for part in parts:
        u = part.upper()
        mod = _MOD_ALIASES.get(u)
        if mod is not None:
            mods |= mod
        else:
            key = u
    return mods, key


def _hotkey_label(mods: int, key: str) -> str:
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
    if key in _PRETTY_KEY_NAMES:
        label_parts[-1] = _PRETTY_KEY_NAMES[key]
    return "+".join(label_parts)


def parse_hotkey(spec: str) -> Optional[Tuple[int, int, str]]:
    raw = " ".join(str(spec or "").strip().split())
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace("-", "+").split("+") if p.strip()]
    if not parts:
        return None
    mods, key = _split_hotkey_mods_and_key(parts)
    if not key:
        return None
    vk = VK_NAMES.get(key)
    if vk is None and len(key) == 1:
        vk = VK_NAMES.get(key.upper())
    if vk is None:
        return None
    return mods, int(vk), _hotkey_label(mods, key)


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
        # single key (compat)
        self._mods = 0
        self._vk = 0
        self._label = ""
        self._callback: Optional[Callable[[], None]] = None
        # multiple bindings: spec -> (mods, vk, label, callback)
        self._bindings: Dict[str, Tuple[int, int, str, Callable[[], None]]] = {}
        self._last_fire = 0.0
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def active(self) -> bool:
        with self._lock:
            bound = bool(self._callback and self._vk) or bool(self._bindings)
        return bound and bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        # No-op: the OS hook is installed lazily by _ensure_hook() once a
        # hotkey is actually bound. This exists only so callers can treat
        # GlobalHotkeys like other start/stop-managed services.
        return

    def stop(self) -> None:
        self.clear()

    def clear(self) -> None:
        with self._lock:
            self._callback = None
            self._vk = 0
            self._mods = 0
            self._label = ""
            self._bindings.clear()
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

    def add_binding(self, spec: str, callback: Callable[[], None]) -> Optional[str]:
        parsed = parse_hotkey(spec)
        if not parsed:
            return None
        mods, vk, label = parsed
        with self._lock:
            self._bindings[spec] = (mods, vk, label, callback)
        self._last_error = None
        self._ensure_hook()
        if self._last_error:
            return None
        return label

    def replace_bindings(
        self,
        single_spec: str,
        single_callback: Callable[[], None],
        bindings: list[tuple[str, Callable[[], None]]],
    ) -> tuple[Optional[str], int]:
        """Atomically replace all bindings without cycling the OS hook unnecessarily."""
        single = parse_hotkey(single_spec)
        parsed_bindings: Dict[str, Tuple[int, int, str, Callable[[], None]]] = {}
        for spec, callback in bindings:
            parsed = parse_hotkey(spec)
            if not parsed:
                continue
            mods, vk, label = parsed
            parsed_bindings[label.casefold()] = (mods, vk, label, callback)

        with self._lock:
            if single:
                self._mods, self._vk, self._label = single
                self._callback = single_callback
            else:
                self._mods = 0
                self._vk = 0
                self._label = ""
                self._callback = None
            self._bindings = parsed_bindings
            active = bool(self._callback and self._vk) or bool(self._bindings)

        self._last_error = None
        if active:
            self._ensure_hook()
        else:
            self._teardown_hook()
        label = single[2] if single else None
        return label, len(parsed_bindings)

    def remove_binding(self, spec: str) -> None:
        with self._lock:
            self._bindings.pop(spec, None)
        if not self._bindings and not (self._callback and self._vk):
            self._teardown_hook()

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
        now = time.perf_counter()
        if now - self._last_fire < HOTKEY_DEBOUNCE:
            return False
        # check multiple bindings first
        with self._lock:
            bindings = dict(self._bindings)
        for _spec, (mods, vk, _label, _cb) in bindings.items():
            if int(vk_code) == vk and self._mods_match(mods):
                return True
        # check single binding (compat)
        with self._lock:
            want_mods = self._mods
            want_vk = self._vk
            cb = self._callback
        if not cb or not want_vk:
            return False
        if int(vk_code) != want_vk:
            return False
        return self._mods_match(want_mods)

    def _mods_match(self, want_mods: int) -> bool:
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
        self._last_fire = now
        # fire matching bindings + single callback
        with self._lock:
            bindings = dict(self._bindings)
            single_cb = self._callback
            single_vk = self._vk
        for _spec, (mods, vk, _label, cb) in bindings.items():
            if int(vk_code) == vk and self._mods_match(mods):
                self._dispatch(cb)
                return
        if single_cb and single_vk and int(vk_code) == single_vk:
            self._dispatch(single_cb)

    @staticmethod
    def _dispatch(callback: Callable[[], None]) -> None:
        def _run() -> None:
            try:
                callback()
            except Exception as exc:
                logger.debug("Hotkey callback failed: %s", exc)

        threading.Thread(target=_run, name="velo-hotkey-action", daemon=True).start()

    def _make_hook_proc(self) -> LowLevelKeyboardProc:
        @LowLevelKeyboardProc
        def _proc(nCode, wParam, lParam):
            # Keep the hook callback minimal; never raise into the OS chain
            if nCode == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                try:
                    kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if (kb.flags & LLKHF_UP) == 0:
                        self._on_key(kb.vkCode)
                except (ValueError, OSError, ctypes.ArgumentError) as exc:
                    logger.debug("Keyboard hook callback error: %s", exc)
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        return _proc

    def _pump_messages(self) -> None:
        msg = MSG()
        while not self._stop.is_set():
            got = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if got == 0 or got == -1:
                break
            if msg.message == WM_QUIT:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        self._proc = self._make_hook_proc()
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, hmod, 0)
        if not self._hook:
            self._last_error = f"SetWindowsHookEx failed ({ctypes.get_last_error()})"
            self._ready.set()
            return

        self._ready.set()
        self._pump_messages()

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
