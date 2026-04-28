"""Tier 0 — sm_WorkTime tests (Plan 12-01 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md
Session boundaries from MMM Book p. 8:
    Asia    00:30–07:00 GMT
    London  07:30–13:00 GMT
    US      13:30–20:30 GMT (default end may be 20:00 hour input + 30m end)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from v3_intelligence.sm_indicators.helpers.sm_worktime import (
    SMWorkTimeParams,
    compute_sm_worktime,
)


def test_returns_session_label_column(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Spec Section 4 Outputs: result has a session_label column."""
    out = compute_sm_worktime(synthetic_ohlc_uptrend)
    assert "session_label" in out.columns


def test_classifies_london_open() -> None:
    """v2.00: 07:30 GMT falls inside LONDON_GAP (07:00-08:00) which wins
    over LONDON at the changeover overlap. With show_gaps=False, falls
    through to LONDON.
    """
    idx = pd.DatetimeIndex(["2024-06-03 07:30:00"])  # Mon at 07:30 GMT
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert out["session_label"].iloc[0] == "LONDON_GAP"

    out_no_gaps = compute_sm_worktime(
        df, SMWorkTimeParams(show_gaps=False)
    )
    assert out_no_gaps["session_label"].iloc[0] == "LONDON"


def test_classifies_london_gap_zone() -> None:
    """v2.00: LONDON_GAP covers 07:00-08:00 GMT (±30m around London open)."""
    idx = pd.DatetimeIndex(
        ["2024-06-03 07:00:00", "2024-06-03 07:45:00", "2024-06-03 08:00:00"]
    )
    df = pd.DataFrame(
        {"Open": [1.1] * 3, "High": [1.1] * 3, "Low": [1.1] * 3, "Close": [1.1] * 3},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert list(out["session_label"]) == ["LONDON_GAP", "LONDON_GAP", "LONDON"]


def test_classifies_ny_gap_zone() -> None:
    """v2.00: NY_GAP covers 13:00-14:00 GMT (±30m around US open)."""
    idx = pd.DatetimeIndex(
        ["2024-06-03 13:00:00", "2024-06-03 13:45:00", "2024-06-03 14:00:00"]
    )
    df = pd.DataFrame(
        {"Open": [1.1] * 3, "High": [1.1] * 3, "Low": [1.1] * 3, "Close": [1.1] * 3},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert list(out["session_label"]) == ["NY_GAP", "NY_GAP", "US"]


def test_asia_range_optional_columns() -> None:
    """v2.00: show_asia_range=True attaches per-day asia_range_high/low/pips."""
    idx = pd.DatetimeIndex([
        "2024-06-03 02:00:00",  # Asia
        "2024-06-03 04:00:00",  # Asia
        "2024-06-03 09:00:00",  # London
    ])
    df = pd.DataFrame(
        {
            "open": [1.10, 1.12, 1.13],
            "high": [1.11, 1.15, 1.14],
            "low":  [1.09, 1.10, 1.12],
            "close":[1.105, 1.13, 1.135],
        },
        index=idx,
    )
    out = compute_sm_worktime(df, SMWorkTimeParams(show_asia_range=True))
    assert "asia_range_high" in out.columns
    assert "asia_range_low" in out.columns
    assert out["asia_range_high"].iloc[0] == pytest.approx(1.15)
    assert out["asia_range_low"].iloc[0] == pytest.approx(1.09)


def test_classifies_asia_session() -> None:
    """Spec Section 5: 02:00 GMT is inside Asia 00:30-07:30 window."""
    idx = pd.DatetimeIndex(["2024-06-03 02:00:00"])
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert out["session_label"].iloc[0] == "ASIA"


def test_classifies_us_session() -> None:
    """Spec Section 5: 14:00 GMT is inside US 13:30-22:00 window."""
    idx = pd.DatetimeIndex(["2024-06-03 14:00:00"])
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert out["session_label"].iloc[0] == "US"


def test_offhours_label_outside_sessions() -> None:
    """Spec Section 5: bars outside all session windows → OFFHOURS."""
    # 23:30 GMT — after US session end (22:00) and before next-day Asia (00:30)
    idx = pd.DatetimeIndex(["2024-06-03 23:30:00"])
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    out = compute_sm_worktime(df)
    assert out["session_label"].iloc[0] == "OFFHOURS"


def test_returns_dataframe_not_mutated_input(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """RESEARCH Pitfall 3: NEVER mutate input."""
    cols_before = list(synthetic_ohlc_uptrend.columns)
    _ = compute_sm_worktime(synthetic_ohlc_uptrend)
    assert list(synthetic_ohlc_uptrend.columns) == cols_before
    assert "session_label" not in synthetic_ohlc_uptrend.columns
