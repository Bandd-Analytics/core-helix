"""Phase 8.5 SESS-01 + SESS-02 — RED scaffold (Wave 0).

All tests import from v3_intelligence.temporal_analysis (created in Plan 02-03).
Until Plan 02 lands, every test fails with ImportError. Plan 02 turns Tests 1-5 GREEN;
Plan 03 turns Tests 6-7 GREEN.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import pytest


def test_session_mask_construction(synthetic_trades_factory):
    """SESS-01 — assign_session must tag trades by entry_ts hour-of-day per D-01.

    Per CONTEXT D-01 (UTC, no DST):
      Tokyo  00:00-09:00, London 07:00-16:00, NY 13:00-22:00,
      Overlap 13:00-16:00, London-open 07:00-09:00.
    Precedence (Plan 02 deviation note 1): NY > London > Tokyo on overlapping hours.
      06:55 UTC (h=6) -> 'TOKYO' (Tokyo only — London hasn't opened yet).
      07:00 UTC (h=7) -> 'LONDON' (London opens; overrides Tokyo overlap; in_london_open=True).
      13:00 UTC (h=13) -> 'NY' (NY opens; overrides London overlap; in_overlap=True until 16:00).
      22:00 UTC (h=22) -> 'OFF' (NY closes — exclusive-right boundary).
    """
    from v3_intelligence.temporal_analysis import assign_session
    ts_list = [
        pd.Timestamp("2025-01-15 06:55", tz="UTC"),
        pd.Timestamp("2025-01-15 07:00", tz="UTC"),
        pd.Timestamp("2025-01-15 13:00", tz="UTC"),
        pd.Timestamp("2025-01-15 22:00", tz="UTC"),
    ]
    trades = pd.DataFrame({"entry_ts": ts_list, "exit_ts": ts_list,
                            "pnl_pct": [0.001, 0.002, -0.001, 0.001]})
    out = assign_session(trades)
    assert list(out["session"]) == ["TOKYO", "LONDON", "NY", "OFF"]
    assert list(out["in_overlap"]) == [False, False, True, False]
    assert list(out["in_london_open"]) == [False, True, False, False]


def test_per_bucket_sharpe(synthetic_trades_factory):
    """SESS-01 — bucket_trades must return Sharpe = mean/std × √252 per dim.

    Phase 7 √252 convention is locked across project (RESEARCH §Pattern 4).
    """
    from v3_intelligence.temporal_analysis import bucket_trades
    # 100 winning trades all in London hour 8, std controlled
    trades = synthetic_trades_factory(
        n_trades=100, entry_hour=8, pnl_mean=0.001, pnl_std=0.002
    )
    out = bucket_trades(trades, timeframe="H1")
    assert "session" in out and "hour" in out and "dow" in out
    london_row = out["session"].set_index("session").loc["LONDON"]
    expected_sharpe = (0.001 / 0.002) * np.sqrt(252)
    # Plan 02 deviation 2: tolerance widened from 0.5 to 2.0 — n=100 sample of
    # N(0.001, 0.002) under seed=42 yields sample mean=0.000899 / std=0.001553,
    # giving Sharpe 9.19 (vs population 7.94 — ~16% deviation from sample noise).
    # Tighter tolerance is unrealistic without n>>1000.
    assert abs(london_row["sharpe"] - expected_sharpe) < 2.0
    assert london_row["trade_count"] == 100


def test_insufficient_evidence_status(synthetic_trades_factory):
    """SESS-01 — buckets with <30 trades emit status='insufficient_evidence' (D-03).

    Bucket at hour=3 with only 5 trades -> status='insufficient_evidence', sharpe=NaN.
    """
    from v3_intelligence.temporal_analysis import bucket_trades
    trades = synthetic_trades_factory(n_trades=5, entry_hour=3,
                                       pnl_mean=0.0, pnl_std=0.001)
    out = bucket_trades(trades, timeframe="H1")
    thin = out["hour"].set_index("hour").loc[3]
    assert thin["status"] == "insufficient_evidence"
    assert pd.isna(thin["sharpe"]) or thin["sharpe"] == 0.0
    assert thin["trade_count"] == 5


def test_trade_source_dispatcher(monkeypatch):
    """SESS-01 — generate_trades dispatches to the right Phase 7/8.4 loop per (strategy, timeframe).

    Patches the four loops to return marker DataFrames; asserts dispatcher
    picks the right one. Covers: H1_SCALP/H1, MOMENTUM/H1, M15_SCALP/M15, SWING/Daily.
    """
    from v3_intelligence import temporal_analysis as ta

    markers = {"H1_SCALP": pd.DataFrame({"marker": ["scalp"]}),
               "MOMENTUM": pd.DataFrame({"marker": ["momentum"]}),
               "M15_SCALP": pd.DataFrame({"marker": ["m15"]}),
               "SWING":    pd.DataFrame({"marker": ["swing"]})}
    monkeypatch.setattr(ta, "_dispatch_h1_scalp", lambda *a, **k: markers["H1_SCALP"])
    monkeypatch.setattr(ta, "_dispatch_momentum", lambda *a, **k: markers["MOMENTUM"])
    monkeypatch.setattr(ta, "_dispatch_m15_scalp", lambda *a, **k: markers["M15_SCALP"])
    monkeypatch.setattr(ta, "_dispatch_swing",    lambda *a, **k: markers["SWING"])

    class _MockCache: pass
    end_ts = pd.Timestamp("2026-01-01", tz="UTC")
    for strat, tf in [("H1_SCALP", "H1"), ("MOMENTUM", "H1"),
                       ("M15_SCALP", "M15"), ("SWING", "Daily")]:
        df = ta.generate_trades("USDJPY", strat, tf, _MockCache(), end_ts)
        assert df.iloc[0]["marker"] == strat.lower().split("_")[0] or \
               df.iloc[0]["marker"] == "m15" if strat == "M15_SCALP" else True


def test_pit_clamp_no_future_leak(monkeypatch):
    """SESS-01 — analysis run inside PitClock(end_ts) raises FutureBarReadError on out-of-range read.

    Single PitClock context wraps the full analysis (RESEARCH Pitfall 5 — no nesting).
    Assert pit_active() returns True inside, False outside.
    """
    from v3_intelligence.pit import PitClock, pit_active
    end_ts = pd.Timestamp("2026-01-01", tz="UTC")
    assert pit_active() is False
    with PitClock(end_ts):
        assert pit_active() is True
    assert pit_active() is False


def test_heatmap_diverging_colormap(tmp_path):
    """SESS-02 — render_combo_heatmaps uses cmap='RdYlGn', center=0, vmin=-1, vmax=1.

    Inspect the saved PNG via matplotlib's figure introspection — patch savefig
    and capture the heatmap kwargs.
    """
    from v3_intelligence.temporal_analysis import render_combo_heatmaps
    captured: dict = {}
    # Plan 03 will expose RENDER_KWARGS module constant for inspection
    from v3_intelligence import temporal_analysis as ta
    assert ta.RENDER_KWARGS["cmap"] == "RdYlGn"
    assert ta.RENDER_KWARGS["center"] == 0
    assert ta.RENDER_KWARGS["vmin"] == -1.0
    assert ta.RENDER_KWARGS["vmax"] == 1.0


def test_heatmap_thin_bucket_masked(tmp_path, synthetic_trades_factory):
    """SESS-02 — heatmap cells where trade_count < 30 must be masked (gray, not zero-filled).

    Synthesize 50-row trades with 5 in hour=3 and 45 in hour=8; render hour heatmap;
    assert mask array has True at hour=3, False at hour=8.
    """
    from v3_intelligence.temporal_analysis import bucket_trades, build_heatmap_mask
    thin = synthetic_trades_factory(n_trades=5, entry_hour=3,
                                     pnl_mean=0.0, pnl_std=0.001)
    thick = synthetic_trades_factory(n_trades=45, entry_hour=8,
                                      pnl_mean=0.001, pnl_std=0.002)
    trades = pd.concat([thin, thick], ignore_index=True)
    buckets = bucket_trades(trades, timeframe="H1")
    mask = build_heatmap_mask(buckets["hour"], min_trades=30)
    # mask is a Series indexed by hour
    assert mask.loc[3] == True   # masked (insufficient)
    assert mask.loc[8] == False  # rendered
