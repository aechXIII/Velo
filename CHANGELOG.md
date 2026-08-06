# Changelog

## [2.2.0] - 2026-08-06

### Added
- Pad background image
- Preset hotkeys
- Border glow effect
- Toast notification variants
- Slider double-click to reset an individual setting

### Changed
- Trail rendering rewritten with per-chunk gradients
- Slider preview now pushes updates to the preview instantly
- Preset toolbar shows "Unsaved changes" instead of "No preset selected" when settings are modified
- Background settings restructured

## [2.1.1] - 2026-07-26

### Fixed
- Preview hiding on click (again 💀)
- Trail color spike on mouse button press during movement

## [2.1.0] - 2026-07-26

### Added
- Speed chart to HUD
- Fade curve presets (6 options) for trail opacity
- Auto-backup system with configurable retention
- Section navigation dots showing unsaved changes
- Loading skeleton while config loads
- WebSocket keepalive to prevent connection drops

### Fixed
- stats_dpi range clamping (100-32000)
- trail_curve interpolation capped at 2000
- Server binding to all interfaces
- Preview hiding on click

### Changed
- Updated scrollbar styling
- Preview focus detection

### Removed
- Connection status indicator from overlay

## [2.0.1] - 2026-07-26

### Fixed
- Window not focusing when launched again

### Changed
- Simplified onboarding wizard

### Added
- OBS cache refresh tip in settings footer

## [2.0.0] - 2026-07-25

### Added
- Settings search bar
- Keyboard navigation
- Customizable accent and background colors
- Undo/redo for config changes
- Average speed toggle to HUD
- Live preview loading and error states
- Active preset menu
- Preset rename on double-click
- Toast notifications
- Onboarding wizard
- Glow customization - opacity, width, custom color
- Auto preview mode - turns off when unfocused, Live when focused

### Changed
- UI overhaul - toggle switches, new theme, redesigned preset toolbar, preview bar, app footer, import section
- Improved tooltips
- Preset share codes (VELO2) - shorter format

### Fixed
- Window not focusing
- Trail glow using wrong speed color on fade

## [1.2.0] - 2026-07-25

- Add Sensitivity and View zoom sliders to Motion
- Update motion feel presets
- Add discard button for dirty preset changes
- Fix camera position reset in fixed view mode

## [1.1.5] - 2026-07-24

- Increase max width and height for Size to 3840x2160

## [1.1.4] - 2026-07-24

- Simplify Updates settings; check every launch by default (or daily / off)
- Update notes in a modal with install, later, and skip
- Open Settings and update modal when an update is found (unless start minimized)
- Cleaner release notes in the update modal
- Esc does nothing while an update is downloading

## [1.1.2] - 2026-07-24

- In-app update check and install (GitHub Releases)
- Folder install (onedir) so the app loads Python DLLs reliably
- Auto-check option; skip / remind later; tray notice when minimized

## [1.0.4] - 2026-07-24

- Per-button click show/hide (left, right, middle, side)
- Click indicators follow the cursor
- Fix side-button colors and browser Back/Forward wiping the preview

## [1.0.3] - 2026-07-23

- Prevent a second Velo instance; open Settings on the already running app

## [1.0.2] - 2026-07-23

- Remove Unclamp sliders option from Size settings

## [1.0.1] - 2026-07-23

- HUD update rate: Slow / Normal / Fast (2 / 4 / 10 per second)

## [1.0.0] - 2026-07-23

First public release.

- Mouse Input overlay for OBS. Made for aim trainers and FPS games.
- Tray app, settings UI, presets, performance controls
- Session HUD with speed, peak, distance, clicks, CPS
- Movable HUD, metric or raw units (DPI-based conversion)
- Portable EXE + installer via GitHub Actions
