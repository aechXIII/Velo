# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules("pystray")
hiddenimports += collect_submodules("webview")
hiddenimports += [
    "aiohttp",
    "multidict",
    "yarl",
    "frozenlist",
    "async_timeout",
    "attr",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("overlay/index.html", "overlay"),
        ("overlay/app.js", "overlay"),
        ("overlay/style.css", "overlay"),
        ("config_ui/index.html", "config_ui"),
        ("config_ui/app.js", "config_ui"),
        ("config_ui/style.css", "config_ui"),
        ("assets/velo.ico", "assets"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Velo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/velo.ico",
    version="build/version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Velo",
)
