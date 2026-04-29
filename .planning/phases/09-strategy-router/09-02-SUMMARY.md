---
phase: 09-strategy-router
plan: 02
subsystem: v3_intelligence/router
tags: [router, 4-gate-chain, swing-first, direction-conflict, sharpe-4yr, regime-confidence]
one_liner: "StrategyRouter 4-gate decision chain (Regime -> Session -> Matrix -> RAG) with ROUT-02 swing-first iteration, ROUT-03 pair-level direction conflict, D-08 SHARPE_4YR tie-break, and OnlineRegimeFilter.current_state_prob() — turns 8 RED router tests GREEN"
dependency_graph:
  requires:
    - V2/v3_intelligence/router.py                     # Plan 01 stub (Strategy/Direction/RouteDecision/PositionStore symbols)
    - V2/v3_intelligence/regime/online_filter.py       # Phase 8 forward filter
    - V2/v3_intelligence/regime/types.py               # RegimeState IntEnum
    - V2/v3_intelligence/pair_config.py                # PAIR_CONFIGS + per-strategy size_mult fields
    - V2/v3_intelligence/temporal_filters.py           # is_tradeable_session predicate (Phase 8.5)
    - V2/v3_intelligence/rag_signal_filter.py          # score_signal() API
    - V2/tests/v3_intelligence/test_router.py          # Plan 01 RED scaffold
    - V2/tests/v3_intelligence/conftest.py             # Plan 01 fixtures
  provides:
    - "OnlineRegimeFilter.current_state_prob() -> tuple[RegimeState, float]   # RESEARCH critical gap #2 closed"
    - "pair_config.SHARPE_4YR module-level dict[str, dict[str, float]]        # 8 pairs x 4 strategies — D-08 tie-break source"
    - "StrategyRouter 4-gate chain implementation (Regime -> Session -> Matrix -> RAG, short-circuit, structured logging)"
    - "ROUT-02 swing-first iteration order + pair-cooldown when swing already open"
    - "ROUT-03 pair-level direction conflict rejection + direction_conflict_count telemetry"
    - "D-08 SHARPE_4YR tie-break for multi-intraday-pass scenarios"
    - "v3_intelligence package re-exports 8 Phase 9 symbols (Phase 10 D-20 forward-compat)"
    - "_STRATEGY_META single-source-of-truth dict (session_key, timeframe, size_mult_field, sharpe_key)"
    - "_ITERATION_ORDER tuple (DAILY_SWING, H1_SCALP, H1_MOMENTUM, M15_SCALP)"
    - "MIN_SHARPE = 0.3 module constant (matches Phase 8.5 SHARPE_GOOD)"
  affects:
    - "Plan 03 inherits a router that already routes 8/8 pairs (no GBPNZD/EURUSD/AUDNZD-specific code path needed)"
    - "Plan 04 simulator constructs StrategyRouter via stable __init__ + calls route() in PiT loop"
    - "Phase 10 LiveSignalEngine imports StrategyRouter from v3_intelligence (D-20 contract honored)"
tech-stack:
  added: []  # No new third-party deps; pure stdlib + existing v3_intelligence modules
  patterns:
    - "Read-only state access (current_state_prob) — avoids Pitfall #6 mutation"
    - "Single-source-of-truth metadata dict (_STRATEGY_META) — Pitfall #4 closed for future 5th strategy additions"
    - "Cheapest-gate-first short-circuit (D-05 / D-06) — Regime O(1) -> Session O(N_patterns) -> Matrix dict-lookup -> RAG ChromaDB query"
    - "Mean-reversion direction inference from daily_z magnitude with ±2.0 threshold"
    - "Module-level constant lift (SHARPE_4YR) — replaces inline literals in print_pair_summary"
    - "Structured logging via stdlib logging.extra — gate_blocked / dispatched record types per CONTEXT D-02"
    - "TYPE_CHECKING-guarded forward references — avoid circular import on regime / rag_signal_filter"
