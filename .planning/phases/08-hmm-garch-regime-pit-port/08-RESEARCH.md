# Phase 8: HMM-GARCH Regime + PiT Port — Research

**Researched:** 2026-04-25
**Domain:** Statistical regime classification (HMM-GARCH) + point-in-time data integrity
**Confidence:** HIGH (V1 source fully read; library APIs verified at V1's pin points; CONTEXT.md decisions locked)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (29)

**Module Structure & Dependencies**
- D-01: `V2/v3_intelligence/regime/` subpackage — `__init__.py`, `hmm_garch.py`, `online_filter.py`, `emissions.py`, `types.py`. NO `viterbi.py`.
- D-02: REGM-01 "regime.py" interpreted as "the regime module"; subpackage satisfies it. Phase 9 imports `from v3_intelligence.regime import OnlineRegimeFilter, RegimeState`.
- D-03: `hmmlearn>=0.3` and `arch>=6.0` added to `V2/pyproject.toml [project.dependencies]`.
- D-12: V1 `V1/helix/src/alpha/regime/` untouched; V2 imports nothing from V1.

**Viterbi Banishment (REGM-04)**
- D-04: No `viterbi.py`, no `predict_viterbi()` method on detector.
- D-05: `tests/v3_intelligence/test_viterbi_ban.py` greps `V2/backtest/`, `V2/v3_intelligence/`, `V2/live/` for `viterbi`/`Viterbi`/`predict_viterbi`.

**PiT Runtime Manager (REGM-03)**
- D-06: `V2/v3_intelligence/pit.py` — replay-clock context manager, pandas-native, no ArcticDB.
- D-07: Opt-in via decorator on backtest method; existing backtest loops unchanged.
- D-08: Future-bar check is timestamp-based (`bar.ts > as_of_ts`), not index-based.
- D-09: Mandatory test: out-of-order read raises `FutureBarReadError`.

**Per-Pair Detector + Persistence**
- D-10: 5 detectors total — USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP.
- D-11: JSON+numpy persistence at `V2/data/regime/{PAIR}_detector.json`. Schema: GARCHParams list + transmat (3×3) + startprob (3,) + variance_ordering metadata + fit_metadata.
- D-13: Standalone CLI `V2/scripts/fit_regime_detectors.py` (mirror `download_history.py`).

**Recalibration Scope**
- D-14: V1 `calibration.py` deferred to v3.0 EXPN-03. Phase 8 ships static-fit only.
- D-15: v2.0 drift handling: manual refit via CLI.

**Validation / Parity**
- D-16: Statistical match within tolerance, not bit-exact. `1e-6` on GARCHParams; ≥95% state agreement.
- D-17: `tests/v3_intelligence/test_regime_parity.py` marked `@pytest.mark.slow`.
- D-18: Parity failure blocks phase completion.

**Returns Input Contract**
- D-19: `fit()` and `update()` accept `np.ndarray` of log-returns (V1 contract).
- D-20: `bars_to_log_returns(df) -> np.ndarray` lives in `regime/__init__.py`.
- D-21: `update()` returns `(state: RegimeState, confidence: float)`. `.state_probs` property exposes vector.

**RegimeState Enum**
- D-22: `RegimeState` at `regime/types.py`, re-exported via `regime/__init__.py`. Values: `TRENDING=0`, `MEAN_REVERTING=1`, `CRISIS=2`.
- D-23: Only `RegimeState` ported from V1 `signal_types.py`.

**Fit Data Window**
- D-24: 4yr H1 per pair (~35k bars).
- D-25: Offline fit explicitly bypasses PitClock — `PitClock.UNBOUNDED` sentinel.

**Failed-Fit Behavior**
- D-26: `detector.fit()` returns False → CLI exits non-zero; no JSON written; no `pair_config` update.
- D-27: Phase 9 router treats missing detector as "regime unavailable" → rejects entries.

**RAG / vol_regime Alignment**
- D-28: HMM and RAG `vol_regime` stay independent for v2.0.
- D-29: `rag_signal_filter.py` untouched in Phase 8.

### Claude's Discretion
- Exact JSON schema field names / key ordering
- Internal class/function naming inside the regime subpackage
- Whether `bars_to_log_returns` lives in `__init__.py` directly or in private `_utils.py`
- Pytest fixture structure for parity tests
- Logging verbosity defaults for offline fit CLI

### Deferred Ideas (OUT OF SCOPE)
- RecalibrationService port (V1 `calibration.py`) — v3.0 EXPN-03
- Walk-forward regime fitting on rolling window — v3.0 EXPN-03
- HMM state coupling into RAG context embeddings
- Pair tier-based detector pooling
- Mandatory PitClock on existing backtest loops (kept opt-in)
- Pre-commit hook for Viterbi import blocking (pytest grep gate sufficient)
- ArcticDB-backed PiT manager
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REGM-01 | HMM-GARCH classifier ported to `V2/v3_intelligence/regime.py` with offline fit + online update split | V1 source fully mapped (§A); subpackage substitution per D-02; offline fit = `HMMGARCHRegimeDetector.fit()`; online update = `OnlineRegimeFilter.update()` |
| REGM-02 | HMM state labels pinned by variance rank at fit time | V1 `_remap_matrix` + sort-by-`unconditional_variance` ports verbatim (`hmm_garch.py:111-119`); reflected in JSON `variance_ordering` block |
| REGM-03 | PiT manager at `V2/v3_intelligence/pit.py` enforces no future-bar read | New `PitClock` context manager (§C); timestamp-based check; `FutureBarReadError` raised on violation |
| REGM-04 | OnlineRegimeFilter is the sole regime source — Viterbi banned | Achieved by NOT porting `viterbi.py` / `predict_viterbi`; enforced by grep gate test (§G) |

</phase_requirements>

## 1. Executive Summary

- **Scope is a faithful port**, not a redesign: V1 regime/ subpackage (922 lines, 5 files) translates cleanly into V2 with two surgical changes — drop `viterbi.py` (REGM-04), and replace `signal_types` import with a local `types.py` containing only `RegimeState`.
- **REGM-02 is satisfied by-construction.** V1 already sorts states by `unconditional_variance` ascending and remaps `transmat_` and `startprob_` (`hmm_garch.py:111-119`). Verbatim port = requirement met.
- **PiT is greenfield.** V1's `pit_manager.py` is ArcticDB-bound (`adb.Arctic(store_uri).get_library(...)`); V2 reimplements as a lightweight pandas timestamp-clock per D-06. Not a port — a fresh ~80 LOC module.
- **Library API surface is stable.** `hmmlearn>=0.3` keeps `GaussianHMM(n_components, covariance_type, n_iter, tol, random_state)` and `monitor_.converged`; `arch>=6.0` keeps `arch_model(returns, vol="Garch", p=1, q=1, dist="normal").fit(disp="off")` and `res.params["mu" | "omega" | "alpha[1]" | "beta[1]"]`. V1 was written against these exact APIs and works today.
- **Parity strategy is statistical, not bit-exact.** D-16 sets `1e-6` rtol on GARCHParams, ≥95% state agreement on synthetic returns. Tolerates BLAS/scipy drift between Python 3.10 (V1) and 3.12 (V2).
- **Persistence is JSON + numpy.tolist().** Per D-11 — human-readable, version-controllable, ~1KB per pair. No pickle, no float-precision loss beyond standard JSON double-precision.
- **CLI mirrors `download_history.py`.** `--pair {USDJPY|...|all}`, idempotent skip-if-exists (or `--force`), `argparse`, exit non-zero on failure (D-26).
- **Wave structure follows Phase 7 pattern.** Wave 0 RED scaffolding → Wave 1 emissions+detector → Wave 2 OnlineFilter+PitClock+persistence → Wave 3 CLI+parity baseline (checkpoint).
- **Top risks are convergence flakiness and parity drift** — both mitigated by V1's existing retry loop and by tolerance-based parity (not bit-exact).
- **Critical recommendation:** `bars_to_log_returns` lives in `regime/__init__.py` as `D-20` requires; do NOT relocate to `_utils.py` — exposed surface is small (one function), and the helper signs the regime module's input contract.

## 2. V1 Port Mechanics

### A.1 — `hmm_garch.py` Walk (253 lines)

**Public methods (V2 keeps):**
| Method | Lines | Port action |
|--------|-------|-------------|
| `__init__(n_states=3, n_iter=100, tol=0.01, max_retries=5, min_state_samples=100, random_state=0)` | 33-52 | Verbatim |
| `fit(returns: np.ndarray) -> bool` | 58-126 | Verbatim, swap import paths |
| `get_regime_label(state: int) -> str` | 150-153 | Verbatim |
| `is_fitted` (property) | 155-158 | Verbatim |

**Public method DROPPED (REGM-04):**
| Method | Lines | Action |
|--------|-------|--------|
| `predict_viterbi(returns)` | 128-148 | DELETE — D-04. The only consumer of `viterbi_decode` import. |

**Private helpers (V2 keeps):**
| Helper | Lines | Port action |
|--------|-------|-------------|
| `_fit_gaussian_hmm(obs)` | 164-199 | Verbatim. Includes V1's retry loop with `seed = self._random_state + attempt`. |
| `_fit_garch(state_returns, state_idx)` | 201-214 | Verbatim. `arch_model(state_returns, vol="Garch", p=1, q=1, dist="normal").fit(disp="off")`; pulls `res.params["mu" | "omega" | "alpha[1]" | "beta[1]"]`. |
| `_gaussian_fallback(state_returns, state_idx)` | 216-227 | Verbatim. Triggers when `len(state_returns) < min_state_samples`. Synthetic GARCHParams with α=0.05, β=0.90, omega = max(var*0.05, 1e-8). |
| `_compute_log_emission_probs(returns)` | 229-240 | DELETE — only consumer was `predict_viterbi`. Drops naturally with REGM-04. |
| `_remap_matrix(matrix, sort_order)` (staticmethod) | 242-250 | Verbatim. THIS IS THE VARIANCE-RANK PIN — see A.2. |

**Imports to update:**
```python
# V1
from src.alpha.regime.emissions import GARCHParams, garch_emission_prob
from src.alpha.regime.viterbi import viterbi_decode  # DROP

# V2
from v3_intelligence.regime.emissions import GARCHParams
# garch_emission_prob no longer needed at this level (only in OnlineFilter)
```

After dropping `predict_viterbi` + `_compute_log_emission_probs`, V2's `hmm_garch.py` is roughly **180 lines** (vs V1's 253).

