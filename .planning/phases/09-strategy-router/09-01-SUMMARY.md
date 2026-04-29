---
phase: 09-strategy-router
plan: 01
subsystem: v3_intelligence/router
tags: [wave-0, red-scaffold, typed-contracts, router, position-store]
one_liner: "Wave 0 RED scaffold for Phase 9 — 5 files / 16 tests collected (10 RED + 6 GREEN) establishing typed contract surface (RouteDecision/Strategy/Direction/PositionStore/StrategyRouter stub) before any 4-gate routing logic"
dependency_graph:
  requires:
    - V2/v3_intelligence/pair_config.py     # PAIR_CONFIGS + PairConfig (Phase 7)
    - V2/v3_intelligence/regime/types.py    # RegimeState IntEnum (Phase 8)
    - V2/v3_intelligence/regime/persistence.py  # load_detector (Phase 8)
    - V2/tests/v3_intelligence/conftest_infra.py  # Phase 8.4 fixture bridge
  provides:
    - "v3_intelligence.router.RouteDecision (frozen dataclass — D-01 contract)"
    - "v3_intelligence.router.Strategy (string-valued enum — RESEARCH §9 EA forward-compat)"
    - "v3_intelligence.router.Direction (LONG/SHORT enum)"
    - "v3_intelligence.router.OpenPosition (frozen dataclass — D-09)"
    - "v3_intelligence.router.PositionStore (Protocol — D-09)"
    - "v3_intelligence.router.InMemoryPositionStore (functional adapter for Plan 04)"
    - "v3_intelligence.router.ZmqPositionStore (live skeleton — Phase 10 wires)"
    - "v3_intelligence.router.StrategyRouter (4-gate stub — Plan 02 implements)"
    - "16 collected tests across 3 new test files (10 RED + 6 GREEN at scaffold)"
    - "7 conftest fixtures for router unit tests"
  affects:
    - "Plan 02 turns 8 RED router tests GREEN"
    - "Plan 03 turns 1 RED detector inventory + 3 SKIPPED variance tests GREEN"
    - "Plan 04 turns 1 RED + 2 slow RED router_simulation tests GREEN"
tech-stack:
  added: []
  patterns:
    - "RED-first Wave 0 scaffold (CONTEXT D-17 / Pitfall #5 — mirrors Phase 7-01/8-01/8.4-01/8.5-01)"
    - "Typed contract surface before logic (frozen dataclasses + Protocol per RESEARCH §9)"
    - "String-valued enums for Phase 10 forward-compat (decision.strategy.value parseable from EA comment)"
    - "Test fixtures append-only (Phase 8 / 8.4 fixtures untouched)"
key-files:
  created:
    - V2/v3_intelligence/router.py            # 166 lines / 8 classes / 2 frozen dataclasses
    - V2/tests/v3_intelligence/test_router.py # 319 lines / 9 def test_
    - V2/tests/v3_intelligence/test_detector_inventory.py    # 66 lines / 2 def test_
    - V2/tests/v3_intelligence/test_router_simulation.py     # 70 lines / 3 def test_
  modified:
    - V2/tests/v3_intelligence/conftest.py    # +148 lines (7 fixtures + 2 test doubles appended)
decisions:
  - "Strategy enum values match enum names verbatim (DAILY_SWING='DAILY_SWING') for Phase 10 EA round-trip via Strategy(value)"
  - "ZmqPositionStore raises NotImplementedError on construct so accidental Phase 9 use surfaces immediately (Phase 10 wires)"
  - "InMemoryPositionStore lands functional (open/close/open_positions) so Plan 04 simulator can use it without further changes"
  - "test_route_decision_is_frozen_dataclass passes GREEN at scaffold (pure stub contract test) — matches Phase 8.5 P01 precedent of N-1 RED + 1 GREEN at scaffold for contract assertions"
  - "Router tests use SimpleNamespace for market_data (BarSnapshot dataclass deferred to Plan 02 per CONTEXT D-01 prose, RESEARCH §4 BarSnapshot recommendation)"
