---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-23T13:26:55.929Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 4
  completed_plans: 2
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

Phase: 06 (zmq-bridge-port) — EXECUTING
Plan: 3 of 4

### Progress Bar

```
Phase 6  [..........] 0%   ZMQ Bridge Port
Phase 7  [..........] 0%   Backtest Entry Fix + 4yr Validation
Phase 8  [..........] 0%   HMM-GARCH Regime + PiT Port
Phase 9  [..........] 0%   Strategy Router
Phase 10 [..........] 0%   Live Execution + Paper Trade Gate
```

**Overall milestone:** 0/20 requirements complete

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

## Plan Execution Metrics

| Plan | Duration (s) | Tasks | Files | Notes |
|------|-------------|-------|-------|-------|
| Phase 06 P01 | 173 | 3 tasks | 8 files | BRDG-01 schema contract complete, 15 tests GREEN |
| Phase 06 P02 | — | 2 tasks | 4 files | BRDG-03 gate PASS — coke5151 fork, MT5 build 5800, Ubuntu+Wine 11.7 |

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

**Last action:** 06-02 complete — BRDG-03 PASS committed (04c846d). MT5 build 5800, coke5151 fork, Ubuntu+Wine 11.7 Staging. (2026-04-23)
**Last agent:** execute-phase
**Next action:** Execute plan 06-03 (Wave 2) — BridgeConsumer + BridgePublisher with env ports, heartbeat, auto-reconnect (BRDG-02)

---

## Phase Transition Log

| From | To | Date | Notes |
|------|----|------|-------|
| v1.0 complete (Phase 5) | v2.0 Phase 6 | 2026-04-22 | Milestone boundary |

---

*Last updated: 2026-04-23 — 06-01 BRDG-01 schema contract complete (15 tests GREEN)*
