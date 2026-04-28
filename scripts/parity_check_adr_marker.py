#!/usr/bin/env python3
"""scripts/parity_check_adr_marker.py — Phase 12 Plan 02 (D-15 advisory).

Diffs an MQL5 buffer dump CSV against the Python compute_adr_marker output
and writes a markdown verdict to
.planning/phases/12-sm-indicators-implementation/evidence/parity_adr_marker_report.md.

Per RESEARCH Open Question #3, this is the validation point for the 1e-4
price tolerance achievable across the MQ5↔Python boundary BEFORE Plan 12-03
commits to the same approach for SM_TDI / SM_PivotPoints.

Usage:
    python scripts/parity_check_adr_marker.py \\
        --csv ~/.mt5/.../MQL5/Files/parity_SM_ADR_Marker_EURUSD_H1.csv \\
        --pair EURUSD --tf H1 \\
        [--tolerance-price 1e-4] [--tolerance-ratio 1e-6]

The MQL5 source emits the CSV when compiled with `#define DUMP_PARITY_CSV`
at the top of SM_ADR_Marker.mq5. Columns: ts, adr, marker_high, marker_low.

Per CONTEXT D-15: Advisory only — non-blocking for Plan 12-02 tier review.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Resolve repo root so the script can be run from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "V2"))

# These imports are deferred until argument parsing succeeds so --help works
# even if the V2 package isn't installed.
DATA_DIR = REPO_ROOT / "V2" / "data"
EVIDENCE_DIR = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "12-sm-indicators-implementation"
    / "evidence"
)
REPORT_PATH = EVIDENCE_DIR / "parity_adr_marker_report.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--csv",
        required=True,
        type=Path,
        help="Path to MQL5/Files/parity_SM_ADR_Marker_*.csv",
    )
    p.add_argument(
        "--pair",
        required=True,
        help="Currency pair (EURUSD, USDJPY, ...) — used to load V2/data CSV",
    )
    p.add_argument("--tf", default="H1", help="Timeframe (default H1)")
    p.add_argument(
        "--tolerance-price",
        type=float,
        default=1e-4,
        help="Max-abs-diff tolerance for price columns (default 1e-4)",
    )
    p.add_argument(
        "--tolerance-ratio",
        type=float,
        default=1e-6,
        help="Max-abs-diff tolerance for ratio columns (default 1e-6)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not args.csv.exists():
        print(f"ERROR: MQL5 parity CSV not found: {args.csv}", file=sys.stderr)
        return 2

    # Read MQL5-emitted CSV
    mq_df = pd.read_csv(args.csv, parse_dates=["ts"])
    mq_df = mq_df.set_index("ts")

    # Load matching OHLCV
    ohlcv_path = DATA_DIR / f"{args.pair}_{args.tf}_4yr.csv"
    if not ohlcv_path.exists():
        print(f"ERROR: OHLCV fixture not found: {ohlcv_path}", file=sys.stderr)
        return 2
    py_in = pd.read_csv(ohlcv_path, parse_dates=["Datetime"]).set_index("Datetime")

    # Late import — V2 sys.path injected above
    from v3_intelligence.sm_indicators.adr_marker import (  # noqa: E402
        ADRMarkerParams,
        compute_adr_marker,
    )

    py_out = compute_adr_marker(py_in, ADRMarkerParams())

    # Inner-join on timestamps both sides have
    common = mq_df.index.intersection(py_out.index)
    if len(common) == 0:
        print(
            "ERROR: no overlapping timestamps between MQL5 dump and Python "
            "OHLCV — verify --pair / --tf and dump-bar window",
            file=sys.stderr,
        )
        return 2

    mq_aligned = mq_df.loc[common]
    py_aligned = py_out.loc[common]

    # Price-tolerance columns
    cols_price = ["adr", "marker_high", "marker_low"]
    diffs = {}
    verdict_pass = True
    for col in cols_price:
        if col not in mq_aligned.columns or col not in py_aligned.columns:
            continue
        d = (mq_aligned[col] - py_aligned[col]).abs().dropna()
        max_abs = float(d.max()) if len(d) else 0.0
        diffs[col] = max_abs
        if max_abs > args.tolerance_price:
            verdict_pass = False

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    verdict = "PASS" if verdict_pass else "FAIL"
    lines = [
        "# Parity Check — SM_ADR_Marker",
        "",
        f"**Verdict:** {verdict} (tolerance: {args.tolerance_price:.0e} price)",
        f"**Pair / TF:** {args.pair} {args.tf}",
        f"**MQL5 CSV:** `{args.csv}`",
        f"**Bars compared:** {len(common)}",
        "",
        "| Column | Max abs diff | Tolerance | Status |",
        "|--------|-------------|-----------|--------|",
    ]
    for col, d in diffs.items():
        ok = "PASS" if d <= args.tolerance_price else "FAIL"
        lines.append(f"| {col} | {d:.6e} | {args.tolerance_price:.0e} | {ok} |")
    lines.append("")
    lines.append(
        "_Per CONTEXT D-15: advisory only — not a blocker for tier review._"
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"VERDICT: {verdict}")
    print(f"Report: {REPORT_PATH}")
    for col, d in diffs.items():
        print(f"  {col}: max_abs_diff = {d:.6e}")
    return 0 if verdict_pass else 1


if __name__ == "__main__":
    sys.exit(main())
