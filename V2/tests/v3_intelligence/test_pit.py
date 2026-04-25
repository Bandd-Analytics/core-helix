"""PitClock tests (REGM-03, D-06/D-08/D-09/D-25).

RED until Plan 03 lands V2/v3_intelligence/pit.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _ohlc_df(n: int = 100, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="h")
    return pd.DataFrame({"close": np.arange(n, dtype=float)}, index=idx)


def test_pitclock_context_manager_enters_and_exits() -> None:
    """REGM-03: PitClock works as a context manager."""
    from v3_intelligence.pit import PitClock
    t = pd.Timestamp("2024-01-02 00:00:00")
    with PitClock(t) as clock:
        assert clock is not None


def test_assert_no_future_raises_on_future_ts() -> None:
    """REGM-03 / D-09 mandatory test: a deliberate out-of-order read raises."""
    from v3_intelligence.pit import PitClock, FutureBarReadError
    t = pd.Timestamp("2024-01-02 00:00:00")
    with PitClock(t) as clock:
        with pytest.raises(FutureBarReadError):
            clock.assert_no_future(t + pd.Timedelta(hours=1))


def test_assert_no_future_passes_on_past_or_equal_ts() -> None:
    """REGM-03 / D-08: ts <= as_of does NOT raise."""
    from v3_intelligence.pit import PitClock
    t = pd.Timestamp("2024-01-02 00:00:00")
    with PitClock(t) as clock:
        clock.assert_no_future(t)
        clock.assert_no_future(t - pd.Timedelta(hours=1))


def test_read_returns_truncated_view() -> None:
    """REGM-03: clock.read(df) returns rows with index <= as_of when df extends past cutoff."""
    from v3_intelligence.pit import PitClock
    df = _ohlc_df(100, "2024-01-01")  # spans Jan 1–5
    t = df.index[49]
    with PitClock(t) as clock:
        out = clock.read(df)
        assert (out.index <= t).all()
        assert len(out) == 50


def test_read_raises_when_no_rows_at_or_before_cutoff() -> None:
    """REGM-03: clock.read on a fully-future df raises FutureBarReadError."""
    from v3_intelligence.pit import PitClock, FutureBarReadError
    df = _ohlc_df(100, "2025-01-01")  # entirely after the cutoff below
    t = pd.Timestamp("2024-01-01 00:00:00")
    with PitClock(t) as clock:
        with pytest.raises(FutureBarReadError):
            clock.read(df)


def test_unbounded_sentinel_allows_any_read() -> None:
    """D-25: PitClock.UNBOUNDED returns df verbatim, never raises."""
    from v3_intelligence.pit import PitClock
    df = _ohlc_df(100, "2024-01-01")
    out = PitClock.UNBOUNDED.read(df)
    assert len(out) == 100
    PitClock.UNBOUNDED.assert_no_future(pd.Timestamp("2099-01-01"))


def test_advance_must_be_monotone() -> None:
    """clock.advance(t-1h) raises when called after as_of=t (no rewind)."""
    from v3_intelligence.pit import PitClock
    t = pd.Timestamp("2024-01-02 00:00:00")
    with PitClock(t) as clock:
        with pytest.raises(ValueError):
            clock.advance(t - pd.Timedelta(hours=1))
        # Forward is fine
        clock.advance(t + pd.Timedelta(hours=1))


def test_advance_moves_cutoff_forward() -> None:
    """advance(t2) means subsequent reads enforce against t2."""
    from v3_intelligence.pit import PitClock
    df = _ohlc_df(100, "2024-01-01")
    t1 = df.index[10]
    t2 = df.index[50]
    with PitClock(t1) as clock:
        out1 = clock.read(df)
        assert len(out1) == 11
        clock.advance(t2)
        out2 = clock.read(df)
        assert len(out2) == 51
