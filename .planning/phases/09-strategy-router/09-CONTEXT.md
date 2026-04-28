# Phase 9: Strategy Router - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `StrategyRouter` in [V2/v3_intelligence/router.py](../../../V2/v3_intelligence/router.py) — a stateful dispatcher that, on every bar close, consults the four upstream gates in fixed order (regime, session, 4yr matrix, RAG) and returns a typed `RouteDecision` or `None`. The router enforces ROUT-02 swing-first priority and ROUT-03 same-pair direction-conflict rejection. The phase ends when a 4yr portfolio simulation using the dispatch log shows aggregate Sharpe ≥ best single per-pair Sharpe + 0.2 (ROUT-04).

**In scope:**
- `RouteDecision` typed dataclass (V2/v3_intelligence/router.py)
- `StrategyRouter` class with injected dependencies (regime detector map, RAG filter, PositionStore)
- `PositionStore` protocol + two adapters (in-memory for backtest, ZMQ-backed for live — Phase 10 wires the live one)
- 4-gate decision chain w/ short-circuit-on-fail and structured trace logging
- Swing-first priority logic (ROUT-02): if swing fires on a pair, intraday strategies on that pair are short-circuited
- Same-pair direction-conflict rejection (ROUT-03): if any open position on pair conflicts with proposed direction, return None
- 4yr portfolio simulator that consumes dispatch log + per-strategy trade lists and produces aggregate Sharpe
- Unit test suite covering 5+ scenarios: regime-block, session-block, matrix-fail, RAG-below-threshold, valid-dispatch, swing-vs-intraday-priority, direction-conflict-reject

**Out of scope:**
- Live ZMQ-PositionStore implementation details (Phase 10 owns; a stub interface lands here)
- Walk-forward detector refits (deferred to v3.0 EXPN-03)
- Sharpe-weighted or Kelly-fractional sizing (defer to future enhancement; equal-per-dispatch baseline first)
- Live order publishing (Phase 10 LiveSignalEngine consumes RouteDecision; router itself does not touch ZMQ)
- New strategy types beyond M15_SCALP / H1_SCALP / H1_MOMENTUM / DAILY_SWING (those four are the closed dispatch set)

</domain>

<decisions>
## Implementation Decisions

### Router signature & return shape

- **D-01:** `route(pair: str, timestamp: datetime, market_data: BarSnapshot) -> RouteDecision | None`. `RouteDecision` is `@dataclass(frozen=True)` in `V2/v3_intelligence/router.py`. Fields: `strategy: Strategy` (enum: M15_SCALP / H1_SCALP / H1_MOMENTUM / DAILY_SWING), `direction: Direction` (enum: LONG / SHORT), `confidence: float` (0.0–1.0), `size_mult: float` (multiplier on pair_config base size; capped at 1.0). Mirrors `RegimeState` pattern in `V2/v3_intelligence/regime/types.py`.
- **D-02:** `None` return = "no dispatch" — collapses {regime-blocked, session-blocked, matrix-fail, RAG-below-threshold, direction-conflict, no-signal} to a single sentinel. Per ROUT-01 text. Observability handled via structured `logging` at DEBUG level: every `None` return writes a `gate_blocked` log record with the failing gate name; valid dispatches write `dispatched` records with the full RouteDecision.
- **D-03:** `confidence` field = RAG score directly (0.0–1.0). RAG is the only gate that produces a continuous score — regime/session/matrix are boolean. RAG score is already computed by the gate chain, so passing it through has zero extra cost.
- **D-04:** `size_mult` field = `pair_config[pair].position_size_mult * regime_confidence`. `regime_confidence` is the HMM posterior probability of the current state from `OnlineRegimeFilter.current_state_prob()`. Capped at 1.0 (never exceed pair_config base). Live path uses the same calculation; live broker enforces final lot-size limits independently via CCircuitBreaker (Phase 10).

### Decision chain ordering & short-circuit

