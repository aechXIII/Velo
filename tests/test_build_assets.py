"""Checks for files required by frozen web interfaces."""

from __future__ import annotations

import re
import runpy
from pathlib import Path
from types import SimpleNamespace

from PyInstaller.building.utils import format_binaries_and_datas

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "Velo.spec"
WEB_ASSET_DIRS = ("config_ui", "overlay")
RELATIVE_IMPORT = re.compile(r'\bfrom\s+["\'](\./[^"\']+)["\']')


def _spec_datas() -> list[tuple[str, str]]:
    captured: dict[str, list[tuple[str, str]]] = {}

    def analysis(*_args, **kwargs):
        captured["datas"] = kwargs["datas"]
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[], zipfiles=[])

    runpy.run_path(
        str(SPEC_PATH),
        init_globals={
            "Analysis": analysis,
            "PYZ": lambda *_args, **_kwargs: None,
            "EXE": lambda *_args, **_kwargs: None,
            "COLLECT": lambda *_args, **_kwargs: None,
        },
    )
    return captured["datas"]


def test_frozen_build_includes_relative_javascript_imports() -> None:
    packaged = {
        Path(target).as_posix()
        for target, _source in format_binaries_and_datas(
            _spec_datas(), workingdir=str(REPO_ROOT)
        )
    }
    required: set[str] = set()
    for asset_dir in WEB_ASSET_DIRS:
        for script in (REPO_ROOT / asset_dir).rglob("*.js"):
            for relative_import in RELATIVE_IMPORT.findall(
                script.read_text(encoding="utf-8")
            ):
                required.add(
                    (
                        Path(asset_dir)
                        / script.parent.relative_to(REPO_ROOT / asset_dir)
                        / relative_import
                    )
                    .resolve()
                    .relative_to(REPO_ROOT)
                    .as_posix()
                )

    assert required <= packaged, f"Missing packaged web assets: {required - packaged}"
