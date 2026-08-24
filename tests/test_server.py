"""Tests for velo.server."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

import pytest

def _get_bound_port(server):
    if server._runner is not None:
        sites = getattr(server._runner, "sites", None) or getattr(server._runner, "_sites", None)
        if sites:
            for site in sites:
                srv = getattr(site, "_server", None)
                if srv is not None:
                    socks = srv.sockets
                    if socks:
                        return socks[0].getsockname()[1]
    return server.config.get("port")


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestVeloServer:

    def test_server_initializes_with_config(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        server = VeloServer(config)
        assert server.config is config
        assert not server.running
        assert server.client_count == 0

    def test_server_status_endpoint(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port(), "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            token = config.get("auth_token") or ""
            url = f"http://127.0.0.1:{port}/api/status?token={token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                assert data["ok"] is True
                assert "version" in data
        finally:
            server.stop()

    def test_server_config_endpoint(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port(), "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            token = config.get("auth_token") or ""
            url = f"http://127.0.0.1:{port}/api/config?token={token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                assert "host" in data
                assert "port" in data
        finally:
            server.stop()

    def test_diagnostics_and_default_export_do_not_expose_auth_token(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update(
            {
                "host": "127.0.0.1",
                "port": _free_port(),
                "auth_enabled": False,
                "auth_token": "private-token-value",
            },
            persist=False,
        )
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/config/export", timeout=5
            ) as response:
                exported = json.loads(response.read().decode("utf-8"))
            assert "auth_token" not in exported["bundle"]["config"]
            assert "host" not in exported["bundle"]["config"]
            assert "port" not in exported["bundle"]["config"]

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/diagnostics", timeout=5
            ) as response:
                diagnostics = json.loads(response.read().decode("utf-8"))
            assert diagnostics["ok"] is True
            assert "private-token-value" not in diagnostics["text"]
            assert "velo_version" in diagnostics["data"]
        finally:
            server.stop()

    def test_server_websocket_connect(self, tmp_path):
        import asyncio

        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port(), "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            import aiohttp

            port = _get_bound_port(server)
            token = config.get("auth_token") or ""

            async def _connect():
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"http://127.0.0.1:{port}/ws?token={token}") as ws:
                        msg = await ws.receive()
                        assert msg.type == aiohttp.WSMsgType.TEXT
                        data = json.loads(msg.data)
                        assert data["type"] == "hello"
                        assert data["app"] == "Velo"

            asyncio.run(_connect())
        finally:
            server.stop()

    def test_websocket_persists_hud_position(self, tmp_path):
        import asyncio
        import aiohttp

        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port()}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            token = config.get("auth_token")

            async def _update():
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        f"http://127.0.0.1:{port}/ws?token={token}"
                    ) as ws:
                        await ws.receive()
                        await ws.send_json(
                            {
                                "type": "config",
                                "data": {"stats_x_pct": 42.5, "stats_y_pct": 37.0},
                            }
                        )
                        for _ in range(10):
                            message = await asyncio.wait_for(ws.receive(), timeout=1)
                            if message.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(message.data)
                                if payload.get("type") == "config":
                                    break

            asyncio.run(_update())
            assert config.get("stats_x_pct") == 42.5
            assert config.get("stats_y_pct") == 37.0
        finally:
            server.stop()

    def test_server_stop_removes_config_listener(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        server = VeloServer(config)
        assert len(config._listeners) == 1
        server.stop()
        assert len(config._listeners) == 0

    def test_authenticated_api_rejects_invalid_config(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port()}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{config.get('port')}/api/config",
                data=json.dumps({"port": "oops"}).encode(),
                headers={
                    "Authorization": f"Bearer {config.get('auth_token')}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=5)
            assert error.value.code == 400
            assert config.get("port") != "oops"
        finally:
            server.stop()

    def test_choosing_background_image_enables_it(self, tmp_path, monkeypatch):
        from PIL import Image

        from velo.config import ConfigStore
        from velo.server import VeloServer

        image_path = tmp_path / "background.gif"
        with Image.new("RGB", (2, 2), "red") as image:
            image.save(image_path, format="GIF")
        monkeypatch.setattr(
            "velo.server.open_image_dialog", lambda _title: str(image_path)
        )
        config = ConfigStore(
            path=tmp_path / "config.json", presets_path=tmp_path / "presets"
        )
        config.update(
            {"host": "127.0.0.1", "port": _free_port(), "auth_enabled": False},
            persist=False,
        )
        server = VeloServer(config)
        server.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{_get_bound_port(server)}/api/config/bg-image-dialog",
                data=b"",
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

            assert data["data"]["pad_bg_image_enabled"] is True
            assert data["data"]["pad_bg_image_zoom"] == 1.0
            assert data["data"]["pad_bg_image_pos_x"] == 50.0
            assert data["data"]["pad_bg_image_pos_y"] == 50.0
            assert config.get("pad_bg_image_enabled") is True
            assert config.get("pad_bg_image") == data["data"]["pad_bg_image"]
        finally:
            server.stop()

    def test_onboarding_endpoint_requires_auth(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "127.0.0.1", "port": _free_port()}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            url = f"http://127.0.0.1:{config.get('port')}/api/onboarding"
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(url, timeout=5)
            assert error.value.code == 401
        finally:
            server.stop()
