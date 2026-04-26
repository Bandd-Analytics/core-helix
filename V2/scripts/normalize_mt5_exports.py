"""V2/scripts/normalize_mt5_exports.py — Phase 8.4 Plan 03 Path A normalizer.

Folds MT5 Symbols-dialog export CSVs into canonical V2/data/{PAIR}_{TF}_4yr.csv.

MT5 export format (tab-separated, 9 columns):
  <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>

Canonical V2/data/ format (per Phase 7 D-15 contract):
  Datetime,Open,High,Low,Close,Volume

Volume source: TICKVOL (forex VOL is always 0; tick count is the standard proxy).

Usage:
  python -m scripts.normalize_mt5_exports --src ~/Desktop --dest V2/data/
  python -m scripts.normalize_mt5_exports --src ~/Desktop --dest V2/data/ --plan-03-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

EIGHT_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]
ALL_TFS = ["M15", "H1", "H4"]

PLAN_03_TARGETS: list[tuple[str, str]] = (
    [("GBPNZD", "H1")] + [(p, "H4") for p in EIGHT_PAIRS]
)

# MT5 export filename pattern: {PAIR}_{TF}_<startts>_<endts>[_export].csv
EXPORT_RE = re.compile(
    r"^(?P<pair>[A-Z]{6})_(?P<tf>M15|H1|H4)_(?P<start>\d{12})_(?P<end>\d{12})(_export)?\.csv$"
)


def find_exports(src_dir: Path) -> dict[tuple[str, str], Path]:
    out: dict[tuple[str, str], Path] = {}
    for p in src_dir.iterdir():
        if not p.is_file() or not p.name.endswith(".csv"):
            continue
        m = EXPORT_RE.match(p.name)
        if not m:
            continue
        pair = m.group("pair")
        tf = m.group("tf")
        if pair not in EIGHT_PAIRS or tf not in ALL_TFS:
            continue
        existing = out.get((pair, tf))
        if existing is None or p.stat().st_size > existing.stat().st_size:
            out[(pair, tf)] = p
    return out


def normalize(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src, sep="\t")
    df.columns = [c.strip("<>").lower() for c in df.columns]
    if not {"date", "time", "open", "high", "low", "close"}.issubset(df.columns):
        raise ValueError(f"{src.name}: unexpected columns {list(df.columns)}")
    dt_str = df["date"].astype(str) + " " + df["time"].astype(str)
    df["Datetime"] = pd.to_datetime(dt_str, format="%Y.%m.%d %H:%M:%S")
    out = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
    out["Volume"] = df["tickvol"] if "tickvol" in df.columns else 0
    out = out.set_index("Datetime")[["Open", "High", "Low", "Close", "Volume"]]
    out = out[~out.index.duplicated(keep="first")].sort_index()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Source dir (e.g. ~/Desktop)")
    ap.add_argument("--dest", required=True, help="Destination dir (V2/data/)")
    ap.add_argument("--plan-03-only", action="store_true",
                    help="Only normalize the 9 Plan 03 targets (GBPNZD H1 + 8 H4)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src_dir = Path(args.src).expanduser().resolve()
    dest_dir = Path(args.dest).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    found = find_exports(src_dir)
    if not found:
        print(f"No matching exports in {src_dir}", file=sys.stderr)
        return 1

    targets: list[tuple[str, str]]
    if args.plan_03_only:
        targets = PLAN_03_TARGETS
    else:
        targets = sorted(found.keys())

    n_ok = 0
    n_missing = 0
    n_short_h4 = 0
    print(f"{'Pair':<8} {'TF':<4} {'Rows':>8}  {'Date Range':<46}  Status")
    print("-" * 90)
    for pair, tf in targets:
        src = found.get((pair, tf))
        if src is None:
            print(f"{pair:<8} {tf:<4} {'-':>8}  {'(no export found)':<46}  MISSING")
            n_missing += 1
            continue
        df = normalize(src)
        rows = len(df)
        date_min = df.index.min()
        date_max = df.index.max()
        threshold_warn = ""
        if tf == "H1" and rows < 15000:
            threshold_warn = "  H1<15k!"
            n_short_h4 += 1
        elif tf == "H4" and rows < 4000:
            threshold_warn = "  H4<4k!"
            n_short_h4 += 1
        date_range = f"{date_min:%Y-%m-%d} → {date_max:%Y-%m-%d}"
        print(f"{pair:<8} {tf:<4} {rows:>8}  {date_range:<46}  OK{threshold_warn}")
        if not args.dry_run:
            target = dest_dir / f"{pair}_{tf}_4yr.csv"
            df.to_csv(target)
        n_ok += 1
    print("-" * 90)
    print(f"Done: {n_ok} normalized, {n_missing} missing, {n_short_h4} below threshold")
    return 0 if n_missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
