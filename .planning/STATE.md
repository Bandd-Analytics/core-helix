---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-25T09:25:37.294Z"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 12
  completed_plans: 11
---

# STATE: MarketMind Helix

*This file is the project's memory. Updated at every phase transition and plan completion.*

---

## Project Reference

**Milestone:** v2.0 — V3 Adaptive Strategy Dispatch System
**Core Value:** A statistically validated daily Z-score mean-reversion signal (Sharpe 2.08) extended to an adaptive multi-strategy router dispatching live to MT5 via ZMQ bridge
**Total Phases (this milestone):** 5 (Phases 6–10)
**Total Requirements (this milestone):** 20

---

## Current Position

Phase: 8 (HMM-GARCH Regime + PiT Port) — EXECUTING
Plan: 4 of 4

### Progress Bar

```
Phase 6  [##########] 100% ZMQ Bridge Port — COMPLETE (BRDG-01/02/03/04)
Phase 7  [##########] 100% Backtest Entry Fix + 4yr Validation — COMPLETE (BKTS-01/02/03/04)
Phase 8  [########..] 75%  HMM-GARCH Regime + PiT Port — Plans 01/02/03 complete (REGM-01 full / REGM-02 / REGM-03 satisfied; REGM-04 ratification pending Plan 04)
Phase 9  [..........] 0%   Strategy Router
Phase 10 [..........] 0%   Live Execution + Paper Trade Gate
```

**Overall milestone:** 11/20 requirements complete (BRDG-01..04, BKTS-01..04, REGM-01, REGM-02, REGM-03)

---

## Performance Metrics (v1.0 Baseline)

| Metric | Value |
|--------|-------|
| Sharpe (base) | 1.67 |
| Sharpe (with RAG) | 2.08 |
| P&L (730-day backtest) | +42.84% |
| Trade count (walk-forward) | 513 |
| Win rate | 35.4% |
| Max drawdown target | <15% |

*v2.0 target: aggregate router Sharpe >= best single-strategy Sharpe + 0.2 (ROUT-04)*

---
| Phase 06 P04 | 230 | 3 tasks | 4 files | - |
| Phase 07 P01 | 208 | 3 tasks | 4 files | - |
| Phase 07 P02 | 498 | 3 tasks | 6 files | - |
| Phase 07 P03 | 755 | 2 tasks | 3 files | - |
| Phase 07 P04 | 300 | 3 tasks | 9 files | - |
| Phase 08 P01 | 319 | 3 tasks | 12 files | - |
| Phase 08 P02 | 32 min | 3 tasks | 7 files | - |
| Phase 08 P03 | 9 min | 3 tasks | 5 files | - |

## Plan Execution Metrics

| Plan | Duration (s) | Tasks | Files | Notes |
|------|-------------|-------|-------|-------|
| Phase 06 P01 | 173 | 3 tasks | 8 files | BRDG-01 schema contract complete, 15 tests GREEN |
| Phase 06 P02 | — | 2 tasks | 4 files | BRDG-03 gate PASS — coke5151 fork, MT5 build 5800, Ubuntu+Wine 11.7 |
| Phase 06 P03 | 182 | 3 tasks | 4 files | BRDG-02 complete — BridgeConsumer + BridgePublisher, 43 tests GREEN |
| Phase 06 P04 | 230 | 4 tasks | 4 files | BRDG-04 PASS — EA compiles 0 errors, all 5 pairs M15 bar-close received in Python; 53 tests GREEN |
| Phase 07 P01 | 208 | 3 tasks | 4 files | Wave 0 test scaffold — 17 RED tests for BKTS-01/02/03/04 |
| Phase 07 P02 | 498 | 3 tasks | 6 files | BKTS-01 entry-fix GREEN (4/4 tests pass) |
| Phase 07 P03 | 755 | 2 tasks | 3 files | BKTS-04 H1 momentum GREEN (7/7 tests pass) |
| Phase 07 P04 | 300 | 3 tasks | 9 files | BKTS-02/03 4yr routing matrix GREEN (6/6 tests pass) |
| Phase 08 P01 | 319 | 3 tasks | 12 files | Wave 0 test scaffold — 41 RED tests across 8 files; parity_baseline.npz captured from V1 |
| Phase 08 P02 | 32 min | 3 tasks | 7 files | REGM-01 offline-fit + REGM-02 variance-rank pinning GREEN — HMMGARCHRegimeDetector ported from V1 minus Viterbi (D-04); 18 tests GREEN (5 emissions + 4 bars + 9 detector); hmmlearn 0.3.3 + arch 8.0.0 |
| Phase 08 P03 | 9 min | 3 tasks | 5 files | REGM-01 online-update + REGM-03 PitClock GREEN — OnlineRegimeFilter ported from V1 minus dead emission-prob import; PitClock + FutureBarReadError + UNBOUNDED + pit_gated; save_detector/load_detector JSON D-11; 17 tests GREEN (5 online_filter + 8 pit + 4 persistence) |

## Accumulated Context

### Carried Forward from v1.0

- Daily swing strategy is the ONLY validated signal source; H1 scalp/momentum layers destroy alpha when run concurrently — valid ONLY as separately dispatched strategies via router
- RAG filter (ChromaDB) boosts Sharpe from 1.67 to 2.08 — non-negotiable feature
- Hurst regime filter added in final v1.0 commit — not yet validated in live conditions
- BEC partial close shelved until win rate >= 40% (currently 35.4%)
- MT5 EA compiles but has no live connection to Python signal engine
- USDJPY is the crown jewel (Sharpe 3.09, 44.4% win rate)
- IC Markets Raw Spread account is the target broker

