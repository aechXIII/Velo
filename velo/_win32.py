"""Win32 type definitions and helpers."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from velo.constants import MOUSE_MOVE_RELATIVE, RIDEV_INPUTSINK, WM_INPUT

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012

RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
RI_MOUSE_LEFT_BUTTON_UP = 0x0002
RI_MOUSE_RIGHT_BUTTON_DOWN = 0x0004
RI_MOUSE_RIGHT_BUTTON_UP = 0x0008
RI_MOUSE_MIDDLE_BUTTON_DOWN = 0x0010
RI_MOUSE_MIDDLE_BUTTON_UP = 0x0020
RI_MOUSE_BUTTON_4_DOWN = 0x0040
RI_MOUSE_BUTTON_4_UP = 0x0080
RI_MOUSE_BUTTON_5_DOWN = 0x0100
RI_MOUSE_BUTTON_5_UP = 0x0200
RI_MOUSE_WHEEL = 0x0400

WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
PM_REMOVE = 0x0001
ERROR_CLASS_ALREADY_EXISTS = 1410
CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002
TIMER_MODIFY_STATE = 0x0002
SYNCHRONIZE = 0x00100000
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0

LRESULT = ctypes.c_ssize_t
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
HBRUSH = getattr(wintypes, "HBRUSH", wintypes.HANDLE)
HICON = getattr(wintypes, "HICON", wintypes.HANDLE)
HINSTANCE = getattr(wintypes, "HINSTANCE", wintypes.HMODULE)


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWMOUSE(ctypes.Structure):
    """Must match MSVC layout: USHORT usFlags + 2-byte pad before the union."""

    class _Buttons(ctypes.Union):
        class _Named(ctypes.Structure):
            _fields_ = [
                ("usButtonFlags", wintypes.USHORT),
                ("usButtonData", wintypes.USHORT),
            ]

        _fields_ = [
            ("ulButtons", wintypes.ULONG),
            ("named", _Named),
        ]

    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("_padding", wintypes.USHORT),
        ("buttons", _Buttons),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWINPUT(ctypes.Structure):
    class _Data(ctypes.Union):
        _fields_ = [("mouse", RAWMOUSE)]

    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", _Data),
    ]


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


WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = LRESULT

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.RegisterRawInputDevices.argtypes = [
    ctypes.POINTER(RAWINPUTDEVICE),
    wintypes.UINT,
    wintypes.UINT,
]
user32.RegisterRawInputDevices.restype = wintypes.BOOL

user32.GetRawInputData.argtypes = [
    wintypes.HANDLE,
    wintypes.UINT,
    wintypes.LPVOID,
    ctypes.POINTER(wintypes.UINT),
    wintypes.UINT,
]
user32.GetRawInputData.restype = wintypes.UINT

user32.PeekMessageW.argtypes = [
    ctypes.POINTER(MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE

kernel32.GetCurrentThread.argtypes = []
kernel32.GetCurrentThread.restype = wintypes.HANDLE

kernel32.SetThreadPriority.argtypes = [wintypes.HANDLE, ctypes.c_int]
kernel32.SetThreadPriority.restype = wintypes.BOOL

kernel32.CreateWaitableTimerExW.argtypes = [
    wintypes.LPVOID,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.CreateWaitableTimerExW.restype = wintypes.HANDLE

kernel32.SetWaitableTimer.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_longlong),
    wintypes.LONG,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.BOOL,
]
kernel32.SetWaitableTimer.restype = wintypes.BOOL

kernel32.CreateEventW.argtypes = [
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
kernel32.CreateEventW.restype = wintypes.HANDLE

kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.SetEvent.restype = wintypes.BOOL

kernel32.WaitForMultipleObjects.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.BOOL,
    wintypes.DWORD,
]
kernel32.WaitForMultipleObjects.restype = wintypes.DWORD

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


class HighResolutionWaiter:
    """Interruptible Windows timer for sub-frame scheduling."""

    def __init__(self) -> None:
        access = TIMER_MODIFY_STATE | SYNCHRONIZE
        self._timer = kernel32.CreateWaitableTimerExW(
            None,
            None,
            CREATE_WAITABLE_TIMER_HIGH_RESOLUTION,
            access,
        )
        if not self._timer:
            self._timer = kernel32.CreateWaitableTimerExW(None, None, 0, access)
        if not self._timer:
            raise ctypes.WinError(ctypes.get_last_error())

        self._stop_event = kernel32.CreateEventW(None, True, False, None)
        if not self._stop_event:
            error = ctypes.WinError(ctypes.get_last_error())
            kernel32.CloseHandle(self._timer)
            self._timer = None
            raise error

        self._handles = (wintypes.HANDLE * 2)(self._stop_event, self._timer)

    def wait(self, delay_seconds: float) -> bool:
        """Wait for the delay, returning True if interrupted."""
        ticks = max(1, round(max(0.0, delay_seconds) * 10_000_000))
        due_time = ctypes.c_longlong(-ticks)
        if not kernel32.SetWaitableTimer(
            self._timer,
            ctypes.byref(due_time),
            0,
            None,
            None,
            False,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        result = kernel32.WaitForMultipleObjects(2, self._handles, False, INFINITE)
        if result == WAIT_OBJECT_0:
            return True
        if result == WAIT_OBJECT_0 + 1:
            return False
        raise ctypes.WinError(ctypes.get_last_error())

    def stop(self) -> None:
        if self._stop_event and not kernel32.SetEvent(self._stop_event):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self._stop_event:
            kernel32.CloseHandle(self._stop_event)
            self._stop_event = None
        if self._timer:
            kernel32.CloseHandle(self._timer)
            self._timer = None
