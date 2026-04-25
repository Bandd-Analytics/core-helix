"""OnlineRegimeFilter tests (REGM-01 behavioral, D-21).

RED until Plan 03 lands V2/v3_intelligence/regime/online_filter.py.
"""
from __future__ import annotations

import numpy as np
import pytest


def test_constructor_raises_on_unfitted_detector() -> None:
    """OnlineRegimeFilter raises if constructed with an unfitted detector."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter
    det = HMMGARCHRegimeDetector(random_state=0)
    # Not fit yet
    with pytest.raises(Exception):
        OnlineRegimeFilter(det)


def test_update_returns_state_conf(synthetic_three_regime_returns) -> None:
    """D-21: update() returns (RegimeState, float) with conf in [0, 1]."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter
    from v3_intelligence.regime.types import RegimeState

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    flt = OnlineRegimeFilter(det)

    state, conf = flt.update(float(returns[0]))
    assert isinstance(state, RegimeState)
    assert isinstance(conf, float)
    assert 0.0 <= conf <= 1.0


def test_state_probs_shape_and_sum(synthetic_three_regime_returns) -> None:
    """state_probs property returns shape (3,) summing to 1.0 ± 1e-9."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    flt = OnlineRegimeFilter(det)
    flt.update(float(returns[0]))
    flt.update(float(returns[1]))

    probs = flt.state_probs
    assert probs.shape == (3,)
    assert abs(probs.sum() - 1.0) < 1e-9


def test_reset_restores_startprob(synthetic_three_regime_returns) -> None:
    """reset() restores state_probs == detector.startprob_."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    flt = OnlineRegimeFilter(det)
    for r in returns[:50]:
        flt.update(float(r))
    flt.reset()
    np.testing.assert_allclose(flt.state_probs, det.startprob_, rtol=1e-12)


def test_underflow_path_keeps_probs_valid(synthetic_three_regime_returns) -> None:
    """Underflow trigger: extremely large return magnitude triggers
    _log_space_forward fallback; probs must still sum to 1 ± 1e-9."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    flt = OnlineRegimeFilter(det)
    # Extreme value that drives Gaussian density to ~0 in normal space
    flt.update(1e6)
    probs = flt.state_probs
    assert abs(probs.sum() - 1.0) < 1e-9
    assert np.all(np.isfinite(probs))
