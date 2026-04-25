"""V2/v3_intelligence/regime/ — HMM-GARCH regime classifier subpackage (Phase 8).

Port of V1/helix/src/alpha/regime/ with two surgical changes per CONTEXT.md:
  - D-04: Viterbi banished — no viterbi.py, no predict_viterbi method.
  - D-22/D-23: RegimeState enum lives at types.py (only enum ported from the
    V1 signal_types module).

Public surface (consumed by Phase 9 router and Phase 10 live):
  - RegimeState
  - HMMGARCHRegimeDetector
  - GARCHParams, garch_emission_prob
  - bars_to_log_returns          (D-20 helper)
  - OnlineRegimeFilter           (Plan 03)
  - save_detector / load_detector (Plan 03)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .emissions import GARCHParams, garch_emission_prob
from .hmm_garch import HMMGARCHRegimeDetector
from .online_filter import OnlineRegimeFilter
from .persistence import save_detector, load_detector
from .types import RegimeState


def bars_to_log_returns(df: pd.DataFrame) -> np.ndarray:
    """Convert OHLC bars DataFrame to a 1-D log-returns ndarray.

    D-20: log(close_t / close_{t-1}); the leading NaN is dropped; dtype
    is float64.

    Accepts either ``close`` (lowercase, V1 / helper input) or ``Close``
    (Title-case, project CSV convention used by Phase 7's ``_H1_4yr.csv``
    files).

    Parameters
    ----------
    df:
        DataFrame with a ``close`` or ``Close`` column. Index is irrelevant.

    Returns
    -------
    np.ndarray
        1-D float64 array of length ``len(df) - 1`` (or shorter if NaNs
        appeared mid-series and were dropped).

    Raises
    ------
    KeyError
        If neither ``close`` nor ``Close`` is in ``df.columns``.
    """
    if "close" in df.columns:
        col = "close"
    elif "Close" in df.columns:
        col = "Close"
    else:
        raise KeyError(
            "bars_to_log_returns: DataFrame missing 'close' or 'Close' column"
        )
    series = np.log(df[col] / df[col].shift(1)).dropna()
    return series.to_numpy(dtype=np.float64)


__all__ = [
    "RegimeState",
    "GARCHParams",
    "garch_emission_prob",
    "HMMGARCHRegimeDetector",
    "OnlineRegimeFilter",
    "bars_to_log_returns",
    "save_detector",
    "load_detector",
]
