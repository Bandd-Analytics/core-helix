---
phase: 07-backtest-entry-fix-h1-momentum-4yr-validation
verified: 2026-04-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
---

# Phase 7: Backtest Entry Fix + H1 Momentum + 4yr Validation Verification Report

**Phase Goal:** Fix lookahead bias in backtest entry timing across all strategy loops, port the V1 PiT validator to V2, produce a 4yr H1 routing matrix for all active pairs, and update pair_config.py allow flags with corrected unbiased numbers.
**Verified:** 2026-04-25
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All strategy loops use next-bar-open entry (BKTS-01) | VERIFIED | `entry_px = next_row['Open']` at lines 279, 428 in backtest_hybrid.py; lines 149, 214, 278 in backtest_evaluate_all.py. Loop bounds changed to `len(h1)-1` in all 3 Evaluator methods and hybrid swing/M15 loops |
| 2 | V2 PiT validator exists and exits 0 against fixed files (BKTS-04) | VERIFIED | V2/backtest/pit_validator.py (464 lines). CLI run: `python3 -m backtest.pit_validator backtest_hybrid.py backtest_evaluate_all.py backtest_4yr_evaluate.py` exits 0 with "PiT check PASSED — 3 file(s) clean" |
| 3 | 4yr routing matrix produced for 5 pairs × 2 strategies (BKTS-02) | VERIFIED | V2/backtest/reports/4yr_routing_matrix.csv has 11 lines (header + 10 rows). All 5 pairs present for both scalp and momentum strategies |
| 4 | pair_config.py allow flags updated from 4yr matrix with notes (BKTS-03) | VERIFIED | `grep -c "4yr corrected" pair_config.py` = 5. All 5 pairs carry correct allow_scalp/allow_momentum values matching the routing matrix |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `V2/tests/unit_tests/backtest/__init__.py` | pytest package init | VERIFIED | Exists |
| `V2/tests/unit_tests/backtest/test_entry_fix.py` | 4 tests for BKTS-01 | VERIFIED | 4 test functions; all PASS |
| `V2/tests/unit_tests/backtest/test_pit_validator.py` | 7 tests for BKTS-04 | VERIFIED | 7 test functions; all PASS |
| `V2/tests/unit_tests/backtest/test_4yr_evaluate.py` | 6 tests for BKTS-02/03 | VERIFIED | 6 test functions; all PASS |
| `V2/backtest/backtest_hybrid.py` | Next-bar-open entry in swing + M15 | VERIFIED | `h1.iloc[i+1]` and `m15.iloc[i+1]` present; loop bounds adjusted; exit-side `px = row['Close']` at lines 222, 358 preserved |
| `V2/backtest/backtest_evaluate_all.py` | Next-bar-open entry in swing/scalp/momentum | VERIFIED | 3x `next_row = h1.iloc[i + 1]`, 3x `entry_px = next_row['Open']`, 3x `'entry_bar_ts': h1.index[i]`, 3x BKTS-01 comments |
| `V2/backtest/pit_validator.py` | PiTValidator class, 180+ lines, Title-case PRICE_COLUMNS, next-bar whitelist, CLI | VERIFIED | 464 lines; `class PiTValidator`; `PRICE_COLUMNS` contains "Close", "Open"; `_is_next_bar_read` defined and called (3 occurrences); `__main__` block present |
| `V2/backtest/__init__.py` | Package init for `python -m backtest.pit_validator` | VERIFIED | Exists |
| `V2/backtest/backtest_4yr_evaluate.py` | `run_4yr_evaluation()` + `write_routing_matrix_csv()`, 100+ lines | VERIFIED | 386 lines; both functions present; `SHARPE_THRESHOLD = 0.5`; `MIN_TRADE_COUNT = 30`; `ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]` |
| `V2/backtest/reports/4yr_routing_matrix.csv` | 10 data rows, correct columns | VERIFIED | 11 lines (header + 10). Columns: pair, strategy, sharpe, win_rate, trade_count, min_trades_met, sharpe_threshold_met, routing_matrix_entry, allow_flag |
| `V2/backtest/reports/entry_bias_comparison.csv` | 15-row before/after Sharpe delta evidence | VERIFIED | 16 lines (header + 15 rows); schema correct |
| `V2/backtest/reports/pit_gate_output.txt` | PiT check PASSED + exit_code=0 | VERIFIED | Contains "PiT check PASSED — 2 file(s) clean" and "exit_code=0" |
| `V2/scripts/download_history.py` | `_fetch_4yr` function, `--4yr` flag, idempotent | VERIFIED | `_fetch_4yr` defined; `ACTIVE_PAIRS_4YR = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]`; `--4yr` flag present |
| `V2/data/{PAIR}_H1_4yr.csv` (5 files) | >= 15,000 bars each | VERIFIED | AUDNZD: 17,355; EURGBP: 17,287; GBPJPY: 17,273; EURUSD: 17,262; USDJPY: 17,149 — all exceed minimum |
| `V2/v3_intelligence/pair_config.py` | allow_scalp/allow_momentum for 5 pairs, "4yr corrected" in all notes | VERIFIED | 5 occurrences of "4yr corrected"; flags match routing matrix (AUDNZD T/T, EURGBP T/T, GBPJPY T/F, EURUSD F/F, USDJPY F/F) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| backtest_hybrid.py `_backtest_swing_symbol` | `h1.iloc[i+1]['Open']` | `entry_px = next_row['Open']` in entry branch | WIRED | Line 279; `'entry_price': entry_px` at line 281 |
| backtest_hybrid.py `_backtest_m15_symbol` | `m15.iloc[i+1]['Open']` | `entry_px = next_row['Open']` in entry branch | WIRED | Line 428; `'entry_price': entry_px` at line 430 |
| backtest_evaluate_all.py `Evaluator.run_scalp_with_cfg` | `h1.iloc[i+1]['Open']` | `'entry_price': entry_px` | WIRED | Line 149, 214, 278; 3 methods all wired |
| pit_validator.py | `sys.exit` | `__main__` block exit-code contract | WIRED | `sys.exit(0)` on pass, `sys.exit(1)` on violations, `sys.exit(2)` on file not found |
| pit_validator.py `_is_next_bar_read` | `ast.BinOp with ast.Add` | detects `iloc[i+1]` pattern | WIRED | `isinstance(iloc_slice, ast.BinOp) and isinstance(iloc_slice.op, (ast.Add, ast.Sub))` |
| backtest_4yr_evaluate.py | `Evaluator` / standalone runners | `run_scalp_with_cfg / run_momentum_with_cfg` equivalent | WIRED | Uses standalone `_run_scalp_loop/_run_momentum_loop` (Evaluator required constructor arg unavailable without data_dir); functionally equivalent |
| backtest_4yr_evaluate.py | pair_config.py | routing matrix dict → allow flag update | WIRED | 4yr_routing_matrix.csv values match pair_config.py allow_scalp/allow_momentum for all 5 pairs |
| pit_validator.py CLI | pair_config.py update gate | PiT gate cleared before edit (D-06) | WIRED | pit_gate_output.txt confirms "PiT check PASSED — 2 file(s) clean, exit_code=0" before Task 3 pair_config.py edit |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BKTS-01 | 07-02-PLAN.md | Next-bar-open entry for all strategy loops, loop bounds fixed | SATISFIED | 5 entry assignments fixed (2 in hybrid, 3 in evaluator); 4 unit tests GREEN; entry_bias_comparison.csv shows negative deltas |
| BKTS-02 | 07-04-PLAN.md | H1 scalp backtested on 4yr data → routing matrix | SATISFIED | backtest_4yr_evaluate.py produces scalp rows for all 5 pairs; 6 unit tests GREEN |
| BKTS-03 | 07-04-PLAN.md | Momentum backtested on 4yr data → routing matrix entry in pair_config.py | SATISFIED | Momentum rows in routing matrix for all 5 pairs; pair_config.py updated with allow_momentum flags |
| BKTS-04 | 07-03-PLAN.md | pit_validator.py PiT gate — no new Sharpe without PiT compliance | SATISFIED | 464-line validator with Title-case PRICE_COLUMNS, 4 whitelist helpers, CLI exit codes; 7 unit tests GREEN; exits 0 against 3 backtest files |

