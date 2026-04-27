"""Tier 0 — sm_gmtoffset tests (Plan 12-01 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from v3_intelligence.sm_indicators.helpers.sm_gmtoffset import (
    SMGMTOffsetParams,
    compute_sm_gmtoffset,
)


def test_returns_zero_when_broker_ts_none() -> None:
    """Backtesting-mode contract per spec Section 11 Backtester integration:
    when broker_ts is None, the offset is always 0 (UTC timestamps).
    """
    result = compute_sm_gmtoffset(SMGMTOffsetParams(), broker_ts=None)
    assert result == 0


def test_returns_manual_when_auto_detect_false() -> None:
    """Spec Section 5 step 1a: AutoDetect=False → return ManualGMT directly."""
    params = SMGMTOffsetParams(auto_detect=False, manual_gmt=3)
    result = compute_sm_gmtoffset(params, broker_ts=None)
    assert result == 3


def test_returns_int_hours_from_broker_delta() -> None:
    """Spec Section 5 step 1b: AutoDetect=True with broker_ts +3h ahead of UTC
    → round((broker - utc) / 3600) == 3.
    """
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    broker_ts = utc_now + timedelta(hours=3)
    result = compute_sm_gmtoffset(SMGMTOffsetParams(auto_detect=True), broker_ts=broker_ts)
    assert result == 3


def test_negative_offset_supported() -> None:
    """Spec valid range -12..+14: NZ-server-style negative offsets work."""
    params = SMGMTOffsetParams(auto_detect=False, manual_gmt=-5)
    result = compute_sm_gmtoffset(params, broker_ts=None)
    assert result == -5


def test_returns_int_type() -> None:
    """Spec Outputs section: GlobalVariable holds integer hours."""
    result = compute_sm_gmtoffset(SMGMTOffsetParams(), broker_ts=None)
    assert isinstance(result, int)
