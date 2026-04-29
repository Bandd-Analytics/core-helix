"""SM_PivotPoints Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md
Primary reference: MMM Book pp. 42-43 (M1-M4 mid-pivot definitions).

SM_PivotPoints — daily floor pivot calculator with MMM-specific M1-M4
mid-pivot overlay. Standard pivots (PP, R1-R3, S1-S3) are an industry
standard with zero ambiguity. MMM M1-M4 mid-pivots are documented in
MMM Book pp. 42-43:
    M1 = (S2 + S1) / 2
    M2 = (S1 + PP) / 2
    M3 = (PP + R1) / 2
    M4 = (R1 + R2) / 2

The M1/M3 vs M2/M4 day-type prediction (red vs green prior candle) is the
Mauro-proprietary technique: if prior candle was red → M1/M3 day (HOD lands
between S2/S1 or PP/R1). If green → M2/M4 day (HOD lands between S1/PP or
R1/R2).

Per D-11: function-first surface, params as frozen dataclass.
Pitfall 3 guard: out = df.copy() — never mutate caller frame.
Pitfall 5 guard: prior-day OHLC via shift(1) — no lookahead.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PivotPointsParams:
    """SM_PivotPoints indicator parameters.

    show_mid_pivots: Draw the four MMM M1-M4 mid-pivot levels (default True
        per MMM Book pp. 42-43 — Mauro uses mid-pivots as HOD/LOD targets).
    show_weekly: Also compute weekly pivots (default False per spec Section 3
        [INFER]).
    """

    show_mid_pivots: bool = True
    show_weekly: bool = False  # [INFER] — weekly likely optional/off-by-default


def compute_pivot_points(
    df: pd.DataFrame,
    params: PivotPointsParams = PivotPointsParams(),
) -> pd.DataFrame:
    """SM_PivotPoints — standard floor pivots + MMM Book pp. 42-43 M1-M4 mid-pivots.

    Per spec Section 5 + MMM Book pp. 42-43. Reads prior-day OHLC via
    shift(1) to prevent lookahead (Pitfall 5). Caller supplies Daily-resampled df.

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close per Phase 8.4 D-20).
            Should be daily-resolution bars for meaningful pivot values.
        params: PivotPointsParams. Defaults: show_mid_pivots=True.

    Returns:
        DataFrame with input columns plus:
            pp   — Pivot Point: (prior_high + prior_low + prior_close) / 3
            r1   — Resistance 1: 2*PP - prior_low
            r2   — Resistance 2: PP + (prior_high - prior_low)
            r3   — Resistance 3: prior_high + 2*(PP - prior_low)
            s1   — Support 1: 2*PP - prior_high
            s2   — Support 2: PP - (prior_high - prior_low)
            s3   — Support 3: prior_low - 2*(prior_high - PP)
            m1   — Mid 1: (S2 + S1) / 2   [if show_mid_pivots=True]
            m2   — Mid 2: (S1 + PP) / 2   [if show_mid_pivots=True]
            m3   — Mid 3: (PP + R1) / 2   [if show_mid_pivots=True]
            m4   — Mid 4: (R1 + R2) / 2   [if show_mid_pivots=True]
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # Pitfall 5: prior-day OHLC via shift(1) to prevent lookahead
    prior_h = out["High"].shift(1)
    prior_l = out["Low"].shift(1)
    prior_c = out["Close"].shift(1)

    # Standard floor pivot formulas (spec Section 5)
    out["pp"] = (prior_h + prior_l + prior_c) / 3.0
    out["r1"] = 2.0 * out["pp"] - prior_l
    out["s1"] = 2.0 * out["pp"] - prior_h
    out["r2"] = out["pp"] + (prior_h - prior_l)
    out["s2"] = out["pp"] - (prior_h - prior_l)
    out["r3"] = prior_h + 2.0 * (out["pp"] - prior_l)
    out["s3"] = prior_l - 2.0 * (prior_h - out["pp"])

    if params.show_mid_pivots:
        # Per MMM Book pp. 42-43 — midpoints between adjacent levels
        out["m1"] = (out["s2"] + out["s1"]) / 2.0
        out["m2"] = (out["s1"] + out["pp"]) / 2.0
        out["m3"] = (out["pp"] + out["r1"]) / 2.0
        out["m4"] = (out["r1"] + out["r2"]) / 2.0
    else:
        # Ensure columns exist with NaN when mid-pivots disabled
        for col in ("m1", "m2", "m3", "m4"):
            out[col] = float("nan")

    return out


__all__ = ["PivotPointsParams", "compute_pivot_points"]
