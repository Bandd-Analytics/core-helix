---
phase: 08-hmm-garch-regime-pit-port
verified: 2026-04-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification:
  was_re_verification: false
---

# Phase 8: HMM-GARCH Regime + PiT Port — Verification Report

**Phase Goal:** "The HMM-GARCH regime classifier and PiT manager are ported to the V2 intelligence module, state labels are pinned to prevent permutation, and OnlineRegimeFilter is the sole regime source — Viterbi is banned from both backtest and live code paths."

**Verified:** 2026-04-25
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HMM-GARCH classifier lives in V2 intelligence module with offline-fit / online-update split — V1 source not imported by any V2 module | VERIFIED | `V2/v3_intelligence/regime/{hmm_garch.py, online_filter.py}` exist; `HMMGARCHRegimeDetector.fit()` is offline path, `OnlineRegimeFilter.update()` is online path; grep `from\s+src\|from\s+V1\|import\s+V1\.` over V2/v3_intelligence + V2/backtest + V2/scripts returns ZERO functional imports (one match in pit_validator.py docstring is a comment) |
| 2 | Re-fitting on different dataset produces same state label ordering (variance-rank pinning prevents permutation) | VERIFIED | `test_refit_preserves_ordering` PASSES; `test_variance_rank_pinning` PASSES; all 5 detector JSONs have `variance_ordering.unconditional_variances` monotonically ascending and state_labels = `["TRENDING", "MEAN_REVERTING", "CRISIS"]`; V1 `_remap_matrix` ported byte-identical |
| 3 | PiT manager enforces no future-bar reads during backtest replay (out-of-order read raises) | VERIFIED | `V2/v3_intelligence/pit.py` exists with `PitClock`, `FutureBarReadError`, `PitClock.UNBOUNDED`; `test_assert_no_future_raises_on_future_ts` PASSES; `test_read_raises_when_no_rows_at_or_before_cutoff` PASSES; `test_advance_must_be_monotone` PASSES (8/8 pit tests green) |
| 4 | Grep/import trace finds zero direct Viterbi calls in any backtest loop or live signal path — OnlineRegimeFilter is the only entry point | VERIFIED | Functional grep `from\s+\S*viterbi\|predict_viterbi\s*(\|viterbi_decode\s*(\|\.predict_viterbi\b\|\.viterbi_decode\b` over V2/backtest + V2/v3_intelligence returns ZERO matches; no `viterbi.py` in V2; `hasattr(HMMGARCHRegimeDetector, 'predict_viterbi') is False`; `hasattr(HMMGARCHRegimeDetector, '_compute_log_emission_probs') is False`; test_viterbi_ban.py 3/3 GREEN |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `V2/v3_intelligence/regime/__init__.py` | Subpackage with public surface re-exports + bars_to_log_returns | VERIFIED | Imports of HMMGARCHRegimeDetector, OnlineRegimeFilter, RegimeState, GARCHParams, garch_emission_prob, bars_to_log_returns, save_detector, load_detector all resolve at runtime |
| `V2/v3_intelligence/regime/types.py` | RegimeState IntEnum (D-22) | VERIFIED | TRENDING=0, MEAN_REVERTING=1, CRISIS=2 — confirmed via direct enum iteration |
| `V2/v3_intelligence/regime/emissions.py` | GARCHParams + garch_emission_prob (V1 verbatim) | VERIFIED | Imports cleanly; 5/5 emissions tests GREEN |
| `V2/v3_intelligence/regime/hmm_garch.py` | HMMGARCHRegimeDetector minus Viterbi (D-04) | VERIFIED | Class importable; predict_viterbi + _compute_log_emission_probs ABSENT at runtime; 9/9 detector tests GREEN |
| `V2/v3_intelligence/regime/online_filter.py` | Forward-algorithm filter; update returns (RegimeState, float) per D-21 | VERIFIED | 177 lines (was 11-line placeholder in Plan 02); 5/5 online_filter tests GREEN; live load+update on all 5 JSONs returns valid (RegimeState, float) |
| `V2/v3_intelligence/regime/persistence.py` | save_detector / load_detector with D-11 schema | VERIFIED | SCHEMA_VERSION=1; STATE_LABELS=["TRENDING", "MEAN_REVERTING", "CRISIS"]; 4/4 persistence tests GREEN |
| `V2/v3_intelligence/pit.py` | PitClock + FutureBarReadError + UNBOUNDED + pit_gated | VERIFIED | All four symbols present; `PitClock.UNBOUNDED = PitClock(None)` constructed at module load (line 109); 8/8 pit tests GREEN |
| `V2/scripts/fit_regime_detectors.py` | Offline-fit CLI per D-13/D-26 | VERIFIED | argparse rejects unknown pairs; idempotent SKIP on existing JSON; D-26 fail-fast contract intact |
| `V2/data/regime/USDJPY_detector.json` | Fitted detector, variance ordering visible | VERIFIED | schema_version=1; variances [9.17e-7, 1.39e-6, 9.01e-5] monotone asc; ratio 98.2x; v1_parity_tested=True |
| `V2/data/regime/GBPJPY_detector.json` | Fitted detector | VERIFIED | variances [8.75e-7, 1.40e-6, 7.32e-5] monotone asc; ratio 83.7x; v1_parity_tested=True |
| `V2/data/regime/GBPAUD_detector.json` | Fitted detector | VERIFIED | variances [6.00e-7, 9.30e-7, 5.13e-5] monotone asc; ratio 85.4x; v1_parity_tested=True |
| `V2/data/regime/GBPUSD_detector.json` | Fitted detector | VERIFIED | variances [5.79e-7, 9.68e-7, 5.86e-5] monotone asc; ratio 101.3x; v1_parity_tested=True |
| `V2/data/regime/EURGBP_detector.json` | Fitted detector | VERIFIED | variances [3.40e-7, 2.00e-5, 2.36e-5] monotone asc; ratio 69.4x; v1_parity_tested=True |
| `V2/pyproject.toml` | hmmlearn>=0.3 + arch>=6.0 added | VERIFIED | Resolved versions hmmlearn 0.3.3 + arch 8.0.0 (per Plan 02 SUMMARY); fit suite passes against active env |

