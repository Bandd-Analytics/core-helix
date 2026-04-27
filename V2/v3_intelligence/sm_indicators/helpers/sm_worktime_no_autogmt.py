"""sm_WorkTime_no_autogmt Python port — Phase 12 Plan 01 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md

Manual-BrokerGMT variant of sm_WorkTime. Spec Section 8 architectural
distinction (D-19): this module does NOT depend on the auto-detect helper.
The broker_gmt offset is taken directly from the SMWorkTimeNoAutoGmtParams
input.

The Sep 2011 binary predates Dec 2011 sm_WorkTime by ~3 months — the
manual variant was the original; the auto-detect variant was added later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SMWorkTimeNoAutoGmtParams:
    """Spec Section 3 inputs — manual-BrokerGMT variant.

    Defaults match SMWorkTimeParams session boundaries (MMM Book p. 8) and
    BrokerGMT=2 (representative European broker). BrokerDSTAdjust defaults
    to False per spec Section 12 — older 2011-era indicators expected manual
    DST handling from the user.
    """

    broker_gmt: int = 2
    broker_dst_adjust: bool = False
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


def _is_northern_hemisphere_dst_active() -> bool:
    """Spec Section 5 + Pseudocode: rough Northern Hemisphere DST window.

    Heuristic: months March (3) through October (10). Brokers following
    US DST may have ~2-week boundary inaccuracy per spec Edge cases.
    """
    month = datetime.now(timezone.utc).month
    return 3 <= month <= 10


def compute_sm_worktime_no_autogmt(
    df: pd.DataFrame,
    params: SMWorkTimeNoAutoGmtParams = SMWorkTimeNoAutoGmtParams(),
) -> pd.DataFrame:
    """Per spec sm_WorkTime_no_autogmt.md Section 5.

    Args:
        df: OHLCV DataFrame with a DatetimeIndex (assumed UTC if naive).
        params: SMWorkTimeNoAutoGmtParams. ``broker_gmt`` is the only
            offset source — there is no auto-detect dependency.

    Returns:
        Copy of df with a new ``session_label`` column whose values are
        in {"ASIA", "LONDON", "US", "OFFHOURS"}.

    Notes:
        - Pitfall 3: NEVER mutates input.
        - Architectural distinction (spec Section 8 / D-19): this module
          does NOT import the auto-detect helper; the offset comes from
          ``params.broker_gmt`` exclusively.
        - Behavioral parity with the auto-variant when ``broker_gmt = 0``
          and the auto-variant is in backtesting mode (offset 0).
    """
    out = df.copy()  # NEVER mutate

    offset_h = int(params.broker_gmt)
    if params.broker_dst_adjust and _is_northern_hemisphere_dst_active():
        offset_h += 1

    ts: pd.DatetimeIndex = out.index
    if not isinstance(ts, pd.DatetimeIndex):
        raise TypeError("compute_sm_worktime_no_autogmt requires a DatetimeIndex")

    # Same minute-bucketing as the auto-variant; offset is applied as
    # subtract-from-index to shift broker-local time back to the GMT
    # session schedule.
    hour_min = ts.hour * 60 + ts.minute - offset_h * 60
    hour_min = ((hour_min % 1440) + 1440) % 1440

    asia_start = params.asia_start_h * 60 + params.asia_start_m
    asia_end = params.asia_end_h * 60 + params.asia_end_m
    london_start = params.london_start_h * 60 + params.london_start_m
    london_end = params.london_end_h * 60 + params.london_end_m
    us_start = params.us_start_h * 60 + params.us_start_m
    us_end = params.us_end_h * 60 + params.us_end_m

    label = np.full(len(out), "OFFHOURS", dtype=object)
    label[(hour_min >= asia_start) & (hour_min < asia_end)] = "ASIA"
    label[(hour_min >= london_start) & (hour_min < london_end)] = "LONDON"
    label[(hour_min >= us_start) & (hour_min < us_end)] = "US"

    out["session_label"] = label
    return out


__all__ = ["SMWorkTimeNoAutoGmtParams", "compute_sm_worktime_no_autogmt"]
