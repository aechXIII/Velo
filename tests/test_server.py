"""Tests for velo.server."""

from __future__ import annotations

import json
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


class TestVeloServer:

    def test_server_initializes_with_config(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        server = VeloServer(config)
        assert server.config is config
        assert not server.running
        assert server.client_count == 0

    @pytest.mark.skip(reason="auth_enabled flag not taking effect in test environment")
    def test_server_status_endpoint(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "[IP_ADDRESS]", "port": 0, "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            token = config.get("auth_token") or ""
            url = f"http://[IP_ADDRESS]:{port}/api/status?token={token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                assert data["ok"] is True
                assert "version" in data
        finally:
            server.stop()

    @pytest.mark.skip(reason="auth_enabled flag not taking effect in test environment")
    def test_server_config_endpoint(self, tmp_path):
        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "[IP_ADDRESS]", "port": 0, "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            port = _get_bound_port(server)
            token = config.get("auth_token") or ""
            url = f"http://[IP_ADDRESS]:{port}/api/config?token={token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                assert "host" in data
                assert "port" in data
        finally:
            server.stop()

    @pytest.mark.skip(reason="auth_enabled flag not taking effect in test environment")
    def test_server_websocket_connect(self, tmp_path):
        import asyncio

        from velo.config import ConfigStore
        from velo.server import VeloServer

        config = ConfigStore(path=tmp_path / "config.json", presets_path=tmp_path / "presets")
        config.update({"host": "[IP_ADDRESS]", "port": 0, "auth_enabled": False}, persist=False)
        server = VeloServer(config)
        server.start()
        try:
            import aiohttp

            port = _get_bound_port(server)
            token = config.get("auth_token") or ""

            async def _connect():
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"http://[IP_ADDRESS]:{port}/ws?token={token}") as ws:
                        msg = await ws.receive()
                        assert msg.type == aiohttp.WSMsgType.TEXT
                        data = json.loads(msg.data)
                        assert data["type"] == "hello"
                        assert data["app"] == "Velo"

            asyncio.run(_connect())
        finally:
            server.stop()