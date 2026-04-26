"""ADR helper (INFRA-04 / D-18).

Public API:
    compute_adr(pair, timeframe, lookback_days=20) -> float

Loads Daily bars from cache (PiT-aware via OHLCVCache). Returns mean of
(High - Low) over the most recent `lookback_days` bars. Used by future
temporal/risk modules and the ADR_Levels MQL5 indicator (D-19).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd


def _load_daily_bars(pair: str, lookback_days: int) -> pd.DataFrame:
    """Load most recent N+5 (buffer for missing days) Daily bars from cache.

    Lazy import of OHLCVCache to keep this module testable with `patch.object`.
    The +5 buffer absorbs weekends / holidays so we still have `lookback_days`
    real bars to average.
    """
    from .cache import OHLCVCache
    cache = OHLCVCache()
    end = pd.Timestamp(datetime.now(timezone.utc))
    start = end - timedelta(days=lookback_days + 5)
    return cache.get_bars(pair, "Daily", start, end)


def compute_adr(pair: str, timeframe: str, lookback_days: int = 20) -> float:
    """Average Daily Range over `lookback_days` Daily bars (D-18).

    Args:
        pair: pair symbol e.g. 'USDJPY'
        timeframe: kept for future per-timeframe ADR (currently always reads Daily)
        lookback_days: number of recent Daily bars to average

    Returns:
        Mean of (High - Low) in price units. Positive float.
    """
    df = _load_daily_bars(pair, lookback_days)
    if df is None or len(df) == 0:
        raise ValueError(f"No Daily bars in cache for {pair}")
    recent = df.iloc[-lookback_days:] if len(df) >= lookback_days else df
    return float((recent["High"] - recent["Low"]).mean())


__all__ = ["compute_adr"]
