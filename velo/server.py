"""HTTP + WebSocket server for overlay, config UI, and live config."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from aiohttp import WSMsgType, web

from velo.config import APP_VERSION, PRESET_EXCLUDE, ConfigStore
from velo.config_types import ConfigMap
from velo.file_dialogs import open_json_dialog, save_json_dialog

RestartCallback = Callable[[], None]
StatsResetCallback = Callable[[], ConfigMap]
ShowSettingsCallback = Callable[[], None]
JsonDict = Dict[str, Any]


def _app_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


ROOT = _app_root()
OVERLAY_DIR = ROOT / "overlay"
CONFIG_UI_DIR = ROOT / "config_ui"


def _clean_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    cleaned = str(path).replace("\x00", "").strip()
    return cleaned or None


class VeloServer:
    def __init__(self, config: ConfigStore) -> None:
        self.config = config
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._runner: Optional[web.AppRunner] = None
        self._clients: Set[web.WebSocketResponse] = set()
        self._lock = threading.Lock()
        self._running = False
        self._started_at = 0.0
        self._event_count = 0
        self._last_error: Optional[str] = None
        self._stop_flag = threading.Event()
        self._restart_callback: Optional[RestartCallback] = None
        self._stats_reset_callback: Optional[StatsResetCallback] = None
        self._show_settings_callback: Optional[ShowSettingsCallback] = None
        self._pending_move_msg: Optional[str] = None
        self._pending_msgs: List[str] = []
        self._flush_scheduled = False
        self._capture_running = False
        self._capture_error: Optional[str] = None
        self.config.on_change(self._on_config_change)

    def set_restart_callback(self, cb: RestartCallback) -> None:
        self._restart_callback = cb

    def set_stats_reset_callback(self, cb: StatsResetCallback) -> None:
        self._stats_reset_callback = cb

    def set_show_settings_callback(self, cb: ShowSettingsCallback) -> None:
        self._show_settings_callback = cb

    @property
    def running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._last_error = None
        self._thread = threading.Thread(
            target=self._run_loop, name="velo-server", daemon=True
        )
        self._thread.start()
        for _ in range(80):
            if self._running or self._last_error:
                break
            time.sleep(0.025)

    def stop(self) -> None:
        self._stop_flag.set()
        try:
            self.config.remove_listener(self._on_config_change)
        except ValueError:
            pass
        if self._loop and self._runner:

            async def _shutdown() -> None:
                with self._lock:
                    clients = list(self._clients)
                for ws in clients:
                    try:
                        await ws.close(code=1001, message=b"server stop")
                    except (ConnectionError, RuntimeError, OSError):
                        pass
                if self._runner:
                    await self._runner.cleanup()

            try:
                fut = asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
                fut.result(timeout=3.0)
            except (TimeoutError, RuntimeError, OSError):
                pass
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except RuntimeError:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._running = False
        self._thread = None
        self._runner = None
        self._loop = None

    def broadcast_mouse(self, payload: ConfigMap) -> None:
        if not self._loop or not self._running:
            return
        self._event_count += 1
        msg = json.dumps(payload, separators=(",", ":"))
        is_move = (
            payload.get("type") == "mouse"
            and not payload.get("btn")
            and not payload.get("wheel")
        )
        self._enqueue_outbox(msg, coalesce_move=is_move)

    def broadcast_config(self, snap: Optional[ConfigMap] = None) -> None:
        public = (
            self.config.overlay_public()
            if snap is None
            else {k: v for k, v in snap.items() if k != "auth_token"}
        )
        payload = {"type": "config", "data": public}
        if not self._loop or not self._running:
            return
        msg = json.dumps(payload, separators=(",", ":"))
        self._enqueue_outbox(msg, coalesce_move=False)

    def _enqueue_outbox(self, msg: str, coalesce_move: bool) -> None:
        with self._lock:
            if coalesce_move:
                self._pending_move_msg = msg
            else:
                self._pending_msgs.append(msg)
            need = not self._flush_scheduled
            if need:
                self._flush_scheduled = True
        if not need:
            return
        try:
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._kick_flush)
        except RuntimeError:
            with self._lock:
                self._flush_scheduled = False

    def _kick_flush(self) -> None:
        if not self._loop:
            return
        asyncio.create_task(self._flush_outbox())

    async def _flush_outbox(self) -> None:
        while True:
            with self._lock:
                msgs = self._pending_msgs
                self._pending_msgs = []
                move = self._pending_move_msg
                self._pending_move_msg = None
                if not msgs and move is None:
                    self._flush_scheduled = False
                    return
            if move is not None:
                msgs.append(move)
            for msg in msgs:
                await self._broadcast_raw(msg)

    def _on_config_change(self, snap: ConfigMap) -> None:
        self.broadcast_config(snap)

    async def _broadcast_raw(self, msg: str) -> None:
        with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        dead: List[web.WebSocketResponse] = []
        for ws in clients:
            try:
                await ws.send_str(msg)
            except (ConnectionError, RuntimeError, OSError):
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._start_app())
            self._running = True
            self._started_at = time.time()
            while not self._stop_flag.is_set():
                self._loop.run_forever()
                break
        except OSError as exc:
            self._last_error = str(exc)
            self._running = False
        except Exception as exc:
            self._last_error = str(exc)
            self._running = False
        finally:
            try:
                if self._runner and self._loop:
                    self._loop.run_until_complete(self._runner.cleanup())
            except (RuntimeError, OSError):
                pass
            try:
                if self._loop:
                    self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except RuntimeError:
                pass
            if self._loop:
                self._loop.close()
            self._loop = None
            self._running = False

    async def _start_app(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._handle_root)
        app.router.add_get("/config", self._handle_config_ui)
        app.router.add_get("/config/", self._handle_config_ui)
        app.router.add_get("/overlay", self._handle_overlay)
        app.router.add_get("/overlay/", self._handle_overlay)
        app.router.add_get("/static/{path:.*}", self._handle_static)
        app.router.add_get("/ui/{path:.*}", self._handle_config_static)
        app.router.add_get("/api/config", self._handle_api_config_get)
        app.router.add_post("/api/config", self._handle_api_config_post)
        app.router.add_post("/api/config/reset", self._handle_api_config_reset)
        app.router.add_post("/api/config/reset-visuals", self._handle_api_config_reset_visuals)
        app.router.add_get("/api/config/export", self._handle_api_config_export)
        app.router.add_post("/api/config/export-dialog", self._handle_api_config_export_dialog)
        app.router.add_post("/api/config/import", self._handle_api_config_import)
        app.router.add_post("/api/config/import-dialog", self._handle_api_config_import_dialog)
        app.router.add_post("/api/config/preset", self._handle_api_preset)
        app.router.add_get("/api/presets", self._handle_api_presets)
        app.router.add_post("/api/presets/save", self._handle_api_presets_save)
        app.router.add_post("/api/presets/update", self._handle_api_presets_update)
        app.router.add_post("/api/presets/delete", self._handle_api_presets_delete)
        app.router.add_post("/api/presets/rename", self._handle_api_presets_rename)
        app.router.add_post("/api/presets/export-dialog", self._handle_api_presets_export_dialog)
        app.router.add_post("/api/presets/import-dialog", self._handle_api_presets_import_dialog)
        app.router.add_post("/api/presets/share", self._handle_api_presets_share)
        app.router.add_post("/api/presets/import-share", self._handle_api_presets_import_share)
        app.router.add_post("/api/server/restart", self._handle_api_restart)
        app.router.add_post("/api/stats/reset", self._handle_api_stats_reset)
        app.router.add_post("/api/app/show", self._handle_api_app_show)
        app.router.add_get("/api/health", self._handle_health)
        app.router.add_get("/api/status", self._handle_status)
        app.router.add_get("/ws", self._handle_ws)

        host = self.config.get("host") or "127.0.0.1"
        port = int(self.config.get("port") or 27180)

        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host, port)
        try:
            await site.start()
        except OSError as exc:
            self._last_error = f"Failed to bind {host}:{port}: {exc}"
            raise

    def _token_ok(self, request: web.Request) -> bool:
        if not self.config.get("auth_enabled"):
            return True
        expected = self.config.get("auth_token") or ""
        if not expected:
            return True
        got = request.rel_url.query.get("token", "")
        if got == expected:
            return True
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth[7:] == expected:
            return True
        return False

    def _unauthorized(self) -> web.Response:
        return web.Response(text="Unauthorized", status=401)

    async def _require_auth(self, request: web.Request) -> Optional[web.Response]:
        if not self._token_ok(request):
            return self._unauthorized()
        return None

    async def _read_json_object(
        self, request: web.Request
    ) -> Tuple[Optional[JsonDict], Optional[web.Response]]:
        try:
            body = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
            return None, web.json_response({"ok": False, "error": "invalid json"}, status=400)
        if not isinstance(body, dict):
            return None, web.json_response(
                {"ok": False, "error": "expected object"}, status=400
            )
        return body, None

    async def _read_json_optional(self, request: web.Request) -> JsonDict:
        try:
            body = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
            return {}
        return body if isinstance(body, dict) else {}

    async def _run_dialog(
        self, fn: Callable[[], Optional[str]]
    ) -> Union[str, web.Response]:
        loop = asyncio.get_running_loop()
        try:
            path = await loop.run_in_executor(None, fn)
        except (OSError, RuntimeError) as exc:
            return web.json_response(
                {"ok": False, "error": f"file dialog: {exc}"}, status=500
            )
        cleaned = _clean_path(path)
        if not cleaned:
            return web.json_response({"ok": False, "cancelled": True})
        return cleaned

    def _preset_list_payload(self) -> JsonDict:
        info = self.config.list_presets()
        names = [p["name"] for p in info["builtin"]] + [p["name"] for p in info["user"]]
        return {
            "ok": True,
            "presets": names,
            "exclude_keys": sorted(PRESET_EXCLUDE),
            **info,
        }

    def _ok_snap(self, snap: ConfigMap, **extra: Any) -> web.Response:
        body: JsonDict = {"ok": True, "data": snap}
        body.update(extra)
        return web.json_response(body)

    async def _handle_root(self, request: web.Request) -> web.StreamResponse:
        raise web.HTTPFound("/config")

    async def _handle_overlay(self, request: web.Request) -> web.StreamResponse:
        path = OVERLAY_DIR / "index.html"
        if not path.is_file():
            return web.Response(text="Overlay not found", status=404)
        return web.FileResponse(
            path,
            headers={"Cache-Control": "no-store", "Content-Type": "text/html; charset=utf-8"},
        )

    async def _handle_config_ui(self, request: web.Request) -> web.StreamResponse:
        path = CONFIG_UI_DIR / "index.html"
        if not path.is_file():
            return web.Response(text="Config UI not found", status=404)
        return web.FileResponse(
            path,
            headers={"Cache-Control": "no-store", "Content-Type": "text/html; charset=utf-8"},
        )

    async def _handle_static(self, request: web.Request) -> web.StreamResponse:
        return self._safe_file(OVERLAY_DIR, request.match_info.get("path", ""))

    async def _handle_config_static(self, request: web.Request) -> web.StreamResponse:
        return self._safe_file(CONFIG_UI_DIR, request.match_info.get("path", ""))

    def _safe_file(self, root: Path, rel: str) -> web.StreamResponse:
        target = (root / rel).resolve()
        base = root.resolve()
        if not str(target).startswith(str(base)) or not target.is_file():
            return web.Response(text="Not found", status=404)
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix.lower() == ".js" and "javascript" not in ctype:
            ctype = "application/javascript"
        return web.FileResponse(
            target, headers={"Content-Type": ctype, "Cache-Control": "no-store"}
        )

    async def _handle_api_config_get(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        return web.json_response(self.config.snapshot())

    async def _handle_api_config_post(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        patch, err = await self._read_json_object(request)
        if err:
            return err
        assert patch is not None
        return self._ok_snap(self.config.update(patch, persist=True))

    async def _handle_api_config_reset(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        return self._ok_snap(self.config.reset_defaults(keep_auth=True))

    async def _handle_api_config_reset_visuals(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        return self._ok_snap(self.config.reset_visuals())

    async def _handle_api_config_export(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        include = request.rel_url.query.get("connection", "1") not in ("0", "false", "no")
        return web.json_response(
            {"ok": True, "bundle": self.config.export_bundle(include_connection=include)}
        )

    async def _handle_api_config_export_dialog(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body = await self._read_json_optional(request)
        include = bool(body.get("include_connection", True))
        result = await self._run_dialog(
            lambda: save_json_dialog("Export Velo settings", "velo-settings.json")
        )
        if isinstance(result, web.Response):
            return result
        try:
            bundle = self.config.export_bundle(include_connection=include)
            Path(result).write_text(
                json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)
        return web.json_response({"ok": True, "path": result})

    async def _handle_api_config_import(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        include = bool(body.get("include_connection"))
        payload = body.get("bundle") if "bundle" in body else body
        try:
            snap = self.config.import_bundle(payload, include_connection=include)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return self._ok_snap(snap)

    async def _handle_api_config_import_dialog(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body = await self._read_json_optional(request)
        include = bool(body.get("include_connection"))
        result = await self._run_dialog(lambda: open_json_dialog("Import Velo settings"))
        if isinstance(result, web.Response):
            return result
        try:
            raw = Path(result).read_text(encoding="utf-8-sig")
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        try:
            snap = self.config.import_bundle(payload, include_connection=include)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return self._ok_snap(snap, path=result)

    async def _handle_api_presets(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        return web.json_response(self._preset_list_payload())

    async def _handle_api_preset(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        name = str(body.get("name") or "")
        if not name:
            return web.json_response({"ok": False, "error": "name required"}, status=400)
        kind = body.get("kind")
        return self._ok_snap(self.config.apply_preset(name, kind=kind))

    async def _preset_mutate(
        self,
        request: web.Request,
        action: Callable[[JsonDict], ConfigMap],
    ) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        try:
            snap = action(body)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return self._ok_snap(snap, presets=self.config.list_presets())

    async def _handle_api_presets_save(self, request: web.Request) -> web.Response:
        def action(body: JsonDict) -> ConfigMap:
            return self.config.save_user_preset(
                str(body.get("name") or ""),
                overwrite=bool(body.get("overwrite")),
            )

        return await self._preset_mutate(request, action)

    async def _handle_api_presets_update(self, request: web.Request) -> web.Response:
        def action(body: JsonDict) -> ConfigMap:
            return self.config.update_user_preset(str(body.get("name") or ""))

        return await self._preset_mutate(request, action)

    async def _handle_api_presets_delete(self, request: web.Request) -> web.Response:
        def action(body: JsonDict) -> ConfigMap:
            return self.config.delete_user_preset(str(body.get("name") or ""))

        return await self._preset_mutate(request, action)

    async def _handle_api_presets_rename(self, request: web.Request) -> web.Response:
        def action(body: JsonDict) -> ConfigMap:
            old_name = str(body.get("old_name") or body.get("name") or "")
            new_name = str(body.get("new_name") or "")
            return self.config.rename_user_preset(old_name, new_name)

        return await self._preset_mutate(request, action)

    async def _handle_api_presets_export_dialog(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        name = str(body.get("name") or "")
        kind = body.get("kind")
        try:
            payload = self.config.export_preset_payload(name, kind)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name).strip("_") or "preset"
        default_name = f"velo-preset-{safe}.json"
        result = await self._run_dialog(lambda: save_json_dialog("Export preset", default_name))
        if isinstance(result, web.Response):
            return result
        try:
            Path(result).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)
        return web.json_response({"ok": True, "path": result})

    async def _handle_api_presets_import_dialog(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        result = await self._run_dialog(lambda: open_json_dialog("Import preset"))
        if isinstance(result, web.Response):
            return result
        try:
            raw = Path(result).read_text(encoding="utf-8-sig")
            decoded = self.config.decode_preset_share(raw)
            snap = self.config.import_preset_payload(decoded, overwrite=False)
        except (OSError, UnicodeError) as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return self._ok_snap(snap, presets=self.config.list_presets(), path=result)

    async def _handle_api_presets_share(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        try:
            code = self.config.encode_preset_share(
                str(body.get("name") or ""), body.get("kind")
            )
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return web.json_response({"ok": True, "code": code})

    async def _handle_api_presets_import_share(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        body, err = await self._read_json_object(request)
        if err:
            return err
        assert body is not None
        text = str(body.get("text") or body.get("code") or "")
        name = body.get("name")
        try:
            decoded = self.config.decode_preset_share(text)
            if name:
                decoded["name"] = name
            snap = self.config.import_preset_payload(decoded, overwrite=False)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return self._ok_snap(snap, presets=self.config.list_presets())

    async def _handle_api_restart(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        if self._restart_callback:
            threading.Thread(target=self._restart_callback, daemon=True).start()
            return web.json_response({"ok": True, "message": "restarting"})
        return web.json_response({"ok": False, "error": "no restart handler"}, status=500)

    async def _handle_api_stats_reset(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        if not self._stats_reset_callback:
            return web.json_response({"ok": False, "error": "no stats handler"}, status=500)
        try:
            data = self._stats_reset_callback()
        except (RuntimeError, ValueError, OSError) as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)
        return web.json_response({"ok": True, "data": data})

    async def _handle_api_app_show(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        if not self._show_settings_callback:
            return web.json_response({"ok": False, "error": "no show handler"}, status=500)
        try:
            self._show_settings_callback()
        except (RuntimeError, OSError, AttributeError) as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)
        return web.json_response({"ok": True})

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response(
            {
                "ok": True,
                "app": "Velo",
                "version": APP_VERSION,
                "running": self._running,
                "clients": self.client_count,
                "events": self._event_count,
                "uptime": time.time() - self._started_at if self._started_at else 0,
                "error": self._last_error,
            }
        )

    def set_runtime_status(
        self, *, capture_running: bool = False, capture_error: Optional[str] = None
    ) -> None:
        self._capture_running = capture_running
        self._capture_error = capture_error

    async def _handle_status(self, request: web.Request) -> web.Response:
        denied = await self._require_auth(request)
        if denied:
            return denied
        return web.json_response(
            {
                "ok": True,
                "running": self._running,
                "clients": self.client_count,
                "events": self._event_count,
                "overlay_url": self.config.overlay_url(),
                "config_url": self.config.config_url(),
                "error": self._last_error,
                "capture_running": self._capture_running,
                "capture_error": self._capture_error,
                "version": APP_VERSION,
                "exclude_keys": sorted(PRESET_EXCLUDE),
            }
        )

    async def _handle_ws(self, request: web.Request) -> web.StreamResponse:
        if not self._token_ok(request):
            return self._unauthorized()

        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)

        with self._lock:
            self._clients.add(ws)

        public = self.config.overlay_public()
        await ws.send_str(
            json.dumps(
                {
                    "type": "hello",
                    "app": "Velo",
                    "version": APP_VERSION,
                    "data": public,
                },
                separators=(",", ":"),
            )
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "get_config":
                        await ws.send_str(
                            json.dumps(
                                {"type": "config", "data": self.config.overlay_public()},
                                separators=(",", ":"),
                            )
                        )
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            with self._lock:
                self._clients.discard(ws)
        return ws
