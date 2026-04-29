"""Strategy router (Phase 9 — IMPLEMENTATION).

Plan 02 implements the full 4-gate chain. Plan 01 typed contracts preserved.

Per CONTEXT D-01..D-12 / D-17:
    - D-01: RouteDecision frozen dataclass with strategy/direction/confidence/size_mult
    - D-02: None return collapses {regime/session/matrix/RAG/direction-conflict/no-signal} to one sentinel
    - D-03: confidence = RAG score directly
    - D-04: size_mult = pair_config[pair].<strat>_size_mult * regime_confidence (capped at 1.0)
    - D-05: 4-gate chain (Regime -> Session -> Matrix -> RAG) — cheapest first
    - D-06: Short-circuit on first fail; one structured log record per blocked dispatch
    - D-07: Per-strategy iteration order (DAILY_SWING first)
    - D-08: Tie-break on multiple intraday strategies = highest 4yr Sharpe from SHARPE_4YR
    - D-09: PositionStore Protocol + InMemoryPositionStore (backtest) + ZmqPositionStore (live, Phase 10)
    - D-10: Direction-conflict scope is pair-level only (strategy-agnostic)
    - D-12: Module location V2/v3_intelligence/router.py

Pitfall #6 honored: route() does NOT call regime_filter.update(). Simulator/live
engine call update() once per bar BEFORE route(); route() reads via
current_state_prob() only.
"""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .pair_config import PairConfig

if TYPE_CHECKING:
    from .regime.online_filter import OnlineRegimeFilter
    from .rag_signal_filter import RAGSignalFilter

# Forward-decl note: avoid circular import on regime / rag_signal_filter.
# OnlineRegimeFilter and RAGSignalFilter are passed by-instance only.

_log = logging.getLogger(__name__)


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


# ─────────────────────────────────────────────────────────────────────────────
# Strategy metadata — single source of truth for the per-strategy keys the
# router needs in each of its gate calls. Defined ONCE so a future 5th strategy
# only requires adding a row here + one entry in pair_config (Pitfall #4 closed).
#
#   session_key   — string passed to is_tradeable_session() (Phase 8.5 SESS-04)
#   timeframe     — string passed to is_tradeable_session() (M15/H1/DAILY)
#   size_mult     — PairConfig attribute name (per-strategy size mult — D-04)
#   sharpe_key    — index into SHARPE_4YR[pair][...] for D-08 tie-break
# ─────────────────────────────────────────────────────────────────────────────
_STRATEGY_META: dict["Strategy", tuple[str, str, str, str]] = {}  # populated below


# Iteration order: swing first, then intraday (CONTEXT D-07 / ROUT-02).
_ITERATION_ORDER: tuple["Strategy", ...] = ()  # populated below


# MIN_SHARPE: D-08 threshold for matrix-Sharpe gate. Mirrors Phase 8.5 SHARPE_GOOD.
# The pair_config.allow_* flags ALREADY encode a 0.5 threshold (Phase 7), so this
# value is a defensive belt-and-braces additional check that scales with future
# pair_config edits — it does not exclude pairs the matrix already disabled.
MIN_SHARPE: float = 0.3


def _init_strategy_metadata() -> None:
    """Populate _STRATEGY_META + _ITERATION_ORDER after Strategy enum is defined."""
    global _STRATEGY_META, _ITERATION_ORDER
    _STRATEGY_META = {
        Strategy.DAILY_SWING: ("swing",     "DAILY", "swing_size_mult",     "swing"),
        Strategy.H1_SCALP:    ("scalp",     "H1",    "scalp_size_mult",     "h1_scalp"),
        Strategy.H1_MOMENTUM: ("momentum",  "H1",    "momentum_size_mult",  "h1_momentum"),
        Strategy.M15_SCALP:   ("m15_scalp", "M15",   "m15_size_mult",       "m15_scalp"),
    }
    _ITERATION_ORDER = (
        Strategy.DAILY_SWING, Strategy.H1_SCALP, Strategy.H1_MOMENTUM, Strategy.M15_SCALP,
    )


