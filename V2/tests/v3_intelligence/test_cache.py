"""OHLCVCache unit tests (INFRA-01 / D-01..D-04).

RED until Plan 02 lands V2/v3_intelligence/cache.py.
"""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


def test_get_bars_returns_titlecase_columns(mock_psycopg_conn) -> None:
    """D-03: get_bars returns DataFrame with Title-case OHLC columns."""
    from v3_intelligence.cache import OHLCVCache

    sample_rows = [
        {"ts": pd.Timestamp("2024-01-02 10:00", tz="UTC"),
         "open": 145.10, "high": 145.20, "low": 145.05, "close": 145.15, "volume": 1000},
        {"ts": pd.Timestamp("2024-01-02 11:00", tz="UTC"),
         "open": 145.15, "high": 145.30, "low": 145.10, "close": 145.25, "volume": 1100},
    ]

    @patch("v3_intelligence.cache.psycopg.connect", side_effect=mock_psycopg_conn)
    def _run(_):
        cache = OHLCVCache(db_url="postgresql://x")
        # max_ts = far future so no auto-pull
        with patch.object(cache, "_auto_pull"):
            with patch("v3_intelligence.cache.psycopg.connect") as conn_mock:
                conn = conn_mock.return_value.__enter__.return_value
                cur = conn.cursor.return_value.__enter__.return_value
                cur.fetchall.return_value = sample_rows
                cur.fetchone.return_value = {"max_ts": pd.Timestamp("2030-01-01", tz="UTC")}
                df = cache.get_bars("USDJPY", "H1",
                                     pd.Timestamp("2024-01-02 10:00", tz="UTC"),
                                     pd.Timestamp("2024-01-02 11:00", tz="UTC"))
                assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    _run()


def test_pit_active_blocks_auto_pull() -> None:
    """D-04 / RESEARCH Pattern 1: get_bars inside PitClock raises FutureBarReadError."""
    from v3_intelligence.cache import OHLCVCache
    from v3_intelligence.pit import PitClock, FutureBarReadError

    cache = OHLCVCache(db_url="postgresql://x")
    t = pd.Timestamp("2024-01-02 10:00", tz="UTC")
    end = t + pd.Timedelta(hours=24)

    with patch("v3_intelligence.cache.psycopg.connect") as conn_mock:
        conn = conn_mock.return_value.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []
        cur.fetchone.return_value = {"max_ts": t}  # max < end -> would auto-pull

        with PitClock(t):
            with pytest.raises(FutureBarReadError):
                cache.get_bars("USDJPY", "H1", t, end)


def test_get_bars_no_pit_triggers_auto_pull() -> None:
    """D-04 mode b: outside PitClock context, get_bars calls _auto_pull when range exceeds max_ts."""
    from v3_intelligence.cache import OHLCVCache

    cache = OHLCVCache(db_url="postgresql://x")
    t = pd.Timestamp("2024-01-02 10:00", tz="UTC")
    end = t + pd.Timedelta(hours=24)

    with patch.object(cache, "_auto_pull") as ap, \
         patch("v3_intelligence.cache.psycopg.connect") as conn_mock:
        conn = conn_mock.return_value.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []
        # Two .fetchone() calls: rows query result then max_ts query; behavior must trigger _auto_pull
        cur.fetchone.side_effect = [{"max_ts": t}, {"max_ts": t + pd.Timedelta(hours=24)}]
        cache.get_bars("USDJPY", "H1", t, end)
        ap.assert_called_once()


def test_upsert_bars_uses_on_conflict_do_nothing() -> None:
    """D-04: upsert_bars issues INSERT ... ON CONFLICT DO NOTHING for idempotency."""
    from v3_intelligence.cache import OHLCVCache

    cache = OHLCVCache(db_url="postgresql://x")
    df = pd.DataFrame({
        "Open": [145.1], "High": [145.2], "Low": [145.0], "Close": [145.15], "Volume": [1000],
    }, index=[pd.Timestamp("2024-01-02 10:00", tz="UTC")])

    with patch("v3_intelligence.cache.psycopg.connect") as conn_mock:
        conn = conn_mock.return_value.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value
        cur.rowcount = 1
        n = cache.upsert_bars("USDJPY", "H1", df, source="MT5")
        assert n == 1
        sql_text = cur.executemany.call_args[0][0]
        assert "INSERT INTO bars" in sql_text
        assert "ON CONFLICT" in sql_text
        assert "DO NOTHING" in sql_text


def test_is_pit_active_default_false() -> None:
    """is_pit_active() returns False outside any PitClock context."""
    from v3_intelligence.cache import is_pit_active
    assert is_pit_active() is False


def test_is_pit_active_true_inside_pitclock() -> None:
    """is_pit_active() returns True inside a non-UNBOUNDED PitClock context."""
    from v3_intelligence.cache import is_pit_active
    from v3_intelligence.pit import PitClock
    t = pd.Timestamp("2024-01-02 10:00")
    with PitClock(t):
        assert is_pit_active() is True
    assert is_pit_active() is False


def test_is_pit_active_unbounded_stays_false() -> None:
    """RESEARCH Pattern 2: PitClock.UNBOUNDED does NOT bump pit_active depth."""
    from v3_intelligence.cache import is_pit_active
    from v3_intelligence.pit import PitClock
    with PitClock.UNBOUNDED:
        assert is_pit_active() is False


def test_constructor_raises_when_db_url_missing(monkeypatch) -> None:
    """RESEARCH Pattern 1: OHLCVCache() with no SUPABASE_DB_URL raises clear error."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    from v3_intelligence import cache as cache_mod
    monkeypatch.setattr(cache_mod, "_DB_URL", None)
    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
        cache_mod.OHLCVCache(db_url=None)
