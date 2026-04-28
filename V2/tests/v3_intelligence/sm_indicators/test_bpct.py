"""Tier 1 — SM_BPCT tests (Plan 12-02 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md
D-17 Low confidence — implementation per Verified Updates 2026-04-27 mini-HUD
interpretation, NOT spec body's pressure-tracker hypothesis (Pitfall 10).

Tests are SHAPE-ONLY per D-17 — they assert the algorithm runs and produces
the expected mini-HUD column shape, NOT that it matches the original .ex4
(unobservable). Built ⚠ marker for SM_BPCT.
"""
from __future__ import annotations

import pandas as pd
import pytest

from v3_intelligence.sm_indicators.bpct import BPCTParams, compute_bpct


def test_returns_mini_hud_columns(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Verified Updates mini-HUD shape: hod / lod / hod_distance_pips /
    lod_distance_pips / spread_pips columns."""
    out = compute_bpct(synthetic_ohlc_uptrend)
    for col in (
        "hod", "lod", "hod_distance_pips", "lod_distance_pips", "spread_pips",
    ):
        assert col in out.columns, f"missing mini-HUD column: {col}"


def test_distance_from_extreme_default_12_pips() -> None:
    """Verified Updates: Distance_From_Extreme=12.0 (pip threshold for
    'at extreme' coloring)."""
    assert BPCTParams().distance_from_extreme == 12.0


def test_hod_lod_alert_default_false() -> None:
    """Verified Updates: HOD_LOD_Alert=false (alerts opt-in)."""
    assert BPCTParams().hod_lod_alert is False


def test_pips_to_hod_lod_for_alert_default_5() -> None:
    """Verified Updates: Pips_To_HOD_LOD_For_Alert=5.0."""
    assert BPCTParams().pips_to_hod_lod_for_alert == 5.0


def test_corner_default_right_top() -> None:
    """Verified Updates: Corner_of_Chart=RIGHT_TOP."""
    assert BPCTParams().corner == "RIGHT_TOP"


def test_alert_signal_column_when_alert_enabled(
    synthetic_ohlc_uptrend: pd.DataFrame,
) -> None:
    """Mini-HUD alert signal column populated when hod_lod_alert=True (D-12
    log-only — no email/push from Python)."""
    params = BPCTParams(hod_lod_alert=True)
    out = compute_bpct(synthetic_ohlc_uptrend, params)
    assert "alert_signal" in out.columns
    # All rows must have a string label (NEAR_HOD / NEAR_LOD / NONE)
    assert out["alert_signal"].notna().all()
