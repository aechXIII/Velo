"""Velo application: tray, settings window, capture server."""

from __future__ import annotations

import queue
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional

from velo import __version__
from velo import autostart
from velo import single_instance
from velo.config import APP_NAME, ConfigStore
from velo.constants import INSTALLER_DELAY, UPDATE_CHECK_DELAY
from velo.hotkeys import GlobalHotkeys
from velo.logging import get_logger
from velo.mouse_capture import MouseCapture
from velo.pipeline import EventPipeline
from velo.server import VeloServer
from velo.tray import TrayApp
from velo.updates import UpdateService, launch_installer

logger = get_logger()


def _win_message(title: str, text: str, *, error: bool = False) -> None:
    try:
        import ctypes

        flags = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        logger.error("[%s] %s", title, text)


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
        self.updates = UpdateService(
            current_version=__version__,
            on_available=self._on_update_available,
            on_install_ready=self._on_install_ready,
        )
        self._wire_server_callbacks()
        self.hotkeys = GlobalHotkeys()

        self._cmd: queue.Queue = queue.Queue()
        self._stopping = False
        self._window = None
        self._webview_lock = threading.Lock()
        self._startup_error: Optional[str] = None
        self._hotkey_spec: Optional[str] = None
        self._autostart_enabled: Optional[bool] = None
        self._pending_installer: Optional[Path] = None
        self._pending_show_requested = False

        self.tray = TrayApp(
            on_open_settings=self._request_show_settings,
            on_copy_url=self._copy_url,
            on_copy_size=self._copy_size,
            on_preview_off=self._preview_off,
            on_open_overlay=lambda: webbrowser.open(self.config.overlay_url()),
            on_quit=self._request_quit,
            status_provider=self._tray_status,
            on_open_update=self._request_show_update,
            update_label_provider=self._tray_update_label,
        )

    def run(self) -> None:
        self.server.start()
        if not self.server.running:
            err = self.server.last_error or "unknown bind error"
            self._startup_error = err
            logger.error("Server failed to start: %s", err)

        try:
            self.pipeline.start()
        except Exception as exc:
            self._startup_error = (self._startup_error or "") + f"\nCapture: {exc}"
            logger.error("Capture failed: %s", exc)

        try:
            self.hotkeys.start()
            self._apply_hotkeys(force=True)
        except Exception as exc:
            logger.error("Hotkeys failed: %s", exc)

        try:
            self._apply_autostart(force=True)
        except Exception as exc:
            logger.error("Autostart failed: %s", exc)

        self.config.on_change(self._on_config_shell)

        self._refresh_runtime_status()
        self.tray.start()
        self._refresh_update_tray()

        logger.info("%s ready", __version__)
        logger.info("Overlay: %s", self.config.overlay_url())
        logger.info("Config:  %s", self.config.config_url())

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
            logger.error("Capture: %s", self.capture.last_error)
        elif not self.capture.running:
            msg = "Mouse capture did not start."
            self.tray.notify("Velo capture issue", msg)
            logger.error("%s", msg)

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

        self._schedule_startup_update_check()
        self._main_loop()

    def _wire_server_callbacks(self) -> None:
        self.server.set_restart_callback(self.restart_server)
        self.server.set_stats_reset_callback(self.pipeline.reset_stats)
        self.server.set_show_settings_callback(self._request_show_settings)
        self.server.set_update_service(self.updates)

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

    def _request_show_settings(self) -> None:
        logger.info("_request_show_settings called")
        if self._stopping:
            return
        win = self._window
        if win is None:
            logger.warning("_window is None, deferring show request")
            self._pending_show_requested = True
            try:
                self._cmd.put_nowait("settings")
            except queue.Full:
                self._cmd.put("settings")
            return

        try:
            if hasattr(win, "restore"):
                logger.info("calling win.restore()")
                win.restore()
                logger.info("win.restore() done")
            if hasattr(win, "show"):
                logger.info("calling win.show()")
                win.show()
                logger.info("win.show() done")
            # Briefly pin window on top to force it to the foreground
            try:
                logger.info("setting on_top = True")
                win.on_top = True
                logger.info("on_top = True done")
                logger.info("setting on_top = False")
                win.on_top = False
                logger.info("on_top = False done")
            except (OSError, RuntimeError, AttributeError) as exc:
                logger.warning("on_top toggle failed: %s", exc)
            logger.info("_request_show_settings - applying force foreground")
            self._force_foreground()
            logger.info("_request_show_settings returning")
            return
        except (OSError, RuntimeError, AttributeError) as exc:
            logger.warning("window restore/show failed: %s", exc)

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

            # Focus window when shown (fires after create_window, during webview.start)
            def _on_shown() -> None:
                logger.info("window shown event fired")
                win = self._window
                if win is None:
                    return
                try:
                    if hasattr(win, "restore"):
                        win.restore()
                    if hasattr(win, "show"):
                        win.show()
                    try:
                        win.on_top = True
                        win.on_top = False
                    except (OSError, RuntimeError, AttributeError):
                        pass
                except (OSError, RuntimeError, AttributeError):
                    pass
                # Process any deferred show request that arrived before window was ready
                if self._pending_show_requested:
                    self._pending_show_requested = False
                    logger.info("processing deferred show request via shown event")
                    try:
                        if hasattr(win, "restore"):
                            win.restore()
                        if hasattr(win, "show"):
                            win.show()
                        try:
                            win.on_top = True
                            win.on_top = False
                        except (OSError, RuntimeError, AttributeError):
                            pass
                    except (OSError, RuntimeError, AttributeError):
                        pass

                self._force_foreground()

            if hasattr(self._window, "events") and hasattr(self._window.events, "shown"):
                self._window.events.shown += _on_shown

            try:
                logger.info("starting webview event loop")
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
    def _force_foreground() -> None:
        import ctypes
        from ctypes import wintypes

        try:
            user32 = ctypes.windll.user32

            hwnd = user32.FindWindowW(None, "Velo")
            if not hwnd:
                return

            foreground = user32.GetForegroundWindow()
            if foreground == hwnd:
                return

            GetWindowThreadProcessId = user32.GetWindowThreadProcessId
            GetWindowThreadProcessId.argtypes = [wintypes.HWND, wintypes.LPVOID]
            GetWindowThreadProcessId.restype = wintypes.DWORD

            foreground_tid = 0
            if foreground:
                foreground_tid = GetWindowThreadProcessId(foreground, None)
            target_tid = GetWindowThreadProcessId(hwnd, None)

            attached = False
            if foreground_tid and foreground_tid != target_tid:
                user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
                user32.AttachThreadInput.restype = wintypes.BOOL
                user32.AttachThreadInput(foreground_tid, target_tid, True)
                attached = True

            try:
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(foreground_tid, target_tid, False)
        except Exception:
            pass

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

    def _tray_update_label(self) -> Optional[str]:
        ver = self.updates.pending_version()
        if not ver:
            return None
        return f"Update to {ver}..."

    def _refresh_update_tray(self) -> None:
        ver = self.updates.pending_version()
        if ver:
            self.tray.set_tooltip(f"Velo {__version__} · update {ver} available")
        else:
            self.tray.set_tooltip(f"Velo {__version__}")
        self.tray.refresh_menu()

    def _schedule_startup_update_check(self) -> None:
        if self._stopping:
            return
        mode = str(self.config.get("update_check_mode") or "launch").strip().lower()
        if mode == "off":
            self._refresh_update_tray()
            return
        daily = mode == "daily"
        if not self.updates.should_auto_check(enabled=True, force_interval=daily):
            self._refresh_update_tray()
            return

        def _later() -> None:
            if self._stopping:
                return
            m = str(self.config.get("update_check_mode") or "launch").strip().lower()
            if m == "off":
                return
            self.updates.check_async(
                manual=False,
                notify=True,
                on_done=lambda _s: self._refresh_update_tray(),
            )

        threading.Timer(UPDATE_CHECK_DELAY, _later).start()

    def _on_update_available(self, status: Dict[str, Any]) -> None:
        if self._stopping:
            return
        ver = str((status or {}).get("latest_version") or "")
        if not ver:
            return
        self._refresh_update_tray()
        if not bool(self.config.get("start_minimized")):
            try:
                self.config.update({"ui_section": "settings"}, persist=True)
            except Exception:
                pass
            self._request_show_settings()
            self.tray.notify(f"Velo {ver} available", "Update available")
        else:
            self.tray.notify(
                f"Velo {ver} available",
                "Right-click the tray icon -> Update, or open Settings",
            )

    def _request_show_update(self) -> None:
        if self._stopping:
            return
        try:
            self.config.update({"ui_section": "settings"}, persist=True)
        except Exception:
            pass
        self._request_show_settings()

    def _on_install_ready(self, setup_path: Path) -> None:
        if self._stopping:
            return
        self._pending_installer = Path(setup_path)
        logger.info("Starting installer: %s", setup_path)
        try:
            launch_installer(Path(setup_path))
        except Exception as exc:
            logger.error("Could not start installer: %s", exc)
            self.updates.fail_install(str(exc))
            self.tray.notify("Velo update failed", str(exc))
            return
        self.tray.notify("Velo", "Installer started. Closing Velo.")
        threading.Timer(INSTALLER_DELAY, self._request_quit).start()

    def restart_server(self) -> None:
        try:
            self.server.stop()
        except Exception:
            pass
        time.sleep(0.2)
        self.server = VeloServer(self.config)
        self.pipeline.server = self.server
        self._wire_server_callbacks()
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
        # also re-apply if any preset hotkey changed
        hotkeys = (snap or {}).get("preset_hotkeys") or []
        if hotkeys:
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
            logger.error("Autostart: %s", err)
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
            logger.info("HUD reset hotkey: %s", label)
        elif spec and not label and self.hotkeys.last_error:
            logger.error("%s", self.hotkeys.last_error)
        elif not spec:
            logger.info("HUD reset hotkey: off")

        # preset hotkeys — clear old, re-register all
        # clear all bindings that start with "preset:"
        hotkeys = self.config.get("preset_hotkeys") or []
        # Re-register: add_binding with the same spec overwrites previous
        seen: set = set()
        for entry in hotkeys:
            hk = str(entry.get("key") or "").strip()
            target = str(entry.get("target") or "").strip()
            if hk and target and hk not in seen:
                seen.add(hk)
                def _make_switch(name):
                    return lambda: self.config.apply_preset(name)
                self.hotkeys.add_binding(hk, _make_switch(target))
        logger.info("Registered %d preset hotkeys", len(seen))

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
    logger.info("starting %s", __version__)
    dep_err = check_dependencies()
    if dep_err:
        logger.error(dep_err)
        _win_message("Velo - setup needed", dep_err, error=True)
        raise SystemExit(1)

    if not single_instance.try_acquire():
        try:
            cfg = ConfigStore()
            handed_off = single_instance.request_show_settings(cfg)
        except Exception as exc:
            handed_off = False
            logger.error("Could not contact running instance: %s", exc)
        if handed_off:
            logger.info("Already running — opened Settings in the existing instance")
        else:
            logger.error("Already running")
            _win_message(
                "Velo",
                "Velo is already running.\n\nUse the tray icon to open Settings.",
            )
        raise SystemExit(0)

    try:
        app = VeloApp()
        app.run()
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("fatal: %s", exc)
        _win_message("Velo - failed to start", str(exc), error=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
