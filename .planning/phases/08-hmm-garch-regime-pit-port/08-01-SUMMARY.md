---
phase: 08-hmm-garch-regime-pit-port
plan: 01
subsystem: testing
tags: [pytest, hmm-garch, pit, regime, parity, wave-0, red-tests]

# Dependency graph
requires:
  - phase: 07-backtest-entry-fix-h1-momentum-4yr-validation
    provides: "RED-test scaffolding pattern (Phase 7 P01) — Wave 0 collects failing tests; subsequent waves turn them GREEN"
provides:
  - "41 RED tests across 8 test files under V2/tests/v3_intelligence/"
  - "synthetic_three_regime_returns + v1_baseline pytest fixtures (deterministic seed=42, T=1000)"
  - "parity_baseline.npz captured from V1 detector + filter (3 GARCHParams, 3x3 transmat, 3 startprob, 1000 online states)"
  - "_capture_v1_baseline.py one-shot generator (committed; never re-run by CI)"
  - "Test contracts that downstream Plans 02/03/04 must satisfy to turn GREEN"
affects:
  - "08-02 (Wave 1: detector + emissions + helper) — turns test_regime_detector / test_emissions / test_bars_to_log_returns GREEN"
  - "08-03 (Wave 2: online filter + PitClock + persistence) — turns test_online_filter / test_pit / test_persistence GREEN"
  - "08-04 (Wave 3: CLI + parity) — turns test_viterbi_ban / test_regime_parity GREEN"
  - "Phase 9 router (consumes detector_registry contract; tests established here pin that contract)"

# Tech tracking
tech-stack:
  added: []  # No production deps added; hmmlearn>=0.3 + arch>=6.0 will be added in Plan 02
  patterns:
    - "Wave 0 RED test scaffolding (mirrors Phase 7 P01)"
    - "One-shot V1 baseline capture committed as .npz (avoids V1 environment dependency in CI)"
    - "@pytest.mark.slow for parity tests (deselected in default fast runs)"

key-files:
  created:
    - "V2/tests/v3_intelligence/__init__.py"
    - "V2/tests/v3_intelligence/conftest.py"
    - "V2/tests/v3_intelligence/_capture_v1_baseline.py"
    - "V2/tests/v3_intelligence/parity_baseline.npz"
    - "V2/tests/v3_intelligence/test_regime_detector.py"
    - "V2/tests/v3_intelligence/test_online_filter.py"
    - "V2/tests/v3_intelligence/test_emissions.py"
    - "V2/tests/v3_intelligence/test_persistence.py"
    - "V2/tests/v3_intelligence/test_bars_to_log_returns.py"
    - "V2/tests/v3_intelligence/test_pit.py"
    - "V2/tests/v3_intelligence/test_viterbi_ban.py"
    - "V2/tests/v3_intelligence/test_regime_parity.py"
  modified: []

key-decisions:
  - "PYTHONPATH=V1/helix (not V1/helix/src) for V1 import — V1's alpha/__init__.py uses absolute 'from src.alpha.*' imports, so the package root must be V1/helix"
  - "Synthetic three-regime mixture (seed=42, T=1000) is the canonical parity fixture — used by both _capture_v1_baseline.py and the V2 parity test"
  - "parity_baseline.npz is committed to repo (binary, ~32KB) — frees CI from any V1 dependency"
  - "Tests are RED at end of Plan 01: 38 failing (ImportError pending Plans 02/03), 3 vacuously green (V2 regime/ files do not yet exist)"

patterns-established:
  - "Wave 0 = RED test scaffolding; subsequent waves turn GREEN — mirrors Phase 7 P01"
  - "Parity test fixtures: deterministic numpy seed + same fixture used by V1 capture and V2 verification"
  - "Grep-based CI gate (test_viterbi_ban.py) runs subprocess with grep -rn -I --include=*.py over scan dirs; self-references excluded"
  - "@pytest.mark.slow at module level via pytestmark = pytest.mark.slow"

requirements-completed: []  # Plan 01 only scaffolds tests; REGM-01..04 turn GREEN in Plans 02/03/04. No requirements complete yet.

# Metrics
duration: 5m 19s
cost: "-"
completed: 2026-04-25
---

# Phase 8 Plan 01: Wave 0 RED Test Scaffolding Summary

**41 RED tests across 8 files plus a committed V1 parity baseline (.npz) wire every Phase 8 requirement (REGM-01..04) to an automated gate that Plans 02/03/04 must turn GREEN.**

## Performance

