"""GARCHParams + garch_emission_prob tests.

RED until Plan 02 lands V2/v3_intelligence/regime/emissions.py.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest


def test_garch_params_is_stationary_true_when_alpha_plus_beta_lt_one() -> None:
    from v3_intelligence.regime.emissions import GARCHParams
    p = GARCHParams(mu=0.0, omega=1e-7, alpha=0.05, beta=0.90)
    assert p.is_stationary is True


def test_garch_params_is_stationary_false_when_sum_ge_one() -> None:
    from v3_intelligence.regime.emissions import GARCHParams
    p = GARCHParams(mu=0.0, omega=1e-7, alpha=0.5, beta=0.5)
    assert p.is_stationary is False


def test_unconditional_variance_formula() -> None:
    """uv = omega / (1 - alpha - beta)."""
    from v3_intelligence.regime.emissions import GARCHParams
    p = GARCHParams(mu=0.0, omega=1e-7, alpha=0.05, beta=0.90)
    assert p.unconditional_variance == pytest.approx(1e-7 / (1 - 0.05 - 0.90))


def test_garch_params_is_frozen() -> None:
    """Frozen dataclass — assignment raises FrozenInstanceError."""
    from v3_intelligence.regime.emissions import GARCHParams
    p = GARCHParams(mu=0.0, omega=1e-7, alpha=0.05, beta=0.90)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.mu = 1.0


def test_garch_emission_prob_shape_and_finite() -> None:
    """garch_emission_prob returns log-probs shape (T,) all finite."""
    from v3_intelligence.regime.emissions import GARCHParams, garch_emission_prob
    p = GARCHParams(mu=0.0, omega=1e-7, alpha=0.05, beta=0.90)
    rng = np.random.default_rng(0)
    returns = rng.normal(0, 1e-3, 200)
    log_probs = garch_emission_prob(returns, p)
    assert log_probs.shape == (200,)
    assert np.all(np.isfinite(log_probs))
