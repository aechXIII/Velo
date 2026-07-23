"""Mouse capture to coalesced WebSocket event pipeline."""

from __future__ import annotations

import math
import queue
import threading
import time
from typing import Any, Dict, Optional

from velo.config import ConfigStore
from velo.defaults import STATS_UPDATE_HZ
from velo.mouse_capture import MouseCapture, MouseEvent
from velo.server import VeloServer


class EventPipeline:
    def __init__(
        self,
        config: ConfigStore,
        capture: MouseCapture,
        server: VeloServer,
    ) -> None:
        self.config = config
        self.capture = capture
        self.server = server
        self._lock = threading.Lock()
        self._stats = {
            "speed": 0.0,
            "peak_speed": 0.0,
            "distance": 0.0,
            "cps": 0.0,
            "clicks": 0,
        }
        self._click_times: list = []
        self._last_t: Optional[float] = None
        self._stats_thread: Optional[threading.Thread] = None
        self._move_thread: Optional[threading.Thread] = None
        self._event_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ev_q: queue.SimpleQueue = queue.SimpleQueue()
        self._last_move_emit = 0.0
        self._acc_dx = 0.0
        self._acc_dy = 0.0
        self._acc_t = 0.0
        self._acc_src: Optional[str] = None
        self._acc_x: Optional[float] = None
        self._acc_y: Optional[float] = None
        self._acc_buttons = 0
        self._has_pending_move = False
        self._min_move_interval = 1.0 / 120.0
        self._stats_interval = 0.25

    def start(self) -> None:
        self.capture.add_listener(self._enqueue_mouse)
        self._apply_capture_config()
        self.config.on_change(lambda _s: self._apply_capture_config())
        self.capture.start()
        self._stop.clear()
        self._event_thread = threading.Thread(
            target=self._event_loop, name="velo-events", daemon=True
        )
        self._event_thread.start()
        self._stats_thread = threading.Thread(
            target=self._stats_loop, name="velo-stats", daemon=True
        )
        self._stats_thread.start()
        self._move_thread = threading.Thread(
            target=self._move_drain_loop, name="velo-moves", daemon=True
        )
        self._move_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.capture.remove_listener(self._enqueue_mouse)
        self.capture.stop()
        self._flush_pending_move(force=True)
        for th in (self._event_thread, self._stats_thread, self._move_thread):
            if th and th.is_alive():
                th.join(timeout=1.0)

    def _apply_capture_config(self) -> None:
        snap = self.config.snapshot()
        self.capture.configure(
            mode=snap.get("capture_mode", "relative"),
            invert_y=bool(snap.get("invert_y", False)),
            sensitivity=1.0,
        )
        hz = float(snap.get("ws_send_hz") or 120)
        fps = float(snap.get("target_fps") or 0)
        if fps > 0:
            hz = min(hz, max(fps * 2.0, 60.0))
        hz = max(30.0, min(hz, 240.0))
        self._min_move_interval = 1.0 / hz

        rate = str(snap.get("stats_update_rate") or "normal").strip().lower()
        stats_hz = float(STATS_UPDATE_HZ.get(rate, STATS_UPDATE_HZ["normal"]))
        stats_hz = max(1.0, min(stats_hz, 30.0))
        self._stats_interval = 1.0 / stats_hz

    def stats_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def reset_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._stats = {
                "speed": 0.0,
                "peak_speed": 0.0,
                "distance": 0.0,
                "cps": 0.0,
                "clicks": 0,
            }
            self._click_times = []
            self._last_t = None
            snap = dict(self._stats)
        if self.server.client_count:
            self.server.broadcast_mouse({"type": "stats", "data": snap})
        return snap

    def _enqueue_mouse(self, ev: MouseEvent) -> None:
        self._ev_q.put_nowait(ev)

    def _event_loop(self) -> None:
        while not self._stop.is_set():
            try:
                ev = self._ev_q.get(timeout=0.01)
            except queue.Empty:
                continue
            self._handle_mouse(ev)
            while True:
                try:
                    ev = self._ev_q.get_nowait()
                except queue.Empty:
                    break
                self._handle_mouse(ev)

    def _handle_mouse(self, ev: MouseEvent) -> None:
        now = ev.t
        dx = float(ev.dx)
        dy = float(ev.dy)
        dist = math.hypot(dx, dy)

        with self._lock:
            if dist > 0.0:
                self._stats["distance"] += dist
                if self._last_t is not None:
                    dt = now - self._last_t
                    if dt > 1e-6:
                        speed = dist / dt
                        prev = self._stats["speed"]
                        self._stats["speed"] = prev * 0.65 + speed * 0.35
                        if speed > self._stats["peak_speed"]:
                            self._stats["peak_speed"] = speed
                self._last_t = now
            elif ev.x is not None:
                self._last_t = now

            if ev.button_event and ev.button_event.endswith("_down"):
                self._stats["clicks"] += 1
                self._click_times.append(now)
                cutoff = now - 1.0
                self._click_times = [t for t in self._click_times if t >= cutoff]
                self._stats["cps"] = float(len(self._click_times))

        if ev.button_event or ev.wheel:
            self._flush_pending_move(force=True)
            payload: Dict[str, Any] = {
                "type": "mouse",
                "t": now,
                "dx": round(dx, 3),
                "dy": round(dy, 3),
                "btn": ev.button_event,
                "wheel": ev.wheel,
                "buttons": ev.buttons,
                "src": ev.source,
            }
            if ev.x is not None and ev.y is not None:
                payload["x"] = ev.x
                payload["y"] = ev.y
            self.server.broadcast_mouse(payload)
            return

        if dist == 0 and ev.x is None:
            return

        with self._lock:
            self._acc_dx += dx
            self._acc_dy += dy
            self._acc_t = now
            self._acc_src = ev.source
            self._acc_buttons = ev.buttons
            if ev.x is not None and ev.y is not None:
                self._acc_x = ev.x
                self._acc_y = ev.y
            self._has_pending_move = True

    def _flush_pending_move(self, force: bool = False) -> None:
        with self._lock:
            if not self._has_pending_move:
                return
            now = time.perf_counter()
            if not force and (now - self._last_move_emit) < self._min_move_interval:
                return
            dx = self._acc_dx
            dy = self._acc_dy
            t = self._acc_t
            src = self._acc_src
            buttons = self._acc_buttons
            x, y = self._acc_x, self._acc_y
            self._acc_dx = 0.0
            self._acc_dy = 0.0
            self._acc_x = None
            self._acc_y = None
            self._has_pending_move = False
            self._last_move_emit = now

        if dx == 0.0 and dy == 0.0 and x is None:
            return

        payload: Dict[str, Any] = {
            "type": "mouse",
            "t": t,
            "dx": round(dx, 3),
            "dy": round(dy, 3),
            "src": src,
        }
        if x is not None and y is not None:
            payload["x"] = x
            payload["y"] = y
        if buttons:
            payload["buttons"] = buttons
        self.server.broadcast_mouse(payload)

    def _move_drain_loop(self) -> None:
        while not self._stop.is_set():
            self._flush_pending_move(force=False)
            self._stop.wait(self._min_move_interval)

    def _stats_loop(self) -> None:
        while not self._stop.is_set():
            interval = max(0.03, float(self._stats_interval or 0.25))
            if self._stop.wait(interval):
                break
            with self._lock:
                if self._last_t is not None and (time.perf_counter() - self._last_t) > 0.12:
                    self._stats["speed"] *= 0.5
                    if self._stats["speed"] < 1:
                        self._stats["speed"] = 0.0
                stats = dict(self._stats)
            if self.server.client_count:
                self.server.broadcast_mouse({"type": "stats", "data": stats})
