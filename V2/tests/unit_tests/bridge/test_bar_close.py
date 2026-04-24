"""Tests for V2 consumer bar-close routing with timeframe tag (BRDG-04)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import msgpack
import numpy as np
import pytest

from bridge.consumer import BridgeConsumer
from bridge.schemas import pack_bar
from bridge.types import Bar


def _make_bar(sym: str = "EURUSD") -> Bar:
    return Bar(
        timestamp=np.datetime64("2026-04-23T10:00:00", "ns"),
        symbol=sym,
        open=1.1, high=1.12, low=1.09, close=1.11,
        volume=1000, spread=2,
    )


class TestHandleBarFrameMsgpack:
    def test_handle_bar_frame_msgpack_d1(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(pack_bar(_make_bar(), "D1"))
        assert tf == "D1"
        assert bar.symbol == "EURUSD"
        assert bar.close == 1.11

    def test_handle_bar_frame_msgpack_h1(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(pack_bar(_make_bar(), "H1"))
        assert tf == "H1"

    def test_handle_bar_frame_msgpack_m15(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(pack_bar(_make_bar(), "M15"))
        assert tf == "M15"

    def test_handle_bar_frame_msgpack_no_tf(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(pack_bar(_make_bar()))
        assert tf == ""


class TestHandleBarFrameJson:
    def _json_frame(self, tf: str | None = "D1") -> bytes:
        obj = {
            "ts": int(np.datetime64("2026-04-23T10:00:00", "ns").astype("int64")),
            "sym": "EURUSD",
            "o": 1.1, "h": 1.12, "l": 1.09, "c": 1.11,
            "v": 1000, "sp": 2,
        }
        if tf is not None:
            obj["tf"] = tf
        return json.dumps(obj).encode("utf-8")

    def test_handle_bar_frame_json_d1(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(self._json_frame("D1"))
        assert tf == "D1"
        assert bar.symbol == "EURUSD"
        assert bar.close == 1.11

    def test_handle_bar_frame_json_without_tf(self):
        c = BridgeConsumer()
        bar, tf = c._handle_bar_frame(self._json_frame(tf=None))
        assert tf == ""


class TestMalformedFrames:
    def test_malformed_bytes_raises_or_returns_none(self):
        c = BridgeConsumer()
        # Random bytes that are neither valid msgpack nor valid JSON
        with pytest.raises(Exception):
            c._handle_bar_frame(b"\xff\xfe\xfd\xfc not valid msgpack or json")


class TestReceiveLoopDispatch:
    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_bar_with_timeframe(self, monkeypatch):
        c = BridgeConsumer()
        c._running = True

        # Mock sockets + poller
        c._tick_sub = MagicMock()
        c._bar_sub = MagicMock()
        bar_frame = pack_bar(_make_bar(), "H1")
        c._bar_sub.recv_multipart = AsyncMock(return_value=[b"EURUSD", bar_frame])

        # Poller always returns bar_sub as ready
        fake_poller = MagicMock()
        fake_poller.poll = AsyncMock(return_value=[(c._bar_sub, 1)])
        fake_poller.register = MagicMock()
        monkeypatch.setattr("zmq.asyncio.Poller", lambda: fake_poller)

        received = []

        async def on_tick(tick):
            pass

        async def on_bar_close(bar, tf):
            received.append((bar.symbol, tf))
            c._running = False  # stop loop after one dispatch

        await c._receive_loop(on_tick, on_bar_close)
        assert received == [("EURUSD", "H1")]

    @pytest.mark.asyncio
    async def test_receive_loop_back_compat_bar_callback_signature(self, monkeypatch):
        """on_bar_close is awaited with (bar, tf) — both args passed to callback."""
        c = BridgeConsumer()
        c._running = True
        c._tick_sub = MagicMock()
        c._bar_sub = MagicMock()
        bar_frame = pack_bar(_make_bar(), "D1")
        c._bar_sub.recv_multipart = AsyncMock(return_value=[b"EURUSD", bar_frame])

        fake_poller = MagicMock()
        fake_poller.poll = AsyncMock(return_value=[(c._bar_sub, 1)])
        fake_poller.register = MagicMock()
        monkeypatch.setattr("zmq.asyncio.Poller", lambda: fake_poller)

        call_args = []

        async def on_tick(tick):
            pass

        async def on_bar_close(bar, tf):
            # Verify both arguments are passed correctly
            call_args.append({"symbol": bar.symbol, "tf": tf})
            c._running = False

        await c._receive_loop(on_tick, on_bar_close)
        assert len(call_args) == 1
        assert call_args[0]["symbol"] == "EURUSD"
        assert call_args[0]["tf"] == "D1"
