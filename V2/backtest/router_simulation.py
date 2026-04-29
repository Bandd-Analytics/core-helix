"""ROUT-04 4yr portfolio simulator (CONTEXT D-18 / Phase 9 P04).

Loads 8 detector JSONs + 8 H1 4yr CSVs (Phase 7/8.4 corpus); enters ONE
PitClock(end_ts) wrap; per bar advances each pair's OnlineRegimeFilter exactly
once via update(); calls StrategyRouter.route(); manages open positions in
InMemoryPositionStore; calls learning_loop.on_trade_close on every simulated
exit (separate sim DB + Chroma collection — RESEARCH §6).

Computes aggregate Sharpe via Phase 7 sqrt(252) convention; compares to
max-per-pair best Sharpe + 0.2; writes report JSON.

Per RESEARCH Pitfalls:
  #1  cache auto-pull refused inside PitClock — read CSVs directly
  #5  Phase 8.4 — single PitClock wrap, NO nesting
  #6  route() never calls update() — sim controls bar advance
  #7  pit_validator: next_row['Open'] for entries; row['Close'] for exits
  #8  RAG cold-start: warm_rag=True keeps gate 4 useful from bar 0
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd

from v3_intelligence.pair_config import PAIR_CONFIGS, SHARPE_4YR
from v3_intelligence.pit import PitClock
from v3_intelligence.regime import OnlineRegimeFilter
from v3_intelligence.regime.persistence import load_detector
from v3_intelligence.router import (
    Direction,
    InMemoryPositionStore,
    OpenPosition,
    RouteDecision,
    Strategy,
    StrategyRouter,
)
from v3_intelligence.learning_loop import on_trade_close
from v3_intelligence.trade_logger import TradeLogger

try:
    from v3_intelligence.rag_signal_filter import RAGSignalFilter, CHROMA_AVAILABLE
except ImportError:  # pragma: no cover
    RAGSignalFilter = None  # type: ignore[misc,assignment]
    CHROMA_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
REGIME_DIR = DATA_DIR / "regime"
REPORTS_DIR = PROJECT_ROOT / "reports"


# Per-strategy exit parameters (D-13 equal-per-dispatch baseline; see plan task 1a).
EXIT_PARAMS: dict[Strategy, dict[str, float]] = {
    Strategy.DAILY_SWING: {"timeout_bars": 5, "target_atr_mult": 2.0, "stop_atr_mult": 1.0},
    Strategy.H1_SCALP: {"timeout_bars": 8, "target_atr_mult": 1.5, "stop_atr_mult": 0.7},
    Strategy.H1_MOMENTUM: {"timeout_bars": 12, "target_atr_mult": 2.0, "stop_atr_mult": 1.0},
    Strategy.M15_SCALP: {"timeout_bars": 6, "target_atr_mult": 1.0, "stop_atr_mult": 0.5},
}


@dataclass
class _LivePosition:
    """Internal position tracker — extends OpenPosition with exit machinery."""

    pair: str
    direction: Direction
    strategy: Strategy
    opened_at: datetime
    entry_px: float
    size_mult: float
    confidence: float
    atr_at_entry: float
    bar_index_at_entry: int
    daily_z_at_entry: float
    h1_z_at_entry: float
    vol_pct_at_entry: float


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range over (High, Low, Close) — receives price columns as args.

    Caller must pass the columns explicitly so the PiT validator whitelists
    the price-column subscripts as indicator-args (per pit_validator.py
    _is_indicator_computation).
    """
    return pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _zscore_20(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """20-period rolling MA, std, and z-score on Close — indicator-arg pattern."""
    ma = close.rolling(20, min_periods=20).mean()
    std = close.rolling(20, min_periods=20).std()
    z = (close - ma) / std
    return ma, std, z


def _log_returns(close: pd.Series) -> pd.Series:
    """Log returns from Close column — indicator-arg pattern."""
    return np.log(close / close.shift(1))


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorised pre-loop indicator computation (PiT-validator-safe — RESEARCH §5).

    Adds: atr (14), ma20, std20, h1_z (20-period z-score on Close), daily_z
    (cheap proxy = h1_z per CONTEXT D-04 simplification), vol_percentile
    (rolling 120-bar percentile of atr), log_return.

    All price-column accesses pass through the helper functions above so the
    PiT validator (V2/backtest/pit_validator.py) whitelists them via
    _is_indicator_computation (RHS-root-Call argument pattern).
    """
    df["atr"] = _true_range(df["High"], df["Low"], df["Close"]).rolling(
        14, min_periods=14
    ).mean()
    ma20, std20, h1_z = _zscore_20(df["Close"])
    df["ma20"] = ma20
    df["std20"] = std20
    df["h1_z"] = h1_z
    # Daily-z: cheap proxy (CONTEXT D-04 simplification for 4yr sim)
    df["daily_z"] = df["h1_z"]
    # Vol percentile via rolling rank (pct=True returns 0.0-1.0)
    df["vol_percentile"] = df["atr"].rolling(120, min_periods=60).rank(pct=True)
    # Log return
    df["log_return"] = _log_returns(df["Close"])
    return df


def _load_h1_data() -> dict[str, pd.DataFrame]:
    """Pre-load all 8 pairs' 4yr CSVs OUTSIDE PitClock (Pitfall #1).

    Reads each CSV with Datetime as parseable index; calls _compute_indicators;
    raises if any pair's CSV is missing.
    """
    out: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for pair in PAIR_CONFIGS:
        csv = DATA_DIR / f"{pair}_H1_4yr.csv"
        if not csv.exists():
            missing.append(pair)
            continue
        df = pd.read_csv(csv, index_col=0, parse_dates=True)
        df = _compute_indicators(df)
        out[pair] = df
    if missing:
        raise RuntimeError(
            f"Missing 4yr H1 CSVs for {missing}. Phase 8.4 INFRA-02 covers GBPNZD; "
            f"Phase 7 P04 covers others. Plan 03 prerequisite — check V2/data/."
        )
    return out


def _load_detectors() -> dict[str, OnlineRegimeFilter]:
    """Construct per-pair OnlineRegimeFilter from saved detector JSONs."""
    out: dict[str, OnlineRegimeFilter] = {}
    missing: list[str] = []
    for pair in PAIR_CONFIGS:
        path = REGIME_DIR / f"{pair}_detector.json"
        if not path.exists():
            missing.append(pair)
            continue
        out[pair] = OnlineRegimeFilter(load_detector(path))
    if missing:
        raise RuntimeError(
            f"Missing detector JSONs for {missing}. "
            f"Plan 03 must run first: cd V2 && python -m scripts.fit_regime_detectors --pair all"
        )
    return out


def _classify_session(hour_utc: int) -> str:
    """UTC hour -> coarse session string (matches v3_intelligence.router._classify_session)."""
    if 0 <= hour_utc < 9:
        return "TOKYO"
    if 7 <= hour_utc < 16:
        return "LONDON"
    if 13 <= hour_utc < 22:
        return "NY"
    return "OFF"


def _build_snapshot(pair: str, ts, row) -> SimpleNamespace:
    """Construct the BarSnapshot-shaped object router.route() expects."""
    return SimpleNamespace(
        pair=pair,
        timestamp=ts,
        close=float(row["Close"]),
        log_return=float(row.get("log_return", 0.0) or 0.0),
        daily_z=float(row.get("daily_z", 0.0) or 0.0),
        h1_z=float(row.get("h1_z", 0.0) or 0.0),
        vol_percentile=float(row.get("vol_percentile", 0.5) or 0.5),
    )


def _exit_position(
    pos: _LivePosition,
    ts,
    exit_px: float,
    exit_reason: str,
    sim_logger: TradeLogger,
    sim_rag,
    *,
    warm_rag: bool,
) -> dict:
    """Build the trade-close dict (learning_loop contract) and dispatch.

    Per RESEARCH §6: trade dict required keys per learning_loop.py lines 11-17.
    Returns the trade dict so caller can append to closed_trades for Sharpe.
    """
    sign = 1.0 if pos.direction == Direction.LONG else -1.0
    pnl_pct = sign * (exit_px - pos.entry_px) / pos.entry_px
    rec = {
        "symbol": pos.pair,
        "type": f"{pos.strategy.value}_{pos.direction.value}",
        "strategy_type": pos.strategy.value,
        "direction": pos.direction.value,
        "entry_date": pos.opened_at,
        "exit_date": ts,
        "entry_price": pos.entry_px,
        "exit_price": exit_px,
        "pnl_pct": pnl_pct,
        "bars_held": None,  # caller fills via current bar index
        "exit_reason": exit_reason,
        "session": _classify_session(ts.hour),
        "hour_utc": pos.opened_at.hour,
        "size": pos.size_mult,
        "daily_z": pos.daily_z_at_entry,
        "h1_z": pos.h1_z_at_entry,
        "vol_percentile": pos.vol_pct_at_entry,
        "regime": None,
        "params_json": json.dumps(
            {
                "size_mult": pos.size_mult,
                "confidence": pos.confidence,
                "atr_at_entry": pos.atr_at_entry,
            }
        ),
    }
    # Dispatch to learning loop (writes to sim_logger SQLite + sim_rag Chroma).
    if warm_rag:
        on_trade_close(rec, logger=sim_logger, rag=sim_rag)
    else:
        on_trade_close(rec, logger=sim_logger, rag=None)
    return rec


def _aggregate_sharpe(pnl_records: list[dict]) -> float:
    """Phase 7 sqrt(252) lock (RESEARCH §6 / Pattern 4).

    Bins pnl_pct by exit_date calendar day; computes daily mean / std *
    sqrt(252). Returns 0.0 on insufficient data (<2 days or zero std).
    """
    if not pnl_records:
        return 0.0
    df = pd.DataFrame(pnl_records)
    df["exit_day"] = pd.to_datetime(df["exit_date"]).dt.date
    daily = df.groupby("exit_day")["pnl_pct"].sum()
    if len(daily) < 2 or daily.std(ddof=1) == 0 or pd.isna(daily.std(ddof=1)):
        return 0.0
    return float(daily.mean() / daily.std(ddof=1) * math.sqrt(252))


def _best_single_sharpe() -> float:
    """Max over pairs of (max over strategies in SHARPE_4YR[pair]) — D-16 baseline."""
    return max(
        max(strategy_sharpes.values())
        for strategy_sharpes in SHARPE_4YR.values()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — Task 1b adds the body. This stub raises so import-time
# tests pass while the loop lands separately.
# ─────────────────────────────────────────────────────────────────────────────


def run_router_simulation(
    *,
    report_path: Optional[Path] = None,
    sim_db_path: Optional[Path] = None,
    rag_collection: str = "router_sim_trades",
    warm_rag: bool = True,
) -> dict:
    """ROUT-04 entry point — Task 1b implements the main loop body."""
    raise NotImplementedError("Task 1b adds the run_router_simulation main loop body")


__all__ = [
    "EXIT_PARAMS",
    "_LivePosition",
    "_compute_indicators",
    "_load_h1_data",
    "_load_detectors",
    "_classify_session",
    "_build_snapshot",
    "_exit_position",
    "_aggregate_sharpe",
    "_best_single_sharpe",
    "run_router_simulation",
]