- **D-05:** Gate order: **Regime → Session → Matrix → RAG**. Rationale: cheapest first.
  - **Regime** is a single dict lookup against `OnlineRegimeFilter.current_state` — O(1).
  - **Session** is `is_tradeable_session()` — predicate over SESSION_RULES dict + BLACKOUT_PATTERNS list — O(N_patterns), small constant.
  - **Matrix** is `pair_config[pair][strategy].sharpe_4yr >= threshold` — dict lookup.
  - **RAG** is `RAGSignalFilter.score_signal()` — vector similarity search against ChromaDB; the most expensive gate. Last-place ordering minimizes RAG queries on blocked dispatches.
- **D-06:** Short-circuit on first fail. Any `False` from a gate immediately returns `None`. Saves compute and produces simpler logs (one `gate_blocked` record per blocked dispatch, named for the failing gate).
- **D-07:** Per-strategy iteration order within a single bar: **Daily swing first**, then H1 scalp, H1 momentum, M15 scalp. If daily swing dispatches on a pair, the router does not evaluate the other strategies for that pair on that bar (ROUT-02 swing-first priority). If swing returns `None`, the next strategy is evaluated.
- **D-08:** Tie-breaking when multiple intraday strategies pass all gates on the same pair on the same bar: select the strategy with the highest 4yr Sharpe from `pair_config.py`. The matrix is the canonical evidence base; this rule is deterministic and audit-friendly.

### Position state coordination

- **D-09:** Router learns about open positions via an **injected `PositionStore` protocol** — defined in `V2/v3_intelligence/router.py` alongside the router itself. Protocol surface: `def open_positions(pair: str) -> list[OpenPosition]` returning frozen dataclasses with `direction`, `strategy`, `opened_at`. Two adapters land in this phase:
  - `InMemoryPositionStore` (backtest) — updated by the 4yr simulator on each fill
  - `ZmqPositionStore` (live skeleton) — Phase 10 wires actual ZMQ subscription; this phase ships the protocol stub
- **D-10:** Direction-conflict scope is **pair-level only**. ROUT-03 text: "opposite-direction position is already open on the same pair". Strategy is irrelevant — a swing-long on USDJPY blocks an H1-scalp-short on USDJPY. Same-direction stacking is permitted (router emits decision; the 4yr simulator and Phase 10 CCircuitBreaker apply final position-count caps).
- **D-11:** Stateful router instance, dependencies injected at construction: `StrategyRouter(regime_detectors: dict[str, OnlineRegimeFilter], rag_filter: RAGSignalFilter, position_store: PositionStore, pair_config: dict[str, PairConfig])`. No global state. Each pair has its own pre-fit `OnlineRegimeFilter` keyed by pair name (Phase 8 produced 5 detector JSONs; Phase 9 grows this to 8 — see D-19).
- **D-12:** Module location: `V2/v3_intelligence/router.py` — alongside `regime/`, `temporal_filters.py`, `pair_config.py`, `cache.py`. The router consumes all of them, so co-location matches the v3_intelligence module contract.

### 4yr simulation methodology (ROUT-04)

- **D-13:** Capital allocation: **equal-per-dispatch**. Each dispatched signal opens one full position sized by `pair_config[pair].position_size_mult * regime_confidence` (D-04). The simulator tracks open positions and routes new signals through the same `direction-conflict` and `swing-first` rules. Matches V1 backtest convention; simplest baseline against the "best single-strategy Sharpe + 0.2" comparison.
- **D-14:** Detector cadence: **4yr-fit single-pass detectors** from Phase 8 (`v1_parity_tested=True`, REGM-04 Viterbi-free). No walk-forward refit. Walk-forward is deferred to v3.0 EXPN-03 — out of v2.0 scope. Phase 9 grows the detector inventory from 5 (Phase 8) to all 8 active pairs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP existing; GBPNZD/EURUSD/AUDNZD new — see D-19).
- **D-15:** Concurrent signal handling: **strict ROUT-03 reject**. When the simulator emits a signal on a pair that already has a conflicting position, the simulator records `rejected_direction_conflict` to the dispatch log and does NOT queue. No replay-when-slot-opens behaviour. Out of scope.
- **D-16:** Sharpe comparison baseline (ROUT-04 gate text): aggregate router Sharpe ≥ **best single per-pair** Sharpe + 0.2. Compute as: for each pair, find the highest single-strategy Sharpe in `pair_config.py`; take the max across pairs; that is the baseline. Router Sharpe = aggregate of all dispatched-and-not-rejected trades over the 4yr window. Both numbers via PiT-gated pipeline (Phase 8 pit_validator).

