"""bars_to_log_returns helper tests (D-20).

RED until Plan 02 adds bars_to_log_returns to v3_intelligence/regime/__init__.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _bars(n: int = 50, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    close = 100 + np.cumsum(rng.normal(0, 0.1, n))
    return pd.DataFrame({"close": close}, index=idx)


def test_returns_ndarray_dtype_float64() -> None:
    from v3_intelligence.regime import bars_to_log_returns
    df = _bars(50)
    out = bars_to_log_returns(df)
    assert isinstance(out, np.ndarray)
    assert out.dtype == np.float64


def test_returns_length_is_input_minus_one() -> None:
    """log_return = log(c_t / c_{t-1}); length is len(df) - 1."""
    from v3_intelligence.regime import bars_to_log_returns
    df = _bars(100)
    out = bars_to_log_returns(df)
    assert len(out) == 99


def test_drops_nan() -> None:
    """The first log-return is NaN (no prior close); helper drops it."""
    from v3_intelligence.regime import bars_to_log_returns
    df = _bars(50)
    out = bars_to_log_returns(df)
    assert not np.any(np.isnan(out))


def test_missing_close_column_raises() -> None:
    """Input must have a 'close' (or 'Close') column; otherwise raise."""
    from v3_intelligence.regime import bars_to_log_returns
    bad = pd.DataFrame({"price": [1.0, 1.1, 1.2]},
                       index=pd.date_range("2024-01-01", periods=3, freq="h"))
    with pytest.raises(Exception):
        bars_to_log_returns(bad)