REQUIREMENTS.md marks all four as `[x]` (complete), Phase 7.

---

## Anti-Patterns Found

No blockers or warnings identified. Scan of key modified files:

- `V2/backtest/backtest_hybrid.py`: No TODOs, FIXMEs, or empty implementations. Exit-side `px = row['Close']` at lines 222 and 358 are correct (not stubs — confirmed as current-bar exit price reads whitelisted by PiT validator).
- `V2/backtest/backtest_evaluate_all.py`: No placeholder patterns. `'entry_price': entry_px` backed by real `next_row['Open']` value in all 3 methods.
- `V2/backtest/pit_validator.py`: No stubs. 464-line implementation passes all 7 tests including real-file scan.
- `V2/backtest/backtest_4yr_evaluate.py`: No stubs. Standalone runners with indicator helpers (`_adaptive_atr`, `_z_score_signal`) compute real metrics.
- `V2/v3_intelligence/pair_config.py`: No placeholder notes. All 5 pairs carry dated 4yr corrected entries with real Sharpe/win/count numbers from the routing matrix.

**Notable deviation (documented, not a gap):** The `_H1_4yr.csv` files were sourced from existing `_H1_730d.csv` data (MetaTrader5 Python package is Windows-only, unavailable on Linux). The window is ~33 months (2023-07 to 2026-04) rather than a true calendar 4yr. All bar counts exceed the 15,000 minimum. The download script correctly implements the idempotent `--4yr` flag and will re-fetch true 4yr data when run on Windows/Wine with MT5 available. This is a known and approved deviation documented in 07-04-SUMMARY.md.

---

## Human Verification Required

None. All acceptance criteria are verifiable programmatically and have been verified.

The pair_config.py update was a `checkpoint:human-verify` task in Plan 04. Per 07-04-SUMMARY.md, the checkpoint was reached and the update was applied (Task 3 completed with commit 6bf2f52 on 2026-04-25). The allow-flag values match the routing matrix, and "4yr corrected" notes are present for all 5 pairs — this is confirmed programmatically above.

---

## Test Suite Summary

| Test File | Tests | Result |
|-----------|-------|--------|
| `test_entry_fix.py` | 4 | 4/4 GREEN |
| `test_pit_validator.py` | 7 | 7/7 GREEN |
| `test_4yr_evaluate.py` | 6 | 6/6 GREEN |
| Phase 6 bridge tests | 53 | 53/53 GREEN |
| **Total** | **70** | **70/70 GREEN** |

PiT gate: `python3 -m backtest.pit_validator backtest_hybrid.py backtest_evaluate_all.py backtest_4yr_evaluate.py` → "PiT check PASSED — 3 file(s) clean", exit=0

---

_Verified: 2026-04-25_
_Verifier: Claude (gsd-verifier)_
