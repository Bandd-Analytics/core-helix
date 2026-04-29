"""SM_IlsleyPsychLevels Python port — Phase 12 Plan 02 / D-07, D-10, D-11 (v2.00).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md

Two independent psychological-level systems:

1. ROUND-NUMBER LEVELS — round-number grid at step_pips intervals (MMM-typical
   50-pip / 100-pip convention). JPY pair edge case via is_jpy flag (3-digit
   pip = 0.01 vs 5-digit pip = 0.0001).

2. WEEKLY FIRST-4HR H/L LEVELS (v2.00) — for each of the last weeks_back
   complete/in-progress ISO weeks, compute the H/L of the first
   week_first_hours * bars_per_hour bars of that week and broadcast them as
   columns weekly_h_{i} / weekly_l_{i} across every row in that week.
   Hypothesis: the first 4 hours of weekly trading establish psychological
   S/R that price respects for the remainder of the week.

Per D-11: function-first surface; D-10 ≥1 GREEN pytest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IlsleyPsychLevelsParams:
    """Spec Section 3 inputs.

    All values are [INFER] per spec Uncertainty log; defaults align with
    MMM-typical 50-pip / 100-pip psychological-level convention.
    """

    # --- Round-number levels (v1 feature) ---
    step_pips: int = 50          # MMM-typical psych level step
    levels_above: int = 5
    levels_below: int = 5
    # Pip math: caller toggles for *JPY pairs (3-digit) — Pitfall: pip math
    is_jpy: bool = False

    # --- Weekly first-4hr H/L levels (v2.00 new feature) ---
    show_weekly_levels: bool = True   # master toggle
    weeks_back: int = 4               # how many past weeks to compute
    week_first_hours: int = 4         # first N hours of each week to sample
    bars_per_hour: int = 1            # default H1 — 1 bar per hour [INFER]


def _pip_size(is_jpy: bool) -> float:
    """3-digit JPY (pip = 0.01) vs 5-digit majors (pip = 0.0001)."""
    return 0.01 if is_jpy else 0.0001


def compute_ilsley_psych_levels(
    df: pd.DataFrame,
    params: IlsleyPsychLevelsParams = IlsleyPsychLevelsParams(),
) -> pd.DataFrame:
    """SM_IlsleyPsychLevels — round-number levels + optional weekly H/L bands.

    Per spec Section 5. Returns immediate above/below for each bar (round-
    number system) and, when show_weekly_levels=True, columns weekly_h_{i} /
    weekly_l_{i} for i in 1..weeks_back (1-indexed, 1 = most recent week).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close) with a
            DatetimeIndex. Assumed H1 cadence unless bars_per_hour differs.
        params: IlsleyPsychLevelsParams.

    Returns:
        DataFrame with the input columns plus:
            psych_level_below  — nearest step_pips multiple ≤ Close
            psych_level_above  — psych_level_below + step_pips × pip
            weekly_h_{i}       — High of the first week_first_hours hours of
                                  week i, broadcast to all rows in that week
                                  (only present when show_weekly_levels=True)
            weekly_l_{i}       — Low of the first week_first_hours hours of
                                  week i, broadcast to all rows in that week
                                  (only present when show_weekly_levels=True)
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # ------------------------------------------------------------------
    # 1. Round-number levels (v1 feature, always computed)
    # ------------------------------------------------------------------
    pip = _pip_size(params.is_jpy)
    step = params.step_pips * pip

    out["psych_level_below"] = np.floor(out["Close"] / step) * step
    out["psych_level_above"] = out["psych_level_below"] + step

    # ------------------------------------------------------------------
    # 2. Weekly first-4hr H/L levels (v2.00 new feature)
    # ------------------------------------------------------------------
    if params.show_weekly_levels:
        _add_weekly_levels(out, params)

    return out


def _add_weekly_levels(out: pd.DataFrame, params: IlsleyPsychLevelsParams) -> None:
    """Compute weekly first-4hr H/L columns and add them in-place to `out`.

    Week detection uses ISO-week Monday starts (dayofweek == 0).
    For each week group (most-recent-first), take the first
    week_first_hours * bars_per_hour bars, compute max(High) / min(Low),
    and broadcast back to every row that falls in that week.

    Columns added: weekly_h_1 .. weekly_h_{weeks_back}
                   weekly_l_1 .. weekly_l_{weeks_back}
    where index 1 = most recent (current or last complete) week.

    Every non-obvious branch carries # [INFER].
    """
    bars_to_sample = params.week_first_hours * params.bars_per_hour

    # Resample to W-MON groups: each group key is the Monday that starts the
    # ISO week.  sort=False preserves natural time order within each group.
    # [INFER] pd.Grouper(freq='W-MON') closes on Monday, labelled by the
    # Monday of the NEXT week end; we shift back one week to get the
    # Monday-start label.  Using resample directly gives Monday-labelled
    # groups when freq='W-MON' with closed/label='left'.
    weekly_groups = out.resample("W-MON", closed="left", label="left")  # [INFER]

    # Collect (week_label, hi, lo) for each week, most-recent-first
    week_summaries: list[tuple[pd.Timestamp, float, float]] = []

    for week_label, group in weekly_groups:
        if group.empty:
            continue  # [INFER] skip empty partial-week buckets
        sample = group.iloc[:bars_to_sample]
        hi = float(sample["High"].max())
        lo = float(sample["Low"].min())
        week_summaries.append((week_label, hi, lo))

    # Reverse so index 0 = most recent
    week_summaries = list(reversed(week_summaries))

    # Add columns for the most recent weeks_back weeks
    for rank, (week_label, hi, lo) in enumerate(week_summaries[: params.weeks_back]):
        col_h = f"weekly_h_{rank + 1}"
        col_l = f"weekly_l_{rank + 1}"

        # Determine row mask for this week: rows from week_label (inclusive)
        # to week_label + 7 days (exclusive).  [INFER]
        week_end = week_label + pd.Timedelta(days=7)
        mask = (out.index >= week_label) & (out.index < week_end)

        out.loc[mask, col_h] = hi
        out.loc[mask, col_l] = lo


__all__ = [
    "IlsleyPsychLevelsParams",
    "compute_ilsley_psych_levels",
    "_pip_size",
]
