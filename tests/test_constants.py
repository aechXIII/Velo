"""Tests for velo.constants."""

from __future__ import annotations

import velo.constants as c


def _public_names():
    return [n for n in dir(c) if n.isupper() and not n.startswith("_")]


def test_all_constants_are_positive_numbers_or_nonempty_strings():
    for name in _public_names():
        value = getattr(c, name)
        if isinstance(value, (int, float)):
            assert value >= 0, f"{name} should be non-negative, got {value}"
        elif isinstance(value, str):
            assert len(value) > 0, f"{name} should be non-empty"


def test_hex_constants_are_valid():
    hex_names = [
        "MOUSE_MOVE_RELATIVE",
        "MOUSE_MOVE_ABSOLUTE",
        "MOUSE_VIRTUAL_DESKTOP",
        "MOUSE_ATTRIBUTES_CHANGED",
        "MOUSE_MOVE_NOCOALESCE",
        "WM_INPUT",
        "RIDEV_INPUTSINK",
        "RIDEV_CAPTUREMOUSE",
        "WM_KEYDOWN",
        "WM_SYSKEYDOWN",
    ]
    for name in hex_names:
        value = getattr(c, name)
        assert isinstance(value, int), f"{name} should be int, got {type(value)}"
        assert value >= 0, f"{name} should be non-negative"


def test_smoothing_weights_sum_to_one():
    assert abs(c.SMOOTHING_WEIGHT_NEW + c.SMOOTHING_WEIGHT_OLD - 1.0) < 1e-9


def test_github_api_url_format():
    assert c.GITHUB_API_URL.startswith("https://api.github.com/repos/")
    assert "/releases" in c.GITHUB_API_URL


def test_default_port_is_positive():
    assert c.DEFAULT_PORT > 0
    assert c.DEFAULT_PORT < 65536


def test_max_message_size_is_power_of_two():
    assert c.MAX_MESSAGE_SIZE > 0
    assert (c.MAX_MESSAGE_SIZE & (c.MAX_MESSAGE_SIZE - 1)) == 0