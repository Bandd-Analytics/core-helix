"""sm_gmtoffset Python port — Phase 12 Plan 01 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md

Detects broker GMT offset in integer hours. In backtesting mode (broker_ts
None) returns 0 — Helix CSVs are already UTC-stamped per
V2/v3_intelligence/pit.py PitClock convention. In manual mode (auto_detect
False) returns params.manual_gmt directly. In auto mode computes
round((broker_ts - utc_now) / 3600).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class SMGMTOffsetParams:
    """Spec Section 3 inputs.

    Defaults align with the most common IC Markets EU configuration:
    Europe/Nicosia broker with auto-detection enabled.
    """

    auto_detect: bool = True
    manual_gmt: int = 0
    broker_iana_tz: str = "Europe/Nicosia"  # IC Markets EU default — [INFER]


def compute_sm_gmtoffset(
    params: SMGMTOffsetParams = SMGMTOffsetParams(),
    broker_ts: Optional[datetime] = None,
) -> int:
    """Per spec sm_gmtoffset.md Section 5 + Section 11 Python port.

    Args:
        params: SMGMTOffsetParams. Default = AutoDetect=True, ManualGMT=0.
        broker_ts: Broker server timestamp (naive datetime, in broker
            server local time). When None (the default — backtesting mode),
            returns 0 per Section 11 Backtester integration.

    Returns:
        Integer hours of broker offset relative to UTC (range -12..+14).
        Backtesting mode → 0. Manual mode → params.manual_gmt. Auto mode
        → round((broker_ts - utc_now) / 3600).

    Notes:
        Half-hour offsets (e.g., India IST UTC+5:30) are not supported by
        this integer-only model per spec Section 12 Uncertainty log.
    """
    if not params.auto_detect:
        return int(params.manual_gmt)
    if broker_ts is None:
        return 0
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta_seconds = (broker_ts - utc_now).total_seconds()
    return int(round(delta_seconds / 3600))


__all__ = ["SMGMTOffsetParams", "compute_sm_gmtoffset"]
