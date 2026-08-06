# Feature Suggestions for Velo

## Game Integration & Profiles

### Game-Aware Profile Switching
The app already captures the foreground window for Raw Input registration. Extend this to detect the active window title/executable and auto-switch to a user-configured preset. Users configure "when Valorant is focused, use X preset" — the app handles the rest. Different games have radically different overlay needs.

### Per-Game DPI Profiles
`stats_dpi` is a single global value. Different games use different sensitivities. Allow binding DPI to game profiles so distance/speed calculations are accurate per-game.

### Game State Integration
Popular aim trainers (Aim Lab, Kovaak's) expose game state via files or local HTTP. Reading this would enable auto-reset stats on new scenario, show scenario name in overlay, or log scores alongside mouse data.

---

## Overlay Visuals

### Crosshair Overlay
The existing `pad_crosshair` is a static reference on the pad background. A proper overlay crosshair that follows the cursor position works in any game, including ones without crosshair customization. Configurable: color, size, gap, thickness, shape (cross, circle, dot, T-shape), dynamic expansion on movement/firing.

### Heatmap Overlay
Accumulate mouse position into a grid and render as a heatmap layer. Shows where you aim most, helps identify bad habits. Configurable: opacity, color gradient, grid resolution, blend mode.

### Per-Element Opacity
Currently `overlay_opacity` is global. Users want independent control of trail opacity, click indicator opacity, cursor dot opacity, HUD opacity, and background/pad opacity.

### Trail Gradient Mode
Add a mode where the trail fades through two user-chosen colors regardless of speed. Simple schema addition, big visual impact.

### Trail Echo / Ghost Trail
Show a trailing ghost of previous trail positions with increasing transparency. Creates a comet-tail effect. Configurable: echo count, decay rate, offset.

### Click Ripple Effect
Water ripple animation on clicks as an alternative to the current ring/fill/cross styles. The click system already has expand and lifetime — this is a new `click_style` option.

### Click Label Overlay
Show "LMB" / "RMB" / "M3" / "SIDE" text labels at click position. Useful for stream viewers to understand what the player is pressing.

---

## Analytics & Data

### Session Summary Panel
The app tracks real-time stats (speed, peak, distance, clicks, CPS) but doesn't persist them. Add a session summary view showing accumulated stats since app start or last reset. Include average speed, total distance, total clicks, peak CPS, session duration, and a sparkline of speed over the session.

### Statistics History / Logging
Log stats to a CSV/JSON file with timestamps. Users can review their performance over time. Optional auto-log on session end. Export button in settings.

### Smoothness & Accuracy Metrics
Beyond raw speed, calculate:
- **Smoothness score**: variance in speed over time (lower = smoother)
- **Micro-correction count**: how often the mouse changes direction rapidly
- **Click timing distribution**: time between clicks

### Performance Overlay
Show overlay FPS, input-to-render latency, WebSocket ping, event queue depth, and client count. The overlay already has a hidden debug FPS counter (`?debug=1`). Make it a proper toggle in settings.

---

## Interaction & UX

### Command Palette (Ctrl+K)
The settings UI already has a search bar. Extend it to support actions: toggle trail on/off, reset stats, switch preset, toggle HUD, toggle clicks, etc. Power users navigate settings much faster.

### Overlay Keyboard Shortcuts
Bind hotkeys to toggle overlay elements without opening settings: toggle trail visibility, toggle HUD, toggle click indicators, freeze/unfreeze trail display, cycle through presets.

### Trail Freeze Mode
Press a hotkey to freeze the current trail on screen. Useful for analyzing mouse path after a play. Frozen trails highlighted with a different color. Press again to clear.

### Auto-Hide HUD on Idle
HUD fades out after N seconds of no mouse input, fades back in on movement. Configurable timeout. Reduces visual clutter during quiet moments.

### Overlay Mirror / Flip
Mirror the overlay horizontally or vertically. Useful for left-handed users or specific OBS layouts.

---

## Presets & Customization

### Color Themes
Pre-built color schemes that set multiple colors at once (trail, clicks, cursor, background, accent). Examples: "Neon", "Minimal", "Streamer", "Classic". Apply a theme then tweak individual colors.

### Preset Favorites / Quick-Switch
Mark presets as favorites and switch between them from the tray icon or a hotkey. The tray menu currently has static items — dynamic preset switching would be high impact.

### Preset Comparison View
Show a side-by-side diff of two presets. Useful when tweaking settings — see what changed between versions.

---

## System & Integration

### OBS Scene / Source Auto-Management
If OBS WebSocket plugin is detected, offer to auto-create the browser source or toggle overlay visibility from OBS scenes.

### Multiple Monitor Support
Allow choosing which monitor the overlay targets. Handle different DPI scaling across monitors.

### Startup Preset
Choose which preset is active on app launch. Currently remembers the last active preset — users might want "always start with my streaming preset".

### Config Profiles (Beyond Presets)
Presets exclude connection settings, DPI, hotkeys, etc. Add config profiles that save everything including connection info, so users can have "Home setup" vs "LAN party setup" profiles.

---

## Quick Wins (Small Scope, Noticeable Impact)

| Suggestion | Why |
|---|---|
| Resolution quick-buttons in Size section (720p, 1080p, 1440p) | Saves typing |
| Color swatches / recently used in color pickers | Faster iteration |
| Tray icon right-click → preset list | Quick switching without opening settings |
| Stats export (CSV/JSON) button in HUD section | Users want to analyze offline |
| Overlay URL copy in tray menu | Currently only in settings |
| "Reset stats" button in the overlay itself (not just settings) | Convenience |
| Trail width per speed toggle (already partially implemented) | Polish existing feature |

---

## Top 5 by Impact/Effort

| # | Feature | Impact | Effort | Why |
|---|---|---|---|---|
| 1 | **Game-Aware Profiles** | High | Moderate | Solves real friction, builds on existing infra |
| 2 | **Crosshair Overlay** | High | Small | Simple addition, huge value for FPS players |
| 3 | **Per-Element Opacity** | Medium | Small | Users will notice immediately |
| 4 | **Heatmap** | High | Moderate | Genuinely useful for aim analysis |
| 5 | **Command Palette** | Medium | Small | Power users will love it |
