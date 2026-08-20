"""Collect license files for dependencies embedded in the Windows build."""

from __future__ import annotations

import argparse
import re
import shutil
from importlib import metadata
from pathlib import Path

PACKAGES = (
    "aiohappyeyeballs",
    "aiohttp",
    "aiosignal",
    "async-timeout",
    "attrs",
    "bottle",
    "cffi",
    "clr-loader",
    "frozenlist",
    "idna",
    "multidict",
    "Pillow",
    "propcache",
    "proxy_tools",
    "pycparser",
    "pystray",
    "pythonnet",
    "pywebview",
    "pywin32",
    "six",
    "typing-extensions",
    "yarl",
)
LICENSE_NAMES = re.compile(r"^(license|copying|notice|copyright|authors)(\.|$)", re.IGNORECASE)


def _safe_reset(output: Path) -> None:
    root = Path.cwd().resolve()
    expected_parent = (root / "build").resolve()
    if output.parent != expected_parent or output.name != "third_party_licenses":
        raise ValueError(f"Refusing to replace unexpected output directory: {output}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)


def _collect_package_license(output: Path, requested_name: str) -> None:
    dist = metadata.distribution(requested_name)
    name = dist.metadata.get("Name", requested_name)
    version = dist.version
    package_dir = output / re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{name}-{version}")
    package_dir.mkdir()
    copied = 0
    for entry in dist.files or ():
        entry_path = Path(str(entry))
        if not LICENSE_NAMES.match(entry_path.name):
            continue
        source = Path(dist.locate_file(entry)).resolve()
        if not source.is_file():
            continue
        destination = package_dir / entry_path.name
        suffix = 2
        while destination.exists():
            destination = package_dir / f"{entry_path.stem}-{suffix}{entry_path.suffix}"
            suffix += 1
        shutil.copy2(source, destination)
        copied += 1

    summary = (
        f"Package: {name}\n"
        f"Version: {version}\n"
        f"License metadata: {dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See project metadata'}\n"
        f"Home page: {dist.metadata.get('Home-page') or dist.metadata.get('Project-URL') or 'See package index'}\n"
        f"License files copied: {copied}\n"
    )
    (package_dir / "PACKAGE.txt").write_text(summary, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="build/third_party_licenses")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    _safe_reset(output)

    for requested_name in PACKAGES:
        _collect_package_license(output, requested_name)

    print(f"Collected dependency notices in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
