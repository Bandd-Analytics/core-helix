"""Phase 8.4 Plan 03 Task 1.5 — PiT-gated 4yr eval for GBPNZD.

Wraps backtest.backtest_4yr_evaluate.run_4yr_evaluation in a PitClock context
clamped to the end of the loaded GBPNZD H1 4yr CSV. Writes a JSON report to
V2/backtest/results/gbpnzd_4yr_eval_<DATE>.json containing per-strategy
(scalp, momentum) Sharpe + trade count + allow_flag for downstream D-07
decisioning (whether to flip pair_config.py allow_* flags True).

The evaluator's existing strategies are "scalp" and "momentum"; there is no
"swing" strategy in the H1 evaluator (swing exists as a Daily strategy in
backtest_hybrid.py — separate evaluator). Plan 03 D-07 thresholds (Sharpe>=0.5
AND trades>=30) apply only to the strategies the evaluator can run, so the
JSON reports those two and pair_config.py allow_swing is left unchanged
unless the operator runs the Daily swing evaluator separately.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from backtest.backtest_4yr_evaluate import run_4yr_evaluation
from v3_intelligence.pit import PitClock


def _gbpnzd_end_ts(data_dir: Path) -> pd.Timestamp:
    df = pd.read_csv(data_dir / "GBPNZD_H1_4yr.csv", index_col=0, parse_dates=True)
    return pd.Timestamp(df.index.max())


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    data_dir = repo / "data"
    out_dir = repo / "backtest" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    end_ts = _gbpnzd_end_ts(data_dir)

    report = {
        "pair": "GBPNZD",
        "data_window_end": str(end_ts),
        "pit_active": True,
        "thresholds": {"sharpe": 0.5, "min_trades": 30},
        "strategies": {},
    }

    with PitClock(end_ts):
        for strat in ("scalp", "momentum"):
            r = run_4yr_evaluation(strategy=strat, data_dir=data_dir, pairs=["GBPNZD"])
            row = r["GBPNZD"]
            report["strategies"][strat] = {
                "sharpe": round(float(row["sharpe"]), 4),
                "win_rate": round(float(row["win_rate"]), 4),
                "trade_count": int(row["trade_count"]),
                "sharpe_threshold_met": bool(row["sharpe_threshold_met"]),
                "min_trades_met": bool(row["min_trades_met"]),
                "allow_flag": bool(row["allow_flag"]),
            }

    out_path = out_dir / f"gbpnzd_4yr_eval_{date.today():%Y-%m-%d}.json"
    with out_path.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote {out_path}")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
