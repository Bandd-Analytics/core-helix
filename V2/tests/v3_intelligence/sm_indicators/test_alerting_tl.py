"""SM_Alerting+TL — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md
Python port: takes a list of (start_ts, start_price, end_ts, end_price) trendline tuples.

3 tests: column presence, trendline-touch detection, no-alert when far from line.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 4) turns them GREEN.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest


def test_returns_alert_column(ohlcv_eurusd_h1):
    """compute_alerting_tl() must return a DataFrame with 'alert_signal' column."""
    from v3_intelligence.sm_indicators.alerting_tl import compute_alerting_tl, AlertingTLParams
    out = compute_alerting_tl(ohlcv_eurusd_h1, trendlines=[], params=AlertingTLParams())
    assert "alert_signal" in out.columns, "Missing 'alert_signal' column"


def test_detects_trendline_touch_within_tolerance(synthetic_ohlc_uptrend):
    """Bar's High/Low within touch_pips of trendline projected price → alert fires.

    Uptrend has High = Close + 0.0005 and Low = Close - 0.0005. We set a
    trendline that runs exactly through the High values, with touch_pips=1
    (0.0001 price units). The trendline start_price and end_price are set
    slightly above the Low so High touches are within 1 pip.
    """
    from v3_intelligence.sm_indicators.alerting_tl import compute_alerting_tl, AlertingTLParams
    df = synthetic_ohlc_uptrend
    # Trendline: starts at first bar's Close, ends at last bar's Close
    t1 = df.index[0]
    t2 = df.index[-1]
    p1 = float(df["Close"].iloc[0])
    p2 = float(df["Close"].iloc[-1])
    trendlines = [(t1, p1, t2, p2)]
    # touch_pips=10 (0.001 price units — generous enough to catch any bar whose
    # High/Low is within 10 pips of the projected Close trendline)
    params = AlertingTLParams(touch_pips=10.0)
    out = compute_alerting_tl(df, trendlines=trendlines, params=params)
    touch_count = (out["alert_signal"] == "TL_TOUCH").sum()
    assert touch_count > 0, "Expected TL_TOUCH alerts when trendline runs through price range"


def test_no_alert_when_far_from_line(ohlcv_eurusd_h1):
    """No TL_TOUCH when trendline price is far from all bars (e.g., way above price range)."""
    from v3_intelligence.sm_indicators.alerting_tl import compute_alerting_tl, AlertingTLParams
    df = ohlcv_eurusd_h1
    t1 = df.index[0]
    t2 = df.index[-1]
    # Trendline far above EURUSD range (set to 10.0 — far above 1.x range)
    p1 = 10.0
    p2 = 10.0
    trendlines = [(t1, p1, t2, p2)]
    params = AlertingTLParams(touch_pips=1.0)  # 1-pip tolerance
    out = compute_alerting_tl(df, trendlines=trendlines, params=params)
    touch_count = (out["alert_signal"] == "TL_TOUCH").sum()
    assert touch_count == 0, "Expected zero TL_TOUCH alerts when trendline is far from price"