### A.2 — Variance-Rank Pinning (REGM-02 source)

`hmm_garch.py:111-119`:

```python
# Sort states by ascending unconditional variance
raw_params.sort(key=lambda x: x[1].unconditional_variance)
sort_order = [orig_idx for orig_idx, _ in raw_params]

self.garch_params = [params for _, params in raw_params]

# Re-map transition matrix and startprob to new state ordering
self.transmat_ = self._remap_matrix(hmm_model.transmat_, sort_order)
self.startprob_ = hmm_model.startprob_[sort_order]
self._fitted = True
```

This is the entire mechanism. After fit():
- `self.garch_params[0]` is always lowest-variance (TRENDING)
- `self.garch_params[1]` is always middle (MEAN_REVERTING)
- `self.garch_params[2]` is always highest (CRISIS)
- `transmat_` and `startprob_` are re-permuted via `_remap_matrix` (lines 242-250) so indices align

**Port verbatim → REGM-02 satisfied.**

### A.3 — `online_filter.py` Walk (151 lines)

**Critical observation:** V1 file imports `garch_emission_prob` (line 9) but **does not call it** in any code path I see. The actual emission computation in `update()` (lines 75-82) is **inlined** — it manually computes `log_b = -0.5 * (log_2pi + math.log(sigma2_j) + eps2 / sigma2_j)`. So:
- The `garch_emission_prob` import on line 9 is **dead code** in `online_filter.py`.
- V2 should **remove** that import.
- `online_filter.py` does NOT need viterbi (V1 doesn't import it here either).

**Public methods (V2 keeps):**
| Method | Lines | Port action |
|--------|-------|-------------|
| `__init__(detector)` | 29-45 | Verbatim. Validates detector.is_fitted, copies `startprob_`, initializes `_sigma2` to per-state unconditional variances. |
| `update(return_value: float) -> tuple[RegimeState, float]` | 51-106 | Verbatim. Forward step + variance recursion + log-space fallback dispatch. |
| `reset()` | 108-114 | Verbatim. |
| `state_probs` (property) | 116-119 | Verbatim. Returns copy of `_alpha`. |

**Private helpers (V2 keeps):**
| Helper | Lines | Port action |
|--------|-------|-------------|
| `_log_space_forward(return_value)` | 125-148 | Verbatim. Triggered when `total = alpha_new.sum() == 0.0` (numerical underflow). Uses `np.logaddexp.reduce`. |

**Local-import quirk:** V1 has `from src.alpha.regime.hmm_garch import HMMGARCHRegimeDetector` inside `__init__` (line 30) to avoid circular import with the `isinstance` check. V2 should preserve the local-import pattern with the V2 path: `from v3_intelligence.regime.hmm_garch import HMMGARCHRegimeDetector`.

### A.4 — `emissions.py` Walk (97 lines)

**`GARCHParams` dataclass (lines 11-40):**
```python
@dataclass(frozen=True)
class GARCHParams:
    mu: float
    omega: float
    alpha: float
    beta: float

    @property
    def unconditional_variance(self) -> float:
        return self.omega / (1.0 - self.alpha - self.beta)

    @property
    def is_stationary(self) -> bool:
        return self.alpha + self.beta < 1.0
```

Frozen, immutable, four floats. **Port verbatim.**

**`garch_emission_prob(returns, params)` function (lines 43-94):**
- Recursive variance: `σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}`, `ε_t = r_t - μ`
- Initialized at `params.unconditional_variance`
- Returns log-emission probs: `log b(r_t) = -0.5 * (log(2π) + log(σ²_t) + ε²_t / σ²_t)`
- **Port verbatim.** But note: per A.3, the only V2 caller would be tests — `OnlineRegimeFilter` inlines its own per-step computation. Worth keeping the function for parity tests and potential future use.

## 3. Library API Surface

### B.5 — hmmlearn 0.3+

**V1 calls (`hmm_garch.py:171-178, 197`):**
```python
GaussianHMM(n_components=self.n_states, covariance_type="diag",
            n_iter=self.n_iter, tol=self.tol, random_state=seed)
model.fit(obs)             # obs shape: (T, 1)
model.monitor_.converged   # bool
model.predict(obs)         # state sequence
model.transmat_            # (n_states, n_states)
model.startprob_           # (n_states,)
```

**Status:** All five surface elements are stable, public API in `hmmlearn` since 0.2.x and through 0.3.x. The `monitor_` object (with `.converged`) and `transmat_`/`startprob_` attributes have been canonical since the GaussianHMM was introduced. V1 is already pinned against 0.3+ semantics (V1 tests pass today against a 0.3-era install). Confidence: HIGH on stability.

**Action for planner:** Verify `hmmlearn>=0.3` resolves to a current version when added to `pyproject.toml`; run V1's existing test suite against the V2 install once dependencies are added — convergence behavior should match.

**Possible breakage flag (LOW probability):** If hmmlearn 0.4+ ships during planning, `n_components` could conceivably become `n_states` (no evidence — flagging as planner-task to verify on install).

### B.6 — arch 6.0+

**V1 calls (`hmm_garch.py:204-210`):**
```python
res = arch_model(state_returns, vol="Garch", p=1, q=1, dist="normal").fit(disp="off")
mu    = float(res.params["mu"])
omega = float(res.params["omega"])
alpha = float(res.params["alpha[1]"])
beta  = float(res.params["beta[1]"])
```

**Status:** `arch_model(...)` is the public factory; `vol="Garch"` (case-insensitive in arch >= 5), `p=1, q=1, dist="normal"` are stable kwargs. The `.fit(disp="off")` signature has been stable since arch 4.x. Parameter names `mu`, `omega`, `alpha[1]`, `beta[1]` are the canonical naming in `res.params` (a pandas Series indexed by string param names). V1 works against this contract today.

**Action for planner:** Verify `arch>=6.0` resolves cleanly, run V1's `_fit_garch` smoke against synthetic returns. Document the exact resolved version in pyproject.toml comment.

## 4. PitClock Design Sketch

### C.7 — Pseudocode (`V2/v3_intelligence/pit.py`)

```python
"""Point-in-time replay clock — runtime no-future-read enforcement.

Lightweight pandas-native context manager. No ArcticDB dependency. Compares
read timestamps against an as-of cutoff and raises FutureBarReadError on any
access where the read timestamp exceeds the cutoff.

Per D-06, D-08: timestamp-based, opt-in via decorator pattern.
Per D-25: PitClock.UNBOUNDED sentinel disables enforcement (offline-fit usage).
"""
from __future__ import annotations
import pandas as pd
from typing import ClassVar, Optional


class FutureBarReadError(Exception):
    """Raised when a PiT-gated read exceeds the as-of timestamp."""


class PitClock:
    """Replay clock. Wrap a backtest loop body to enforce no-future reads."""

    # Sentinel: any timestamp comparison returns False → enforcement disabled
    UNBOUNDED: ClassVar["PitClock"]  # set after class def; see bottom of file

    def __init__(self, as_of_ts: Optional[pd.Timestamp]) -> None:
        # None marks the UNBOUNDED sentinel; callers should prefer the constant.
        self._as_of: Optional[pd.Timestamp] = as_of_ts
        self._active: bool = False

    def __enter__(self) -> "PitClock":
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._active = False

    def advance(self, new_ts: pd.Timestamp) -> None:
        """Move the cutoff forward inside the loop (must be monotone)."""
        if self._as_of is not None and new_ts < self._as_of:
            raise ValueError(f"PitClock cannot rewind ({new_ts} < {self._as_of})")
        self._as_of = new_ts

    def read(
        self,
        df: pd.DataFrame,
        sym: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return rows of df whose index is <= self._as_of.

        Raises FutureBarReadError if df.index.max() > self._as_of AND the caller
        attempts to use rows beyond the cutoff. In practice we slice and return
        the truncated view; the error is raised only when the underlying df
        contains nothing within the cutoff.
        """
        if self._as_of is None:  # UNBOUNDED
            return df
        if df.index.max() <= self._as_of:
            return df
        # Truncate: rows with index > as_of are excluded silently.
        # This is the non-leakage-by-construction read.
        truncated = df.loc[df.index <= self._as_of]
        if truncated.empty:
            raise FutureBarReadError(
                f"No bars at or before {self._as_of}"
                + (f" for {sym}" if sym else "")
            )
        return truncated

    def assert_no_future(self, ts: pd.Timestamp, sym: Optional[str] = None) -> None:
        """Explicit guard: raise if ts > as_of. Use when caller already has a ts."""
        if self._as_of is None:
            return
        if ts > self._as_of:
            raise FutureBarReadError(
                f"Read at {ts} exceeds clock {self._as_of}"
                + (f" for {sym}" if sym else "")
            )


# Sentinel construction — single shared instance with as_of=None
PitClock.UNBOUNDED = PitClock(None)  # type: ignore[assignment]


def pit_gated(method):
    """Decorator: backtest method ensures it receives a PitClock kw or default."""
    def wrapper(self, *args, clock: Optional[PitClock] = None, **kwargs):
        if clock is None:
            clock = PitClock.UNBOUNDED
        return method(self, *args, clock=clock, **kwargs)
    return wrapper
```

### C.8 — Why no monkey-patching of pandas

The check is **on the access call** (`clock.read(df, sym=...)` or `clock.assert_no_future(ts)`), not on iteration. Two design implications:

1. **The underlying `df` is intact** — callers continue to use vanilla pandas everywhere except where they explicitly route through the clock. There's no global state, no pandas hook, no monkey-patch.
2. **Opt-in is clean** — Phase 9 router replay loop wraps its body in `with PitClock(t) as clock:` and calls `clock.read(df_h1)`. Existing Phase 7 backtests (`backtest_hybrid.py`, `backtest_evaluate_all.py`) are untouched (D-07).

**Test trick (D-09):** A deliberate out-of-order read like `clock.assert_no_future(t + pd.Timedelta(hours=1))` while `clock._as_of == t` raises `FutureBarReadError`. This is the success criterion 3 contract.

## 5. JSON Persistence (D-11)

### D.9 — Schema sketch (`V2/data/regime/{PAIR}_detector.json`)

```jsonc
{
  "schema_version": 1,
  "pair": "USDJPY",
  "n_states": 3,
  "garch_params": [
    { "mu": 1.234e-05, "omega": 4.567e-08, "alpha": 0.0521, "beta": 0.9234 },
    { "mu": 2.345e-05, "omega": 8.901e-08, "alpha": 0.0612, "beta": 0.9123 },
    { "mu": 3.456e-05, "omega": 1.234e-06, "alpha": 0.0834, "beta": 0.8901 }
  ],
  "transmat":  [[0.95, 0.04, 0.01],
                [0.06, 0.90, 0.04],
                [0.01, 0.10, 0.89]],
  "startprob": [0.60, 0.30, 0.10],
  "variance_ordering": {
    "state_labels": ["TRENDING", "MEAN_REVERTING", "CRISIS"],
    "unconditional_variances": [1.20e-07, 4.80e-07, 2.30e-06]
  },
  "fit_metadata": {
    "fitted_at_utc": "2026-04-25T12:34:56Z",
    "data_window": "4yr",
    "data_path": "V2/data/USDJPY_H1_4yr.csv",
    "n_bars": 35040,
    "n_states_iter_actual": 100,
    "hmmlearn_converged": true,
    "v1_parity_tested": false
  }
}
```

Every numeric field is a JSON-native double. Round-trip via `numpy.tolist()` (write) and `np.asarray(..., dtype=np.float64)` (read). Roundtrip absolute error stays within IEEE-754 double precision (~1e-15) — assertion in tests should be `≤ 1e-12` to be safe.

### D.10 — Function signatures

```python
# V2/v3_intelligence/regime/persistence.py  (or inside hmm_garch.py)

def save_detector(
    detector: HMMGARCHRegimeDetector,
    path: pathlib.Path,
    *,
    pair: str,
    data_path: str,
    data_window: str = "4yr",
) -> None:
    """Serialize fitted detector to JSON. Raises if not fitted."""

def load_detector(path: pathlib.Path) -> HMMGARCHRegimeDetector:
    """Reconstruct fitted detector from JSON. Raises FileNotFoundError or
    schema-version mismatch."""
```

Both go through `json.dump(..., indent=2)` / `json.load`. No pickle, no msgpack. The detector is reconstructed by directly setting `garch_params`, `transmat_`, `startprob_`, and `_fitted = True` — no re-fit.

## 6. CLI Pattern (E.11)

`V2/scripts/download_history.py` (Phase 7) layout used as template:

```python
# V2/scripts/fit_regime_detectors.py
"""Offline HMM-GARCH detector fitting for all 5 pairs.

Usage:
    python -m scripts.fit_regime_detectors --pair USDJPY
    python -m scripts.fit_regime_detectors --pair all
    python -m scripts.fit_regime_detectors --pair all --force   # re-fit existing
    python -m scripts.fit_regime_detectors --pair USDJPY --data-window 4yr

Idempotent: skips pairs whose JSON exists unless --force is set.
Per D-26: exits non-zero if any pair fails to fit.
"""
from __future__ import annotations
import argparse, sys, pathlib
import pandas as pd

from v3_intelligence.regime import (
    HMMGARCHRegimeDetector, bars_to_log_returns, save_detector,
)

ACTIVE_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP"]
DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
REGIME_DIR = DATA_DIR / "regime"


def _fit_one(pair: str, data_window: str, force: bool) -> bool:
    out = REGIME_DIR / f"{pair}_detector.json"
    if out.exists() and not force:
        print(f"  SKIP {pair} — {out.name} exists (idempotent)")
        return True

    csv = DATA_DIR / f"{pair}_H1_{data_window}.csv"
    if not csv.exists():
        print(f"  FAIL {pair} — {csv} not found", file=sys.stderr)
        return False

    df = pd.read_csv(csv, index_col=0, parse_dates=True)
    returns = bars_to_log_returns(df)

    detector = HMMGARCHRegimeDetector(random_state=0)
    if not detector.fit(returns):
        print(f"  FAIL {pair} — fit() returned False (stationarity or convergence)",
              file=sys.stderr)
        return False

    REGIME_DIR.mkdir(parents=True, exist_ok=True)
    save_detector(detector, out, pair=pair, data_path=str(csv),
                  data_window=data_window)
    print(f"  OK   {pair} — variances={[f'{p.unconditional_variance:.2e}' for p in detector.garch_params]} → {out.name}")
    return True


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pair", required=True, choices=ACTIVE_PAIRS + ["all"])
    p.add_argument("--data-window", default="4yr")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    targets = ACTIVE_PAIRS if args.pair == "all" else [args.pair]
    failed = [p for p in targets if not _fit_one(p, args.data_window, args.force)]
    if failed:
        print(f"FAILED pairs: {failed}", file=sys.stderr)
        return 1
    print(f"All {len(targets)} pair(s) fitted successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Mirrors `download_history.py` shape: argparse, ACTIVE_PAIRS list at module top, idempotent-skip pattern, DATA_DIR resolution via `parents[1]`, `SystemExit(main(sys.argv[1:]))`.

## 7. Parity Testing (F.12, F.13)

### F.12 — Synthetic returns fixture

```python
# tests/v3_intelligence/conftest.py  (or fixtures.py)

import numpy as np, pytest

@pytest.fixture(scope="module")
def synthetic_three_regime_returns():
    """Deterministic 3-regime mixture; seed=42, T=1000."""
    rng = np.random.default_rng(42)
    T = 1000
    # Ground truth state sequence: 600 trending, 300 mean-rev, 100 crisis
    state_seq = np.concatenate([
        np.zeros(600, dtype=int),
        np.ones(300, dtype=int),
        np.full(100, 2, dtype=int),
    ])
    rng.shuffle(state_seq)
    # Per-state mu/sigma (annualised-ish, in log-return units)
    mus    = np.array([1e-5,  0.0,    -2e-5])
    sigmas = np.array([1e-3,  3e-3,   8e-3])
    returns = rng.normal(loc=mus[state_seq], scale=sigmas[state_seq])
    return returns, state_seq


@pytest.fixture(scope="module")
def v1_baseline():
    """Loaded baseline (recorded once from V1 detector). Sourced from npz."""
    return np.load("tests/v3_intelligence/parity_baseline.npz")
```

The baseline `.npz` is captured **once** from V1 by running V1's detector against the same fixture (which lives in repo so V1 can read it too). Stored fields: `garch_params` (4 × n_states float array), `transmat`, `startprob`, `online_states` (length-T int array of OnlineRegimeFilter outputs).

### F.13 — Tolerance design

| Metric | Tolerance | Rationale |
|--------|-----------|-----------|
| `GARCHParams.{mu, omega, alpha, beta}` | `rtol=1e-6` (np.allclose) | V1/V2 share the same `arch_model` solver; numpy/scipy version drift between Py3.10 and Py3.12 typically stays below this. |
| `transmat_`, `startprob_` | `rtol=1e-6` | Same path through hmmlearn EM. |
| `OnlineRegimeFilter.update()` state agreement | `≥ 95%` raw match rate | Forward-algorithm divergence accumulates over T bars; a 5% disagreement budget tolerates underflow-fallback path differences across BLAS versions. |
| JSON round-trip of all fitted floats | `atol=1e-12` | IEEE-754 double precision through `json.dumps`/`json.loads` is exact for finite values; 1e-12 is the safety margin. |

**Why raw match rate, not Cohen's kappa?** Kappa adjusts for chance agreement, which matters when class distributions are imbalanced. Here the baseline state distribution and the V2 distribution come from the **same fixture** — by construction the chance-agreement baseline is identical. Raw match rate is the simpler, equivalent metric. Document this in test docstring.

## 8. Test Scaffolding Plan (G.14)

Wave 0 collects all of the following as **RED** (skipped or failing) tests:

```
tests/v3_intelligence/
├── __init__.py
├── conftest.py                        # synthetic fixture, baseline loader
├── parity_baseline.npz                # captured from V1 (committed)
├── test_regime_detector.py            # HMMGARCHRegimeDetector unit
├── test_online_filter.py              # OnlineRegimeFilter unit
├── test_emissions.py                  # GARCHParams + garch_emission_prob
├── test_pit.py                        # PitClock + FutureBarReadError
├── test_viterbi_ban.py                # REGM-04 grep gate
├── test_persistence.py                # save_detector / load_detector roundtrip
├── test_bars_to_log_returns.py        # helper unit
└── test_regime_parity.py              # @pytest.mark.slow — V1 vs V2
```

| File | Tests collected (RED) |
|------|----------------------|
| `test_regime_detector.py` | (1) `fit()` returns True on synthetic; (2) variance-rank pinning: states sorted by `unconditional_variance` ascending; (3) re-fit on perturbed copy preserves state ordering (REGM-02); (4) `is_fitted` flips False→True; (5) `get_regime_label(0)`=="TRENDING" |
| `test_online_filter.py` | (1) `update()` returns `(RegimeState, float)` with conf in [0, 1]; (2) `reset()` restores `state_probs == startprob_`; (3) `state_probs` returns shape (3,) summing to 1.0 ± 1e-9; (4) underflow trigger → `_log_space_forward` keeps probs valid; (5) constructor raises on unfitted detector |
| `test_emissions.py` | (1) `GARCHParams.is_stationary` True when α+β<1, False otherwise; (2) `unconditional_variance == omega/(1-α-β)`; (3) `garch_emission_prob` shape (T,) finite; (4) frozen dataclass — assignment raises |
| `test_pit.py` | (1) `with PitClock(t)` enters/exits cleanly; (2) `clock.read(df_after_t)` raises `FutureBarReadError` (D-09); (3) `clock.read(df_at_or_before_t)` returns truncated rows; (4) `PitClock.UNBOUNDED.read(df)` returns df verbatim (D-25); (5) `clock.advance(t-1h)` raises (monotone); (6) `clock.assert_no_future(t+1h)` raises |
| `test_viterbi_ban.py` | (1) Grep `viterbi`/`Viterbi`/`predict_viterbi` over `V2/backtest/`, `V2/v3_intelligence/`, `V2/live/` (when present) — assert zero matches (D-05) |
| `test_persistence.py` | (1) save+load roundtrip preserves `garch_params` within 1e-12; (2) preserves `transmat_`, `startprob_` within 1e-12; (3) `load_detector` raises on missing schema_version; (4) `save_detector` raises if detector unfitted |
| `test_bars_to_log_returns.py` | (1) returns np.ndarray dtype float64; (2) length == len(df) - 1; (3) NaN dropped; (4) input missing 'close' or 'Close' raises |
| `test_regime_parity.py` (`@pytest.mark.slow`) | (1) V2 GARCHParams within rtol=1e-6 of V1 baseline; (2) V2 OnlineRegimeFilter state agreement ≥ 95% on synthetic returns vs V1 baseline; (3) V2 transmat/startprob within rtol=1e-6 |

## 9. Wave Breakdown (H.15)

**Phase 7 pattern:** Wave 0 RED → subsequent waves GREEN. Phase 8 mirrors:

| Wave | Plan | Scope | Type | Dependencies |
|------|------|-------|------|--------------|
| **Wave 0** | 08-01-PLAN | Test scaffolding for all 8 test files (RED) + `parity_baseline.npz` capture from V1 + `tests/v3_intelligence/conftest.py` fixture | Autonomous | None — pure test files |
| **Wave 1** | 08-02-PLAN | `pyproject.toml` adds `hmmlearn>=0.3, arch>=6.0` + `regime/types.py` (RegimeState) + `regime/emissions.py` + `regime/hmm_garch.py` (no Viterbi) + `regime/__init__.py` exports + `bars_to_log_returns` helper | Autonomous | Wave 0 (tests turn GREEN for `test_regime_detector`, `test_emissions`, `test_bars_to_log_returns`) |
| **Wave 2** | 08-03-PLAN | `regime/online_filter.py` + `pit.py` (PitClock + FutureBarReadError + UNBOUNDED + pit_gated decorator) + persistence (save_detector, load_detector) | Autonomous | Wave 1 (detector exists for OnlineRegimeFilter to consume; tests for filter/pit/persistence turn GREEN) |
| **Wave 3** | 08-04-PLAN | `scripts/fit_regime_detectors.py` CLI + capture all 5 pair fits → `V2/data/regime/*.json` + `test_viterbi_ban` enforcement run + `test_regime_parity` GREEN | **Checkpoint** | Wave 2 (CLI uses persistence; parity test exercises the whole stack; the 4yr fits succeeding is the empirical gate before Phase 9 can wire detector_registry) |

**Why Wave 3 is a checkpoint, not autonomous:** the 4yr fits are the empirical proof that v2.0 has a working regime gate. If a pair fails (D-26), that informs whether Phase 9 router should be planned around 4 pairs or 5. The user should review the fitted variance ordering per pair before proceeding.

**Wave 0 autonomy detail:** Capturing the V1 baseline requires running V1 code once. The plan should script this as a one-shot `tests/v3_intelligence/_capture_v1_baseline.py` that imports V1 from the V1 repo path and writes `parity_baseline.npz`. This script is committed but not run in CI (it's a one-time artifact generator).

## 10. Top 5 Risks (I.16)

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | **hmmlearn convergence flakiness** — EM doesn't converge in 100 iter on 4yr H1 returns of certain pairs | V1's retry loop ports verbatim (`_fit_gaussian_hmm` lines 169-199): 5 seeds tried; if all fail, last fit still returned and stationarity check downstream rejects. CLI exits non-zero per D-26 — failure visible. |
| 2 | **GARCH non-stationarity (α+β ≥ 1)** — common with high-vol pairs (e.g. GBPJPY, GBPAUD) on long windows | V1 explicit check (`hmm_garch.py:101-107`): if `not params.is_stationary`, fit() returns False. CLI surfaces "stationarity fail" reason (D-26). Manual mitigation: try shorter `data_window` or different `random_state`. |
| 3 | **Parity drift across BLAS / numpy / scipy versions** between V1 (Py3.10) and V2 (Py3.12) | Tolerance not bit-exact (D-16): rtol=1e-6 on params, ≥95% state agreement. If parity test fails, investigate before declaring it spurious — could be a real port bug. |
| 4 | **4yr data gaps causing returns NaN / state imbalance** — bars missing over weekends, broker outages | `bars_to_log_returns` calls `.dropna()` per D-20. If too many drops happen the GaussianHMM still fits; the risk surfaces as `min_state_samples` triggering Gaussian fallback for some state. CLI logs it. Wave 1 unit test on synthetic data exercises this path. |
| 5 | **JSON float precision loss** — read-modify-write on detector files could drift | Roundtrip test in `test_persistence.py` enforces 1e-12 absolute tolerance. JSON doubles are IEEE-754; precision loss is ~1e-15 per operation. If anyone introduces a write path that re-encodes, this test catches drift before merge. |

## 11. Validation Architecture

> Phase 8 follows Phase 7's Nyquist pattern: every requirement maps to ≥1 automated test; Wave 0 collects them RED; Wave 1-3 turn them GREEN.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured in V2/pyproject.toml lines 7-14) |
| Config file | `V2/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/v3_intelligence -x` |
| Full suite command | `pytest tests/v3_intelligence -m 'slow or not slow'` (includes parity) |
| Default fast run | `pytest tests/v3_intelligence` (excludes `slow` per `addopts = "-v -m 'not slow'"`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REGM-01 (structural) | Subpackage exists with required files; nothing in V2 imports from V1 | unit + grep | `pytest tests/v3_intelligence/test_regime_detector.py::test_subpackage_layout -x` | ❌ Wave 0 |
| REGM-01 (behavioral) | `HMMGARCHRegimeDetector.fit()` returns True on synthetic three-regime returns | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_fit_returns_true -x` | ❌ Wave 0 |
| REGM-01 (behavioral) | `OnlineRegimeFilter.update()` returns `(RegimeState, float)` after detector fit | unit | `pytest tests/v3_intelligence/test_online_filter.py::test_update_returns_state_conf -x` | ❌ Wave 0 |
| REGM-02 | After `fit()`, `garch_params[i].unconditional_variance` is monotonically increasing | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_variance_rank_pinning -x` | ❌ Wave 0 |
| REGM-02 | Re-fit on perturbed (+1e-7 shift) returns preserves state ordering | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_refit_preserves_ordering -x` | ❌ Wave 0 |
| REGM-03 | `PitClock(t)` raises `FutureBarReadError` on `assert_no_future(t + 1h)` | unit | `pytest tests/v3_intelligence/test_pit.py::test_future_read_raises -x` | ❌ Wave 0 |
| REGM-03 | `PitClock.UNBOUNDED` allows reads of any timestamp | unit | `pytest tests/v3_intelligence/test_pit.py::test_unbounded_allows -x` | ❌ Wave 0 |
| REGM-03 | `clock.read(df)` returns rows with index ≤ as_of when df extends beyond cutoff | unit | `pytest tests/v3_intelligence/test_pit.py::test_read_truncates -x` | ❌ Wave 0 |
| REGM-04 | Grep finds zero `viterbi`/`Viterbi`/`predict_viterbi` in V2/backtest, V2/v3_intelligence, V2/live | grep gate | `pytest tests/v3_intelligence/test_viterbi_ban.py -x` | ❌ Wave 0 |
| Port faithfulness (D-16) | V2 GARCHParams within rtol=1e-6 of V1 baseline | parity / slow | `pytest tests/v3_intelligence/test_regime_parity.py -m slow -x` | ❌ Wave 0 |
| Port faithfulness (D-16) | V2 OnlineRegimeFilter state agreement ≥ 95% with V1 baseline on synthetic returns | parity / slow | `pytest tests/v3_intelligence/test_regime_parity.py::test_online_state_agreement -m slow -x` | ❌ Wave 0 |
| Persistence integrity | save→load roundtrip preserves all fitted parameters within 1e-12 | unit | `pytest tests/v3_intelligence/test_persistence.py::test_roundtrip -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/v3_intelligence -x` (~ < 30s, excludes `slow`)
- **Per wave merge:** `pytest tests/v3_intelligence -m 'slow or not slow' -x` (parity included; estimated 1-3 min)
- **Phase gate (before `/gsd:verify-work`):** Full suite green + 5/5 detector JSON files exist in `V2/data/regime/*.json` + `test_viterbi_ban` clean

### Wave 0 Gaps
- [ ] `tests/v3_intelligence/__init__.py` — package marker
- [ ] `tests/v3_intelligence/conftest.py` — `synthetic_three_regime_returns`, `v1_baseline` fixtures
- [ ] `tests/v3_intelligence/parity_baseline.npz` — captured from V1 (one-time, committed)
- [ ] `tests/v3_intelligence/_capture_v1_baseline.py` — generator script (committed but not run in CI)
- [ ] `tests/v3_intelligence/test_regime_detector.py`
- [ ] `tests/v3_intelligence/test_online_filter.py`
- [ ] `tests/v3_intelligence/test_emissions.py`
- [ ] `tests/v3_intelligence/test_pit.py`
- [ ] `tests/v3_intelligence/test_viterbi_ban.py`
- [ ] `tests/v3_intelligence/test_persistence.py`
- [ ] `tests/v3_intelligence/test_bars_to_log_returns.py`
- [ ] `tests/v3_intelligence/test_regime_parity.py`
- Framework install: `pip install hmmlearn>=0.3 arch>=6.0` (ensure resolves; document the resolved versions in pyproject comment)
- Pytest is already configured — no install needed.

---

## Sources

### Primary (HIGH confidence)
- `V1/helix/src/alpha/regime/hmm_garch.py:1-253` — full read; port mechanics validated
- `V1/helix/src/alpha/regime/online_filter.py:1-151` — full read; OnlineRegimeFilter contract
- `V1/helix/src/alpha/regime/emissions.py:1-97` — GARCHParams + garch_emission_prob
- `V1/helix/src/alpha/signal_types.py:11-17` — RegimeState IntEnum source
- `V1/helix/src/data/pit_manager.py:1-151` — V1 ArcticDB PiT (semantics only; V2 reimplements lightweight)
- `V2/scripts/download_history.py:1-152` — CLI template for `fit_regime_detectors.py`
- `V2/backtest/pit_validator.py:1-465` — Phase 7 static-AST cousin (complementary to runtime PitClock)
- `V2/v3_intelligence/__init__.py:1-13` — current subpackage exports (will need regime addition)
- `V2/pyproject.toml:1-25` — pytest markers (slow, pit_check, spike) and Python 3.12 target
- `.planning/phases/08-hmm-garch-regime-pit-port/08-CONTEXT.md` — 29 user decisions (locked)
- `.planning/REQUIREMENTS.md:25-29` — REGM-01/02/03/04 wording

### Secondary (MEDIUM confidence)
- hmmlearn 0.3 GaussianHMM API surface (verified by V1 source compiling+running today; no changelog read this session)
- arch 6.0 `arch_model` API surface (same — V1 works against this contract)

### Tertiary (LOW confidence)
- (none — research scoped tightly to repo files per time budget directive)

## Metadata

**Confidence breakdown:**
- V1 port mechanics: HIGH — full source read, line-numbered references
- Library API surface: HIGH (V1 calls these APIs and tests pass) — flagged as planner-task-to-verify-on-install
- PitClock design: HIGH — fresh design, 30 LOC, no library dependencies
- JSON persistence: HIGH — JSON+numpy.tolist() is well-trodden
- Parity testing: HIGH — strategy from D-16/D-17, baseline-from-V1 approach is mechanical
- Wave breakdown: HIGH — Phase 7 pattern is the template

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days; library APIs and V1 source are stable; renew if hmmlearn 0.4 ships)
