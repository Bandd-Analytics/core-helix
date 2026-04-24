"""4yr routing matrix tests (BKTS-02, BKTS-03, D-10/D-11/D-14).

Verifies the new V2/backtest/backtest_4yr_evaluate.py runner:
  - Produces a routing_matrix row for every one of the 5 active pairs
  - Each row contains sharpe (float), win_rate (float), trade_count (int)
  - `allow_scalp` / `allow_momentum` flag set True iff sharpe >= 0.5 AND trade_count >= 30
  - Below-threshold pairs are included with the allow flag False (NOT dropped)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest


ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]


def _synthetic_4yr_h1(seed: int) -> pd.DataFrame:
    """Build ~4yr of synthetic H1 bars (~24,000 rows) with OHLC + indicators."""
    rng = np.random.default_rng(seed)
    n = 24_000
    idx = pd.date_range("2022-04-24", periods=n, freq="h")
    close = 100 + np.cumsum(rng.normal(0.0, 0.05, n))
    open_ = np.r_[close[0], close[:-1]]
    df = pd.DataFrame({
        "Open": open_, "High": close + 0.1, "Low": close - 0.1, "Close": close,
        "atr": np.full(n, 0.5),
        "z_score": rng.normal(0, 1.5, n),
        "daily_z": rng.normal(0, 1.2, n),
    }, index=idx)
    return df


@pytest.fixture
def mock_4yr_data(tmp_path, monkeypatch) -> Path:
    """Write synthetic _H1_4yr.csv files for each active pair."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for i, sym in enumerate(ACTIVE_PAIRS):
        df = _synthetic_4yr_h1(seed=i + 1)
        df.to_csv(data_dir / f"{sym}_H1_4yr.csv")
    return data_dir


def test_runner_module_importable() -> None:
    """BKTS-02 / BKTS-03: backtest_4yr_evaluate.py exists and exposes run()."""
    from backtest.backtest_4yr_evaluate import run_4yr_evaluation  # noqa: F401


def test_scalp_routing_matrix(mock_4yr_data) -> None:
    """BKTS-02: H1 scalp produces a row for every one of the 5 active pairs."""
    from backtest.backtest_4yr_evaluate import run_4yr_evaluation

    result: dict[str, Any] = run_4yr_evaluation(
        strategy="scalp", data_dir=mock_4yr_data, pairs=ACTIVE_PAIRS,
    )
    assert set(result.keys()) == set(ACTIVE_PAIRS)
    for sym, row in result.items():
        assert "sharpe" in row and isinstance(row["sharpe"], float)
        assert "win_rate" in row and isinstance(row["win_rate"], float)
        assert "trade_count" in row and isinstance(row["trade_count"], int)
        assert "allow_flag" in row and isinstance(row["allow_flag"], bool)


def test_momentum_routing_matrix(mock_4yr_data) -> None:
    """BKTS-03: Momentum produces a row for every one of the 5 active pairs."""
    from backtest.backtest_4yr_evaluate import run_4yr_evaluation

    result = run_4yr_evaluation(
        strategy="momentum", data_dir=mock_4yr_data, pairs=ACTIVE_PAIRS,
    )
    assert set(result.keys()) == set(ACTIVE_PAIRS)
    for sym, row in result.items():
        for key in ("sharpe", "win_rate", "trade_count", "allow_flag"):
            assert key in row


def test_allow_flag_threshold_logic(mock_4yr_data) -> None:
    """D-10 + Open Questions #2: allow_flag is True iff sharpe >= 0.5 AND trade_count >= 30."""
    from backtest.backtest_4yr_evaluate import run_4yr_evaluation

    result = run_4yr_evaluation(
        strategy="scalp", data_dir=mock_4yr_data, pairs=ACTIVE_PAIRS,
    )
    for sym, row in result.items():
        expected = row["sharpe"] >= 0.5 and row["trade_count"] >= 30
        assert row["allow_flag"] == expected, \
            f"{sym}: allow_flag={row['allow_flag']} but sharpe={row['sharpe']} trades={row['trade_count']}"


def test_below_threshold_pair_not_dropped(mock_4yr_data) -> None:
    """D-11: Pairs that fail the Sharpe/trade threshold still appear with allow=False."""
    from backtest.backtest_4yr_evaluate import run_4yr_evaluation

    result = run_4yr_evaluation(
        strategy="scalp", data_dir=mock_4yr_data, pairs=ACTIVE_PAIRS,
    )
    # Every active pair must be present — no silent drops
    missing = set(ACTIVE_PAIRS) - set(result.keys())
    assert not missing, f"Missing pairs in routing matrix: {missing}"


def test_csv_report_schema(tmp_path, mock_4yr_data) -> None:
    """07-UI-SPEC.md: routing matrix CSV has the documented columns."""
    from backtest.backtest_4yr_evaluate import write_routing_matrix_csv, run_4yr_evaluation

    result = run_4yr_evaluation(
        strategy="scalp", data_dir=mock_4yr_data, pairs=ACTIVE_PAIRS,
    )
    csv_path = tmp_path / "matrix.csv"
    write_routing_matrix_csv(result, strategy="scalp", out_path=csv_path)

    df = pd.read_csv(csv_path)
    required = {"pair", "strategy", "sharpe", "win_rate", "trade_count",
                "min_trades_met", "sharpe_threshold_met",
                "routing_matrix_entry", "allow_flag"}
    assert required.issubset(df.columns), f"Missing cols: {required - set(df.columns)}"
    assert len(df) == len(ACTIVE_PAIRS)
