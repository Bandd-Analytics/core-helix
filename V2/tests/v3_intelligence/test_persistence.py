"""Detector JSON persistence roundtrip tests (D-11).

RED until Plan 03 lands save_detector/load_detector in
V2/v3_intelligence/regime/persistence.py (or re-exported from regime/__init__.py).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def test_save_then_load_roundtrip(synthetic_three_regime_returns, tmp_path) -> None:
    """save_detector → load_detector preserves all fitted floats within 1e-12."""
    from v3_intelligence.regime import save_detector, load_detector
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True

    out = tmp_path / "USDJPY_detector.json"
    save_detector(det, out, pair="USDJPY", data_path="synthetic", data_window="test")

    det2 = load_detector(out)
    assert det2.is_fitted is True

    # GARCH params — element-wise within 1e-12
    for a, b in zip(det.garch_params, det2.garch_params):
        for field in ("mu", "omega", "alpha", "beta"):
            assert abs(getattr(a, field) - getattr(b, field)) < 1e-12

    np.testing.assert_allclose(det.transmat_,  det2.transmat_,  atol=1e-12)
    np.testing.assert_allclose(det.startprob_, det2.startprob_, atol=1e-12)


def test_save_detector_raises_on_unfitted(tmp_path) -> None:
    """save_detector raises when the detector has not been fit."""
    from v3_intelligence.regime import save_detector
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    det = HMMGARCHRegimeDetector()
    with pytest.raises(Exception):
        save_detector(det, tmp_path / "x.json", pair="X",
                      data_path="x", data_window="x")


def test_load_detector_rejects_missing_schema_version(tmp_path) -> None:
    """load_detector raises on a JSON file with no schema_version field."""
    from v3_intelligence.regime import load_detector
    bad = tmp_path / "bad.json"
    bad.write_text('{"pair": "X"}')
    with pytest.raises(Exception):
        load_detector(bad)


def test_json_contains_variance_ordering_block(synthetic_three_regime_returns,
                                                 tmp_path) -> None:
    """REGM-02 visibility (D-11): JSON has variance_ordering block with state_labels."""
    import json
    from v3_intelligence.regime import save_detector
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True

    out = tmp_path / "X_detector.json"
    save_detector(det, out, pair="X", data_path="synthetic", data_window="test")

    blob = json.loads(out.read_text())
    assert blob["schema_version"] == 1
    assert blob["variance_ordering"]["state_labels"] == \
        ["TRENDING", "MEAN_REVERTING", "CRISIS"]
    uvs = blob["variance_ordering"]["unconditional_variances"]
    assert uvs == sorted(uvs)  # monotonically increasing (REGM-02)
