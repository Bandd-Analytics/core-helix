"""GBPNZD H1 4yr parity tests (INFRA-02 / D-05, D-06, D-07).

RED until Plan 03 lands V2/data/GBPNZD_H1_4yr.csv + bars rows in Supabase.
The slow-marked tests hit Supabase; the file-existence test runs in fast mode.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]  # V2/
GBPNZD_CSV = REPO / "data" / "GBPNZD_H1_4yr.csv"
MIN_BAR_OK = 15_000          # download_history.py constant
EXPECTED_LOW_BAR_WARN = 17_000  # 4yr × 24 hr/d × ~5 d/wk × 52 wk/yr ≈ 24960 — accept 17k+


def test_gbpnzd_h1_4yr_csv_exists() -> None:
    """INFRA-02 / D-06: V2/data/GBPNZD_H1_4yr.csv exists."""
    assert GBPNZD_CSV.exists(), f"Missing {GBPNZD_CSV} (Plan 03 GBPNZD MT5 GUI export task)"


def test_gbpnzd_h1_4yr_row_count() -> None:
    """INFRA-02: at least MIN_BAR_OK bars (15k); ideally >= 17k for full 4yr."""
    if not GBPNZD_CSV.exists():
        pytest.skip("CSV not yet produced (Plan 03 task)")
    df = pd.read_csv(GBPNZD_CSV)
    assert len(df) >= MIN_BAR_OK, f"Only {len(df)} bars (need >= {MIN_BAR_OK})"


def test_gbpnzd_h1_4yr_titlecase_columns() -> None:
    """D-03 / D-06: CSV columns match other 7 pairs' Title-case convention."""
    if not GBPNZD_CSV.exists():
        pytest.skip("CSV not yet produced")
    df = pd.read_csv(GBPNZD_CSV)
    required = {"Open", "High", "Low", "Close"}
    assert required.issubset(set(df.columns)), \
        f"Missing Title-case columns; have {list(df.columns)}"


def test_gbpnzd_h1_4yr_date_range_at_least_4yr() -> None:
    """INFRA-02: date span covers ≥ 4 years (matches other 7 pairs' 4yr window)."""
    if not GBPNZD_CSV.exists():
        pytest.skip("CSV not yet produced")
    df = pd.read_csv(GBPNZD_CSV, parse_dates=[0], index_col=0)
    span = df.index.max() - df.index.min()
    assert span >= pd.Timedelta(days=4 * 365 - 30), \
        f"Span {span} < 4yr"


@pytest.mark.slow
def test_gbpnzd_in_supabase_bars_table() -> None:
    """INFRA-02 / D-06: cache holds same data — Supabase row count >= MIN_BAR_OK."""
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("SUPABASE_DB_URL not provisioned")
    from v3_intelligence.cache import OHLCVCache
    cache = OHLCVCache()
    df = cache.get_bars("GBPNZD", "H1",
                          pd.Timestamp("2022-01-01", tz="UTC"),
                          pd.Timestamp("2026-12-31", tz="UTC"))
    assert len(df) >= MIN_BAR_OK


def test_pair_config_gbpnzd_present() -> None:
    """D-07 sanity: pair_config has a GBPNZD entry (already true; matrix may flip flags)."""
    from v3_intelligence.pair_config import get_pair_config
    cfg = get_pair_config("GBPNZD")
    assert cfg is not None
    assert cfg.symbol == "GBPNZD"