### Key Decisions for v2.0

| Decision | Rationale |
|----------|-----------|
| ZMQ bridge (not file-polling, not named pipes) | Sub-10ms latency; file-polling has 1s latency + lock risk; named pipes Windows-only |
| Adaptive router over single-strategy dispatch | H1 scalp/momentum valid as isolated dispatched strategies — not concurrent layers |
| 4yr validation window for routing matrix | Replaces 730-day numbers with statistically stronger evidence |
| OnlineRegimeFilter only (Viterbi banned) | Prevents future-bar leakage in both backtest and live |
| Swing-first priority in router | Daily swing fires whenever conditions met; intraday only when no swing position open |
| 7-day IC Markets demo as live gate | Validates live dispatch matches backtest expectation within 20% before real capital |
| Fill replaces OrderResult in V2 (D-08) | class OrderResult does not exist in V2/bridge/ — V2 uses Fill throughout (06-01) |
| SCHEMA_VERSION=1 module constant (D-06) | Single source of truth for schema version in V2/bridge/schemas.py (06-01) |
| unpack_heartbeat returns dict not datetime64 (D-07) | Consumer can check schema_version on connect — deliberate V1 breaking change (06-01) |
| zmqContext.destroy(0) omitted from OnDeinit (06-04) | coke5151 RAII destructor handles context cleanup on scope exit — explicit destroy causes double-free crash |
| _handle_bar_frame dual-decoder: msgpack first, JSON fallback (06-04) | Consumer resilient to both V2 msgpack (Python-to-Python) and MQL5 JSON Option A payload formats |
| PYTHONPATH=V1/helix for V1 baseline capture (08-01) | V1's alpha/__init__.py uses absolute `from src.alpha.*` imports — package root must be V1/helix, not V1/helix/src |
| parity_baseline.npz committed to repo (08-01) | Frees CI from any V1 environment dependency; .npz captured once via _capture_v1_baseline.py |
| Wave 0 = 41 RED tests for REGM-01/02/03/04 (08-01) | Mirrors Phase 7 P01 pattern; Plans 02/03/04 turn them GREEN |
| HMMGARCHRegimeDetector ported verbatim from V1 minus predict_viterbi method and _compute_log_emission_probs helper (08-02 / D-04) | REGM-04 Viterbi ban enforced by-construction at the source; the only consumer of _compute_log_emission_probs was predict_viterbi |
| bars_to_log_returns helper accepts both 'close' and 'Close' columns (08-02 / D-20) | V1 / synthetic tests use lowercase; Phase 7 _H1_4yr.csv files use Title-case — single helper covers both |
| OnlineRegimeFilter ported from V1 minus dead emission-prob import (08-03 / RESEARCH A.3) | V1 imported the helper on line 9 but never called it (emission inlined in update()). V2 omits the import entirely; grep gates verify symbol absence |
| PitClock.UNBOUNDED constructed at module load via class-level assignment (08-03 / D-25) | Sentinel always available before any with-block; None as_of_ts disables enforcement (read returns df verbatim, assert_no_future never raises) |
| save_detector + load_detector live in dedicated persistence.py module (08-03 / D-11) | Keeps regime/__init__.py focused on re-exports + bars_to_log_returns helper; isolates JSON schema for future evolution; mirrors V1 one-concept-per-file convention |

### Critical Gates

| Gate | Phase | What It Unlocks |
|------|-------|-----------------|
| BRDG-03 DLL compatibility spike | Phase 6 | Phase 10 EA work — **PASS (2026-04-23): coke5151 fork, MT5 build 5800, Ubuntu+Wine 11.7 Staging. Phase 10 unblocked.** |
| BKTS-01 entry bias fix | Phase 7 | Trusted Sharpe numbers for BKTS-02/03 routing matrix entries |
| REGM-04 Viterbi ban | Phase 8 | Phase 9 router 4yr simulation (ROUT-04) |
| ROUT-04 simulation Sharpe gate | Phase 9 | Phase 10 live deployment |
| LIVE-04 7-day paper trade | Phase 10 | Live capital deployment |

### Todos

- [ ] Start Phase 6 planning: `/gsd:plan-phase 6`

### Blockers

None currently.

---

## Session Continuity

**Last action:** Phase 8 Plan 03 complete — OnlineRegimeFilter ported from V1 minus dead emission-prob import (REGM-01 online half); PitClock + FutureBarReadError + UNBOUNDED + pit_gated landed (REGM-03); save_detector/load_detector JSON D-11 schema. 17 tests GREEN (5 online_filter + 8 pit + 4 persistence); v3_intelligence fast suite 35/35 GREEN; full V2 fast suite 105/105 GREEN — no Phase 6/7 regression. (2026-04-25)
**Last agent:** execute-phase
**Next action:** Execute Phase 8 Plan 04 (Wave 3: fit_regime_detectors.py CLI + Viterbi grep gate ratification + parity tests — checkpoint plan; produces 5 detector JSONs in V2/data/regime/)

---

## Phase Transition Log

| From | To | Date | Notes |
|------|----|------|-------|
| v1.0 complete (Phase 5) | v2.0 Phase 6 | 2026-04-22 | Milestone boundary |

---

*Last updated: 2026-04-25 — Phase 8 Plan 03 COMPLETE: OnlineRegimeFilter + PitClock + JSON persistence landed. REGM-01 (full) + REGM-03 GREEN. 17 newly-green tests; full v3_intelligence fast suite 35/35 GREEN; full V2 fast suite 105/105 GREEN. Plan 04 next: fit_regime_detectors.py CLI + Viterbi grep gate ratification + 5 detector JSONs (checkpoint plan).*
