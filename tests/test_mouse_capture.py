"""Tests for mouse capture event data."""

from __future__ import annotations

from velo._win32 import MOUSE_MOVE_RELATIVE, RAWMOUSE
from velo.mouse_capture import MouseCapture


def test_relative_capture_preserves_counts_before_sensitivity():
    capture = MouseCapture()
    events = []
    capture.add_listener(events.append)
    capture.configure(sensitivity=2.5)
    mouse = RAWMOUSE()
    mouse.usFlags = MOUSE_MOVE_RELATIVE
    mouse.lLastX = 5
    mouse.lLastY = -2

    capture._handle_raw_mouse(mouse)

    assert len(events) == 1
    assert events[0].dx == 12.5
    assert events[0].dy == -5.0
    assert events[0].raw_dx == 5.0
    assert events[0].raw_dy == -2.0
