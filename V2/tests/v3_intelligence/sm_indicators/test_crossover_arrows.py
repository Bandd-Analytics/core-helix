"""Tier 1 — SM_Crossover_Arrows tests (Plan 12-02 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md
EMA 5/13 crossover (MMM Book p. 47); cross detected at bar[i] vs bar[i-1]
to avoid lookahead/repaint (Pitfall 5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from v3_intelligence.sm_indicators.crossover_arrows import (
    CrossoverArrowsParams,
    compute_crossover_arrows,
)


def test_returns_ema_columns_and_signal(
    synthetic_ohlc_uptrend: pd.DataFrame,
) -> None:
    """Spec Section 4 Outputs: result has ema_fast / ema_slow / cross_signal
    columns."""
    out = compute_crossover_arrows(synthetic_ohlc_uptrend)
    assert "ema_fast" in out.columns
    assert "ema_slow" in out.columns
    assert "cross_signal" in out.columns


def test_default_periods_v2() -> None:
    """v2.00: EMA 7/13 (operator-tuned 2026-04-28). Original MMM Book
    p. 47 reference is 5/13; the operator's working setup uses the
    slightly slower 7-period fast EMA to filter intra-bar noise.
    """
    p = CrossoverArrowsParams()
    assert p.fast == 7
    assert p.slow == 13


def test_bullish_cross_in_uptrend(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """In a sustained uptrend, EMA(5) starts below EMA(13) due to EMA
    initialization, then crosses above as the trend builds. We expect at
    least one BUY signal in the synthetic 100-bar uptrend.
    """
    out = compute_crossover_arrows(synthetic_ohlc_uptrend)
    assert (out["cross_signal"] == "BUY").any(), (
        "Expected at least one bullish cross in synthetic uptrend"
    )


def test_no_cross_in_doji_consolidation(synthetic_doji: pd.DataFrame) -> None:
    """Pure doji consolidation: Open=Close=mid for every bar → both EMAs
    converge to mid and never cross. cross_signal stays NONE.
    """
    out = compute_crossover_arrows(synthetic_doji)
    assert (out["cross_signal"] == "NONE").all(), (
        "Doji consolidation must not produce crossover signals"
    )


def test_cross_signal_values_constrained(
    synthetic_ohlc_uptrend: pd.DataFrame,
) -> None:
    """cross_signal column may only contain BUY / SELL / NONE."""
    out = compute_crossover_arrows(synthetic_ohlc_uptrend)
    valid = {"BUY", "SELL", "NONE"}
    actual = set(out["cross_signal"].unique())
    assert actual <= valid, f"unexpected cross_signal values: {actual - valid}"
