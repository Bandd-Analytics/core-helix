# ROADMAP: MarketMind Helix

**Milestone:** v2.0 — V3 Adaptive Strategy Dispatch System
**Created:** 2026-04-22
**Phases:** 6–10 + 8.5 (v1.0 ended at Phase 5)
**Coverage:** 20/20 v2.0 requirements mapped

---

## Phases

- [x] **Phase 6: ZMQ Bridge Port** — Establish the Python-MT5 communication layer with schema contract, heartbeat, DLL compatibility spike, and bar-close event push (completed 2026-04-24)
- [x] **Phase 7: Backtest Entry Fix + 4yr Validation** — Fix entry bias in the backtest harness, then generate trusted H1 scalp and Momentum routing matrix entries over 4yr data (completed 2026-04-24)
- [ ] **Phase 8: HMM-GARCH Regime + PiT Port** — Port and harden the regime classifier and point-in-time manager so downstream router and live paths consume a single, leakage-free regime series
- [ ] **Phase 8.5: Temporal & Session Analysis** — Full statistical analysis of when each pair and strategy performs best: session windows, hour-of-day/day-of-week/month/year heatmaps, entry/exit timing distributions, and risk calendar — produces session_config.py and temporal_filters.py consumed by Phase 9
- [ ] **Phase 9: Strategy Router** — Build the StrategyRouter that dispatches per-pair per-bar using regime gate, 4yr matrix, session gates, and RAG score, and validate aggregate portfolio Sharpe uplift
- [ ] **Phase 10: Live Execution + Paper Trade Gate** — Wire LiveSignalEngine and MT5 EA into the ZMQ bridge, fix equity baseline, and run 7-day IC Markets demo as final go/no-go gate

---

## Phase Details

### Phase 6: ZMQ Bridge Port

**Goal:** The Python-MT5 communication channel is operational, schema-typed, heartbeat-guarded, and DLL compatibility is confirmed on the target IC Markets terminal before any downstream EA work begins.

**Depends on:** Phase 5 (v1.0 foundation — MT5 EA skeleton, Python environment)

**Requirements:** BRDG-01, BRDG-02, BRDG-03, BRDG-04

**Success Criteria** (what must be TRUE):
1. A versioned msgpack schema contract file exists and defines all five message types (Tick, Bar, OrderRequest, Fill, Heartbeat) — no bridge code compiles against ad-hoc dicts
2. The ZMQ bridge sends a heartbeat every N seconds and auto-reconnects within one missed heartbeat cycle without manual restart
3. The mql-zmq DLL loads and sends a test message on the IC Markets MT5 terminal without crash or rejection — Phase 10 EA work is unblocked (go/no-go gate)
4. The MT5 EA pushes a completed-bar event per pair with timeframe tag; Python receives and processes it on bar close without polling the terminal

**Plans:** 4/4 plans complete

Plans:
- [x] 06-01-PLAN.md — Wave 1: V2 test scaffolding + msgpack schema contract (BRDG-01) [autonomous]
- [x] 06-02-PLAN.md — Wave 1: BRDG-03 DLL compatibility spike — PASS (coke5151 fork, build 5800, Wine 11.7) [checkpoint]
- [x] 06-03-PLAN.md — Wave 2: BridgeConsumer + BridgePublisher with env ports, heartbeat, auto-reconnect (BRDG-02) [autonomous]
- [x] 06-04-PLAN.md — Wave 3: MT5 EA bar-close publisher + consumer bar routing across D1/H1/M15 (BRDG-04) [checkpoint]

---

### Phase 7: Backtest Entry Fix + H1/Momentum 4yr Validation

**Goal:** The backtest harness produces trusted Sharpe numbers by entering on next-bar-open, and both H1 scalp and Momentum strategies have been validated over 4yr data across all active pairs — their results are committed to the routing matrix in pair_config.py via PiT-gated pipeline.

**Depends on:** Phase 6 (bridge schema establishes data contract that backtest must honour for bar events)

