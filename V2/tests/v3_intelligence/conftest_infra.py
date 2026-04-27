"""Phase 8.4 test fixtures (INFRA-01..04).

Provides:
    sample_trade        — canonical trade dict matching backtest_hybrid.py rec shape
    in_memory_logger    — TradeLogger pointing at :memory: SQLite for fast unit tests
    mock_chroma_collection — Object satisfying RAGSignalFilter._col contract (.upsert, .count)
    mock_psycopg_conn   — Context-manager-shaped mock for psycopg.connect() in unit tests
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def sample_trade() -> dict:
    """Trade dict matching V2/backtest/backtest_hybrid.py rec at lines 240-261."""
    return {
        "symbol": "USDJPY",
        "type": "DAILY_SWING_LONG",
        "strategy": "SWING",
        "entry_date": pd.Timestamp("2024-01-02 10:00"),
        "exit_date": pd.Timestamp("2024-01-04 14:00"),
        "entry_price": 145.123,
        "exit_price": 146.567,
        "pnl_pct": 0.0099,
        "bars_held": 52,
        "size": 1.0,
        "exit_reason": "target_hit",
        "daily_z": -2.3,
        "h1_z": -1.2,
        "h1_atr": 0.0150,
        "vol_percentile": 45.0,
        "session": "NY",
        "hour_utc": 14,
    }


@pytest.fixture
def in_memory_logger(tmp_path):
    """TradeLogger with a tmp_path-scoped SQLite file (fast + isolated)."""
    from v3_intelligence.trade_logger import TradeLogger
    return TradeLogger(db_path=tmp_path / "test_marketmind.db")


@pytest.fixture
def mock_chroma_collection() -> MagicMock:
    """Mock satisfying ChromaDB collection contract used by RAGSignalFilter."""
    col = MagicMock()
    col._docs = {}  # noqa: SLF001 — test scaffold
    def _upsert(ids, documents, metadatas):
        for i, d, m in zip(ids, documents, metadatas):
            col._docs[i] = (d, m)
    col.upsert.side_effect = _upsert
    col.count.side_effect = lambda: len(col._docs)
    return col


@pytest.fixture
def mock_psycopg_conn():
    """Returns a callable replacing psycopg.connect that yields a context-managed mock."""
    @contextmanager
    def _connect(url=None, **kw):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = lambda self: cur
        cur.__exit__ = lambda *a: None
        conn.cursor = MagicMock(return_value=cur)
        conn.__enter__ = lambda self: conn
        conn.__exit__ = lambda *a: None
        conn.commit = MagicMock()
        cur.fetchall = MagicMock(return_value=[])
        cur.fetchone = MagicMock(return_value={"max_ts": None})
        cur.execute = MagicMock()
        cur.executemany = MagicMock()
        cur.rowcount = 0
        yield conn
    return _connect


# ── Phase 8.5 fixtures (Wave 0) ───────────────────────────────────────────

@pytest.fixture
def synthetic_trades_factory():
    """Factory: produce a trades DataFrame with controllable session/hour distribution.

    Returns a callable: factory(n_trades, entry_hour=8, pnl_mean=0.001, pnl_std=0.002,
                                 pair='USDJPY', start='2024-01-15')
    Output columns: entry_ts (UTC), exit_ts, pnl_pct, direction, strategy, pair, timeframe.
    """
    import numpy as np
    import pandas as pd

    def _factory(n_trades: int, entry_hour: int = 8,
                 pnl_mean: float = 0.001, pnl_std: float = 0.002,
                 pair: str = "USDJPY",
                 start: str = "2024-01-15") -> pd.DataFrame:
        rng = np.random.default_rng(seed=42)
        base = pd.Timestamp(start, tz="UTC")
        # Spread n_trades across consecutive weekdays at the given hour
        entry_ts = pd.DatetimeIndex([
            base + pd.Timedelta(days=i) + pd.Timedelta(hours=entry_hour)
            for i in range(n_trades)
        ])
        pnl = rng.normal(pnl_mean, pnl_std, n_trades)
        return pd.DataFrame({
            "entry_ts":  entry_ts,
            "exit_ts":   entry_ts + pd.Timedelta(hours=4),
            "pnl_pct":   pnl,
            "direction": ["LONG" if p > 0 else "SHORT" for p in pnl],
            "strategy":  "TEST_STRAT",
            "pair":      pair,
            "timeframe": "H1",
        })

    return _factory


@pytest.fixture
def synthetic_bars_with_spikes():
    """Factory: produce 4yr OHLC bars with injected volatility spikes at a given pattern.

    Returns: (bars_df, injected_timestamps).
    spike_pattern values: 'first_friday_1230' -> 1st Friday of every month at 12:30 UTC.
    Spike injection: multiply (High - Low) by spike_magnitude on those bars.
    """
    import numpy as np
    import pandas as pd

    def _factory(pair: str = "EURUSD", timeframe: str = "H1",
                 n_years: int = 4, spike_pattern: str = "first_friday_1230",
                 spike_magnitude: float = 10.0):
        freq = {"H1": "h", "M15": "15min", "Daily": "D", "H4": "4h"}[timeframe]
        end = pd.Timestamp("2026-01-01", tz="UTC")
        start = end - pd.DateOffset(years=n_years)
        idx = pd.date_range(start, end, freq=freq, tz="UTC")
        rng = np.random.default_rng(seed=123)

        close = 1.10 + np.cumsum(rng.normal(0, 0.0001, len(idx)))
        high = close + np.abs(rng.normal(0, 0.0005, len(idx)))
        low  = close - np.abs(rng.normal(0, 0.0005, len(idx)))
        opn  = close + rng.normal(0, 0.0001, len(idx))
        vol  = rng.integers(100, 1000, len(idx))

        bars = pd.DataFrame({
            "Open": opn, "High": high, "Low": low, "Close": close, "Volume": vol,
        }, index=idx)
        bars.index.name = "ts"

        # Inject spikes
        injected = []
        if spike_pattern == "first_friday_1230":
            for ts in idx:
                if ts.dayofweek == 4 and 1 <= ts.day <= 7 and ts.hour == 12:
                    bars.loc[ts, "High"] = bars.loc[ts, "Close"] + abs(
                        bars.loc[ts, "High"] - bars.loc[ts, "Close"]) * spike_magnitude
                    bars.loc[ts, "Low"]  = bars.loc[ts, "Close"] - abs(
                        bars.loc[ts, "Close"] - bars.loc[ts, "Low"])  * spike_magnitude
                    injected.append(ts)
        return bars, pd.DatetimeIndex(injected)

    return _factory
