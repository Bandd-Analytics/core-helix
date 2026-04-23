"""MessagePack serialization schemas for the V2 ZeroMQ bridge (BRDG-01).

Defines SCHEMA_VERSION and pack/unpack functions for all five bridge message types:
Tick, Bar, OrderRequest, Fill, Heartbeat.

Schema deltas from V1/helix/src/execution/bridge/message_schemas.py:
  - D-06: SCHEMA_VERSION module constant added
  - D-07: Heartbeat carries schema_version field for connect-time version check
  - D-08: OrderResult renamed to Fill
  - D-15: Bar gains optional tf (timeframe) field for bar-close event tagging

Timestamps are transmitted as int64 nanoseconds-since-epoch.
"""

from __future__ import annotations

import time
from typing import Any

import msgpack  # type: ignore[import-untyped,unused-ignore]
import numpy as np

from .types import Bar, Fill, OrderRequest, OrderType, Side, Tick


SCHEMA_VERSION: int = 1


def _dt64_to_ns(dt: np.datetime64) -> int:
    return int(dt.astype("datetime64[ns]").astype(np.int64))


def _ns_to_dt64(ns: int) -> np.datetime64:
    return np.datetime64(ns, "ns")


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------

def pack_tick(tick: Tick) -> bytes:
    return msgpack.packb({
        "ts": _dt64_to_ns(tick.timestamp),
        "sym": tick.symbol,
        "bid": tick.bid, "ask": tick.ask,
        "bv": tick.bid_volume, "av": tick.ask_volume,
        "src": tick.source,
    })  # type: ignore[no-any-return]


def unpack_tick(data: bytes) -> Tick:
    d: dict[str, Any] = msgpack.unpackb(data)
    return Tick(
        timestamp=_ns_to_dt64(d["ts"]),
        symbol=d["sym"],
        bid=d["bid"], ask=d["ask"],
        bid_volume=d["bv"], ask_volume=d["av"],
        source=d["src"],
    )


# ---------------------------------------------------------------------------
# Bar (D-15: optional timeframe tag)
# ---------------------------------------------------------------------------

def pack_bar(bar: Bar, timeframe: str = "") -> bytes:
    payload: dict[str, Any] = {
        "ts": _dt64_to_ns(bar.timestamp),
        "sym": bar.symbol,
        "o": bar.open, "h": bar.high, "l": bar.low, "c": bar.close,
        "v": bar.volume, "sp": bar.spread,
    }
    if timeframe:
        payload["tf"] = timeframe
    return msgpack.packb(payload)  # type: ignore[no-any-return]


def unpack_bar(data: bytes) -> Bar:
    d: dict[str, Any] = msgpack.unpackb(data)
    return Bar(
        timestamp=_ns_to_dt64(d["ts"]),
        symbol=d["sym"],
        open=d["o"], high=d["h"], low=d["l"], close=d["c"],
        volume=d["v"], spread=d["sp"],
    )


def unpack_bar_with_timeframe(data: bytes) -> tuple[Bar, str]:
    """Unpack a bar and return (bar, timeframe_tag). Returns tf='' if absent."""
    d: dict[str, Any] = msgpack.unpackb(data)
    bar = Bar(
        timestamp=_ns_to_dt64(d["ts"]),
        symbol=d["sym"],
        open=d["o"], high=d["h"], low=d["l"], close=d["c"],
        volume=d["v"], spread=d["sp"],
    )
    return bar, d.get("tf", "")


# ---------------------------------------------------------------------------
# OrderRequest
# ---------------------------------------------------------------------------

def pack_order_request(order: OrderRequest) -> bytes:
    return msgpack.packb({
        "sym": order.symbol,
        "side": order.side.value,
        "qty": order.quantity,
        "ot": order.order_type.value,
        "px": order.price,
        "sl": order.sl, "tp": order.tp,
        "cmt": order.comment,
    })  # type: ignore[no-any-return]


def unpack_order_request(data: bytes) -> OrderRequest:
    d: dict[str, Any] = msgpack.unpackb(data)
    return OrderRequest(
        symbol=d["sym"],
        side=Side(d["side"]),
        quantity=d["qty"],
        order_type=OrderType(d["ot"]),
        price=d["px"], sl=d["sl"], tp=d["tp"],
        comment=d["cmt"],
    )


# ---------------------------------------------------------------------------
# Fill (D-08: renamed from OrderResult)
# ---------------------------------------------------------------------------

def pack_fill(fill: Fill) -> bytes:
    return msgpack.packb({
        "oid": fill.order_id,
        "fp": fill.fill_price, "fq": fill.fill_quantity,
        "slip": fill.slippage, "comm": fill.commission,
        "ok": fill.success, "err": fill.error_message,
    })  # type: ignore[no-any-return]


def unpack_fill(data: bytes) -> Fill:
    d: dict[str, Any] = msgpack.unpackb(data)
    return Fill(
        order_id=d["oid"],
        fill_price=d["fp"], fill_quantity=d["fq"],
        slippage=d["slip"], commission=d["comm"],
        success=d["ok"], error_message=d["err"],
    )


# ---------------------------------------------------------------------------
# Heartbeat (D-07: carries schema_version field)
# ---------------------------------------------------------------------------

def pack_heartbeat() -> bytes:
    ns = int(time.time_ns())
    return msgpack.packb({
        "type": "heartbeat",
        "ts": ns,
        "schema_version": SCHEMA_VERSION,
    })  # type: ignore[no-any-return]


def unpack_heartbeat(data: bytes) -> dict[str, Any]:
    """Return the full heartbeat dict so caller can check schema_version (D-07)."""
    result: dict[str, Any] = msgpack.unpackb(data)
    return result