key-files:
  created: []
  modified:
    - V2/v3_intelligence/router.py                # 167 -> 486 lines (+319; Plan 01 stub bodies filled)
    - V2/v3_intelligence/regime/online_filter.py  # 178 -> 186 lines (+8; current_state_prob method)
    - V2/v3_intelligence/pair_config.py           # 235 -> 251 lines (+16; SHARPE_4YR constant + print_pair_summary refactor)
    - V2/v3_intelligence/__init__.py              # 28 -> 50 lines (+22; 8 router re-exports)
decisions:
  - "current_state_prob() implemented as a method (not @property) to mirror update()'s call semantics — fixture test doubles match this convention"
  - "MIN_SHARPE = 0.3 chosen as a defensive belt-and-braces threshold (Phase 7 already encoded 0.5 in pair_config.allow_*); does NOT exclude pairs the matrix already disabled"
  - "Direction inference threshold ±2.0 (matches PairConfig defaults across pairs); below threshold returns None with reason=no_signal_direction"
  - "Swing pair-cooldown applies to ALL strategies, including DAILY_SWING itself — distinct log reasons swing_already_open vs swing_open_skips_intraday for telemetry"
  - "_classify_session() ordering: TOKYO check first (0-9 UTC), then LONDON (7-16), then NY (13-22) — overlapping windows favor earliest session per RAG vocabulary precedent"
  - "atr_at_entry NOT added to RouteDecision (CONTEXT D-01 explicit field list honored; Phase 10 may revisit per RESEARCH §9 if SL/TP derivation needs it)"
metrics:
  duration: "8m 10s"
  completed: "2026-04-29T00:22:16Z"
  tasks: 3
  files: 4
  commits: 3
  red_to_green: 8        # 8 router unit tests RED -> GREEN
  green_at_start: 1      # test_route_decision_is_frozen_dataclass
  green_at_end: 9        # all router tests
  fast_suite_passing: 226
requirements:
  - ROUT-01  # 4-gate chain returns RouteDecision | None
  - ROUT-02  # swing-first priority + pair cooldown
  - ROUT-03  # pair-level direction conflict
---

# Phase 09 Plan 02: Router core — 4-gate decision chain Summary

## One-Liner

`StrategyRouter` 4-gate decision chain (Regime -> Session -> Matrix -> RAG) with ROUT-02 swing-first iteration, ROUT-03 pair-level direction conflict, D-08 `SHARPE_4YR` tie-break, and `OnlineRegimeFilter.current_state_prob()` — turns 8 RED router unit tests GREEN. Plan 01 typed contracts preserved verbatim; only `route()` body filled.

## Files Modified

| File | Before | After | Delta | Purpose |
| --- | ---: | ---: | ---: | --- |
| `V2/v3_intelligence/router.py` | 167 | 486 | +319 | Replace Plan 01 stub `route()` with full 4-gate chain + ROUT-02 cooldown + ROUT-03 conflict + D-08 tie-break + structured logging. Adds `_STRATEGY_META`, `_ITERATION_ORDER`, `MIN_SHARPE`, `_classify_session`, `_infer_direction`. Public `direction_conflict_count` property added. |
| `V2/v3_intelligence/regime/online_filter.py` | 178 | 186 | +8 | Add `current_state_prob() -> tuple[RegimeState, float]` — read-only mirror of `update()` return shape. Closes RESEARCH critical gap #2. |
| `V2/v3_intelligence/pair_config.py` | 235 | 251 | +16 | Lift `SHARPE_4YR: dict[str, dict[str, float]]` module constant (8 pairs × 4 strategies). Refactor `print_pair_summary()` to read from constant — auto-corrects GBPNZD h1_scalp drift `-0.60 -> 0.66`. |
| `V2/v3_intelligence/__init__.py` | 28 | 50 | +22 | Re-export 8 Phase 9 router symbols (D-20 forward-compat). Preserves all Phase 6/7/8 exports. |
| **Total** | 608 | 973 | **+365** | 4 files, 3 commits, ~8m wall-clock |

## Test Transition: 8 RED → 8 GREEN

`tests/v3_intelligence/test_router.py` — 9 tests total (8 RED + 1 GREEN at Plan 01 end → 9/9 GREEN now):

