"""Round-trip tests for V2 bridge msgpack schemas (BRDG-01).

Covers all five message types: Tick, Bar, OrderRequest, Fill, Heartbeat.
Schema deltas tested:
  - D-06: SCHEMA_VERSION == 1
  - D-07: Heartbeat carries schema_version field
  - D-08: Fill replaces OrderResult
  - D-15: Bar gains optional tf (timeframe) field
"""

from __future__ import annotations

import time

import msgpack
import numpy as np
import pytest

from bridge.schemas import (
    SCHEMA_VERSION,
    pack_bar,
    pack_fill,
    pack_heartbeat,
    pack_order_request,
    pack_tick,
    unpack_bar,
    unpack_fill,
    unpack_heartbeat,
    unpack_order_request,
    unpack_tick,
)
from bridge.types import Bar, Fill, OrderRequest, OrderType, Side, Tick


# ---------------------------------------------------------------------------
# Schema version constant
# ---------------------------------------------------------------------------


def test_schema_version_constant_exported() -> None:
    """SCHEMA_VERSION is exported and equals 1 (D-06)."""
    assert SCHEMA_VERSION == 1


# ---------------------------------------------------------------------------
# Tick round-trip
# ---------------------------------------------------------------------------


def test_tick_round_trip() -> None:
    """pack_tick/unpack_tick preserves all Tick fields."""
    original = Tick(
        timestamp=np.datetime64("2026-04-23T10:00:00.000000001", "ns"),
        symbol="EURUSD",
        bid=1.1234,
        ask=1.1236,
        bid_volume=100.0,
        ask_volume=150.0,
        source="MT5",
    )
    raw = pack_tick(original)
    result = unpack_tick(raw)

    assert result.timestamp == original.timestamp
    assert result.symbol == original.symbol
    assert result.bid == original.bid
    assert result.ask == original.ask
    assert result.bid_volume == original.bid_volume
    assert result.ask_volume == original.ask_volume
    assert result.source == original.source


# ---------------------------------------------------------------------------
# Bar round-trip + timeframe tag (D-15)
# ---------------------------------------------------------------------------


class TestBarTimeframeTag:
    """Covers D-15 and BRDG-04: optional tf tag for bar-close events."""

    _bar = Bar(
        timestamp=np.datetime64("2026-04-23T00:00:00", "ns"),
        symbol="USDJPY",
        open=154.50,
        high=155.00,
        low=154.25,
        close=154.75,
        volume=1000.0,
        spread=0.03,
    )

    def test_bar_without_timeframe_omits_tf_field(self) -> None:
        """pack_bar without tf arg must NOT include 'tf' key in payload."""
        raw = pack_bar(self._bar)
        unpacked: dict = msgpack.unpackb(raw)
        assert "tf" not in unpacked

    def test_bar_with_d1_timeframe(self) -> None:
        """pack_bar(bar, 'D1') includes tf='D1' in msgpack payload."""
        raw = pack_bar(self._bar, "D1")
        unpacked: dict = msgpack.unpackb(raw)
        assert unpacked["tf"] == "D1"

    def test_bar_with_h1_timeframe(self) -> None:
        """pack_bar(bar, 'H1') includes tf='H1' in msgpack payload."""
        raw = pack_bar(self._bar, "H1")
        unpacked: dict = msgpack.unpackb(raw)
        assert unpacked["tf"] == "H1"

    def test_bar_with_m15_timeframe(self) -> None:
        """pack_bar(bar, 'M15') includes tf='M15' in msgpack payload."""
        raw = pack_bar(self._bar, "M15")
        unpacked: dict = msgpack.unpackb(raw)
        assert unpacked["tf"] == "M15"

    def test_bar_ohlcv_round_trip_with_timeframe(self) -> None:
        """Full round-trip with tf='D1' preserves all OHLCV + spread fields."""
        raw = pack_bar(self._bar, "D1")
        result = unpack_bar(raw)

        assert result.timestamp == self._bar.timestamp
        assert result.symbol == self._bar.symbol
        assert result.open == self._bar.open
        assert result.high == self._bar.high
        assert result.low == self._bar.low
        assert result.close == self._bar.close
        assert result.volume == self._bar.volume
        assert result.spread == self._bar.spread


# ---------------------------------------------------------------------------
# OrderRequest round-trip
# ---------------------------------------------------------------------------


