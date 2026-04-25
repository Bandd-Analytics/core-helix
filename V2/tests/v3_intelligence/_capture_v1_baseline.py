"""One-shot V1 baseline generator for Phase 8 D-16 parity tests.

Run ONCE manually to capture V1 outputs into parity_baseline.npz:
    cd <repo-root>
    PYTHONPATH=V1/helix python3 V2/tests/v3_intelligence/_capture_v1_baseline.py

V1 modules use absolute imports rooted at ``src.*`` (see V1/helix/src/alpha/__init__.py),
so PYTHONPATH must point at ``V1/helix`` (not ``V1/helix/src``).

The .npz is then committed; CI never re-runs this script.
Captured arrays:
  - garch_params  shape (n_states, 4) float64  [mu, omega, alpha, beta] per state
  - transmat      shape (n_states, n_states) float64
  - startprob     shape (n_states,) float64
  - online_states shape (T,) int64  — OnlineRegimeFilter state sequence
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# V1 imports (caller must set PYTHONPATH=V1/helix so 'src.*' resolves)
from src.alpha.regime.hmm_garch import HMMGARCHRegimeDetector
from src.alpha.regime.online_filter import OnlineRegimeFilter

OUT_PATH = Path(__file__).resolve().parent / "parity_baseline.npz"


def _synthetic_returns():
    rng = np.random.default_rng(42)
    T = 1000
    state_seq = np.concatenate([
        np.zeros(600, dtype=int),
        np.ones(300, dtype=int),
        np.full(100, 2, dtype=int),
    ])
    rng.shuffle(state_seq)
    mus    = np.array([1e-5,  0.0,    -2e-5])
    sigmas = np.array([1e-3,  3e-3,   8e-3])
    return rng.normal(loc=mus[state_seq], scale=sigmas[state_seq])


def main() -> int:
    returns = _synthetic_returns()

    det = HMMGARCHRegimeDetector(random_state=0)
    ok = det.fit(returns)
    if not ok:
        print("V1 detector.fit() returned False — cannot capture baseline",
              file=sys.stderr)
        return 1

    garch = np.array(
        [[p.mu, p.omega, p.alpha, p.beta] for p in det.garch_params],
        dtype=np.float64,
    )
    transmat  = np.asarray(det.transmat_,  dtype=np.float64)
    startprob = np.asarray(det.startprob_, dtype=np.float64)

    flt = OnlineRegimeFilter(det)
    online_states = np.empty(len(returns), dtype=np.int64)
    for i, r in enumerate(returns):
        state, _conf = flt.update(float(r))
        online_states[i] = int(state)

    np.savez(
        OUT_PATH,
        garch_params=garch,
        transmat=transmat,
        startprob=startprob,
        online_states=online_states,
    )
    print(f"Wrote {OUT_PATH}: garch={garch.shape}, transmat={transmat.shape},"
          f" startprob={startprob.shape}, online_states={online_states.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
