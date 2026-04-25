"""Offline HMM-GARCH detector fitting for the 5 Phase 8 active pairs (D-10).

Usage:
    python -m scripts.fit_regime_detectors --pair USDJPY
    python -m scripts.fit_regime_detectors --pair all
    python -m scripts.fit_regime_detectors --pair all --force
    python -m scripts.fit_regime_detectors --pair USDJPY --data-window 4yr

Idempotent: skips pairs whose JSON exists unless --force is set (mirrors
download_history.py CLI pattern from Phase 7 — D-13).

Per D-26: exits non-zero if any pair fails to fit (stationarity or HMM
non-convergence, missing CSV, etc.). No JSON written for failed pairs.

Output JSON schema (D-11): see V2/v3_intelligence/regime/persistence.py
SCHEMA_VERSION=1. Each pair's JSON includes garch_params (3 entries),
transmat (3x3), startprob (3,), variance_ordering with monotonically
increasing unconditional_variances (REGM-02 visible), and fit_metadata
with ISO-8601 UTC timestamp + data provenance.

Phase 9 ROUT-04 router consumes the produced JSONs via
v3_intelligence.regime.load_detector(...) — see Phase 8 D-27.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from v3_intelligence.regime import (
    HMMGARCHRegimeDetector,
    bars_to_log_returns,
    save_detector,
)

ACTIVE_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP"]   # D-10
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REGIME_DIR = DATA_DIR / "regime"


def _fit_one(pair: str, data_window: str, force: bool) -> bool:
    """Fit a single pair. Returns True on success/skip, False on failure."""
    out = REGIME_DIR / f"{pair}_detector.json"
    if out.exists() and not force:
        print(f"  SKIP {pair} — {out.name} exists (idempotent)")
        return True

    csv = DATA_DIR / f"{pair}_H1_{data_window}.csv"
    if not csv.exists():
        print(f"  FAIL {pair} — {csv} not found", file=sys.stderr)
        return False

    df = pd.read_csv(csv, index_col=0, parse_dates=True)
    returns = bars_to_log_returns(df)

    detector = HMMGARCHRegimeDetector(random_state=0)
    if not detector.fit(returns):
        print(
            f"  FAIL {pair} — fit() returned False (stationarity or convergence)",
            file=sys.stderr,
        )
        return False

    REGIME_DIR.mkdir(parents=True, exist_ok=True)
    save_detector(
        detector,
        out,
        pair=pair,
        data_path=str(csv),
        data_window=data_window,
        n_bars=len(df),
        hmmlearn_converged=True,
        v1_parity_tested=False,
    )
    variances = [f"{p.unconditional_variance:.2e}" for p in detector.garch_params]
    print(f"  OK   {pair} — variances={variances} → {out.name}")
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, choices=ACTIVE_PAIRS + ["all"])
    parser.add_argument("--data-window", default="4yr")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    targets = ACTIVE_PAIRS if args.pair == "all" else [args.pair]
    failed = [p for p in targets if not _fit_one(p, args.data_window, args.force)]
    if failed:
        print(f"FAILED pairs: {failed}", file=sys.stderr)
        return 1
    print(f"All {len(targets)} pair(s) fitted successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