### Test scaffold (RED-first)

- **D-17:** Wave 0 RED scaffold lands first (mirrors Phase 7/8/8.4/8.5 P01 pattern): test files at `V2/tests/v3_intelligence/test_router.py` covering 8 RED tests (one per scenario: regime-block, session-block, matrix-fail, RAG-below-threshold, valid-dispatch, swing-vs-intraday-priority, direction-conflict-reject, return-shape-typed-dataclass). All RED at scaffold time; Plans 02–04 turn them GREEN.
- **D-18:** ROUT-04 simulation lives in `V2/backtest/router_simulation.py` — a separate file from `backtest_hybrid.py`. Reuses `Phase 8 pit_validator` and `Phase 8 OnlineRegimeFilter`. Output: `V2/reports/router_4yr_simulation.json` with `{aggregate_sharpe, best_single_sharpe, baseline_plus_0_2, gate_passed: bool}`. Test asserts `gate_passed=True` against committed reference numbers.

### Detector inventory expansion

- **D-19:** Phase 8 produced 5 `OnlineRegimeFilter` detector JSONs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP). Phase 9 must grow this to 8 active pairs (add GBPNZD/EURUSD/AUDNZD) before the ROUT-04 simulation can run. This work lives in Plan 03 ("regime detector inventory completion") — extends `V2/scripts/fit_regime_detectors.py` to fit + persist the missing 3 detectors using the same 4yr-fit methodology Phase 8 established. Phase 7 4yr CSVs cover these pairs already (Phase 8.4 closed the GBPNZD gap).

### Live integration shape (Phase 10 contract)

- **D-20:** Phase 10's `LiveSignalEngine` will instantiate `StrategyRouter` once at startup with: regime detector JSONs loaded via `load_detector()` per pair; `RAGSignalFilter` initialized against `chroma_rag.trade_memory`; `ZmqPositionStore` connected to the bridge consumer; `pair_config` loaded as today. On every bar-close event, calls `router.route(pair, ts, market_data)`; if non-None, packs the `RouteDecision` into an `OrderRequest` schema and publishes over the ZMQ PUSH socket. Phase 9 ships the typed contract; Phase 10 wires it to ZMQ.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`V2/v3_intelligence/regime/`** — Phase 8: `OnlineRegimeFilter`, `PitClock`, `RegimeState` enum, `load_detector()`. Router consumes these directly; D-11 stores per-pair `OnlineRegimeFilter` instances at construction.
- **`V2/v3_intelligence/temporal_filters.py`** — Phase 8.5 SESS-04: `is_tradeable_session(pair, strategy, timeframe, ts) -> bool`, `is_blackout_window(ts) -> bool`. Router gate 2 calls these.
- **`V2/v3_intelligence/pair_config.py`** — Phase 7: `PAIR_CONFIGS` dict with per-pair × per-strategy 4yr Sharpe and enable flags. Router gate 3 (matrix check) reads this; D-08 tie-break also reads it.
- **`V2/v3_intelligence/rag_signal_filter.py`** — V1 ported: `RAGSignalFilter.score_signal()` returns 0.0–1.0 confidence. Router gate 4 calls this.
- **`V2/v3_intelligence/cache.py`** — Phase 8.4: `OHLCVCache` with PiT-safe auto-pull. Router does NOT call cache directly — it accepts a `BarSnapshot` from the caller (LiveSignalEngine in live, simulator in backtest); the caller is responsible for cache reads.
- **`V2/backtest/pit_validator.py`** — Phase 7: ROUT-04 simulation must pass through this PiT gate before any router metrics are committed.
- **`V2/v3_intelligence/learning_loop.py`** — Phase 8.4: `on_trade_close()` writes to SQLite + ChromaDB + decision_log. ROUT-04 simulator calls this on every simulated close so RAG memory grows during the 4yr run (already supported via INFRA-03).

