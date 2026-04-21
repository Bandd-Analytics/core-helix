#!/usr/bin/env python3
"""
fetch_data.py — Automated historical forex data downloader.

Source: Dukascopy public datafeed (no registration, no API key).
Fetches hourly tick files (bi5 format), resamples to M15 / H1 / Daily,
saves to data/ directory in the same format the backtester expects.

Output files:
  {SYM}_M15.csv       — full history M15 (replaces _M15_60d.csv in backtester)
  {SYM}_H1.csv        — full history H1
  {SYM}_DAILY.csv     — full history Daily

Usage:
  python fetch_data.py                     # all 8 pairs, 2022-01-01 to today
  python fetch_data.py --since 2020        # from 2020 onwards
  python fetch_data.py --sym GBPUSD        # single pair only
  python fetch_data.py --tf M15            # M15 only (skip H1/Daily)
  python fetch_data.py --workers 30        # concurrent connections (default 20)

Dukascopy tick data URL pattern:
  https://datafeed.dukascopy.com/datafeed/{SYM}/{YEAR}/{MONTH-1:02d}/{DAY:02d}/{HOUR:02d}h_ticks.bi5
  Note: Dukascopy months are 0-indexed (Jan=00, Dec=11).

bi5 format (after LZMA decompression):
  Each record = 20 bytes: [uint32 ms_from_hour, uint32 ask, uint32 bid, float32 ask_vol, float32 bid_vol]
  Price scaling: JPY pairs ÷ 1000, all others ÷ 100000
"""
import asyncio
import struct
import lzma
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import pandas as pd
import numpy as np

# ── Config ─────────────────────────────────────────────────────────────────────

SYMBOLS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]

PRICE_SCALE = {"USDJPY": 1000, "GBPJPY": 1000}
DEFAULT_SCALE = 100_000

BASE_URL = "https://datafeed.dukascopy.com/datafeed"

DATA_DIR = Path(__file__).parent / "data"

# ── Tick parsing ────────────────────────────────────────────────────────────────

def _parse_bi5(raw_bytes: bytes, sym: str, hour_dt: datetime) -> pd.DataFrame:
    """Decompress and parse a Dukascopy bi5 tick file into a DataFrame."""
    if not raw_bytes:
        return pd.DataFrame()
    try:
        data = lzma.decompress(raw_bytes, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError:
        try:
            data = lzma.decompress(raw_bytes)
        except lzma.LZMAError:
            return pd.DataFrame()

    n = len(data) // 20
    if n == 0:
        return pd.DataFrame()

    scale = PRICE_SCALE.get(sym, DEFAULT_SCALE)
    rows = []
    epoch = hour_dt.replace(tzinfo=timezone.utc).timestamp()

    for i in range(n):
        off = i * 20
        ms, ask_i, bid_i = struct.unpack('>III', data[off:off+12])
        ts = epoch + ms / 1000.0
        ask = ask_i / scale
        bid = bid_i / scale
        rows.append((ts, (ask + bid) / 2.0))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['ts', 'price'])
    df.index = pd.to_datetime(df['ts'], unit='s', utc=True)
    return df[['price']]


