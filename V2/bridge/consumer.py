"""V2 bridge consumer — async ZMQ subscriber with heartbeat guard + auto-reconnect.

Ported from V1/helix/src/execution/bridge/linux_consumer.py with deltas:
  - D-02, D-03: env-configurable host + ports
  - D-07: schema_version check on heartbeat (logs WARNING on mismatch)
  - D-10, D-11, D-12: stale threshold 10s, reconnect after one missed cycle, exponential backoff
  - 06-UI-SPEC: log messages use the [BRIDGE] prefix and exact format strings from the copywriting contract.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

import zmq  # type: ignore[import-untyped,unused-ignore]
import zmq.asyncio  # type: ignore[import-untyped,unused-ignore]

from .schemas import (
    SCHEMA_VERSION,
    pack_order_request,
    unpack_bar,
    unpack_bar_with_timeframe,
    unpack_heartbeat,
    unpack_fill,
    unpack_tick,
)
from .types import Bar, OrderRequest, Tick

logger = logging.getLogger("bridge")


class BridgeConsumer:
    """ZMQ subscriber for the V2 Python signal-engine host.

    Env variables:
        BRIDGE_HOST        — remote publisher host (default 10.200.0.1)
        ZMQ_TICK_PORT      — SUB tick stream port (default 5556)
        ZMQ_BAR_PORT       — SUB bar stream port (default 5557)
        ZMQ_ORDER_PORT     — PUSH order request port (default 5558)
        ZMQ_FILL_PORT      — PULL fill port (default 5559)
    """

    RECONNECT_DELAYS: list[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
    STALE_THRESHOLD: float = 10.0

    def __init__(self) -> None:
        self._host: str = os.getenv("BRIDGE_HOST", "10.200.0.1")
        self._tick_port: int = int(os.getenv("ZMQ_TICK_PORT", "5556"))
        self._bar_port: int = int(os.getenv("ZMQ_BAR_PORT", "5557"))
        self._order_port: int = int(os.getenv("ZMQ_ORDER_PORT", "5558"))
        self._fill_port: int = int(os.getenv("ZMQ_FILL_PORT", "5559"))

        self._ctx: zmq.asyncio.Context | None = None
        self._tick_sub: Any = None
        self._bar_sub: Any = None
        self._order_push: Any = None
        self._order_pull: Any = None

        self._last_heartbeat: float = 0.0
        self._reconnect_attempt: int = 0
        self._subscribed_symbols: set[str] = set()
        self._running: bool = False
        self._zmq_subscribe_opt: int = zmq.SUBSCRIBE

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open ZMQ context + all four sockets."""
        self._ctx = zmq.asyncio.Context()

        self._tick_sub = self._ctx.socket(zmq.SUB)
        self._tick_sub.connect(f"tcp://{self._host}:{self._tick_port}")

        self._bar_sub = self._ctx.socket(zmq.SUB)
        self._bar_sub.connect(f"tcp://{self._host}:{self._bar_port}")

        self._order_push = self._ctx.socket(zmq.PUSH)
        self._order_push.connect(f"tcp://{self._host}:{self._order_port}")

        self._order_pull = self._ctx.socket(zmq.PULL)
        self._order_pull.connect(f"tcp://{self._host}:{self._fill_port}")

        # Restore subscription filters after reconnect
        for sym in self._subscribed_symbols:
            self._tick_sub.setsockopt(self._zmq_subscribe_opt, sym.encode())
            self._bar_sub.setsockopt(self._zmq_subscribe_opt, sym.encode())

        self._running = True
        logger.info(
            "[BRIDGE] Connected to %s:%d — heartbeat OK",
            self._host, self._tick_port,
        )
        if self._reconnect_attempt > 0:
            logger.info(
                "[BRIDGE] Reconnected successfully after %d attempt(s)",
                self._reconnect_attempt,
            )
        self._reconnect_attempt = 0

    async def disconnect(self) -> None:
        """Close all sockets and terminate the ZMQ context."""
        self._running = False
        for sock in (self._tick_sub, self._bar_sub, self._order_push, self._order_pull):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        if self._ctx is not None:
            self._ctx.term()
        self._tick_sub = None
        self._bar_sub = None
        self._order_push = None
        self._order_pull = None
        self._ctx = None

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def subscribe(self, symbol: str) -> None:
        """Subscribe to tick and bar data for the given symbol."""
        if self._tick_sub is not None:
            self._tick_sub.setsockopt(self._zmq_subscribe_opt, symbol.encode())
        if self._bar_sub is not None:
            self._bar_sub.setsockopt(self._zmq_subscribe_opt, symbol.encode())
        self._subscribed_symbols.add(symbol)

    # ------------------------------------------------------------------
    # Stale detection (D-10)
    # ------------------------------------------------------------------

    @property
    def is_stale(self) -> bool:
        """True if no heartbeat received within STALE_THRESHOLD seconds.

        Returns True initially (before any heartbeat) because _last_heartbeat
        starts at 0.0, which is more than STALE_THRESHOLD seconds in the past.
        """
        return time.monotonic() - self._last_heartbeat > self.STALE_THRESHOLD

    # ------------------------------------------------------------------
    # Heartbeat handling (D-07)
    # ------------------------------------------------------------------

    def _handle_heartbeat_frame(self, data: bytes) -> None:
        """Parse a heartbeat frame, check schema_version, update _last_heartbeat."""
        try:
            hb = unpack_heartbeat(data)
        except Exception:
            logger.warning("[BRIDGE] WARNING: failed to decode heartbeat frame")
            return
        remote_ver = hb.get("schema_version")
        if remote_ver != SCHEMA_VERSION:
            logger.warning(
                "[BRIDGE] WARNING: Schema version mismatch — remote=%s, expected=%s",
                remote_ver, SCHEMA_VERSION,
            )
        self._last_heartbeat = time.monotonic()

    # ------------------------------------------------------------------
    # Bar-close frame handling (BRDG-04)
    # ------------------------------------------------------------------

    def _handle_bar_frame(self, data: bytes) -> tuple[Bar, str]:
        """Parse a bar-close frame. Accepts msgpack (V2 native) or JSON (MQL5 Option A).

        Returns:
            tuple[Bar, str]: the Bar object and the timeframe tag ("" if absent).

        Raises:
            Exception: if the bytes are neither valid msgpack-with-expected-keys
                       nor valid JSON-with-expected-keys. Caller (receive loop)
                       must catch and log without killing the loop.
        """
        # Try msgpack first (V2 native path)
        try:
            return unpack_bar_with_timeframe(data)
        except Exception:
            pass
        # Fallback to JSON (MQL5 EA payload path per RESEARCH Option A)
        obj = json.loads(data.decode("utf-8"))
        bar = Bar(
            timestamp=np.datetime64(int(obj["ts"]), "ns"),
            symbol=obj["sym"],
            open=float(obj["o"]), high=float(obj["h"]),
            low=float(obj["l"]), close=float(obj["c"]),
            volume=float(obj.get("v", 0.0)),
            spread=float(obj.get("sp", 0.0)),
        )
        return bar, str(obj.get("tf", ""))

    # ------------------------------------------------------------------
    # Receive loop
    # ------------------------------------------------------------------

    async def _receive_loop(
        self,
        on_tick: Callable[[Tick], Awaitable[None]],
        on_bar_close: Callable[[Bar, str], Awaitable[None]],
    ) -> None:
        """Receive ticks, bars, and heartbeats; dispatch to callbacks.

        on_bar_close is invoked with (Bar, timeframe_tag).
        Heartbeats arrive on the tick socket as single-frame messages.
        Ticks arrive as two-frame [symbol, payload] messages.
        """
        while self._running:
            poller = zmq.asyncio.Poller()
            if self._tick_sub is not None:
                poller.register(self._tick_sub, zmq.POLLIN)
            if self._bar_sub is not None:
                poller.register(self._bar_sub, zmq.POLLIN)

            events = dict(await poller.poll(timeout=100))

            if self._tick_sub in events:
                frames = await self._tick_sub.recv_multipart()
                if len(frames) == 1:
                    self._handle_heartbeat_frame(frames[0])
                elif len(frames) == 2:
                    try:
                        tick = unpack_tick(frames[1])
                        await on_tick(tick)
                    except Exception as e:
                        logger.warning("[BRIDGE] WARNING: failed to decode tick frame: %s", e)

            if self._bar_sub in events:
                frames = await self._bar_sub.recv_multipart()
                if len(frames) == 2:
                    try:
                        bar, tf = self._handle_bar_frame(frames[1])
                        await on_bar_close(bar, tf)
                    except Exception as e:
                        logger.warning("[BRIDGE] WARNING: failed to decode bar frame: %s", e)

    # ------------------------------------------------------------------
    # Order sending (to MT5 publisher via PUSH)
    # ------------------------------------------------------------------

    async def send_order(self, order: OrderRequest) -> None:
        """Push an OrderRequest to the Windows publisher."""
        if self._order_push is not None:
            await self._order_push.send(pack_order_request(order))

    # ------------------------------------------------------------------
    # Reconnect (D-11, D-12)
    # ------------------------------------------------------------------

    def _get_reconnect_delay(self) -> float:
        """Return the delay for the current reconnect attempt (capped at 30s)."""
        idx = min(self._reconnect_attempt, len(self.RECONNECT_DELAYS) - 1)
        return self.RECONNECT_DELAYS[idx]

    async def _reconnect(self) -> None:
        """Attempt to reconnect once with exponential back-off.

        Logs a WARNING with the UI-SPEC format, sleeps, closes existing sockets,
        then calls connect() which restores subscription filters.
        """
        delay = self._get_reconnect_delay()
        attempt_n = self._reconnect_attempt + 1
        max_attempts = len(self.RECONNECT_DELAYS)
        logger.warning(
            "[BRIDGE] Reconnecting in %.0fs (attempt %d/%d)",
            delay, attempt_n, max_attempts,
        )
        self._reconnect_attempt = attempt_n
        await asyncio.sleep(delay)
        if not self._running:
            return
        # Close existing sockets
        for sock in (self._tick_sub, self._bar_sub, self._order_push, self._order_pull):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        self._tick_sub = None
        self._bar_sub = None
        self._order_push = None
        self._order_pull = None
        # Reconnect — connect() restores subscription filters and logs success
        await self.connect()
