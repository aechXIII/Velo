"""System tray icon for Velo."""

from __future__ import annotations

import threading
from typing import Callable, Optional

import pystray
from PIL import Image

from velo import __version__
from velo.assets import load_icon


class TrayApp:
    def __init__(
        self,
        *,
        on_open_settings: Callable[[], None],
        on_copy_url: Callable[[], None],
        on_copy_size: Callable[[], None],
        on_preview_off: Callable[[], None],
        on_open_overlay: Callable[[], None],
        on_quit: Callable[[], None],
        status_provider: Callable[[], str],
    ) -> None:
        self._on_open_settings = on_open_settings
        self._on_copy_url = on_copy_url
        self._on_copy_size = on_copy_size
        self._on_preview_off = on_preview_off
        self._on_open_overlay = on_open_overlay
        self._on_quit = on_quit
        self._status_provider = status_provider
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        image: Image.Image = load_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem("Open Settings", self._settings, default=True),
            pystray.MenuItem("Copy OBS URL", self._copy),
            pystray.MenuItem("Copy OBS size", self._copy_size),
            pystray.MenuItem("Preview Off", self._preview_off),
            pystray.MenuItem("Open Overlay Preview", self._preview),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: self._status_provider(),
                lambda _icon, _item: None,
                enabled=False,
            ),
            pystray.MenuItem(
                f"Velo {__version__}",
                lambda _icon, _item: None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Velo", self._quit),
        )
        self._icon = pystray.Icon("Velo", image, f"Velo {__version__}", menu)
        self._thread = threading.Thread(target=self._icon.run, name="velo-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except (RuntimeError, OSError, AttributeError):
                pass
        self._icon = None

    def notify(self, title: str, message: str) -> None:
        if not self._icon:
            return
        try:
            self._icon.notify(message, title)
        except (RuntimeError, OSError, AttributeError):
            pass

    def _settings(self, _icon=None, _item=None) -> None:
        self._on_open_settings()

    def _copy(self, _icon=None, _item=None) -> None:
        self._on_copy_url()

    def _copy_size(self, _icon=None, _item=None) -> None:
        self._on_copy_size()

    def _preview_off(self, _icon=None, _item=None) -> None:
        self._on_preview_off()

    def _preview(self, _icon=None, _item=None) -> None:
        self._on_open_overlay()

    def _quit(self, _icon=None, _item=None) -> None:
        self._on_quit()