**No viterbi.py file** in V2/v3_intelligence/regime/ — confirmed by `ls` returning "No such file or directory" (D-04 satisfied).

**V1 calibration.py NOT ported** — `grep -n "calibration\|RecalibrationService" V2/v3_intelligence/regime/*.py` returns zero matches (D-14 satisfied).

---

### Key Link Verification (Wiring)

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `v3_intelligence.regime` public surface | Phase 9 router consumers | Top-level `__init__.py` re-exports | WIRED | `from v3_intelligence import RegimeState, PitClock, FutureBarReadError, OnlineRegimeFilter` resolves cleanly |
| `load_detector(json)` | `OnlineRegimeFilter(det).update(r)` | `detector_registry[pair].update(...)` Phase 9 contract | WIRED | Smoke loop over all 5 detector JSONs returns valid (RegimeState, float) tuples per D-21 |
| `HMMGARCHRegimeDetector.fit()` | `_remap_matrix` + variance-rank sort | REGM-02 by-construction | WIRED | V1 sort line ported verbatim; test_variance_rank_pinning + test_refit_preserves_ordering both GREEN |
| `PitClock.advance(t)` + `clock.assert_no_future(t+1h)` | Future-bar guard | D-09 contract | WIRED | test_assert_no_future_raises_on_future_ts GREEN; test_advance_must_be_monotone GREEN; UNBOUNDED sentinel verified at line 109 |
| `bars_to_log_returns(df)` | Detector input contract D-19/D-20 | Helper at regime/__init__.py | WIRED | 4/4 tests GREEN; accepts both 'close' and 'Close' columns for Phase 7 CSV compat |
| `fit_regime_detectors.py` | `save_detector(det, ...)` | CLI persistence path | WIRED | All 5 JSONs on disk demonstrate the path works end-to-end |
| `test_viterbi_ban.py` (functional regex) | V2/backtest, V2/v3_intelligence, V2/live | REGM-04 grep gate | WIRED | 3/3 tests GREEN (literal-substring → functional regex per Plan 04 refinement); zero functional Viterbi imports/calls/attribute access detected |
| `rag_signal_filter.py` | Untouched in Phase 8 (D-29) | git log | WIRED | Last (only) commit is initial — no Phase 8 modifications |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| **REGM-01** | 08-02 (offline) + 08-03 (online) | HMM-GARCH classifier ported with offline fit + online update split | SATISFIED | `HMMGARCHRegimeDetector.fit()` + `OnlineRegimeFilter.update()` split confirmed; subpackage layout per D-01/D-02; 18 tests GREEN (Plan 02) + 5 tests GREEN (Plan 03) |
| **REGM-02** | 08-02 | State labels pinned by variance rank at fit time | SATISFIED | V1 `_remap_matrix` ported verbatim; all 5 detector JSONs show monotone ascending variances; `test_refit_preserves_ordering` GREEN |
| **REGM-03** | 08-03 | PiT manager enforces no future-bar read | SATISFIED | `V2/v3_intelligence/pit.py` with `PitClock` + `FutureBarReadError` + `UNBOUNDED`; 8 PiT tests GREEN |
| **REGM-04** | 08-04 | OnlineRegimeFilter sole regime source — Viterbi banned | SATISFIED | Functional grep gate 3/3 GREEN; no `viterbi.py`; `predict_viterbi` + `_compute_log_emission_probs` absent at runtime; only docstring/comment references remain (intentional, document the deliberate omission) |