- **Duration:** 5m 19s (319 seconds)
- **API Cost:** -
- **Started:** 2026-04-25T07:27:28Z
- **Completed:** 2026-04-25T07:32:47Z
- **Tasks:** 3
- **Files modified:** 12 (all newly created)

## Accomplishments

- Captured V1 detector + online filter outputs into a deterministic `parity_baseline.npz` artifact committed to repo — CI no longer needs a V1 environment to validate parity.
- Established full RED scaffold for REGM-01 (subpackage layout + fit + state enum), REGM-02 (variance-rank pinning + refit ordering), REGM-03 (PitClock context manager + UNBOUNDED + monotone advance + FutureBarReadError), and REGM-04 (subprocess grep gate over backtest/v3_intelligence/live + viterbi.py absence).
- Wired GARCHParams stationarity + JSON persistence roundtrip + bars_to_log_returns helper contracts so Plan 02's emissions module and Plan 03's persistence + helper modules have RED tests waiting.
- Pinned D-21 OnlineRegimeFilter contract: `update(return_value: float) -> tuple[RegimeState, float]`, `state_probs` shape (3,) summing to 1, underflow fallback path, reset behaviour.
- Pinned D-16 parity tolerances: GARCHParams/transmat/startprob within rtol=1e-6 of V1, ≥95% OnlineRegimeFilter state agreement on synthetic returns.

## Task Commits

Each task was committed atomically:

1. **Task 1: Test package, conftest fixtures, V1 baseline capture** — `ab3c63a` (test)
2. **Task 2: RED scaffolds for regime_detector / online_filter / emissions / persistence / bars_to_log_returns** — `7131a2f` (test)
3. **Task 3: RED scaffolds for PitClock / Viterbi grep gate / V1 parity** — `e17c75c` (test)

**Plan metadata commit:** pending — committed alongside SUMMARY/STATE/ROADMAP after this file.

## Files Created/Modified

| File | Tests | Purpose |
| --- | --- | --- |
| `V2/tests/v3_intelligence/__init__.py` | — | Package marker |
| `V2/tests/v3_intelligence/conftest.py` | — | `synthetic_three_regime_returns` + `v1_baseline` fixtures |
| `V2/tests/v3_intelligence/_capture_v1_baseline.py` | — | One-shot V1 baseline generator (committed, not in CI) |
| `V2/tests/v3_intelligence/parity_baseline.npz` | — | Captured V1 outputs: garch_params (3,4), transmat (3,3), startprob (3,), online_states (1000,) |
| `V2/tests/v3_intelligence/test_regime_detector.py` | 9 | REGM-01 (structural+behavioral) + REGM-02 + REGM-04 method-drop |
| `V2/tests/v3_intelligence/test_online_filter.py` | 5 | D-21 update contract, state_probs, reset, underflow |
| `V2/tests/v3_intelligence/test_emissions.py` | 5 | GARCHParams stationarity, unconditional_variance, frozen, garch_emission_prob |
| `V2/tests/v3_intelligence/test_persistence.py` | 4 | D-11 JSON roundtrip + schema_version + variance_ordering block |
| `V2/tests/v3_intelligence/test_bars_to_log_returns.py` | 4 | D-20 helper: float64 dtype, length, dropna, missing-close raises |
| `V2/tests/v3_intelligence/test_pit.py` | 8 | REGM-03 PitClock context manager, FutureBarReadError, UNBOUNDED, monotone advance |
| `V2/tests/v3_intelligence/test_viterbi_ban.py` | 2 | REGM-04 / D-05 grep gate over V2/backtest, V2/v3_intelligence, V2/live + D-04 viterbi.py absence |
| `V2/tests/v3_intelligence/test_regime_parity.py` | 4 | D-16 parity (`@pytest.mark.slow`): GARCHParams/transmat/startprob rtol=1e-6 + ≥95% online state agreement |
| **Total** | **41** | 8 test files, 41 collected tests |

## Requirement → Test Coverage Map

