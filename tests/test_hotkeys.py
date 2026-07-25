"""Tests for velo.hotkeys."""

from __future__ import annotations

import pytest

from velo.hotkeys import parse_hotkey


def test_parse_hotkey_simple_key():
    result = parse_hotkey("A")
    assert result is not None
    mods, vk, label = result
    assert mods == 0
    assert label == "A"


def test_parse_hotkey_with_modifiers():
    result = parse_hotkey("Ctrl+Shift+A")
    assert result is not None
    mods, vk, label = result
    assert mods & 0x0002  # MOD_CONTROL
    assert mods & 0x0004  # MOD_SHIFT
    assert "Ctrl" in label
    assert "Shift" in label


def test_parse_hotkey_ctrl_alt():
    result = parse_hotkey("Ctrl+Alt+F5")
    assert result is not None
    mods, vk, label = result
    assert mods & 0x0002  # MOD_CONTROL
    assert mods & 0x0001  # MOD_ALT
    assert "Ctrl" in label
    assert "Alt" in label
    assert "F5" in label


def test_parse_hotkey_win_key():
    result = parse_hotkey("Win+D")
    assert result is not None
    mods, vk, label = result
    assert mods & 0x0008  # MOD_WIN
    assert "Win" in label


def test_parse_hotkey_empty_string():
    assert parse_hotkey("") is None
    assert parse_hotkey("   ") is None


def test_parse_hotkey_invalid_key():
    assert parse_hotkey("Ctrl+InvalidKey") is None


def test_parse_hotkey_special_keys():
    tests = [
        ("SPACE", "Space"),
        ("ESCAPE", "Esc"),
        ("ENTER", "Enter"),
        ("TAB", "Tab"),
        ("DELETE", "Delete"),
        ("HOME", "Home"),
        ("END", "End"),
        ("PAGEUP", "PageUp"),
        ("PAGEDOWN", "PageDown"),
        ("UP", "Up"),
        ("DOWN", "Down"),
        ("LEFT", "Left"),
        ("RIGHT", "Right"),
    ]
    for spec, expected_label in tests:
        result = parse_hotkey(spec)
        assert result is not None, f"Failed to parse: {spec}"
        mods, vk, label = result
        assert label == expected_label, f"Expected {expected_label}, got {label}"


def test_parse_hotkey_dash_separator():
    result = parse_hotkey("Ctrl-Shift-A")
    assert result is not None
    mods, vk, label = result
    assert "Ctrl" in label
    assert "Shift" in label


def test_parse_hotkey_numeric():
    result = parse_hotkey("Ctrl+1")
    assert result is not None
    mods, vk, label = result
    assert "Ctrl" in label
    assert "1" in label


def test_parse_hotkey_function_keys():
    for i in range(1, 13):
        result = parse_hotkey(f"F{i}")
        assert result is not None, f"Failed to parse F{i}"
        mods, vk, label = result
        assert f"F{i}" in label


def test_parse_hotkey_none_input():
    assert parse_hotkey(None) is None  # type: ignore[arg-type]