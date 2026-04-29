"""SM_AlertZone_1 Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md
RESEARCH Open Question #5: SM_AlertZone_1 and SM_AlertZone_2 share the same
algorithm — the two binaries differ by only 148 bytes (12,562 vs 12,710 bytes)
suggesting same logic compiled with different default values.

This module is the SHARED CORE for both AlertZone variants:
    AlertZone_1 = LOWER zone preset (long setups near LOD/S1 — Strike Zone)
    AlertZone_2 = UPPER zone preset (short setups near HOD/R1)

MMM context per spec Section 2:
    Strike Zone / Trading Zone / Blue Box — area within 15-20 pips of HOD/LOD
    where market makers accumulate before a directional move.
    MMM Glossary: "Trading Zone: an area within 15-20 pips of HOD/LOD where
    setups occur." MMM Book p. 55: "Look for Strike Zones, item 4: Is there a
    significant pivot point near this price?"

Per D-11: function-first surface, params as frozen dataclass.
Pitfall 3 guard: out = df.copy() — never mutate caller frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class AlertZone1Params:
    """SM_AlertZone_1 indicator parameters (LOWER zone preset).

    Per RESEARCH Open Question #5: same algorithm as AlertZone_2, different
    default zone_type. AlertZone_1 targets LOWER zone (long setups near LOD/S1).

    auto_zone=True: zone center tracks LOD (LOWER) or HOD (UPPER) plus
    zone_offset_pips offset — implementing the MMM Strike Zone semantics
    (within zone_offset_pips of day's extreme) per MMM Book p. 55.

    auto_zone=False: zone centered at zone_center with zone_width_pips width.
    """

    zone_center: float = 0.0               # Manual zone center (auto_zone=False)
    zone_width_pips: float = 30.0          # Zone full width in pips [INFER]
    zone_type: Literal["LOWER", "UPPER"] = "LOWER"  # LOWER = near LOD, UPPER = near HOD
    auto_zone: bool = True                 # Track LOD/HOD automatically
    zone_offset_pips: float = 15.0         # Strike Zone offset from LOD/HOD per MMM Book p. 55 [INFER]
    is_jpy: bool = False                   # JPY pair (pip = 0.01, not 0.0001)


def compute_alert_zone(
    df: pd.DataFrame,
    params: AlertZone1Params = AlertZone1Params(),
) -> pd.DataFrame:
    """Shared core for SM_AlertZone_1 and SM_AlertZone_2.

    Per RESEARCH Open Question #5: same algorithm, two parameter presets.
    AlertZone_1 = LOWER (long-setup near LOD); AlertZone_2 = UPPER (short-setup near HOD).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close per Phase 8.4 D-20).
        params: AlertZone1Params (or AlertZone2Params mapped to AlertZone1Params).

    Returns:
        DataFrame with input columns plus:
            zone_upper   — upper boundary of the alert zone
            zone_lower   — lower boundary of the alert zone
            alert_signal — 'NEAR_ZONE' when Close is inside zone; 'OUTSIDE' otherwise
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    pip = 0.01 if params.is_jpy else 0.0001

    if params.auto_zone:
        # Track HOD or LOD dynamically
        if params.zone_type == "UPPER":
            # UPPER zone: center above HOD minus offset (near day's high — short setup zone)
            center = out["High"].cummax() - params.zone_offset_pips * pip
        else:
            # LOWER zone: center below LOD plus offset (near day's low — long setup zone)
            center = out["Low"].cummin() + params.zone_offset_pips * pip
    else:
        center = pd.Series(params.zone_center, index=out.index)

    half_width = params.zone_width_pips * pip / 2.0
    out["zone_upper"] = center + half_width
    out["zone_lower"] = center - half_width

    # Alert fires when Close is inside the zone bounds (D-12 alert_signal column pattern)
    in_zone = (out["Close"] >= out["zone_lower"]) & (out["Close"] <= out["zone_upper"])
    out["alert_signal"] = "OUTSIDE"
    out.loc[in_zone, "alert_signal"] = "NEAR_ZONE"

    return out


__all__ = ["AlertZone1Params", "compute_alert_zone"]
