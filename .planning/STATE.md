---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-26T06:42:01.768Z"
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 16
  completed_plans: 13
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

Phase: 08.4 (infrastructure-prereqs-ohlcv-cache-rag-learning-loop-trade-replay) — EXECUTING
Plan: 2 of 4

### Progress Bar

```
Phase 6  [##########] 100% ZMQ Bridge Port — COMPLETE (BRDG-01/02/03/04)
Phase 7  [##########] 100% Backtest Entry Fix + 4yr Validation — COMPLETE (BKTS-01/02/03/04)
Phase 8  [##########] 100% HMM-GARCH Regime + PiT Port — Plans 01-04 complete (REGM-01/02/03/04 satisfied; awaiting /gsd:verify-work 08)
Phase 8.4[##........] 25%  Infrastructure Prereqs (Cache/RAG/GBPNZD/Replay) — Plan 01 complete (INFRA-01..04 registered + Wave 0 RED scaffold landed); Task 2 + Task 3 partial deferred (operator follow-up)
Phase 9  [..........] 0%   Strategy Router
Phase 10 [..........] 0%   Live Execution + Paper Trade Gate
```

**Overall milestone:** 12/24 requirements complete (BRDG-01..04, BKTS-01..04, REGM-01..04; INFRA-01..04 registered Phase 8.4 Plan 01 — implementation pending Plans 02-04)

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
| Phase 08 P04 | 12 min | 4 tasks | 9 files | - |
| Phase 08.4 P01 | 9 min (resume pass) | 4 tasks | 11 files | Wave 0 RED scaffold (32 fns / 53 items / 8 files) + INFRA-01..04 registered + psycopg/dotenv deps + bars-table migration provenance. Task 2 deferred (no SUPABASE_DB_URL); Task 3 partial (migration application deferred). Phase 8 regression: 109 passed, 20F/7E are new Wave 0 RED only |

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
| Phase 08 P04 | 12 min | 4 tasks | 9 files | REGM-04 GREEN (phase gate) — fit_regime_detectors.py CLI + 5 detector JSONs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP) with variance ratios 69x-101x; functional-pattern grep gate refinement (3/3 GREEN); D-16 parity GREEN at rtol=1e-6; v1_parity_tested=True stamped on all 5 JSONs; v3_intelligence 42 GREEN; full V2 112 GREEN; operator approved 2026-04-25 |

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
| Linux/MT5 failover applied per Phase 7 D-15 (08-04) | MetaTrader5 Python package not available on Linux dev host; download_history.py `_fetch_4yr_pairs_linux_failover()` copies existing 730d-shape H1 CSVs into *_H1_4yr.csv paths to preserve naming continuity. All 5 detectors fit on ~17k bars Jul-2023→Apr-2026 with strong regime separation (CRISIS/TRENDING ratios 69x-101x). Windows MT5 refresh recommended before LIVE-04 paper trade gate (non-blocking for Phase 9) |
| REGM-04 grep gate refined to functional patterns (08-04) | test_viterbi_ban.py switched from literal-substring scan to functional regex (imports + calls + attribute access) + viterbi.py file scan as defense-in-depth. Permits docstring/comment documentation of D-04 deliberate omission without false positives; catches actual re-introduction. 3/3 GREEN |
| v1_parity_tested metadata uses two-stage flip (08-04 / D-11) | fit_regime_detectors.py emits False at fit time; Task 3 flips to True only after the 4 @pytest.mark.slow parity tests clear at rtol=1e-6 vs V1 baseline. Keeps on-disk artefact an honest provenance record; pattern reusable for v3.0 EXPN-03 walk-forward refits |
| Wave 0 RED scaffold = 32 test fns / 53 collected items across 8 files (08.4-01) | Mirrors Phase 8 P01 pattern; Plans 02-04 turn them GREEN. Nyquist compliance: every implementation task has a `<verify>` command pointing to a real test file on disk |
| Task 2 deferred — SUPABASE_DB_URL not provisioned (08.4-01) | Operator chose deferred path; Plan 02 slow integration tests will RED-block (psycopg connection error) rather than RED-import-only until URL provisioned. Plan 02 cache.py development unaffected (unit tests use mock_psycopg_conn fixture) |
| Task 3 partial — bars-table migration provenance committed; application deferred (08.4-01) | mcp__supabase__* tools not in resumed agent context AND no SUPABASE_DB_URL for direct psql application. V2/migrations/0001_create_bars.sql committed with re-application playbook (Options A/B/C: MCP / psql / Python). DDL on disk is canonical source-of-truth; application is re-runnable side-effect |

### Critical Gates

| Gate | Phase | What It Unlocks |
|------|-------|-----------------|
| BRDG-03 DLL compatibility spike | Phase 6 | Phase 10 EA work — **PASS (2026-04-23): coke5151 fork, MT5 build 5800, Ubuntu+Wine 11.7 Staging. Phase 10 unblocked.** |
| BKTS-01 entry bias fix | Phase 7 | Trusted Sharpe numbers for BKTS-02/03 routing matrix entries |
| REGM-04 Viterbi ban | Phase 8 | Phase 9 router 4yr simulation (ROUT-04) — **PASS (2026-04-25): functional grep gate 3/3 GREEN; 5/5 detector JSONs landed; D-16 parity GREEN at rtol=1e-6; operator approved. Phase 9 ROUT-04 unblocked.** |
| ROUT-04 simulation Sharpe gate | Phase 9 | Phase 10 live deployment |
| LIVE-04 7-day paper trade | Phase 10 | Live capital deployment |

