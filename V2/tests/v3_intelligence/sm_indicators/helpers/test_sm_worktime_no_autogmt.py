"""Tier 0 — sm_WorkTime_no_autogmt tests (Plan 12-01 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md
Architectural distinction (Section 8): NO sm_gmtoffset dependency by design.
"""
from __future__ import annotations

import inspect

import pandas as pd
import pytest

from v3_intelligence.sm_indicators.helpers import sm_worktime_no_autogmt as _module
from v3_intelligence.sm_indicators.helpers.sm_worktime_no_autogmt import (
    SMWorkTimeNoAutoGmtParams,
    compute_sm_worktime_no_autogmt,
)


def test_accepts_broker_gmt_input() -> None:
    """Spec Section 3: broker_gmt is the manual integer input."""
    idx = pd.DatetimeIndex(["2024-06-03 07:30:00"])
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    out = compute_sm_worktime_no_autogmt(df, SMWorkTimeNoAutoGmtParams(broker_gmt=3))
    assert "session_label" in out.columns


def test_no_sm_gmtoffset_dependency() -> None:
    """Spec Section 8 architectural distinction (D-19 grep gate):
    the module MUST NOT import or reference sm_gmtoffset.
    """
    src = inspect.getsource(_module)
    # Allow comments/docstrings to mention the absence; only forbid live imports
    # and live references in code lines.
    code_lines = [
        line for line in src.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    # Strip docstrings: a permissive heuristic — drop lines inside triple-quote
    # blocks. For this small module a simple in/out toggle is sufficient.
    in_doc = False
    code_only = []
    for line in code_lines:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Toggle if line contains the open and not a matching close
            quote = stripped[:3]
            count = stripped.count(quote)
            if count >= 2:
                continue  # one-line docstring
            in_doc = not in_doc
            continue
        if in_doc:
            continue
        code_only.append(line)
    code_str = "\n".join(code_only)
    assert "sm_gmtoffset" not in code_str, (
        "spec Section 8: no_autogmt variant must NOT import sm_gmtoffset"
    )


def test_same_shape_as_auto_variant(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Behavioral parity: output columns superset matches auto-variant output."""
    from v3_intelligence.sm_indicators.helpers.sm_worktime import compute_sm_worktime

    auto_out = compute_sm_worktime(synthetic_ohlc_uptrend)
    manual_out = compute_sm_worktime_no_autogmt(
        synthetic_ohlc_uptrend, SMWorkTimeNoAutoGmtParams(broker_gmt=0)
    )
    assert set(manual_out.columns) >= set(auto_out.columns)
    assert "session_label" in manual_out.columns


def test_returns_dataframe_not_mutated_input(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Pitfall 3 — never mutate input."""
    cols_before = list(synthetic_ohlc_uptrend.columns)
    _ = compute_sm_worktime_no_autogmt(synthetic_ohlc_uptrend)
    assert list(synthetic_ohlc_uptrend.columns) == cols_before


def test_classifies_gap_zones_with_zero_offset() -> None:
    """v2.00: with broker_gmt=0 the gap defaults match sm_WorkTime exactly."""
    idx = pd.DatetimeIndex(
        ["2024-06-03 07:15:00", "2024-06-03 13:45:00", "2024-06-03 11:00:00"]
    )
    df = pd.DataFrame(
        {"Open": [1.1] * 3, "High": [1.1] * 3, "Low": [1.1] * 3, "Close": [1.1] * 3},
        index=idx,
    )
    out = compute_sm_worktime_no_autogmt(
        df, SMWorkTimeNoAutoGmtParams(broker_gmt=0)
    )
    assert list(out["session_label"]) == ["LONDON_GAP", "NY_GAP", "LONDON"]


def test_show_gaps_off_disables_gap_labels() -> None:
    """v2.00: show_gaps=False reverts to bare ASIA/LONDON/US classification.

    07:15 GMT falls inside Asia 00:30-07:30 (last 15 min of Asia). With
    show_gaps=True it would be LONDON_GAP (07:00-08:00 wins); without
    gaps it stays ASIA.
    """
    idx = pd.DatetimeIndex(["2024-06-03 07:15:00"])
    df = pd.DataFrame(
        {"Open": [1.1], "High": [1.1], "Low": [1.1], "Close": [1.1]},
        index=idx,
    )
    with_gaps = compute_sm_worktime_no_autogmt(
        df, SMWorkTimeNoAutoGmtParams(broker_gmt=0, show_gaps=True)
    )
    without_gaps = compute_sm_worktime_no_autogmt(
        df, SMWorkTimeNoAutoGmtParams(broker_gmt=0, show_gaps=False)
    )
    assert with_gaps["session_label"].iloc[0] == "LONDON_GAP"
    assert without_gaps["session_label"].iloc[0] == "ASIA"
