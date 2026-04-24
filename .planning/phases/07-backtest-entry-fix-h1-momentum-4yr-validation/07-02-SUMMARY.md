---
phase: 07-backtest-entry-fix-h1-momentum-4yr-validation
plan: "02"
subsystem: backtest-engine
tags: [entry-fix, look-ahead-bias, sharpe-correction, BKTS-01]
dependency_graph:
  requires: ["07-01"]
  provides: ["BKTS-01"]
  affects: ["07-03", "07-04"]
tech_stack:
  added: []
  patterns:
    - next-bar-open fill simulation (entry_px = next_row['Open'])
    - loop bound adjustment (len(data) - 1) to prevent IndexError on last bar
    - entry_bar_ts tracking for unit-test invariant assertion
key_files:
  created:
    - V2/tests/unit_tests/backtest/__init__.py
    - V2/tests/unit_tests/backtest/test_entry_fix.py
    - V2/backtest/reports/compare_entry_bias.py
    - V2/backtest/reports/entry_bias_comparison.csv
  modified:
    - V2/backtest/backtest_hybrid.py
    - V2/backtest/backtest_evaluate_all.py
decisions:
  - "entry_bar_ts recorded in position dict so tests can assert next-bar-open equality without a separate index lookup"
  - "M15 loop bound kept at range(50, len(m15)-1) matching existing start of 50, not changed to 100 (plan assumed wrong start)"
  - "CSV force-added to git with -f flag since *.csv is in .gitignore; justified as committed evidence artifact for BKTS-01 D-02"
  - "momentum test uses z_threshold=0.5 and n=2000 bars to ensure trades generated on synthetic data"
metrics:
  duration_seconds: 498
  completed_date: "2026-04-24"
  tasks_completed: 3
  files_changed: 6
---

# Phase 07 Plan 02: Entry Bias Fix + Before/After Comparison Report Summary

Next-bar-open entry fix applied to all 5 strategy loops (swing + M15 in backtest_hybrid.py; swing + scalp + momentum in Evaluator), loop bounds adjusted to prevent IndexError, and a 15-row before/after Sharpe CSV committed as BKTS-01 evidence.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 + 2 | BKTS-01 entry fix (hybrid + evaluator) | 6fe2ec7 | backtest_hybrid.py, backtest_evaluate_all.py, test_entry_fix.py |
| 3 | Before/after comparison CSV | 3bcd675 | compare_entry_bias.py, entry_bias_comparison.csv |

## Entry Fix Details

### Files Modified

**V2/backtest/backtest_hybrid.py**
- `_backtest_swing_symbol()`: `range(100, len(h1))` → `range(100, len(h1) - 1)`, added `next_row = h1.iloc[i + 1]`, entry block now sets `entry_px = next_row['Open']` and `'entry_price': entry_px`
- `_backtest_m15_symbol()`: `range(50, len(m15))` → `range(50, len(m15) - 1)`, same pattern with `next_row = m15.iloc[i + 1]`
- Exit-side `px   = row['Close']` preserved unchanged in both loops

**V2/backtest/backtest_evaluate_all.py (Evaluator class)**
- `run_swing_with_cfg()`: same fix applied
- `run_scalp_with_cfg()`: same fix applied
- `run_momentum_with_cfg()`: same fix applied
- All 3 methods now include `'entry_bar_ts': h1.index[i]` in the position dict for test assertion

## BKTS-01 Test Results (all 4 GREEN)

```
tests/unit_tests/backtest/test_entry_fix.py::test_scalp_entry_price_is_next_bar_open   PASSED
tests/unit_tests/backtest/test_entry_fix.py::test_momentum_entry_price_is_next_bar_open PASSED
tests/unit_tests/backtest/test_entry_fix.py::test_sharpe_delta                          PASSED
tests/unit_tests/backtest/test_entry_fix.py::test_loop_bound_prevents_index_error       PASSED
4 passed in 1.58s
```

## Before/After Sharpe Comparison (730d data)

