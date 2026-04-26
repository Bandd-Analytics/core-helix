"""OHLCV cache — Supabase Postgres backing, Title-case OHLC, PiT-safe auto-pull.

Per Phase 8.4 CONTEXT.md decisions:
  D-01: Supabase Postgres backing (project nubmgoyyndtolsjyynln, Session pooler 5432)
  D-02: bars(pair, timeframe, ts, open, high, low, close, volume, source) composite PK
  D-03: Title-case OHLC columns returned (Open, High, Low, Close, Volume)
  D-04: dual-mode fetch — manual CLI (scripts/update_cache.py) + on-demand auto-pull
  Phase 8 D-25: PitClock-active calls never auto-pull (would leak future bars into cache).

RESEARCH §Pattern 1 + §Common Pitfalls 1, 2.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from .pit import FutureBarReadError, pit_active

# Load .env from V2/.env (Phase 8.4 D-01 — operator-managed secret)
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)

_DB_URL = os.environ.get("SUPABASE_DB_URL")


def is_pit_active() -> bool:
    """Cache-side re-export of pit.pit_active() for callers that don't want pit imports.

    True iff caller is inside a non-UNBOUNDED PitClock with-block on this thread.
    See RESEARCH §Pattern 2 / Anti-Patterns.
    """
    return pit_active()


class OHLCVCache:
    """Read-through OHLCV cache backed by Supabase Postgres.

    All callers should use the singleton-friendly constructor:
        cache = OHLCVCache()
        df = cache.get_bars("USDJPY", "H1", start, end)
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url if db_url is not None else _DB_URL
        if not self._db_url:
            raise RuntimeError(
                "SUPABASE_DB_URL not set — add it to V2/.env "
                "(get it from Supabase dashboard -> project nubmgoyyndtolsjyynln "
                "-> Connect -> Session pooler -> URI; use port 5432 not 6543)"
            )

    def _connect(self) -> "psycopg.Connection":
        # prepare_threshold=None disables prepared statements for pgbouncer/pooler
        # compatibility (RESEARCH Pitfall 1 / Supavisor FAQ).
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def get_bars(
        self,
        pair: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        """Fetch bars in [start, end] inclusive. Returns Title-case OHLC.

        If end exceeds max(ts) for this (pair, timeframe) AND we are NOT inside
        a PitClock context, attempt to auto-pull (max_ts, end] from broker (D-04 b).
        Inside a PitClock context, missing bars raise FutureBarReadError instead
        (RESEARCH Anti-Patterns: auto-pulling under PiT leaks future bars).
        """
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT ts, open, high, low, close, volume
                FROM bars
                WHERE pair = %s AND timeframe = %s
                  AND ts BETWEEN %s AND %s
                ORDER BY ts ASC
                """,
                (pair, timeframe, start, end),
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT MAX(ts) AS max_ts FROM bars WHERE pair=%s AND timeframe=%s",
                (pair, timeframe),
            )
            max_ts_row = cur.fetchone()
            max_ts = max_ts_row["max_ts"] if max_ts_row else None

        if max_ts is None or end > max_ts:
            if is_pit_active():
                raise FutureBarReadError(
                    f"Cache requested {pair} {timeframe} up to {end} but "
                    f"cache max_ts={max_ts}; PiT-active so refusing to auto-pull "
                    f"(RESEARCH Anti-Patterns)"
                )
            self._auto_pull(pair, timeframe, since=max_ts, until=end)
            # One retry — auto_pull may insert nothing if broker has no new bars
            return self._read_only(pair, timeframe, start, end)

        return self._rows_to_titlecase_df(rows)

    def _read_only(self, pair: str, timeframe: str,
                    start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """Read-only retry path used after _auto_pull (no recursion)."""
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT ts, open, high, low, close, volume
                FROM bars
                WHERE pair = %s AND timeframe = %s
                  AND ts BETWEEN %s AND %s
                ORDER BY ts ASC
                """,
                (pair, timeframe, start, end),
            )
            rows = cur.fetchall()
        return self._rows_to_titlecase_df(rows)

    @staticmethod
    def _rows_to_titlecase_df(rows: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        return df

    def upsert_bars(
        self,
        pair: str,
        timeframe: str,
        df: pd.DataFrame,
        source: str,
    ) -> int:
        """Insert bars; on (pair, timeframe, ts) conflict do nothing. Returns rows inserted."""
        if df is None or len(df) == 0:
            return 0
        records = [
            (pair, timeframe, ts,
             float(row["Open"]), float(row["High"]),
             float(row["Low"]), float(row["Close"]),
             float(row.get("Volume", 0) or 0), source)
            for ts, row in df.iterrows()
        ]
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO bars (pair, timeframe, ts, open, high, low, close, volume, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pair, timeframe, ts) DO NOTHING
                """,
                records,
            )
            inserted = cur.rowcount
            conn.commit()
        return inserted

    def _auto_pull(
        self,
        pair: str,
        timeframe: str,
        since: Optional[pd.Timestamp],
        until: pd.Timestamp,
    ) -> None:
        """On-demand fetch from broker (D-04 mode b). Lazy import avoids cycle."""
        from scripts.update_cache import fetch_range
        fetched = fetch_range(pair, timeframe, since, until)
        if fetched is not None and len(fetched) > 0:
            self.upsert_bars(pair, timeframe, fetched, source="MT5")


__all__ = ["OHLCVCache", "is_pit_active"]
