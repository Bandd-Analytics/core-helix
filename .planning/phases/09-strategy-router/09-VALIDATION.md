---
phase: 9
slug: strategy-router
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (uv-managed; pyproject.toml requires-python>=3.12) |
| **Config file** | V2/pyproject.toml (pytest section) |
| **Quick run command** | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py -v` |
| **Full suite command** | `cd V2 && python -m pytest tests/v3_intelligence/ -v -m "not slow"` |
| **Estimated runtime** | ~12 seconds quick / ~95 seconds full fast suite |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full fast suite (filters out slow Supabase + 4yr sim)
- **Before `/gsd:verify-work`:** Full suite must be green INCLUDING the slow `-m slow` ROUT-04 simulation gate
- **Max feedback latency:** 15 seconds (quick) / 95 seconds (full fast)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | ROUT-01..04 | RED scaffold | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py --collect-only` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | ROUT-01 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_route_returns_typed_decision -v` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | ROUT-01 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_regime_blocks_dispatch -v` | ❌ W0 | ⬜ pending |
| 09-02-03 | 02 | 1 | ROUT-01 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_session_blocks_dispatch -v` | ❌ W0 | ⬜ pending |
| 09-02-04 | 02 | 1 | ROUT-01 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_matrix_fail_blocks -v` | ❌ W0 | ⬜ pending |
| 09-02-05 | 02 | 1 | ROUT-01 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_rag_below_threshold_blocks -v` | ❌ W0 | ⬜ pending |
| 09-02-06 | 02 | 1 | ROUT-02 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_swing_first_priority -v` | ❌ W0 | ⬜ pending |
| 09-02-07 | 02 | 1 | ROUT-03 | unit | `cd V2 && python -m pytest tests/v3_intelligence/test_router.py::test_direction_conflict_rejects -v` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | ROUT-04 prereq | integration | `ls V2/v3_intelligence/regime/detectors/{GBPNZD,EURUSD,AUDNZD}.json` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | ROUT-04 prereq | unit | `cd V2 && python -m pytest tests/v3_intelligence/regime/test_detector_inventory.py -v` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 3 | ROUT-04 | slow | `cd V2 && python -m pytest tests/v3_intelligence/test_router_simulation.py -v -m slow` | ❌ W0 | ⬜ pending |
| 09-04-02 | 04 | 3 | ROUT-04 | gate | `cd V2 && python -m scripts.run_router_simulation && jq '.gate_passed' V2/reports/router_4yr_simulation.json` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `V2/tests/v3_intelligence/test_router.py` — RED scaffold for 8 router scenarios (matches CONTEXT D-17)
- [ ] `V2/tests/v3_intelligence/regime/test_detector_inventory.py` — RED that all 8 active pairs have detector JSONs
- [ ] `V2/tests/v3_intelligence/test_router_simulation.py` — slow-marker test importing `router_simulation` module (RED, no impl yet)
- [ ] `V2/tests/conftest.py` — extend with `mock_position_store`, `mock_regime_detectors`, `mock_rag_filter` fixtures for unit tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live engine integration sanity | ROUT-01 (Phase 10 contract) | LiveSignalEngine doesn't exist until Phase 10 | Verified at Phase 10 boundary; Phase 9 ships only the typed contract |
| Regime detector quality on new 3 pairs | ROUT-04 prereq | Statistical "good fit" is non-binary | Operator inspects variance ratios in detector JSONs (target: 50x+ between TRENDING and CRISIS); flag if <10x |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (quick) / 95s (fast suite)
- [ ] `nyquist_compliant: true` set in frontmatter once all plans pass

**Approval:** pending
