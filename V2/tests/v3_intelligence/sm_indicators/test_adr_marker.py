"""Tier 1 — SM_ADR_Marker tests (Plan 12-02 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md
Verified Updates 2026-04-27: ATRPeriod=14 (CORRECTED — was claimed 20).

Per spec Section 10:
  1. EURUSD H1 (5-digit) — today_open ± ADR/2 markers, 4-decimal price math
  2. USDJPY H1 (3-digit JPY) — pip math via SYMBOL_DIGITS detection
  3. GBPNZD partial-history fallback — first day after broker rollover

These RED scaffolds import the not-yet-existing compute_adr_marker; Wave 1
turns them GREEN.
"""
from __future__ import annotations

import pandas as pd
import pytest

from v3_intelligence.sm_indicators.adr_marker import (
    ADRMarkerParams,
    compute_adr_marker,
)


def test_returns_required_columns(ohlcv_eurusd_h1: pd.DataFrame) -> None:
    """Spec Section 4 Outputs: result has adr / marker_high / marker_low /
    marker_mid columns."""
    out = compute_adr_marker(ohlcv_eurusd_h1)
    for col in ("adr", "marker_high", "marker_low", "marker_mid"):
        assert col in out.columns, f"missing column: {col}"


def test_uses_verified_atr_period_14() -> None:
    """Verified Updates 2026-04-27: ATRPeriod=14 (was claimed 20).

    Hard-coded gate to prevent silent regression to the older 20-day
    convention.
    """
    assert ADRMarkerParams().atr_period == 14


def test_marker_high_minus_marker_low_equals_adr(
    ohlcv_eurusd_h1: pd.DataFrame,
) -> None:
    """Algebraic invariant per spec Section 5 step 3:
    marker_high - marker_low = ADR (today_open ± ADR/2 → range = ADR).
    """
    out = compute_adr_marker(ohlcv_eurusd_h1)
    diff = (out["marker_high"] - out["marker_low"]) - out["adr"]
    # Allow tiny float roundoff
    valid = diff.dropna()
    assert (valid.abs() < 1e-9).all(), "marker_high - marker_low must equal ADR"


def test_handles_jpy_pip_format(ohlcv_usdjpy_h1: pd.DataFrame) -> None:
    """JPY pair edge case (Pitfall: pip math).

    USDJPY is 3-digit; the compute function still returns numeric ADR in
    price units. Output prices must be in the JPY price range (>1.0) to
    confirm we're not mis-scaling to 5-digit pip arithmetic.
    """
    out = compute_adr_marker(ohlcv_usdjpy_h1)
    valid = out["marker_mid"].dropna()
    # USDJPY trades in 100-160 range over the 4yr window
    assert valid.min() > 50.0, "USDJPY marker_mid out of expected price range"
    assert valid.max() < 250.0, "USDJPY marker_mid out of expected price range"
    # ADR must be positive non-zero on real data
    valid_adr = out["adr"].dropna()
    assert (valid_adr > 0).all(), "ADR must be positive on real bars"


def test_manual_adr_override(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Verified Updates: UseManualADR=true bypasses ATR — ManualADRValuePips
    in pips converts to price (×0.0001 for 5-digit majors)."""
    params = ADRMarkerParams(use_manual_adr=True, manual_adr_value_pips=100)
    out = compute_adr_marker(synthetic_ohlc_uptrend, params)
    # 100 pips = 0.01 in price for 5-digit majors
    assert out["adr"].iloc[0] == pytest.approx(0.01)
    assert (out["adr"] - 0.01).abs().max() < 1e-9