### Established Patterns

- **Dataclass-based typed contracts** — `RegimeState` (`@dataclass(frozen=True)`) sets the precedent for typed return shapes in v3_intelligence. `RouteDecision` follows.
- **Injected dependencies, no globals** — `OHLCVCache(env=…)`, `OnlineRegimeFilter(detector_path=…)` — every v3_intelligence component takes its deps at construction. Router follows.
- **Wave 0 RED test scaffold** — Phase 7/8/8.4/8.5 all started with a RED-tests file in Plan 01. Phase 9 mirrors.
- **PitClock-wrapped backtests** — All 4yr simulations run inside `with PitClock(end_ts):`. ROUT-04 simulator must wrap.
- **`pair_config.py` as canonical 4yr matrix** — never recompute Sharpes ad-hoc; read from this module.
- **Single ledger** — `marketmind.db.trades` is the only trade journal; `decision_log` and ChromaDB are derived. Simulator must follow.

### Integration Points

- **Phase 10 LiveSignalEngine** — D-20 specifies the construction handshake. Router must be importable + constructable in <1s for the live engine startup path.
- **Backtest harness** — `V2/backtest/router_simulation.py` (new in Plan 04) replaces `backtest_hybrid.py` for the router-aware multi-strategy run; `backtest_hybrid.py` stays for the per-pair-per-strategy batch backtests already wired into Phase 7/8.
- **MT5 ZMQ schema** — `V2/bridge/schemas.py` `OrderRequest`. RouteDecision → OrderRequest is a Phase 10 mapping; Phase 9 ships only RouteDecision.
- **CCircuitBreaker (MT5 EA)** — Phase 10 owns. Phase 9 does not modify any MQL5 sources.

</code_context>

<specifics>
## Specific Ideas

- **Logging discipline** — Every `route()` call produces exactly one structured log record (`gate_blocked` or `dispatched`). Records use a stable schema for downstream Grafana dashboards in v3.0 MONI-01.
- **Frozen dataclasses everywhere** — RouteDecision, OpenPosition (used by PositionStore), all enums (Strategy, Direction). No mutation; all router state changes go through the simulator's harness or the live engine's event loop.
- **Mock all upstream gates in unit tests** — Phase 9 tests mock `OnlineRegimeFilter.current_state`, `is_tradeable_session()`, `pair_config[pair][strategy].sharpe_4yr`, `RAGSignalFilter.score_signal()`. Integration test (`test_router_integration.py`, slow-marker) wires real Phase 8 detector JSONs and ChromaDB.

</specifics>

<deferred>
## Deferred Ideas

- **Sharpe-weighted or Kelly-fractional sizing** — Out of v2.0 scope. v3.0 EXPN-04 may revisit when monthly re-ranking lands.
- **Walk-forward detector refits** — v3.0 EXPN-03.
- **Concurrent signal queueing** — Out of scope. Strict ROUT-03 reject for v2.0.
- **Strategy-level direction conflict** — Could relax ROUT-03 to allow swing+scalp on opposite directions on the same pair (Phase 9 D-10 keeps it pair-level). Revisit if router 4yr simulation shows opportunities being missed.
- **Live ZMQ position store implementation** — Phase 10 owns; Phase 9 ships protocol + in-memory adapter.
- **Grafana router dashboard** — v3.0 MONI-01.
- **Multi-account portfolio sizing** — Out of scope (PROJECT.md Out of Scope: "Multi-account / portfolio management").

</deferred>
