# Velo

Mouse Input overlay for OBS. Made for aim trainers and FPS games.

[![Release](https://img.shields.io/github/v/release/aechXIII/Velo?style=flat-square&color=3B6AD8)](https://github.com/aechXIII/Velo/releases) [![License: GPL v3+](https://img.shields.io/badge/license-GPLv3%2B-blue?style=flat-square)](LICENSE) [![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-lightgrey?style=flat-square)]() [![Buy Me a Coffee](https://img.shields.io/badge/support-Buy%20Me%20a%20Coffee-F5A623?style=flat-square&logo=buy-me-a-coffee)](https://buymeacoffee.com/aechxiii)

---

## Demo

| | |
|---|---|
| ![Demo](docs/screenshots/demo.gif) | ![Velo](docs/screenshots/velo.gif) |

![Trail](docs/screenshots/trail.png)

<details>
<summary>More screenshots</summary>

![Settings](docs/screenshots/settings.png)

![Presets](docs/screenshots/presets.png)

![Size](docs/screenshots/size.png)

![Background](docs/screenshots/background.png)

![Motion](docs/screenshots/motion.png)

![Trail](docs/screenshots/trail.png)

![Cursor](docs/screenshots/cursor.png)

![HUD](docs/screenshots/hud.png)

![Performance](docs/screenshots/performance.png)

![OBS](docs/screenshots/obs.png)

</details>

---

## Features

**Overlay**
- Speed-colored or solid mouse trails with glow, curve smoothing, and fade modes
- Configurable background (fill, border, grid, vignette, shadow)
- Per-button click indicators (ring, fill, double, cross)
- Cursor dot with show/hide and expand-on-click
- Full Canvas rendering with live preview in settings

**Presets**
- 6 built-in presets (removable)
- Save, rename, duplicate, and delete your own presets
- Share codes to send presets to anyone
- Import from file or paste a code

**HUD**
- Real-time speed, peak speed, distance, clicks, and CPS
- DPI-aware metric
- Configurable update rate

**Motion**
- Three feel presets (Tight, Normal, Soft) plus custom sliders
- Sensitivity and view zoom controls
- Camera lag, look-ahead, and follow
- Infinite pan or fixed pad view modes

**Settings UI**
- Search bar to instantly find any setting
- Undo/redo for config changes
- Customizable accent color and background color
- Onboarding wizard for first-time setup

**System**
- Low-level Raw Input capture for games
- System tray with quick actions
- In-app update checker with one-click install
- Autostart with Windows, start minimized
- Single instance- launching again opens the settings window

---

## Install

1. Download the setup from [Releases](https://github.com/aechXIII/Velo/releases)
2. Run it (no admin needed)
3. Installs to `%LOCALAPPDATA%\Velo`

Config and presets live in `%APPDATA%\Velo` and survive updates.

Requires Windows 10 or 11 (64-bit) and [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) (already included on Windows 11).

---

## OBS setup

1. Start Velo
2. Open Settings → OBS and copy the URL
3. In OBS: add a Browser source and paste the URL
4. Set the browser width/height to match what you have under Size (or use Copy size)
5. Uncheck "Shutdown source when not visible"
6. Leave the background transparent

Common sizes: 480×480 or 640×360 for a corner pad.

Set the settings preview to Off or Lite while streaming or recording if you want to save CPU.

---

## Config paths

| | |
|---|---|
| Config | `%APPDATA%\Velo\config.json` |
| Presets | `%APPDATA%\Velo\presets\` |

---

## Build from source

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

```powershell
.\scripts\build.ps1 -Clean
.\scripts\build.ps1 -Clean -Installer
```

The installer build needs [Inno Setup 6](https://jrsoftware.org/isdl.php). Output goes to `dist\Velo\` and `installer\Output\Velo-Setup-*.exe`.

---

## Credits

Inspired by [input-overlay](https://github.com/girlglock/input-overlay).

## License

GNU GPL v3 or later. See [LICENSE](LICENSE).

The GPL covers Velo's source code. It does not grant permission to use the Velo name or logo for modified or unofficial distributions.
