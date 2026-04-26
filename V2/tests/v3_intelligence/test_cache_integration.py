"""OHLCVCache integration tests (INFRA-01 — real Supabase).

@pytest.mark.slow — only runs with `pytest -m slow`. Requires SUPABASE_DB_URL.
RED until Plan 02 lands V2/v3_intelligence/cache.py + scripts/update_cache.py.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

pytestmark = pytest.mark.slow

TEST_PAIR = "TEST_USDJPY"
TEST_TF = "H1_TEST"
TEST_SOURCE = "test"


def _skip_if_no_db_url():
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("SUPABASE_DB_URL not provisioned (operator step)")


def test_round_trip_upsert_then_get() -> None:
    """Real Supabase: upsert N bars, get_bars returns those N bars with Title-case cols."""
    _skip_if_no_db_url()
    from v3_intelligence.cache import OHLCVCache
    cache = OHLCVCache()

    idx = pd.date_range("2099-01-01", periods=5, freq="h", tz="UTC")  # 2099 = far future, won't collide
    df = pd.DataFrame({
        "Open":   [1.0, 1.1, 1.2, 1.3, 1.4],
        "High":   [1.5, 1.6, 1.7, 1.8, 1.9],
        "Low":    [0.5, 0.6, 0.7, 0.8, 0.9],
        "Close":  [1.2, 1.3, 1.4, 1.5, 1.6],
        "Volume": [100, 110, 120, 130, 140],
    }, index=idx)

    n_inserted = cache.upsert_bars(TEST_PAIR, TEST_TF, df, source=TEST_SOURCE)
    assert n_inserted == 5

    out = cache.get_bars(TEST_PAIR, TEST_TF, idx[0], idx[-1])
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 5


def test_idempotent_upsert_second_call_zero_rows() -> None:
    """D-04: re-running upsert with same (pair, tf, ts) inserts 0 new rows."""
    _skip_if_no_db_url()
    from v3_intelligence.cache import OHLCVCache
    cache = OHLCVCache()

    idx = pd.date_range("2099-02-01", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({
        "Open": [1.0, 1.1, 1.2], "High": [1.5, 1.6, 1.7],
        "Low": [0.5, 0.6, 0.7], "Close": [1.2, 1.3, 1.4],
        "Volume": [100, 110, 120],
    }, index=idx)

    n1 = cache.upsert_bars(TEST_PAIR, TEST_TF, df, source=TEST_SOURCE)
    n2 = cache.upsert_bars(TEST_PAIR, TEST_TF, df, source=TEST_SOURCE)
    assert n1 >= 1
    assert n2 == 0


def test_update_cache_cli_idempotent_second_run() -> None:
    """D-04 mode a: two consecutive `update_cache --since auto` runs — second inserts 0."""
    _skip_if_no_db_url()
    import subprocess, sys
    cmd = [sys.executable, "-m", "scripts.update_cache",
           "--pair", TEST_PAIR, "--tf", TEST_TF, "--since", "auto"]
    r1 = subprocess.run(cmd, capture_output=True, text=True, cwd="V2")
    r2 = subprocess.run(cmd, capture_output=True, text=True, cwd="V2")
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    # Second run reports 0 new bars in stdout
    assert "0 new bars" in r2.stdout or "skip" in r2.stdout.lower()
