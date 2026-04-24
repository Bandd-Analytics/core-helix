"""4yr H1 scalp + momentum evaluation runner (BKTS-02, BKTS-03).

Runs H1 scalp and momentum strategies over 4yr data for every active pair,
producing a routing matrix dict and CSV evidence file.

Entry fix (BKTS-01): next-bar open fill simulation — all entry loops use
    next_row = h1.iloc[i + 1]
    entry_px = next_row['Open']
exactly as in backtest_evaluate_all.py after Plan 02 fix.

Thresholds (per CONTEXT.md D-10 and RESEARCH.md Open Questions #2):
    - Sharpe >= 0.5  AND  trade_count >= 30  →  allow_flag = True

Indicator resolution:
    If the loaded DataFrame already contains 'atr', 'z_score', 'daily_z'
    columns (e.g. synthetic test data), those are used directly.
    Otherwise they are computed via the Evaluator's rolling methods.

Usage:
    cd V2 && python -m backtest.backtest_4yr_evaluate
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from v3_intelligence.pair_config import PAIR_CONFIGS

ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parent / "reports"

SHARPE_THRESHOLD = 0.5    # D-10
MIN_TRADE_COUNT  = 30     # Open Questions #2


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_h1_4yr(pair: str, data_dir: Path) -> pd.DataFrame | None:
    """Load a {PAIR}_H1_4yr.csv file.  Returns None if missing."""
    f = data_dir / f"{pair}_H1_4yr.csv"
    if not f.exists():
        return None
    return pd.read_csv(f, index_col=0, parse_dates=True)


def _adaptive_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 14) -> pd.Series:
    """Rolling ATR — same formula as HybridMultiTimeframeBacktest.adaptive_atr."""
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))),
    )
    return tr.rolling(period).mean()


def _z_score_signal(close: pd.Series, period: int = 20) -> pd.Series:
    """Rolling z-score — same formula as HybridMultiTimeframeBacktest.z_score_signal."""
    ma  = close.rolling(period).mean()
    std = close.rolling(period).std()
    return (close - ma) / std.replace(0, np.nan)


def _ensure_indicators(h1: pd.DataFrame) -> pd.DataFrame:
    """Compute ATR, z_score and daily_z if not already present.

    Test fixtures supply these columns pre-baked; real CSVs do not.
    For real H1-only data (no separate daily DataFrame), daily_z is
    approximated from the same H1 z_score series — conservative but
    sufficient for the threshold-comparison routing matrix (D-09).
    """
    h1 = h1.copy()
    if "atr" not in h1.columns:
        h1["atr"] = _adaptive_atr(h1["High"], h1["Low"], h1["Close"])
    if "z_score" not in h1.columns:
        h1["z_score"] = _z_score_signal(h1["Close"])
    if "daily_z" not in h1.columns:
        h1["daily_z"] = h1["z_score"]
    return h1


def _run_scalp_loop(
    h1: pd.DataFrame,
    cfg: Any,
) -> pd.DataFrame:
    """Self-contained H1 scalp loop against pre-computed indicator columns.

    Mirrors the BKTS-01-fixed logic in Evaluator.run_scalp_with_cfg but
    operates on a single H1 DataFrame that already contains 'atr', 'z_score',
    'daily_z' (populated by _ensure_indicators before this call).
    """
    from backtest.backtest_hybrid import _session

    position = None
    trades: list[dict[str, Any]] = []

    for i in range(100, len(h1) - 1):
        row      = h1.iloc[i]
        next_row = h1.iloc[i + 1]
        ts       = h1.index[i]
        h1z  = row["z_score"]
        dz   = row["daily_z"]
        atr  = row["atr"]
        px   = row["Close"]
        sess = _session(ts.hour)

        if position is not None:
            ep  = position["entry_price"]
            lng = "LONG" in position["type"]
            pnl = (px - ep) / ep if lng else (ep - px) / ep
            av  = position["atr_entry"]
            bars = i - position["entry_bar"]
            tgt = av * cfg.scalp_target_atr / ep
            sl  = av * cfg.scalp_stop_atr   / ep
            why = None
            if   pnl >= tgt:                why = "target"
            elif pnl <= -sl:                why = "stop"
            elif bars > cfg.scalp_max_bars: why = "timeout"
            if why:
                trades.append({
                    "type":       position["type"],
                    "direction":  "LONG" if lng else "SHORT",
                    "strategy":   "H1_SCALP",
                    "entry_date": position["entry_date"],
                    "exit_date":  ts,
                    "entry_price": ep,
                    "exit_price":  px,
                    "pnl_pct":    pnl,
                    "bars_held":  bars,
                    "exit_reason": why,
                })
                position = None
        else:
            if (
                sess in ("LONDON", "NY")
                and not pd.isna(h1z) and abs(h1z) > cfg.scalp_z_threshold
                and not pd.isna(atr)  and atr > 0
                and (pd.isna(dz) or abs(dz) < 1.5
                     or (dz < 0 and h1z < 0) or (dz > 0 and h1z > 0))
            ):
                pt       = "H1_SCALP_LONG" if h1z < 0 else "H1_SCALP_SHORT"
                # BKTS-01: next-bar open fill
                entry_px = next_row["Open"]
                position = {
                    "type":        pt,
                    "entry_price": entry_px,
                    "entry_date":  ts,
                    "entry_bar":   i,
                    "atr_entry":   atr,
                    "size":        cfg.scalp_size_mult,
                }

    return pd.DataFrame(trades)


def _run_momentum_loop(
    h1: pd.DataFrame,
    cfg: Any,
) -> pd.DataFrame:
    """Self-contained momentum loop against pre-computed indicator columns."""
    from backtest.backtest_hybrid import _session

    position = None
    trades: list[dict[str, Any]] = []

    for i in range(100, len(h1) - 1):
        row      = h1.iloc[i]
        next_row = h1.iloc[i + 1]
        ts       = h1.index[i]
        h1z  = row["z_score"]
        dz   = row["daily_z"]
        atr  = row["atr"]
        px   = row["Close"]
        sess = _session(ts.hour)

        if position is not None:
            ep  = position["entry_price"]
            lng = "LONG" in position["type"]
            pnl = (px - ep) / ep if lng else (ep - px) / ep
            av  = position["atr_entry"]
            bars = i - position["entry_bar"]
            tgt = av * cfg.momentum_target_atr / ep
            sl  = av * cfg.momentum_stop_atr   / ep
            why = None
            if   pnl >= tgt:                   why = "target"
            elif pnl <= -sl:                   why = "stop"
            elif bars > cfg.momentum_max_bars: why = "timeout"
            if why:
                trades.append({
                    "type":       position["type"],
                    "direction":  "LONG" if lng else "SHORT",
                    "strategy":   "MOMENTUM",
                    "entry_date": position["entry_date"],
                    "exit_date":  ts,
                    "entry_price": ep,
                    "exit_price":  px,
                    "pnl_pct":    pnl,
                    "bars_held":  bars,
                    "exit_reason": why,
                })
                position = None
        else:
            if (
                sess in ("LONDON", "NY")
                and not pd.isna(h1z) and not pd.isna(dz)
                and abs(h1z) > cfg.momentum_z_threshold
                and abs(dz)  > cfg.momentum_daily_z_threshold
                and not pd.isna(atr) and atr > 0
                and ((dz < 0 and h1z < 0) or (dz > 0 and h1z > 0))
            ):
                pt       = "MOMENTUM_LONG" if h1z < 0 else "MOMENTUM_SHORT"
                # BKTS-01: next-bar open fill
                entry_px = next_row["Open"]
                position = {
                    "type":        pt,
                    "entry_price": entry_px,
                    "entry_date":  ts,
                    "entry_bar":   i,
                    "atr_entry":   atr,
                    "size":        cfg.momentum_size_mult,
                }

    return pd.DataFrame(trades)


def _metrics_from_trades(trades: pd.DataFrame) -> dict[str, float | int]:
    """Compute sharpe, win_rate, trade_count from a trades DataFrame."""
    if trades is None or len(trades) == 0:
        return {"sharpe": 0.0, "win_rate": 0.0, "trade_count": 0}

    pnl = trades["pnl_pct"]
    wins = pnl[pnl > 0]
    sharpe = float(
        pnl.mean() / pnl.std() * np.sqrt(252) if pnl.std() > 0 else 0.0
    )
    win_rate = float(len(wins) / len(pnl)) if len(pnl) > 0 else 0.0
    return {
        "sharpe":      sharpe,
        "win_rate":    win_rate,
        "trade_count": int(len(pnl)),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def run_4yr_evaluation(
    strategy: Literal["scalp", "momentum"],
    data_dir: Path = DEFAULT_DATA_DIR,
    pairs: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the chosen strategy over 4yr data for every pair in *pairs*.

    Returns:
        {pair: {"sharpe": float, "win_rate": float, "trade_count": int,
                "allow_flag": bool, "min_trades_met": bool,
                "sharpe_threshold_met": bool, "routing_matrix_entry": bool}}

    No pair is silently dropped — if the CSV is missing the row carries zeros
    and allow_flag=False.
    """
    if pairs is None:
        pairs = ACTIVE_PAIRS

    result: dict[str, dict[str, Any]] = {}

    for pair in pairs:
        df   = _load_h1_4yr(pair, data_dir)
        cfg  = PAIR_CONFIGS.get(pair)

        if df is None or cfg is None:
            result[pair] = {
                "sharpe": 0.0, "win_rate": 0.0, "trade_count": 0,
                "min_trades_met": False, "sharpe_threshold_met": False,
                "routing_matrix_entry": False, "allow_flag": False,
            }
            continue

        # Populate missing indicator columns (no-op when already present)
        h1 = _ensure_indicators(df)

        if strategy == "scalp":
            trades = _run_scalp_loop(h1, cfg)
        elif strategy == "momentum":
            trades = _run_momentum_loop(h1, cfg)
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")

        m = _metrics_from_trades(trades)
        sharpe      = float(m["sharpe"])
        win_rate    = float(m["win_rate"])
        trade_count = int(m["trade_count"])

        sharpe_ok = sharpe >= SHARPE_THRESHOLD
        trades_ok = trade_count >= MIN_TRADE_COUNT
        entry     = sharpe_ok and trades_ok

        result[pair] = {
            "sharpe":               sharpe,
            "win_rate":             win_rate,
            "trade_count":          trade_count,
            "min_trades_met":       trades_ok,
            "sharpe_threshold_met": sharpe_ok,
            "routing_matrix_entry": entry,
            "allow_flag":           entry,
        }

    return result