**No orphaned requirements.** REQUIREMENTS.md lines 26–29 and lines 86–89 list exactly REGM-01..04 mapped to Phase 8, all marked Complete; every ID is also present in at least one Plan SUMMARY's `requirements-completed` field.

---

### Decision Compliance Audit (D-01..D-29)

| Decision | Description | Compliance |
|----------|-------------|------------|
| D-01 | regime/ subpackage layout | VERIFIED — all 6 expected files present, no viterbi.py |
| D-03 | hmmlearn + arch added to pyproject | VERIFIED — Plan 02 commit + active env resolves 0.3.3 + 8.0.0 |
| D-04 | Viterbi entirely dropped | VERIFIED — predict_viterbi + _compute_log_emission_probs absent at runtime |
| D-05 | Grep gate test_viterbi_ban.py | VERIFIED — 3/3 GREEN, refined to functional regex per Plan 04 |
| D-06 | PitClock pandas-native, no ArcticDB | VERIFIED — pit.py imports only pandas/typing; no arcticdb anywhere |
| D-09 | Out-of-order read raises | VERIFIED — test_assert_no_future_raises_on_future_ts GREEN |
| D-10 | 5 detectors total | VERIFIED — 5 JSON files in V2/data/regime/ |
| D-11 | JSON+numpy persistence with full schema | VERIFIED — schema_version=1, garch_params, transmat, startprob, variance_ordering, fit_metadata all present |
| D-12 | No V1 imports in V2 | VERIFIED — grep `from\s+src\|from\s+V1\|import\s+V1\.` returns zero functional matches in V2/v3_intelligence + V2/backtest + V2/scripts |
| D-13 | Standalone fit CLI | VERIFIED — V2/scripts/fit_regime_detectors.py present and exit-clean |
| D-14 | calibration.py NOT ported (deferred to v3.0) | VERIFIED — no calibration.py / RecalibrationService in V2 regime subpackage |
| D-16/D-17/D-18 | Statistical parity within tolerance, slow-marked | VERIFIED — 4/4 slow parity tests GREEN |
| D-21 | update() returns (RegimeState, float) | VERIFIED — runtime smoke on all 5 pairs returns isinstance(RegimeState, float) tuples |
| D-22 | RegimeState in regime/types.py | VERIFIED — values TRENDING=0, MEAN_REVERTING=1, CRISIS=2 |
| D-25 | PitClock.UNBOUNDED sentinel | VERIFIED — line 109 of pit.py: `PitClock.UNBOUNDED = PitClock(None)` |
| D-26 | CLI fail-fast on unknown pair | VERIFIED — argparse rejects FAKEUSD with "invalid choice" error |
| D-29 | rag_signal_filter.py untouched | VERIFIED — git log shows only the initial commit, no Phase 8 modifications |

All 29 decisions either reflected in code or correctly excluded.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `V2/v3_intelligence/regime/__init__.py` | 4 | "Viterbi banished — no viterbi.py, no predict_viterbi method." | Info | Docstring explicitly documents the D-04 deliberate omission. Permitted by Plan 04's functional-regex grep gate refinement. NOT a stub. |
| `V2/v3_intelligence/regime/hmm_garch.py` | 6, 7, 46, 47 | Docstring lines mentioning "predict_viterbi" / "_compute_log_emission_probs" / "Viterbi" | Info | Same — intentional documentation of D-04 omission. Functional grep gate confirms zero actual code calls/imports/attribute access. |

**No blocker anti-patterns.** No TODO/FIXME/XXX/HACK markers found in production code paths. No empty `return null` / `return []` placeholders in non-stub paths. No console.log-only handlers. No hardcoded empty data flowing to Phase 9 contract.

---

### Test Suite Status

| Suite | Status | Count | Notes |
|-------|--------|-------|-------|
| `tests/v3_intelligence/test_emissions.py` | GREEN | 5/5 | Plan 02 |
| `tests/v3_intelligence/test_bars_to_log_returns.py` | GREEN | 4/4 | Plan 02 |
| `tests/v3_intelligence/test_regime_detector.py` | GREEN | 9/9 | Plan 02 |
| `tests/v3_intelligence/test_online_filter.py` | GREEN | 5/5 | Plan 03 |
| `tests/v3_intelligence/test_pit.py` | GREEN | 8/8 | Plan 03 |
| `tests/v3_intelligence/test_persistence.py` | GREEN | 4/4 | Plan 03 |
| `tests/v3_intelligence/test_viterbi_ban.py` | GREEN | 3/3 | Plan 04 (refined 2→3 tests) |
| `tests/v3_intelligence/test_regime_parity.py` (slow) | GREEN | 4/4 | Plan 04 D-16 phase gate |
| **v3_intelligence subtotal** | **GREEN** | **42/42** | (fast + slow combined) |
| **Full V2 fast suite** | **GREEN** | **108/108** | Phase 6 + Phase 7 + Phase 8 — no cross-phase regression |
| **Full V2 fast + slow suite** | **GREEN** | **112/112** | 108 fast + 4 slow parity |

