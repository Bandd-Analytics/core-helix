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


def compute_bpct(
    df: pd.DataFrame,
    params: BPCTParams = BPCTParams(),
) -> pd.DataFrame:
    """SM_BPCT mini-HUD compute (D-17 Built ⚠ Low confidence).

    Per Pitfall 10: implementation follows Verified Updates 2026-04-27
    (mini-HUD), NOT spec body (pressure-tracker hypothesis).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: BPCTParams. Defaults match Verified Updates.

    Returns:
        DataFrame with the input columns plus mini-HUD shape:
            hod                 — running cumulative max of High (proxy for
                                  current Daily HOD; in MT5 this would be
                                  iHigh(_Symbol, PERIOD_D1, 0))
            lod                 — running cumulative min of Low
            hod_distance_pips   — (hod - Close) / pip_size
            lod_distance_pips   — (Close - lod) / pip_size
            spread_pips         — constant proxy (D-12 — backtest has no
                                  live bid/ask)
            alert_signal        — 'NEAR_HOD' / 'NEAR_LOD' / 'NONE' when
                                  hod_lod_alert=True (D-12 log-only)

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

    return out


__all__ = ["BPCTParams", "compute_bpct"]
