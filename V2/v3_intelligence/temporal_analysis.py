"""Phase 8.5 — Temporal & Session Analysis library.

SESS-01: per-(pair, strategy, timeframe) session performance bucketing (this Plan 02).
SESS-02: heatmap rendering (added in Plan 03 — render_combo_heatmaps lives here too).
SESS-03: empirical risk-calendar pipeline (added in Plan 04).
SESS-04: session_config.py regeneration (added in Plan 05).

Reuses Phase 7 _run_scalp_loop / _run_momentum_loop / _metrics_from_trades and
Phase 8.4 OHLCVCache + PitClock — assembly, not invention (RESEARCH §Don't Hand-Roll).

Architecture:
  - assign_session()          — vectorized .between() session masks (RESEARCH Pattern 1)
  - discover_active_combos()  — iterates PAIR_CONFIGS dynamically; never hardcodes the list
  - discover_end_ts()         — min-of-maxes PiT anchor across timeframes
  - generate_trades()         — dispatches to the right Phase 7/8.4 loop (RESEARCH Pattern 2)
  - bucket_trades()           — per-dim Sharpe (mean/std × √252) + status taxonomy
  - write_combo_csv()         — materialize one CSV per (pair, strategy, timeframe)

Constants are frozen contract — Plans 03/04/05 import them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

# Use Agg backend for headless PNG rendering — no display required (CONTEXT D-16).
# Set BEFORE importing pyplot so the backend is locked in.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import seaborn as sns  # noqa: E402

from v3_intelligence.cache import OHLCVCache
from v3_intelligence.pair_config import (
    PAIR_CONFIGS,
    PairConfig,
    get_pair_config,
)
from v3_intelligence.pit import PitClock, pit_active

# ── Constants (frozen contract — Plans 03/04/05 import these) ──────────────
SHARPE_GOOD: float = 0.3      # CONTEXT D-04 — bucket = "good window"
SHARPE_BAD:  float = -0.2     # CONTEXT D-04 — bucket = "bad window" (blacklisted)
MIN_TRADES:  int   = 30       # CONTEXT D-03 — significance gate (matches Phase 7)

# CONTEXT D-01 — session UTC boundaries (start_hour, end_hour) inclusive-left/exclusive-right
SESSION_BOUNDS_UTC: dict[str, tuple[int, int]] = {
    "TOKYO":  (0,  9),    # 00:00-09:00 UTC
    "LONDON": (7,  16),   # 07:00-16:00 UTC
    "NY":     (13, 22),   # 13:00-22:00 UTC
}
OVERLAP_BOUNDS:     tuple[int, int] = (13, 16)   # London-NY overlap (also CONTEXT D-01)
LONDON_OPEN_BOUNDS: tuple[int, int] = (7,  9)    # London open (early-London peak)

# Active timeframes considered in CSV bucketing dimensions
DIMS_ALWAYS:        list[str] = ["session", "hour", "dow"]
DIMS_H1_DAILY_ONLY: list[str] = ["dom", "doy"]   # CONTEXT D-14 — M15 corpus too thin


# ── Pattern 1: Vectorized session-mask construction ───────────────────────────
def assign_session(trades: pd.DataFrame) -> pd.DataFrame:
    """Tag each trade by entry_ts hour-of-day per CONTEXT D-01/D-02.

    Bar at 06:55 UTC -> session='OFF' (no session active).
    Bar at 07:00 UTC -> session='LONDON' (London opens; in_london_open=True).
    Bar at 13:00 UTC -> session='NY' (NY opens; in_overlap=True).
    Bar at 22:00 UTC -> session='OFF' (NY closes).
    Cross-session bars inherit the session their start-ts belongs to.

    Returns a copy of `trades` with added columns:
      session ∈ {TOKYO, LONDON, NY, OFF},
      in_overlap (bool — 13:00-15:59 UTC),
      in_london_open (bool — 07:00-08:59 UTC).

    Uses .between() vectorized over the entry_ts hour series — RESEARCH §Pattern 1
    (200×–500× faster than .apply on 24k-row DataFrames; RESEARCH §Anti-Patterns).
    """
    h = trades["entry_ts"].dt.hour
    out = trades.copy()
    out["session"] = "OFF"
    # Order matters: NY overrides London (overlap 13-16); London overrides Tokyo (overlap 7-9).
    out.loc[h.between(SESSION_BOUNDS_UTC["TOKYO"][0],
                      SESSION_BOUNDS_UTC["TOKYO"][1] - 1), "session"] = "TOKYO"
    out.loc[h.between(SESSION_BOUNDS_UTC["LONDON"][0],
                      SESSION_BOUNDS_UTC["LONDON"][1] - 1), "session"] = "LONDON"
    out.loc[h.between(SESSION_BOUNDS_UTC["NY"][0],
                      SESSION_BOUNDS_UTC["NY"][1] - 1), "session"] = "NY"
    out["in_overlap"]     = h.between(OVERLAP_BOUNDS[0], OVERLAP_BOUNDS[1] - 1)
    out["in_london_open"] = h.between(LONDON_OPEN_BOUNDS[0], LONDON_OPEN_BOUNDS[1] - 1)
    return out


# ── Active-combo discovery (RESEARCH Anti-Pattern: NEVER hardcode 13-tuple) ───
def discover_active_combos(
    pair_configs: dict[str, PairConfig] | None = None,
) -> list[tuple[str, str, str]]:
    """Iterate PAIR_CONFIGS to discover (pair, strategy, timeframe) combos.

    Strategy/timeframe mapping (per ROADMAP active matrix):
      allow_swing       -> ("SWING",     "Daily")
      allow_scalp       -> ("H1_SCALP",  "H1")
      allow_momentum    -> ("MOMENTUM",  "H1")
      allow_m15_scalp   -> ("M15_SCALP", "M15")

    NEVER hardcoded — adapts when Phase 8.4 D-07-style flag flips happen.
    """
    if pair_configs is None:
        pair_configs = PAIR_CONFIGS
    combos: list[tuple[str, str, str]] = []
    for pair, cfg in pair_configs.items():
        if cfg.allow_swing:
            combos.append((pair, "SWING", "Daily"))
        if cfg.allow_scalp:
            combos.append((pair, "H1_SCALP", "H1"))
        if cfg.allow_momentum:
            combos.append((pair, "MOMENTUM", "H1"))
        if cfg.allow_m15_scalp:
            combos.append((pair, "M15_SCALP", "M15"))
    return combos


# ── PiT-anchor end_ts discovery (mirror run_gbpnzd_4yr_eval._gbpnzd_end_ts) ───
def discover_end_ts(
    cache: OHLCVCache,
    timeframes: tuple[str, ...] = ("M15", "H1", "Daily"),
) -> pd.Timestamp:
    """Return the minimum max(ts) across the cache for given timeframes.

    Min-of-maxes ensures end_ts is reachable for every (pair, timeframe);
    guards against partial cache-state where one timeframe is fresher than another.
    Falls back to a CSV-mtime probe if cache.get_bars raises (Linux failover scenario).

    Caller is responsible for wrapping subsequent reads in `with PitClock(end_ts):`.
    """
    far = pd.Timestamp("2030-01-01", tz="UTC")
    end_candidates: list[pd.Timestamp] = []
    for tf in timeframes:
        try:
            df = cache.get_bars(
                "USDJPY", tf,
                start=far - pd.Timedelta(days=14),
                end=far,
            )
            if not df.empty:
                end_candidates.append(df.index.max())
        except Exception:
            # Cache may auto-pull and miss, or no SUPABASE_DB_URL — fall back to CSV mtime
            csv = Path(__file__).resolve().parents[1] / "data" / f"USDJPY_{tf}_4yr.csv"
            if csv.exists():
                end_candidates.append(
                    pd.Timestamp(csv.stat().st_mtime, unit="s", tz="UTC")
                )
    if not end_candidates:
        raise RuntimeError("discover_end_ts: no usable timeframes in cache")
    return min(end_candidates)


# ── Pattern 2: Trade-source dispatcher ────────────────────────────────────────
# Each dispatcher reads bars via cache.get_bars() (CONTEXT D-17) and reuses the
# Phase 7 / 8.4 trade-generation loops verbatim. We do NOT fork those loops.
def _dispatch_h1_scalp(
    pair: str, cache: OHLCVCache, end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """H1_SCALP / H1 -> backtest_4yr_evaluate._run_scalp_loop on cache-loaded H1 bars."""
    from backtest.backtest_4yr_evaluate import _ensure_indicators, _run_scalp_loop
    cfg = get_pair_config(pair)
    df = cache.get_bars(
        pair, "H1",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    h1 = _ensure_indicators(df)
    trades = _run_scalp_loop(h1, cfg)
    return _normalize_trade_df(trades, pair, "H1_SCALP", "H1")


def _dispatch_momentum(
    pair: str, cache: OHLCVCache, end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """MOMENTUM / H1 -> backtest_4yr_evaluate._run_momentum_loop on cache-loaded H1 bars."""
    from backtest.backtest_4yr_evaluate import _ensure_indicators, _run_momentum_loop
    cfg = get_pair_config(pair)
    df = cache.get_bars(
        pair, "H1",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    h1 = _ensure_indicators(df)
    trades = _run_momentum_loop(h1, cfg)
    return _normalize_trade_df(trades, pair, "MOMENTUM", "H1")


def _dispatch_m15_scalp(
    pair: str, cache: OHLCVCache, end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """M15_SCALP / M15 -> backtest_hybrid._backtest_m15_symbol on cache-loaded M15+Daily bars."""
    from backtest.backtest_hybrid import HybridMultiTimeframeBacktest
    daily = cache.get_bars(
        pair, "Daily",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    m15 = cache.get_bars(
        pair, "M15",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    bt = HybridMultiTimeframeBacktest(
        data_dir=Path(__file__).resolve().parents[1] / "data",
        enable_rag=False, enable_logging=False,
        enable_changepoint=False, enable_hurst_filter=False,
    )
    trades = bt._backtest_m15_symbol(pair, daily, m15)
    return _normalize_trade_df(trades, pair, "M15_SCALP", "M15")


def _dispatch_swing(
    pair: str, cache: OHLCVCache, end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """SWING / Daily -> backtest_hybrid._backtest_swing_symbol on cache-loaded Daily+H1 bars."""
    from backtest.backtest_hybrid import HybridMultiTimeframeBacktest
    daily = cache.get_bars(
        pair, "Daily",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    h1 = cache.get_bars(
        pair, "H1",
        start=end_ts - pd.Timedelta(days=4 * 366),
        end=end_ts,
    )
    bt = HybridMultiTimeframeBacktest(
        data_dir=Path(__file__).resolve().parents[1] / "data",
        enable_rag=False, enable_logging=False,
        enable_changepoint=False, enable_hurst_filter=False,
    )
    trades = bt._backtest_swing_symbol(pair, daily, h1)
    return _normalize_trade_df(trades, pair, "SWING", "Daily")


def _normalize_trade_df(
    trades: pd.DataFrame, pair: str, strategy: str, timeframe: str,
) -> pd.DataFrame:
    """Normalize the four loops' output schemas into a single trade DF.

    Phase 7/8.4 loops emit columns: type, direction, strategy, entry_date,
    exit_date, entry_price, exit_price, pnl_pct, bars_held, exit_reason.
    We rename entry_date -> entry_ts, exit_date -> exit_ts and add pair/timeframe.
    Empty input returns the empty canonical schema (no error, no exception).
    """
    if trades is None or len(trades) == 0:
        return pd.DataFrame(columns=[
            "entry_ts", "exit_ts", "pnl_pct",
            "direction", "strategy", "pair", "timeframe",
        ])
    out = trades.copy()
    if "entry_date" in out.columns:
        out = out.rename(columns={"entry_date": "entry_ts"})
    if "exit_date" in out.columns:
        out = out.rename(columns={"exit_date": "exit_ts"})
    out["pair"] = pair
    out["strategy"] = strategy
    out["timeframe"] = timeframe
    # Ensure entry_ts is tz-aware UTC (D-01)
    if "entry_ts" in out.columns:
        # Normalize to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(out["entry_ts"]):
            out["entry_ts"] = pd.to_datetime(out["entry_ts"], utc=True)
        elif out["entry_ts"].dt.tz is None:
            out["entry_ts"] = out["entry_ts"].dt.tz_localize("UTC")
    return out


def generate_trades(
    pair: str, strategy: str, timeframe: str,
    cache: OHLCVCache, end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """Dispatch to the right Phase 7/8.4 trade generator.

    RESEARCH §Pattern 2: do not fork the loops; route to the existing PiT-validated
    implementation. Caller is responsible for wrapping in `with PitClock(end_ts):`.

    Raises ValueError on unsupported (strategy, timeframe) combos.
    """
    if strategy == "H1_SCALP" and timeframe == "H1":
        return _dispatch_h1_scalp(pair, cache, end_ts)
    if strategy == "MOMENTUM" and timeframe == "H1":
        return _dispatch_momentum(pair, cache, end_ts)
    if strategy == "M15_SCALP" and timeframe == "M15":
        return _dispatch_m15_scalp(pair, cache, end_ts)
    if strategy == "SWING" and timeframe == "Daily":
        return _dispatch_swing(pair, cache, end_ts)
    raise ValueError(
        f"unsupported combo: {strategy}/{timeframe} (pair={pair})"
    )


# ── Pattern 4: Trade-count-based Sharpe (locked to Phase 7 √252 convention) ──
def _bucket_metrics(group: pd.Series) -> dict[str, Any]:
    """Compute sharpe, win_rate, trade_count for a group's pnl_pct series.

    Per RESEARCH §Pattern 4: use Phase 7 √252 convention regardless of timeframe.
    This matches backtest_4yr_evaluate._metrics_from_trades.
    """
    n = len(group)
    if n == 0:
        return {"sharpe": 0.0, "win_rate": 0.0, "trade_count": 0}
    std = group.std()
    sharpe = float(group.mean() / std * np.sqrt(252)) if std and std > 0 else 0.0
    win_rate = float((group > 0).mean())
    return {"sharpe": sharpe, "win_rate": win_rate, "trade_count": int(n)}


def _classify_status(sharpe: float, trade_count: int) -> str:
    """D-03 + D-04 status taxonomy — bucket-level decision.

    Order of checks matters: insufficient_evidence wins over good/bad/neutral
    so a 5-trade bucket with sharpe=10.0 still emits 'insufficient_evidence'.
    """
    if trade_count < MIN_TRADES:
        return "insufficient_evidence"
    if sharpe >= SHARPE_GOOD:
        return "good"
    if sharpe <= SHARPE_BAD:
        return "bad"
    return "neutral"


def bucket_trades(
    trades: pd.DataFrame, timeframe: str,
) -> dict[str, pd.DataFrame]:
    """Return {dim: DataFrame} with columns [bucket, sharpe, win_rate, trade_count, status].

    Dimensions: session, hour, dow always; dom, doy for H1 + Daily only (CONTEXT D-14).
    For insufficient_evidence buckets, sharpe is set to NaN (heatmap mask hook).

    The session dim uses the 5-state taxonomy from assign_session (TOKYO/LONDON/NY/OFF).
    Other dims are integer keys (hour 0-23, dow 0-6, dom 1-31, doy 1-366).
    """
    dims = list(DIMS_ALWAYS)
    if timeframe in ("H1", "Daily"):
        dims += list(DIMS_H1_DAILY_ONLY)

    if trades is None or len(trades) == 0:
        return {
            dim: pd.DataFrame(
                columns=[dim, "sharpe", "win_rate", "trade_count", "status"]
            )
            for dim in dims
        }

    trades = assign_session(trades)
    trades = trades.copy()
    trades["hour"] = trades["entry_ts"].dt.hour
    trades["dow"]  = trades["entry_ts"].dt.dayofweek
    trades["dom"]  = trades["entry_ts"].dt.day
    trades["doy"]  = trades["entry_ts"].dt.dayofyear

    out: dict[str, pd.DataFrame] = {}
    for dim in dims:
        grouped = trades.groupby(dim, observed=False)["pnl_pct"]
        rows: list[dict[str, Any]] = []
        for key, group in grouped:
            m = _bucket_metrics(group)
            m[dim] = key
            m["status"] = _classify_status(m["sharpe"], m["trade_count"])
            if m["status"] == "insufficient_evidence":
                m["sharpe"] = float("nan")
            rows.append(m)
        df = pd.DataFrame(
            rows,
            columns=[dim, "sharpe", "win_rate", "trade_count", "status"],
        )
        out[dim] = df.sort_values(dim).reset_index(drop=True)
    return out


# ── CSV writer (SESS-01 closes here) ──────────────────────────────────────────
def write_combo_csv(
    buckets: dict[str, pd.DataFrame],
    pair: str, strategy: str, timeframe: str,
    out_dir: Path,
) -> Path:
    """Materialize one CSV per (pair, strategy, timeframe) with one row per (dim, bucket).

    Schema: dim, bucket, sharpe, win_rate, trade_count, status, pair, strategy, timeframe.
    Path: {out_dir}/session_performance_{pair}_{strategy}_{timeframe}.csv

    Insufficient_evidence rows are emitted (NOT silently dropped) — D-03 + RESEARCH
    §Specifics requires "first-class status, not silently dropped".
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for dim, df in buckets.items():
        for _, r in df.iterrows():
            rows.append({
                "dim":         dim,
                "bucket":      r[dim],
                "sharpe":      r["sharpe"],
                "win_rate":    r["win_rate"],
                "trade_count": r["trade_count"],
                "status":      r["status"],
                "pair":        pair,
                "strategy":    strategy,
                "timeframe":   timeframe,
            })
    out_df = pd.DataFrame(
        rows,
        columns=[
            "dim", "bucket", "sharpe", "win_rate", "trade_count", "status",
            "pair", "strategy", "timeframe",
        ],
    )
    path = out_dir / f"session_performance_{pair}_{strategy}_{timeframe}.csv"
    out_df.to_csv(path, index=False)
    return path