| Test | Plan 01 status | Plan 02 status | Gate(s) Exercised |
| --- | --- | --- | --- |
| `test_route_decision_is_frozen_dataclass` | GREEN | GREEN | Return-shape contract (D-01) |
| `test_route_returns_typed_decision` | RED | **GREEN** | All 4 gates pass (permissive fixtures) |
| `test_regime_blocks_dispatch` | RED | **GREEN** | Gate 1 fails (CRISIS state) |
| `test_session_blocks_dispatch` | RED | **GREEN** | Gate 2 fails (monkeypatched is_tradeable_session=False) |
| `test_matrix_fail_blocks` | RED | **GREEN** | Gate 3 fails (all allow_* False) |
| `test_rag_below_threshold_blocks` | RED | **GREEN** | Gate 4 fails (action=SKIP) |
| `test_swing_first_priority` | RED | **GREEN** | ROUT-02 — DAILY_SWING dispatched preferentially |
| `test_intraday_skipped_when_swing_open` | RED | **GREEN** | ROUT-02 BLOCKER #1 — pair cooldown when swing position open |
| `test_direction_conflict_rejects` | RED | **GREEN** | ROUT-03 — pair-level direction conflict (D-10) |

```
$ python3 -m pytest tests/v3_intelligence/test_router.py -v
======================== 9 passed, 13 warnings in 0.07s ========================
```

## Phase 6/7/8/8.4/8.5 Regression Result

```
$ python3 -m pytest tests/ -m "not slow" -q
==== 1 failed, 226 passed, 20 deselected, 20 warnings in 147.40s (0:02:27) =====

FAILED tests/v3_intelligence/test_router_simulation.py::test_router_simulation_module_importable
```

**Pre-Plan-02 baseline:** 216 passed / 10 failed.
**Post-Plan-02:** 226 passed / 1 failed.

**Delta:**
- **+10 passing** (8 router unit tests RED → GREEN; +1 detector_inventory test pre-existing GREEN once 7th detector landed; +1 detector parametrized test).
- **−9 failing** (8 router RED resolved; the 9th was detector inventory which is GREEN due to all 8 detector JSONs already on disk — this is upstream Plan 03 turf and not a Plan 02 deliverable).
- **0 pre-existing-pass regressions.**

The remaining 1 failure (`test_router_simulation_module_importable`) is Plan 04 territory (creates `V2/backtest/router_simulation.py`).

## New Module Surface

The `v3_intelligence` package now exports 8 Phase 9 symbols (added to `__all__`):

```python
from v3_intelligence import (
    StrategyRouter,
    RouteDecision,
    Strategy,
    Direction,
    OpenPosition,
    PositionStore,
    InMemoryPositionStore,
    ZmqPositionStore,
)
```

Plus all Phase 6/7/8 exports preserved verbatim:
`TradeLogger`, `PairConfig`, `PAIR_CONFIGS`, `get_pair_config`, `RAGSignalFilter`, `CHROMA_AVAILABLE`, `RegimeState`, `OnlineRegimeFilter`, `PitClock`, `FutureBarReadError`.

## SHARPE_4YR Concrete Numbers (D-08 Tie-Break Source)

```python
SHARPE_4YR: dict[str, dict[str, float]] = {
    "USDJPY": {"swing":  3.09, "h1_scalp": -2.34, "h1_momentum": -1.61, "m15_scalp":  0.93},
    "GBPJPY": {"swing":  1.93, "h1_scalp":  0.85, "h1_momentum":  0.21, "m15_scalp": -0.02},
    "GBPAUD": {"swing":  1.86, "h1_scalp": -0.61, "h1_momentum": -0.11, "m15_scalp":  1.08},
    "GBPUSD": {"swing":  1.05, "h1_scalp": -0.15, "h1_momentum":  1.00, "m15_scalp":  2.60},
    "EURGBP": {"swing":  0.45, "h1_scalp":  1.32, "h1_momentum":  1.57, "m15_scalp":  1.86},
    "GBPNZD": {"swing": -0.34, "h1_scalp":  0.66, "h1_momentum": -1.23, "m15_scalp":  3.65},  # h1_scalp 0.66 (Phase 8.4 P03 4yr correction)
    "EURUSD": {"swing": -0.20, "h1_scalp": -0.17, "h1_momentum": -1.03, "m15_scalp":  2.62},
    "AUDNZD": {"swing": -2.16, "h1_scalp":  1.63, "h1_momentum":  0.55, "m15_scalp":  2.19},
}
```

