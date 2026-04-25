"""MT5 H1 historical download script (BKTS-02/03 D-13/D-14/D-15/D-16).

Usage:
    python scripts/download_history.py                              # full-history (legacy, 2015-2026)
    python scripts/download_history.py --4yr                        # idempotent 4yr fetch for Phase 7
    python scripts/download_history.py --4yr-pairs GBPAUD GBPUSD    # arbitrary pair subset (Phase 8 D-10)

The 4yr modes write {PAIR}_H1_4yr.csv into V2/data/, skipping pairs whose
file already exists. Output format per 07-UI-SPEC.md §download_history.py.

The --4yr-pairs flag (added in Phase 8 Plan 04) accepts an arbitrary list
of pair codes and is used to fetch the Phase 8 active set (D-10:
USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP) — distinct from Phase 7's --4yr set.

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

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# MetaTrader5 is Windows COM only; on Linux we fall back to the 730d-CSV
# copy path (Phase 7 D-15 / Phase 8 Plan 04 documented workaround). Import
# guarded so module load succeeds on Linux for Phase 8's --4yr-pairs path.
try:
    import MetaTrader5 as mt5  # type: ignore[import-not-found]
    _MT5_AVAILABLE = True
except ModuleNotFoundError:
    mt5 = None  # type: ignore[assignment]
    _MT5_AVAILABLE = False

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


def _fetch_4yr_pairs(pairs: list[str]) -> int:
    """Idempotent 4yr H1 fetch for an arbitrary subset of pairs (Phase 8 D-10).

    Used by Phase 8 to fetch GBPAUD + GBPUSD (CONTEXT.md D-10) — pairs not in
    Phase 7's ACTIVE_PAIRS_4YR set. Reuses the same fetch loop as _fetch_4yr().

    Linux-failover path (per Phase 7 D-15 / Phase 8 Plan 04 documented
    workaround): if the MetaTrader5 Python package is unavailable
    (Linux/Wine env), fall back to copying the matching {PAIR}_H1_730d.csv
    that already exists from previous Phase-6/7 work. This is the same
    pattern Phase 7 used for the other 5 pairs — the existing "_4yr" CSVs
    are 730-day-shape (~17k bars). The CLI prints WARN lines so the
    operator knows the data is placeholder-grade, and the fitted detector
    JSONs from fit_regime_detectors.py should be re-fit on Windows when
    full MT5 access is available.
    """
    if not _MT5_AVAILABLE:
        return _fetch_4yr_pairs_linux_failover(pairs)

    if not mt5.initialize():
        err = mt5.last_error()
        print(
            f"ERROR: MT5 init failed — {err}. Ensure MT5 terminal is running.",
            file=sys.stderr,
        )
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    end = datetime.now()
    start = end - timedelta(days=4 * 365 + 2)

    succeeded = 0
    total = len(pairs)
    for sym in pairs:
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


def _fetch_4yr_pairs_linux_failover(pairs: list[str]) -> int:
    """Linux-failover for --4yr-pairs when MetaTrader5 package is unavailable.

    Mirrors what Phase 7 did for the existing 5 _4yr CSVs: copy the matching
    {PAIR}_H1_730d.csv (already produced earlier in v2.0) to the {PAIR}_H1_4yr.csv
    path. The 730d shape (~17k bars covering ~3 years of H1 trading data) is
    sufficient for HMM-GARCH fitting with min_state_samples=100 — Phase 8 D-24
    accepts this as a stable-fit input pending MT5/Windows re-export.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    succeeded = 0
    total = len(pairs)
    print(
        "  NOTE MetaTrader5 package unavailable on this OS — using Phase 7 "
        "Linux-failover (copy from {PAIR}_H1_730d.csv).",
        file=sys.stderr,
    )
    for sym in pairs:
        out = DATA_DIR / f"{sym}_H1_4yr.csv"
        if out.exists():
            print(f"  SKIP {sym} — {out.name} already exists (idempotent)")
            succeeded += 1
            continue

        src = DATA_DIR / f"{sym}_H1_730d.csv"
        if not src.exists():
            print(
                f"  FAIL {sym} — Linux-failover source {src.name} not found; "
                f"cannot create {out.name}.",
                file=sys.stderr,
            )
            continue

        shutil.copyfile(src, out)
        try:
            n = sum(1 for _ in out.open()) - 1  # subtract header
        except OSError:
            n = -1
        if 0 < n < LOW_BAR_WARN:
            print(
                f"  WARN {sym} — {n} bars copied from {src.name} (Phase 7 "
                f"Linux-failover; placeholder for 4yr data — re-fit on Windows "
                f"when MT5 access is available)."
            )
        else:
            print(f"  OK   {sym} — {n} bars copied from {src.name} → {out.name}")
        succeeded += 1

    if succeeded == 0:
        print(
            "No pairs fetched. No matching _H1_730d.csv sources available.",
            file=sys.stderr,
        )
        return 1
    print(f"Download complete (Linux-failover): {succeeded}/{total} pairs succeeded.")
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
    if "--4yr-pairs" in argv:
        idx = argv.index("--4yr-pairs")
        pairs = argv[idx + 1:]
        if not pairs:
            print(
                "ERROR: --4yr-pairs requires at least one pair code",
                file=sys.stderr,
            )
            return 1
        return _fetch_4yr_pairs(pairs)
    if "--4yr" in argv:
        return _fetch_4yr()
    return _fetch_legacy()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
