"""System tray icon for Velo."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import pystray
from PIL import Image

from velo import __version__
from velo.assets import load_icon
from velo.logging import get_logger

logger = get_logger()


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
        on_open_update: Optional[Callable[[], None]] = None,
        update_label_provider: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        self._on_open_settings = on_open_settings
        self._on_copy_url = on_copy_url
        self._on_copy_size = on_copy_size
        self._on_preview_off = on_preview_off
        self._on_open_overlay = on_open_overlay
        self._on_quit = on_quit
        self._status_provider = status_provider
        self._on_open_update = on_open_update
        self._update_label_provider = update_label_provider
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _adapt(callback: Callable[[], None]) -> Callable[[Any, Any], None]:
        """Wrap a no-arg callback as a pystray menu handler, which expects (icon, item)."""

        def _handler(_icon=None, _item=None) -> None:
            callback()

        return _handler

    def start(self) -> None:
        image: Image.Image = load_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem("Open Settings", self._adapt(self._on_open_settings), default=True),
            pystray.MenuItem(
                self._update_text,
                self._update,
                visible=self._update_visible,
            ),
            pystray.MenuItem("Copy OBS URL", self._adapt(self._on_copy_url)),
            pystray.MenuItem("Copy OBS size", self._adapt(self._on_copy_size)),
            pystray.MenuItem("Preview Off", self._adapt(self._on_preview_off)),
            pystray.MenuItem("Open Overlay Preview", self._adapt(self._on_open_overlay)),
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
            pystray.MenuItem("Quit Velo", self._adapt(self._on_quit)),
        )
        self._icon = pystray.Icon("Velo", image, f"Velo {__version__}", menu)
        self._thread = threading.Thread(target=self._icon.run, name="velo-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except (RuntimeError, OSError, AttributeError) as exc:
                logger.debug("Could not stop tray icon cleanly: %s", exc)
        self._icon = None

    def notify(self, title: str, message: str) -> None:
        if not self._icon:
            return
        try:
            self._icon.notify(message, title)
        except (RuntimeError, OSError, AttributeError) as exc:
            logger.debug("Could not show tray notification: %s", exc)

    def refresh_menu(self) -> None:
        if not self._icon:
            return
        try:
            self._icon.update_menu()
        except (RuntimeError, OSError, AttributeError) as exc:
            logger.debug("Could not refresh tray menu: %s", exc)

    def set_tooltip(self, text: str) -> None:
        if not self._icon:
            return
        try:
            self._icon.title = text
        except (RuntimeError, OSError, AttributeError) as exc:
            logger.debug("Could not set tray tooltip: %s", exc)

    def _update_text(self, _item=None) -> str:
        if self._update_label_provider:
            try:
                label = self._update_label_provider()
                if label:
                    return label
            except Exception as exc:
                logger.debug("Update label provider failed: %s", exc)
        return "Update available..."

    def _update_visible(self, _item=None) -> bool:
        if not self._update_label_provider:
            return False
        try:
            return bool(self._update_label_provider())
        except Exception:
            return False

    def _update(self, _icon=None, _item=None) -> None:
        if self._on_open_update:
            self._on_open_update()
        else:
            self._on_open_settings()
