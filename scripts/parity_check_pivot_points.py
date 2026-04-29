#!/usr/bin/env python3
"""scripts/parity_check_pivot_points.py — Phase 12 Plan 03 (D-15 advisory).

Diffs an MQL5 buffer dump CSV against the Python compute_pivot_points output
and writes a markdown verdict to
.planning/phases/12-sm-indicators-implementation/evidence/parity_pivot_points_report.md.

Per RESEARCH Open Question #3: same advisory tolerance approach as SM_ADR_Marker
and SM_TDI parity checks, applied to standard floor pivots + MMM M1-M4.

Usage:
    python scripts/parity_check_pivot_points.py \\
        --csv ~/.mt5/.../MQL5/Files/parity_SM_PivotPoints_EURUSD_D1.csv \\
        --pair EURUSD --tf D1 \\
        [--tolerance-price 1e-4]

The MQL5 source emits the CSV when compiled with `#define DUMP_PARITY_CSV`
at the top of SM_PivotPoints.mq5. Columns: ts, pp, r1, r2, r3, s1, s2, s3, m1, m2, m3, m4.

Per CONTEXT D-15: Advisory only — non-blocking for Plan 12-03 tier review.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def _load_mq_csv(csv_path: str) -> pd.DataFrame:
    """Load the MQL5-emitted parity CSV.

    Expected columns: ts, pp, r1, r2, r3, s1, s2, s3, m1, m2, m3, m4
    """
    df = pd.read_csv(csv_path, parse_dates=["ts"])
    df = df.set_index("ts")
    df = df.sort_index()
    return df


def _load_ohlcv(pair: str, tf: str) -> pd.DataFrame:
    """Load V2/data/{PAIR}_{TF}_4yr.csv or available variant."""
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "V2" / "data"
    # PivotPoints needs Daily bars ideally; try D1 first, fall back to H1
    candidates = [
        data_dir / f"{pair}_{tf}_4yr.csv",
        data_dir / f"{pair}_H1_4yr.csv",
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path, parse_dates=["Datetime"])
            df = df.set_index("Datetime")
            return df
    print(f"ERROR: OHLCV not found for {pair} {tf}", file=sys.stderr)
    sys.exit(1)


def run_parity_check(
    csv_path: str,
    pair: str,
    tf: str,
    tol_price: float = 1e-4,
) -> str:
    """Run parity check and return markdown report string."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "V2"))
    from v3_intelligence.sm_indicators.pivot_points import compute_pivot_points, PivotPointsParams

    mq_df = _load_mq_csv(csv_path)
    ohlcv_df = _load_ohlcv(pair, tf)

    # Align on common timestamps
    common_idx = mq_df.index.intersection(ohlcv_df.index)
    if len(common_idx) == 0:
        return "## Parity Check FAILED\n\nNo common timestamps between MQ dump and OHLCV.\n"

    py_out = compute_pivot_points(ohlcv_df.loc[common_idx], PivotPointsParams())
    mq_aligned = mq_df.loc[common_idx]

    buffer_cols = ["pp", "r1", "r2", "r3", "s1", "s2", "s3", "m1", "m2", "m3", "m4"]
    results = []
    overall_pass = True

    for col in buffer_cols:
        if col not in mq_aligned.columns or col not in py_out.columns:
            results.append(f"| {col} | MISSING | N/A | SKIP |")
            continue
        mq_vals = mq_aligned[col].dropna()
        py_vals = py_out[col].dropna()
        aligned = mq_vals.index.intersection(py_vals.index)
        if len(aligned) == 0:
            results.append(f"| {col} | NO OVERLAP | N/A | SKIP |")
            continue
        diff = (mq_vals.loc[aligned] - py_vals.loc[aligned]).abs()
        max_abs_diff = float(diff.max())
        status = "PASS" if max_abs_diff <= tol_price else "FAIL"
        if status == "FAIL":
            overall_pass = False
        results.append(f"| {col} | {max_abs_diff:.2e} | {tol_price:.0e} | {status} |")

    verdict = "PASS" if overall_pass else "FAIL"
    report_lines = [
        f"# SM_PivotPoints Parity Check — {pair} {tf}",
        "",
        f"**Verdict: {verdict}**  ",
        f"Price tolerance: {tol_price:.0e}  ",
        f"Bars compared: {len(common_idx)}",
        "",
        "| Level | Max abs diff | Price tol | Status |",
        "|-------|-------------|-----------|--------|",
    ]
    report_lines.extend(results)
    report_lines += [
        "",
        "_Per CONTEXT D-15: advisory only — non-blocking for tier review._",
        "",
    ]
    return "\n".join(report_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SM_PivotPoints MQ5↔Python parity check (D-15 advisory)"
    )
    parser.add_argument("--csv", required=True, help="Path to MQL5-emitted parity CSV")
    parser.add_argument("--pair", default="EURUSD", help="Pair name (e.g. EURUSD)")
    parser.add_argument("--tf", default="D1", help="Timeframe (e.g. D1)")
    parser.add_argument("--tolerance-price", type=float, default=1e-4, dest="tol_price")
    args = parser.parse_args()

    report = run_parity_check(args.csv, args.pair, args.tf, args.tol_price)

    # Write report
    repo_root = Path(__file__).resolve().parents[1]
    evidence_dir = repo_root / ".planning" / "phases" / "12-sm-indicators-implementation" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out_path = evidence_dir / "parity_pivot_points_report.md"
    out_path.write_text(report)
    print(report)
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
