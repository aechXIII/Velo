"""Mouse capture to coalesced WebSocket event pipeline."""

from __future__ import annotations

import math
import queue
import threading
import time
from typing import Any, Dict, Optional, Tuple

from velo._win32 import HighResolutionWaiter
from velo.config import ConfigStore
from velo.constants import (
    IDLE_DECAY_FACTOR,
    IDLE_THRESHOLD,
    MAX_STATS_UPDATE_HZ,
    MIN_STATS_UPDATE_HZ,
    SMOOTHING_WEIGHT_NEW,
    SMOOTHING_WEIGHT_OLD,
    SPEED_SAMPLE_INTERVAL,
)
from velo.defaults import DEFAULTS
from velo.error_handling import safe_thread
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
        self._speed_sample_t: Optional[float] = None
        self._speed_sample_distance = 0.0
        self._stats_thread: Optional[threading.Thread] = None
        self._move_thread: Optional[threading.Thread] = None
        self._event_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._stats_waiter_lock = threading.Lock()
        self._stats_waiter: Optional[HighResolutionWaiter] = None
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
        self._stats_interval = IDLE_THRESHOLD

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
        with self._stats_waiter_lock:
            if self._stats_waiter is not None:
                self._stats_waiter.stop()
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
            sensitivity=float(snap.get("sensitivity") or 1.0),
        )
        hz = float(snap.get("ws_send_hz") or 120)
        fps = float(snap.get("target_fps") or 0)
        if fps > 0:
            hz = min(hz, max(fps * 2.0, 60.0))
        hz = max(30.0, min(hz, 240.0))
        self._min_move_interval = 1.0 / hz

        stats_hz = float(snap.get("stats_update_rate") or DEFAULTS["stats_update_rate"])
        stats_hz = max(MIN_STATS_UPDATE_HZ, min(stats_hz, MAX_STATS_UPDATE_HZ))
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
            self._speed_sample_t = None
            self._speed_sample_distance = 0.0
            snap = dict(self._stats)
        if self.server.client_count:
            self.server.broadcast_mouse({"type": "stats", "data": snap})
        return snap

    def _enqueue_mouse(self, ev: MouseEvent) -> None:
        self._ev_q.put_nowait(ev)

    @safe_thread("event")
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

    def _update_motion_stats_unlocked(self, dist: float, now: float) -> None:
        self._stats["distance"] += dist
        if self._speed_sample_t is None:
            self._speed_sample_t = now
        else:
            dt = now - self._speed_sample_t
            if dt > IDLE_THRESHOLD:
                self._speed_sample_t = now
                self._speed_sample_distance = 0.0
            else:
                self._speed_sample_distance += dist
                if dt >= SPEED_SAMPLE_INTERVAL:
                    speed = self._speed_sample_distance / dt
                    prev = self._stats["speed"]
                    self._stats["speed"] = prev * SMOOTHING_WEIGHT_NEW + speed * SMOOTHING_WEIGHT_OLD
                    self._stats["peak_speed"] = max(self._stats["peak_speed"], speed)
                    self._speed_sample_t = now
                    self._speed_sample_distance = 0.0
        self._last_t = now

    def _update_click_stats_unlocked(self, now: float) -> None:
        self._stats["clicks"] += 1
        self._click_times.append(now)
        cutoff = now - 1.0
        self._click_times = [t for t in self._click_times if t >= cutoff]
        self._stats["cps"] = float(len(self._click_times))

    def _update_stats_for_event(self, ev: MouseEvent, dist: float, now: float) -> None:
        with self._lock:
            if dist > 0.0:
                self._update_motion_stats_unlocked(dist, now)
            elif ev.x is not None:
                self._last_t = now
                if self._speed_sample_t is None:
                    self._speed_sample_t = now
            if ev.button_event and ev.button_event.endswith("_down"):
                self._update_click_stats_unlocked(now)

    def _emit_button_or_wheel_event(
        self, ev: MouseEvent, now: float, dx: float, dy: float
    ) -> None:
        with self._lock:
            self._acc_dx += dx
            self._acc_dy += dy
            self._acc_t = now
            self._acc_src = ev.source
            self._acc_buttons = ev.buttons
            self._has_pending_move = True
        self._flush_pending_move(force=True)
        payload: Dict[str, Any] = {
            "type": "mouse",
            "t": now,
            "dx": 0.0,
            "dy": 0.0,
            "btn": ev.button_event,
            "wheel": ev.wheel,
            "buttons": ev.buttons,
            "src": ev.source,
        }
        if ev.x is not None and ev.y is not None:
            payload["x"] = ev.x
            payload["y"] = ev.y
        self.server.broadcast_mouse(payload)

    def _accumulate_move_unlocked(self, ev: MouseEvent, now: float, dx: float, dy: float) -> None:
        self._acc_dx += dx
        self._acc_dy += dy
        self._acc_t = now
        self._acc_src = ev.source
        self._acc_buttons = ev.buttons
        if ev.x is not None and ev.y is not None:
            self._acc_x = ev.x
            self._acc_y = ev.y
        self._has_pending_move = True

    def _handle_mouse(self, ev: MouseEvent) -> None:
        now = ev.t
        dx = float(ev.dx)
        dy = float(ev.dy)
        stats_dx = dx if ev.raw_dx is None else float(ev.raw_dx)
        stats_dy = dy if ev.raw_dy is None else float(ev.raw_dy)
        dist = math.hypot(stats_dx, stats_dy)

        self._update_stats_for_event(ev, dist, now)

        if ev.button_event or ev.wheel:
            self._emit_button_or_wheel_event(ev, now, dx, dy)
            return

        if dist == 0 and ev.x is None:
            return

        with self._lock:
            self._accumulate_move_unlocked(ev, now, dx, dy)

    def _take_pending_move_unlocked(
        self, force: bool
    ) -> Optional[Tuple[float, float, float, Optional[str], int, Optional[float], Optional[float]]]:
        if not self._has_pending_move:
            return None
        now = time.perf_counter()
        if not force and (now - self._last_move_emit) < self._min_move_interval:
            return None
        dx, dy, t, src, buttons = (
            self._acc_dx,
            self._acc_dy,
            self._acc_t,
            self._acc_src,
            self._acc_buttons,
        )
        x, y = self._acc_x, self._acc_y
        self._acc_dx = 0.0
        self._acc_dy = 0.0
        self._acc_x = None
        self._acc_y = None
        self._has_pending_move = False
        self._last_move_emit = now
        return dx, dy, t, src, buttons, x, y

    def _flush_pending_move(self, force: bool = False) -> None:
        with self._lock:
            taken = self._take_pending_move_unlocked(force)
        if taken is None:
            return
        dx, dy, t, src, buttons, x, y = taken

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

    @safe_thread("drain")
    def _move_drain_loop(self) -> None:
        while not self._stop.is_set():
            self._flush_pending_move(force=False)
            self._stop.wait(self._min_move_interval)

    @safe_thread("stats")
    def _stats_loop(self) -> None:
        waiter = HighResolutionWaiter()
        try:
            with self._stats_waiter_lock:
                self._stats_waiter = waiter
                if self._stop.is_set():
                    waiter.stop()

            deadline = time.perf_counter()
            while not self._stop.is_set():
                interval = max(
                    1.0 / MAX_STATS_UPDATE_HZ,
                    float(self._stats_interval or IDLE_THRESHOLD),
                )
                now = time.perf_counter()
                deadline += interval
                if deadline <= now:
                    deadline = now + interval
                if waiter.wait(deadline - now):
                    break
                with self._lock:
                    if self._last_t is not None and (time.perf_counter() - self._last_t) > IDLE_DECAY_FACTOR:
                        self._stats["speed"] *= 0.5
                        if self._stats["speed"] < 1:
                            self._stats["speed"] = 0.0
                    stats = dict(self._stats)
                if self.server.client_count:
                    self.server.broadcast_mouse({"type": "stats", "data": stats})
        finally:
            with self._stats_waiter_lock:
                if self._stats_waiter is waiter:
                    self._stats_waiter = None
            waiter.close()