Verifier independently reproduced both runs (~3.05s fast Phase 8; ~99.18s full slow+fast).

---

### Phase 9 Readiness Check

Live load+update smoke test by verifier (independent of Plan 04 SUMMARY):

| Pair | `load_detector()` | `is_fitted` post-load | First `update(0.001)` | Tuple type |
|------|-------------------|------------------------|----------------------|-----------|
| USDJPY | OK | True | (TRENDING, 0.5684) | (RegimeState, float) |
| GBPJPY | OK | True | (TRENDING, 0.9987) | (RegimeState, float) |
| GBPAUD | OK | True | (MEAN_REVERTING, 0.5126) | (RegimeState, float) |
| GBPUSD | OK | True | (TRENDING, 0.5295) | (RegimeState, float) |
| EURGBP | OK | True | (TRENDING, 0.9995) | (RegimeState, float) |

Phase 9 router can build `detector_registry: dict[str, OnlineRegimeFilter]` from `V2/data/regime/*.json` and consume the D-21 contract per bar. ROUT-04 4yr simulation is unblocked (modulo Phase 8.5 prerequisite per ROADMAP).

---

### Failover Caveat (Documented, Accepted)

All 5 detectors were fitted on **730d-shape H1 data** (~17k bars per pair), filenamed `*_H1_4yr.csv` per Phase 7 D-15 naming continuity. The full 4yr fetch (~35k bars) was unavailable on the Linux dev host because the `MetaTrader5` Python package is Windows-only. Plan 04 applied D-15's documented Linux-failover path and the operator approved this at checkpoint.

This is a **known/accepted limitation**, not a verification failure:

- All 5 detectors converged cleanly (no fit failures).
- All 5 show strong regime separation (CRISIS/TRENDING ratios 69x–101x, well above 5x sanity threshold).
- D-16 parity gate cleared at rtol=1e-6 against V1 baseline.
- Phase 9 ROUT-04 contract is fit-window-independent.

A Windows MT5 detector refresh is **recommended before LIVE-04 paper trade gate**. This is captured in Plan 04 SUMMARY's "Failover Caveat" section and tracked in STATE.md key decisions for Phase 10 readiness. v3.0 EXPN-03 walk-forward retraining will eventually moot the concern.

---

### Human Verification Required

None. Operator already approved the Plan 04 checkpoint payload (variance-ordering table, Phase 9 detector_registry smoke test, REGM-04 grep gate sweep, full-suite test results) on 2026-04-25 with no caveats, no notes, no blocks. All four Success Criteria from ROADMAP.md verify automatically and have been independently re-verified by this report.

---

## Gaps Summary

**No gaps.** Phase 8 goal achievement is complete:

- Subpackage layout (D-01) lands as specified — six files, no viterbi.py.
- Two-stage offline-fit / online-update split (REGM-01) is operational; smoke test on all 5 pairs returns valid `(RegimeState, float)` tuples per D-21.
- Variance-rank pinning (REGM-02) is satisfied by-construction via verbatim port of V1's `_remap_matrix`; both unit tests + the persisted JSON metadata confirm monotone ascending variances on every pair.
- PitClock (REGM-03) raises `FutureBarReadError` on out-of-order reads as required by D-09; UNBOUNDED sentinel (D-25) is constructed at module load.
- Viterbi ban (REGM-04) is enforced by a functional-regex grep gate that catches imports + calls + attribute access; defense-in-depth file scan; 3/3 GREEN. Five docstring/comment references documenting the deliberate D-04 omission are intentional and do not represent functional Viterbi code.
- Phase 9 detector_registry contract (Phase 9 ROUT-04 dependency) is verified end-to-end: all 5 JSONs deserialise and produce valid online updates.
- Cross-phase regression: full V2 fast suite 108/108 GREEN; slow parity tests 4/4 GREEN; Phase 6 (53) + Phase 7 (17) + Phase 8 (38 fast + 4 slow) reconcile to the documented totals.
- All 29 locked CONTEXT.md decisions either reflect in code or correctly excluded (D-14 calibration deferred; D-29 rag_signal_filter untouched).
- Linux-failover caveat for 4yr fit window is documented, operator-acknowledged, and non-blocking for Phase 9; flagged as a Phase 10 LIVE-04 prerequisite.

Phase 8 gate **CLEARED** for handoff to Phase 8.5 (Temporal & Session Analysis), then Phase 9 (Strategy Router).

---

*Verified: 2026-04-25*
*Verifier: Claude (gsd-verifier, Opus 4.7)*
