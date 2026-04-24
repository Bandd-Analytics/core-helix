---
phase: 07-backtest-entry-fix-h1-momentum-4yr-validation
plan: "01"
subsystem: backtest-testing
tags: [pytest, tdd, bkts-01, bkts-02, bkts-03, bkts-04, scaffolding, red-tests]
dependency_graph:
  requires: []
  provides:
    - "V2/tests/unit_tests/backtest/ test package (17 RED tests)"
    - "Wave 0 pytest scaffold for Phase 7 BKTS-01/02/03/04"
  affects:
    - "Plans 02, 03, 04 — each plan must make its RED tests GREEN"
tech_stack:
  added: []
  patterns:
    - "pytest fixtures with tmp_path and monkeypatch for synthetic data"
    - "subprocess-based CLI exit-code testing"
    - "synthetic DataFrame factories (no live MT5 dependency)"
key_files:
  created:
    - V2/tests/unit_tests/backtest/__init__.py
    - V2/tests/unit_tests/backtest/test_entry_fix.py
    - V2/tests/unit_tests/backtest/test_pit_validator.py
    - V2/tests/unit_tests/backtest/test_4yr_evaluate.py
  modified: []
decisions:
  - "Used existing test_entry_fix.py scaffold (pre-existing, better API alignment) rather than overwriting with plan template — existing file matches real run_*_with_cfg(symbol, daily, h1, cfg) API and is a valid RED scaffold"
  - "PRICE_COLUMNS test covers both Title-case (Close/Open) and lowercase (close/open) per D-07"
  - "ACTIVE_PAIRS list in test_4yr_evaluate.py matches D-14: AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY"
metrics:
  duration: 208
  completed_date: "2026-04-24"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 0
---

# Phase 7 Plan 01: Wave 0 Test Scaffolding Summary

Wave 0 pytest scaffold for Phase 7. Four test files created covering BKTS-01 (entry fix), BKTS-02/03 (4yr routing matrix), and BKTS-04 (PiT validator gate). All 17 tests collected by pytest with zero collection errors; all are RED against current code.

## What Was Built

- **Test package init:** `V2/tests/unit_tests/backtest/__init__.py` (Phase 7 package marker)
- **Entry-fix scaffold** (`test_entry_fix.py`): 4 RED tests for BKTS-01 — verifies next-bar-open entry price, loop bound safety, and Sharpe delta
- **PiT validator scaffold** (`test_pit_validator.py`): 7 RED tests for BKTS-04 — verifies class importability, Title-case PRICE_COLUMNS, bias flagging, next-bar whitelist, CLI exit codes, real-file scan gate
- **4yr evaluator scaffold** (`test_4yr_evaluate.py`): 6 RED tests for BKTS-02/03 — verifies runner module, routing matrix shape, allow_flag threshold logic, no-silent-drop guarantee, CSV schema

## Test Count by File

| File | Tests | Requirement | Status |
|------|-------|-------------|--------|
| `test_entry_fix.py` | 4 | BKTS-01 | RED — Plan 02 makes GREEN |
| `test_pit_validator.py` | 7 | BKTS-04 | RED — Plan 03 makes GREEN |
| `test_4yr_evaluate.py` | 6 | BKTS-02, BKTS-03 | RED — Plan 04 makes GREEN |
| **Total** | **17** | BKTS-01/02/03/04 | All RED |

## Requirement Coverage Map

| Requirement | Test File | Test Functions |
|-------------|-----------|----------------|
| BKTS-01 | test_entry_fix.py | test_scalp_entry_price_is_next_bar_open, test_momentum_entry_price_is_next_bar_open, test_loop_bound_prevents_index_error, test_sharpe_delta |
| BKTS-02 | test_4yr_evaluate.py | test_runner_module_importable, test_scalp_routing_matrix, test_allow_flag_threshold_logic, test_below_threshold_pair_not_dropped, test_csv_report_schema |
| BKTS-03 | test_4yr_evaluate.py | test_runner_module_importable, test_momentum_routing_matrix, test_allow_flag_threshold_logic, test_below_threshold_pair_not_dropped, test_csv_report_schema |
| BKTS-04 | test_pit_validator.py | test_validator_class_exists, test_price_columns_covers_title_case, test_flags_biased_close_read, test_whitelists_next_bar_open, test_cli_exits_zero_on_clean_file, test_cli_exits_nonzero_on_violation, test_cli_scans_real_backtest_files_after_fix |

## All Tests Are RED

Verification confirms tests are RED against current (unfixed) code:

- `test_entry_fix.py`: fails because `entry_bar_ts` key does not exist in trade dicts (Plan 02 adds it with the entry-fix)
- `test_pit_validator.py`: fails with `ModuleNotFoundError: backtest.pit_validator` (Plan 03 creates it)
- `test_4yr_evaluate.py`: fails with `ModuleNotFoundError: backtest.backtest_4yr_evaluate` (Plan 04 creates it)

## Deviations from Plan

### Auto-fixed Issues

None. Plan executed exactly as written.

### Notes

The `test_entry_fix.py` file was already pre-populated with a compatible scaffold (using the real 4-argument API signature `run_scalp_with_cfg(symbol, daily, h1, cfg)`) when the directory was created. The existing file is a valid RED scaffold per acceptance criteria — all 4 named test functions are present and pytest collects them. The plan template showed a 2-argument form for the API, but the existing scaffold correctly uses the actual current API, which is a better match for the implementation Plan 02 will need to adapt.

## Known Stubs

None — this plan creates test scaffolding only, no implementation stubs.

## Self-Check: PASSED

Files created:
- FOUND: V2/tests/unit_tests/backtest/__init__.py
- FOUND: V2/tests/unit_tests/backtest/test_entry_fix.py
- FOUND: V2/tests/unit_tests/backtest/test_pit_validator.py
- FOUND: V2/tests/unit_tests/backtest/test_4yr_evaluate.py

Commits:
- FOUND: 4922007 (test(07-01): Task 1 — __init__.py + test_entry_fix.py)
- FOUND: d06b656 (test(07-01): Task 2 — test_pit_validator.py)
- FOUND: f0ca188 (test(07-01): Task 3 — test_4yr_evaluate.py)

pytest --collect-only: 17 tests collected, 0 errors
