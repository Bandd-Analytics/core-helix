---
phase: 09-strategy-router
plan: 03
subsystem: v3_intelligence/regime + scripts/fit_regime_detectors
tags: [detector-inventory, hmm-garch, 8-pair, pitfall-3-closure, regm-02, parallel-wave-1]
one_liner: "Detector inventory expanded from 5 → 8 — fitted GBPNZD/EURUSD/AUDNZD HMM-GARCH JSONs (variance ratios 66.6x/47.7x/47.8x) and refactored fit_regime_detectors.py to source ACTIVE_PAIRS from PAIR_CONFIGS.keys() (Pitfall #3 closed)"
dependency_graph:
  requires:
    - V2/v3_intelligence/pair_config.py            # PAIR_CONFIGS — 8 keys, source of truth
    - V2/v3_intelligence/regime/hmm_garch.py       # HMMGARCHRegimeDetector + fit()
    - V2/v3_intelligence/regime/persistence.py     # save_detector / load_detector schema_version=1
    - V2/data/GBPNZD_H1_4yr.csv                    # Phase 8.4 INFRA-02 fill
    - V2/data/EURUSD_H1_4yr.csv                    # Phase 7 era 4yr corpus
    - V2/data/AUDNZD_H1_4yr.csv                    # Phase 7 era 4yr corpus (8159 bars — 16mo)
  provides:
    - "V2/data/regime/GBPNZD_detector.json — HMM-GARCH detector, ratio=66.6x, seed=0"
    - "V2/data/regime/EURUSD_detector.json — HMM-GARCH detector, ratio=47.7x, seed=1 (boundary GARCH at seed 0)"
    - "V2/data/regime/AUDNZD_detector.json — HMM-GARCH detector, ratio=47.8x, seed=0 (n_bars=8159)"
    - "V2/scripts/fit_regime_detectors.py — ACTIVE_PAIRS sourced from PAIR_CONFIGS.keys() (Pitfall #3 closure)"
    - "Auto-retry seeds [0,1,2,3] for new pairs that hit GARCH stationarity boundary"
  affects:
    - "Plan 04 ROUT-04 simulator can now load 8 OnlineRegimeFilters (one per active pair)"
    - "tests/v3_intelligence/test_detector_inventory.py: 1 RED + 3 SKIPPED → 9 PASSED"
tech-stack:
  added: []
  patterns:
    - "Dynamic ACTIVE_PAIRS = list(PAIR_CONFIGS.keys()) — adapts when pairs added/removed (D-19)"
    - "Self-healing seed retry [0,1,2,3] inside _fit_one() — preserves Phase 8 parity (5 existing detectors fitted at seed 0) while unblocking low-vol pairs"
    - "v1_parity_tested=False for new pairs (RESEARCH §7 — V1 never had baseline data for GBPNZD/EURUSD/AUDNZD)"
    - "Idempotency D-13 preserved: existing 5 detectors byte-untouched (mtimes April 25 confirmed)"
key-files:
  created:
    - V2/data/regime/GBPNZD_detector.json
    - V2/data/regime/EURUSD_detector.json
    - V2/data/regime/AUDNZD_detector.json
  modified:
    - V2/scripts/fit_regime_detectors.py  # +12 / -2 dynamic ACTIVE_PAIRS, +seed retry
decisions:
  - "Auto-retry seeds [0,1,2,3] inside _fit_one() rather than adding a --random-state CLI flag — preserves the 'fit is deterministic per pair' contract while making the script self-healing for new low-vol pairs (Rule 3 deviation, plan Step 3 honored: 'after 3 retries flag for operator review')"
  - "EURUSD seed=0 hits GARCH boundary (alpha+beta=1.0000, IGARCH-like, common for low-vol majors); seed=1 converges with ratio 47.7x (above 10x floor, below 50x optimal — flagged MEDIUM-confidence in operator log)"
  - "AUDNZD has only 8159 bars (~16 months, not 4yr) — fit converges at seed=0 with ratio 47.8x; flagged for Plan 04 awareness (shorter window may impact tail-state sample quality)"
  - "Phase 8's existing 5 detectors all converge at seed=0 → byte-identical to disk; only 3 new files added"
