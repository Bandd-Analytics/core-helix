"""MT5 H1 historical download script (BKTS-02/03 D-13/D-14/D-15/D-16).

Usage:
    python scripts/download_history.py           # full-history (legacy, 2015-2026)
    python scripts/download_history.py --4yr     # idempotent 4yr fetch for Phase 7

The 4yr mode writes {PAIR}_H1_4yr.csv into V2/data/, skipping pairs whose
file already exists. Output format per 07-UI-SPEC.md §download_history.py.

# DATA ACQUISITION FAILOVER (MetaTrader5 Python package is Windows COM only)
#
# The MetaTrader5 pip package cannot install on Linux. If `_fetch_4yr()` fails
# with "no matching distribution" or an import error, follow this chain:
#
# A — MT5 GUI History Export (fastest, ~5 min per pair)
#     MT5 terminal is already running (coke5151 fork, IC Markets Raw, under Wine).
#     1. Press F2 in MT5 (Tools → History Center)
#     2. Select pair → H1 → click Download (ensures full broker history is loaded)
#     3. Click Export → save as V2/data/{PAIR}_H1_4yr.csv
#     4. Repeat for: AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY
#     Column map: MT5 exports <Date>,<Time>,<Open>,<High>,<Low>,<Close>,<Volume>
#     Rename to: Datetime,Open,High,Low,Close,Volume  (Title-case OHLC required)
#     This script's idempotency (SKIP if file exists) still applies on re-runs.
#
# B — Wine Python execution (~15 min if Wine Python is present)
#     MetaTrader5 package works inside Wine's Windows Python environment.
#     find ~/.wine -name "python*.exe" 2>/dev/null   # locate Wine Python
#     wine <path>/python.exe -m pip install MetaTrader5 pandas
#     wine <path>/python.exe scripts/download_history.py --4yr
#     The script runs inside Wine where MT5 COM interface is reachable.
#
# D — Dukascopy tick data (broker-neutral, no account needed, works on Linux)
#     pip install duka
#     duka -s AUDNZD EURGBP GBPJPY EURUSD USDJPY -d 2022-04-01 -e 2026-04-25 \\
#          -t TICK -c 1  # then aggregate ticks → H1 OHLCV
#     Dukascopy publishes free FX tick data back to 2003.
#     Aggregate with pandas: df.resample('1H').agg({'Ask':'ohlc',...})
#     Rename columns to Title-case (Open, High, Low, Close) before saving.
#
# After any manual export: re-run backtest_4yr_evaluate.py to regenerate
# the routing matrix, then re-run the PiT gate before updating pair_config.py.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ACTIVE_PAIRS_4YR = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]
LEGACY_SYMBOLS = ["EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"]
LOW_BAR_WARN = 20_000
MIN_BAR_OK = 15_000


def _fetch_4yr() -> int:
    """Idempotent 4yr H1 fetch. Returns exit code."""
    if not mt5.initialize():
        err = mt5.last_error()
        print(
            f"ERROR: MT5 init failed — {err}. Ensure MT5 terminal is running.",
            file=sys.stderr,
        )
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    end = datetime.now()
    start = end - timedelta(days=4 * 365 + 2)  # +2 leap buffer

    succeeded = 0
    total = len(ACTIVE_PAIRS_4YR)
    for sym in ACTIVE_PAIRS_4YR:
        out = DATA_DIR / f"{sym}_H1_4yr.csv"
        if out.exists():
            print(f"  SKIP {sym} — {out.name} already exists (idempotent)")
            succeeded += 1
            continue

        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_H1, start, end)
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            print(f"  FAIL {sym} — {err}", file=sys.stderr)
            continue

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")
        # Capitalise OHLC columns to match project convention (pair_config.py / backtests)
        col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
        df = df.rename(columns=col_map)
        df.to_csv(out)

        n = len(df)
        if n < LOW_BAR_WARN:
            print(
                f"  WARN {sym} — only {n} bars returned (expected >= 20,000). "
                f"Check broker history."
            )
        else:
            print(f"  OK   {sym} — {n} bars → {out.name}")
        succeeded += 1

    mt5.shutdown()

    if succeeded == 0:
        print(
            "No pairs fetched. Verify MT5 terminal is running and IC Markets is connected.",
            file=sys.stderr,
        )
    else:
        print(f"Download complete: {succeeded}/{total} pairs succeeded.")
    return 0


def _fetch_legacy() -> int:
    """Original full-history download behavior (unchanged external contract)."""
    if not mt5.initialize():
        print("MT5 init failed", file=sys.stderr)
        return 1

    start_date = datetime(2015, 1, 1)
    end_date = datetime(2026, 4, 20)

    for symbol in LEGACY_SYMBOLS:
        print(f"\nDownloading {symbol}...")
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_date, end_date)
        if rates is None or len(rates) == 0:
            print(f"  Failed: {mt5.last_error()}")
            continue
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        filename = f"{symbol}_H1_2015-2026.csv"
        df.to_csv(filename, index=False)
        print(f"  Saved {len(df)} bars → {filename}")

    mt5.shutdown()
    print("\nDone!")
    return 0


def main(argv: list[str]) -> int:
    if "--4yr" in argv:
        return _fetch_4yr()
    return _fetch_legacy()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
