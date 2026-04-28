"""SM_IlsleyPsychLevels Python port — Phase 12 Plan 02 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md

Round-number psychological levels at 50-pip intervals (MMM-typical
convention). JPY pair edge case via is_jpy flag (3-digit pip = 0.01 vs
5-digit pip = 0.0001).

Per D-11: function-first surface; D-10 ≥1 GREEN pytest.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IlsleyPsychLevelsParams:
    """Spec Section 3 inputs.

    All values are [INFER] per spec Uncertainty log; defaults align with
    MMM-typical 50-pip / 100-pip psychological-level convention.
    """

    step_pips: int = 50          # MMM-typical psych level step
    levels_above: int = 5
    levels_below: int = 5
    # Pip math: caller toggles for *JPY pairs (3-digit) — Pitfall: pip math
    is_jpy: bool = False


def _pip_size(is_jpy: bool) -> float:
    """3-digit JPY (pip = 0.01) vs 5-digit majors (pip = 0.0001)."""
    return 0.01 if is_jpy else 0.0001


def compute_ilsley_psych_levels(
    df: pd.DataFrame,
    params: IlsleyPsychLevelsParams = IlsleyPsychLevelsParams(),
) -> pd.DataFrame:
    """SM_IlsleyPsychLevels — round-number levels at step_pips intervals.

    Per spec Section 5. Returns immediate above/below for each bar so
    callers can assess proximity. Caller-side rendering of the additional
    levels_above / levels_below lines is the MQ4/MQ5 indicator's job; the
    Python compute exposes only the immediate envelope (anchor pair).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: IlsleyPsychLevelsParams. Default 50-pip step, 5/5
            above/below, is_jpy=False.

    Returns:
        DataFrame with the input columns plus:
            psych_level_below — nearest 50-pip multiple ≤ Close
            psych_level_above — psych_level_below + step_pips × pip
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    pip = _pip_size(params.is_jpy)
    step = params.step_pips * pip

    # Floor-divide Close by step to find the nearest round-number below.
    out["psych_level_below"] = np.floor(out["Close"] / step) * step
    out["psych_level_above"] = out["psych_level_below"] + step
    return out


__all__ = [
    "IlsleyPsychLevelsParams",
    "compute_ilsley_psych_levels",
    "_pip_size",
]
