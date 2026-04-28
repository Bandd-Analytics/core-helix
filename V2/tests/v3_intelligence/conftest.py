"""Phase 8 test fixtures (REGM-01..04 / D-16 parity baseline).

Provides:
    synthetic_three_regime_returns — deterministic (seed=42, T=1000)
                                      3-regime mixture; reused by V1 capture
                                      and V2 parity tests.
    v1_baseline                    — np.load() of parity_baseline.npz committed
                                      to this dir (one-time captured from V1).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

BASELINE_PATH = Path(__file__).resolve().parent / "parity_baseline.npz"


@pytest.fixture(scope="session")
def synthetic_three_regime_returns():
    """Deterministic 3-regime mixture; seed=42, T=1000.

    Ground truth state sequence: 600 trending, 300 mean-rev, 100 crisis,
    then shuffled. Per-state mu/sigma chosen so unconditional variance is
    monotonically increasing across the three regimes (REGM-02 testable).
    Returns: (returns: np.ndarray (T,), state_seq: np.ndarray (T,) int).
    """
    rng = np.random.default_rng(42)
    T = 1000
    state_seq = np.concatenate([
        np.zeros(600, dtype=int),
        np.ones(300, dtype=int),
        np.full(100, 2, dtype=int),
    ])
    rng.shuffle(state_seq)
    mus    = np.array([1e-5,  0.0,    -2e-5])
    sigmas = np.array([1e-3,  3e-3,   8e-3])
    returns = rng.normal(loc=mus[state_seq], scale=sigmas[state_seq])
    return returns, state_seq


@pytest.fixture(scope="session")
def v1_baseline():
    """Loaded baseline (recorded once from V1 detector). Sourced from npz."""
    if not BASELINE_PATH.exists():
        pytest.skip(f"parity_baseline.npz not present at {BASELINE_PATH}")
    return np.load(BASELINE_PATH)


# Phase 8.4 INFRA-01..04 fixtures live in conftest_infra.py (Plan 01 chose this
# filename to keep Phase 8.4 scaffold visually separate from the Phase 8 baseline
# fixtures above). Pytest only auto-discovers files literally named conftest.py,
# so we re-export the Phase 8.4 fixtures from here. This preserves
# conftest_infra.py as canonical source while making fixtures usable in
# test_cache.py / test_learning_loop.py / test_adr.py / etc.
from .conftest_infra import (  # noqa: E402, F401
    sample_trade,
    in_memory_logger,
    mock_chroma_collection,
    mock_psycopg_conn,
    synthetic_trades_factory,
    synthetic_bars_with_spikes,
)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 ROUT-01..04 fixtures (added 2026-04-28 by Plan 09-01 Task 4).
#
# MUST NOT shadow Phase 8 (synthetic_three_regime_returns, v1_baseline) nor
# Phase 8.4 (sample_trade, in_memory_logger, mock_chroma_collection,
# mock_psycopg_conn, synthetic_trades_factory, synthetic_bars_with_spikes)
# fixtures — those are imported above and remain canonical.
#
# Fixtures provided (7):
#   mock_regime_detectors           — 8 pairs, TRENDING/0.85 (gate 1 PASSES)
#   mock_regime_detectors_crisis    — 8 pairs, CRISIS/0.95 (gate 1 FAILS)
#   mock_rag_filter                 — confidence 0.55, action TAKE (gate 4 PASSES)
#   mock_rag_filter_low             — confidence 0.10, action SKIP (gate 4 FAILS)
#   mock_position_store             — empty InMemoryPositionStore
#   mock_pair_config_permissive     — USDJPY all allow_* True (gate 3 PASSES)
#   mock_pair_config_disabled       — USDJPY all allow_* False (gate 3 FAILS)
# ─────────────────────────────────────────────────────────────────────────────
from v3_intelligence.router import (  # noqa: E402
    Strategy as _RouterStrategy,            # noqa: F401  (referenced in fixtures below)
    Direction as _RouterDirection,          # noqa: F401
    OpenPosition as _RouterOpenPosition,    # noqa: F401
    InMemoryPositionStore as _RouterInMemoryStore,
)
from v3_intelligence.regime.types import RegimeState as _RegimeState  # noqa: E402
from v3_intelligence.pair_config import PairConfig as _PairConfig  # noqa: E402


class _FakeOnlineRegimeFilter:
    """Test double — exposes current_state_prob() and update() without HMM math.

    Plan 02 will add OnlineRegimeFilter.current_state_prob() per RESEARCH §1
    Pitfall #12; this fake mirrors the planned tuple[RegimeState, float]
    shape so router unit tests do not depend on the live HMM-GARCH stack.
    """

    def __init__(self, state=_RegimeState.TRENDING, prob=0.85):
        self._state = state
        self._prob = prob

    def current_state_prob(self):
        return (self._state, self._prob)

    def update(self, return_value: float):
        return (self._state, self._prob)

    @property
    def state_probs(self):
        arr = np.full(3, (1 - self._prob) / 2)
        arr[int(self._state)] = self._prob
        return arr


@pytest.fixture
def mock_regime_detectors():
    """All 8 PAIR_CONFIGS pairs map to TRENDING / 0.85 — gate 1 PASSES."""
    from v3_intelligence.pair_config import PAIR_CONFIGS
    return {pair: _FakeOnlineRegimeFilter(_RegimeState.TRENDING, 0.85) for pair in PAIR_CONFIGS}


@pytest.fixture
def mock_regime_detectors_crisis():
    """All 8 PAIR_CONFIGS pairs map to CRISIS / 0.95 — gate 1 FAILS."""
    from v3_intelligence.pair_config import PAIR_CONFIGS
    return {pair: _FakeOnlineRegimeFilter(_RegimeState.CRISIS, 0.95) for pair in PAIR_CONFIGS}


class _FakeRagFilter:
    """Test double for RAGSignalFilter.

    Mirrors the V1 score_signal() return shape (RESEARCH §4) so Plan 02 router
    tests can construct deterministic gate-4 outcomes without ChromaDB.
    """

    def __init__(self, confidence: float = 0.55, action: str = "TAKE"):
        self._conf = confidence
        self._action = action

    def score_signal(self, **kwargs):
        return {
            "confidence": self._conf,
            "sample_size": 20,
            "avg_pnl": 0.001,
            "size_modifier": 1.0,
            "action": self._action,
            "reason": "test-fixture",
        }

    def index_trade(self, trade):
        # Plan 04 simulator calls this on close; no-op for unit tests.
        pass


@pytest.fixture
def mock_rag_filter():
    """confidence=0.55, action=TAKE — gate 4 PASSES."""
    return _FakeRagFilter(confidence=0.55, action="TAKE")


@pytest.fixture
def mock_rag_filter_low():
    """confidence=0.10, action=SKIP — gate 4 FAILS."""
    return _FakeRagFilter(confidence=0.10, action="SKIP")


@pytest.fixture
def mock_position_store():
    """Empty InMemoryPositionStore — no positions on any pair."""
    return _RouterInMemoryStore()


@pytest.fixture
def mock_pair_config_permissive():
    """USDJPY with all 4 strategies enabled (allow_* True) — gate 3 PASSES."""
    cfg = _PairConfig(
        symbol="USDJPY",
        tier=1,
        swing_size_mult=1.0,
        scalp_size_mult=1.0,
        momentum_size_mult=1.0,
        m15_size_mult=1.0,
        allow_swing=True,
        allow_scalp=True,
        allow_momentum=True,
        allow_m15_scalp=True,
        notes="permissive test fixture",
    )
    return {"USDJPY": cfg}


@pytest.fixture
def mock_pair_config_disabled():
    """USDJPY with all 4 strategies disabled (allow_* False) — gate 3 FAILS."""
    cfg = _PairConfig(
        symbol="USDJPY",
        tier=4,
        swing_size_mult=1.0,
        scalp_size_mult=1.0,
        momentum_size_mult=1.0,
        m15_size_mult=1.0,
        allow_swing=False,
        allow_scalp=False,
        allow_momentum=False,
        allow_m15_scalp=False,
        notes="disabled test fixture",
    )
    return {"USDJPY": cfg}
