---
phase: 7
slug: backtest-entry-fix-h1-momentum-4yr-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in `V2/pyproject.toml`) |
| **Config file** | `V2/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd V2 && python -m pytest tests/unit_tests/backtest/ -v -x` |
| **Full suite command** | `cd V2 && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds (unit tests, no live MT5 dependency) |

---

## Sampling Rate

- **After every task commit:** Run `cd V2 && python -m pytest tests/unit_tests/backtest/ -v -x`
- **After every plan wave:** Run `cd V2 && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | BKTS-01 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_entry_fix.py -x` | Wave 0 | ⬜ pending |
| 7-01-02 | 01 | 0 | BKTS-04 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_pit_validator.py -x` | Wave 0 | ⬜ pending |
| 7-01-03 | 01 | 0 | BKTS-02/03 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_4yr_evaluate.py -x` | Wave 0 | ⬜ pending |
| 7-02-01 | 02 | 1 | BKTS-01 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_entry_fix.py -x` | ✅ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | BKTS-01 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_entry_fix.py::test_sharpe_delta -x` | ✅ W0 | ⬜ pending |
| 7-03-01 | 03 | 1 | BKTS-04 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_pit_validator.py -x` | ✅ W0 | ⬜ pending |
| 7-04-01 | 04 | 2 | BKTS-02 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_4yr_evaluate.py::test_scalp_routing_matrix -x` | ✅ W0 | ⬜ pending |
| 7-04-02 | 04 | 2 | BKTS-03 | unit | `cd V2 && python -m pytest tests/unit_tests/backtest/test_4yr_evaluate.py::test_momentum_routing_matrix -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `V2/tests/unit_tests/backtest/__init__.py` — package init for new test subdir
- [ ] `V2/tests/unit_tests/backtest/test_entry_fix.py` — stubs for BKTS-01: synthetic DataFrame verifies entry_price == next_bar_open; Sharpe comparison with deterministic P&L sequence
- [ ] `V2/tests/unit_tests/backtest/test_pit_validator.py` — stubs for BKTS-04: validator returns violations on biased code, zero violations on fixed code, zero on iloc[i+1] whitelist pattern
- [ ] `V2/tests/unit_tests/backtest/test_4yr_evaluate.py` — stubs for BKTS-02/03: with mock 4yr data, run_scalp_with_cfg and run_momentum_with_cfg return non-empty dicts with expected keys

Follow the exact structural pattern from `V2/tests/unit_tests/bridge/` (imports, fixture style, no external deps in unit tests).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MT5 4yr data download completes for all 5 pairs | BKTS-02/03 | Requires live MT5 terminal on Linux+Wine with IC Markets connectivity | Run `cd V2 && python scripts/download_history.py --4yr`; verify 5 `*_H1_4yr.csv` files exist in `V2/data/` with >15,000 rows each |
| pair_config.py updated with 4yr Sharpe values | BKTS-02/03 | Requires actual backtest run results; not mockable | After backtest run, verify `allow_scalp`/`allow_momentum` flags and `notes` field updated for all 5 pairs in `V2/v3_intelligence/pair_config.py` |
| PiT validator exits 0 before pair_config.py commit | BKTS-04 | CLI gate (D-06 — manual, not pre-commit hook) | Run `cd V2 && python backtest/pit_validator.py`; confirm exit code is 0 before any pair_config.py edit |
| Before/after Sharpe comparison report | BKTS-01 | Requires actual run numbers | Confirm `V2/backtest/reports/entry_bias_comparison_*.csv` exists and shows old Sharpe > new Sharpe for AUDNZD and EURGBP strategies |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
