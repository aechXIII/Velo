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
from velo import autostart, distribution, single_instance
from velo.config import APP_NAME, ConfigStore
from velo.constants import INSTALLER_DELAY, UPDATE_CHECK_DELAY
from velo.hotkeys import GlobalHotkeys
from velo.logging import get_logger, install_exception_hooks, log_path
from velo.mouse_capture import MouseCapture
from velo.pipeline import EventPipeline
from velo.server import VeloServer
from velo.tray import TrayApp
from velo.updates import UpdateService, launch_installer
from velo.webview2 import WEBVIEW2_DOWNLOAD_URL, is_installed as webview2_is_installed

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
            pass  # optional: only used for extra Win32 integration, not required to run
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
        self.distribution_channel = distribution.distribution_channel()
        self.capture = MouseCapture()
        self.server = VeloServer(self.config)
        self.pipeline = EventPipeline(self.config, self.capture, self.server)
        self.updates = UpdateService(
            current_version=__version__,
            on_available=self._on_update_available,
            on_install_ready=self._on_install_ready,
            managed_externally=distribution.updates_managed_externally(),
        )
        self._wire_server_callbacks()
        self.hotkeys = GlobalHotkeys()

        self._cmd: queue.Queue = queue.Queue()
        self._stopping = False
        self._window = None
        self._webview_lock = threading.Lock()
        self._startup_error: Optional[str] = None
        self._hotkey_spec: Optional[str] = None
        self._preset_hotkey_state: tuple[tuple[str, str], ...] = ()
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

    def _start_subsystems(self) -> None:
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

    def _notify_startup_issues(self) -> None:
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

    def run(self) -> None:
        self.server.start()
        if not self.server.running:
            err = self.server.last_error or "unknown bind error"
            self._startup_error = err
            logger.error("Server failed to start: %s", err)

        self._start_subsystems()

        self.config.on_change(self._on_config_shell)

        self._refresh_runtime_status()
        self.tray.start()
        self._refresh_update_tray()

        if self.config.recovery_notice:
            self.tray.notify("Velo recovered settings", self.config.recovery_notice)

        logger.info("%s ready", __version__)
        logger.info("Overlay server ready on %s:%s", self.config.get("host"), self.config.get("port"))
        logger.info("Distribution: %s", self.distribution_channel)

        self._notify_startup_issues()

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
        except Exception as exc:
            logger.debug("Could not refresh runtime status: %s", exc)

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
        logger.debug("_request_show_settings called")
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
                logger.debug("calling win.restore()")
                win.restore()
                logger.debug("win.restore() done")
            if hasattr(win, "show"):
                logger.debug("calling win.show()")
                win.show()
                logger.debug("win.show() done")
            # Briefly pin window on top to force it to the foreground
            try:
                logger.debug("setting on_top = True")
                win.on_top = True
                logger.debug("on_top = True done")
                logger.debug("setting on_top = False")
                win.on_top = False
                logger.debug("on_top = False done")
            except (OSError, RuntimeError, AttributeError) as exc:
                logger.warning("on_top toggle failed: %s", exc)
            logger.debug("_request_show_settings - applying force foreground")
            self._force_foreground()
            logger.debug("_request_show_settings returning")
            return
        except (OSError, RuntimeError, AttributeError) as exc:
            logger.warning("window restore/show failed: %s", exc)

    def _restore_and_focus_window(self, win: Any) -> None:
        try:
            if hasattr(win, "restore"):
                win.restore()
            if hasattr(win, "show"):
                win.show()
            try:
                win.on_top = True
                win.on_top = False
            except (OSError, RuntimeError, AttributeError) as exc:
                logger.debug("on_top toggle failed: %s", exc)
        except (OSError, RuntimeError, AttributeError) as exc:
            logger.debug("window restore/show failed: %s", exc)

    def _create_settings_window(self, webview_module: Any) -> None:
        url = self.config.config_url()
        self._window = webview_module.create_window(
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
            logger.debug("window shown event fired")
            win = self._window
            if win is None:
                return
            self._restore_and_focus_window(win)
            # Process any deferred show request that arrived before window was ready
            if self._pending_show_requested:
                self._pending_show_requested = False
                logger.debug("processing deferred show request via shown event")
                self._restore_and_focus_window(win)

            self._force_foreground()

        if hasattr(self._window, "events") and hasattr(self._window.events, "shown"):
            self._window.events.shown += _on_shown

    def _drain_pending_quit(self) -> None:
        if self._stopping:
            return
        while True:
            try:
                extra = self._cmd.get_nowait()
            except queue.Empty:
                break
            if extra == "quit":
                self._cmd.put("quit")
                break

    def _open_settings_blocking(self) -> None:
        if not webview2_is_installed():
            _win_message(
                "Velo - WebView2 required",
                "Microsoft Edge WebView2 Runtime is required for Velo settings.\n\n"
                "The official Microsoft download page will open now. Install the Evergreen "
                "Runtime, then start Velo again.",
                error=True,
            )
            webbrowser.open(WEBVIEW2_DOWNLOAD_URL)
            return
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

            self._create_settings_window(webview)

            try:
                distribution.unblock_packaged_settings_runtime()
                logger.debug("starting webview event loop")
                webview.start(debug=False)
            except (OSError, RuntimeError) as exc:
                _win_message(
                    "Velo - settings window failed",
                    f"Could not open the settings UI.\n\n{exc}\n\n"
                    "Restart Velo. If it still fails, include the latest file from "
                    "%APPDATA%\\Velo\\logs when reporting it.",
                    error=True,
                )
            self._window = None

        self._drain_pending_quit()

    def _request_quit(self) -> None:
        self._stopping = True
        if self._window is not None:
            try:
                self._window.destroy()
            except (OSError, RuntimeError, AttributeError) as exc:
                logger.debug("Could not destroy window on quit: %s", exc)
        self._cmd.put("quit")

    def _copy_url(self) -> None:
        url = self.config.overlay_url()
        ok = self._clipboard(url)
        if ok:
            self.tray.notify("OBS URL copied", "Authenticated OBS URL copied to the clipboard")
        else:
            self.tray.notify("Velo", "Could not copy the OBS URL. Open Settings → OBS to try again.")

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
        except Exception as exc:
            logger.debug("Could not force window to foreground: %s", exc)

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
            except Exception as exc:
                logger.debug("Could not switch UI section for update prompt: %s", exc)
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
        except Exception as exc:
            logger.debug("Could not switch UI section for update view: %s", exc)
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
        except Exception as exc:
            logger.debug("Could not stop server cleanly before restart: %s", exc)
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
        hotkey_state = self._normalized_preset_hotkeys((snap or {}).get("preset_hotkeys"))
        if spec != (self._hotkey_spec or "") or hotkey_state != self._preset_hotkey_state:
            self._apply_hotkeys(force=True)
        enabled = bool((snap or {}).get("start_with_windows"))
        if self._autostart_enabled is None or enabled != self._autostart_enabled:
            self._apply_autostart(force=True)

    def _apply_autostart(self, force: bool = False) -> None:
        if self._stopping:
            return
        enabled = bool(self.config.get("start_with_windows"))
        if not distribution.autostart_supported():
            err = autostart.set_enabled(False)
            if err:
                logger.error("Could not remove unsupported itch autostart entry: %s", err)
            self._autostart_enabled = False
            if enabled:
                self.config.update({"start_with_windows": False}, persist=True)
            return
        if not force and self._autostart_enabled is not None and enabled == self._autostart_enabled:
            return
        err = autostart.set_enabled(enabled)
        if err:
            logger.error("Autostart: %s", err)
            return
        self._autostart_enabled = enabled

    def _log_hotkey_registration(
        self, spec: str, label: Optional[str], binding_count: int
    ) -> None:
        if spec and label:
            logger.info("HUD reset hotkey: %s", label)
        elif spec and not label and self.hotkeys.last_error:
            logger.error("%s", self.hotkeys.last_error)
        elif not spec:
            logger.info("HUD reset hotkey: off")
        logger.info("Registered %d preset hotkeys", binding_count)

    def _apply_hotkeys(self, force: bool = False) -> None:
        if self._stopping:
            return
        spec = str(self.config.get("stats_reset_hotkey") or "").strip()
        hotkeys = self.config.get("preset_hotkeys") or []
        hotkey_state = self._normalized_preset_hotkeys(hotkeys)
        if (
            not force
            and spec == (self._hotkey_spec or "")
            and hotkey_state == self._preset_hotkey_state
        ):
            return
        self._hotkey_spec = spec
        self._preset_hotkey_state = hotkey_state

        def _on_reset() -> None:
            try:
                self.pipeline.reset_stats()
            except Exception as exc:
                logger.debug("Could not reset stats via hotkey: %s", exc)

        bindings = []
        for key, target in hotkey_state:
            def _make_switch(name: str):
                return lambda: self.config.apply_preset(name)

            bindings.append((key, _make_switch(target)))

        label, binding_count = self.hotkeys.replace_bindings(spec, _on_reset, bindings)
        self._log_hotkey_registration(spec, label, binding_count)

    @staticmethod
    def _normalized_preset_hotkeys(value: Any) -> tuple[tuple[str, str], ...]:
        if not isinstance(value, list):
            return ()
        result = []
        seen = set()
        for entry in value:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("key") or "").strip()
            target = str(entry.get("target") or "").strip()
            normalized = key.casefold()
            if key and target and normalized not in seen:
                result.append((key, target))
                seen.add(normalized)
        return tuple(result)

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
            except (OSError, RuntimeError, AttributeError) as exc:
                logger.debug("Shutdown step %s failed: %s", getattr(step, "__name__", step), exc)
        threading.Timer(0.35, lambda: sys.exit(0)).start()