_init_strategy_metadata()


def _classify_session(hour_utc: int) -> str:
    """UTC hour -> coarse session string for RAG queries.

    Matches V1 RAG vocabulary used by RAGSignalFilter.score_signal().
    Tokyo / London / NY are the three principal trading sessions.
    """
    if 0 <= hour_utc < 9:
        return "TOKYO"
    if 7 <= hour_utc < 16:
        return "LONDON"
    if 13 <= hour_utc < 22:
        return "NY"
    return "OFF"


def _infer_direction(market_data) -> "Direction | None":
    """Mean-reversion direction inference from z-scores.

    Per CONTEXT D-01 prose + RESEARCH §4: z<0 -> LONG (price below mean -> buy);
    z>0 -> SHORT (price above mean -> sell). Threshold 2.0 ensures we only
    dispatch when there is actually a tradeable z-score signal (otherwise
    return None -> "no_signal_direction" log).
    """
    z = getattr(market_data, "daily_z", None)
    if z is None:
        return None
    if z <= -2.0:
        return Direction.LONG
    if z >= 2.0:
        return Direction.SHORT
    return None


class StrategyRouter:
    """4-gate router (CONTEXT D-05 / D-06).

    Composes four upstream gates into a single typed dispatch:

        Gate 1 (Regime):   read-only via OnlineRegimeFilter.current_state_prob()
        Gate 2 (Session):  is_tradeable_session() per Phase 8.5 SESS-04
        Gate 3 (Matrix):   pair_config.allow_<strategy> + SHARPE_4YR >= MIN_SHARPE
        Gate 4 (RAG):      RAGSignalFilter.score_signal() action != SKIP

    ROUT-02 swing-first priority: DAILY_SWING dispatched immediately if it
    passes all gates. If a DAILY_SWING is already open on the pair, ALL
    strategies (including swing itself) are skipped on this bar — pair is
    cooled-down until the swing closes.

    ROUT-03 same-pair direction-conflict: any open position with a direction
    opposite to the proposed direction blocks the dispatch (pair-level scope
    per D-10; strategy-agnostic). The conflict counter increments for each
    rejection so the simulator can report it without a heuristic (WARN #5).

    D-08 tie-break: when multiple intraday strategies pass all gates on the
    same bar, the one with the highest SHARPE_4YR[pair][sharpe_key] wins.

    Logging: every route() call emits exactly one structured log record at
    DEBUG level — `gate_blocked` (with gate name + pair + strategy + ts) on
    None return, `dispatched` (with full RouteDecision) on success.
    """

    def __init__(
        self,
        regime_detectors: dict[str, "OnlineRegimeFilter"],
        rag_filter: "RAGSignalFilter",
        position_store: PositionStore,
        pair_config: dict[str, PairConfig],
    ) -> None:
        self.regime_detectors = regime_detectors
        self.rag_filter       = rag_filter
        self.position_store   = position_store
        self.pair_config      = pair_config
        # ROUT-03 telemetry — incremented inside _direction_conflict (D-10).
        self._direction_conflict_count: int = 0

    @property
    def direction_conflict_count(self) -> int:
        """Total direction-conflicts rejected (ROUT-03 telemetry — WARN #5)."""
        return self._direction_conflict_count

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────
    def route(self, pair: str, timestamp: datetime, market_data) -> RouteDecision | None:
        """4-gate dispatch with swing-first iteration + direction conflict (D-01..D-10).

        Returns RouteDecision when ALL gates pass for the selected strategy, or
        None when ANY gate fails (D-02 single sentinel).
        """
        cfg = self.pair_config.get(pair)
        if cfg is None:
            self._log_blocked(pair, None, timestamp, "unknown_pair")
            return None

        # Gate 1 (cheapest): regime — read-only via current_state_prob (Pitfall #6).
        regime_filter = self.regime_detectors.get(pair)
        if regime_filter is None:
            self._log_blocked(pair, None, timestamp, "no_regime_detector")
            return None
        # Local import to avoid load-time cycle through .regime package
        from .regime.types import RegimeState
        regime_state, regime_conf = regime_filter.current_state_prob()
        if regime_state == RegimeState.CRISIS:
            self._log_blocked(pair, None, timestamp, "regime_crisis")
            return None

        # ROUT-02 pair cooldown: if a DAILY_SWING is already open on this pair,
        # ALL strategies (including swing itself) are skipped this bar — the
        # pair is effectively cooled-down until the swing closes (D-07).
        swing_open = any(
            pos.strategy == Strategy.DAILY_SWING
            for pos in self.position_store.open_positions(pair)
        )

        # Iterate strategies in D-07 order; collect intraday candidates for
        # D-08 tie-break.
        intraday_candidates: list[RouteDecision] = []
        for strategy in _ITERATION_ORDER:
            # Matrix gate part 1 — strategy disabled at the pair level.
            if not self._matrix_enabled(cfg, strategy):
                self._log_blocked(pair, strategy, timestamp, "matrix_allow_false")
                continue
            # ROUT-02 cooldown — short-circuit ALL strategies if swing-open.
            if swing_open:
                reason = (
                    "swing_already_open" if strategy == Strategy.DAILY_SWING
                    else "swing_open_skips_intraday"
                )
                self._log_blocked(pair, strategy, timestamp, reason)
                continue
            # Gates 2 (session) + 3b (matrix Sharpe) + 4 (RAG) +
            # direction-inference. Returns None on any gate fail.
            decision = self._evaluate_strategy(
                pair, strategy, timestamp, market_data, cfg, regime_conf,
            )
            if decision is None:
                continue
            # ROUT-03 / D-10 — pair-level direction conflict.
            if self._direction_conflict(pair, decision.direction):
                self._log_blocked(pair, strategy, timestamp, "direction_conflict")
                continue
            if strategy == Strategy.DAILY_SWING:
                # Swing-first: dispatch immediately, do NOT evaluate intraday.
                self._log_dispatched(pair, decision, timestamp)
                return decision
            intraday_candidates.append(decision)

        if not intraday_candidates:
            # All strategies blocked — at least one gate-blocked log was already
            # emitted in the loop. Emit a final sentinel for observability.
            self._log_blocked(pair, None, timestamp, "no_strategy_passed_all_gates")
            return None

        # D-08 tie-break: highest 4yr Sharpe wins.
        from .pair_config import SHARPE_4YR

        def _sharpe_for(d: RouteDecision) -> float:
            _sk, _tf, _sm, sharpe_key = _STRATEGY_META[d.strategy]
            return SHARPE_4YR.get(pair, {}).get(sharpe_key, 0.0)

        best = max(intraday_candidates, key=_sharpe_for)
        self._log_dispatched(pair, best, timestamp)
        return best

    # ──────────────────────────────────────────────────────────────────────
    # Gate predicates (private)
    # ──────────────────────────────────────────────────────────────────────
    def _matrix_enabled(self, cfg: PairConfig, strategy: "Strategy") -> bool:
        """Gate 3 part 1 — pair_config allow_* flag for the strategy."""
        return {
            Strategy.DAILY_SWING: cfg.allow_swing,
            Strategy.H1_SCALP:    cfg.allow_scalp,
            Strategy.H1_MOMENTUM: cfg.allow_momentum,
            Strategy.M15_SCALP:   cfg.allow_m15_scalp,
        }[strategy]

    def _evaluate_strategy(
        self,
        pair: str,
        strategy: "Strategy",
        timestamp: datetime,
        market_data,
        cfg: PairConfig,
        regime_conf: float,
    ) -> RouteDecision | None:
        """Run gates 2 (session) + 3b (Sharpe) + 4 (RAG) + direction inference."""
        # Local import — temporal_filters reads SESSION_RULES at module-load.
        # This is the canonical attachment point so test_session_blocks_dispatch
        # can monkeypatch v3_intelligence.temporal_filters.is_tradeable_session.
        from . import temporal_filters as _tf

        session_key, timeframe, size_field, sharpe_key = _STRATEGY_META[strategy]

        # Gate 2: session
        if not _tf.is_tradeable_session(pair, session_key, timeframe, timestamp):
            self._log_blocked(pair, strategy, timestamp, "session_not_tradeable")
            return None

        # Gate 3 part 2: matrix Sharpe (defensive — pair_config.allow_* already
        # encodes Phase 7's 0.5 threshold, but D-08 belt-and-braces).
        from .pair_config import SHARPE_4YR
        sharpe = SHARPE_4YR.get(pair, {}).get(sharpe_key, 0.0)
        if sharpe < MIN_SHARPE:
            self._log_blocked(pair, strategy, timestamp, "matrix_sharpe_below_threshold")
            return None

        # Direction inference (mean-reversion: z<=-2.0 -> LONG, z>=+2.0 -> SHORT).
        direction = _infer_direction(market_data)
        if direction is None:
            self._log_blocked(pair, strategy, timestamp, "no_signal_direction")
            return None

        # Gate 4: RAG (most expensive — runs LAST per D-05).
        rag_strategy_type = f"{strategy.value}_{direction.value}"
        session_str = _classify_session(timestamp.hour)
        rag_result = self.rag_filter.score_signal(
            symbol=pair,
            strategy_type=rag_strategy_type,
            session=session_str,
            daily_z=getattr(market_data, "daily_z", 0.0),
            h1_z=getattr(market_data, "h1_z", 0.0),
            vol_percentile=getattr(market_data, "vol_percentile", 0.5),
            hour_utc=timestamp.hour,
        )
        if rag_result.get("action") == "SKIP":
            self._log_blocked(pair, strategy, timestamp, "rag_skip")
            return None
        confidence = float(rag_result.get("confidence", 0.0))

        # size_mult per D-04 (with RESEARCH §3 fix for the size field name).
        base_size = float(getattr(cfg, size_field, 1.0))
        size_mult = min(1.0, base_size * regime_conf)

        return RouteDecision(
            strategy=strategy,
            direction=direction,
            confidence=confidence,
            size_mult=size_mult,
        )

    def _direction_conflict(self, pair: str, proposed: "Direction") -> bool:
        """ROUT-03 / D-10 — pair-level direction conflict.

        Increments self._direction_conflict_count when a conflict is detected so
        the simulator (Plan 04) can report an accurate rejection_count without
        a heuristic.
        """
        conflict = any(
            pos.direction != proposed
            for pos in self.position_store.open_positions(pair)
        )
        if conflict:
            self._direction_conflict_count += 1
        return conflict

    # ──────────────────────────────────────────────────────────────────────
    # Structured logging (CONTEXT D-02 / D-06)
    # ──────────────────────────────────────────────────────────────────────
    def _log_blocked(
        self,
        pair: str,
        strategy: "Strategy | None",
        timestamp: datetime,
        reason: str,
    ) -> None:
        _log.debug(
            "gate_blocked",
            extra={
                "pair":      pair,
                "strategy":  strategy.value if strategy is not None else None,
                "timestamp": str(timestamp),
                "reason":    reason,
            },
        )

    def _log_dispatched(
        self,
        pair: str,
        decision: RouteDecision,
        timestamp: datetime,
    ) -> None:
        _log.debug(
            "dispatched",
            extra={
                "pair":       pair,
                "strategy":   decision.strategy.value,
                "direction":  decision.direction.value,
                "confidence": decision.confidence,
                "size_mult":  decision.size_mult,
                "timestamp":  str(timestamp),
            },
        )


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
