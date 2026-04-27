"""sm_WorkTime Python port — Phase 12 Plan 01 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md

Classifies each bar in an OHLCV DataFrame into one of {ASIA, LONDON, US,
OFFHOURS} per the MMM session schedule (Book p. 8):
    Asia    00:30–07:30 GMT
    London  07:30–13:30 GMT
    US      13:30–22:00 GMT

Reads the broker GMT offset via compute_sm_gmtoffset (per spec Section 8
Dependencies). In backtesting mode (broker_ts=None) this is always 0 —
Helix CSVs are UTC-stamped, so session classification is direct.

Spec D-19 architectural distinction: this module DOES depend on
sm_gmtoffset, unlike the no_autogmt sibling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .sm_gmtoffset import SMGMTOffsetParams, compute_sm_gmtoffset


@dataclass(frozen=True)
class SMWorkTimeParams:
    """Spec Section 3 inputs.

    Defaults follow MMM Book p. 8 GMT session windows. The hour+minute
    split here resolves the spec Section 12 ambiguity (the integer-hour
    inputs in the original binary do not capture 30-min offsets) by
    surfacing both fields explicitly.
    """

    asia_start_h: int = 0
    asia_start_m: int = 30
    asia_end_h: int = 7
    asia_end_m: int = 30
    london_start_h: int = 7
    london_start_m: int = 30
    london_end_h: int = 13
    london_end_m: int = 30
    us_start_h: int = 13
    us_start_m: int = 30
    us_end_h: int = 22
    us_end_m: int = 0
    # Default uses the auto-detect helper. In backtesting mode this returns
    # 0, which is the only value Helix needs.
    gmt_params: SMGMTOffsetParams = field(default_factory=SMGMTOffsetParams)


def compute_sm_worktime(
    df: pd.DataFrame,
    params: SMWorkTimeParams = SMWorkTimeParams(),
) -> pd.DataFrame:
    """Per spec sm_WorkTime.md Section 5 + MMM Book p. 8 / p. 40.

    Args:
        df: OHLCV DataFrame with a DatetimeIndex (assumed UTC if naive,
            per Phase 8 PitClock convention).
        params: SMWorkTimeParams with verified MMM session boundaries.

    Returns:
        Copy of df with a new ``session_label`` column whose values are
        in {"ASIA", "LONDON", "US", "OFFHOURS"}.

    Notes:
        - Pitfall 3: NEVER mutates input.
        - Half-open intervals: a bar at exactly 07:30 GMT classifies as
          LONDON (the new session "wins"), not ASIA — matching the
          natural reading of MMM Book p. 8 (London opens at 07:30 GMT).
        - Backtester integration (spec Section 11): broker offset is
          0 in backtest, so df.index minute-of-day is the GMT clock.
    """
    out = df.copy()  # NEVER mutate input — Pitfall 3

    # Spec Section 11 Backtester integration: broker_ts=None → offset 0.
    # In live mode the caller can pre-shift the index or pass a broker_ts
    # via SMGMTOffsetParams.manual_gmt; the helper itself never reads a
    # broker connection.
    offset_h = compute_sm_gmtoffset(params.gmt_params, broker_ts=None)

    ts: pd.DatetimeIndex = out.index
    if not isinstance(ts, pd.DatetimeIndex):
        raise TypeError("compute_sm_worktime requires a DatetimeIndex")

    # Compose minute-of-day in GMT (offset already 0 in backtest mode).
    # Subtract the broker offset to shift broker-local minutes back to UTC
    # when the index represents broker server time.
    hour_min = ts.hour * 60 + ts.minute - offset_h * 60

    # Wrap-safe normalisation to [0, 1440)
    hour_min = ((hour_min % 1440) + 1440) % 1440

    asia_start = params.asia_start_h * 60 + params.asia_start_m
    asia_end = params.asia_end_h * 60 + params.asia_end_m
    london_start = params.london_start_h * 60 + params.london_start_m
    london_end = params.london_end_h * 60 + params.london_end_m
    us_start = params.us_start_h * 60 + params.us_start_m
    us_end = params.us_end_h * 60 + params.us_end_m

    label = np.full(len(out), "OFFHOURS", dtype=object)
    # Apply ASIA first; LONDON and US masks overwrite at boundary minutes
    # so the new session "wins" at 07:30 / 13:30 transitions.
    label[(hour_min >= asia_start) & (hour_min < asia_end)] = "ASIA"
    label[(hour_min >= london_start) & (hour_min < london_end)] = "LONDON"
    label[(hour_min >= us_start) & (hour_min < us_end)] = "US"

    out["session_label"] = label
    return out


__all__ = ["SMWorkTimeParams", "compute_sm_worktime"]