### Roadmap Evolution

- Phase 8.5 added 2026-04-25: Temporal & Session Analysis (prerequisite for Phase 9 StrategyRouter)
- Phase 8.4 inserted 2026-04-25 after Phase 8: Infrastructure Prereqs — OHLCV Cache + RAG Learning Loop + GBPNZD parity + Trade Replay (URGENT — addresses 2026-04-25 architectural audit findings: CSV-only data layer, unclosed RAG learning loop, missing GBPNZD 4yr H1, no MQ5 strategy-replay indicator, mempalace/claude-mem ambiguity). Inserted before Phase 8.5 so the heavy temporal analysis runs on a stable cache and produces decision_log entries that flow back into RAG memory.
- Scope correction 2026-04-25: PROJECT.md "5 forex pairs / daily-only" prose was stale; project-default scope restored to 8 pairs × M15/H1/Daily as committed in [pair_config.py](../V2/v3_intelligence/pair_config.py). H4 timeframe flagged as not-currently-in-scope, awaiting explicit decision.

### Todos

- [ ] Start Phase 6 planning: `/gsd:plan-phase 6`
- [ ] **Phase 8.4 follow-up:** Operator provisions SUPABASE_DB_URL in V2/.env (Session pooler URI, port 5432) — unblocks Plan 02 slow integration tests
- [ ] **Phase 8.4 follow-up:** Apply 0001_create_bars migration via Option A (MCP-enabled agent re-spawn) / B (`psql "$SUPABASE_DB_URL" -f V2/migrations/0001_create_bars.sql`) / C (Python psycopg) — provenance file already on disk

### Blockers

None blocking — Phase 8.4 follow-ups are tracked, not blockers (Plan 02 cache.py dev can proceed under mocked psycopg; only slow integration tests gate on Supabase availability).

---

## Session Continuity

**Last action:** Phase 8.4 Plan 01 COMPLETE — Wave 0 RED scaffold (32 test fns / 53 collected items across 8 files: conftest_infra + test_cache×2 + test_gbpnzd_parity + test_h4_provisioning + test_learning_loop + test_backfill_rag + test_adr) + INFRA-01..04 added to REQUIREMENTS.md (D-21 satisfied) + psycopg[binary]>=3.3 + python-dotenv>=1.0 in V2/pyproject.toml + V2/.env.example + V2/migrations/0001_create_bars.sql provenance. Task 2 deferred by operator (SUPABASE_DB_URL not provisioned); Task 3 partial — migration application deferred (mcp__supabase__* not in resumed agent context AND no DB URL for direct psql). Both deferrals tracked as Phase 8.4 known follow-ups; Plans 02-04 unblocked. Phase 8 fast-suite regression GREEN: 109 passed, 20 failed/7 errors are exclusively new Wave 0 RED tests (expected). Commits: 7aa2cf1 (T1), 502df94 (T3 partial), 7250313 (T4), bb03d2b (T5). (2026-04-26)
**Last agent:** execute-plan (resume pass)
**Stopped at:** Completed 08.4-01-PLAN.md (Tasks 3/4/5 of resume pass; Task 1 from prior agent; Task 2 operator-deferred)
**Next action:** Continue Phase 8.4 with Plan 02 (cache.py implementation). Plan 02 unit tests can run immediately under mocked psycopg; slow integration tests will skip until SUPABASE_DB_URL provisioned. Operator follow-up: provision SUPABASE_DB_URL + apply 0001_create_bars migration (three documented paths in file header) when ready.

---

## Phase Transition Log

| From | To | Date | Notes |
|------|----|------|-------|
| v1.0 complete (Phase 5) | v2.0 Phase 6 | 2026-04-22 | Milestone boundary |

---

*Last updated: 2026-04-25 — Phase 8 Plan 04 COMPLETE: fit_regime_detectors.py CLI + 5 detector JSONs + REGM-04 ratified (functional grep gate 3/3 GREEN) + D-16 parity GREEN at rtol=1e-6. All four REGM requirements (REGM-01/02/03/04) satisfied. Operator approved 2026-04-25. v3_intelligence 42/42 GREEN; full V2 project suite 112/112 GREEN. Phase 8 ready for verification (`/gsd:verify-work 08`). Phase 9 ROUT-04 unblocked (after Phase 8.5).*

*2026-04-26 — Phase 8.4 Plan 01 COMPLETE: Wave 0 RED scaffold (8 files / 32 test fns / 53 collected items) + INFRA-01..04 registered + psycopg/dotenv deps + V2/migrations/0001_create_bars.sql provenance. Operator deferred Task 2 (SUPABASE_DB_URL); Task 3 partial (migration application deferred). Plans 02-04 unblocked. Phase 8 regression GREEN (109 passed; 20 fails/7 errors are exclusively new Wave 0 RED — expected). Commits: 7aa2cf1, 502df94, 7250313, bb03d2b.*