**GBPNZD h1_scalp = 0.66 verified** (Phase 8.4 P03 4yr re-eval supersedes the stale `-0.60` literal that was hardcoded in `print_pair_summary` line 219). The lift to a typed module constant + refactor of `print_pair_summary` ensures the canonical source (`SHARPE_4YR`) and the legacy printer never drift again.

## CONTEXT D-01..D-12 Compliance

| Decision | How Honored |
| --- | --- |
| D-01 | RouteDecision (frozen dataclass, 4 fields) preserved from Plan 01; `route()` returns `RouteDecision \| None` per signature |
| D-02 | Single None sentinel collapses {regime/session/matrix/RAG/direction-conflict/no-signal} cases; `gate_blocked` log record on every None return |
| D-03 | `confidence` field = `rag_result["confidence"]` directly (pass-through, no transformation) |
| D-04 | `size_mult = min(1.0, getattr(cfg, <strategy>_size_mult) * regime_conf)` per-strategy size field selection (RESEARCH §3 fix for `position_size_mult` prose imprecision) |
| D-05 | Gate order Regime -> Session -> Matrix -> RAG (cheapest first) |
| D-06 | Short-circuit on first fail; one structured log record per blocked dispatch |
| D-07 | `_ITERATION_ORDER = (DAILY_SWING, H1_SCALP, H1_MOMENTUM, M15_SCALP)` |
| D-08 | Tie-break uses `SHARPE_4YR[pair][sharpe_key]`; `max()` over intraday candidates |
| D-09 | PositionStore Protocol + InMemoryPositionStore preserved from Plan 01 |
| D-10 | `_direction_conflict()` is pair-level only; strategy-agnostic per CONTEXT |
| D-11 | All deps injected at construction; no globals; `_direction_conflict_count` is per-instance |
| D-12 | Module location `V2/v3_intelligence/router.py` unchanged |

## RESEARCH Critical Gaps Closed

1. **#2 — `OnlineRegimeFilter.current_state_prob()`** — Method now exists, returns `tuple[RegimeState, float]` mirroring `update()`'s return shape. Read-only — does NOT advance the filter (Pitfall #6 honored).
2. **#3 — `pair_config.SHARPE_4YR` typed source** — Module constant lifted from `print_pair_summary` inline dict; D-08 tie-break can now read a single canonical source.

## Anti-Patterns Avoided (Verified)

