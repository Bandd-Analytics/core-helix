"""SM_NewHUD Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md
D-17: Low confidence — every guessed branch carries # [INFER] with spec ref.
Verified Updates 2026-04-27: OVERRIDES spec body with 18+ fields + HYADR +
Av_N EMA periods (1, 4, 13, 26, 52).

SM_NewHUD — live corner HUD indicator displaying key market metrics:
    ASK/BID, spread, HOD+distance, LOD+distance, TDR, YDR, WADR, MADR,
    HYADR, PTO, WH+distance, WL+distance, WR, MWR/3MWR/6MWR, 3xADR,
    Candle Time, Av_N EMA row at periods 1, 4, 13, 26, 52.

Python port: returns shape-only DataFrame per D-17 (internals [INFER]).
All formula choices carry # [INFER] annotations.

Per D-11: function-first surface, params as frozen dataclass.
Pitfall 3 guard: out = df.copy() — never mutate caller frame.
Pitfall 5 guard: YDR uses shift(1) — prior-bar only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pandas as pd


@dataclass(frozen=True)
class NewHUDParams:
    """SM_NewHUD indicator parameters — Verified Updates 2026-04-27.

    D-17 Low confidence: every default tagged with provenance or [INFER].
    Verified Updates MATERIAL INPUTS (from MT4 Inputs dialog screenshot):
        max_spread_pips = 1.75 (Verified Updates — MaxSpread filter)
        av_periods = (1, 4, 13, 26, 52) (Verified Updates — Av_N EMA row)
        hilo_alert_distance_1 = 10.0 (Verified Updates — HiLoAlert_Distance1)
        hilo_alert_distance_2 = 20.0 (Verified Updates — HiLoAlert_Distance2)
        week_hilo_alert_distance_3 = 25.0 (Verified Updates — Week_HiLo_Alert_Distance3)
        week_hilo_alert_distance_4 = 50.0 (Verified Updates — Week_HiLo_Alert_Distance4)
        adr_alert_distance = 10.0 (Verified Updates — adrAlert_Distance)
    """

    max_spread_pips: float = 1.75                    # Verified Updates MaxSpread
    hilo_alert_distance_1: float = 10.0              # Verified Updates HiLoAlert_Distance1
    hilo_alert_distance_2: float = 20.0              # Verified Updates HiLoAlert_Distance2
    week_hilo_alert_distance_3: float = 25.0         # Verified Updates Week_HiLo_Alert_Distance3
    week_hilo_alert_distance_4: float = 50.0         # Verified Updates Week_HiLo_Alert_Distance4
    adr_alert_distance: float = 10.0                 # Verified Updates adrAlert_Distance
    av_periods: Tuple[int, ...] = (1, 4, 13, 26, 52)  # Verified Updates Av_N EMA row
    is_jpy: bool = False                              # JPY pair (pip = 0.01)


def compute_new_hud(
    df: pd.DataFrame,
    params: NewHUDParams = NewHUDParams(),
) -> pd.DataFrame:
    """SM_NewHUD (D-17 Built ⚠ Low confidence — Verified Updates 18-field set).

    Returns shape-only DataFrame with 18+ HUD field columns including
    HYADR, WADR, MADR, Av_N EMAs. All formula choices are [INFER] per
    Open Question #4 — no source code available.

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close per Phase 8.4 D-20).
            For meaningful ADR variants, caller should supply daily-resolution bars.
            For H1/M15, rolling windows approximate monthly/weekly semantics.
        params: NewHUDParams. Verified Updates 2026-04-27 defaults.

    Returns:
        DataFrame with input columns plus all 18+ HUD field columns:
            bid               — Bid proxy (Close in backtest)
            ask               — Ask proxy (Close + 1.5 pip spread estimate) [INFER]
            spread_pips       — Spread in pips [INFER]
            hod               — High of Day (intra-day cummax)
            lod               — Low of Day (intra-day cummin)
            hod_distance_pips — Distance from bid to HOD in pips
            lod_distance_pips — Distance from LOD to bid in pips
            tdr               — Today's Daily Range = High - Low
            ydr               — Yesterday's Daily Range = shift(1) High - Low [Pitfall 5]
            wadr              — Weekly ADR: 5-bar rolling mean of tdr [INFER]
            madr              — Monthly ADR: 22-bar rolling mean of tdr [INFER]
            hyadr             — Half-Yearly ADR: 132-bar rolling mean of tdr [INFER] (Verified Updates NEW)
            pto               — Price-To-Open: Close - Open [INFER]
            wh                — Week High: 5-bar rolling max of High [INFER]
            wh_distance_pips  — Distance from bid to WH in pips
            wl                — Week Low: 5-bar rolling min of Low [INFER]
            wl_distance_pips  — Distance from WL to bid in pips
            wr                — Week Range: WH - WL [INFER]
            x3_adr            — 3xADR: wadr * 3 [INFER]
            ema_{p}           — EMA at period p for each p in av_periods (1, 4, 13, 26, 52)
            alert_signal      — 'NEAR_HOD' / 'NEAR_LOD' / 'NONE' per hilo_alert_distance_1
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    pip = 0.01 if params.is_jpy else 0.0001

    # --- Live price state (Bid proxy = Close in backtest)
    out["bid"] = out["Close"]
    out["ask"] = out["Close"] + 1.5 * pip              # [INFER] spread proxy ~1.5 pips
    out["spread_pips"] = (out["ask"] - out["bid"]) / pip

    # --- Intra-day HOD/LOD (cummax/cummin within session — [INFER] simple cummax used here)
    out["hod"] = out["High"].cummax()
    out["lod"] = out["Low"].cummin()
    out["hod_distance_pips"] = (out["hod"] - out["bid"]) / pip
    out["lod_distance_pips"] = (out["bid"] - out["lod"]) / pip

    # --- Daily range metrics
    out["tdr"] = out["High"] - out["Low"]               # Today's Daily Range
    out["ydr"] = (out["High"] - out["Low"]).shift(1)    # Yesterday's Daily Range [Pitfall 5]

    # --- ADR variants — formulas [INFER] per Open Question #4; named per Verified Updates
    out["wadr"]  = out["tdr"].rolling(5).mean()           # [INFER] Weekly = 5 D1 bars
    out["madr"]  = out["tdr"].rolling(22).mean()          # [INFER] Monthly ~22 D1 bars
    out["hyadr"] = out["tdr"].rolling(132).mean()         # [INFER] Half-Yearly ~132 D1 bars (Verified Updates NEW)

    # --- Price-To-Open
    out["pto"] = out["Close"] - out["Open"]               # [INFER] Distance from Open to Close

    # --- Week H/L
    out["wh"] = out["High"].rolling(5).max()              # [INFER] Weekly high = 5-bar rolling max
    out["wl"] = out["Low"].rolling(5).min()               # [INFER] Weekly low = 5-bar rolling min
    out["wh_distance_pips"] = (out["wh"] - out["bid"]) / pip
    out["wl_distance_pips"] = (out["bid"] - out["wl"]) / pip
    out["wr"] = out["wh"] - out["wl"]                     # [INFER] Week Range

    # --- 3xADR
    out["x3_adr"] = out["wadr"] * 3.0                    # [INFER] 3 × weekly ADR threshold

    # --- Av_N EMA row at periods (1, 4, 13, 26, 52) per Verified Updates
    for p in params.av_periods:
        out[f"ema_{p}"] = out["Close"].ewm(span=p, adjust=False).mean()

    # --- Alert signal per D-12 (NEAR_HOD / NEAR_LOD / NONE)
    out["alert_signal"] = "NONE"
    near_hod = out["hod_distance_pips"] < params.hilo_alert_distance_1
    near_lod = out["lod_distance_pips"] < params.hilo_alert_distance_1
    out.loc[near_hod, "alert_signal"] = "NEAR_HOD"
    out.loc[near_lod, "alert_signal"] = "NEAR_LOD"

    return out


__all__ = ["NewHUDParams", "compute_new_hud"]
