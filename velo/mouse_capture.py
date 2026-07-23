"""Windows mouse capture via Raw Input and cursor polling."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from velo._win32 import (
    ERROR_CLASS_ALREADY_EXISTS,
    MOUSE_MOVE_RELATIVE,
    MSG,
    PM_REMOVE,
    POINT,
    RAWINPUT,
    RAWINPUTDEVICE,
    RAWINPUTHEADER,
    RAWMOUSE,
    RID_INPUT,
    RIDEV_INPUTSINK,
    RIM_TYPEMOUSE,
    RI_MOUSE_BUTTON_4_DOWN,
    RI_MOUSE_BUTTON_4_UP,
    RI_MOUSE_BUTTON_5_DOWN,
    RI_MOUSE_BUTTON_5_UP,
    RI_MOUSE_LEFT_BUTTON_DOWN,
    RI_MOUSE_LEFT_BUTTON_UP,
    RI_MOUSE_MIDDLE_BUTTON_DOWN,
    RI_MOUSE_MIDDLE_BUTTON_UP,
    RI_MOUSE_RIGHT_BUTTON_DOWN,
    RI_MOUSE_RIGHT_BUTTON_UP,
    RI_MOUSE_WHEEL,
    WM_CLOSE,
    WM_DESTROY,
    WM_INPUT,
    WM_QUIT,
    WNDCLASSW,
    WNDPROC,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_POPUP,
    kernel32,
    user32,
)


@dataclass
class MouseEvent:
    t: float
    dx: float = 0.0
    dy: float = 0.0
    x: Optional[float] = None
    y: Optional[float] = None
    buttons: Optional[Dict[str, bool]] = None
    wheel: float = 0.0
    button_event: Optional[str] = None
    source: str = "raw"


Listener = Callable[[MouseEvent], None]


class MouseCapture:
    def __init__(self) -> None:
        self._listeners: List[Listener] = []
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._hwnd: Optional[int] = None
        self._wndproc: Optional[WNDPROC] = None
        self._buttons: Dict[str, bool] = {
            "left": False,
            "right": False,
            "middle": False,
            "x1": False,
            "x2": False,
        }
        self._mode = "relative"
        self._invert_y = False
        self._sensitivity = 1.0
        self._abs_thread: Optional[threading.Thread] = None
        self._last_abs: Optional[Tuple[float, float]] = None
        self._lock = threading.Lock()
        self._running = False
        self._last_error: Optional[str] = None
        self._raw_count = 0

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def raw_event_count(self) -> int:
        return self._raw_count

    def add_listener(self, cb: Listener) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: Listener) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)

    def configure(
        self,
        mode: str = "relative",
        invert_y: bool = False,
        sensitivity: float = 1.0,
    ) -> None:
        with self._lock:
            self._mode = mode if mode in ("relative", "absolute") else "relative"
            self._invert_y = bool(invert_y)
            self._sensitivity = float(sensitivity) if sensitivity else 1.0
            if self._mode != "absolute":
                self._last_abs = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._last_error = None
        self._raw_count = 0
        self._thread = threading.Thread(
            target=self._raw_message_loop, name="velo-rawinput", daemon=True
        )
        self._thread.start()
        self._abs_thread = threading.Thread(
            target=self._absolute_poll_loop, name="velo-abs-cursor", daemon=True
        )
        self._abs_thread.start()
        for _ in range(50):
            if self._hwnd or self._last_error:
                break
            time.sleep(0.02)
        self._running = self._hwnd is not None and not self._last_error

    def stop(self) -> None:
        self._stop.set()
        self._running = False
        hwnd = self._hwnd
        if hwnd:
            user32.PostMessageW(wintypes.HWND(hwnd), WM_CLOSE, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.5)
        if self._abs_thread and self._abs_thread.is_alive():
            self._abs_thread.join(timeout=1.0)
        self._thread = None
        self._abs_thread = None
        self._hwnd = None
        self._wndproc = None

    def _emit(self, event: MouseEvent) -> None:
        for cb in list(self._listeners):
            try:
                cb(event)
            except Exception:
                # One bad listener must not stop capture delivery.
                continue

    def _apply_transform(self, dx: float, dy: float) -> Tuple[float, float]:
        with self._lock:
            sens = self._sensitivity
            inv = self._invert_y
        dx *= sens
        dy *= sens
        if inv:
            dy = -dy
        return dx, dy

    def _handle_raw_mouse(self, mouse: RAWMOUSE) -> None:
        self._raw_count += 1
        now = time.perf_counter()
        flags = mouse.usFlags
        btn_flags = mouse.buttons.named.usButtonFlags
        btn_data = mouse.buttons.named.usButtonData

        button_event = None
        mapping = [
            (RI_MOUSE_LEFT_BUTTON_DOWN, "left", True, "left_down"),
            (RI_MOUSE_LEFT_BUTTON_UP, "left", False, "left_up"),
            (RI_MOUSE_RIGHT_BUTTON_DOWN, "right", True, "right_down"),
            (RI_MOUSE_RIGHT_BUTTON_UP, "right", False, "right_up"),
            (RI_MOUSE_MIDDLE_BUTTON_DOWN, "middle", True, "middle_down"),
            (RI_MOUSE_MIDDLE_BUTTON_UP, "middle", False, "middle_up"),
            (RI_MOUSE_BUTTON_4_DOWN, "x1", True, "x1_down"),
            (RI_MOUSE_BUTTON_4_UP, "x1", False, "x1_up"),
            (RI_MOUSE_BUTTON_5_DOWN, "x2", True, "x2_down"),
            (RI_MOUSE_BUTTON_5_UP, "x2", False, "x2_up"),
        ]
        for mask, name, pressed, ev_name in mapping:
            if btn_flags & mask:
                self._buttons[name] = pressed
                button_event = ev_name

        wheel = 0.0
        if btn_flags & RI_MOUSE_WHEEL:
            wheel = ctypes.c_short(btn_data).value / 120.0

        dx = float(mouse.lLastX)
        dy = float(mouse.lLastY)
        is_relative = (flags & 0x01) == MOUSE_MOVE_RELATIVE

        with self._lock:
            mode = self._mode

        if mode == "relative" and is_relative and (dx != 0.0 or dy != 0.0):
            tdx, tdy = self._apply_transform(dx, dy)
            self._emit(
                MouseEvent(
                    t=now,
                    dx=tdx,
                    dy=tdy,
                    buttons=dict(self._buttons),
                    wheel=wheel,
                    button_event=button_event,
                    source="raw",
                )
            )
        elif button_event or wheel:
            self._emit(
                MouseEvent(
                    t=now,
                    dx=0.0,
                    dy=0.0,
                    buttons=dict(self._buttons),
                    wheel=wheel,
                    button_event=button_event,
                    source="raw",
                )
            )

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            self._process_wm_input(lparam)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _process_wm_input(self, lparam) -> None:
        size = wintypes.UINT(0)
        hraw = wintypes.HANDLE(lparam)
        header_size = ctypes.sizeof(RAWINPUTHEADER)

        user32.GetRawInputData(
            hraw,
            RID_INPUT,
            None,
            ctypes.byref(size),
            header_size,
        )
        if size.value == 0:
            return

        buf = ctypes.create_string_buffer(size.value)
        got = user32.GetRawInputData(
            hraw,
            RID_INPUT,
            buf,
            ctypes.byref(size),
            header_size,
        )
        if got == 0xFFFFFFFF or got == 0:
            return

        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        if raw.header.dwType != RIM_TYPEMOUSE:
            return
        self._handle_raw_mouse(raw.data.mouse)

    def _raw_message_loop(self) -> None:
        try:
            kernel32.SetThreadPriority(kernel32.GetCurrentThread(), 2)
        except Exception:
            pass

        class_name = "VeloRawInputSink_v1"
        hinstance = kernel32.GetModuleHandleW(None)
        self._wndproc = WNDPROC(self._wnd_proc)

        wc = WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = self._wndproc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = class_name

        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            err = ctypes.get_last_error()
            if err != ERROR_CLASS_ALREADY_EXISTS:
                self._last_error = f"RegisterClassW failed ({err})"
                return

        hwnd = user32.CreateWindowExW(
            WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
            class_name,
            "VeloRawInput",
            WS_POPUP,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            self._last_error = f"CreateWindowExW failed ({ctypes.get_last_error()})"
            return

        self._hwnd = int(hwnd) if hwnd else None

        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01
        rid.usUsage = 0x02
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = hwnd

        if not user32.RegisterRawInputDevices(
            ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE)
        ):
            self._last_error = (
                f"RegisterRawInputDevices failed ({ctypes.get_last_error()})"
            )
            user32.DestroyWindow(hwnd)
            self._hwnd = None
            return

        msg = MSG()
        while not self._stop.is_set():
            processed = False
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                processed = True
                if msg.message == WM_QUIT:
                    self._hwnd = None
                    return
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if not processed:
                time.sleep(0.0005)

        if self._hwnd:
            try:
                user32.DestroyWindow(wintypes.HWND(self._hwnd))
            except Exception:
                pass
            self._hwnd = None

    def _absolute_poll_loop(self) -> None:
        pt = POINT()
        while not self._stop.is_set():
            with self._lock:
                mode = self._mode
            if mode != "absolute":
                time.sleep(0.05)
                continue

            if user32.GetCursorPos(ctypes.byref(pt)):
                now = time.perf_counter()
                x, y = float(pt.x), float(pt.y)
                dx = dy = 0.0
                first = self._last_abs is None
                if not first:
                    lx, ly = self._last_abs  # type: ignore[misc]
                    raw_dx, raw_dy = x - lx, y - ly
                    if raw_dx == 0 and raw_dy == 0:
                        time.sleep(1.0 / 250.0)
                        continue
                    dx, dy = self._apply_transform(raw_dx, raw_dy)
                self._last_abs = (x, y)
                self._emit(
                    MouseEvent(
                        t=now,
                        dx=dx,
                        dy=dy,
                        x=x,
                        y=y,
                        buttons=dict(self._buttons),
                        source="absolute",
                    )
                )
            time.sleep(1.0 / 250.0)
