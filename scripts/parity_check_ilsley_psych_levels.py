#!/usr/bin/env python3
"""scripts/parity_check_ilsley_psych_levels.py — Phase 12 Plan 02 (D-15 advisory).

Diffs an MQL5 buffer dump CSV against the Python compute_ilsley_psych_levels
output.

Per CONTEXT D-15: Advisory only — non-blocking.

Usage:
    python scripts/parity_check_ilsley_psych_levels.py \\
        --csv ~/.mt5/.../MQL5/Files/parity_SM_IlsleyPsychLevels_EURUSD_H1.csv \\
        --pair EURUSD --tf H1 [--tolerance-price 1e-4]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "V2"))

DATA_DIR = REPO_ROOT / "V2" / "data"
EVIDENCE_DIR = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "12-sm-indicators-implementation"
    / "evidence"
)
REPORT_PATH = EVIDENCE_DIR / "parity_ilsley_psych_levels_report.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--pair", required=True)
    p.add_argument("--tf", default="H1")
    p.add_argument("--tolerance-price", type=float, default=1e-4)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.csv.exists():
        print(f"ERROR: MQL5 parity CSV not found: {args.csv}", file=sys.stderr)
        return 2

    mq_df = pd.read_csv(args.csv, parse_dates=["ts"]).set_index("ts")

    ohlcv_path = DATA_DIR / f"{args.pair}_{args.tf}_4yr.csv"
    if not ohlcv_path.exists():
        print(f"ERROR: OHLCV fixture not found: {ohlcv_path}", file=sys.stderr)
        return 2
    py_in = pd.read_csv(ohlcv_path, parse_dates=["Datetime"]).set_index("Datetime")

    from v3_intelligence.sm_indicators.ilsley_psych_levels import (  # noqa: E402
        IlsleyPsychLevelsParams,
        compute_ilsley_psych_levels,
    )

    is_jpy = args.pair.upper().endswith("JPY")
    params = IlsleyPsychLevelsParams(is_jpy=is_jpy)
    py_out = compute_ilsley_psych_levels(py_in, params)

    common = mq_df.index.intersection(py_out.index)
    if len(common) == 0:
        print("ERROR: no overlapping timestamps", file=sys.stderr)
        return 2

    mq_aligned = mq_df.loc[common]
    py_aligned = py_out.loc[common]

    diffs = {}
    verdict_pass = True
    for col in ("psych_level_above", "psych_level_below"):
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
        "# Parity Check — SM_IlsleyPsychLevels",
        "",
        f"**Verdict:** {verdict} (tolerance: {args.tolerance_price:.0e} price)",
        f"**Pair / TF:** {args.pair} {args.tf}  ({'JPY-3digit' if is_jpy else '5-digit'})",
        f"**Bars compared:** {len(common)}",
        "",
        "| Column | Max abs diff | Tolerance | Status |",
        "|--------|-------------|-----------|--------|",
    ]
    for col, d in diffs.items():
        ok = "PASS" if d <= args.tolerance_price else "FAIL"
        lines.append(f"| {col} | {d:.6e} | {args.tolerance_price:.0e} | {ok} |")
    lines.append("")
    lines.append("_Per CONTEXT D-15: advisory only — not a blocker._")

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"VERDICT: {verdict}")
    print(f"Report: {REPORT_PATH}")
    for col, d in diffs.items():
        print(f"  {col}: max_abs_diff = {d:.6e}")
    return 0 if verdict_pass else 1


if __name__ == "__main__":
    sys.exit(main())