# ── SESS-02: Heatmap rendering (Plan 03) ──────────────────────────────────────
# Frozen render contract — test_heatmap_diverging_colormap inspects this dict.
# Locked per RESEARCH §Pattern 3 — diverging RdYlGn anchored at zero with ±1.0 clip
# so cell color encodes Sharpe sign + magnitude consistently across combos.
RENDER_KWARGS: dict = {
    "cmap":   "RdYlGn",   # diverging: red negative, yellow ~zero, green positive
    "center": 0,          # anchors zero-Sharpe to colormap midpoint (critical)
    "vmin":   -1.0,       # clip extreme outliers below (rare bucket Sharpe < -1
                          # would otherwise dominate the colormap)
    "vmax":    1.0,       # clip extreme outliers above
    "annot":   True,      # cell-level numeric annotation
    "fmt":    ".2f",
}


def build_heatmap_mask(
    bucket_df: pd.DataFrame,
    min_trades: int = MIN_TRADES,
) -> pd.Series:
    """Return a boolean Series indexed by the bucket dim (e.g., hour/dow/dom/doy).

    True  = mask out (trade_count < min_trades — render gray, "no data").
    False = render normally (sufficient evidence).

    Per CONTEXT D-03 + D-04 + RESEARCH §Anti-Patterns: cells with insufficient
    evidence MUST be masked (gray), NOT zero-filled. Zero-fill lies green/yellow
    on a diverging colormap and would mislead operators.

    Input contract: bucket_df has the dim column as its first column, plus
    columns [sharpe, win_rate, trade_count, status] (the bucket_trades schema).
    """
    # The dim column name is the first column (matches bucket_trades output).
    dim_col = bucket_df.columns[0]
    mask = bucket_df.set_index(dim_col)["trade_count"] < min_trades
    return mask


