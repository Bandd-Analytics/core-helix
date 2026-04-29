"""SM_AlertZone_2 Python port — Phase 12 Plan 03 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md
RESEARCH Open Question #5: same algorithm as AlertZone_1; UPPER zone preset.

AlertZone_2 — UPPER zone preset (short setups near HOD/R1).
Same algorithm as SM_AlertZone_1. The binary delta between the two .ex4
files is only 148 bytes — hypothesized as same algorithm with different
default parameter values (zone_type="UPPER" vs "LOWER").

This module REUSES compute_alert_zone() from alert_zone_1.py:
    from .alert_zone_1 import compute_alert_zone

AlertZone_2 consumers should:
    1. Instantiate AlertZone2Params (zone_type="UPPER" default)
    2. Call compute_alert_zone() from alert_zone_1 with a mapped params object

Per D-11: function-first surface, params as frozen dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .alert_zone_1 import compute_alert_zone, AlertZone1Params  # shared algorithm


@dataclass(frozen=True)
class AlertZone2Params:
    """SM_AlertZone_2 indicator parameters (UPPER zone preset — short-setup).

    Same algorithm as AlertZone_1. Per RESEARCH Open Question #5: SM_AlertZone_1
    vs SM_AlertZone_2 binary delta is 148 bytes — hypothesized as same algorithm
    with different defaults. This module reuses compute_alert_zone() from
    alert_zone_1.

    UPPER zone targets short setups near HOD/R1 (auto_zone=True tracks HOD).
    """

    zone_center: float = 0.0               # Manual zone center (auto_zone=False)
    zone_width_pips: float = 30.0          # Zone full width in pips [INFER]
    zone_type: Literal["LOWER", "UPPER"] = "UPPER"  # Only difference from AlertZone1Params default
    auto_zone: bool = True                 # Track HOD automatically
    zone_offset_pips: float = 15.0         # Strike Zone offset from HOD per MMM Book p. 55 [INFER]
    is_jpy: bool = False                   # JPY pair (pip = 0.01, not 0.0001)


def _to_zone1_params(params: AlertZone2Params) -> AlertZone1Params:
    """Map AlertZone2Params to AlertZone1Params for compute_alert_zone()."""
    return AlertZone1Params(
        zone_center=params.zone_center,
        zone_width_pips=params.zone_width_pips,
        zone_type=params.zone_type,
        auto_zone=params.auto_zone,
        zone_offset_pips=params.zone_offset_pips,
        is_jpy=params.is_jpy,
    )


__all__ = ["AlertZone2Params", "compute_alert_zone"]  # re-export compute_alert_zone
