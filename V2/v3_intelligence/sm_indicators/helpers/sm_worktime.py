"""sm_WorkTime Python port — Phase 12 Plan 01 v2.00.

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md

Classifies each bar in an OHLCV DataFrame into one of {ASIA, LONDON, US,
LONDON_GAP, NY_GAP, OFFHOURS} per the MMM session schedule (Book p. 8) plus
the v2.00 changeover-zone overlay introduced by the BandD_WorktimeRibbon
visual contract (operator-confirmed 2026-04-28).

Default GMT session windows (Book p. 8):
    Asia        00:30–07:30 GMT
    London      07:30–13:30 GMT
    US          13:30–22:00 GMT

Default GMT changeover windows (v2.00 — 30 min before + 30 min after the
session-open clock event):
    LONDON_GAP  07:00–08:00 GMT  (Asia close - 30m → London open + 30m)
    NY_GAP      13:00–14:00 GMT  (London close - 30m → US open + 30m)

The gap labels OVERWRITE the underlying ASIA/LONDON/US labels at overlap —
the changeover zone is the more analytically interesting state (stop hunts,
trend reversals, traps per MMM theory).

Reads broker GMT offset via compute_sm_gmtoffset. In backtesting mode
(broker_ts=None) this is always 0 — Helix CSVs are UTC-stamped, so session
classification is direct.

Spec D-19: this module DOES depend on sm_gmtoffset, unlike the no_autogmt
sibling.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .sm_gmtoffset import SMGMTOffsetParams, compute_sm_gmtoffset


@dataclass(frozen=True)
class SMWorkTimeParams:
    """Spec Section 3 inputs (v2.00 — gap windows + AR Line opt-in).

    Defaults follow MMM Book p. 8 GMT session windows. Gap defaults
    encode the v2.00 BandD reference: 30 min before + 30 min after each
    session open as a changeover-overlay window.
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

    # v2.00: changeover gap windows (default ±30 min around session open in GMT)
    show_gaps: bool = True
    london_gap_start_h: int = 7
    london_gap_start_m: int = 0
    london_gap_end_h: int = 8
    london_gap_end_m: int = 0
    ny_gap_start_h: int = 13
    ny_gap_start_m: int = 0
    ny_gap_end_h: int = 14
    ny_gap_end_m: int = 0

    # v2.00: optional Asian Range (AR Line) — adds asia_range_high / low / pips
    # columns indexed per-day. Off by default (matches MQ5 InpARLine=false).
    show_asia_range: bool = False

    gmt_params: SMGMTOffsetParams = field(default_factory=SMGMTOffsetParams)


def _hm(h: int, m: int) -> int:
    return h * 60 + m


def compute_sm_worktime(
    df: pd.DataFrame,
    params: SMWorkTimeParams = SMWorkTimeParams(),
) -> pd.DataFrame:
    """Classify bars per spec sm_WorkTime.md Section 5 + v2.00 gap overlay.

    Args:
        df: OHLCV DataFrame with a DatetimeIndex (assumed UTC if naive,
            per Phase 8 PitClock convention).
        params: SMWorkTimeParams with verified MMM session boundaries.

    Returns:
        Copy of df with a new ``session_label`` column whose values are
        in {"ASIA", "LONDON", "US", "LONDON_GAP", "NY_GAP", "OFFHOURS"}.
        If ``params.show_asia_range`` is True, also adds
        ``asia_range_high``, ``asia_range_low``, ``asia_range_pips``
        columns (per-day Asia H/L broadcast to all bars of that day).

    Notes:
        - Pitfall 3: NEVER mutates input.
        - Half-open intervals: a bar at exactly 07:30 GMT classifies as
          LONDON (the new session "wins"), not ASIA — matching MMM Book p. 8.
        - Gap labels overwrite session labels at overlap (the changeover
          window is the analytically interesting state).
    """
    out = df.copy()  # NEVER mutate — Pitfall 3

    offset_h = compute_sm_gmtoffset(params.gmt_params, broker_ts=None)

    ts: pd.DatetimeIndex = out.index
    if not isinstance(ts, pd.DatetimeIndex):
        raise TypeError("compute_sm_worktime requires a DatetimeIndex")

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

        # Gap wins at overlap — the changeover is the analytically
        # interesting state (stop hunts, trend reversals per MMM theory).
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
    """Compute per-day Asia high/low/pips from bars in the Asia window
    and broadcast to every bar of that day. Mirrors MQ5 v2.00 DrawARLine.
    """
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


__all__ = ["SMWorkTimeParams", "compute_sm_worktime"]