**Requirements:** BKTS-01, BKTS-02, BKTS-03, BKTS-04

**Success Criteria** (what must be TRUE):
1. backtest_hybrid.py enters all strategy loops on the next bar's open price — signal-bar close entries are eliminated and the previously inflated Sharpe delta (0.2–0.4) is demonstrably corrected in re-run results
2. H1 scalp strategy produces a routing matrix entry (Sharpe, win rate, pair-level performance) for every active pair from 4yr data, committed to pair_config.py
3. Momentum strategy produces a routing matrix entry (Sharpe, win rate, pair-level performance) for every active pair from 4yr data, committed to pair_config.py
4. pit_validator.py rejects any Sharpe number that exhibits future-bar leakage — no routing matrix entry enters pair_config.py without a passing PiT validation run

**Plans:** 4/4 plans complete

Plans:
- [x] 07-01-PLAN.md — Wave 0: Test scaffolding for BKTS-01/02/03/04 (RED tests covering entry fix, PiT validator, 4yr evaluator) [autonomous]
- [x] 07-02-PLAN.md — Wave 1: Entry bias fix across 4 strategy loops + before/after comparison CSV (BKTS-01) [autonomous]
- [x] 07-03-PLAN.md — Wave 1: Port V1 PiT validator to V2 with Title-case PRICE_COLUMNS + next-bar whitelist + CLI gate (BKTS-04) [autonomous]
- [x] 07-04-PLAN.md — Wave 2: 4yr H1 fetch + scalp/momentum evaluation + PiT-gated pair_config.py update (BKTS-02, BKTS-03) [checkpoint]

---

### Phase 8: HMM-GARCH Regime + PiT Port

**Goal:** The HMM-GARCH regime classifier and PiT manager are ported to the V2 intelligence module, state labels are pinned to prevent permutation, and OnlineRegimeFilter is the sole regime source — Viterbi is banned from both backtest and live code paths.

**Depends on:** Phase 6 (bridge bar events needed to define the online update cadence)

**Requirements:** REGM-01, REGM-02, REGM-03, REGM-04

**Success Criteria** (what must be TRUE):
1. HMM-GARCH classifier lives at V2/v3_intelligence/regime.py with a clear offline-fit / online-update split — V1 source is not imported by any V2 module
2. Re-fitting the HMM on a different dataset produces the same state label ordering (low/high variance pinned by variance rank) — no permutation of labels between fits
3. PiT manager at V2/v3_intelligence/pit.py enforces that no future bar is readable during backtest replay — a deliberate out-of-order read raises an error rather than silently succeeding
4. A grep or import trace of the V2 codebase finds zero direct Viterbi calls in any backtest loop or live signal path — OnlineRegimeFilter is the only entry point

**Plans:** 4 plans

Plans:
- [x] 08-01-PLAN.md — Wave 0: Test scaffolding (RED) for REGM-01/02/03/04 + V1 parity baseline capture (12 files: conftest + capture script + parity_baseline.npz + 8 test_*.py with 41 RED tests) [autonomous]
- [ ] 08-02-PLAN.md — Wave 1: Core port — pyproject.toml deps (hmmlearn>=0.3, arch>=6.0) + types.py (RegimeState) + emissions.py (GARCHParams) + hmm_garch.py (HMMGARCHRegimeDetector minus Viterbi) + bars_to_log_returns helper (REGM-01, REGM-02) [autonomous]
- [ ] 08-03-PLAN.md — Wave 2: OnlineRegimeFilter (Viterbi-free) + PitClock context manager + FutureBarReadError + UNBOUNDED sentinel + JSON persistence (save_detector / load_detector) (REGM-01, REGM-03, REGM-04) [autonomous]
- [ ] 08-04-PLAN.md — Wave 3: fit_regime_detectors.py CLI + 5/5 detector JSONs (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP) + REGM-04 grep gate ratification + D-16 parity test green (REGM-04) [checkpoint]

