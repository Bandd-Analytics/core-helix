"""V2 bridge publisher — async ZMQ PUB/PULL/PUSH bindings with heartbeat loop.

Ported from V1/helix/src/execution/bridge/windows_publisher.py with deltas:
  - D-02, D-03: env-configurable bind ports (defaults match V1)
  - D-07: heartbeat carries SCHEMA_VERSION field (via pack_heartbeat in schemas.py)
  - D-09: heartbeat interval 5.0 seconds
  - D-15: publish_bar accepts optional timeframe argument for bar-close events
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import zmq  # type: ignore[import-untyped,unused-ignore]
import zmq.asyncio  # type: ignore[import-untyped,unused-ignore]

from .schemas import (
    pack_bar,
    pack_fill,
    pack_heartbeat,
    pack_tick,
    unpack_order_request,
)
from .types import Bar, Fill, OrderRequest, Tick

logger = logging.getLogger("bridge")


class BridgePublisher:
    """ZMQ publisher bound to the MT5/Windows side of the bridge.

    Env variables:
        ZMQ_TICK_PORT   — PUB tick stream port (default 5556)
        ZMQ_BAR_PORT    — PUB bar stream port (default 5557)
        ZMQ_ORDER_PORT  — PULL order request port (default 5558)
        ZMQ_FILL_PORT   — PUSH fill port (default 5559)
    """

    TICK_PORT: int = 5556
    BAR_PORT: int = 5557
    ORDER_PORT: int = 5558
    FILL_PORT: int = 5559
    HEARTBEAT_INTERVAL: float = 5.0

    def __init__(self, bind_address: str = "tcp://*") -> None:
        self._bind_address = bind_address
        self._tick_port: int = int(os.getenv("ZMQ_TICK_PORT", str(self.TICK_PORT)))
        self._bar_port: int = int(os.getenv("ZMQ_BAR_PORT", str(self.BAR_PORT)))
        self._order_port: int = int(os.getenv("ZMQ_ORDER_PORT", str(self.ORDER_PORT)))
        self._fill_port: int = int(os.getenv("ZMQ_FILL_PORT", str(self.FILL_PORT)))

        self._ctx: zmq.asyncio.Context | None = None
        self._tick_pub: Any = None
        self._bar_pub: Any = None
        self._order_pull: Any = None
        self._fill_push: Any = None

        self._running: bool = False
        self._heartbeat_interval_seconds: float = self.HEARTBEAT_INTERVAL

    async def start(self) -> None:
        """Bind all sockets and set running flag."""
        self._ctx = zmq.asyncio.Context()
        self._tick_pub = self._ctx.socket(zmq.PUB)
        self._tick_pub.bind(f"{self._bind_address}:{self._tick_port}")
        self._bar_pub = self._ctx.socket(zmq.PUB)
        self._bar_pub.bind(f"{self._bind_address}:{self._bar_port}")
        self._order_pull = self._ctx.socket(zmq.PULL)
        self._order_pull.bind(f"{self._bind_address}:{self._order_port}")
        self._fill_push = self._ctx.socket(zmq.PUSH)
        self._fill_push.bind(f"{self._bind_address}:{self._fill_port}")
        self._running = True
        logger.info(
            "[BRIDGE] Publisher bound tick=%d bar=%d order=%d fill=%d",
            self._tick_port, self._bar_port, self._order_port, self._fill_port,
        )

    async def stop(self) -> None:
        """Close all sockets and terminate the ZMQ context."""
        self._running = False
        for sock in (self._tick_pub, self._bar_pub, self._order_pull, self._fill_push):
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        if self._ctx is not None:
            self._ctx.term()
        self._tick_pub = None
        self._bar_pub = None
        self._order_pull = None
        self._fill_push = None
        self._ctx = None

    async def publish_tick(self, tick: Tick) -> None:
        """Publish a Tick as a multipart ZMQ message [symbol, payload]."""
        if self._tick_pub is None:
            return
        await self._tick_pub.send_multipart([tick.symbol.encode(), pack_tick(tick)])

    async def publish_bar(self, bar: Bar, timeframe: str = "") -> None:
        """Publish a Bar as a multipart ZMQ message [symbol, payload].

        Args:
            bar: Bar dataclass with OHLCV data.
            timeframe: Optional timeframe tag (e.g. "D1", "H1", "M15") for bar-close events.
        """
        if self._bar_pub is None:
            return
        await self._bar_pub.send_multipart([bar.symbol.encode(), pack_bar(bar, timeframe)])

    async def publish_fill(self, fill: Fill) -> None:
        """Push a Fill message to the Linux consumer."""
        if self._fill_push is None:
            return
        await self._fill_push.send(pack_fill(fill))

    async def _heartbeat_loop(self) -> None:
        """Send a heartbeat message periodically on the tick PUB socket.

        Sends pack_heartbeat() bytes (which include SCHEMA_VERSION) every
        HEARTBEAT_INTERVAL seconds while running. The consumer disambiguates
        heartbeats from ticks by frame count (1 frame = heartbeat, 2 = tick).
        """
        while self._running:
            if self._tick_pub is not None:
                await self._tick_pub.send(pack_heartbeat())
            await asyncio.sleep(self._heartbeat_interval_seconds)

    async def _order_loop(
        self,
        handler: Callable[[OrderRequest], Awaitable[None]],
    ) -> None:
        """Receive order requests from Linux consumers and pass to handler."""
        while self._running:
            if self._order_pull is None:
                await asyncio.sleep(0.01)
                continue
            raw = await self._order_pull.recv()
            order = unpack_order_request(raw)
            await handler(order)
