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
