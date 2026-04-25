"""HMMGARCHRegimeDetector tests (REGM-01 structural+behavioral, REGM-02).

RED until Plan 02 lands V2/v3_intelligence/regime/hmm_garch.py and types.py.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def test_subpackage_layout() -> None:
    """REGM-01 (structural / D-01): regime subpackage exists with required files."""
    repo = Path(__file__).resolve().parents[2]
    base = repo / "v3_intelligence" / "regime"
    for name in ("__init__.py", "types.py", "emissions.py",
                 "hmm_garch.py", "online_filter.py"):
        assert (base / name).exists(), f"Missing {base / name}"
    # D-04: viterbi.py must NOT exist
    assert not (base / "viterbi.py").exists(), "viterbi.py forbidden per D-04"


def test_no_v1_imports() -> None:
    """D-12: V2 regime subpackage does not import from V1."""
    repo = Path(__file__).resolve().parents[2]
    base = repo / "v3_intelligence" / "regime"
    for py in base.glob("*.py"):
        text = py.read_text()
        assert "from src.alpha" not in text, f"{py.name} imports V1 (src.alpha.*)"
        assert "from V1" not in text, f"{py.name} imports V1"


def test_regime_state_enum_values() -> None:
    """D-22: RegimeState IntEnum values TRENDING=0, MEAN_REVERTING=1, CRISIS=2."""
    from v3_intelligence.regime.types import RegimeState
    assert int(RegimeState.TRENDING) == 0
    assert int(RegimeState.MEAN_REVERTING) == 1
    assert int(RegimeState.CRISIS) == 2


def test_regime_state_reexported_from_subpackage() -> None:
    """D-22 / D-02: from v3_intelligence.regime import RegimeState works."""
    from v3_intelligence.regime import RegimeState
    assert int(RegimeState.TRENDING) == 0


def test_fit_returns_true(synthetic_three_regime_returns) -> None:
    """REGM-01 (behavioral): detector.fit() returns True on synthetic returns."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    assert det.is_fitted is True


def test_variance_rank_pinning(synthetic_three_regime_returns) -> None:
    """REGM-02: garch_params[i].unconditional_variance is monotonically increasing."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    returns, _ = synthetic_three_regime_returns
    det = HMMGARCHRegimeDetector(random_state=0)
    assert det.fit(returns) is True
    variances = [p.unconditional_variance for p in det.garch_params]
    assert variances == sorted(variances), \
        f"variances {variances} are not monotonically increasing (REGM-02 fail)"


def test_refit_preserves_ordering(synthetic_three_regime_returns) -> None:
    """REGM-02: re-fit on perturbed returns preserves state ordering."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    returns, _ = synthetic_three_regime_returns

    det1 = HMMGARCHRegimeDetector(random_state=0)
    assert det1.fit(returns) is True
    order1 = [round(p.unconditional_variance, 12) for p in det1.garch_params]

    det2 = HMMGARCHRegimeDetector(random_state=0)
    assert det2.fit(returns + 1e-7) is True   # perturb
    order2 = [round(p.unconditional_variance, 12) for p in det2.garch_params]

    # Same monotonicity (REGM-02): both ascending
    assert order1 == sorted(order1)
    assert order2 == sorted(order2)


def test_get_regime_label() -> None:
    """REGM-01: get_regime_label maps 0→TRENDING, 1→MEAN_REVERTING, 2→CRISIS."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    det = HMMGARCHRegimeDetector()
    assert det.get_regime_label(0) == "TRENDING"
    assert det.get_regime_label(1) == "MEAN_REVERTING"
    assert det.get_regime_label(2) == "CRISIS"


def test_predict_viterbi_method_dropped() -> None:
    """D-04 / REGM-04: predict_viterbi method MUST NOT exist on the detector."""
    from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector
    assert not hasattr(HMMGARCHRegimeDetector, "predict_viterbi"), \
        "predict_viterbi must be dropped per D-04"
