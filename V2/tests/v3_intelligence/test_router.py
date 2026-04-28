"""Phase 9 ROUT-01/02/03 unit tests (Wave 0 RED scaffold per CONTEXT D-17).

These 9 tests collect at scaffold time (Plan 01) but all fail when run because
StrategyRouter.route() raises NotImplementedError. Plan 02 turns them GREEN by
implementing the 4-gate decision chain (Regime -> Session -> Matrix -> RAG)
plus ROUT-02 swing-first priority + ROUT-03 same-pair direction conflict.

Test names follow CONTEXT D-17 verbatim:
    - test_route_decision_is_frozen_dataclass  (return-shape contract)
    - test_route_returns_typed_decision        (ROUT-01 valid dispatch)
    - test_regime_blocks_dispatch              (ROUT-01 gate 1)
    - test_session_blocks_dispatch             (ROUT-01 gate 2)
    - test_matrix_fail_blocks                  (ROUT-01 gate 3)
    - test_rag_below_threshold_blocks          (ROUT-01 gate 4)
    - test_swing_first_priority                (ROUT-02 priority)
    - test_intraday_skipped_when_swing_open    (ROUT-02 skip — BLOCKER #1 from
                                                 plan iter 1 review)
    - test_direction_conflict_rejects          (ROUT-03 same-pair conflict)

Fixtures consumed (added in Task 4 conftest extension):
    mock_regime_detectors                   — TRENDING / 0.85 (gate 1 PASSES)
    mock_regime_detectors_crisis            — CRISIS / 0.95 (gate 1 FAILS)
    mock_rag_filter                         — confidence 0.55 / TAKE (gate 4 PASSES)
    mock_rag_filter_low                     — confidence 0.10 / SKIP (gate 4 FAILS)
    mock_position_store                     — empty InMemoryPositionStore
    mock_pair_config_permissive             — USDJPY all allow_* True
    mock_pair_config_disabled               — USDJPY all allow_* False

DO NOT @pytest.mark.skip / xfail any of these — they MUST collect and FAIL
RED per CONTEXT D-17 Pitfall #5 (RED-first scaffold mandatory).
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from v3_intelligence.router import (
    StrategyRouter, RouteDecision, Strategy, Direction,
    OpenPosition, InMemoryPositionStore,
)
from v3_intelligence.regime.types import RegimeState  # noqa: F401  (used by Plan 02)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_snapshot(pair: str = "USDJPY", ts: datetime | None = None, **overrides):
    """Minimal market_data shape — Plan 02 will tighten the BarSnapshot dataclass.

    Default fields are crafted to mock a clean LONG mean-reversion signal on
    USDJPY (negative daily_z / negative h1_z) so a permissive run produces
    DAILY_SWING LONG.
    """
    base = dict(
        pair=pair,
        timestamp=ts or datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        close=145.50,
        log_return=0.0001,
        daily_z=-2.5,
        h1_z=-1.8,
        vol_percentile=0.5,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ─────────────────────────────────────────────────────────────────────────────
# Return-shape contract (CONTEXT D-01)
# ─────────────────────────────────────────────────────────────────────────────

def test_route_decision_is_frozen_dataclass():
    """RouteDecision must be a frozen dataclass with the 4 typed fields per D-01.

    This is a pure-stub contract test — no router invocation needed; just
    constructs RouteDecision and asserts immutability.
    """
    rd = RouteDecision(
        strategy=Strategy.DAILY_SWING,
        direction=Direction.LONG,
        confidence=0.5,
        size_mult=1.0,
    )
    assert rd.strategy is Strategy.DAILY_SWING
    assert rd.direction is Direction.LONG
    assert rd.confidence == 0.5
    assert rd.size_mult == 1.0
    # Frozen guarantee
    with pytest.raises(FrozenInstanceError):
        rd.strategy = Strategy.H1_SCALP  # type: ignore[misc]
    # Hash-able (frozen dataclasses are hashable by default)
    assert hash(rd) == hash(rd)


# ─────────────────────────────────────────────────────────────────────────────
# 4-gate chain (ROUT-01)
# ─────────────────────────────────────────────────────────────────────────────

def test_route_returns_typed_decision(
    mock_regime_detectors,
    mock_rag_filter,
    mock_position_store,
    mock_pair_config_permissive,
):
    """ROUT-01: with all 4 gates permissive, route() returns a typed RouteDecision."""
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        mock_position_store,
        mock_pair_config_permissive,
    )
    decision = router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    )
    assert isinstance(decision, RouteDecision)
    assert decision.strategy in Strategy
    assert decision.direction in Direction
    assert 0.0 <= decision.confidence <= 1.0
    assert 0.0 <= decision.size_mult <= 1.0


def test_regime_blocks_dispatch(
    mock_regime_detectors_crisis,
    mock_rag_filter,
    mock_position_store,
    mock_pair_config_permissive,
):
    """ROUT-01 gate 1: regime CRISIS blocks all dispatches."""
    router = StrategyRouter(
        mock_regime_detectors_crisis,
        mock_rag_filter,
        mock_position_store,
        mock_pair_config_permissive,
    )
    assert router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    ) is None


def test_session_blocks_dispatch(
    monkeypatch,
    mock_regime_detectors,
    mock_rag_filter,
    mock_position_store,
    mock_pair_config_permissive,
):
    """ROUT-01 gate 2: is_tradeable_session=False blocks all dispatches."""
    # Plan 02 will import temporal_filters; force the predicate False so gate
    # 2 always fails. monkeypatch reverts at test teardown.
    monkeypatch.setattr(
        "v3_intelligence.temporal_filters.is_tradeable_session",
        lambda *a, **kw: False,
    )
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        mock_position_store,
        mock_pair_config_permissive,
    )
    assert router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    ) is None


def test_matrix_fail_blocks(
    mock_regime_detectors,
    mock_rag_filter,
    mock_position_store,
    mock_pair_config_disabled,
):
    """ROUT-01 gate 3: all allow_* flags False -> matrix gate always fails."""
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        mock_position_store,
        mock_pair_config_disabled,
    )
    assert router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    ) is None


def test_rag_below_threshold_blocks(
    mock_regime_detectors,
    mock_rag_filter_low,
    mock_position_store,
    mock_pair_config_permissive,
):
    """ROUT-01 gate 4: RAG action=SKIP / confidence=0.10 blocks dispatch."""
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter_low,
        mock_position_store,
        mock_pair_config_permissive,
    )
    assert router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    ) is None


# ─────────────────────────────────────────────────────────────────────────────
# Swing-first priority (ROUT-02)
# ─────────────────────────────────────────────────────────────────────────────

def test_swing_first_priority(
    mock_regime_detectors,
    mock_rag_filter,
    mock_position_store,
    mock_pair_config_permissive,
):
    """ROUT-02: when both DAILY_SWING and intraday strategies pass all gates,
    DAILY_SWING is selected (D-07 iteration order — swing first).
    """
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        mock_position_store,
        mock_pair_config_permissive,
    )
    decision = router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    )
    assert decision is not None, "Permissive setup should produce a dispatch"
    assert decision.strategy == Strategy.DAILY_SWING, (
        f"ROUT-02 swing-first priority violated: got {decision.strategy} "
        f"when DAILY_SWING was eligible"
    )


def test_intraday_skipped_when_swing_open(
    mock_regime_detectors,
    mock_rag_filter,
    mock_pair_config_permissive,
):
    """ROUT-02 (BLOCKER #1 from plan revision iter 1): when a DAILY_SWING is
    already open on USDJPY, intraday strategies must be skipped.

    Acceptable Plan 02 behaviour:
        - return None (no double-fire on swing AND no intraday backfill)

    This was the test that drove the iter 1 revision — the original plan
    didn't gate intraday strategies behind the open-swing check, leaking
    duplicate dispatches into the simulator.
    """
    store = InMemoryPositionStore()
    store.open(OpenPosition(
        pair="USDJPY",
        direction=Direction.LONG,
        strategy=Strategy.DAILY_SWING,
        opened_at=datetime(2025, 5, 31, 14, 0, tzinfo=timezone.utc),
    ))
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        store,
        mock_pair_config_permissive,
    )
    decision = router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        _build_snapshot(),
    )
    assert decision is None, (
        f"ROUT-02 intraday-skip violated: got {decision} when "
        f"DAILY_SWING already open on USDJPY"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Direction conflict (ROUT-03)
# ─────────────────────────────────────────────────────────────────────────────

def test_direction_conflict_rejects(
    mock_regime_detectors,
    mock_rag_filter,
    mock_pair_config_permissive,
):
    """ROUT-03 (CONTEXT D-10 pair-level): when a LONG is open on USDJPY and
    market_data implies a SHORT signal (positive daily_z), router returns None.
    """
    store = InMemoryPositionStore()
    store.open(OpenPosition(
        pair="USDJPY",
        direction=Direction.LONG,
        strategy=Strategy.DAILY_SWING,
        opened_at=datetime(2025, 5, 31, 14, 0, tzinfo=timezone.utc),
    ))
    # Positive Z-score under mean-reversion -> SHORT signal
    snapshot = _build_snapshot(daily_z=+2.5, h1_z=+1.8)
    router = StrategyRouter(
        mock_regime_detectors,
        mock_rag_filter,
        store,
        mock_pair_config_permissive,
    )
    decision = router.route(
        "USDJPY",
        datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc),
        snapshot,
    )
    assert decision is None, (
        f"ROUT-03 direction-conflict violated: got {decision} when "
        f"open LONG on USDJPY conflicts with proposed SHORT"
    )
