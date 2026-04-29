"""SM_NewHUD — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md
D-17 Low confidence — SHAPE-ONLY tests. Verified Updates 2026-04-27 field set.

4 tests: 18-field column presence, HYADR column, Av_N periods, max_spread default.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 5) turns them GREEN.
"""
from __future__ import annotations

import pytest


def test_returns_18_field_columns(ohlcv_eurusd_h1):
    """Verified Updates 2026-04-27: 18+ HUD fields confirmed.

    Required columns (shape-only per D-17):
        ask, bid, spread_pips, hod, lod, hod_distance_pips, lod_distance_pips,
        tdr, ydr, wadr, madr, hyadr, pto, wh, wh_distance_pips, wl,
        wl_distance_pips, wr
    """
    from v3_intelligence.sm_indicators.new_hud import compute_new_hud, NewHUDParams
    out = compute_new_hud(ohlcv_eurusd_h1, NewHUDParams())
    required = {
        "ask", "bid", "spread_pips",
        "hod", "lod", "hod_distance_pips", "lod_distance_pips",
        "tdr", "ydr", "wadr", "madr", "hyadr",
        "pto",
        "wh", "wh_distance_pips", "wl", "wl_distance_pips", "wr",
    }
    missing = required - set(out.columns)
    assert not missing, f"Missing HUD field columns: {missing}"


def test_hyadr_present_per_verified_updates(ohlcv_eurusd_h1):
    """HYADR (Half-Yearly ADR) is a NEW field per Verified Updates 2026-04-27 — must be present."""
    from v3_intelligence.sm_indicators.new_hud import compute_new_hud, NewHUDParams
    out = compute_new_hud(ohlcv_eurusd_h1, NewHUDParams())
    assert "hyadr" in out.columns, "HYADR column must be present per Verified Updates 2026-04-27"


def test_av_periods_default_1_4_13_26_52():
    """Verified Updates 2026-04-27: Av_N EMA periods are (1, 4, 13, 26, 52)."""
    from v3_intelligence.sm_indicators.new_hud import NewHUDParams
    assert NewHUDParams().av_periods == (1, 4, 13, 26, 52), (
        "av_periods must be (1, 4, 13, 26, 52) per Verified Updates 2026-04-27"
    )


def test_max_spread_default_1_75():
    """Verified Updates 2026-04-27: MaxSpread=1.75 pips."""
    from v3_intelligence.sm_indicators.new_hud import NewHUDParams
    assert NewHUDParams().max_spread_pips == 1.75, "max_spread_pips must be 1.75 per Verified Updates"
