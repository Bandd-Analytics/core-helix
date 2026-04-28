"""sm_WorkTime_no_autogmt Python port — Phase 12 Plan 01 v2.00.

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md

Manual-BrokerGMT variant of sm_WorkTime. Spec Section 8 architectural
distinction (D-19): this module does NOT depend on the auto-detect helper.
The broker_gmt offset is taken directly from the SMWorkTimeNoAutoGmtParams
input.

v2.00 — gap-window classification (LONDON_GAP, NY_GAP) and optional Asian
Range (AR Line) parity with sm_WorkTime. Visual differences in the MQ5
sources (light colors, pip labels) do not apply to the Python port.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SMWorkTimeNoAutoGmtParams:
    """Spec Section 3 inputs — manual-BrokerGMT variant (v2.00)."""

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

    # v2.00 changeover gap windows (default ±30 min around session open in GMT)
    show_gaps: bool = True
    london_gap_start_h: int = 7
    london_gap_start_m: int = 0
    london_gap_end_h: int = 8
    london_gap_end_m: int = 0
    ny_gap_start_h: int = 13
    ny_gap_start_m: int = 0
    ny_gap_end_h: int = 14
    ny_gap_end_m: int = 0

    # v2.00 Asian Range (AR Line) — optional per-day H/L broadcast
    show_asia_range: bool = False


def _is_northern_hemisphere_dst_active() -> bool:
    """Spec Section 5 + Pseudocode: rough Northern Hemisphere DST window."""
    month = datetime.now(timezone.utc).month
    return 3 <= month <= 10


def _hm(h: int, m: int) -> int:
    return h * 60 + m


def compute_sm_worktime_no_autogmt(
    df: pd.DataFrame,
    params: SMWorkTimeNoAutoGmtParams = SMWorkTimeNoAutoGmtParams(),
) -> pd.DataFrame:
    """Per spec sm_WorkTime_no_autogmt.md Section 5 + v2.00 gap overlay.

    Args:
        df: OHLCV DataFrame with a DatetimeIndex (assumed UTC if naive).
        params: SMWorkTimeNoAutoGmtParams. ``broker_gmt`` is the only
            offset source — there is no auto-detect dependency (D-19).

    Returns:
        Copy of df with a new ``session_label`` column whose values are
        in {"ASIA", "LONDON", "US", "LONDON_GAP", "NY_GAP", "OFFHOURS"}.
        If ``params.show_asia_range`` is True, also adds
        ``asia_range_high``, ``asia_range_low``, ``asia_range_pips``.

    Notes:
        - Pitfall 3: NEVER mutates input.
        - D-19: this module does NOT import compute_sm_gmtoffset; the
          offset comes from ``params.broker_gmt`` exclusively.
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

    hour_min = ts.hour * 60 + ts.minute - offset_h * 60
    hour_min = ((hour_min % 1440) + 1440) % 1440

    asia_start = _hm(params.asia_start_h, params.asia_start_m)
    asia_end = _hm(params.asia_end_h, params.asia_end_m)
    london_start = _hm(params.london_start_h, params.london_start_m)
    london_end = _hm(params.london_end_h, params.london_end_m)
    us_start = _hm(params.us_start_h, params.us_start_m)
    us_end = _hm(params.us_end_h, params.us_end_m)

    label = np.full(len(out), "OFFHOURS", dtype=object)
    label[(hour_min >= asia_start) & (hour_min < asia_end)] = "ASIA"
    label[(hour_min >= london_start) & (hour_min < london_end)] = "LONDON"
    label[(hour_min >= us_start) & (hour_min < us_end)] = "US"

    if params.show_gaps:
        lgap_start = _hm(params.london_gap_start_h, params.london_gap_start_m)
        lgap_end = _hm(params.london_gap_end_h, params.london_gap_end_m)
        nygap_start = _hm(params.ny_gap_start_h, params.ny_gap_start_m)
        nygap_end = _hm(params.ny_gap_end_h, params.ny_gap_end_m)

        label[(hour_min >= lgap_start) & (hour_min < lgap_end)] = "LONDON_GAP"
        label[(hour_min >= nygap_start) & (hour_min < nygap_end)] = "NY_GAP"

    out["session_label"] = label

    if params.show_asia_range:
        _attach_asia_range(out, asia_start, asia_end, offset_h)

    return out


def _attach_asia_range(
    out: pd.DataFrame,
    asia_start: int,
    asia_end: int,
    offset_h: int,
) -> None:
    ts = out.index
    hour_min = ts.hour * 60 + ts.minute - offset_h * 60
    hour_min = ((hour_min % 1440) + 1440) % 1440
    in_asia = (hour_min >= asia_start) & (hour_min < asia_end)

    day_key = ts.normalize()
    asia_only = out[in_asia]
    asia_only_days = asia_only.index.normalize()
    daily_high = asia_only.groupby(asia_only_days)["high"].max()
    daily_low = asia_only.groupby(asia_only_days)["low"].min()

    out["asia_range_high"] = day_key.map(daily_high).astype(float)
    out["asia_range_low"] = day_key.map(daily_low).astype(float)
    out["asia_range_pips"] = (out["asia_range_high"] - out["asia_range_low"]) * 10_000.0


__all__ = ["SMWorkTimeNoAutoGmtParams", "compute_sm_worktime_no_autogmt"]