- **No `update()` calls inside `route()`** — only `current_state_prob()` reads (Pitfall #6 closed). Live engine and Plan 04 simulator are responsible for advancing the filter once per bar BEFORE calling route().
- **No Viterbi reintroduction** — REGM-04 ban respected; `predict_viterbi` not referenced anywhere in router.py.
- **No `position_size_mult` field added** — uses existing per-strategy `*_size_mult` fields (RESEARCH §3 imprecision fix).
- **No Plan 01 stub class signature changes** — only filled bodies and added module-level constants/helpers.
- **No test file modifications** — Plan 01's RED tests turned GREEN by implementation alone.
- **`SESSION_RULES` empty-seed safe** — `is_tradeable_session()` returns True permissively when no rule registered; router correctly treats False as veto, True as "permit, other gates may still reject" (Pitfall #11).

## Deviations from Plan

None auto-fixed. Plan 09-02 executed exactly as written. The plan body in `<phase_specific_context>` and the actual `09-02-PLAN.md` file have a minor wording difference (the prompt-block paraphrase vs. the canonical PLAN.md), but the implementation matches the canonical PLAN.md with these explicit choices:
- `MIN_SHARPE = 0.3` per phase_specific_context anchor (also matches Phase 8.5 `SHARPE_GOOD`).
- Direction inference threshold ±2.0 (matches `PairConfig.swing_z_threshold`/`scalp_z_threshold`/`m15_z_threshold` defaults across all pairs); positions below ±2.0 return None with `no_signal_direction` reason instead of accepting any non-zero z.

The single auto-applied refinement: chose method (not property) for `current_state_prob` because the test fixture `_FakeOnlineRegimeFilter.current_state_prob()` already calls it as a method, and matching that convention avoids a fixture rewrite.

## Authentication Gates

None — pure routing logic. No external service or auth required.

## Hand-off

| Plan | Owns Next | Plan 02 Provides |
| --- | --- | --- |
| **Plan 03** | Extend `V2/scripts/fit_regime_detectors.py` to source `ACTIVE_PAIRS` from `PAIR_CONFIGS.keys()`; fit + persist any missing detector JSONs (currently 7/8 exist on disk; only EURUSD missing). Note: `b6dc206 refactor(09-03): source ACTIVE_PAIRS from PAIR_CONFIGS.keys()` already landed in parallel. | Plan 03 inherits a fully-functional 8-pair router; no router-side changes needed when EURUSD detector lands. |
| **Plan 04** | Build `V2/backtest/router_simulation.py` (CONTEXT D-18); PiT-wrapped 4yr loop over 8 pairs × H1 CSVs; emit `V2/reports/router_4yr_simulation.json` with `{aggregate_sharpe, best_single_sharpe, baseline_plus_0_2, gate_passed}`. | Plan 04 constructs `StrategyRouter(filters, rag, store, PAIR_CONFIGS)` via stable `__init__` signature; `route()` is read-only on regime state so `filter.update()` can be called once-per-bar in the simulator's outer loop. `direction_conflict_count` property gives Plan 04 an honest rejection-count for the simulation report without requiring a heuristic. |
| **Phase 10** | LiveSignalEngine — `from v3_intelligence import StrategyRouter, RouteDecision, Strategy, Direction` per D-20. | Plan 02 ships the Phase 9 contract surface clean; Phase 10 only needs to wire ZmqPositionStore + bridge consumer. |

## Self-Check: PASSED

Files exist on disk:
- `V2/v3_intelligence/router.py` (486 lines)
- `V2/v3_intelligence/regime/online_filter.py` (186 lines)
- `V2/v3_intelligence/pair_config.py` (251 lines)
- `V2/v3_intelligence/__init__.py` (50 lines)

Commits in `git log`:
- `cc5ac19` feat(09-02): add current_state_prob() + lift SHARPE_4YR (Task 1) — FOUND
- `91767b9` feat(09-02): implement StrategyRouter 4-gate chain (Task 2) — FOUND
- `ec7e597` feat(09-02): re-export Phase 9 router symbols (Task 3) — FOUND

Verification commands all pass:
- `python3 -m pytest tests/v3_intelligence/test_router.py -v` → 9/9 GREEN
- `python3 -c 'from v3_intelligence.pair_config import SHARPE_4YR; print(len(SHARPE_4YR))'` → 8
- `python3 -c 'from v3_intelligence.regime import OnlineRegimeFilter; assert hasattr(OnlineRegimeFilter, "current_state_prob")'` → exit 0
- `python3 -c 'from v3_intelligence import StrategyRouter, RouteDecision'` → exit 0
- `python3 -c 'from v3_intelligence.router import StrategyRouter; assert hasattr(StrategyRouter, "direction_conflict_count")'` → exit 0
- `python3 -m pytest tests/ -m "not slow" -q` → 226 passed, 1 failed (Plan 04 territory)

No stubs leak unintended UI/data behaviour. The 2 remaining `NotImplementedError` raises in router.py are intentional Phase 10 markers in `ZmqPositionStore.__init__` and `ZmqPositionStore.open_positions` (per CONTEXT D-09 / D-20 — Phase 10 wires the live ZMQ subscription).

## Known Stubs

None new. The pre-existing intentional stubs are tracked in Plan 01's SUMMARY:
- `ZmqPositionStore.__init__` raises `NotImplementedError` (Phase 10 wires bridge consumer)
- `ZmqPositionStore.open_positions` raises `NotImplementedError` (same)

Both surface immediately on accidental Phase-9-side instantiation, which is the intended behaviour per CONTEXT D-09.