def _self_test() -> Optional[str]:
    dep_err = check_dependencies()
    if dep_err:
        return dep_err
    try:
        distribution.unblock_packaged_settings_runtime()
        if sys.platform == "win32":
            import webview.platforms.winforms  # noqa: F401

        from velo.server import CONFIG_UI_DIR, OVERLAY_DIR

        required = (
            OVERLAY_DIR / "index.html",
            OVERLAY_DIR / "app.js",
            CONFIG_UI_DIR / "index.html",
            CONFIG_UI_DIR / "app.js",
            distribution.executable_root() / "LICENSE",
            distribution.executable_root() / "PRIVACY.md",
            distribution.executable_root() / "THIRD_PARTY_NOTICES.md",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            return "Missing packaged assets: " + ", ".join(missing)
        if (distribution.executable_root() / ".itch.toml").is_file():
            if distribution.distribution_channel() != "itch":
                return "itch distribution marker was not detected"
    except (ImportError, OSError, RuntimeError) as exc:
        return str(exc)
    return None


def _handle_existing_instance() -> None:
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


def main() -> None:
    install_exception_hooks()
    logger.info("starting %s", __version__)

    if "--version" in sys.argv:
        if sys.stdout is not None:
            print(__version__)
        return
    if "--self-test" in sys.argv:
        error = _self_test()
        if error:
            logger.error("Self-test failed: %s", error)
            raise SystemExit(1)
        logger.info("Self-test passed")
        return

    dep_err = check_dependencies()
    if dep_err:
        logger.error(dep_err)
        _win_message("Velo - setup needed", dep_err, error=True)
        raise SystemExit(1)

    if not single_instance.try_acquire():
        _handle_existing_instance()
        raise SystemExit(0)

    try:
        app = VeloApp()
        app.run()
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("fatal startup error")
        _win_message(
            "Velo - failed to start",
            f"{exc}\n\nDetails were saved to:\n{log_path()}",
            error=True,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