---

### Phase 8.5: Temporal & Session Analysis

**Goal:** Every pair-strategy combination has a statistically validated performance profile across trading sessions, time-of-day, day-of-week, day-of-month, and day-of-year — riskiest windows are identified and blacklisted, best windows are encoded as filters — so Phase 9's StrategyRouter can gate entries on time as a first-class input alongside regime and Sharpe.

**Depends on:** Phase 7 (4yr data and corrected Sharpe numbers must exist before time-sliced analysis is meaningful), Phase 8 (regime labels per bar enable regime×session interaction analysis — knowing whether London open is mean-reverting or trending changes how you weight it)

**Requirements:** SESS-01, SESS-02, SESS-03, SESS-04

**Success Criteria** (what must be TRUE):
1. For every active pair × strategy combination, a session performance table exists showing Sharpe, win rate, and trade count for each of: Tokyo (00:00–09:00 UTC), London (07:00–16:00 UTC), New York (13:00–22:00 UTC), London-NY overlap (13:00–16:00 UTC), London open (07:00–09:00 UTC) — top and bottom sessions identified per pair
2. Hour-of-day, day-of-week, day-of-month, and day-of-year heatmaps are produced per pair × strategy, showing average P&L per bar across each temporal bucket — best and worst buckets documented
3. A risk calendar is produced listing high-volatility recurring windows (FOMC, NFP, BoE, BoJ, ECB, RBA, RBNZ release windows) with empirical evidence of abnormal spread/slippage behaviour drawn from the 4yr dataset — these windows are flagged as blackout periods
4. `V2/v3_intelligence/session_config.py` and `V2/v3_intelligence/temporal_filters.py` exist with typed, testable interfaces that Phase 9 can import — `is_tradeable_session(pair, strategy, timestamp) -> bool` is the minimum contract

**Scope detail:**
- **Multi-timeframe comparison** — M15 vs H1 vs D1 Sharpe per pair per strategy; best timeframe per pair documented
- **Session windows** — Tokyo, London, New York, London-NY overlap, London open, NY open; winner per pair
- **Hour-of-day heatmap** — 24-bucket bar chart, wins vs losses by entry hour, per pair × strategy
- **Day-of-week analysis** — Monday–Friday P&L distribution; does Monday open / Friday close matter?
- **Day-of-month analysis** — first week vs mid-month vs month-end; rollover effects
- **Day-of-year analysis** — seasonal patterns, Q1/Q2/Q3/Q4 Sharpe split; holiday thin-market windows
- **Entry/exit timing distributions** — histogram of winning vs losing trade entry times; is there a golden hour?
- **Risk calendar** — recurring event windows with empirical spread/volatility spikes flagged as blackouts
- **Outputs** — session_config.py (allowed sessions per pair×strategy), temporal_filters.py (is_tradeable_session, is_blackout_window), analysis notebooks/CSVs as committed evidence

**Plans:** TBD

---

### Phase 9: Strategy Router

**Goal:** StrategyRouter dispatches the correct strategy per pair per bar using a three-layer decision chain (regime gate, 4yr matrix check, RAG score), enforces swing-first priority and direction conflict rejection, and a 4yr simulation demonstrates that aggregate portfolio Sharpe exceeds the best individual strategy Sharpe by at least 0.2.

**Depends on:** Phase 7 (routing matrix entries must be in pair_config.py), Phase 8 (OnlineRegimeFilter and PiT manager must be the sole regime source — REGM-04 Viterbi ban must be enforced before the simulation runs), Phase 8.5 (session_config.py and temporal_filters.py must exist — router uses is_tradeable_session() as a first-class gate alongside regime and 4yr matrix)

**Requirements:** ROUT-01, ROUT-02, ROUT-03, ROUT-04

