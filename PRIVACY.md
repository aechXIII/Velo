# Velo privacy

Velo does not include analytics, advertising, telemetry, or crash-reporting services.

## Data stored on this computer

Velo stores settings, presets, managed background images, automatic backups, update state, and rotating diagnostic logs under `%APPDATA%\Velo`. These files remain on the computer unless the user removes them. The uninstaller intentionally keeps them so reinstalling does not erase presets.

The settings export excludes the local server host, port, and authentication token by default. A user can explicitly create a full private backup that includes those connection fields.

## Network activity

Velo opens a local HTTP/WebSocket server for its settings page and OBS Browser Source. The server uses a randomly generated authentication token. Binding it to an address other than `127.0.0.1` can make it reachable from other devices on the local network.

Standard installer and portable builds contact the GitHub Releases API when update checks are enabled. Installing an update downloads the selected installer and its SHA-256 checksum from the project's GitHub release. Itch-managed builds leave updates to the itch.io app and do not perform Velo update checks.

The Windows installer may download Microsoft's WebView2 Evergreen Bootstrapper when the WebView2 Runtime is missing. Choosing support links opens GitHub in the default browser.

## Diagnostics

The **Copy diagnostics** action includes the Velo version, Windows version, distribution type, Python/runtime architecture, WebView2 version, server state, and generalized config/log locations. It excludes authentication tokens, OBS URLs, settings contents, presets, managed images, and other personal files. Nothing is sent automatically; the user decides where to paste it.

## Contact

Questions and bug reports can be opened at <https://github.com/aechXIII/Velo/issues>.
