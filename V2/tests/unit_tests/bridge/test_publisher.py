"""Tests for V2/bridge/publisher.py — BRDG-02 publisher side (heartbeat loop, env ports, multipart publish)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import numpy as np
import pytest

from bridge.publisher import BridgePublisher
from bridge.schemas import SCHEMA_VERSION
from bridge.types import Bar, Tick


class TestEnvConfig:
    def test_default_ports(self, monkeypatch):
        for var in ("ZMQ_TICK_PORT", "ZMQ_BAR_PORT", "ZMQ_ORDER_PORT", "ZMQ_FILL_PORT"):
            monkeypatch.delenv(var, raising=False)
        p = BridgePublisher()
        assert p._tick_port == 5556
        assert p._bar_port == 5557
        assert p._order_port == 5558
        assert p._fill_port == 5559

    def test_env_ports_override(self, monkeypatch):
        monkeypatch.setenv("ZMQ_TICK_PORT", "6556")
        monkeypatch.setenv("ZMQ_BAR_PORT", "6557")
        monkeypatch.setenv("ZMQ_ORDER_PORT", "6558")
        monkeypatch.setenv("ZMQ_FILL_PORT", "6559")
        p = BridgePublisher()
        assert p._tick_port == 6556
        assert p._bar_port == 6557
        assert p._order_port == 6558
        assert p._fill_port == 6559


class TestHeartbeatInterval:
    def test_heartbeat_interval_is_5s(self):
        assert BridgePublisher.HEARTBEAT_INTERVAL == 5.0


class TestHeartbeatLoop:
    @pytest.mark.asyncio
    async def test_heartbeat_sends_on_tick_socket(self):
        p = BridgePublisher()
        p._tick_pub = AsyncMock()
        p._running = True
        # Shrink interval so test finishes quickly
        p._heartbeat_interval_seconds = 0.01

        async def stop_after_one_tick():
            await asyncio.sleep(0.03)
            p._running = False

        await asyncio.gather(p._heartbeat_loop(), stop_after_one_tick())
        # At least one heartbeat was sent
        assert p._tick_pub.send.await_count >= 1
        sent_bytes = p._tick_pub.send.await_args_list[0].args[0]
        decoded = msgpack.unpackb(sent_bytes)
        assert decoded["type"] == "heartbeat"
        assert decoded["schema_version"] == SCHEMA_VERSION

    @pytest.mark.asyncio
    async def test_heartbeat_loop_respects_running_flag(self):
        p = BridgePublisher()
        p._tick_pub = AsyncMock()
        p._running = False
        # Must return immediately
        await asyncio.wait_for(p._heartbeat_loop(), timeout=0.2)

    @pytest.mark.asyncio
    async def test_start_then_stop_toggles_running(self, monkeypatch):
        p = BridgePublisher()
        mock_ctx = MagicMock()
        mock_sock = MagicMock()
        mock_sock.bind = MagicMock()
        mock_sock.close = MagicMock()
        mock_ctx.socket = MagicMock(return_value=mock_sock)
        monkeypatch.setattr("zmq.asyncio.Context", MagicMock(return_value=mock_ctx))
        await p.start()
        assert p._running is True
        await p.stop()
        assert p._running is False


class TestPublishMultipart:
    @pytest.mark.asyncio
    async def test_publish_tick_sends_multipart(self):
        p = BridgePublisher()
        p._tick_pub = AsyncMock()
        tick = Tick(
            timestamp=np.datetime64("2026-04-23T10:00:00", "ns"),
            symbol="EURUSD", bid=1.1234, ask=1.1236,
            bid_volume=100.0, ask_volume=100.0, source="MT5",
        )
        await p.publish_tick(tick)
        p._tick_pub.send_multipart.assert_awaited_once()
        frames = p._tick_pub.send_multipart.await_args.args[0]
        assert frames[0] == b"EURUSD"
        # payload is msgpack tick — decode and check symbol
        assert msgpack.unpackb(frames[1])["sym"] == "EURUSD"

    @pytest.mark.asyncio
    async def test_publish_bar_sends_multipart(self):
        p = BridgePublisher()
        p._bar_pub = AsyncMock()
        bar = Bar(
            timestamp=np.datetime64("2026-04-23T10:00:00", "ns"),
            symbol="EURUSD",
            open=1.1, high=1.12, low=1.09, close=1.11,
            volume=1000, spread=2,
        )
        await p.publish_bar(bar)
        p._bar_pub.send_multipart.assert_awaited_once()
        frames = p._bar_pub.send_multipart.await_args.args[0]
        assert frames[0] == b"EURUSD"

    @pytest.mark.asyncio
    async def test_publish_bar_with_timeframe_includes_tf(self):
        p = BridgePublisher()
        p._bar_pub = AsyncMock()
        bar = Bar(
            timestamp=np.datetime64("2026-04-23T10:00:00", "ns"),
            symbol="EURUSD",
            open=1.1, high=1.12, low=1.09, close=1.11,
            volume=1000, spread=2,
        )
        await p.publish_bar(bar, timeframe="D1")
        frames = p._bar_pub.send_multipart.await_args.args[0]
        payload = msgpack.unpackb(frames[1])
        assert payload["tf"] == "D1"

    @pytest.mark.asyncio
    async def test_publish_tick_no_op_when_socket_none(self):
        p = BridgePublisher()
        p._tick_pub = None
        tick = Tick(
            timestamp=np.datetime64("2026-04-23T10:00:00", "ns"),
            symbol="EURUSD", bid=1.1, ask=1.11,
        )
        # Must not raise
        await p.publish_tick(tick)
