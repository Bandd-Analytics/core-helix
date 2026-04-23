"""V2 bridge type definitions — Tick, Bar, OrderRequest, Fill, Side, OrderType.

Ported from V1/helix/src/execution/abstract.py with one intentional rename:
OrderResult (V1) -> Fill (V2) per BRDG-01 and decision D-08.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

import numpy as np


class Side(enum.Enum):
    """Direction of a trade."""
    BUY = 1
    SELL = -1


class OrderType(enum.Enum):
    """Execution instruction type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class Tick:
    timestamp: np.datetime64
    symbol: str
    bid: float
    ask: float
    bid_volume: float = 0.0
    ask_volume: float = 0.0
    source: str = ""


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: np.datetime64
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    spread: float = 0.0


@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    side: Side
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    comment: str = ""


@dataclass(frozen=True, slots=True)
class Fill:
    """Outcome of a submitted order (V1 OrderResult renamed per D-08)."""
    order_id: str
    fill_price: float
    fill_quantity: float
    slippage: float
    commission: float
    success: bool
    error_message: str = ""
