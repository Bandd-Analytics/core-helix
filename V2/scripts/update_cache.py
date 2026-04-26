"""V2/scripts/update_cache.py — Phase 8.4 INFRA-01 / D-04 cache pre-warming CLI.

Two modes:
  Mode A (manual batch — D-04 mode a):
      python -m scripts.update_cache --pair USDJPY --tf H1 --since auto
      python -m scripts.update_cache --all                 # 8 pairs × {M15, H1, H4, Daily}

  Mode B (programmatic — D-04 mode b):
      from scripts.update_cache import fetch_range
      df = fetch_range("USDJPY", "H1", since=None, until=now)

The script preserves V2/scripts/download_history.py's failover chain pattern.
On Linux dev hosts without MetaTrader5 package, fetch_range falls back to
read-from-CSV (existing V2/data/{PAIR}_*.csv files) so cache pre-warming
works end-to-end without a live MT5 install (Phase 7 D-15 / Phase 8 P04 pattern).

For H4 specifically — RESEARCH §Pitfall 3 — operator MUST scroll H4 charts
back 4yr in the IC Markets MT5 GUI before running this script with --tf H4,
or `copy_rates_range` returns < 1000 bars. The MT5 GUI export path (A) in
download_history.py header is the reliable backup.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# MetaTrader5 is Windows COM only; on Linux we fall back to CSV (Phase 7 D-15).
try:
    import MetaTrader5 as mt5  # type: ignore[import-not-found]
    _MT5_AVAILABLE = True
except ModuleNotFoundError:
    mt5 = None  # type: ignore[assignment]
    _MT5_AVAILABLE = False

from v3_intelligence.cache import OHLCVCache

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

EIGHT_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]
ALL_TIMEFRAMES = ["M15", "H1", "H4", "Daily"]

# MT5 timeframe constants (numeric values guarded behind _MT5_AVAILABLE)
_MT5_TF = {
    "M15":   getattr(mt5, "TIMEFRAME_M15", None) if _MT5_AVAILABLE else None,
    "H1":    getattr(mt5, "TIMEFRAME_H1", None)  if _MT5_AVAILABLE else None,
    "H4":    getattr(mt5, "TIMEFRAME_H4", None)  if _MT5_AVAILABLE else None,
    "Daily": getattr(mt5, "TIMEFRAME_D1", None)  if _MT5_AVAILABLE else None,
}

_CSV_NAMES = {
    "Daily": "{pair}_DAILY_2015-2026.csv",
    "H1":    "{pair}_H1_4yr.csv",
    "H4":    "{pair}_H4_4yr.csv",
    "M15":   "{pair}_M15_60d.csv",
}


def fetch_range(
    pair: str,
    timeframe: str,
    since: Optional[pd.Timestamp],
    until: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Broker-side fetch of bars in (since, until]. Returns DataFrame with
    Title-case OHLC columns + DatetimeIndex, or None on failure.

    On Linux without MetaTrader5: reads from V2/data/{PAIR}_<TF>_*.csv and
    filters to (since, until]. Honors Phase 7 D-15 Linux failover.
    """
    if _MT5_AVAILABLE:
        return _fetch_from_mt5(pair, timeframe, since, until)
    return _fetch_from_csv(pair, timeframe, since, until)


def _fetch_from_mt5(
    pair: str, timeframe: str,
    since: Optional[pd.Timestamp], until: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    if not mt5.initialize():
        print(f"  ERROR: MT5 init failed — {mt5.last_error()}", file=sys.stderr)
        return None
    tf_const = _MT5_TF.get(timeframe)
    if tf_const is None:
        print(f"  ERROR: unsupported timeframe {timeframe}", file=sys.stderr)
        return None
    start_dt = since.to_pydatetime() if since is not None else (until - timedelta(days=4*365 + 2)).to_pydatetime()
    end_dt = until.to_pydatetime()
    rates = mt5.copy_rates_range(pair, tf_const, start_dt, end_dt)
    if rates is None or len(rates) == 0:
        print(f"  WARN: 0 bars returned for {pair} {timeframe}", file=sys.stderr)
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                              "close": "Close", "tick_volume": "Volume"})
    return df[["Open", "High", "Low", "Close", "Volume"]]


def _fetch_from_csv(
    pair: str, timeframe: str,
    since: Optional[pd.Timestamp], until: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Linux failover (Phase 7 D-15 / Phase 8 P04). Reads existing CSV."""
    name_template = _CSV_NAMES.get(timeframe)
    if name_template is None:
        return None
    csv_path = DATA_DIR / name_template.format(pair=pair)
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)
    # Normalize index to UTC tz-aware
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    if since is not None:
        df = df[df.index > since]
    df = df[df.index <= until]
    # Ensure Title-case OHLC columns
    rename_map = {c: c.capitalize() for c in df.columns if c.lower() in ("open", "high", "low", "close", "volume")}
    df = df.rename(columns=rename_map)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    return df[keep]


def update_pair_tf(pair: str, timeframe: str, since_arg: str) -> int:
    """Pre-warm cache for one (pair, timeframe). Returns rows inserted."""
    cache = OHLCVCache()
    if since_arg == "auto":
        with cache._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT MAX(ts) FROM bars WHERE pair=%s AND timeframe=%s",
                        (pair, timeframe))
            row = cur.fetchone()
            since = row[0] if row and row[0] else None
        if since is not None:
            since = pd.Timestamp(since)
    elif since_arg in (None, "all"):
        since = None
    else:
        since = pd.Timestamp(since_arg, tz="UTC")
    until = pd.Timestamp(datetime.now(timezone.utc))
    df = fetch_range(pair, timeframe, since, until)
    if df is None or len(df) == 0:
        print(f"  {pair} {timeframe}: 0 new bars (cache up-to-date or broker empty)")
        return 0
    n = cache.upsert_bars(pair, timeframe, df, source="MT5" if _MT5_AVAILABLE else "CSV-fallback")
    print(f"  {pair} {timeframe}: {n} new bars inserted (skipped duplicates per ON CONFLICT)")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(prog="update_cache",
        description="Phase 8.4 INFRA-01 cache pre-warming CLI (D-04 mode a)")
    ap.add_argument("--pair", help="Single pair (e.g. USDJPY)")
    ap.add_argument("--tf", choices=ALL_TIMEFRAMES, help="Timeframe")
    ap.add_argument("--since", default="auto",
                    help="Start: 'auto' (= cache MAX(ts)), 'all' (full 4yr), or YYYY-MM-DD")
    ap.add_argument("--all", action="store_true",
                    help="Iterate all 8 pairs × 4 timeframes (32 fetches)")
    args = ap.parse_args()

    if args.all:
        total = 0
        for p in EIGHT_PAIRS:
            for tf in ALL_TIMEFRAMES:
                total += update_pair_tf(p, tf, args.since)
        print(f"\nTotal new bars inserted: {total}")
        return 0

    if not args.pair or not args.tf:
        ap.error("--pair and --tf are required unless --all is set")
    update_pair_tf(args.pair, args.tf, args.since)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
