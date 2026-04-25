---
phase: 8
slug: hmm-garch-regime-pit-port
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `08-RESEARCH.md` §11 Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured in V2/pyproject.toml lines 7-14) |
| **Config file** | `V2/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/v3_intelligence -x` |
| **Full suite command** | `pytest tests/v3_intelligence -m 'slow or not slow' -x` |
| **Estimated runtime** | ~30s quick / 1–3 min full (parity tests are slow) |

The default `addopts = "-v -m 'not slow'"` excludes parity tests from fast runs; they run on demand or per-wave-merge.

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/v3_intelligence -x` (~ < 30s, excludes `slow`)
- **After every plan wave:** Run `pytest tests/v3_intelligence -m 'slow or not slow' -x` (parity included; 1–3 min)
- **Before `/gsd:verify-work`:** Full suite must be green + 5/5 detector JSON files exist in `V2/data/regime/*.json` + `test_viterbi_ban` clean
- **Max feedback latency:** 30 seconds for fast suite

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| REGM-01 (structural) | Subpackage exists; nothing in V2 imports from V1 | unit + grep | `pytest tests/v3_intelligence/test_regime_detector.py::test_subpackage_layout -x` | ❌ Wave 0 | ⬜ pending |
| REGM-01 (behavioral) | `HMMGARCHRegimeDetector.fit()` returns True on synthetic three-regime returns | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_fit_returns_true -x` | ❌ Wave 0 | ⬜ pending |
| REGM-01 (behavioral) | `OnlineRegimeFilter.update()` returns `(RegimeState, float)` after detector fit | unit | `pytest tests/v3_intelligence/test_online_filter.py::test_update_returns_state_conf -x` | ❌ Wave 0 | ⬜ pending |
| REGM-02 | After `fit()`, `garch_params[i].unconditional_variance` is monotonically increasing | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_variance_rank_pinning -x` | ❌ Wave 0 | ⬜ pending |
| REGM-02 | Re-fit on perturbed (+1e-7 shift) returns preserves state ordering | unit | `pytest tests/v3_intelligence/test_regime_detector.py::test_refit_preserves_ordering -x` | ❌ Wave 0 | ⬜ pending |
| REGM-03 | `PitClock(t)` raises `FutureBarReadError` on access past `as_of_ts` | unit | `pytest tests/v3_intelligence/test_pit.py::test_assert_no_future_raises_on_future_ts -x` | ❌ Wave 0 | ⬜ pending |
| REGM-03 | `PitClock.UNBOUNDED` allows reads of any timestamp | unit | `pytest tests/v3_intelligence/test_pit.py::test_unbounded_sentinel_allows_any_read -x` | ❌ Wave 0 | ⬜ pending |
| REGM-03 | `clock.read(df)` returns rows with index ≤ as_of when df extends beyond cutoff | unit | `pytest tests/v3_intelligence/test_pit.py::test_read_returns_truncated_view -x` | ❌ Wave 0 | ⬜ pending |
| REGM-04 | Grep finds zero `viterbi`/`Viterbi`/`predict_viterbi` in V2/backtest, V2/v3_intelligence, V2/live | grep gate | `pytest tests/v3_intelligence/test_viterbi_ban.py -x` | ❌ Wave 0 | ⬜ pending |
| Port faithfulness (D-16) | V2 GARCHParams within rtol=1e-6 of V1 baseline | parity / slow | `pytest tests/v3_intelligence/test_regime_parity.py -m slow -x` | ❌ Wave 0 | ⬜ pending |
| Port faithfulness (D-16) | V2 OnlineRegimeFilter state agreement ≥ 95% with V1 baseline on synthetic returns | parity / slow | `pytest tests/v3_intelligence/test_regime_parity.py::test_online_state_agreement -m slow -x` | ❌ Wave 0 | ⬜ pending |
| Persistence integrity (D-11) | save→load roundtrip preserves all fitted parameters within 1e-12 | unit | `pytest tests/v3_intelligence/test_persistence.py::test_save_then_load_roundtrip -x` | ❌ Wave 0 | ⬜ pending |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/v3_intelligence/__init__.py` — package marker
- [ ] `tests/v3_intelligence/conftest.py` — `synthetic_three_regime_returns`, `v1_baseline` fixtures
- [ ] `tests/v3_intelligence/parity_baseline.npz` — captured from V1 (one-time, committed)
- [ ] `tests/v3_intelligence/_capture_v1_baseline.py` — generator script (committed but not run in CI)
- [ ] `tests/v3_intelligence/test_regime_detector.py` — RED stubs for REGM-01 (structural+behavioral) and REGM-02
- [ ] `tests/v3_intelligence/test_online_filter.py` — RED stubs for OnlineRegimeFilter.update() contract
- [ ] `tests/v3_intelligence/test_emissions.py` — RED stubs for GARCHParams stationarity property + emission prob
- [ ] `tests/v3_intelligence/test_pit.py` — RED stubs for REGM-03 PitClock + UNBOUNDED sentinel
- [ ] `tests/v3_intelligence/test_viterbi_ban.py` — RED stub for REGM-04 grep gate
- [ ] `tests/v3_intelligence/test_persistence.py` — RED stub for save/load JSON roundtrip
- [ ] `tests/v3_intelligence/test_bars_to_log_returns.py` — RED stubs for the helper
- [ ] `tests/v3_intelligence/test_regime_parity.py` — RED stub marked `@pytest.mark.slow`
- [ ] Framework install: `pip install 'hmmlearn>=0.3' 'arch>=6.0'` (ensure resolves; document resolved versions in `V2/pyproject.toml` comment)

Pytest is already configured — no install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Detector JSON layout is human-readable & inspectable | D-11 / REGM-02 visibility | Inspection of variance_ordering metadata is forensic, not algorithmic | After `python -m scripts.fit_regime_detectors --pair USDJPY`, open `V2/data/regime/USDJPY_detector.json`; verify `variance_ordering.unconditional_variances` is monotonically increasing and `state_labels` reads `["TRENDING", "MEAN_REVERTING", "CRISIS"]` |
| Failed fit propagates non-zero exit code | D-26 | Exit-code semantics are CLI-shell concern; integration test sufficient but final gate is operator confirmation | Run `python -m scripts.fit_regime_detectors --pair FAKEUSD` (no data file). Confirm: exit code is non-zero (`echo $?` ≠ 0); no JSON written; stderr mentions reason |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for fast suite
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