| Requirement | Tests | Files |
| --- | --- | --- |
| REGM-01 (structural) | `test_subpackage_layout`, `test_no_v1_imports`, `test_regime_state_enum_values`, `test_regime_state_reexported_from_subpackage` | test_regime_detector.py |
| REGM-01 (behavioral) | `test_fit_returns_true`, `test_get_regime_label`, `test_update_returns_state_conf`, `test_state_probs_shape_and_sum`, `test_reset_restores_startprob`, `test_underflow_path_keeps_probs_valid`, `test_constructor_raises_on_unfitted_detector` | test_regime_detector.py + test_online_filter.py |
| REGM-02 | `test_variance_rank_pinning`, `test_refit_preserves_ordering`, `test_json_contains_variance_ordering_block` | test_regime_detector.py + test_persistence.py |
| REGM-03 | `test_pitclock_context_manager_enters_and_exits`, `test_assert_no_future_raises_on_future_ts`, `test_assert_no_future_passes_on_past_or_equal_ts`, `test_read_returns_truncated_view`, `test_read_raises_when_no_rows_at_or_before_cutoff`, `test_unbounded_sentinel_allows_any_read`, `test_advance_must_be_monotone`, `test_advance_moves_cutoff_forward` | test_pit.py |
| REGM-04 | `test_no_viterbi_imports_or_calls_in_v2`, `test_no_viterbi_py_file_in_regime_subpackage`, `test_predict_viterbi_method_dropped` | test_viterbi_ban.py + test_regime_detector.py |
| D-11 persistence | `test_save_then_load_roundtrip`, `test_save_detector_raises_on_unfitted`, `test_load_detector_rejects_missing_schema_version`, `test_json_contains_variance_ordering_block` | test_persistence.py |
| D-16 parity | `test_garch_params_within_rtol_1e6`, `test_transmat_within_rtol_1e6`, `test_startprob_within_rtol_1e6`, `test_online_state_agreement` | test_regime_parity.py |
| D-20 helper | `test_returns_ndarray_dtype_float64`, `test_returns_length_is_input_minus_one`, `test_drops_nan`, `test_missing_close_column_raises` | test_bars_to_log_returns.py |

## Parity Baseline Capture Method

Run **once** by the executor with the V1 environment available:

```bash
PYTHONPATH=V1/helix python3 V2/tests/v3_intelligence/_capture_v1_baseline.py
```

The script:

1. Generates the synthetic returns fixture (numpy seed=42, T=1000, three-regime mixture).
2. Runs V1's `HMMGARCHRegimeDetector.fit(returns)` — V1 produces `(3, 4)` GARCHParams plus `(3, 3)` `transmat_` and `(3,)` `startprob_`.
3. Drives an `OnlineRegimeFilter` over all 1000 returns, recording the state index per bar.
4. Writes everything into `parity_baseline.npz` (savez, four arrays).

**Captured shapes (verified on disk):**
- `garch_params`: `(3, 4)` float64 — rows are states (variance-ascending), columns are `[mu, omega, alpha, beta]`
- `transmat`: `(3, 3)` float64
- `startprob`: `(3,)` float64
- `online_states`: `(1000,)` int64

**Note on V1 fit warnings:** arch's GARCH optimiser emitted a `DataScaleWarning` (synthetic returns ~1e-3 scale) and one inequality-constraint warning during V1 capture. V1's retry loop accepted the result and produced finite params; this is fine for parity (V2 will see the same warnings on the same inputs and converge to the same numbers within rtol=1e-6).

## RED-State Verification

```
$ cd V2 && python3 -m pytest tests/v3_intelligence/ -m 'slow or not slow' --tb=no
========================= 38 failed, 3 passed in 0.80s =========================
```

- **38 failing tests** — all `ImportError`/`ModuleNotFoundError` because `v3_intelligence.regime` and `v3_intelligence.pit` do not exist yet (Plans 02/03 land them). This is the intended Wave 0 outcome.
- **3 passing tests:**
  - `test_no_v1_imports` (vacuously: V2/v3_intelligence/regime/ does not exist, so cannot contain V1 imports)
  - `test_no_viterbi_imports_or_calls_in_v2` (vacuously: V2 regime code not yet present)
  - `test_no_viterbi_py_file_in_regime_subpackage` (vacuously: no regime/ subpackage exists)

These three structural gates will become *meaningfully* green only after Plans 02-04 land code that respects them. The plan's `<plan_specifics>` explicitly documents this as expected.

## Decisions Made

- **Use PYTHONPATH=V1/helix for V1 baseline capture (not V1/helix/src).** V1's `src/alpha/__init__.py` imports `src.alpha.orchestrator` (absolute import rooted at `src.*`), so the package root must be `V1/helix`. The plan's original PYTHONPATH suggestion was V1/helix/src; the corrected path is documented in the capture script docstring.
- **Use `from src.alpha.regime.hmm_garch import HMMGARCHRegimeDetector` in `_capture_v1_baseline.py`.** Matches V1's actual public surface. Substring `"alpha.regime.hmm_garch import HMMGARCHRegimeDetector"` still satisfies the plan's grep acceptance criterion.
- **Tests intentionally left RED at end of plan.** All 38 ImportError failures are the expected gate condition for Plans 02/03 to satisfy. Three vacuously-green tests cannot fail until Plans 02-04 actually create `V2/v3_intelligence/regime/` files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected V1 PYTHONPATH and import in _capture_v1_baseline.py**

