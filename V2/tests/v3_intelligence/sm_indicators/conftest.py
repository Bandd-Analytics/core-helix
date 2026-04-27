"""Phase 12 SM Indicators test fixtures (Plan 12-01 Wave 0).

Provides OHLCV + synthetic-bar fixtures used by Tier 0/1/2 indicator tests.

Real-data fixtures (session-scoped) read the Phase 8.4 INFRA-02 4yr H1 CSVs
from V2/data/. Synthetic fixtures generate deterministic test data for
shape / smoke / boundary tests where real-data semantics are not required.

All OHLC fixtures use Title-case column names (Open/High/Low/Close) per
Phase 8.4 D-20.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Repo path resolution: tests/v3_intelligence/sm_indicators/conftest.py
# .parents[0] = sm_indicators
# .parents[1] = v3_intelligence
# .parents[2] = tests
# .parents[3] = V2
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_ohlcv_csv(pair: str, timeframe: str = "H1", window: str = "4yr") -> pd.DataFrame:
    """Load V2/data/{PAIR}_{TF}_{WINDOW}.csv as Title-case OHLC DataFrame.

    Phase 8.4 D-20 convention: columns are Title-case (Open/High/Low/Close).
    The CSVs ship with header `Datetime,Open,High,Low,Close,Volume` already
    in Title-case; we just parse Datetime and set it as index.
    """
    path = DATA_DIR / f"{pair}_{timeframe}_{window}.csv"
    if not path.exists():
        pytest.skip(f"OHLCV fixture not present: {path}")
    df = pd.read_csv(path, parse_dates=["Datetime"])
    df = df.set_index("Datetime")
    return df


@pytest.fixture(scope="session")
def ohlcv_eurusd_h1() -> pd.DataFrame:
    """EURUSD H1 4yr OHLCV (Phase 8.4 INFRA-02)."""
    return _load_ohlcv_csv("EURUSD", "H1", "4yr")


@pytest.fixture(scope="session")
def ohlcv_usdjpy_h1() -> pd.DataFrame:
    """USDJPY H1 4yr OHLCV."""
    return _load_ohlcv_csv("USDJPY", "H1", "4yr")


@pytest.fixture(scope="session")
def ohlcv_gbpnzd_h1() -> pd.DataFrame:
    """GBPNZD H1 4yr OHLCV (INFRA-02 closure / Phase 8.4)."""
    return _load_ohlcv_csv("GBPNZD", "H1", "4yr")


@pytest.fixture(scope="session")
def synthetic_ohlc_uptrend() -> pd.DataFrame:
    """100-bar deterministic uptrend at H1 cadence starting 2024-01-01 UTC.

    Each bar advances by 0.0010 in Close; High = Close + 0.0005, Low = Close
    - 0.0005, Open = previous Close. Volume = 100. Use for shape/structure
    tests where the actual numeric profile does not matter.
    """
    n = 100
    idx = pd.date_range("2024-01-01 00:00:00", periods=n, freq="h")
    close = 1.0500 + np.arange(n) * 0.0010
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = close + 0.0005
    low = close - 0.0005
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 100},
        index=idx,
    )


@pytest.fixture(scope="session")
def synthetic_doji() -> pd.DataFrame:
    """100-bar series with Open == Close (doji candles), narrow High-Low.

    Used by SM_BPCT shape test (Plan 12-02) and any candle-pattern indicator
    that needs a deterministic non-trending series. H1 cadence, starts
    2024-01-01.
    """
    n = 100
    idx = pd.date_range("2024-01-01 00:00:00", periods=n, freq="h")
    mid = 1.1000
    return pd.DataFrame(
        {
            "Open": np.full(n, mid),
            "High": np.full(n, mid + 0.0002),
            "Low": np.full(n, mid - 0.0002),
            "Close": np.full(n, mid),
            "Volume": 50,
        },
        index=idx,
    )