def write_routing_matrix_csv(
    result: dict[str, dict[str, Any]],
    strategy: str,
    out_path: Path,
) -> None:
    """Write per 07-UI-SPEC.md §4yr Routing Matrix Report.

    Columns: pair, strategy, sharpe, win_rate, trade_count,
             min_trades_met, sharpe_threshold_met, routing_matrix_entry, allow_flag
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "pair", "strategy", "sharpe", "win_rate", "trade_count",
        "min_trades_met", "sharpe_threshold_met",
        "routing_matrix_entry", "allow_flag",
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for pair, row in result.items():
            w.writerow({
                "pair":                  pair,
                "strategy":              strategy,
                "sharpe":                round(row["sharpe"], 2),
                "win_rate":              round(row["win_rate"] * 100, 1),
                "trade_count":           int(row["trade_count"]),
                "min_trades_met":        row["min_trades_met"],
                "sharpe_threshold_met":  row["sharpe_threshold_met"],
                "routing_matrix_entry":  row["routing_matrix_entry"],
                "allow_flag":            row["allow_flag"],
            })


# ── __main__ runner ───────────────────────────────────────────────────────────

def main() -> int:
    combined_rows: list[dict[str, Any]] = []

    for strat in ("scalp", "momentum"):
        print(f"\n--- Running {strat} strategy on 4yr H1 data ---")
        r = run_4yr_evaluation(strat)
        for pair, row in r.items():
            combined_rows.append({
                "pair":                  pair,
                "strategy":              strat,
                "sharpe":                round(row["sharpe"], 2),
                "win_rate":              round(row["win_rate"] * 100, 1),
                "trade_count":           int(row["trade_count"]),
                "min_trades_met":        row["min_trades_met"],
                "sharpe_threshold_met":  row["sharpe_threshold_met"],
                "routing_matrix_entry":  row["routing_matrix_entry"],
                "allow_flag":            row["allow_flag"],
            })
            flag = "+" if row["routing_matrix_entry"] else "-"
            print(
                f"  {flag} {pair:7} {strat:9} "
                f"Sh={row['sharpe']:+.2f}  win={row['win_rate'] * 100:4.1f}%  "
                f"n={row['trade_count']:4d}  allow={row['allow_flag']}"
            )

    out = DEFAULT_REPORTS_DIR / "4yr_routing_matrix.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = list(combined_rows[0].keys())
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(combined_rows)
    print(f"\nReport saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
