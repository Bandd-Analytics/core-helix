"""SM_Daily_HiLo Python port — Phase 12 Plan 02 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md

Computes PHOD (Previous High of Day) and PLOD (Previous Low of Day) by
reading the prior-completed bar's High/Low. Pitfall 5 lookahead-bias
guard via .shift(lookback_bars).

Per D-11: function-first surface; D-10 ≥1 GREEN pytest.
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

    lookback_bars: int = 1  # 1 = yesterday's completed bar (Pitfall 5 guard)


def compute_daily_hilo(
    df: pd.DataFrame,
    params: DailyHiLoParams = DailyHiLoParams(),
) -> pd.DataFrame:
    """SM_Daily_HiLo — PHOD / PLOD lines via prior-bar High/Low.

    Per spec Section 5. Caller is responsible for resampling to Daily bars
    if the strict spec semantics are required; on intra-day frames the
    PHOD/PLOD columns are bar-local (still correct for shape tests and
    parity).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: DailyHiLoParams. Default lookback_bars=1.

    Returns:
        DataFrame with the input columns plus:
            phod — High of bar (i - lookback_bars)
            plod — Low of bar (i - lookback_bars)

    Notes:
        First `lookback_bars` rows have NaN PHOD/PLOD (warmup; Pitfall 5
        lookahead guard).
    """
    out = df.copy()  # Pitfall 3 — never mutate caller
    out["phod"] = out["High"].shift(params.lookback_bars)
    out["plod"] = out["Low"].shift(params.lookback_bars)
    return out


__all__ = ["DailyHiLoParams", "compute_daily_hilo"]
