"""Icon loading and fallback generation."""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from typing import Tuple, Union

from PIL import Image, ImageDraw


def make_icon(size: int = 64, accent: Tuple[int, int, int] = (91, 140, 255)) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=size // 5,
        fill=(14, 16, 22, 255),
    )
    colors = [
        (59, 130, 246, 220),
        (34, 197, 94, 230),
        (234, 179, 8, 240),
        (239, 68, 68, 255),
    ]
    cx, cy = size * 0.28, size * 0.62
    for i, col in enumerate(colors):
        t = (i + 1) / len(colors)
        x1 = cx + size * 0.08 * i
        y1 = cy - size * 0.1 * i
        x2 = x1 + size * 0.22
        y2 = y1 - size * 0.18
        width = max(2, int(size * (0.06 + t * 0.04)))
        draw.line([(x1, y1), (x2, y2)], fill=col, width=width)
    r = max(2, size // 12)
    dx, dy = size * 0.72, size * 0.28
    draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(255, 255, 255, 240))
    return img


def icon_bytes(size: int = 64) -> bytes:
    buf = BytesIO()
    make_icon(size).save(buf, format="PNG")
    return buf.getvalue()


def write_ico(
    path: Union[str, Path],
    sizes: Tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256),
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = make_icon(max(sizes)).convert("RGBA")
    img.save(out, format="ICO", sizes=[(s, s) for s in sizes])
    return out


def _app_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def load_icon(size: int = 64) -> Image.Image:
    try:
        ico_path = _app_root() / "assets" / "velo.ico"
        img = Image.open(ico_path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        return img
    except Exception:
        return make_icon(size)
