"""Strategy router (Phase 9 — STUB).

Plan 01 (Wave 0): typed contracts only. All routing logic raises
NotImplementedError. Plans 02-04 implement.

Per CONTEXT D-01..D-12 / D-17:
    - D-01: RouteDecision frozen dataclass with strategy/direction/confidence/size_mult
    - D-05: 4-gate chain (Regime -> Session -> Matrix -> RAG)
    - D-07: Per-strategy iteration order (DAILY_SWING first)
    - D-09: PositionStore Protocol + InMemoryPositionStore (backtest) + ZmqPositionStore (live, Phase 10)
    - D-12: Module location V2/v3_intelligence/router.py
    - D-17: Wave 0 RED scaffold lands first; Plans 02-04 turn tests GREEN

This module exposes the typed contract surface only. Plan 02 implements the
4-gate chain logic in StrategyRouter.route(); Plan 03 fits the missing detector
JSONs; Plan 04 builds the 4yr simulation harness.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from .pair_config import PairConfig

# Forward-decl note: avoid circular import on regime / rag_signal_filter.
# OnlineRegimeFilter and RAGSignalFilter are passed by-instance only.


class Strategy(enum.Enum):
    """Closed dispatch set (CONTEXT D-01).

    String values match the enum names exactly so the Phase 10 EA comment
    field can parse them back to a Strategy via Strategy(value) (RESEARCH §9
    forward-compat for OrderRequest.comment).
    """
    DAILY_SWING = "DAILY_SWING"
    H1_SCALP    = "H1_SCALP"
    H1_MOMENTUM = "H1_MOMENTUM"
    M15_SCALP   = "M15_SCALP"


class Direction(enum.Enum):
    """Trade direction (CONTEXT D-01)."""
    LONG  = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class RouteDecision:
    """Output of StrategyRouter.route() (CONTEXT D-01).

    Frozen dataclass — never mutated; all router state changes go through the
    simulator harness or the live engine event loop.

    Fields:
        strategy:    The dispatched strategy (one of 4).
        direction:   LONG / SHORT.
        confidence:  RAG score (0.0-1.0) — passed through verbatim per D-03.
        size_mult:   pair_config[pair].<strategy>_size_mult * regime_confidence,
                     capped at 1.0 (D-04).
    """
    strategy:   Strategy
    direction:  Direction
    confidence: float
    size_mult:  float


@dataclass(frozen=True)
class OpenPosition:
    """Used by PositionStore (CONTEXT D-09).

    Frozen dataclass tracking an open position for ROUT-02 (swing-first) and
    ROUT-03 (direction-conflict) checks.
    """
    pair:       str
    direction:  Direction
    strategy:   Strategy
    opened_at:  datetime


@runtime_checkable
class PositionStore(Protocol):
    """Injected position-state oracle (CONTEXT D-09).

    Two adapters land in Phase 9: InMemoryPositionStore (backtest), and
    ZmqPositionStore (live skeleton — Phase 10 wires actual ZMQ subscription).
    """
    def open_positions(self, pair: str) -> list[OpenPosition]: ...


class InMemoryPositionStore:
    """Backtest-side adapter (CONTEXT D-09).

    Backed by a dict[str, list[OpenPosition]]. Updated by the 4yr simulator on
    each fill (Plan 04). For Plan 01 RED tests, only open() / open_positions()
    are exercised — close() lands here for symmetry / Plan 04 use.
    """
    def __init__(self) -> None:
        self._positions: dict[str, list[OpenPosition]] = {}

    def open_positions(self, pair: str) -> list[OpenPosition]:
        """Return a fresh list copy so callers cannot mutate internal state."""
        return list(self._positions.get(pair, []))

    def open(self, pos: OpenPosition) -> None:
        """Record a newly-opened position (Plan 04 simulator calls this)."""
        self._positions.setdefault(pos.pair, []).append(pos)

    def close(self, pair: str, opened_at: datetime) -> None:
        """Remove the position with matching opened_at (Plan 04 simulator)."""
        lst = self._positions.get(pair, [])
        self._positions[pair] = [p for p in lst if p.opened_at != opened_at]


class ZmqPositionStore:
    """Live-side adapter — Phase 10 wires actual ZMQ subscription (CONTEXT D-09 / D-20).

    Phase 9 ships only the Protocol-conforming stub; instantiation raises so
    accidental Phase-9-side use surfaces immediately.
    """
    def __init__(self, zmq_endpoint: str | None = None) -> None:
        self._endpoint = zmq_endpoint
        raise NotImplementedError("Phase 10 wires ZmqPositionStore to bridge consumer")

    def open_positions(self, pair: str) -> list[OpenPosition]:  # pragma: no cover
        raise NotImplementedError("Phase 10 wires ZmqPositionStore to bridge consumer")


class StrategyRouter:
    """4-gate router (CONTEXT D-05). Plan 02 implements; Plan 01 stubs.

    Construction signature is locked here so Plan 02 fills the body without
    touching the call site. Tests (Wave 0 RED) construct via this signature
    and assert .route() raises NotImplementedError until Plan 02 lands.
    """
    def __init__(
        self,
        regime_detectors: dict,        # dict[str, OnlineRegimeFilter] — Plan 02 will type via TYPE_CHECKING
        rag_filter,                    # RAGSignalFilter
        position_store: PositionStore,
        pair_config: dict[str, PairConfig],
    ) -> None:
        self.regime_detectors = regime_detectors
        self.rag_filter       = rag_filter
        self.position_store   = position_store
        self.pair_config      = pair_config
        # Direction-conflict counter (ROUT-03 observability — Plan 02 increments).
        self._direction_conflict_count = 0

    def route(self, pair: str, timestamp: datetime, market_data) -> RouteDecision | None:
        """Dispatch a single bar through the 4-gate chain (Plan 02 implements)."""
        raise NotImplementedError("Plan 02 implements 4-gate chain (regime -> session -> matrix -> RAG)")


__all__ = [
    "Strategy",
    "Direction",
    "RouteDecision",
    "OpenPosition",
    "PositionStore",
    "InMemoryPositionStore",
    "ZmqPositionStore",
    "StrategyRouter",
]