| Pair | Strategy | Old Sharpe (biased) | New Sharpe (corrected) | Delta |
|------|----------|---------------------|------------------------|-------|
| AUDNZD | swing | -2.16 | -3.26 | -1.10 |
| AUDNZD | scalp | 1.63 | 1.53 | **-0.10** |
| AUDNZD | momentum | 0.55 | 0.40 | **-0.15** |
| EURGBP | swing | 0.45 | 0.61 | +0.16 |
| EURGBP | scalp | 1.32 | 1.26 | **-0.06** |
| EURGBP | momentum | 1.57 | 1.38 | **-0.19** |
| GBPJPY | swing | 1.93 | 2.14 | +0.21 |
| GBPJPY | scalp | 0.85 | 0.83 | -0.02 |
| GBPJPY | momentum | 0.21 | 0.21 | -0.00 |
| EURUSD | swing | -0.20 | -0.31 | -0.11 |
| EURUSD | scalp | -0.17 | -0.43 | -0.26 |
| EURUSD | momentum | -1.03 | -1.35 | -0.32 |
| USDJPY | swing | 3.09 | 3.08 | -0.01 |
| USDJPY | scalp | -2.34 | -2.34 | 0.00 |
| USDJPY | momentum | -1.61 | -1.64 | -0.03 |

**11/15 rows show negative delta** — confirming Sharpe inflation from signal-bar close fill has been removed. The AUDNZD scalp drop (-0.10) and EURGBP momentum drop (-0.19) are the key validated corrections. Two swing pairs (EURGBP, GBPJPY) show slight positive delta due to the different trade timing changing exit interactions.

## Success Criteria Verification

- [x] 5 entry-price assignments fixed (2 in hybrid: swing + M15; 3 in Evaluator: swing + scalp + momentum)
- [x] All loop bounds changed to `len(data) - 1`
- [x] Exit-side `px = row['Close']` reads preserved (2 in hybrid, 3 in evaluator)
- [x] test_entry_fix.py all 4 tests PASS
- [x] entry_bias_comparison.csv committed with valid schema and negative deltas present (11/15)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] M15 loop start 50, not 100 as plan assumed**
- **Found during:** Task 1
- **Issue:** Plan acceptance criteria expects `range(100, len(m15) - 1)` but actual code uses `range(50, len(m15))` (start of 50, not 100)
- **Fix:** Changed to `range(50, len(m15) - 1)` — correct behavior (prevents IndexError) but grep for `range(100, len(m15) - 1)` returns 0
- **Impact:** Acceptance criterion grep check fails but semantic correctness is maintained

**2. [Rule 2 - Missing functionality] Momentum test needed lower thresholds**
- **Found during:** Task 2
- **Issue:** `test_momentum_entry_price_is_next_bar_open` skipped because no trades generated with default thresholds (z_threshold=1.5) on n=500 synthetic bars
- **Fix:** Lowered momentum test config to z_threshold=0.5, n=2000 bars, more volatile daily data — generates 73+ trades on synthetic data
- **Files modified:** test_entry_fix.py

**3. [Rule 3 - Blocking] CSV in gitignore**
- **Found during:** Task 3
- **Issue:** `*.csv` pattern in root `.gitignore` prevented `git add` of `entry_bias_comparison.csv`
- **Fix:** Used `git add -f` to force-commit the evidence artifact — plan explicitly requires this CSV in git

**4. [Rule 2 - Missing functionality] Evaluator method signatures differ from plan template**
- **Found during:** Task 3
- **Issue:** Plan template called `ev.run_scalp_with_cfg(df, cfg)` but actual signature is `run_scalp_with_cfg(self, symbol, daily, h1, cfg)`
- **Fix:** compare_entry_bias.py uses correct 4-argument form with pair name, daily data, h1 data, and injected config. Daily data loaded separately; fallback to h1 when daily missing for scalp/momentum.

## Known Stubs

None — all data flows to the CSV output. The `old_win_pct` and `old_trades` columns are 0 (baseline biased values were not documented per pair in pair_config.py, only Sharpe). This is intentional per the plan — the plan only specified Sharpe for the "old" baseline. Future plans (07-04) will fill in complete metrics from 4yr data.

## Self-Check

### Files exist
- /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/backtest/backtest_hybrid.py — FOUND
- /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/backtest/backtest_evaluate_all.py — FOUND
- /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/backtest/reports/compare_entry_bias.py — FOUND
- /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/backtest/reports/entry_bias_comparison.csv — FOUND
- /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/tests/unit_tests/backtest/test_entry_fix.py — FOUND

### Commits exist
- 6fe2ec7 (feat: entry fix to both backtest files + tests) — FOUND
- 3bcd675 (feat: compare_entry_bias.py + CSV) — FOUND
