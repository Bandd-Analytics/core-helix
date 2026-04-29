"""SM_PivotPoints — Tier 2 composite indicator tests (Phase 12 Plan 03 Wave 0 RED → Wave 1 GREEN).

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md
Primary formulas: standard floor pivots + MMM Book pp. 42-43 M1-M4 mid-pivots.

4 algebraic invariant tests per spec Section 10.

TDD contract: Wave 0 all fail with ModuleNotFoundError or AttributeError.
Wave 1 (Task 2) turns them GREEN.
"""
from __future__ import annotations

import pytest


def test_returns_pivot_columns(ohlcv_eurusd_h1):
    """Output DataFrame must contain all standard + MMM mid-pivot columns."""
    from v3_intelligence.sm_indicators.pivot_points import compute_pivot_points, PivotPointsParams
    out = compute_pivot_points(ohlcv_eurusd_h1, PivotPointsParams())
    required = {"pp", "r1", "r2", "r3", "s1", "s2", "s3", "m1", "m2", "m3", "m4"}
    missing = required - set(out.columns)
    assert not missing, f"Missing pivot columns: {missing}"


def test_pivot_invariant_pp_equals_h_l_c_div_3(ohlcv_eurusd_h1):
    """PP[i] == (prior_high + prior_low + prior_close) / 3.

    Per spec Section 5 standard formula. Uses shift(1) to access prior bar.
    """
    from v3_intelligence.sm_indicators.pivot_points import compute_pivot_points, PivotPointsParams
    out = compute_pivot_points(ohlcv_eurusd_h1, PivotPointsParams())
    # Check on a valid (non-NaN) range
    sample = out.dropna(subset=["pp"]).iloc[5:20]
    prior_h = ohlcv_eurusd_h1["High"].shift(1).loc[sample.index]
    prior_l = ohlcv_eurusd_h1["Low"].shift(1).loc[sample.index]
    prior_c = ohlcv_eurusd_h1["Close"].shift(1).loc[sample.index]
    expected_pp = (prior_h + prior_l + prior_c) / 3.0
    import pandas as pd
    pd.testing.assert_series_equal(
        sample["pp"].reset_index(drop=True),
        expected_pp.reset_index(drop=True),
        check_names=False,
        rtol=1e-9,
    )


def test_r1_invariant(ohlcv_eurusd_h1):
    """R1 == 2*PP - prior_low (spec Section 5 standard formula)."""
    from v3_intelligence.sm_indicators.pivot_points import compute_pivot_points, PivotPointsParams
    out = compute_pivot_points(ohlcv_eurusd_h1, PivotPointsParams())
    sample = out.dropna(subset=["r1", "pp"]).iloc[5:20]
    prior_l = ohlcv_eurusd_h1["Low"].shift(1).loc[sample.index]
    expected_r1 = 2.0 * sample["pp"] - prior_l
    import pandas as pd
    pd.testing.assert_series_equal(
        sample["r1"].reset_index(drop=True),
        expected_r1.reset_index(drop=True),
        check_names=False,
        rtol=1e-9,
    )


def test_m_pivots_are_midpoints(ohlcv_eurusd_h1):
    """MMM Book pp. 42-43: M1=(S2+S1)/2, M2=(S1+PP)/2, M3=(PP+R1)/2, M4=(R1+R2)/2."""
    from v3_intelligence.sm_indicators.pivot_points import compute_pivot_points, PivotPointsParams
    out = compute_pivot_points(ohlcv_eurusd_h1, PivotPointsParams())
    sample = out.dropna(subset=["m1", "m2", "m3", "m4"]).iloc[5:20]

    import numpy as np
    assert np.allclose(sample["m1"], (sample["s2"] + sample["s1"]) / 2.0), "M1 = (S2+S1)/2 failed"
    assert np.allclose(sample["m2"], (sample["s1"] + sample["pp"]) / 2.0), "M2 = (S1+PP)/2 failed"
    assert np.allclose(sample["m3"], (sample["pp"] + sample["r1"]) / 2.0), "M3 = (PP+R1)/2 failed"
    assert np.allclose(sample["m4"], (sample["r1"] + sample["r2"]) / 2.0), "M4 = (R1+R2)/2 failed"
