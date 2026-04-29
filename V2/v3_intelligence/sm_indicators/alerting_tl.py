"""SM_Alerting+TL Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md
Primary reference: MMM Book p. 55 + Anatomy of Stop Hunts PDF context.

SM_Alerting+TL — trendline-touch detector. In MT4/MT5 this indicator monitors
OBJ_TREND chart objects drawn by the operator and fires alerts when price
approaches within touch_pips of any trendline.

Python port limitation: Python has no live OBJ_TREND chart objects. The
caller supplies trendlines explicitly as (start_ts, start_price, end_ts,
end_price) tuples. Each bar: project each trendline to bar's time via linear
interpolation, compute expected price, if abs(High - expected) <= tolerance
OR abs(Low - expected) <= tolerance → alert fires.

Per D-11: function-first surface, params as frozen dataclass.
Pitfall 3 guard: out = df.copy() — never mutate caller frame.

MMM context: Trendlines are key structural tools in the MMM Anatomy of Stop
Hunts methodology — price sweeps trendline to hunt stops, then reverses.
SM_Alerting+TL provides the monitoring mechanism for this setup pattern.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd


@dataclass(frozen=True)
class AlertingTLParams:
    """SM_Alerting+TL indicator parameters.

    touch_pips: Alert fires when bar's High or Low is within this many pips
        of the projected trendline price at the bar's time. Default 5.0 pips
        per spec Section 3 [INFER].
    is_jpy: True for JPY pairs (pip = 0.01); False for 4-decimal pairs.
    """

    touch_pips: float = 5.0     # [INFER] Touch tolerance in pips
    is_jpy: bool = False         # JPY pair (pip = 0.01, not 0.0001)


def compute_alerting_tl(
    df: pd.DataFrame,
    trendlines: List[Tuple],
    params: AlertingTLParams = AlertingTLParams(),
) -> pd.DataFrame:
    """SM_Alerting+TL — trendline-touch detector.

    Python port can't read live OBJ_TREND chart objects; caller supplies
    trendlines explicitly as list of (start_ts, start_price, end_ts, end_price)
    tuples.

    Each bar: project each trendline to bar's time via linear interpolation.
    Alert fires if abs(High - projected) <= tolerance OR
                  abs(Low  - projected) <= tolerance.

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close per Phase 8.4 D-20).
        trendlines: List of (t1, p1, t2, p2) tuples.
            t1, t2 — pd.Timestamp or datetime-like (start/end of trendline)
            p1, p2 — float price at t1/t2
        params: AlertingTLParams.

    Returns:
        DataFrame with input columns plus:
            alert_signal — 'TL_TOUCH' when price is within touch_pips of any
                           trendline; 'NONE' otherwise.
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    pip = 0.01 if params.is_jpy else 0.0001
    tolerance = params.touch_pips * pip

    out["alert_signal"] = "NONE"

    if not trendlines:
        return out

    for (t1, p1, t2, p2) in trendlines:
        # Ensure t1, t2 are pd.Timestamp objects
        t1 = pd.Timestamp(t1)
        t2 = pd.Timestamp(t2)

        # Total time delta in seconds
        total_seconds = (t2 - t1).total_seconds()
        if total_seconds == 0:
            # Vertical line (undefined slope) — skip
            continue

        for ts, row in out.iterrows():
            ts = pd.Timestamp(ts)
            # Only project within trendline time range
            if ts < t1 or ts > t2:
                continue

            # Linear interpolation: price at time ts
            alpha = (ts - t1).total_seconds() / total_seconds
            expected_price = p1 + (p2 - p1) * alpha

            # Touch if High or Low within tolerance of projected price
            if (
                abs(row["High"] - expected_price) <= tolerance
                or abs(row["Low"] - expected_price) <= tolerance
            ):
                out.loc[ts, "alert_signal"] = "TL_TOUCH"

    return out


__all__ = ["AlertingTLParams", "compute_alerting_tl"]
