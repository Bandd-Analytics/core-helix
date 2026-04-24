"""Before/After entry-bias comparison report (BKTS-01, D-02).

Runs the FIXED backtest on existing 730d H1 CSVs for all 5 active pairs
x 3 strategies (swing, scalp, momentum) and writes a CSV comparing the
new Sharpe against the biased baseline values recorded in pair_config.py.

Usage:
    cd V2 && python -m backtest.reports.compare_entry_bias
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

# ── path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]   # V2/
sys.path.insert(0, str(ROOT))

from backtest.backtest_evaluate_all import Evaluator, metrics
from v3_intelligence.pair_config import PairConfig

# Biased baseline Sharpe / win-rate / trade-count per (pair, strategy).
# Sourced from V2/v3_intelligence/pair_config.py module docstring and per-pair notes.
# These are the 730d biased values that the entry fix will correct downward.
BIASED_BASELINE: dict[tuple[str, str], dict[str, float]] = {
    ("AUDNZD", "scalp"):    {"sharpe": 1.63, "win_pct": 0.0, "trades": 0},
    ("AUDNZD", "momentum"): {"sharpe": 0.55, "win_pct": 0.0, "trades": 0},
    ("AUDNZD", "swing"):    {"sharpe": -2.16, "win_pct": 0.0, "trades": 0},
    ("EURGBP", "scalp"):    {"sharpe": 1.32, "win_pct": 0.0, "trades": 0},
    ("EURGBP", "momentum"): {"sharpe": 1.57, "win_pct": 0.0, "trades": 0},
    ("EURGBP", "swing"):    {"sharpe": 0.45, "win_pct": 0.0, "trades": 0},
    ("GBPJPY", "scalp"):    {"sharpe": 0.85, "win_pct": 0.0, "trades": 0},
    ("GBPJPY", "momentum"): {"sharpe": 0.21, "win_pct": 0.0, "trades": 0},
    ("GBPJPY", "swing"):    {"sharpe": 1.93, "win_pct": 0.0, "trades": 0},
    ("EURUSD", "scalp"):    {"sharpe": -0.17, "win_pct": 0.0, "trades": 0},
    ("EURUSD", "momentum"): {"sharpe": -1.03, "win_pct": 0.0, "trades": 0},
    ("EURUSD", "swing"):    {"sharpe": -0.20, "win_pct": 0.0, "trades": 0},
    ("USDJPY", "scalp"):    {"sharpe": -2.34, "win_pct": 0.0, "trades": 0},
    ("USDJPY", "momentum"): {"sharpe": -1.61, "win_pct": 0.0, "trades": 0},
    ("USDJPY", "swing"):    {"sharpe": 3.09,  "win_pct": 0.0, "trades": 0},
}

ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]
DATA_DIR = ROOT / "data"
OUT_PATH = Path(__file__).resolve().parent / "entry_bias_comparison.csv"

# ── Evaluation configs (injected, not from pair_config.py) ────────────────────
# Mirrors the _eval_cfg_* pattern in backtest_evaluate_all.py


def _eval_cfg_swing(sym: str) -> PairConfig:
    return PairConfig(
        symbol=sym, tier=2,
        swing_size_mult=1.0,
        swing_z_threshold=2.0,
        swing_target_atr=4.0, swing_stop_atr=1.5,
        swing_max_bars=120,
        allow_swing=True, allow_scalp=False, allow_momentum=False, allow_m15_scalp=False,
    )


def _eval_cfg_scalp(sym: str) -> PairConfig:
    return PairConfig(
        symbol=sym, tier=2,
        scalp_size_mult=0.5,
        scalp_z_threshold=2.0,
        scalp_target_atr=2.0, scalp_stop_atr=0.75,
        scalp_max_bars=4,
        allow_swing=False, allow_scalp=True, allow_momentum=False, allow_m15_scalp=False,
    )


def _eval_cfg_momentum(sym: str) -> PairConfig:
    return PairConfig(
        symbol=sym, tier=2,
        momentum_size_mult=0.3,
        momentum_z_threshold=1.5, momentum_daily_z_threshold=1.5,
        momentum_target_atr=1.0, momentum_stop_atr=0.5,
        momentum_max_bars=2,
        allow_swing=False, allow_scalp=False, allow_momentum=True, allow_m15_scalp=False,
    )


def _load_730d(pair: str) -> pd.DataFrame | None:
    p = DATA_DIR / f"{pair}_H1_730d.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, index_col=0, parse_dates=True)


def _load_daily(pair: str) -> pd.DataFrame | None:
    """Load daily data for the pair — used by swing strategy."""
    p = DATA_DIR / f"{pair}_DAILY_2015-2026.csv"
    if not p.exists():
        # Fallback: check if we have any daily file
        matches = list(DATA_DIR.glob(f"{pair}_DAILY*.csv"))
        if matches:
            return pd.read_csv(matches[0], index_col=0, parse_dates=True)
        return None
    return pd.read_csv(p, index_col=0, parse_dates=True)


def main() -> int:
    ev = Evaluator(DATA_DIR, enable_rag=False, enable_logging=False, enable_changepoint=True)
    rows: list[dict] = []

    for pair in ACTIVE_PAIRS:
        h1 = _load_730d(pair)
        if h1 is None:
            print(f"  SKIP {pair} — 730d file missing")
            continue

        daily = _load_daily(pair)

        for strat in ("swing", "scalp", "momentum"):
            if strat == "swing":
                if daily is None:
                    print(f"  SKIP {pair}/swing — daily file missing")
                    trades_df = None
                else:
                    cfg = _eval_cfg_swing(pair)
                    trades_df = ev.run_swing_with_cfg(pair, daily, h1, cfg)
            elif strat == "scalp":
                cfg = _eval_cfg_scalp(pair)
                # scalp/momentum use h1 as daily substitute (no daily alignment in eval config)
                trades_df = ev.run_scalp_with_cfg(pair, daily if daily is not None else h1, h1, cfg)
            else:  # momentum
                cfg = _eval_cfg_momentum(pair)
                trades_df = ev.run_momentum_with_cfg(pair, daily if daily is not None else h1, h1, cfg)

            b = BIASED_BASELINE[(pair, strat)]

            if trades_df is None or trades_df.empty:
                m_sharpe = 0.0
                m_win_pct = 0.0
                m_trade_count = 0
                print(f"  WARN {pair:8} {strat:9} no trades generated")
            else:
                m = metrics(trades_df)
                if m is None:
                    m_sharpe = 0.0
                    m_win_pct = 0.0
                    m_trade_count = 0
                else:
                    m_sharpe = float(m["sharpe"])
                    m_win_pct = float(m.get("win_pct", 0.0))
                    m_trade_count = int(m.get("n", len(trades_df)))

            rows.append({
                "pair":         pair,
                "strategy":     strat,
                "old_sharpe":   round(b["sharpe"], 2),
                "new_sharpe":   round(m_sharpe, 2),
                "delta":        round(m_sharpe - b["sharpe"], 2),
                "old_win_pct":  round(b["win_pct"], 1),
                "new_win_pct":  round(m_win_pct, 1),
                "old_trades":   int(b["trades"]),
                "new_trades":   m_trade_count,
            })
            print(f"  OK   {pair:8} {strat:9} "
                  f"old={b['sharpe']:+.2f}  new={m_sharpe:+.2f}  "
                  f"delta={m_sharpe - b['sharpe']:+.2f}")

    # Write CSV
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "pair", "strategy", "old_sharpe", "new_sharpe", "delta",
            "old_win_pct", "new_win_pct", "old_trades", "new_trades",
        ])
        w.writeheader()
        w.writerows(rows)

    try:
        rel = OUT_PATH.relative_to(Path.cwd())
    except ValueError:
        rel = OUT_PATH
    print(f"\nReport saved: {rel}")
    if rows:
        deltas = [r["delta"] for r in rows]
        print(f"Rows: {len(rows)}  |  Deltas: "
              f"min={min(deltas):+.2f} "
              f"max={max(deltas):+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
