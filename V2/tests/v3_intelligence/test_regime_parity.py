"""V1↔V2 parity tests (D-16, D-17, D-18).

Marked @pytest.mark.slow per D-17; default fast runs (-m 'not slow') skip.
RED until Plans 02/03 land the V2 detector + filter producing outputs that
match V1's baseline within tolerance.

Tolerances (D-16, RESEARCH §F.13):
  - GARCHParams (mu, omega, alpha, beta): rtol=1e-6
  - transmat_, startprob_:                rtol=1e-6
  - OnlineRegimeFilter state agreement:   ≥ 95%
"""
from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.slow


def test_garch_params_within_rtol_1e6(synthetic_three_regime_returns,
                                       v1_baseline) -> None:
    """D-16: V2 GARCHParams within rtol=1e-6 of V1 baseline."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True

    v2_garch = np.array(
        [[p.mu, p.omega, p.alpha, p.beta] for p in det.garch_params],
        dtype=np.float64,
    )
    v1_garch = v1_baseline["garch_params"]
    np.testing.assert_allclose(v2_garch, v1_garch, rtol=1e-6,
                                err_msg="V2 GARCHParams drift > rtol=1e-6 vs V1")


def test_transmat_within_rtol_1e6(synthetic_three_regime_returns,
                                    v1_baseline) -> None:
    """D-16: V2 transmat_ within rtol=1e-6 of V1 baseline."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    np.testing.assert_allclose(np.asarray(det.transmat_),
                                v1_baseline["transmat"], rtol=1e-6)


def test_startprob_within_rtol_1e6(synthetic_three_regime_returns,
                                     v1_baseline) -> None:
    """D-16: V2 startprob_ within rtol=1e-6 of V1 baseline."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    np.testing.assert_allclose(np.asarray(det.startprob_),
                                v1_baseline["startprob"], rtol=1e-6)


def test_online_state_agreement(synthetic_three_regime_returns,
                                  v1_baseline) -> None:
    """D-16: OnlineRegimeFilter state agreement ≥ 95% on synthetic returns vs V1."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    from v3_intelligence.regime.online_filter import OnlineRegimeFilter

    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    flt = OnlineRegimeFilter(det)

    v2_states = np.empty(len(returns), dtype=np.int64)
    for i, r in enumerate(returns):
        state, _ = flt.update(float(r))
        v2_states[i] = int(state)

    v1_states = v1_baseline["online_states"]
    agreement = float(np.mean(v2_states == v1_states))
    assert agreement >= 0.95, (
        f"Online state agreement {agreement:.3f} below threshold 0.95 (D-16)"
    )