def _ticks_to_ohlcv(ticks: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample tick mid-price to OHLCV candles."""
    ohlcv = ticks['price'].resample(freq).ohlc()
    ohlcv.columns = ['Open', 'High', 'Low', 'Close']
    ohlcv['Volume'] = 0
    return ohlcv.dropna()


# ── Async downloader ────────────────────────────────────────────────────────────

def _url(sym: str, dt: datetime) -> str:
    return f"{BASE_URL}/{sym}/{dt.year}/{dt.month-1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5"


async def _fetch_hour(session: aiohttp.ClientSession, sym: str, dt: datetime,
                      sem: asyncio.Semaphore) -> tuple[datetime, pd.DataFrame]:
    url = _url(sym, dt)
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    raw = await resp.read()
                    return dt, _parse_bi5(raw, sym, dt)
                return dt, pd.DataFrame()
        except Exception:
            return dt, pd.DataFrame()


async def _download_symbol(sym: str, start: datetime, end: datetime,
                           workers: int, show_progress: bool = True) -> pd.DataFrame:
    """Download all hourly tick files for a symbol between start and end."""
    hours = []
    cur = start.replace(minute=0, second=0, microsecond=0)
    while cur < end:
        # Skip weekends (Dukascopy market hours: Sun 22 UTC - Fri 22 UTC approximately)
        if not (cur.weekday() == 5 or (cur.weekday() == 6 and cur.hour < 21)):
            hours.append(cur)
        cur += timedelta(hours=1)

    sem = asyncio.Semaphore(workers)
    ticks_frames = []
    done = 0
    total = len(hours)

    connector = aiohttp.TCPConnector(limit=workers * 2, limit_per_host=workers)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_hour(session, sym, h, sem) for h in hours]
        for coro in asyncio.as_completed(tasks):
            dt, df = await coro
            done += 1
            if show_progress and done % 100 == 0:
                pct = done / total * 100
                print(f"    {sym}  {done}/{total} ({pct:.0f}%)  ticks collected: "
                      f"{sum(len(f) for f in ticks_frames):,}", end='\r', flush=True)
            if len(df) > 0:
                ticks_frames.append(df)

    if show_progress:
        print(f"    {sym}  {done}/{total} (100%)  download complete.        ")

    if not ticks_frames:
        return pd.DataFrame()
    return pd.concat(ticks_frames).sort_index()


# ── Save helpers ────────────────────────────────────────────────────────────────

def _save(df: pd.DataFrame, path: Path):
    df.index = df.index.tz_convert('UTC').strftime('%Y-%m-%d %H:%M:%S+00:00')
    df.index.name = 'Datetime'
    df.to_csv(path)
    print(f"    Saved: {path.name}  ({len(df):,} bars)")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download forex data from Dukascopy")
    parser.add_argument('--since', default='2022', help='Start year (default: 2022)')
    parser.add_argument('--sym',   default=None,   help='Single symbol (default: all 8)')
    parser.add_argument('--tf',    default=None,   help='Timeframe: M15, H1, D, or all (default: all)')
    parser.add_argument('--workers', type=int, default=20, help='Concurrent downloads (default: 20)')
    args = parser.parse_args()

    start = datetime(int(args.since), 1, 1)
    end   = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    syms  = [args.sym.upper()] if args.sym else SYMBOLS
    tfs   = [args.tf.upper()] if args.tf else ['M15', 'H1', 'D']

    DATA_DIR.mkdir(exist_ok=True)

    print(f"\nDukascopy Downloader")
    print(f"  Pairs:    {', '.join(syms)}")
    print(f"  Period:   {start.date()} → {end.date()}")
    print(f"  Output:   {DATA_DIR}")
    print(f"  Workers:  {args.workers}")
    print(f"  Timeframes: {', '.join(tfs)}")

    total_days = (end - start).days
    est_hours  = total_days * 16 * len(syms) / args.workers / 3600
    print(f"  Est. time: ~{est_hours:.0f}–{est_hours*2:.0f} min (varies by connection)\n")

    for sym in syms:
        print(f"\n{'─'*60}")
        print(f"  Downloading {sym}  ({start.year}–{end.year})")
        print(f"{'─'*60}")

        ticks = asyncio.run(_download_symbol(sym, start, end, args.workers))

        if len(ticks) == 0:
            print(f"  WARNING: No data received for {sym}. Skipping.")
            continue

        print(f"  Total ticks: {len(ticks):,}")

        if 'M15' in tfs:
            m15 = _ticks_to_ohlcv(ticks, '15min')
            _save(m15, DATA_DIR / f"{sym}_M15.csv")

        if 'H1' in tfs:
            h1 = _ticks_to_ohlcv(ticks, '1h')
            _save(h1, DATA_DIR / f"{sym}_H1.csv")

        if 'D' in tfs:
            daily = _ticks_to_ohlcv(ticks, '1D')
            _save(daily, DATA_DIR / f"{sym}_DAILY.csv")

    print(f"\nDone. Files saved to {DATA_DIR}")
    print("Update backtest_hybrid.py _load_m15/_load_h1/_load_daily to use the new files,")
    print("or run: python backtest_hybrid.py --swing  (auto-detects full-history files)\n")


if __name__ == "__main__":
    main()