def test_order_request_round_trip() -> None:
    """pack_order_request/unpack_order_request preserves all fields."""
    original = OrderRequest(
        symbol="GBPUSD",
        side=Side.BUY,
        quantity=0.1,
        order_type=OrderType.MARKET,
        price=None,
        sl=1.2800,
        tp=1.2950,
        comment="test",
    )
    raw = pack_order_request(original)
    result = unpack_order_request(raw)

    assert result.symbol == original.symbol
    assert result.side == original.side
    assert result.quantity == original.quantity
    assert result.order_type == original.order_type
    assert result.price is None
    assert result.sl == original.sl
    assert result.tp == original.tp
    assert result.comment == original.comment


def test_order_request_side_stored_as_int() -> None:
    """Side enum must be serialized as int (1 or -1), not the enum object."""
    order = OrderRequest(
        symbol="GBPJPY",
        side=Side.SELL,
        quantity=0.05,
    )
    raw = pack_order_request(order)
    unpacked: dict = msgpack.unpackb(raw)
    assert unpacked["side"] == -1


def test_order_request_optional_none_preserved() -> None:
    """price=None, sl=None, tp=None round-trip without KeyError."""
    order = OrderRequest(
        symbol="GBPUSD",
        side=Side.BUY,
        quantity=0.1,
        price=None,
        sl=None,
        tp=None,
    )
    raw = pack_order_request(order)
    result = unpack_order_request(raw)

    assert result.price is None
    assert result.sl is None
    assert result.tp is None


# ---------------------------------------------------------------------------
# Fill round-trip (D-08: renamed from OrderResult)
# ---------------------------------------------------------------------------


class TestFillRoundTrip:
    """Covers D-08: Fill replaces OrderResult in V2."""

    def test_fill_round_trip(self) -> None:
        """pack_fill/unpack_fill preserves all Fill fields."""
        original = Fill(
            order_id="12345",
            fill_price=1.1235,
            fill_quantity=0.1,
            slippage=0.0001,
            commission=0.50,
            success=True,
            error_message="",
        )
        raw = pack_fill(original)
        result = unpack_fill(raw)

        assert result.order_id == original.order_id
        assert result.fill_price == original.fill_price
        assert result.fill_quantity == original.fill_quantity
        assert result.slippage == original.slippage
        assert result.commission == original.commission
        assert result.success is True
        assert result.error_message == original.error_message
        assert isinstance(result, Fill)

    def test_fill_failure_case(self) -> None:
        """Fill with success=False and error_message round-trips correctly."""
        original = Fill(
            order_id="99999",
            fill_price=0.0,
            fill_quantity=0.0,
            slippage=0.0,
            commission=0.0,
            success=False,
            error_message="INSUFFICIENT_MARGIN",
        )
        raw = pack_fill(original)
        result = unpack_fill(raw)

        assert result.success is False
        assert result.error_message == "INSUFFICIENT_MARGIN"


# ---------------------------------------------------------------------------
# Heartbeat (D-07: schema_version field)
# ---------------------------------------------------------------------------


def test_heartbeat_schema_version() -> None:
    """Heartbeat payload includes schema_version == SCHEMA_VERSION (D-07)."""
    raw = pack_heartbeat()
    unpacked: dict = msgpack.unpackb(raw)

    assert "schema_version" in unpacked
    assert unpacked["schema_version"] == SCHEMA_VERSION
    assert unpacked["schema_version"] == 1
    assert unpacked["type"] == "heartbeat"


def test_heartbeat_timestamp_is_nanoseconds() -> None:
    """Heartbeat ts field is in nanoseconds (within 5s of time.time_ns())."""
    before_ns = int(time.time_ns())
    raw = pack_heartbeat()
    after_ns = int(time.time_ns())

    unpacked: dict = msgpack.unpackb(raw)
    ts = unpacked["ts"]

    assert isinstance(ts, int)
    # ts must be within 5 seconds (in nanoseconds) of before_ns
    assert before_ns - 5_000_000_000 <= ts <= after_ns + 5_000_000_000


def test_unpack_heartbeat_returns_dict() -> None:
    """unpack_heartbeat returns full dict with type/ts/schema_version keys (D-07)."""
    raw = pack_heartbeat()
    result = unpack_heartbeat(raw)

    assert isinstance(result, dict)
    assert "type" in result
    assert "ts" in result
    assert "schema_version" in result
