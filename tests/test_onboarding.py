"""Tests for onboarding wizard."""

from __future__ import annotations

from velo.defaults import DEFAULTS


def test_defaults_has_show_onboarding():
    assert "show_onboarding" in DEFAULTS
    assert DEFAULTS["show_onboarding"] is True