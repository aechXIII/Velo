# Privacy

Velo has no analytics, ads, telemetry, or automatic crash reporting.

## Local data

Velo stores settings, presets, background images, backups, update state, and logs under `%APPDATA%\Velo`. Uninstalling Velo leaves this folder in place so a reinstall does not erase your settings.

Normal settings exports leave out the local server host, port, and authentication token. Full backups include them and should stay private.

## Network activity

Velo runs a local HTTP/WebSocket server for Settings and the OBS Browser Source. It uses a random authentication token. Changing the host from `127.0.0.1` can make the server reachable from other devices on your network.

Standard builds contact GitHub Releases when update checks are enabled. Installing an update downloads the installer and its SHA-256 checksum from GitHub. itch.io builds leave updates to the itch app.

The installer uses Microsoft's WebView2 bootstrapper when WebView2 is missing. Support links open GitHub in your default browser.

## Diagnostics

**Copy diagnostics** includes Velo and Windows versions, distribution type, runtime architecture, WebView2 version, server state, and general config/log locations. It leaves out authentication tokens, OBS URLs, settings, presets, images, and other personal files.

Nothing is sent automatically. You choose where to paste the copied text.

## Contact

Questions and bugs: <https://github.com/aechXIII/Velo/issues>
