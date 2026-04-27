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


# =============================================================================
# Risk-calendar pipeline (Plan 04 — SESS-03)
# =============================================================================

# D-10: detection threshold
RISK_SIGMA = 2.5
# Pitfall 4: spread-proxy noise floor — buckets with vanishingly small dispersion
# are skipped to avoid spurious detections from quantization or sparse data.
RISK_NOISE_FLOOR = 1e-5
# Robust scale: 1.4826 * MAD == σ for a normal distribution. Robust to up to ~50%
# contamination — required because the (hour, dow) buckets that hold our spike
# patterns ARE polluted with the spikes themselves (e.g. ~23% of the
# (hour=12, dow=Friday) bucket on a 1st-Friday-12:30 release pattern).
_MAD_TO_STD = 1.4826
# Default blackout window duration if not otherwise specified
RISK_DEFAULT_DURATION_MIN = 30


def _infer_currencies(pair: str | None) -> list[str]:
    """Split a 6-letter pair into [base, quote]. Empty list if pair is None / malformed."""
    if not pair or len(pair) != 6 or not pair.isalpha():
        return []
    return [pair[:3].upper(), pair[3:].upper()]


def detect_blackout_bars(
    bars: pd.DataFrame,
    sigma: float = RISK_SIGMA,
) -> pd.DatetimeIndex:
    """SESS-03 / D-10 — identify bars where realized range exceeds robust baseline.

    Baseline is computed per (hour-of-day, day-of-week) bucket on the bar's
    realized range (High - Low). We use median + MAD-based scale (rather than
    mean + std) because the same bucket holds the spikes we're trying to detect
    — naive moments are dragged up by the very outliers we want to flag.

    A bar is flagged iff:
      (range - median) / (1.4826 * MAD) > sigma   AND   1.4826*MAD >= NOISE_FLOOR

    Pitfall 4 noise floor (RESEARCH.md): buckets where the scaled MAD is below
    1e-5 are considered too quiet to trust — skip detection rather than emit
    false positives from quantization noise.

    Args:
        bars: DataFrame with DatetimeIndex (UTC) and Title-case OHLC columns.
        sigma: Robust z-score threshold (default 2.5 per CONTEXT D-10).

    Returns:
        DatetimeIndex of timestamps where the bar exceeds the threshold.
    """
    if bars is None or len(bars) == 0:
        return pd.DatetimeIndex([])
    if "High" not in bars.columns or "Low" not in bars.columns:
        raise ValueError("detect_blackout_bars requires Title-case High + Low columns")

    df = pd.DataFrame(index=bars.index)
    df["range"] = bars["High"] - bars["Low"]
    df["hour"] = df.index.hour
    df["dow"] = df.index.dayofweek

    grp = df.groupby(["hour", "dow"])["range"]
    df["median"] = grp.transform("median")
    abs_dev = (df["range"] - df["median"]).abs()
    df["mad"] = abs_dev.groupby([df["hour"], df["dow"]]).transform("median")
    df["scale"] = _MAD_TO_STD * df["mad"]

    valid = df["scale"] >= RISK_NOISE_FLOOR
    safe_scale = df["scale"].where(valid, np.nan)
    df["zscore"] = (df["range"] - df["median"]) / safe_scale

    detected = df[valid & (df["zscore"] > sigma)].index
    return pd.DatetimeIndex(detected)


