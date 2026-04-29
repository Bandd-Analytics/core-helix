"""SM_AlertZone_1 — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md
RESEARCH Open Question #5: shared algorithm with AlertZone_2; different parameter defaults.
AlertZone_1 = LOWER zone (long setups near LOD/S1).

3 tests: column check, zone_type default, in-zone detection.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 3) turns them GREEN.
"""
from __future__ import annotations

import pytest


def test_zone_type_default_lower():
    """AlertZone_1 default zone_type is 'LOWER' per RESEARCH Open Question #5."""
    from v3_intelligence.sm_indicators.alert_zone_1 import AlertZone1Params
    assert AlertZone1Params().zone_type == "LOWER", "AlertZone_1 must default to zone_type='LOWER'"


def test_returns_alert_columns(ohlcv_eurusd_h1):
    """compute_alert_zone() must return alert_signal + zone_upper + zone_lower columns."""
    from v3_intelligence.sm_indicators.alert_zone_1 import compute_alert_zone, AlertZone1Params
    out = compute_alert_zone(ohlcv_eurusd_h1, AlertZone1Params())
    for col in ("alert_signal", "zone_upper", "zone_lower"):
        assert col in out.columns, f"Missing column: {col}"


def test_near_zone_alert_fires_when_price_in_zone(synthetic_ohlc_uptrend):
    """When price is within the zone bounds, alert_signal should be 'NEAR_ZONE' on at least some bars."""
    from v3_intelligence.sm_indicators.alert_zone_1 import compute_alert_zone, AlertZone1Params
    # Use auto_zone=False with a zone centered around the uptrend's approximate price
    # Uptrend starts at 1.0500 and goes up by 0.001/bar over 100 bars → 1.1490 at end
    # Zone from 1.07 to 1.12 should catch several bars
    params = AlertZone1Params(
        auto_zone=False,
        zone_center=1.0950,
        zone_width_pips=500,  # 500 pips = 0.05 price units
        zone_type="LOWER",
    )
    out = compute_alert_zone(synthetic_ohlc_uptrend, params)
    near_count = (out["alert_signal"] == "NEAR_ZONE").sum()
    assert near_count > 0, "Expected NEAR_ZONE alerts when price is within configured zone"
