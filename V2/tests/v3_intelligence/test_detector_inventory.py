"""Phase 9 ROUT-04 prerequisite: 8/8 active pairs must have detector JSONs (CONTEXT D-19).

Today (Phase 8 carry-over): 5 detectors exist on disk under V2/data/regime/:
    USDJPY / GBPJPY / GBPAUD / GBPUSD / EURGBP

Plan 03 fits + persists the 3 missing detectors:
    GBPNZD / EURUSD / AUDNZD

Once Plan 03 lands, both tests in this file turn GREEN.

This test sources the active-pairs list from PAIR_CONFIGS.keys() rather than
a hardcoded literal (RESEARCH §8 Pitfall #3 — fit_regime_detectors.py and
backtest_hybrid.py drift independently when pairs are hardcoded).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from v3_intelligence.pair_config import PAIR_CONFIGS

# Repo-relative path to the regime detector JSON directory.
# tests/v3_intelligence/__file__ -> tests/v3_intelligence -> tests -> V2 -> data/regime
REGIME_DIR = Path(__file__).resolve().parents[2] / "data" / "regime"


def test_all_active_pairs_have_detector_json():
    """Every key in PAIR_CONFIGS must have a corresponding {PAIR}_detector.json.

    RED at scaffold time (3 missing: GBPNZD/EURUSD/AUDNZD per D-19).
    Plan 03 turns this GREEN by extending fit_regime_detectors.py to source
    ACTIVE_PAIRS from PAIR_CONFIGS.keys() (Pitfall #3) and running fits for
    the missing 3 pairs.
    """
    missing = []
    for pair in PAIR_CONFIGS.keys():
        json_path = REGIME_DIR / f"{pair}_detector.json"
        if not json_path.exists():
            missing.append(pair)
    assert not missing, (
        f"Missing detector JSONs (Plan 03 must add): {missing}. "
        f"Searched dir: {REGIME_DIR}"
    )


@pytest.mark.parametrize("pair", list(PAIR_CONFIGS.keys()))
def test_detector_variance_ordering_monotone(pair):
    """REGM-02 visible: unconditional_variances strictly increasing per detector.

    Skips pairs whose detector JSON does not yet exist (Plan 03 adds the
    missing 3); for pairs whose JSON does exist, asserts strictly increasing
    variances (no ties — REGM-02 D-08 pinning by variance rank).
    """
    from v3_intelligence.regime.persistence import load_detector
    json_path = REGIME_DIR / f"{pair}_detector.json"
    if not json_path.exists():
        pytest.skip(f"{pair} detector not yet fitted (Plan 03)")
    detector = load_detector(json_path)
    variances = [p.unconditional_variance for p in detector.garch_params]
    assert sorted(variances) == variances, (
        f"{pair}: variances NOT monotone increasing: {variances}"
    )
    assert len(set(variances)) == len(variances), (
        f"{pair}: variances have ties: {variances}"
    )
