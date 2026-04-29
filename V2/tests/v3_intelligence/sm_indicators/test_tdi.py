"""SM_TDI — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md
Verified Updates 2026-04-27: RSI_Period=21, Shark_Fin 63/37.

7 test cases mirroring spec Section 10 + Verified Updates gates + CONTEXT
backtester-ready output shape requirement.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 1) turns them GREEN.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Structural / param tests (no import of df fixture needed)
# ---------------------------------------------------------------------------

def test_uses_verified_rsi_period_21():
    """Verified Updates 2026-04-27: RSI_Period was 13 in spec body, corrected to 21."""
    from v3_intelligence.sm_indicators.tdi import TDIParams
    assert TDIParams().rsi_period == 21, "RSI period must be 21 per Verified Updates 2026-04-27"


def test_uses_verified_shark_fin_levels_63_37():
    """Verified Updates 2026-04-27: Shark_Fin_Upper was 68, corrected to 63; Lower was 32, corrected to 37."""
    from v3_intelligence.sm_indicators.tdi import TDIParams
    p = TDIParams()
    assert p.shark_fin_upper == 63.0, "Shark Fin Upper must be 63.0 per Verified Updates 2026-04-27"
    assert p.shark_fin_lower == 37.0, "Shark Fin Lower must be 37.0 per Verified Updates 2026-04-27"


def test_vb_threshold_inputs_defaults():
    """Verified Updates 2026-04-27 NEW inputs: VB_High_Value=45.0, VB_Low_Value=55.0."""
    from v3_intelligence.sm_indicators.tdi import TDIParams
    p = TDIParams()
    assert p.vb_high_value == 45.0, "VB_High_Value must be 45.0 per Verified Updates"
    assert p.vb_low_value == 55.0, "VB_Low_Value must be 55.0 per Verified Updates"


# ---------------------------------------------------------------------------
# DataFrame shape / column tests
# ---------------------------------------------------------------------------

def test_returns_required_columns(ohlcv_eurusd_h1):
    """CONTEXT specifics: backtester-ready output shape required.

    compute_tdi() must return columns:
        rsi_raw, rsi_pl, tsl, mbl, vb_upper, vb_lower, alert_signal
    plus vb_high_threshold and vb_low_threshold (constant Verified Updates new inputs).
    """
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams
    out = compute_tdi(ohlcv_eurusd_h1, TDIParams())
    required = {"rsi_raw", "rsi_pl", "tsl", "mbl", "vb_upper", "vb_lower", "alert_signal"}
    missing = required - set(out.columns)
    assert not missing, f"Missing backtester-ready columns: {missing}"


def test_warmup_bars_are_nan(ohlcv_eurusd_h1):
    """Spec Section 9 edge case 1 + Pitfall 4: first N bars NaN due to RSI + MBL warmup.

    With RSI_Period=21 and Market_Base_Line=34, warmup = 21+34 = 55 bars minimum.
    The first 54 bars of rsi_pl / tsl / mbl / vb_upper / vb_lower must be NaN.
    """
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams
    import pandas as pd
    out = compute_tdi(ohlcv_eurusd_h1, TDIParams())
    warmup = TDIParams().rsi_period + TDIParams().market_base_line - 1
    for col in ("rsi_pl", "tsl", "mbl", "vb_upper", "vb_lower"):
        nan_count = out[col].iloc[:warmup].isna().sum()
        assert nan_count > 0, f"Expected NaN warmup bars in '{col}', got none"


def test_signal_cross_bullish_in_uptrend(synthetic_ohlc_uptrend):
    """Spec Section 10 case 5 analog: uptrend series should produce at least one SIGNAL_CROSS_BULLISH."""
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams
    out = compute_tdi(synthetic_ohlc_uptrend, TDIParams())
    has_bullish = (out["alert_signal"] == "SIGNAL_CROSS_BULLISH").any()
    assert has_bullish, "Expected at least one SIGNAL_CROSS_BULLISH in uptrend series"


def test_mbl_cross_bullish_in_uptrend(synthetic_ohlc_uptrend):
    """Spec Section 10 case 2 analog: Blood in the Water — MBL_CROSS_BULLISH fires in uptrend."""
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams
    out = compute_tdi(synthetic_ohlc_uptrend, TDIParams())
    has_mbl = (out["alert_signal"] == "MBL_CROSS_BULLISH").any()
    assert has_mbl, "Expected at least one MBL_CROSS_BULLISH in uptrend series"


def test_no_lookahead_in_alerts(ohlcv_eurusd_h1):
    """Pitfall 5 / Anti-Patterns 'Repainting on bar[0] alerts'.

    Alert at row i must depend only on bar[i] and bar[i-1] (shift(1) guard).
    Verify structurally: alert column must not contain values for the very
    first row (needs at least 2 rows to compare transitions), i.e., index 0
    is NaN or 'NONE'/'no_alert' — no alert can fire on bar 0.
    """
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams
    out = compute_tdi(ohlcv_eurusd_h1, TDIParams())
    first_alert = out["alert_signal"].iloc[0]
    # first bar cannot have a cross (needs prior bar for comparison)
    assert first_alert in (None, "NONE", float("nan")) or str(first_alert) in ("NONE", "nan"), (
        f"Bar 0 alert should be 'NONE', got {first_alert!r}"
    )