def cluster_into_patterns(
    stamps: pd.DatetimeIndex,
    source_pair: str | None = None,
) -> list[dict[str, Any]]:
    """SESS-03 / D-11 — collapse a list of detected timestamps into parametric patterns.

    Recognizes (in order of precedence):
      - wom    — Nth weekday-of-month at HH:MM (e.g. 1st Friday 12:30 = NFP)
      - dow    — every weekday-N at HH:MM (e.g. every Wed 14:00 = FOMC fallback)
      - mom    — Nth day of every month at HH:MM (e.g. 15th at 18:00)
      - dates  — explicit dates fallback for the unmatched residual

    Each emitted pattern is a recurring rule (NOT a date list) so the calendar
    generalizes forward without yearly re-fitting. `affects` defaults to
    [base, quote] of source_pair if provided; downstream policy (D-13) may
    refine this to USD-only for known FOMC/NFP windows.

    Args:
        stamps: DatetimeIndex of detected blackout timestamps.
        source_pair: Optional 6-letter pair (e.g. "EURUSD") used to infer affects.

    Returns:
        List of pattern dicts. Each dict carries: pattern, time, duration_min,
        affects, source, plus pattern-specific keys (n/dow/dates).
    """
    if stamps is None or len(stamps) == 0:
        return []

    affects = _infer_currencies(source_pair)
    df = pd.DataFrame({"ts": pd.DatetimeIndex(stamps)})
    df["dow"] = df["ts"].dt.dayofweek
    df["dom"] = df["ts"].dt.day
    df["wom"] = ((df["dom"] - 1) // 7) + 1
    df["time"] = df["ts"].dt.strftime("%H:%M")

    patterns: list[dict[str, Any]] = []
    used: set[int] = set()

    # Pattern 1: wom — recurring Nth weekday-of-month at HH:MM
    # Confidence: ≥3 occurrences AND covers ≥50% of expected month-spans.
    for (wom, dow, time), grp in df.groupby(["wom", "dow", "time"]):
        if len(grp) < 3:
            continue
        span_days = max((grp["ts"].max() - grp["ts"].min()).days, 30)
        expected_months = max(span_days / 30, 1)
        if len(grp) >= max(3, expected_months * 0.5):
            patterns.append({
                "pattern": "wom",
                "n": int(wom),
                "dow": int(dow),
                "time": str(time),
                "duration_min": RISK_DEFAULT_DURATION_MIN,
                "affects": list(affects),
                "source": "empirical",
            })
            used.update(grp.index.tolist())

    # Pattern 2: dow — every-weekday recurrence at HH:MM
    remaining = df[~df.index.isin(used)]
    for (dow, time), grp in remaining.groupby(["dow", "time"]):
        if len(grp) < 4:
            continue
        span_days = max((grp["ts"].max() - grp["ts"].min()).days, 7)
        expected_weeks = max(span_days / 7, 1)
        if len(grp) >= max(4, expected_weeks * 0.5):
            patterns.append({
                "pattern": "dow",
                "dow": int(dow),
                "time": str(time),
                "duration_min": RISK_DEFAULT_DURATION_MIN,
                "affects": list(affects),
                "source": "empirical",
            })
            used.update(grp.index.tolist())

    # Pattern 3: mom — Nth day of month at HH:MM (e.g. 15th @ 18:00)
    remaining = df[~df.index.isin(used)]
    for (dom, time), grp in remaining.groupby(["dom", "time"]):
        if len(grp) < 3:
            continue
        span_days = max((grp["ts"].max() - grp["ts"].min()).days, 30)
        expected_months = max(span_days / 30, 1)
        if len(grp) >= max(3, expected_months * 0.5):
            patterns.append({
                "pattern": "mom",
                "n": int(dom),
                "time": str(time),
                "duration_min": RISK_DEFAULT_DURATION_MIN,
                "affects": list(affects),
                "source": "empirical",
            })
            used.update(grp.index.tolist())

    # Pattern 4: dates fallback — unmatched residual flagged as explicit dates.
    # Capped to keep YAML manageable; operator can review and convert manually.
    remaining = df[~df.index.isin(used)]
    if len(remaining) > 0:
        date_strs = sorted({ts.strftime("%Y-%m-%d") for ts in remaining["ts"]})[:50]
        if date_strs:
            mode_time = remaining["time"].mode()
            time_str = str(mode_time.iloc[0]) if not mode_time.empty else "00:00"
            patterns.append({
                "pattern": "dates",
                "dates": date_strs,
                "time": time_str,
                "duration_min": RISK_DEFAULT_DURATION_MIN,
                "affects": list(affects),
                "source": "empirical",
            })

    return patterns


def _blackout_key(b: dict[str, Any]) -> tuple:
    """Conflict key for blackout-merge: (pattern, time, sorted affects)."""
    return (
        b.get("pattern"),
        b.get("time"),
        tuple(sorted(b.get("affects", []) or [])),
    )


def write_risk_calendar(
    empirical_patterns: list[dict[str, Any]],
    path: Path,
) -> Path:
    """SESS-03 / D-12 — round-trip risk_calendar.yaml preserving comments + manual entries.

    Merge semantics:
      - Detection takes PRECEDENCE on (pattern, time, affects) conflict.
        An empirical entry replaces a manual entry with the same conflict key.
      - Manual entries (source: manual) without an empirical conflict are KEPT.
      - Operator comments (lines starting with '#') and structural formatting
        survive across re-runs via ruamel.yaml round-trip mode (PyYAML loses
        these — see RESEARCH Pitfall on YAML library choice).

    Args:
        empirical_patterns: list of pattern dicts as produced by cluster_into_patterns.
        path: Output path. Created with parent directories if needed.

    Returns:
        The path written.
    """
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing doc (if any) to preserve top-level comments + manual entries
    if path.exists():
        with path.open("r") as f:
            doc = yaml.load(f) or {}
    else:
        doc = {}

    existing_blackouts = list(doc.get("blackouts", []) or [])

    # Index existing manuals by conflict key
    manual_by_key: dict[tuple, dict[str, Any]] = {}
    for b in existing_blackouts:
        if (b.get("source") == "manual"):
            manual_by_key[_blackout_key(b)] = dict(b)

    empirical_keys = {_blackout_key(b) for b in empirical_patterns}

    # Merge: empirical first (precedence), then non-conflicting manuals
    merged: list[dict[str, Any]] = [dict(b) for b in empirical_patterns]
    for k, b in manual_by_key.items():
        if k not in empirical_keys:
            merged.append(b)

    # Replace value but preserve key-level comments by editing the existing
    # CommentedMap in place rather than reconstructing it.
    doc["blackouts"] = merged

    with path.open("w") as f:
        yaml.dump(doc, f)

    return path


def detect_and_write_risk_calendar(
    cache: OHLCVCache,
    pairs: list[str],
    timeframe: str,
    end_ts: pd.Timestamp,
    out_path: Path,
    sigma: float = RISK_SIGMA,
    history_years: int = 4,
) -> Path:
    """End-to-end risk-calendar pass driver — for run_temporal_analysis.py CLI use.

    Aggregates blackout detections across the supplied pairs (all using one
    shared timeframe — H1 by default per RESEARCH §"H4 confirmatory") and
    writes the merged parametric calendar.

    Each pattern's `affects` is the union of currency codes from the pairs
    that contributed detections to that pattern. Manual entries from any
    prior run survive per write_risk_calendar's merge contract.

    Args:
        cache: OHLCVCache instance.
        pairs: list of 6-letter pair codes.
        timeframe: bar timeframe to detect on (typically "H1").
        end_ts: PiT clamp — bar reads are bounded by this timestamp.
        out_path: target risk_calendar.yaml path.
        sigma: detection threshold (default 2.5).
        history_years: lookback window in years (default 4).

    Returns:
        Path written.
    """
    start_ts = end_ts - pd.DateOffset(years=history_years)
    pattern_pool: list[dict[str, Any]] = []

    for pair in pairs:
        try:
            bars = cache.get_bars(pair, timeframe, start_ts, end_ts)
        except Exception:
            continue
        if bars is None or len(bars) == 0:
            continue
        stamps = detect_blackout_bars(bars, sigma=sigma)
        if len(stamps) == 0:
            continue
        pattern_pool.extend(cluster_into_patterns(stamps, source_pair=pair))

    # Merge same-pattern entries from different pairs by unioning their affects
    by_key: dict[tuple, dict[str, Any]] = {}
    for p in pattern_pool:
        # Use a key WITHOUT affects so we union currencies across pairs
        k = (p.get("pattern"), p.get("time"),
             p.get("n"), p.get("dow"),
             tuple(p.get("dates", []) or []))
        if k in by_key:
            merged_affects = sorted(set(by_key[k]["affects"]) | set(p["affects"]))
            by_key[k]["affects"] = merged_affects
        else:
            by_key[k] = dict(p)

    return write_risk_calendar(list(by_key.values()), out_path)


# =============================================================================
# session_config.py code generator (Plan 05 — SESS-04)
# =============================================================================

import hashlib
from datetime import datetime, timezone


def _build_session_rules(
    evidence_dir: Path,
) -> dict[tuple[str, str, str], dict]:
    """Read session_performance_{pair}_{strategy}_{timeframe}.csv files and derive rules.

    Per CONTEXT D-04 + RESEARCH Pattern 6:
      - blacklisted_hours: hours where Sharpe <= SHARPE_BAD AND status != insufficient_evidence
      - blacklisted_dows:  dows  where Sharpe <= SHARPE_BAD AND status != insufficient_evidence
      - tradeable_sessions: sessions where Sharpe >= SHARPE_GOOD AND status != insufficient_evidence

    Buckets in (-0.2, 0.3) generate no rule (D-04 — neither allow nor block).
    """
    rules: dict[tuple[str, str, str], dict] = {}
    if not evidence_dir.exists():
        return rules
    for csv_path in sorted(evidence_dir.glob("session_performance_*.csv")):
        df = pd.read_csv(csv_path)
        if df.empty:
            continue
        stem = csv_path.stem.removeprefix("session_performance_")
        parts = stem.rsplit("_", 2)  # split from the right: pair_strategy_tf
        if len(parts) != 3:
            continue
        pair, strategy, timeframe = parts[0], parts[1], parts[2]

        evaluable = df[df["status"] != "insufficient_evidence"].copy()
        evaluable["sharpe"] = pd.to_numeric(evaluable["sharpe"], errors="coerce")

        blacklisted_hours = sorted({
            int(r["bucket"]) for _, r in
            evaluable[(evaluable["dim"] == "hour") &
                      (evaluable["sharpe"] <= SHARPE_BAD)].iterrows()
        })
        blacklisted_dows = sorted({
            int(r["bucket"]) for _, r in
            evaluable[(evaluable["dim"] == "dow") &
                      (evaluable["sharpe"] <= SHARPE_BAD)].iterrows()
        })
        tradeable_sessions = sorted({
            str(r["bucket"]) for _, r in
            evaluable[(evaluable["dim"] == "session") &
                      (evaluable["sharpe"] >= SHARPE_GOOD)].iterrows()
            if str(r["bucket"]) != "OFF"
        })
        if blacklisted_hours or blacklisted_dows or tradeable_sessions:
            rules[(pair, strategy, timeframe)] = {
                "blacklisted_hours":  blacklisted_hours,
                "blacklisted_dows":   blacklisted_dows,
                "tradeable_sessions": tradeable_sessions,
            }
    return rules


def _read_blackout_patterns(risk_calendar_path: Path) -> list[dict]:
    """Read risk_calendar.yaml and project to BLACKOUT_PATTERNS shape.

    Each pattern dict: pattern, time_utc=(hh,mm), duration_min, affects, source,
    plus pattern-specific fields (n, dow, day, month, dates).
    """
    if not risk_calendar_path.exists():
        return []
    from ruamel.yaml import YAML
    yaml = YAML(typ="rt")
    with risk_calendar_path.open() as f:
        data = yaml.load(f) or {}
    out: list[dict] = []
    for entry in (data.get("blackouts") or []):
        time_str = entry.get("time", "00:00")
        try:
            hh_s, mm_s = time_str.split(":")
            hh, mm = int(hh_s), int(mm_s)
        except (ValueError, AttributeError):
            hh, mm = 0, 0
        projected = {
            "pattern":      entry.get("pattern", "dates"),
            "time_utc":     (hh, mm),
            "duration_min": int(entry.get("duration_min", 30)),
            "affects":      list(entry.get("affects", []) or []),
            "source":       entry.get("source", "empirical"),
        }
        for fld in ("n", "dow", "day", "month", "dates"):
            if fld in entry:
                projected[fld] = entry[fld]
        out.append(projected)
    return out


def regenerate_session_config(
    evidence_dir: Path,
    target: Path,
    risk_calendar_path: Path | None = None,
) -> Path:
    """SESS-04 / D-08 — generate V2/v3_intelligence/session_config.py from evidence/.

    Output is a Python literal file (CONTEXT D-08) consumed by temporal_filters.py.
    Per RESEARCH Pattern 6: matches pair_config.py convention (generated data as
    Python literals so Phase 9 can import without parser dependencies).

    Args:
        evidence_dir: where session_performance_*.csv files live.
        target: path to write session_config.py (V2/v3_intelligence/session_config.py).
        risk_calendar_path: optional path to risk_calendar.yaml; defaults to
            evidence_dir / "risk_calendar.yaml".

    Returns:
        Path written.
    """
    if risk_calendar_path is None:
        risk_calendar_path = evidence_dir / "risk_calendar.yaml"

    rules = _build_session_rules(evidence_dir)
    patterns = _read_blackout_patterns(risk_calendar_path)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    h = hashlib.sha256()
    if evidence_dir.exists():
        for csv_path in sorted(evidence_dir.glob("session_performance_*.csv")):
            h.update(csv_path.read_bytes())
    if risk_calendar_path.exists():
        h.update(risk_calendar_path.read_bytes())
    source_hash = h.hexdigest()[:16] or "seed-empty"

    body: list[str] = [
        '"""GENERATED BY V2/scripts/run_temporal_analysis.py — DO NOT EDIT BY HAND.',
        "",
        "Phase 8.5 SESS-04 — emitted from .planning/phases/08.5-temporal-session-analysis/evidence/",
        "Re-generate via: cd V2 && python -m scripts.run_temporal_analysis",
        '"""',
        "from __future__ import annotations",
        "",
        f'GENERATED_AT: str = "{generated_at}"',
        f'SOURCE_HASH:  str = "{source_hash}"',
        "",
        "# Per (pair, strategy, timeframe), the set of buckets that gate entries.",
        "# blacklisted_hours / blacklisted_dows -> hard veto (Sharpe <= -0.2)",
        "# tradeable_sessions -> empirically validated as Sharpe >= 0.3",
        "SESSION_RULES: dict[tuple[str, str, str], dict] = {",
    ]
    for key, rule in sorted(rules.items()):
        pair, strat, tf = key
        body.append(f'    ({pair!r}, {strat!r}, {tf!r}): {{')
        body.append(f'        "blacklisted_hours":  {rule["blacklisted_hours"]!r},')
        body.append(f'        "blacklisted_dows":   {rule["blacklisted_dows"]!r},')
        body.append(f'        "tradeable_sessions": {rule["tradeable_sessions"]!r},')
        body.append('    },')
    body += [
        "}",
        "",
        "# Empirically detected + manually overridden recurring blackouts.",
        "# Each entry resolved at call-time by temporal_filters.is_blackout_window(ts).",
        "BLACKOUT_PATTERNS: list[dict] = [",
    ]
    for p in patterns:
        body.append(f'    {p!r},')
    body += ["]", ""]

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(body))
    return target


__all__ = [
    # Constants
    "SHARPE_GOOD", "SHARPE_BAD", "MIN_TRADES",
    "SESSION_BOUNDS_UTC", "OVERLAP_BOUNDS", "LONDON_OPEN_BOUNDS",
    "DIMS_ALWAYS", "DIMS_H1_DAILY_ONLY",
    "RENDER_KWARGS",
    "RISK_SIGMA", "RISK_NOISE_FLOOR", "RISK_DEFAULT_DURATION_MIN",
    # Public API
    "assign_session",
    "discover_active_combos",
    "discover_end_ts",
    "generate_trades",
    "bucket_trades",
    "write_combo_csv",
    "build_heatmap_mask",
    "render_combo_heatmaps",
    "detect_blackout_bars",
    "cluster_into_patterns",
    "write_risk_calendar",
    "detect_and_write_risk_calendar",
    "regenerate_session_config",
    # Re-exports for convenience
    "PitClock", "pit_active",
]
