#!/usr/bin/env python3
"""scripts/parity_check_tdi.py — Phase 12 Plan 03 (D-15 advisory).

Diffs an MQL5 buffer dump CSV against the Python compute_tdi output and
writes a markdown verdict to
.planning/phases/12-sm-indicators-implementation/evidence/parity_tdi_report.md.

Per RESEARCH Open Question #3 (validated by Plan 12-02 SM_ADR_Marker parity
approach): same advisory tolerance approach applied to SM_TDI 6 buffers.

Usage:
    python scripts/parity_check_tdi.py \\
        --csv ~/.mt5/.../MQL5/Files/parity_SM_TDI_EURUSD_H1.csv \\
        --pair EURUSD --tf H1 \\
        [--tolerance-price 1e-4] [--tolerance-ratio 1e-6]

The MQL5 source emits the CSV when compiled with `#define DUMP_PARITY_CSV`
at the top of SM_TDI.mq5. Columns: ts, rsi_pl, tsl, mbl, vb_upper, vb_lower.

Per CONTEXT D-15: Advisory only — non-blocking for Plan 12-03 tier review.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def _load_mq_csv(csv_path: str) -> pd.DataFrame:
    """Load the MQL5-emitted parity CSV.

    Expected columns: ts, rsi_pl, tsl, mbl, vb_upper, vb_lower
    """
    df = pd.read_csv(csv_path, parse_dates=["ts"])
    df = df.set_index("ts")
    df = df.sort_index()
    return df


def _load_ohlcv(pair: str, tf: str) -> pd.DataFrame:
    """Load V2/data/{PAIR}_{TF}_4yr.csv (Phase 8.4 INFRA-02 format)."""
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "V2" / "data"
    path = data_dir / f"{pair}_{tf}_4yr.csv"
    if not path.exists():
        print(f"ERROR: OHLCV not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path, parse_dates=["Datetime"])
    df = df.set_index("Datetime")
    return df


def run_parity_check(
    csv_path: str,
    pair: str,
    tf: str,
    tol_price: float = 1e-4,
    tol_ratio: float = 1e-6,
) -> str:
    """Run parity check and return markdown report string."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "V2"))
    from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams

    mq_df = _load_mq_csv(csv_path)
    ohlcv_df = _load_ohlcv(pair, tf)

    # Align on common timestamps
    common_idx = mq_df.index.intersection(ohlcv_df.index)
    if len(common_idx) == 0:
        return "## Parity Check FAILED\n\nNo common timestamps between MQ dump and OHLCV.\n"

    py_out = compute_tdi(ohlcv_df.loc[common_idx], TDIParams())
    mq_aligned = mq_df.loc[common_idx]

    buffer_cols = ["rsi_pl", "tsl", "mbl", "vb_upper", "vb_lower"]
    results = []
    overall_pass = True

    for col in buffer_cols:
        if col not in mq_aligned.columns or col not in py_out.columns:
            results.append(f"| {col} | MISSING | N/A | N/A | SKIP |")
            continue
        mq_vals = mq_aligned[col].dropna()
        py_vals = py_out[col].dropna()
        aligned = mq_vals.index.intersection(py_vals.index)
        if len(aligned) == 0:
            results.append(f"| {col} | NO OVERLAP | N/A | N/A | SKIP |")
            continue
        diff = (mq_vals.loc[aligned] - py_vals.loc[aligned]).abs()
        max_abs_diff = float(diff.max())
        # Ratio diff (relative to MQ values, avoiding zero)
        denom = mq_vals.loc[aligned].abs().replace(0, 1e-10)
        max_ratio_diff = float((diff / denom).max())
        price_pass = max_abs_diff <= tol_price
        ratio_pass = max_ratio_diff <= tol_ratio
        status = "PASS" if (price_pass or ratio_pass) else "FAIL"
        if status == "FAIL":
            overall_pass = False
        results.append(
            f"| {col} | {max_abs_diff:.2e} | {tol_price:.0e} | "
            f"{max_ratio_diff:.2e} | {status} |"
        )

    verdict = "PASS" if overall_pass else "FAIL"
    report_lines = [
        f"# SM_TDI Parity Check — {pair} {tf}",
        "",
        f"**Verdict: {verdict}**  ",
        f"Tolerances: price={tol_price:.0e}, ratio={tol_ratio:.0e}  ",
        f"Bars compared: {len(common_idx)}",
        "",
        "| Buffer | Max abs diff | Price tol | Max ratio diff | Status |",
        "|--------|-------------|-----------|----------------|--------|",
    ]
    report_lines.extend(results)
    report_lines += [
        "",
        "_Per CONTEXT D-15: advisory only — non-blocking for tier review._",
        "",
    ]
    return "\n".join(report_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="SM_TDI MQ5↔Python parity check (D-15 advisory)")
    parser.add_argument("--csv", required=True, help="Path to MQL5-emitted parity CSV")
    parser.add_argument("--pair", default="EURUSD", help="Pair name (e.g. EURUSD)")
    parser.add_argument("--tf", default="H1", help="Timeframe (e.g. H1)")
    parser.add_argument("--tolerance-price", type=float, default=1e-4, dest="tol_price")
    parser.add_argument("--tolerance-ratio", type=float, default=1e-6, dest="tol_ratio")
    args = parser.parse_args()

    report = run_parity_check(args.csv, args.pair, args.tf, args.tol_price, args.tol_ratio)

    # Write report
    repo_root = Path(__file__).resolve().parents[1]
    evidence_dir = repo_root / ".planning" / "phases" / "12-sm-indicators-implementation" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out_path = evidence_dir / "parity_tdi_report.md"
    out_path.write_text(report)
    print(report)
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
