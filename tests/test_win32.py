"""Tests for Win32 helpers."""

from __future__ import annotations

from velo import _win32


def test_high_resolution_waiter_falls_back_to_compatible_timer(monkeypatch):
    requested_flags = []
    closed_handles = []

    def create_timer(_security, _name, flags, _access):
        requested_flags.append(flags)
        return None if flags == _win32.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION else 101

    monkeypatch.setattr(_win32.kernel32, "CreateWaitableTimerExW", create_timer)
    monkeypatch.setattr(_win32.kernel32, "CreateEventW", lambda *_args: 202)
    monkeypatch.setattr(
        _win32.kernel32,
        "CloseHandle",
        lambda handle: closed_handles.append(handle) or True,
    )

    waiter = _win32.HighResolutionWaiter()
    waiter.close()

    assert requested_flags == [_win32.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, 0]
    assert closed_handles == [202, 101]
