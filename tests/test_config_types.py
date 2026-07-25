"""Tests for velo.config_types."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any, Dict

from velo.config_types import ConfigMap, ConfigPatch, ConfigView


def test_config_map_is_dict_subtype():
    data: ConfigMap = {"host": "localhost"}
    assert isinstance(data, dict)


def test_config_view_is_mapping():
    data: ConfigView = {"host": "localhost"}
    assert isinstance(data, Mapping)


def test_config_patch_is_mutable_mapping():
    data: ConfigPatch = {"host": "localhost"}
    assert isinstance(data, MutableMapping)


def test_config_map_creation():
    data: ConfigMap = {"host": "localhost", "port": 8080}
    assert data["host"] == "localhost"
    assert data["port"] == 8080


def test_config_map_defaults():
    data: ConfigMap = {}
    assert isinstance(data, dict)
    assert len(data) == 0