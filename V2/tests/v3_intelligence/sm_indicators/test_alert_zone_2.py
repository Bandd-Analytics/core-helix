"""SM_AlertZone_2 — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md
RESEARCH Open Question #5: shares compute_alert_zone() from alert_zone_1; UPPER preset.
AlertZone_2 = UPPER zone (short setups near HOD/R1).

3 tests: zone_type default, shared-module architectural assertion, near-zone detection.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 3) turns them GREEN.
"""
from __future__ import annotations

import pytest


def test_zone_type_default_upper():
    """AlertZone_2 default zone_type is 'UPPER' per RESEARCH Open Question #5."""
    from v3_intelligence.sm_indicators.alert_zone_2 import AlertZone2Params
    assert AlertZone2Params().zone_type == "UPPER", "AlertZone_2 must default to zone_type='UPPER'"


def test_shared_module_import():
    """Architectural test: alert_zone_2.py must import compute_alert_zone from alert_zone_1.

    Per RESEARCH Open Question #5: same algorithm, different parameter presets.
    The shared-module pattern is enforced by source inspection.
    """
    import inspect
    import v3_intelligence.sm_indicators.alert_zone_2 as az2_mod
    src = inspect.getsource(az2_mod)
    assert "from .alert_zone_1 import" in src, (
        "alert_zone_2 must import compute_alert_zone from alert_zone_1 "
        "(RESEARCH Open Question #5 shared-module pattern)"
    )


def test_near_zone_alert_fires_when_price_in_upper_zone(synthetic_ohlc_uptrend):
    """UPPER zone: price above zone_center - half_width should trigger NEAR_ZONE."""
    from v3_intelligence.sm_indicators.alert_zone_2 import AlertZone2Params
    from v3_intelligence.sm_indicators.alert_zone_1 import compute_alert_zone, AlertZone1Params
    # Map AlertZone2Params to AlertZone1Params for compute call
    p2 = AlertZone2Params(
        auto_zone=False,
        zone_center=1.0950,
        zone_width_pips=500,
        zone_type="UPPER",
    )
    # AlertZone2Params is structurally identical to AlertZone1Params — can construct directly
    p1 = AlertZone1Params(
        auto_zone=p2.auto_zone,
        zone_center=p2.zone_center,
        zone_width_pips=p2.zone_width_pips,
        zone_type=p2.zone_type,
    )
    out = compute_alert_zone(synthetic_ohlc_uptrend, p1)
    near_count = (out["alert_signal"] == "NEAR_ZONE").sum()
    assert near_count > 0, "Expected NEAR_ZONE alerts for UPPER zone when price is within bounds"