- **Found during:** Task 1 (running the capture script)
- **Issue:** Plan specified `PYTHONPATH=V1/helix/src python ...` and imports `from alpha.regime.hmm_garch import HMMGARCHRegimeDetector`. Running this fails with `ModuleNotFoundError: No module named 'src'` because V1's `alpha/__init__.py` triggers `from src.alpha.orchestrator import CrossAssetCache, RegimeOrchestrator` — V1 uses absolute `src.*` imports, so the package root must be `V1/helix`, not `V1/helix/src`.
- **Fix:**
  - Updated capture script imports to `from src.alpha.regime.hmm_garch import HMMGARCHRegimeDetector` and `from src.alpha.regime.online_filter import OnlineRegimeFilter`.
  - Updated docstring to specify `PYTHONPATH=V1/helix python3 ...` and explain why.
- **Files modified:** `V2/tests/v3_intelligence/_capture_v1_baseline.py`
- **Verification:** Capture ran successfully, produced `parity_baseline.npz` with all four arrays at expected shapes; the plan's acceptance grep `"alpha.regime.hmm_garch import HMMGARCHRegimeDetector"` is satisfied as a substring of `"src.alpha.regime.hmm_garch import HMMGARCHRegimeDetector"`.
- **Committed in:** `ab3c63a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor — only adjusted V1 import root to match V1's actual package layout. No scope creep; output artifacts identical to plan intent.

## Issues Encountered

- **arch optimiser warnings during V1 capture.** `DataScaleWarning` (returns scale ~1e-3) and one inequality-constraints warning during V1's `arch_model().fit()`. Non-fatal — V1's retry loop produced finite, monotonically-increasing variances. These warnings will reproduce identically when V2 runs the parity test (rtol=1e-6 is robust to warning-state behaviour as long as both V1 and V2 fit on identical inputs).

## User Setup Required

None — no external service configuration. The capture script ran with the existing system Python 3.10.12 + hmmlearn 0.3.3 + arch 8.0.0 already installed.

## Next Plan Readiness

- **Plan 02 (Wave 1: detector + emissions + helper)** is unblocked. The following test files will be partially turned GREEN:
  - `test_regime_detector.py` (9 tests — except those needing OnlineRegimeFilter, which Plan 03 owns)
  - `test_emissions.py` (all 5 tests)
  - `test_bars_to_log_returns.py` (all 4 tests)
- **Plan 03 (Wave 2: online filter + PitClock + persistence)** can begin in parallel-or-after Plan 02. It owns:
  - `test_online_filter.py` (5 tests)
  - `test_pit.py` (8 tests)
  - `test_persistence.py` (4 tests)
- **Plan 04 (Wave 3: CLI + parity)** consumes everything from Plans 02/03 and turns:
  - `test_viterbi_ban.py` (2 tests, must remain green throughout)
  - `test_regime_parity.py` (4 tests, marked slow; this is the D-18 phase-completion gate)

No blockers. parity_baseline.npz is on disk and ready for Plan 04 to consume.

## Self-Check

Files verified on disk:

- FOUND: `V2/tests/v3_intelligence/__init__.py`
- FOUND: `V2/tests/v3_intelligence/conftest.py`
- FOUND: `V2/tests/v3_intelligence/_capture_v1_baseline.py`
- FOUND: `V2/tests/v3_intelligence/parity_baseline.npz`
- FOUND: `V2/tests/v3_intelligence/test_regime_detector.py`
- FOUND: `V2/tests/v3_intelligence/test_online_filter.py`
- FOUND: `V2/tests/v3_intelligence/test_emissions.py`
- FOUND: `V2/tests/v3_intelligence/test_persistence.py`
- FOUND: `V2/tests/v3_intelligence/test_bars_to_log_returns.py`
- FOUND: `V2/tests/v3_intelligence/test_pit.py`
- FOUND: `V2/tests/v3_intelligence/test_viterbi_ban.py`
- FOUND: `V2/tests/v3_intelligence/test_regime_parity.py`

Commits verified in git log:

- FOUND: `ab3c63a` (Task 1: package + conftest + capture script + parity_baseline.npz)
- FOUND: `7131a2f` (Task 2: 5 RED test files, 27 tests)
- FOUND: `e17c75c` (Task 3: 3 RED test files, 14 tests)

## Self-Check: PASSED

---

*Phase: 08-hmm-garch-regime-pit-port*
*Plan: 01*
*Completed: 2026-04-25*
