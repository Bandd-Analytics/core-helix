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
