"""Generate the Windows version resource consumed by PyInstaller."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_version() -> str:
    source = (REPO_ROOT / "velo" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', source, re.MULTILINE)
    if not match:
        raise ValueError("Could not read Velo version")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="build/version_info.txt")
    args = parser.parse_args()

    version = _read_version()
    parts = [int(part) for part in version.split(".")]
    if len(parts) != 3:
        raise ValueError(f"Expected a semantic version, got {version!r}")
    version_tuple = tuple(parts + [0])
    dotted_version = f"{version}.0"
    output = (REPO_ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple!r},
    prodvers={version_tuple!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'aechXIII'),
          StringStruct('FileDescription', 'Velo mouse input overlay for OBS'),
          StringStruct('FileVersion', '{dotted_version}'),
          StringStruct('InternalName', 'Velo'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 aechXIII'),
          StringStruct('OriginalFilename', 'Velo.exe'),
          StringStruct('ProductName', 'Velo'),
          StringStruct('ProductVersion', '{dotted_version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    print(f"Generated {output} for Velo {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
