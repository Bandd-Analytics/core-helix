"""H4 provisioning tests (D-08).

RED until Plan 03 fetches H4 4yr for 8 pairs into V2/data/{PAIR}_H4_4yr.csv + bars.
H4 strategies remain OUT OF SCOPE per D-09.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]  # V2/
EIGHT_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]
H4_MIN_BAR_OK = 4_000  # 4yr × 6 H4 bars/day × 5 d/wk × 52 wk/yr ≈ 6240 — accept 4k+


@pytest.mark.parametrize("pair", EIGHT_PAIRS)
def test_h4_4yr_csv_exists(pair: str) -> None:
    """D-08: V2/data/{PAIR}_H4_4yr.csv exists for each of 8 pairs."""
    p = REPO / "data" / f"{pair}_H4_4yr.csv"
    assert p.exists(), f"Missing {p} (Plan 03 H4 fetch task)"


@pytest.mark.parametrize("pair", EIGHT_PAIRS)
def test_h4_4yr_row_count(pair: str) -> None:
    """D-08: each pair's H4 4yr CSV has at least 4000 bars."""
    p = REPO / "data" / f"{pair}_H4_4yr.csv"
    if not p.exists():
        pytest.skip(f"{p.name} not yet produced")
    df = pd.read_csv(p)
    assert len(df) >= H4_MIN_BAR_OK, \
        f"{pair}: only {len(df)} H4 bars (need >= {H4_MIN_BAR_OK})"


@pytest.mark.slow
@pytest.mark.parametrize("pair", EIGHT_PAIRS)
def test_h4_4yr_in_cache(pair: str) -> None:
    """D-08: cache holds H4 rows for each pair (timeframe='H4')."""
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("SUPABASE_DB_URL not provisioned")
    from v3_intelligence.cache import OHLCVCache
    cache = OHLCVCache()
    df = cache.get_bars(pair, "H4",
                          pd.Timestamp("2022-01-01", tz="UTC"),
                          pd.Timestamp("2026-12-31", tz="UTC"))
    assert len(df) >= H4_MIN_BAR_OK