metrics:
  duration: "13m 0s"
  completed: "2026-04-29T00:24:09Z"
  tasks: 2
  files: 4
  commits: 2
---

# Phase 09 Plan 03: Detector Inventory Expansion Summary

## One-Liner

Detector inventory expanded from 5 → 8 — fitted `GBPNZD/EURUSD/AUDNZD` HMM-GARCH JSONs (variance ratios 66.6x / 47.7x / 47.8x) and refactored `fit_regime_detectors.py` to source `ACTIVE_PAIRS` from `PAIR_CONFIGS.keys()` (Pitfall #3 closed). Phase 9 D-19 prerequisite for ROUT-04 satisfied; all 8 active pairs now have `OnlineRegimeFilter`-loadable detectors.

## Tasks Executed

| # | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Refactor `fit_regime_detectors.py` to source `ACTIVE_PAIRS` from `PAIR_CONFIGS.keys()` | `b6dc206` | `V2/scripts/fit_regime_detectors.py` |
| 2 | Fit + persist GBPNZD/EURUSD/AUDNZD detectors | `06931fb` | `V2/scripts/fit_regime_detectors.py` (seed retry), `V2/data/regime/{GBPNZD,EURUSD,AUDNZD}_detector.json` |

## Files Delivered

| File | Type | Notes |
| --- | --- | --- |
| `V2/scripts/fit_regime_detectors.py` | MODIFIED (+12 -2 in T1, +20 -5 in T2) | ACTIVE_PAIRS dynamic; docstring updated; seed retry [0,1,2,3] inside _fit_one |
| `V2/data/regime/GBPNZD_detector.json` | NEW (1415 bytes) | n_bars=24871, ratio=66.6x, seed=0 — STRONG (in-band with Phase 8) |
| `V2/data/regime/EURUSD_detector.json` | NEW (1446 bytes) | n_bars=24873, ratio=47.7x, seed=1 — MEDIUM (boundary GARCH at seed=0) |
| `V2/data/regime/AUDNZD_detector.json` | NEW (1351 bytes) | n_bars=8159, ratio=47.8x, seed=0 — MEDIUM (16mo data window) |

## Variance-Ratio Audit (max/min unconditional_variance)

| Pair | Ratio | Tier | n_bars | Seed | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| **GBPNZD** | **66.6x** | STRONG | 24,871 | 0 | In-band with Phase 8 (EURGBP=69.4x); 4yr H1 corpus from Phase 8.4 INFRA-02 |
| **EURUSD** | **47.7x** | MEDIUM | 24,873 | 1 | Boundary GARCH at seed=0 (State 1: alpha+beta=1.0000); seed=1 clean |
| **AUDNZD** | **47.8x** | MEDIUM | 8,159 | 0 | Short data window (~16 months) — Plan 04 should be aware |

**Reference Phase 8 ratios:** USDJPY=98.2x, GBPJPY=83.7x, GBPAUD=85.4x, GBPUSD=101.3x, EURGBP=69.4x. New pairs all clear the 10x floor (RESEARCH §7) but two sit below the 50x "optimal" line — documented MEDIUM-confidence per plan Step 4.

## ACTIVE_PAIRS — Now vs Then

| State | Definition | Resolves To |
| --- | --- | --- |
| **Before** | `ACTIVE_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP"]` (Phase 8 D-10 hardcoded literal) | 5 pairs |
| **After** | `ACTIVE_PAIRS: list[str] = list(PAIR_CONFIGS.keys())` (Phase 9 D-19) | 8 pairs: USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP, GBPNZD, EURUSD, AUDNZD |

Pitfall #3 closed (RESEARCH §8) — `fit_regime_detectors.py` now auto-adapts when `pair_config.PAIR_CONFIGS` gains/loses keys. Memory feedback `feedback_8pairs_multi_timeframe.md` ("never silently narrow scope") honored.

## Test Transition

| File | Before Plan 03 | After Plan 03 |
| --- | --- | --- |
| `test_detector_inventory.py::test_all_active_pairs_have_detector_json` | RED (3 missing: GBPNZD/EURUSD/AUDNZD) | **GREEN** |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[USDJPY]` | GREEN | GREEN (unchanged) |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[GBPJPY]` | GREEN | GREEN (unchanged) |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[GBPAUD]` | GREEN | GREEN (unchanged) |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[GBPUSD]` | GREEN | GREEN (unchanged) |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[EURGBP]` | GREEN | GREEN (unchanged) |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[GBPNZD]` | SKIPPED | **GREEN** |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[EURUSD]` | SKIPPED | **GREEN** |
| `test_detector_inventory.py::test_detector_variance_ordering_monotone[AUDNZD]` | SKIPPED | **GREEN** |

**Net delta:** 1 RED + 3 SKIPPED → **9 PASSED**.

Full v3_intelligence regression (`pytest tests/v3_intelligence/ -q`): 156 passed, 1 failed (`test_router_simulation_module_importable` — Plan 04 territory), 20 deselected (slow). Plan 02's parallel work (router 4-gate chain) also turned its 8 RED tests GREEN — confirmed via isolated `tests/v3_intelligence/test_router.py` run (9 passed).

Cross-suite (`pytest tests/ -m "not slow" --cache-clear`): 226 passed, 1 failed (Plan 04 Sim importability), 20 deselected — no Plan 03 regressions.

## Idempotency Verification (D-13)

`python -m scripts.fit_regime_detectors --pair all` (post-fit re-run): produces 8 SKIP lines and exit 0. Existing 5 Phase 8 detectors confirmed byte-untouched (mtimes April 25, 12:37 — preserved verbatim).

## Pitfall #3 Closure Verification

```python
from scripts.fit_regime_detectors import ACTIVE_PAIRS
from v3_intelligence.pair_config import PAIR_CONFIGS
assert ACTIVE_PAIRS == list(PAIR_CONFIGS.keys())
# PASS — Pitfall #3 closed: ['USDJPY', 'GBPJPY', 'GBPAUD', 'GBPUSD', 'EURGBP', 'GBPNZD', 'EURUSD', 'AUDNZD']
```

Acceptance grep counts:

| Pattern | Hits | Required |
| --- | ---: | --- |
| `'^ACTIVE_PAIRS\s*=\s*\["USDJPY"'` (hardcoded literal) | 0 | 0 |
| `'PAIR_CONFIGS.keys()'` | 2 | ≥1 |
| `'from v3_intelligence.pair_config import PAIR_CONFIGS'` | 1 | 1 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] EURUSD GARCH boundary at seed=0**
- **Found during:** Task 2, first `--pair all` run.
- **Issue:** EURUSD's State 1 GARCH fit hits boundary `alpha+beta=1.0000` (IGARCH-like, common for low-vol majors with std~1e-3) under default `random_state=0`, causing `HMMGARCHRegimeDetector.fit()` to return `False` and the script to exit non-zero per D-26. Pre-fit return-quality check confirmed data was healthy (24,872 finite log-returns, 0 NaN, 0.7% zeros, mean=3.8e-6, std=1.04e-3) — the failure was numerical, not data-quality.
- **Fix:** Extended `_fit_one()` to retry seeds `[0, 1, 2, 3]` in order, taking first convergent fit. Plan 09-03 Step 3 explicitly authorizes this: "If a pair completely fails to converge after 3 retries with `--force`, flag for operator review". Implemented as automatic in-script retry rather than separate `--force` re-runs to keep the script self-healing for future pairs. EURUSD converges at `seed=1` with ratio 47.7x (above 10x floor).
- **Files modified:** `V2/scripts/fit_regime_detectors.py` (`_fit_one` body + docstring).
- **Commit:** `06931fb` (combined with Task 2 detector creation).
- **Phase 8 parity preserved:** All 5 existing detectors converged at seed=0 originally — they remain byte-identical (idempotent SKIP path takes precedence over re-fit). The retry only kicks in for new pairs.

### Out-of-Scope Discoveries

None. Plan 03 touched exactly the files declared in `<files>` (1 script + 3 new JSONs).

## Authentication Gates

None — pure local fit work. No external service auth needed (CSVs already on disk from Phase 8.4 INFRA-02 + Phase 7 P04, per RESEARCH §7).

## Hand-off to Plan 04

| Resource | Status | Plan 04 Use |
| --- | --- | --- |
| 8 detector JSONs at `V2/data/regime/{PAIR}_detector.json` | Available | `OnlineRegimeFilter(load_detector(...))` per pair in router_simulation.py |
| `ACTIVE_PAIRS = list(PAIR_CONFIGS.keys())` | Live | Plan 04 simulator iterates the same 8 keys (no separate hardcoded list to drift) |
| `test_detector_inventory.py` | 9/9 GREEN | Regression-protects Plan 04's 4yr loop assumption |

**Caveats for Plan 04 simulator:**
- AUDNZD detector fitted on 8,159 H1 bars (~16 months), not 4yr — fewer tail-state samples than other pairs. Verify Plan 04 PiT loop end-time matches detector fit window or document the gap.
- EURUSD/AUDNZD variance ratios 47.7x / 47.8x sit below the 50x line — fine for routing decisions but flag if Plan 04 finds CRISIS-state signals firing inappropriately on these pairs.

## CONTEXT D-19 Compliance

> "Phase 8 produced 5 OnlineRegimeFilter detector JSONs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP). Phase 9 must grow this to 8 active pairs (add GBPNZD/EURUSD/AUDNZD) before the ROUT-04 simulation can run."

- `ls V2/data/regime/*_detector.json | wc -l` → **8** (was 5) ✓
- All 8 JSONs parseable by `load_detector(...)` ✓
- All 8 have `variance_ordering.unconditional_variances` strictly increasing (REGM-02 visible) ✓
- 3 new JSONs have `v1_parity_tested: false` (RESEARCH §7 honest provenance) ✓
- Existing 5 byte-identical (idempotent — D-13) ✓
- `fit_regime_detectors.py` sources `ACTIVE_PAIRS` from `PAIR_CONFIGS.keys()` (Pitfall #3 closed) ✓

## Self-Check: PASSED

Files exist on disk:
- `V2/scripts/fit_regime_detectors.py`: FOUND (114 lines after edits)
- `V2/data/regime/GBPNZD_detector.json`: FOUND (1415 bytes)
- `V2/data/regime/EURUSD_detector.json`: FOUND (1446 bytes)
- `V2/data/regime/AUDNZD_detector.json`: FOUND (1351 bytes)

Commits in `git log`:
- `b6dc206` refactor(09-03): source ACTIVE_PAIRS from PAIR_CONFIGS.keys(): FOUND
- `06931fb` feat(09-03): fit + persist GBPNZD/EURUSD/AUDNZD detectors: FOUND

Verification commands all pass:
- ACTIVE_PAIRS dynamic: 8 pairs from PAIR_CONFIGS.keys() — exit 0
- `test_detector_inventory.py`: 9 passed (1 inventory + 8 variance) — exit 0
- Phase 6/7/8/8.4/8.5/9-02 fast-suite regression: 226 passed / 1 failed (Plan 04 RED) — no Plan 03 regressions
- Idempotent re-run: 8 SKIP lines on `--pair all` second invocation — exit 0
- Existing 5 Phase 8 detectors: untouched (mtimes April 25 12:37 preserved)

No stubs leak. The 3 new JSONs are real fitted detectors with monotone variance ordering and proper persistence schema (schema_version=1). The seed-retry logic in `_fit_one` is functional, not a stub.
