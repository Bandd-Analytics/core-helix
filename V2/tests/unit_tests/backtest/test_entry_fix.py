"""
BKTS-01 unit tests — next-bar-open entry fix.

Tests:
  test_scalp_entry_price_is_next_bar_open    — every trade.entry_price == h1.iloc[i+1]['Open']
  test_momentum_entry_price_is_next_bar_open — same invariant for run_momentum_with_cfg
  test_sharpe_delta                          — Sharpe on synthetic drift scalp < 1.63 (biased baseline)
  test_loop_bound_prevents_index_error       — end-of-data signal does not crash
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ── path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]   # V2/
sys.path.insert(0, str(ROOT))

from backtest.backtest_evaluate_all import Evaluator, metrics
from v3_intelligence.pair_config import PairConfig

# ── synthetic data factory ───────────────────────────────────────────────────

def _make_h1(n: int = 300, drift: float = 0.0001) -> pd.DataFrame:
    """Upward-drifting H1 OHLCV with a 20-period Z-score that oscillates strongly."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="h")

    close = 1.10 + np.cumsum(rng.normal(drift, 0.0005, n))
    open_ = close - rng.uniform(0.0001, 0.0003, n)
    high  = close + rng.uniform(0.0001, 0.0004, n)
    low   = close - rng.uniform(0.0001, 0.0004, n)
    vol   = rng.integers(500, 2000, n).astype(float)

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )
    return df


def _make_daily(n_days: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-01", periods=n_days, freq="D")
    close = 1.10 + np.cumsum(rng.normal(0.0, 0.001, n_days))
    open_ = close - 0.0001
    high  = close + 0.001
    low   = close - 0.001
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 1000.0},
        index=idx,
    )


def _scalp_cfg(sym: str = "AUDNZD") -> PairConfig:
    return PairConfig(
        symbol=sym, tier=2,
        scalp_size_mult=0.5,
        scalp_z_threshold=2.0,
        scalp_target_atr=2.0,
        scalp_stop_atr=0.75,
        scalp_max_bars=4,
        allow_swing=False, allow_scalp=True, allow_momentum=False, allow_m15_scalp=False,
    )


def _momentum_cfg(sym: str = "AUDNZD") -> PairConfig:
    return PairConfig(
        symbol=sym, tier=2,
        momentum_size_mult=0.3,
        momentum_z_threshold=1.5,
        momentum_daily_z_threshold=1.5,
        momentum_target_atr=1.0,
        momentum_stop_atr=0.5,
        momentum_max_bars=2,
        allow_swing=False, allow_scalp=False, allow_momentum=True, allow_m15_scalp=False,
    )


def _evaluator() -> Evaluator:
    return Evaluator(
        ROOT / "data",
        enable_rag=False,
        enable_logging=False,
        enable_changepoint=False,
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _locate_entry_bar(h1: pd.DataFrame, trade: dict) -> int:
    """Return the integer position of the entry bar in h1 using entry_bar_ts."""
    ts = trade["entry_bar_ts"]
    return h1.index.get_loc(ts)


# ── tests ────────────────────────────────────────────────────────────────────

def test_scalp_entry_price_is_next_bar_open():
    """Every scalp trade's entry_price must equal h1.iloc[entry_bar + 1]['Open']."""
    ev     = _evaluator()
    h1     = _make_h1(n=500)
    daily  = _make_daily()
    cfg    = _scalp_cfg()

    trades_df = ev.run_scalp_with_cfg("AUDNZD", daily, h1, cfg)
    if trades_df.empty:
        pytest.skip("No trades generated on synthetic data — adjust parameters")

    assert "entry_bar_ts" in trades_df.columns, (
        "run_scalp_with_cfg must record 'entry_bar_ts' in position dict"
    )

    for _, row in trades_df.iterrows():
        i       = _locate_entry_bar(h1, row)
        expected = h1.iloc[i + 1]["Open"]
        actual   = row["entry_price"]
        assert math.isclose(actual, expected, rel_tol=1e-9), (
            f"entry_price {actual} != next-bar Open {expected} (bar {i})"
        )


def test_momentum_entry_price_is_next_bar_open():
    """Every momentum trade's entry_price must equal h1.iloc[entry_bar + 1]['Open']."""
    ev     = _evaluator()
    h1     = _make_h1(n=500)
    daily  = _make_daily()
    cfg    = _momentum_cfg()

    trades_df = ev.run_momentum_with_cfg("AUDNZD", daily, h1, cfg)
    if trades_df.empty:
        pytest.skip("No trades generated on synthetic data — adjust parameters")

    assert "entry_bar_ts" in trades_df.columns, (
        "run_momentum_with_cfg must record 'entry_bar_ts' in position dict"
    )

    for _, row in trades_df.iterrows():
        i        = _locate_entry_bar(h1, row)
        expected = h1.iloc[i + 1]["Open"]
        actual   = row["entry_price"]
        assert math.isclose(actual, expected, rel_tol=1e-9), (
            f"entry_price {actual} != next-bar Open {expected} (bar {i})"
        )


def test_sharpe_delta():
    """Corrected Sharpe on synthetic upward drift must be < 1.63 (biased baseline)."""
    BIASED_BASELINE_SCALP = 1.63

    ev     = _evaluator()
    h1     = _make_h1(n=2000, drift=0.0002)
    daily  = _make_daily(n_days=200)
    cfg    = _scalp_cfg()

    trades_df = ev.run_scalp_with_cfg("AUDNZD", daily, h1, cfg)
    if trades_df.empty:
        pytest.skip("No trades generated — adjust parameters")

    m = metrics(trades_df)
    assert m is not None, "metrics() returned None on non-empty trades DataFrame"
    corrected_sharpe = float(m["sharpe"])

    assert corrected_sharpe < BIASED_BASELINE_SCALP, (
        f"Corrected Sharpe {corrected_sharpe:.4f} must be < biased baseline {BIASED_BASELINE_SCALP}. "
        "The fix has not reduced Sharpe — entry bias may still be present."
    )


def test_loop_bound_prevents_index_error():
    """Feeding a DataFrame whose LAST bar triggers a signal must NOT raise IndexError."""
    ev    = _evaluator()
    daily = _make_daily()
    cfg   = _scalp_cfg()

    # Build a minimal H1 frame where the very last bar has an extreme Z-score
    # to maximise chance the last-bar entry would be attempted
    h1 = _make_h1(n=130)
    # Force the last bar to have a very high Close to create Z-score extreme
    h1.iloc[-1, h1.columns.get_loc("Close")] = h1["Close"].mean() + 5 * h1["Close"].std()

    try:
        trades_df = ev.run_scalp_with_cfg("AUDNZD", daily, h1, cfg)
    except IndexError as exc:
        pytest.fail(
            f"IndexError raised — loop bound not adjusted to len(h1)-1: {exc}"
        )
    # Function must return a DataFrame (possibly empty)
    assert isinstance(trades_df, pd.DataFrame)
