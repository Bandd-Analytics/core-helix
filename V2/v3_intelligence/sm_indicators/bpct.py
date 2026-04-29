"""SM_BPCT Python port — Phase 12 Plan 02 / D-07, D-10, D-11, D-17.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md
Implementation follows Verified Updates 2026-04-27 mini-HUD interpretation,
NOT spec body's pressure-tracker hypothesis (Pitfall 10).

# [INFER] D-17 Low confidence — every guessed branch is annotated. The
# Verified Updates dialog confirmed:
#   - Indicator is a corner-positioned mini-HUD (real-time price + spread
#     + HOD/LOD distance + proximity alert)
#   - 16 inputs verbatim from VERIFIED-DEFAULTS.md §1
#   - Distance_From_Extreme=12.0, HOD_LOD_Alert=false,
#     Pips_To_HOD_LOD_For_Alert=5.0
# Algorithm internals (rolling HOD/LOD window, exact threshold check)
# remain inferred — Python returns the underlying numeric series so the
# parity test can verify they're computed identically across targets.

v2.00 additions (operator-tuned 2026-04-28):
  - phod_distance_pips  — distance from Close to previous day's High (PHOD)
  - plod_distance_pips  — distance from Close to previous day's Low (PLOD)
    PHOD = High.shift(1) on daily data; PLOD = Low.shift(1).

v2.01 additions (operator-tuned 2026-04-28 round 2):
  - bars_remaining_seconds — seconds to bar close per bar (countdown analogue).
    Computed as: bar_duration_seconds - (unix_timestamp % bar_duration_seconds).
    Caller must set bar_duration_seconds to match the chart timeframe.
  - BPCTParams: added y_offset, trade_color; removed separate buy/sell colour params.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BPCTParams:
    """Verified Updates 2026-04-27 mini-HUD inputs (NOT spec-body pressure-
    tracker hypothesis — Pitfall 10).

    # [INFER] D-17 Low confidence — defaults from operator screenshot;
    # see VERIFIED-DEFAULTS.md §1.
    """

    # Display
    corner: str = "RIGHT_TOP"            # 4-corner enum
    show_price: bool = True
    show_xtra_details: bool = True
    show_smaller_size: bool = True
    show_trade_pips: bool = True
    shift_up_dn: int = 0                 # pixel offsets
    adjust_side_to_side: int = 0
    # Behavior thresholds
    distance_from_extreme: float = 12.0  # pip threshold for "at extreme" coloring
    hod_lod_alert: bool = False          # opt-in proximity alert
    pips_to_hod_lod_for_alert: float = 5.0
    # Pip math
    pip_size: float = 0.0001             # 5-digit majors; caller overrides for JPY
    # Backtest spread proxy (no live bid/ask in CSV-fed compute)
    spread_pips_proxy: float = 1.5       # [INFER] typical IC Markets EURUSD spread
    # v2.01 — vertical offset (avoids overlap with SM_ADR_Marker HUD)
    y_offset: int = 0
    # v2.01 — unified trade-row colour (replaces separate buy/sell colour params)
    trade_color: str = "White"
    # v2.01 — bar duration for countdown column; caller should match chart timeframe
    # (e.g. 3600 for H1, 14400 for H4, 900 for M15).
    bar_duration_seconds: int = 3600     # default H1


def compute_bpct(
    df: pd.DataFrame,
    params: BPCTParams = BPCTParams(),
) -> pd.DataFrame:
    """SM_BPCT mini-HUD compute (D-17 Built ⚠ Low confidence).

    Per Pitfall 10: implementation follows Verified Updates 2026-04-27
    (mini-HUD), NOT spec body (pressure-tracker hypothesis).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close). Index must be a
            DatetimeIndex when bars_remaining_seconds is required.
        params: BPCTParams. Defaults match Verified Updates.

    Returns:
        DataFrame with the input columns plus mini-HUD shape:
            hod                   — running cumulative max of High (proxy for
                                    current Daily HOD; in MT5 this would be
                                    iHigh(_Symbol, PERIOD_D1, 0))
            lod                   — running cumulative min of Low
            hod_distance_pips     — (hod - Close) / pip_size
            lod_distance_pips     — (Close - lod) / pip_size
            spread_pips           — constant proxy (D-12 — backtest has no
                                    live bid/ask)
            alert_signal          — 'NEAR_HOD' / 'NEAR_LOD' / 'NONE' when
                                    hod_lod_alert=True (D-12 log-only)
            phod_distance_pips    — (Close - PHOD) / pip_size, where PHOD is
                                    yesterday's High (High.shift(1) on daily
                                    data). [INFER] On intra-day frames, PHOD
                                    is approximated by shifting the cummax of
                                    each prior day's High by one bar — caller
                                    should supply daily-aligned data for
                                    accurate semantics.
            plod_distance_pips    — (Close - PLOD) / pip_size, where PLOD is
                                    yesterday's Low (Low.shift(1) on daily
                                    data).
            bars_remaining_seconds — seconds to bar close per bar.
                                    = bar_duration_seconds -
                                      (unix_timestamp_seconds % bar_duration_seconds)
                                    Matches MT4/MT5 formula:
                                    PeriodSeconds() - (TimeCurrent() % PeriodSeconds()).
                                    [INFER] On historical data this is the
                                    time-within-bar remainder, not a live
                                    countdown; caller sets
                                    params.bar_duration_seconds to match the
                                    chart timeframe.

    Notes:
        # [INFER] HOD/LOD computed as running cummax/cummin of the input
        # frame — caller must supply Daily-aligned df (or accept
        # cumulative-from-frame-start semantics for shape tests).
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # [INFER] HOD = high-of-day, LOD = low-of-day. In MT5 this is
    # iHigh/iLow(_Symbol, PERIOD_D1, 0); in Python the closest analogue
    # without an explicit daily-resample is cummax/cummin from frame start.
    out["hod"] = out["High"].cummax()
    out["lod"] = out["Low"].cummin()

    # Distance from current Close (Bid proxy in backtest). Pitfall: pip math.
    pip = params.pip_size
    out["hod_distance_pips"] = (out["hod"] - out["Close"]) / pip
    out["lod_distance_pips"] = (out["Close"] - out["lod"]) / pip

    # Spread proxy — backtest has no live bid/ask.
    out["spread_pips"] = params.spread_pips_proxy  # [INFER]

    # Alert signal column (D-12 — log only, no email/push from Python).
    out["alert_signal"] = "NONE"
    if params.hod_lod_alert:
        # [INFER] Threshold is "within N pips of extreme" — VERIFIED 5.0 default.
        near_hod = out["hod_distance_pips"] < params.pips_to_hod_lod_for_alert
        near_lod = out["lod_distance_pips"] < params.pips_to_hod_lod_for_alert
        out.loc[near_hod, "alert_signal"] = "NEAR_HOD"
        out.loc[near_lod, "alert_signal"] = "NEAR_LOD"

    # -------------------------------------------------------------------------
    # v2.00 — PHOD / PLOD distance columns
    # PHOD = previous day's High = High.shift(1) on daily data.
    # PLOD = previous day's Low  = Low.shift(1)  on daily data.
    # [INFER] On intra-day frames, shift(1) gives the previous BAR's value,
    # not the previous DAY's value; caller should resample to daily before
    # calling if strict daily semantics are required.  For shape tests the
    # shifted series is the correct structural analogue.
    # -------------------------------------------------------------------------
    phod = out["High"].shift(1)  # [INFER] PHOD = High.shift(1)
    plod = out["Low"].shift(1)   # [INFER] PLOD = Low.shift(1)
    out["phod_distance_pips"] = (out["Close"] - phod) / pip
    out["plod_distance_pips"] = (out["Close"] - plod) / pip

    # -------------------------------------------------------------------------
    # v2.01 — bars_remaining_seconds countdown column
    # MT4/MT5 formula: PeriodSeconds() - (TimeCurrent() % PeriodSeconds())
    # Python equivalent on DatetimeIndex (UTC unix seconds):
    #   bar_duration_seconds - (timestamp_unix_seconds % bar_duration_seconds)
    # [INFER] Returns seconds to bar close for each bar based on bar open
    # timestamp; for historical data this is "time elapsed into bar" complement,
    # not a live countdown.
    # -------------------------------------------------------------------------
    bds = params.bar_duration_seconds
    if bds > 0:
        # [INFER] Convert DatetimeIndex to integer unix seconds; handle both
        # DatetimeIndex and RangeIndex/Int64Index gracefully.
        try:
            unix_s = out.index.astype("int64") // 1_000_000_000  # ns → s
        except (AttributeError, TypeError):
            # [INFER] Non-datetime index: fill with NaN for shape compatibility
            out["bars_remaining_seconds"] = float("nan")
        else:
            out["bars_remaining_seconds"] = bds - (unix_s % bds)
    else:
        out["bars_remaining_seconds"] = float("nan")  # [INFER] degenerate guard

    return out


__all__ = ["BPCTParams", "compute_bpct"]
