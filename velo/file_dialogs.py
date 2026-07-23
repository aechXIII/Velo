"""Native open/save dialogs (tkinter)."""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional

_dialog_lock = threading.Lock()


def _documents_dir() -> str:
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents")
    return docs if os.path.isdir(docs) else home


def _run_tk_dialog(fn: Callable) -> Optional[str]:
    with _dialog_lock:
        try:
            import tkinter as tk
            from tkinter import TclError, filedialog
        except ImportError:
            return None

        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        try:
            root.attributes("-topmost", True)
        except TclError:
            pass
        path = None
        try:
            root.lift()
            path = fn(filedialog)
        except TclError:
            path = None
        finally:
            try:
                root.destroy()
            except TclError:
                pass
        if not path:
            return None
        path = str(path).strip().strip("\x00")
        return path or None


def save_json_dialog(
    title: str = "Export Velo settings",
    default_name: str = "velo-settings.json",
) -> Optional[str]:
    initial = _documents_dir()

    def _ask(filedialog):
        return filedialog.asksaveasfilename(
            title=title,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=initial,
            initialfile=default_name,
        )

    path = _run_tk_dialog(_ask)
    if not path:
        return None
    if not path.lower().endswith(".json"):
        path += ".json"
    return path


def open_json_dialog(title: str = "Import Velo settings") -> Optional[str]:
    initial = _documents_dir()

    def _ask(filedialog):
        return filedialog.askopenfilename(
            title=title,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=initial,
        )

    return _run_tk_dialog(_ask)