metrics:
  duration: "8m 26s"
  completed: "2026-04-28T12:36:58Z"
  tasks: 4
  files: 5
  commits: 4
  red_tests_collected: 10
  green_tests_at_scaffold: 6
  prior_phase_regression: "0 (107 baseline preserved + 6 new GREEN)"
---

# Phase 09 Plan 01: Wave 0 RED Scaffold Summary

## One-Liner

Wave 0 RED scaffold for Phase 9 — 5 files / 16 tests collected (10 RED + 6 GREEN) establishing the typed contract surface (`RouteDecision` / `Strategy` / `Direction` / `PositionStore` / `StrategyRouter` stub) before any 4-gate routing logic. Mirrors Phase 7-01 / 8-01 / 8.4-01 / 8.5-01 patterns. Plans 02-04 turn the 10 RED tests GREEN.

## Files Delivered

| File | Lines | Type | Purpose |
| --- | --- | --- | --- |
| `V2/v3_intelligence/router.py` | 166 | NEW | Typed contract stub: 8 classes (Strategy/Direction enums, 2 frozen dataclasses, PositionStore Protocol, InMemoryPositionStore, ZmqPositionStore, StrategyRouter). 3 NotImplementedError raises (StrategyRouter.route + ZmqPositionStore __init__/open_positions). `__all__` exports 8 symbols. |
| `V2/tests/v3_intelligence/test_router.py` | 319 | NEW | 9 RED unit tests: 5 ROUT-01 4-gate (typed/regime/session/matrix/RAG), 2 ROUT-02 swing-first (priority + intraday-skip BLOCKER #1), 1 ROUT-03 direction-conflict, 1 frozen-dataclass return-shape (passes GREEN at scaffold). |
| `V2/tests/v3_intelligence/test_detector_inventory.py` | 66 | NEW | 2 RED tests sourcing pairs from `PAIR_CONFIGS.keys()` (Pitfall #3): missing-JSON gate (lists `[GBPNZD, EURUSD, AUDNZD]`) + parametrized variance-ordering (5 GREEN existing + 3 SKIPPED missing). |
| `V2/tests/v3_intelligence/test_router_simulation.py` | 70 | NEW | 3 RED tests: 1 module-importable (RED — `backtest.router_simulation` not yet exists) + 2 `@pytest.mark.slow` (ROUT-04 Sharpe gate + sim-report-schema). |
| `V2/tests/v3_intelligence/conftest.py` | +148 | EXTEND | Append-only: 7 Phase 9 fixtures + 2 helper test doubles (`_FakeOnlineRegimeFilter`, `_FakeRagFilter`) at end. Phase 8 / 8.4 fixtures untouched. |

**Totals:** 5 files / 769 net new lines / 4 commits / 8m 26s wall-clock.

## Tests Collected

| Test File | Items | RED at scaffold | GREEN at scaffold | SKIPPED | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `test_router.py` | 9 | 8 | 1 | 0 | `test_route_decision_is_frozen_dataclass` passes GREEN (stub contract). Other 8 fail on `StrategyRouter.route()` `NotImplementedError`. |
| `test_detector_inventory.py` | 9* | 1 | 5 | 3 | `test_all_active_pairs_have_detector_json` RED (`[GBPNZD, EURUSD, AUDNZD]` missing). Variance ordering: 5 existing pairs GREEN, 3 missing pairs SKIPPED. |
| `test_router_simulation.py` | 3 | 1 | 0 | 0 | 1 RED (`from backtest.router_simulation import` ModuleNotFoundError). 2 `@pytest.mark.slow` deselected by `addopts = -m 'not slow'` — collected cleanly per CONTEXT D-18. |
| **Total** | **21 collected** (19 non-slow + 2 slow deselected) | **10 RED** | **6 GREEN** | **3 SKIPPED** | Exceeds CONTEXT D-17 minimum (`≥10 RED`). |

*`test_detector_inventory.py` exposes 2 `def test_` functions, but parametrization over `PAIR_CONFIGS.keys()` (8 pairs) yields 9 collected items.

## RED Count Distribution (10 RED)

By plan that turns each GREEN:

- **Plan 02 turns 8 RED GREEN** (router unit tests):
  - `test_route_returns_typed_decision`
  - `test_regime_blocks_dispatch`
  - `test_session_blocks_dispatch`
  - `test_matrix_fail_blocks`
  - `test_rag_below_threshold_blocks`
  - `test_swing_first_priority`
  - `test_intraday_skipped_when_swing_open` (BLOCKER #1 from plan revision iter 1)
  - `test_direction_conflict_rejects`
- **Plan 03 turns 1 RED + 3 SKIPPED GREEN** (detector inventory):
  - `test_all_active_pairs_have_detector_json` (RED)
  - 3 parametrized variance-ordering tests for GBPNZD/EURUSD/AUDNZD (currently SKIPPED — flip to GREEN once detectors land)
- **Plan 04 turns 1 RED + 2 slow RED GREEN** (router simulation):
  - `test_router_simulation_module_importable` (RED — module not yet exists)
  - `test_aggregate_sharpe_beats_single_by_0_2` (slow — ROUT-04 Sharpe gate)
  - `test_sim_report_schema` (slow — D-18 JSON keys)

## Phase 6/7/8/8.4/8.5 Regression

```
Full v3_intelligence -m "not slow":
  113 passed, 10 failed, 3 skipped, 20 deselected (slow)

Pre-Plan-09-01 baseline:
  107 passed, 0 failed, 0 skipped, 18 deselected (slow)

Delta:
  +6 passing  (1 frozen-dataclass + 5 detector-variance for existing pairs)
  +10 failing (Wave 0 RED — expected per CONTEXT D-17)
  +3 skipped  (3 missing-pair variance-ordering — Plan 03 unblocks)
  +2 deselected (2 slow simulation tests — Plan 04 unblocks)

Pre-existing regressions: 0 — 107 prior-phase passes preserved verbatim.
```

Phase-8 fixture-shadow guard: `test_online_filter.py` 5/5 still GREEN (Phase 8 OnlineRegimeFilter unaffected by Phase 9 fixture additions).

## Key Decisions Made During Execution

1. **String-valued enums for Phase 10 EA round-trip** (RESEARCH §9 forward-compat). `Strategy.DAILY_SWING.value == "DAILY_SWING"` and `Direction.LONG.value == "LONG"` — Phase 10 EA can encode strategy in the OrderRequest comment field and parse it back via `Strategy(value)` without lookup tables.

2. **`ZmqPositionStore` raises on construct** (CONTEXT D-09 / D-20). Accidental Phase 9-side instantiation surfaces immediately rather than silently returning empty. Phase 10's `LiveSignalEngine` will replace this stub.

3. **`InMemoryPositionStore` lands functional** (open / open_positions / close). Tests 7 & 8 (intraday-skipped + direction-conflict) need `store.open(OpenPosition(...))` at the test level today, and Plan 04's simulator needs it for fills — landing it now avoids a follow-up edit.

4. **`test_route_decision_is_frozen_dataclass` passes GREEN at scaffold** (8/9 RED). Pure stub contract test — `RouteDecision` is fully usable as a frozen dataclass once Task 1 lands. Matches Phase 8.5 P01 precedent (`test_pit_clamp_no_future_leak` GREEN at scaffold because Phase 8 PitClock already satisfied the contract). Does not violate the "RED-first" principle: the 8 ROUT-01/02/03 *behavioural* tests are all RED.

5. **Test market_data uses `SimpleNamespace`** rather than introducing a `BarSnapshot` dataclass in Plan 01. CONTEXT D-01 names the type but RESEARCH §4 recommends Plan 02 land it (so the simulator and live engine can build it from cached data without a Plan 01 forward-decl). `SimpleNamespace` carries the same fields RAG and regime gates need — Plan 02 swaps it cleanly.

## Deviations from Plan

None auto-fixed. Plan 09-01 executed exactly as written (post-iter-1 revision). Tasks 1-4 landed in plan order; all acceptance criteria met (with one documented variant: `grep -c "^def test_"` on `test_router.py` returns 9 instead of 8 because the prompt context block explicitly added `test_route_decision_is_frozen_dataclass` to the 8 D-17 names — success criteria target was 9, satisfied).

## Authentication Gates

None — pure scaffold work. No external service auth needed.

## Hand-off

| Plan | Owns | Turns Tests GREEN |
| --- | --- | --- |
| **Plan 02** | 4-gate decision chain + `OnlineRegimeFilter.current_state_prob()` (RESEARCH §1 Pitfall #12) + swing-first iteration + tie-break + structured logging. Lift `SHARPE_4YR` constant in `pair_config.py` for D-08 tie-break (RESEARCH §3). | 8 router unit tests + structured-logging tests (Plan 02 may add 2 more). |
| **Plan 03** | Extend `V2/scripts/fit_regime_detectors.py` to source `ACTIVE_PAIRS` from `PAIR_CONFIGS.keys()` (Pitfall #3); fit + persist GBPNZD/EURUSD/AUDNZD detector JSONs (~7.5 min wall-clock per RESEARCH §7). | `test_all_active_pairs_have_detector_json` (RED -> GREEN) + 3 SKIPPED variance-ordering parametrized tests (-> GREEN). |
| **Plan 04** | Create `V2/backtest/router_simulation.py` (CONTEXT D-18). PiT-wrapped 4yr loop over 8 pairs × H1 CSVs; emit `V2/reports/router_4yr_simulation.json` with `{aggregate_sharpe, best_single_sharpe, baseline_plus_0_2, gate_passed}`. Pre-warm RAG via `learning_loop.on_trade_close()` to avoid cold-start inflation (RESEARCH §6 / Pitfall #8). | `test_router_simulation_module_importable` (-> GREEN) + 2 slow tests (`test_aggregate_sharpe_beats_single_by_0_2`, `test_sim_report_schema` -> GREEN). |

## CONTEXT D-17 Compliance

> "Wave 0 RED scaffold lands first (mirrors Phase 7/8/8.4/8.5 P01 pattern): test files at V2/tests/v3_intelligence/test_router.py covering 8 RED tests..."

- All 8 named D-17 tests present and RED (verified by name): `test_route_returns_typed_decision`, `test_regime_blocks_dispatch`, `test_session_blocks_dispatch`, `test_matrix_fail_blocks`, `test_rag_below_threshold_blocks`, `test_swing_first_priority`, `test_intraday_skipped_when_swing_open`, `test_direction_conflict_rejects`.
- Plus `test_route_decision_is_frozen_dataclass` (return-shape contract) per phase-context-block specification.
- Pitfall #5 honored — RED-first scaffold per Phase 7/8/8.4/8.5 precedent.
- Pitfall #3 honored — detector inventory test sources from `PAIR_CONFIGS.keys()`, not a hardcoded list.

## Self-Check: PASSED

Files exist on disk:
- `V2/v3_intelligence/router.py`: FOUND (166 lines)
- `V2/tests/v3_intelligence/test_router.py`: FOUND (319 lines)
- `V2/tests/v3_intelligence/test_detector_inventory.py`: FOUND (66 lines)
- `V2/tests/v3_intelligence/test_router_simulation.py`: FOUND (70 lines)
- `V2/tests/v3_intelligence/conftest.py`: FOUND (extended +148 lines, total 215 lines)

Commits in `git log`:
- `a8e57ae` feat(09-01): add router.py stub with typed contracts (Wave 0 RED): FOUND
- `e44051c` test(09-01): add 9 RED router tests (Wave 0 RED scaffold): FOUND
- `5a881be` test(09-01): add RED detector inventory + slow simulation tests: FOUND
- `21d1632` test(09-01): extend conftest.py with 7 Phase 9 fixtures: FOUND

Verification commands all pass:
- Wave 0 collection: 19/21 (2 slow deselected by addopts) — exit 0
- Phase regression: 113 passed / 10 failed / 3 skipped / 20 deselected — no pre-existing regressions
- Stub-import smoke: `OK 4` (4 strategies importable)

No stubs leak unintended UI/data behaviour — all `NotImplementedError` raises are intentional Plan 02/Phase 10 markers (StrategyRouter.route, ZmqPositionStore.__init__, ZmqPositionStore.open_positions). Plans 02-04 are responsible for resolving them.
