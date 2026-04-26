"""V2/scripts/fetch_4yr_dukascopy.py — Phase 8.4 Plan 03 Path D failover (Dukascopy historical).

Standalone fetch script invoked by the orchestrator when MT5 GUI (Path A) and Wine
Python (Path B) are unavailable. Pulls 4 years of OHLC from Dukascopy historical via
the duka package, normalizes to Title-case OHLCV format, and writes V2/data/ CSVs
matching the Phase 7 D-15 schema.

Targets (per Plan 03 must_haves):
  - GBPNZD H1 4yr → V2/data/GBPNZD_H1_4yr.csv (≥15000 rows)
  - {USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP, GBPNZD, EURUSD, AUDNZD} H4 4yr (≥4000 rows each)

Reliability:
  - duka 0.2.0 has been monkey-patched to use datafeed.dukascopy.com (see repo follow-up).
  - duka drops hours on transient network errors; this script merges any pre-existing
    output CSV with a fresh fetch on each run, so re-running closes gaps.
  - Each (pair, tf) is fetched into a temp dir, then merged into the canonical V2/data/
    file on success.

Usage:
  python -m scripts.fetch_4yr_dukascopy           # run all 9 datasets sequentially
  python -m scripts.fetch_4yr_dukascopy --gbpnzd  # GBPNZD H1 only
  python -m scripts.fetch_4yr_dukascopy --h4      # 8 H4 datasets only
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fetch_4yr")

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "data"

EIGHT_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]

END_DATE = date(2026, 4, 26)
START_DATE = date(2022, 4, 26)


def _run_duka(pair: str, tf: str, out_dir: Path, start: date, end: date) -> Path | None:
    from duka.core.utils import TimeFrame
    from duka.app.app import app as duka_run
    tf_const = getattr(TimeFrame, tf.upper())
    out_dir.mkdir(parents=True, exist_ok=True)
    duka_run(
        symbols=[pair],
        start=start,
        end=end,
        threads=20,
        timeframe=tf_const,
        folder=str(out_dir),
        header=True,
    )
    candidates = list(out_dir.glob(f"{pair}-*.csv"))
    if not candidates:
        log.error(f"{pair} {tf}: no output csv found")
        return None
    return candidates[0]


def _normalize_duka_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    if "time" not in df.columns:
        return pd.DataFrame()
    df["Datetime"] = pd.to_datetime(df["time"])
    rename_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
    df = df.rename(columns=rename_map)
    keep = [c for c in ("Open", "High", "Low", "Close") if c in df.columns]
    if not keep:
        return pd.DataFrame()
    out = df.set_index("Datetime")[keep].sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out["Volume"] = 0
    return out[["Open", "High", "Low", "Close", "Volume"]]


def _merge_with_existing(target: Path, fresh: pd.DataFrame) -> pd.DataFrame:
    if target.exists():
        try:
            existing = pd.read_csv(target, parse_dates=[0], index_col=0)
            existing.index.name = "Datetime"
            keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in existing.columns]
            existing = existing[keep]
            merged = pd.concat([existing, fresh])
            merged = merged[~merged.index.duplicated(keep="first")].sort_index()
            return merged
        except Exception as e:
            log.warning(f"failed to merge with existing {target}: {e}")
    return fresh


def fetch_one(pair: str, tf: str) -> bool:
    target = DATA_DIR / f"{pair}_{tf}_4yr.csv"
    log.warning(f"=== fetching {pair} {tf} 4yr ({START_DATE} → {END_DATE}) ===")
    with tempfile.TemporaryDirectory(prefix="duka_") as tmp:
        tmp_path = Path(tmp)
        try:
            csv_path = _run_duka(pair, tf, tmp_path, START_DATE, END_DATE)
        except Exception as e:
            log.error(f"{pair} {tf}: duka fetch raised {type(e).__name__}: {e}")
            return False
        if csv_path is None:
            return False
        fresh = _normalize_duka_csv(csv_path)
        if fresh.empty:
            log.error(f"{pair} {tf}: normalized DF empty — skipping write")
            return False
        merged = _merge_with_existing(target, fresh)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        merged.to_csv(target)
        rows = len(merged)
        date_min = merged.index.min()
        date_max = merged.index.max()
        log.warning(f"{pair} {tf}: wrote {rows} rows  ({date_min} → {date_max})  → {target}")
        return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gbpnzd", action="store_true", help="GBPNZD H1 only")
    ap.add_argument("--h4", action="store_true", help="8-pair H4 only")
    args = ap.parse_args()

    only_gbpnzd = args.gbpnzd
    only_h4 = args.h4

    targets: list[tuple[str, str]] = []
    if only_gbpnzd:
        targets = [("GBPNZD", "H1")]
    elif only_h4:
        targets = [(p, "H4") for p in EIGHT_PAIRS]
    else:
        targets = [("GBPNZD", "H1")] + [(p, "H4") for p in EIGHT_PAIRS]

    n_ok = 0
    n_fail = 0
    for pair, tf in targets:
        if fetch_one(pair, tf):
            n_ok += 1
        else:
            n_fail += 1
    log.warning(f"=== done: {n_ok} ok / {n_fail} fail ===")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