def render_combo_heatmaps(
    buckets: dict[str, pd.DataFrame],
    pair: str, strategy: str, timeframe: str,
    out_dir: Path,
) -> list[Path]:
    """Render one PNG per dimension per (pair, strategy, timeframe).

    Per CONTEXT D-14:
      - hour + dow always rendered for every combo
      - dom + doy ONLY rendered for H1 / Daily combos (M15 corpus too thin per
        RESEARCH §Pitfall 2 — DoM/DoY buckets would be sparse and noisy at M15)
    Per RESEARCH §Pattern 3 (locked render contract):
      - cmap='RdYlGn', center=0, vmin/vmax=±1.0, annot=True, fmt='.2f'
      - mask=trade_count<MIN_TRADES (gray cells, never zero-filled)
    Per CONTEXT D-14 (output path convention):
      - {out_dir}/heatmap_{dim}_{pair}_{strategy}_{timeframe}.png

    Note on `session` dim: session is a categorical (TOKYO/LONDON/NY/OFF) and
    is reported in the CSV alongside other dims. We deliberately skip a session
    heatmap here — heatmaps are for the integer-keyed dims (hour/dow/dom/doy)
    where the diverging colormap reads naturally as a 1×N strip.

    Returns the list of written PNG paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Determine which dims to render. M15 skips dom/doy per CONTEXT D-14.
    dims_to_render = list(DIMS_ALWAYS)  # session, hour, dow
    if timeframe in ("H1", "Daily"):
        dims_to_render += list(DIMS_H1_DAILY_ONLY)  # dom, doy
    # session is reported via CSV; heatmaps are for integer dims only.
    dims_to_render = [d for d in dims_to_render if d != "session"]

    for dim in dims_to_render:
        df = buckets.get(dim)
        if df is None or df.empty:
            continue

        # Build matrix: 1 row × N columns (N = bucket count for this dim).
        matrix = df.set_index(dim)[["sharpe"]].T   # shape (1, N)
        mask_series = build_heatmap_mask(df)        # Series indexed by dim
        mask = mask_series.values.reshape(1, -1)    # shape (1, N), aligned

        # Figure sizing: scale width with bucket count (24 hours wide → 12in).
        width = max(8.0, 0.5 * len(df))
        fig, ax = plt.subplots(figsize=(width, 2.5))

        sns.heatmap(
            matrix,
            mask=mask,
            cmap=RENDER_KWARGS["cmap"],
            center=RENDER_KWARGS["center"],
            vmin=RENDER_KWARGS["vmin"],
            vmax=RENDER_KWARGS["vmax"],
            annot=RENDER_KWARGS["annot"],
            fmt=RENDER_KWARGS["fmt"],
            cbar_kws={"label": "Sharpe (annualized, clipped to ±1.0)"},
            ax=ax,
        )
        ax.set_title(f"{pair} / {strategy} / {timeframe} — Sharpe by {dim}")
        ax.set_xlabel(dim)
        ax.set_ylabel("")
        fig.tight_layout()

        out_path = out_dir / f"heatmap_{dim}_{pair}_{strategy}_{timeframe}.png"
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        written.append(out_path)

    return written


__all__ = [
    # Constants
    "SHARPE_GOOD", "SHARPE_BAD", "MIN_TRADES",
    "SESSION_BOUNDS_UTC", "OVERLAP_BOUNDS", "LONDON_OPEN_BOUNDS",
    "DIMS_ALWAYS", "DIMS_H1_DAILY_ONLY",
    "RENDER_KWARGS",
    # Public API
    "assign_session",
    "discover_active_combos",
    "discover_end_ts",
    "generate_trades",
    "bucket_trades",
    "write_combo_csv",
    "build_heatmap_mask",
    "render_combo_heatmaps",
    # Re-exports for convenience
    "PitClock", "pit_active",
]
