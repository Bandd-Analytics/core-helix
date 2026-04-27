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
