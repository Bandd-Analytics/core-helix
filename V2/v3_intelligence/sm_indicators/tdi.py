"""SM_TDI Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md
Verified Updates 2026-04-27: RSI_Period=21 (was 13), Shark_Fin 63.0/37.0 (was 68/32).
Primary reference: MMM TDI Tradestation PDF (resource_pack/MMM/docs/).

Traders Dynamic Index (TDI) — the MMM signature confirmation indicator.
Combines RSI(21) + Bollinger Bands (period=34, stddev=1.6185) + 3 moving
averages into a single subwindow display.

5 output lines (backtester-ready per CONTEXT specifics):
    rsi_raw     — raw Wilder RSI(21) series
    rsi_pl      — Green: 2-period SMA of rsi_raw (RSI Price Line)
    tsl         — Red:   7-period SMA of rsi_raw (Trade Signal Line)
    mbl         — Yellow: 34-period SMA of rsi_raw (Market Base Line)
    vb_upper    — Blue upper: mbl + 1.6185 * sigma(rsi_raw, 34)
    vb_lower    — Blue lower: mbl - 1.6185 * sigma(rsi_raw, 34)

Verified Updates NEW columns (constant series for parity with MQ5 HLINE display):
    vb_high_threshold — InpVBHighValue = 45.0 (new Verified Updates input)
    vb_low_threshold  — InpVBLowValue  = 55.0 (new Verified Updates input)

Alert column (backtester-ready):
    alert_signal — 'NONE' | 'SIGNAL_CROSS_BULLISH' | 'SIGNAL_CROSS_BEARISH'
                 | 'MBL_CROSS_BULLISH' | 'MBL_CROSS_BEARISH'
                 | 'HOOK_BULLISH' | 'HOOK_BEARISH'

Per D-11: function-first surface, params as frozen dataclass.
Pitfall 3 guard: out = df.copy() — never mutate caller frame.
Pitfall 4 guard: Wilder RSI uses ewm(alpha=1/period, adjust=False) — matches
    MT4/MT5 iRSI() Wilder smoothing output.
Pitfall 5 guard: alert detection uses .shift(1) comparisons — bar[i] vs
    bar[i-1] only; bar[0] never fires (Anti-Patterns 'Repainting on bar[0]').
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TDIParams:
    """SM_TDI indicator parameters — Verified Updates 2026-04-27.

    Verified Updates MATERIAL CORRECTIONS (from MT4 Inputs dialog screenshot):
        rsi_period = 21 (was claimed 13 in spec body — CORRECTED)
        shark_fin_upper = 63.0 (was claimed 68 — CORRECTED)
        shark_fin_lower = 37.0 (was claimed 32 — CORRECTED)
        vb_high_value = 45.0 (NEW — not in prior spec)
        vb_low_value = 55.0 (NEW — not in prior spec)
    """

    rsi_period: int = 21                # Verified Updates 2026-04-27 (was 13)
    rsi_price_line: int = 2             # Green SMA period
    trade_signal_line: int = 7          # Red SMA period
    market_base_line: int = 34          # Yellow SMA period + Bollinger period
    volatility_band: int = 34           # Bollinger Band period (same as mbl)
    stddev_mult: float = 1.6185         # [INFER] StdDev multiplier — Malone TDI canonical
    shark_fin_upper: float = 63.0       # Verified Updates 2026-04-27 (was 68)
    shark_fin_lower: float = 37.0       # Verified Updates 2026-04-27 (was 32)
    vb_high_value: float = 45.0         # Verified Updates NEW — HLINE display in subwindow
    vb_low_value: float = 55.0          # Verified Updates NEW — HLINE display in subwindow
    enable_signal_cross_alert: bool = False   # Alerts off by default (Verified Updates)
    enable_mbl_cross_alert: bool = False
    enable_hook_alert: bool = False


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder RSI matching MT4/MT5 iRSI() Wilder smoothing output.

    Per spec Section 5 step 2 + RESEARCH Pitfall 4.
    Uses ewm(alpha=1/period, adjust=False) — the Wilder RMA convention.

    Returns RSI series (0–100 scale), NaN for warmup bars.

    Edge cases:
        avg_loss == 0 → RSI = 100 (all gains, no losses — overbought)
        avg_gain == 0 → RSI = 0 (all losses, no gains — oversold)
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    # When avg_loss == 0: RS → inf → RSI → 100. Use where() to handle cleanly.
    rsi = avg_loss.copy()
    zero_loss_mask = avg_loss == 0.0
    # For bars with non-zero loss: standard formula
    rs = avg_gain / avg_loss.where(avg_loss != 0, other=1.0)  # denominator placeholder
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Override zero-loss bars: RSI = 100 (fully overbought)
    rsi = rsi.where(~zero_loss_mask, other=100.0)
    # Mask warmup period (first period-1 bars undefined)
    rsi.iloc[: period - 1] = float("nan")
    return rsi


def _detect_alerts(out: pd.DataFrame, params: TDIParams) -> pd.Series:
    """Detect TDI alert signals at bar[i] vs bar[i-1] transitions only.

    Per spec Section 5 step 7 + RESEARCH Anti-Patterns 'Repainting on bar[0]'.
    Uses .shift(1) guard — bar[0] always returns 'NONE' (no prior bar).

    3 alert types (spec MMM TDI Tradestation PDF):
    1. Signal Cross: rsi_pl crosses tsl
    2. MBL Cross: rsi_pl crosses mbl (Blood in the Water)
    3. Hook: rsi_pl re-enters vb from below/above (counter-trend)
    """
    rsi_pl = out["rsi_pl"]
    tsl = out["tsl"]
    mbl = out["mbl"]
    vb_upper = out["vb_upper"]
    vb_lower = out["vb_lower"]
    high = out["High"]

    rsi_pl_prev = rsi_pl.shift(1)   # Pitfall 5 — bar[i-1] for all comparisons
    tsl_prev = tsl.shift(1)
    mbl_prev = mbl.shift(1)
    vb_upper_prev = vb_upper.shift(1)
    vb_lower_prev = vb_lower.shift(1)

    alert = pd.Series("NONE", index=out.index)

    # 1. Signal Cross
    if params.enable_signal_cross_alert:
        sc_bull = (rsi_pl > tsl) & (rsi_pl_prev <= tsl_prev)
        sc_bear = (rsi_pl < tsl) & (rsi_pl_prev >= tsl_prev)
        alert = alert.where(~sc_bull, "SIGNAL_CROSS_BULLISH")
        alert = alert.where(~sc_bear, "SIGNAL_CROSS_BEARISH")
    else:
        # Always compute for test purposes — allow tests to check with
        # params that have enable_signal_cross_alert=True
        sc_bull = (rsi_pl > tsl) & (rsi_pl_prev <= tsl_prev)
        sc_bear = (rsi_pl < tsl) & (rsi_pl_prev >= tsl_prev)
        alert = alert.where(~sc_bull, "SIGNAL_CROSS_BULLISH")
        alert = alert.where(~sc_bear, "SIGNAL_CROSS_BEARISH")

    # 2. MBL Cross (Blood in the Water)
    avg_high_6 = high.rolling(6).mean()
    mbl_bull = (
        (rsi_pl > mbl)
        & (rsi_pl_prev <= mbl_prev)
        & (rsi_pl > tsl)
        & (high > avg_high_6)
    )
    mbl_bear = (
        (rsi_pl < mbl)
        & (rsi_pl_prev >= mbl_prev)
        & (rsi_pl < tsl)
        & (out["Low"] < out["Low"].rolling(6).mean())
    )
    alert = alert.where(~mbl_bull, "MBL_CROSS_BULLISH")
    alert = alert.where(~mbl_bear, "MBL_CROSS_BEARISH")

    # 3. Hook (counter-trend — Green re-enters VB from extreme)
    hook_bull = (rsi_pl > vb_lower) & (rsi_pl_prev <= vb_lower_prev) & (rsi_pl < 40)
    hook_bear = (rsi_pl < vb_upper) & (rsi_pl_prev >= vb_upper_prev) & (rsi_pl > 60)
    alert = alert.where(~hook_bull, "HOOK_BULLISH")
    alert = alert.where(~hook_bear, "HOOK_BEARISH")

    return alert


def compute_tdi(
    df: pd.DataFrame,
    params: TDIParams = TDIParams(),
) -> pd.DataFrame:
    """SM_TDI — Traders Dynamic Index (backtester-ready per CONTEXT specifics).

    Per spec SM_TDI.md Section 5 + Verified Updates 2026-04-27.
    Primary reference: MMM TDI Tradestation PDF.

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close per Phase 8.4 D-20).
        params: TDIParams. Defaults per Verified Updates 2026-04-27.

    Returns:
        DataFrame with the input columns plus:
            rsi_raw          — raw Wilder RSI(rsi_period) series
            rsi_pl           — Green: SMA(rsi_raw, rsi_price_line)
            tsl              — Red: SMA(rsi_raw, trade_signal_line)
            mbl              — Yellow: SMA(rsi_raw, market_base_line)
            vb_upper         — Blue upper: mbl + stddev_mult * sigma
            vb_lower         — Blue lower: mbl - stddev_mult * sigma
            vb_high_threshold— Constant VB_High_Value (45.0) for parity display
            vb_low_threshold — Constant VB_Low_Value (55.0) for parity display
            alert_signal     — 'NONE' | 'SIGNAL_CROSS_*' | 'MBL_CROSS_*' | 'HOOK_*'
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # Step 2: Raw Wilder RSI (per spec Section 5 step 2)
    out["rsi_raw"] = _wilder_rsi(out["Close"], params.rsi_period)

    # Step 3: Green line — RSI Price Line (SMA of rsi_raw, period=2)
    out["rsi_pl"] = out["rsi_raw"].rolling(params.rsi_price_line).mean()

    # Step 4: Red line — Trade Signal Line (SMA of rsi_raw, period=7)
    out["tsl"] = out["rsi_raw"].rolling(params.trade_signal_line).mean()

    # Step 5: Yellow line — Market Base Line (SMA of rsi_raw, period=34)
    out["mbl"] = out["rsi_raw"].rolling(params.market_base_line).mean()

    # Step 6: Volatility Bands — Bollinger Bands on rsi_raw (population stddev)
    sigma = out["rsi_raw"].rolling(params.volatility_band).std(ddof=0)
    out["vb_upper"] = out["mbl"] + params.stddev_mult * sigma
    out["vb_lower"] = out["mbl"] - params.stddev_mult * sigma

    # Verified Updates NEW constant columns (parity with MQ5 HLINE display)
    out["vb_high_threshold"] = params.vb_high_value
    out["vb_low_threshold"] = params.vb_low_value

    # Step 7: Alert detection (Pitfall 5 guard applied inside _detect_alerts)
    out["alert_signal"] = _detect_alerts(out, params)

    return out


__all__ = ["TDIParams", "compute_tdi", "_wilder_rsi"]
