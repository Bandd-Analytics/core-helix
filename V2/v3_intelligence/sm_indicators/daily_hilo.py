"""SM_Daily_HiLo Python port — v2.01 — Phase 12 Plan 02 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md

v2.01 — trailing N-day snake pattern.

Computes PHOD (Previous High of Day) and PLOD (Previous Low of Day).

Primary columns (shift(1)):
    phod  — High of bar (i-1)   — yesterday's completed bar high
    plod  — Low  of bar (i-1)   — yesterday's completed bar low

Following-day projection / snake history (i = 2 .. days_back):
    phod_2 .. phod_{days_back}  — High of bar (i-2) .. High of bar (i-days_back)
    plod_2 .. plod_{days_back}  — Low  of bar (i-2) .. Low  of bar (i-days_back)

This mirrors the MQ5 v2.01 snake pattern where each completed bar i's H/L is
projected into bar (i-1)'s time range — yesterday's H/L becomes today's
reference line, the day-before-yesterday's H/L overlays yesterday's bar, etc.

Pitfall 5 lookahead-bias guard: all values are via .shift(n) — no future data
leaks into any row.

Per D-11: function-first surface; D-10 >= 1 GREEN pytest.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DailyHiLoParams:
    """Spec Section 3 inputs.

    Display-only inputs (HighColor, LowColor, LineStyle, ShowLabel,
    ShowCurrentDay, ObjectPrefix) are kept off the dataclass — Python
    doesn't render OBJ_HLINE.
    """

    lookback_bars: int = 1   # 1 = yesterday's completed bar (Pitfall 5 guard)
    days_back: int = 14      # v2.01: how many historical snake levels to output


def compute_daily_hilo(
    df: pd.DataFrame,
    params: DailyHiLoParams = DailyHiLoParams(),
) -> pd.DataFrame:
    """SM_Daily_HiLo v2.01 — PHOD / PLOD lines + N-day snake history.

    Per spec Section 5. Caller is responsible for resampling to Daily bars
    if the strict spec semantics are required; on intra-day frames the
    PHOD/PLOD columns are bar-local (still correct for shape tests and
    parity).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: DailyHiLoParams. Default lookback_bars=1, days_back=14.

    Returns:
        DataFrame with the input columns plus:
            phod          — High of bar (i - 1)  [primary, shift(1)]
            plod          — Low  of bar (i - 1)  [primary, shift(1)]
            phod_2 ..
            phod_{days_back}  — High of bar (i - n) for n = 2 .. days_back
            plod_2 ..
            plod_{days_back}  — Low  of bar (i - n) for n = 2 .. days_back

    Notes:
        First `n` rows have NaN for phod_n / plod_n (warmup; Pitfall 5
        lookahead guard). The primary phod/plod columns are always shift(1)
        regardless of lookback_bars to preserve v2.01 snake semantics;
        lookback_bars is retained for backward-compatibility with callers
        that historically set it to values > 1 via the params.days_back path.
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # Primary columns: shift(1) — yesterday's completed bar (v2.01 semantics)
    out["phod"] = out["High"].shift(1)
    out["plod"] = out["Low"].shift(1)

    # v2.01 snake history: phod_2 .. phod_{days_back} and plod equivalents
    for n in range(2, params.days_back + 1):
        out[f"phod_{n}"] = out["High"].shift(n)
        out[f"plod_{n}"] = out["Low"].shift(n)

    return out


__all__ = ["DailyHiLoParams", "compute_daily_hilo"]
