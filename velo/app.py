"""Velo application: tray, settings window, capture server."""

from __future__ import annotations

import queue
import sys
import threading
import time
import webbrowser
from typing import Any, Dict, Optional

from velo import __version__
from velo import autostart
from velo.config import APP_NAME, ConfigStore
from velo.hotkeys import GlobalHotkeys
from velo.mouse_capture import MouseCapture
from velo.pipeline import EventPipeline
from velo.server import VeloServer
from velo.tray import TrayApp


def _win_message(title: str, text: str, *, error: bool = False) -> None:
    try:
        import ctypes

        flags = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        print(f"[{title}] {text}", file=sys.stderr)


def check_dependencies() -> Optional[str]:
    missing = []
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        missing.append("aiohttp")
    try:
        import pystray  # noqa: F401
    except ImportError:
        missing.append("pystray")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    try:
        import webview  # noqa: F401
    except ImportError:
        missing.append("pywebview")
    if sys.platform == "win32":
        try:
            import win32api  # noqa: F401
        except ImportError:
            pass
    if missing:
        return (
            "Missing Python packages:\n  "
            + ", ".join(missing)
            + "\n\nFrom the Velo folder run:\n  setup.bat\n\nor:\n  pip install -r requirements.txt"
        )
    return None


class VeloApp:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise SystemExit("Velo currently supports Windows only.")

        self.config = ConfigStore()
        self.capture = MouseCapture()
        self.server = VeloServer(self.config)
        self.pipeline = EventPipeline(self.config, self.capture, self.server)
        self.server.set_restart_callback(self.restart_server)
        self.server.set_stats_reset_callback(self.pipeline.reset_stats)
        self.hotkeys = GlobalHotkeys()

        self._cmd: queue.Queue = queue.Queue()
        self._stopping = False
        self._window = None
        self._webview_lock = threading.Lock()
        self._startup_error: Optional[str] = None
        self._hotkey_spec: Optional[str] = None
        self._autostart_enabled: Optional[bool] = None

        self.tray = TrayApp(
            on_open_settings=lambda: self._cmd.put("settings"),
            on_copy_url=self._copy_url,
            on_copy_size=self._copy_size,
            on_preview_off=self._preview_off,
            on_open_overlay=lambda: webbrowser.open(self.config.overlay_url()),
            on_quit=self._request_quit,
            status_provider=self._tray_status,
        )

    def run(self) -> None:
        self.server.start()
        if not self.server.running:
            err = self.server.last_error or "unknown bind error"
            self._startup_error = err
            print(f"[Velo] Server failed to start: {err}", file=sys.stderr)

        try:
            self.pipeline.start()
        except Exception as exc:
            self._startup_error = (self._startup_error or "") + f"\nCapture: {exc}"
            print(f"[Velo] Capture failed: {exc}", file=sys.stderr)

        try:
            self.hotkeys.start()
            self._apply_hotkeys(force=True)
        except Exception as exc:
            print(f"[Velo] Hotkeys failed: {exc}", file=sys.stderr)

        try:
            self._apply_autostart(force=True)
        except Exception as exc:
            print(f"[Velo] Autostart failed: {exc}", file=sys.stderr)

        self.config.on_change(self._on_config_shell)

        self._refresh_runtime_status()
        self.tray.start()

        print(f"[Velo] {__version__} ready")
        print(f"[Velo] Overlay: {self.config.overlay_url()}")
        print(f"[Velo] Config:  {self.config.config_url()}")

        if not self.server.running:
            self.tray.notify("Velo server failed", self.server.last_error or "Could not bind port")
            _win_message(
                "Velo - server error",
                "Could not start the local server.\n\n"
                f"{self.server.last_error or 'Unknown error'}\n\n"
                "Another app may be using the port, or the host/port settings are wrong.\n"
                "Open Settings and change Port, then Restart server.",
                error=True,
            )
        elif self.capture.last_error:
            self.tray.notify("Velo capture issue", self.capture.last_error)
            print(f"[Velo] Capture: {self.capture.last_error}", file=sys.stderr)
        elif not self.capture.running:
            msg = "Mouse capture did not start."
            self.tray.notify("Velo capture issue", msg)
            print(f"[Velo] {msg}", file=sys.stderr)

        snap = self.config.snapshot()
        # Tray-only when Autostart + Minimized; otherwise open settings
        open_ui = not (
            bool(snap.get("start_with_windows")) and bool(snap.get("start_minimized"))
        )
        if self._startup_error or not self.server.running:
            open_ui = True
        if open_ui:
            self._cmd.put("settings")
        else:
            self.tray.notify(
                "Velo is running",
                "Right-click the tray icon → Open Settings",
            )

        self._main_loop()

    def _refresh_runtime_status(self) -> None:
        try:
            self.server.set_runtime_status(
                capture_running=bool(self.capture.running),
                capture_error=self.capture.last_error,
            )
        except Exception:
            pass

    def _main_loop(self) -> None:
        while not self._stopping:
            try:
                cmd = self._cmd.get(timeout=0.5)
            except queue.Empty:
                self._refresh_runtime_status()
                continue
            if cmd == "quit":
                self.shutdown()
                break
            if cmd == "settings":
                self._open_settings_blocking()

    def _open_settings_blocking(self) -> None:
        try:
            import webview
        except ImportError:
            _win_message(
                "Velo - missing pywebview",
                "pywebview is not installed.\n\nRun setup.bat, then try again.",
                error=True,
            )
            return

        with self._webview_lock:
            if self._stopping:
                return
            if not self.server.running:
                err = self.server.last_error or "Server is not running"
                _win_message(
                    "Velo - cannot open settings",
                    f"{err}\n\n"
                    "The settings page is served by the local server.\n"
                    "Fix the port conflict (or close the other app using it),\n"
                    "then start Velo again.",
                    error=True,
                )
                return

            url = self.config.config_url()
            self._window = webview.create_window(
                f"{APP_NAME}",
                url=url,
                width=1180,
                height=820,
                min_size=(920, 640),
                background_color="#08090d",
                text_select=True,
            )

            def _on_closed() -> None:
                self._window = None

            if hasattr(self._window, "events") and hasattr(self._window.events, "closed"):
                self._window.events.closed += _on_closed

            try:
                webview.start(debug=False)
            except (OSError, RuntimeError) as exc:
                _win_message(
                    "Velo - settings window failed",
                    f"Could not open the settings UI.\n\n{exc}\n\n"
                    "On Windows, pywebview needs a WebView2 runtime (Edge).",
                    error=True,
                )
            self._window = None

        if not self._stopping:
            while True:
                try:
                    extra = self._cmd.get_nowait()
                except queue.Empty:
                    break
                if extra == "quit":
                    self._cmd.put("quit")
                    break

    def _request_quit(self) -> None:
        self._stopping = True
        if self._window is not None:
            try:
                self._window.destroy()
            except (OSError, RuntimeError, AttributeError):
                pass
        self._cmd.put("quit")

    def _copy_url(self) -> None:
        url = self.config.overlay_url()
        ok = self._clipboard(url)
        if ok:
            self.tray.notify("OBS URL copied", url)
        else:
            self.tray.notify("Velo", url)

    def _copy_size(self) -> None:
        w = int(self.config.get("canvas_width") or 640)
        h = int(self.config.get("canvas_height") or 360)
        text = f"{w} x {h}"
        ok = self._clipboard(text)
        if ok:
            self.tray.notify("OBS size copied", text)
        else:
            self.tray.notify("Velo", text)

    def _preview_off(self) -> None:
        self.config.update({"ui_preview_mode": "off"}, persist=True)
        self.tray.notify("Velo", "Settings preview set to Off")

    @staticmethod
    def _clipboard(text: str) -> bool:
        try:
            import ctypes

            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            if not user32.OpenClipboard(None):
                return False
            user32.EmptyClipboard()
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h:
                user32.CloseClipboard()
                return False
            p = kernel32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            kernel32.GlobalUnlock(h)
            user32.SetClipboardData(CF_UNICODETEXT, h)
            user32.CloseClipboard()
            return True
        except Exception:
            try:
                import subprocess

                p = subprocess.run(
                    "clip",
                    input=text,
                    text=True,
                    encoding="utf-16-le",
                    check=False,
                    shell=True,
                )
                return p.returncode == 0
            except Exception:
                return False

    def _tray_status(self) -> str:
        if not self.server.running:
            return "Server offline"
        if self.capture.last_error:
            return "Capture error"
        if not self.capture.running:
            return "Capture offline"
        n = self.server.client_count
        return f"Online, {n} client{'s' if n != 1 else ''}"

    def restart_server(self) -> None:
        try:
            self.server.stop()
        except Exception:
            pass
        time.sleep(0.2)
        self.server = VeloServer(self.config)
        self.server.set_restart_callback(self.restart_server)
        self.server.set_stats_reset_callback(self.pipeline.reset_stats)
        self.pipeline.server = self.server
        self.server.start()
        self._refresh_runtime_status()
        if self.server.running:
            self.tray.notify("Velo", f"Server on port {self.config.get('port')}")
        else:
            self.tray.notify("Velo", f"Server failed: {self.server.last_error}")

    def _on_config_shell(self, snap: Dict[str, Any]) -> None:
        if self._stopping:
            return
        spec = str((snap or {}).get("stats_reset_hotkey") or "").strip()
        if spec != (self._hotkey_spec or ""):
            self._apply_hotkeys(force=True)
        enabled = bool((snap or {}).get("start_with_windows"))
        if self._autostart_enabled is None or enabled != self._autostart_enabled:
            self._apply_autostart(force=True)

    def _apply_autostart(self, force: bool = False) -> None:
        if self._stopping:
            return
        enabled = bool(self.config.get("start_with_windows"))
        if not force and self._autostart_enabled is not None and enabled == self._autostart_enabled:
            return
        err = autostart.set_enabled(enabled)
        if err:
            print(f"[Velo] Autostart: {err}", file=sys.stderr)
            return
        self._autostart_enabled = enabled

    def _apply_hotkeys(self, force: bool = False) -> None:
        if self._stopping:
            return
        spec = str(self.config.get("stats_reset_hotkey") or "").strip()
        if not force and spec == (self._hotkey_spec or ""):
            return
        self._hotkey_spec = spec

        def _on_reset() -> None:
            try:
                self.pipeline.reset_stats()
            except Exception:
                pass

        label = self.hotkeys.set_hotkey(spec, _on_reset)
        if spec and label:
            print(f"[Velo] HUD reset hotkey: {label}", file=sys.stderr)
        elif spec and not label and self.hotkeys.last_error:
            print(f"[Velo] {self.hotkeys.last_error}", file=sys.stderr)
        elif not spec:
            print("[Velo] HUD reset hotkey: off", file=sys.stderr)

    def shutdown(self) -> None:
        self._stopping = True
        for step in (
            self.hotkeys.stop,
            lambda: self._window.destroy() if self._window is not None else None,
            self.pipeline.stop,
            self.server.stop,
            self.tray.stop,
        ):
            try:
                step()
            except (OSError, RuntimeError, AttributeError):
                pass
        threading.Timer(0.35, lambda: sys.exit(0)).start()


def main() -> None:
    print(f"[Velo] starting {__version__}")
    dep_err = check_dependencies()
    if dep_err:
        print(dep_err, file=sys.stderr)
        _win_message("Velo - setup needed", dep_err, error=True)
        raise SystemExit(1)
    try:
        app = VeloApp()
        app.run()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[Velo] fatal: {exc}", file=sys.stderr)
        _win_message("Velo - failed to start", str(exc), error=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
