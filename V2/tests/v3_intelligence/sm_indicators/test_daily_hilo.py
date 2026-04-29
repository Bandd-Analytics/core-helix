"""Tier 1 — SM_Daily_HiLo tests (Plan 12-02 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md
PHOD/PLOD = previous-day completed bar high/low (Pitfall 5 lookahead-bias
guard via shift(1)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from v3_intelligence.sm_indicators.daily_hilo import (
    DailyHiLoParams,
    compute_daily_hilo,
)


def test_returns_phod_plod_columns(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Spec Section 4 Outputs: result has phod / plod columns."""
    out = compute_daily_hilo(synthetic_ohlc_uptrend)
    assert "phod" in out.columns
    assert "plod" in out.columns


def test_phod_equals_prior_bar_high(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Spec Section 5 step 1: PHOD = High of prior bar (lookback_bars=1)."""
    out = compute_daily_hilo(synthetic_ohlc_uptrend)
    # bar i's PHOD == bar (i-1)'s High
    expected = synthetic_ohlc_uptrend["High"].shift(1)
    pd.testing.assert_series_equal(
        out["phod"], expected, check_names=False
    )


def test_plod_equals_prior_bar_low(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Spec Section 5 step 1: PLOD = Low of prior bar."""
    out = compute_daily_hilo(synthetic_ohlc_uptrend)
    expected = synthetic_ohlc_uptrend["Low"].shift(1)
    pd.testing.assert_series_equal(
        out["plod"], expected, check_names=False
    )


def test_first_n_bars_are_nan(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """First lookback_bars rows have NaN PHOD/PLOD (warmup / lookahead
    guard — Pitfall 5)."""
    out = compute_daily_hilo(synthetic_ohlc_uptrend)
    assert pd.isna(out["phod"].iloc[0])
    assert pd.isna(out["plod"].iloc[0])


def test_days_back_2(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """v2.01 snake: phod_2 column holds bar (i-2) high; phod remains shift(1)."""
    params = DailyHiLoParams(days_back=14)
    out = compute_daily_hilo(synthetic_ohlc_uptrend, params)
    # v2.01: primary phod is always shift(1) — yesterday's high
    expected_phod = synthetic_ohlc_uptrend["High"].shift(1)
    pd.testing.assert_series_equal(out["phod"], expected_phod, check_names=False)
    # snake history: phod_2 == shift(2)
    expected_phod2 = synthetic_ohlc_uptrend["High"].shift(2)
    pd.testing.assert_series_equal(out["phod_2"], expected_phod2, check_names=False)
