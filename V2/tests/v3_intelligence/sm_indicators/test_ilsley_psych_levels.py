"""Tier 1 — SM_IlsleyPsychLevels tests (Plan 12-02 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md
Round-number psychological levels at 50-pip intervals; JPY pair edge case
via is_jpy flag (Pitfall: pip math 3-digit vs 5-digit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from v3_intelligence.sm_indicators.ilsley_psych_levels import (
    IlsleyPsychLevelsParams,
    compute_ilsley_psych_levels,
)


def test_returns_psych_level_columns(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """Spec Section 4 Outputs: result has psych_level_above /
    psych_level_below columns."""
    out = compute_ilsley_psych_levels(synthetic_ohlc_uptrend)
    assert "psych_level_above" in out.columns
    assert "psych_level_below" in out.columns


def test_psych_levels_are_50_pip_multiples(
    synthetic_ohlc_uptrend: pd.DataFrame,
) -> None:
    """Spec Section 5 + Section 10 test case 1: psych_level_below is a
    50-pip multiple (every value modulo 0.0050 = 0 within float roundoff).
    """
    out = compute_ilsley_psych_levels(synthetic_ohlc_uptrend)
    step = 0.0050  # 50 pips on a 5-digit major
    below = out["psych_level_below"].dropna()
    # Round to step then compare — fp noise tolerance
    rounded = (below / step).round() * step
    assert np.allclose(below.values, rounded.values, atol=1e-9), (
        "psych_level_below values not aligned to 50-pip grid"
    )


def test_above_minus_below_equals_step(
    synthetic_ohlc_uptrend: pd.DataFrame,
) -> None:
    """Algebraic invariant: above level = below level + step_pips * pip."""
    out = compute_ilsley_psych_levels(synthetic_ohlc_uptrend)
    diff = out["psych_level_above"] - out["psych_level_below"]
    assert np.allclose(diff.values, 0.0050, atol=1e-9)


def test_jpy_pair_uses_3digit_pip(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """JPY pair edge case: is_jpy=True uses 0.01 pip size, so 50-pip step
    = 0.50 (not 0.0050).
    """
    # Construct a synthetic JPY-priced frame
    df = synthetic_ohlc_uptrend.copy() * 100  # promote 1.05xx → 105.xx
    params = IlsleyPsychLevelsParams(is_jpy=True)
    out = compute_ilsley_psych_levels(df, params)
    diff = out["psych_level_above"] - out["psych_level_below"]
    assert np.allclose(diff.values, 0.50, atol=1e-9), (
        "JPY pair must use 0.50 step (not 0.0050)"
    )


def test_default_levels_above_below() -> None:
    """Defaults: 5 above, 5 below (per spec Section 3 [INFER] / Plan
    [INFER] selection)."""
    p = IlsleyPsychLevelsParams()
    assert p.levels_above == 5
    assert p.levels_below == 5
    assert p.step_pips == 50