**Success Criteria** (what must be TRUE):
1. StrategyRouter.route(pair, timestamp, market_data) returns a typed dict {strategy, direction, confidence, size_mult} or None, passing a unit test suite that covers regime-block, matrix-fail, session-block, RAG-below-threshold, and valid-dispatch scenarios
2. When a daily swing signal fires on a pair, the router selects it over any intraday strategy — and intraday strategies are only dispatched when no swing position is open on that pair
3. The router returns None when an existing position on the pair is open in the opposite direction — no counter-position orders are published
4. A 4yr portfolio simulation using the router dispatch log shows aggregate Sharpe >= (best single-strategy Sharpe across the matrix + 0.2), confirming that adaptive dispatch adds measurable value over picking one strategy

**Plans:** TBD

---

### Phase 10: Live Execution + Paper Trade Gate

**Goal:** LiveSignalEngine and the MT5 EA are connected end-to-end over the ZMQ bridge, equity baseline is fixed to use the live account balance, and a 7-day IC Markets demo paper trade confirms the live trade count matches the router's backtest expectation within 20% — clearing the final gate before real capital is deployed.

**Depends on:** Phase 6 (DLL spike must have passed — BRDG-03 go/no-go gate), Phase 9 (router must be complete and validated)

**Requirements:** LIVE-01, LIVE-02, LIVE-03, LIVE-04

**Success Criteria** (what must be TRUE):
1. LiveSignalEngine runs as a Python service, subscribes to MT5 bar-close events via ZMQ, calls StrategyRouter.route() for each bar, and publishes a valid OrderRequest to the ZMQ PUSH socket — observable in the terminal log without manual triggers
2. The MT5 EA reads an OrderRequest from the ZMQ PULL socket and executes it through CCircuitBreaker — a test order placed via Python appears in MT5 order history
3. CCircuitBreaker reads its equity baseline from AccountInfoDouble(ACCOUNT_EQUITY) on OnInit — the hard-coded 1000.0 constant is removed and the EA compiles and initialises with a live account value
4. After 7 consecutive trading days on the IC Markets demo account, the live trade count is within ±20% of the count projected by the router backtest for that period — go/no-go gate cleared for live capital deployment

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. ZMQ Bridge Port | 4/4 | Complete | 2026-04-24 |
| 7. Backtest Entry Fix + 4yr Validation | 4/4 | Complete | 2026-04-25 |
| 8. HMM-GARCH Regime + PiT Port | 0/4 | Planned | — |
| 8.5. Temporal & Session Analysis | 0/? | Not started | — |
| 9. Strategy Router | 0/? | Not started | — |
| 10. Live Execution + Paper Trade Gate | 0/? | Not started | — |

---

## Dependency Graph

```
Phase 6 (Bridge)
    ├── Phase 7 (Backtest) ──────────────────────────────────┐
    └── Phase 8 (Regime) ──── Phase 8.5 (Session Analysis) ── Phase 9 (Router) ── Phase 10 (Live)
         [REGM-04 Viterbi ban]  [session_config.py]           [4yr + session gates] [BRDG-03 gate]
```

**Critical path:** Phase 6 → Phase 8 → Phase 8.5 → Phase 9 → Phase 10

Phase 7 can run in parallel with Phase 8 after Phase 6 completes. Phase 8.5 requires both Phase 7 (4yr data) and Phase 8 (regime labels for regime×session interaction). Phase 9 cannot begin until Phase 7, Phase 8, and Phase 8.5 are all done.

---

*Roadmap created: 2026-04-22*
*Phase 7 completed: 2026-04-25 (4 plans, 70/70 tests, BKTS-01/02/03/04 verified)*
*Phase 8.5 added: 2026-04-25 — Temporal & Session Analysis, prerequisite for Phase 9 StrategyRouter*
*Phase 8 planned: 2026-04-25 — 4 plans (Wave 0 RED scaffold → Wave 1 core port → Wave 2 OnlineRegimeFilter+PitClock+JSON → Wave 3 CLI+5 detector JSONs+grep gate+parity)*
*Next: `/gsd:execute-phase 8`*
