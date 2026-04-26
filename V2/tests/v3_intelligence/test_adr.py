"""compute_adr tests (INFRA-04 / D-18).

RED until Plan 04 lands V2/v3_intelligence/adr.py.
"""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


def _daily_df(n: int = 30, base: float = 145.0, range_pips: float = 0.5) -> pd.DataFrame:
    """Synthetic daily OHLC with deterministic H-L = range_pips per bar."""
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "Open":  [base] * n,
        "High":  [base + range_pips / 2] * n,
        "Low":   [base - range_pips / 2] * n,
        "Close": [base] * n,
        "Volume": [1000] * n,
    }, index=idx)


def test_compute_adr_returns_positive_float() -> None:
    """D-18: compute_adr returns a positive float."""
    from v3_intelligence import adr
    fake_df = _daily_df(30, range_pips=0.5)
    with patch.object(adr, "_load_daily_bars", return_value=fake_df):
        result = adr.compute_adr("USDJPY", "Daily", lookback_days=20)
        assert isinstance(result, float)
        assert result > 0


def test_compute_adr_equals_mean_high_low(synthetic_three_regime_returns=None) -> None:
    """D-18: compute_adr(N) == mean(H-L) over N most recent bars."""
    from v3_intelligence import adr
    fake_df = _daily_df(30, range_pips=0.5)
    with patch.object(adr, "_load_daily_bars", return_value=fake_df):
        result = adr.compute_adr("USDJPY", "Daily", lookback_days=20)
        # All bars have identical H-L=0.5 -> mean is 0.5 regardless of lookback
        assert abs(result - 0.5) < 1e-9


def test_compute_adr_uses_only_lookback_days() -> None:
    """D-18: ADR uses ONLY the last lookback_days bars (not entire history)."""
    from v3_intelligence import adr
    df_old = _daily_df(20, range_pips=10.0)
    df_new = _daily_df(20, range_pips=0.1)
    df_new.index = pd.date_range("2024-02-01", periods=20, freq="D")
    full = pd.concat([df_old, df_new])
    with patch.object(adr, "_load_daily_bars", return_value=full):
        result = adr.compute_adr("USDJPY", "Daily", lookback_days=20)
        assert abs(result - 0.1) < 1e-9, f"Got {result} — should reflect only recent 20 bars"


def test_compute_adr_signature() -> None:
    """D-18: signature is (pair: str, timeframe: str, lookback_days: int = 20) -> float."""
    import inspect
    from v3_intelligence import adr
    sig = inspect.signature(adr.compute_adr)
    params = list(sig.parameters)
    assert params[0] == "pair"
    assert params[1] == "timeframe"
    assert params[2] == "lookback_days"
    assert sig.parameters["lookback_days"].default == 20
