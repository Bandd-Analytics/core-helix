"""Tests for V2/bridge/consumer.py — BRDG-02 (heartbeat + stale detection + reconnect)."""

from __future__ import annotations

import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest

from bridge.consumer import BridgeConsumer
from bridge.schemas import SCHEMA_VERSION, pack_heartbeat


class TestStaleDetection:
    def test_is_stale_true_initially(self):
        c = BridgeConsumer()
        assert c.is_stale is True

    def test_is_stale_false_after_heartbeat(self):
        c = BridgeConsumer()
        c._last_heartbeat = time.monotonic()
        assert c.is_stale is False

    def test_is_stale_true_after_10s(self):
        c = BridgeConsumer()
        c._last_heartbeat = time.monotonic() - 11.0
        assert c.is_stale is True

    def test_stale_threshold_is_10(self):
        assert BridgeConsumer.STALE_THRESHOLD == 10.0


class TestReconnectBackoff:
    def test_delay_schedule(self):
        c = BridgeConsumer()
        expected = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
        for i, exp in enumerate(expected):
            c._reconnect_attempt = i
            assert c._get_reconnect_delay() == exp

    def test_delay_caps_at_30s(self):
        c = BridgeConsumer()
        c._reconnect_attempt = 10
        assert c._get_reconnect_delay() == 30.0

    def test_reconnect_delays_constant_value(self):
        assert BridgeConsumer.RECONNECT_DELAYS == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]


class TestEnvConfig:
    def test_default_host(self, monkeypatch):
        monkeypatch.delenv("BRIDGE_HOST", raising=False)
        c = BridgeConsumer()
        assert c._host == "10.200.0.1"

    def test_env_host_override(self, monkeypatch):
        monkeypatch.setenv("BRIDGE_HOST", "10.99.99.99")
        c = BridgeConsumer()
        assert c._host == "10.99.99.99"

    def test_default_ports(self, monkeypatch):
        for var in ("ZMQ_TICK_PORT", "ZMQ_BAR_PORT", "ZMQ_ORDER_PORT", "ZMQ_FILL_PORT"):
            monkeypatch.delenv(var, raising=False)
        c = BridgeConsumer()
        assert c._tick_port == 5556
        assert c._bar_port == 5557
        assert c._order_port == 5558
        assert c._fill_port == 5559

    def test_env_ports_override(self, monkeypatch):
        monkeypatch.setenv("ZMQ_TICK_PORT", "6556")
        monkeypatch.setenv("ZMQ_BAR_PORT", "6557")
        monkeypatch.setenv("ZMQ_ORDER_PORT", "6558")
        monkeypatch.setenv("ZMQ_FILL_PORT", "6559")
        c = BridgeConsumer()
        assert c._tick_port == 6556
        assert c._bar_port == 6557
        assert c._order_port == 6558
        assert c._fill_port == 6559


class TestSchemaMismatchWarning:
    def test_mismatched_version_logs_warning(self, caplog):
        caplog.set_level(logging.WARNING, logger="bridge")
        c = BridgeConsumer()
        bad_hb = msgpack.packb({"type": "heartbeat", "ts": int(time.time_ns()), "schema_version": 99})
        c._handle_heartbeat_frame(bad_hb)
        assert any("Schema version mismatch" in r.message and "99" in r.message for r in caplog.records)

    def test_missing_version_logs_warning(self, caplog):
        caplog.set_level(logging.WARNING, logger="bridge")
        c = BridgeConsumer()
        no_ver = msgpack.packb({"type": "heartbeat", "ts": int(time.time_ns())})
        c._handle_heartbeat_frame(no_ver)
        assert any("Schema version mismatch" in r.message for r in caplog.records)

    def test_matching_version_no_warning(self, caplog):
        caplog.set_level(logging.WARNING, logger="bridge")
        c = BridgeConsumer()
        c._handle_heartbeat_frame(pack_heartbeat())
        schema_warnings = [r for r in caplog.records if "Schema version mismatch" in r.message]
        assert schema_warnings == []

    def test_valid_heartbeat_updates_last_heartbeat(self):
        c = BridgeConsumer()
        assert c._last_heartbeat == 0.0
        c._handle_heartbeat_frame(pack_heartbeat())
        assert c._last_heartbeat > 0.0


class TestAutoReconnect:
    @pytest.mark.asyncio
    async def test_reconnect_increments_attempt(self, monkeypatch):
        c = BridgeConsumer()
        c._running = True
        monkeypatch.setattr("asyncio.sleep", AsyncMock())
        # Avoid actually reconnecting sockets — stub connect
        c.connect = AsyncMock()
        before = c._reconnect_attempt
        await c._reconnect()
        assert c._reconnect_attempt == before + 1

    @pytest.mark.asyncio
    async def test_reconnect_logs_attempt(self, caplog, monkeypatch):
        caplog.set_level(logging.WARNING, logger="bridge")
        c = BridgeConsumer()
        c._running = True
        monkeypatch.setattr("asyncio.sleep", AsyncMock())
        c.connect = AsyncMock()
        await c._reconnect()
        assert any("Reconnecting in" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_reconnect_closes_and_rebinds_sockets(self, monkeypatch):
        c = BridgeConsumer()
        c._running = True
        # Stub sockets
        c._tick_sub = MagicMock()
        c._bar_sub = MagicMock()
        c._order_push = MagicMock()
        c._order_pull = MagicMock()
        c._ctx = MagicMock()
        monkeypatch.setattr("asyncio.sleep", AsyncMock())
        c.connect = AsyncMock()
        await c._reconnect()
        # connect() must have been called again
        c.connect.assert_awaited()


class TestBarCloseReceive:
    def test_placeholder_for_plan_04(self):
        pytest.skip("Plan 04 adds bar-close routing with timeframe tag — see 06-04-PLAN.md")
