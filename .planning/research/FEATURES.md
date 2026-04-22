# Feature Landscape — V3 Adaptive Strategy Dispatch System

**Domain:** Adaptive strategy router for a multi-pair, multi-strategy forex algo trading system
**Researched:** 2026-04-21
**Confidence sources:** V1 codebase (RegimeOrchestrator, HMMGARCHRegimeDetector, OnlineRegimeFilter, RecalibrationService, LinuxConsumer, pit_manager, pit_validator, message_schemas, abstract), V2 codebase (PairConfig evaluation matrix, HybridMultiTimeframeBacktest, CCircuitBreaker, CSignalManager), PROJECT.md

---

## Table Stakes

Features users expect in a production adaptive routing system. Missing = system is not deployable.

| Feature | Why Expected | Complexity | Dependencies on Existing Stack |
|---------|--------------|------------|-------------------------------|
| ZMQ bridge heartbeat + stale detection | Without it, the signal engine silently stops working and the EA keeps running with stale state — known destroyer of small accounts | Low-Medium | LinuxConsumer.is_stale already implemented in V1; needs porting to V2 context and wiring to live signal engine |
| Per-symbol close-bar detection | Router must be called exactly once per bar close, not per tick — calling on every tick re-enters the regime filter and generates duplicate signals | Medium | tick stream from ZMQ bridge; needs explicit bar-close detection logic (timestamp boundary check) |
| Position collision check before dispatch | Router should not dispatch a new entry if an open position on the same pair and direction already exists — double-loading a correlated position is a capital risk | Medium | CPositionManager (V2 EA) + requires Python-side position state mirror updated from OrderResult fills |
| Circuit breaker gate before any OrderRequest | EA-side CCircuitBreaker already exists but Python signal engine must also check its own soft limit before publishing — defense in depth | Low | CCircuitBreaker (V2 EA, already built); Python side needs a soft DD monitor mirroring the same thresholds |
| Regime gate as first filter in router | Before any signal scoring, check regime state — wrong regime = no signal regardless of indicator values; prevents mean-reversion entries in trending regime | Low | Hurst regime filter (already built); HMM-GARCH will replace/supplement; hysteresis dwell logic from V1 RegimeOrchestrator must be ported |
| OrderRequest strategy tag in comment field | EA must know which strategy dispatched the order for exit management (different ATR multiples per strategy type) — comment field is the only channel in the existing schema | Low | OrderRequest.comment already has a `comment: str` field in abstract.py; convention must be defined |
| PiT compliance enforcement in all backtest code | HMM training data, regime labels, and signal features must all use only data available at signal time — failure here produces backtests that cannot be replicated in live | High | pit_manager.pit_read + PiTValidator (V1, already built) — must be integrated into all new backtest scripts for H1 scalp and momentum strategies |
| 4-year routing matrix persisted to config | Per-pair per-strategy Sharpe results must be written to a durable config (pair_config.py pattern already used in V2) so router can read without re-running backtests | Low | pair_config.py (V2) already has this pattern for swing; needs extension to include H1 scalp and momentum entries |

---

## Differentiators

Features that set this system apart from a single-strategy static EA. Not expected by default, but provide substantial alpha lift.

| Feature | Value Proposition | Complexity | Dependencies on Existing Stack |
|---------|-------------------|------------|-------------------------------|
| HMM-GARCH regime classifier (forward pass only) | Forward-algorithm OnlineRegimeFilter produces causal regime probabilities with no look-ahead — far more robust than ADX/Hurst alone as it models volatility state transitions explicitly | High | HMMGARCHRegimeDetector + OnlineRegimeFilter + RecalibrationService all fully implemented in V1 — need porting to V2 signal engine; GARCH emission path already tested |
| Atomic model swap at bar boundary | RecalibrationService.apply_pending() pattern (V1 D-12) ensures the online filter is never mid-update when a new bar arrives — prevents race condition in regime label assignment | Low | RecalibrationService.apply_pending() already implemented; must be reproduced in live signal engine's bar-close event handler |
| 20-bar hysteresis dwell logic | Prevents thrashing between regime states on noisy transitions — V1 RegimeOrchestrator._hysteresis_bars=20 with confidence thresholds per state (0.65–0.70) | Low | RegimeOrchestrator dwell logic already implemented in V1; must be re-implemented in v2 StrategyRouter or ported directly |
| RAG confidence gate as final filter | Existing +0.41 Sharpe lift from ChromaDB RAG filter should be applied after regime gate + routing matrix — scored confidence acts as signal quality multiplier on size_mult output | Medium | RAGSignalFilter + ChromaDB already integrated in V2 backtest; needs wiring into StrategyRouter dispatch path |
| Per-pair per-strategy routing matrix (pair_config.py) | Data-driven routing decisions based on validated 4yr Sharpe per strategy per pair — avoids dispatching strategies with known negative edge on specific pairs | Low | pair_config.py (V2) already has this structure — GBPJPY M15 disabled (Sh -0.02), USDJPY H1 scalp disabled (Sh -2.34); router consumes allow_scalp/allow_momentum flags |
| Dual-gate model recalibration | V1 RecalibrationService enforces stationarity gate (alpha+beta < 1) and 90% state agreement on last 100 bars before applying new model — prevents degraded recalibration from corrupting live state | Medium | RecalibrationService already built; weekly recalibration schedule needs a cron/timer trigger in signal engine service |
| 7-day paper trade count gate | Requires live demo trade count within ±20% of backtest projection before promoting to live capital — catches execution-path bugs that don't show up in unit tests | Medium | Needs new: paper_gate.py module comparing SQLite trade journal counts vs backtest expectation; trade logger already writes to SQLite |

---

## Anti-Features

Features that look beneficial but provably hurt this specific system. Flag and avoid.

| Anti-Feature | Why It Hurts This System | What to Do Instead |
|--------------|--------------------------|-------------------|
| Running H1 scalp and daily swing concurrently on the same capital pool | Confirmed in V2 testing: running both simultaneously on the same pair destroys daily alpha — swing exits are triggered early by intraday noise, and the correlated losses compound; the pair_config evaluation matrix shows the damage | Route via strategy router — dispatch exactly one strategy per pair per bar based on regime + matrix, never both simultaneously with shared capital |
| Multi-directional positions on the same pair from different strategies | If swing says LONG USDJPY and momentum says SHORT USDJPY simultaneously, you have paid spread and commission on both legs while netting near-zero exposure — broker profit, yours zero | Router must enforce a single-direction lock per pair: if an open position exists in direction X, block all dispatch of direction -X until position is closed; same-direction stacking is permitted per size_mult rules |
| Viterbi decoding in the live signal path | predict_viterbi() is the offline batch decoder — it uses the full observation sequence (backward pass). Running it on live data introduces look-ahead bias and is O(T·N²) per bar | Use OnlineRegimeFilter.update() exclusively in the live path — it is the causal forward algorithm, O(N²) per bar where N=3 states |
| Recalibrating HMM-GARCH on every bar | Refitting the full Gaussian HMM (EM algorithm, 100 iterations) is expensive (~1–5s on 1260 bars) — calling it per bar would block the signal engine loop entirely | Recalibrate on a timer: weekly or after 5% equity drawdown; use RecalibrationService.has_pending + apply_pending() at bar boundary to swap atomically |
| Confidence threshold without hysteresis | Setting a single confidence threshold on regime output (e.g., "only trade if confidence > 0.65") without dwell protection causes rapid regime flickering during ambiguous market periods | Use the 20-bar dwell counter pattern from V1 RegimeOrchestrator: only allow regime change after N consecutive bars supporting the new state with confidence above the entry threshold |
| Paper trade gate using P&L instead of trade count | P&L over 7 days is heavily influenced by market conditions and volatility — a system can be routing correctly and show zero trades due to no signals, or large losses due to adverse moves | Gate on trade count ±20% — this measures whether the execution pipeline (ZMQ bridge, EA, fill confirmation) is functioning, not whether markets cooperated; P&L validation is a separate, longer-horizon check |
| Position sizing based on HMM confidence directly | Using regime probability output (e.g., 0.73 confidence) as a continuous size multiplier creates unpredictable sizing behavior and amplifies risk during transitions | Use confidence as a binary gate (above threshold = full size_mult from pair_config; below = no trade) — RAG scorer already provides a continuous confidence multiplier for size scaling |
| Storing regime labels at the time of model refit | Recalibration produces new Viterbi labels for the historical window — writing these back to the signal history creates retrospective look-ahead bias in any downstream analysis | Store regime labels only from the OnlineRegimeFilter forward pass; recalibration updates model parameters only, never rewrites historical labels |
| Publishing OrderRequest for every regime-valid signal without dedup | H1 bar close fires once per bar on 5 pairs — if bar close detection has any imprecision (e.g., processes the same H1 close twice), the same signal is published twice, creating accidental double-entry | Deduplicate on (symbol, strategy, bar_open_timestamp) in the signal engine before publishing to ZMQ; the EA's CCircuitBreaker is a second safety net but not a substitute |

---

## Feature Dependencies

```
ZMQ bridge (tick/bar stream)
    └── Close-bar detection
            └── Regime gate (OnlineRegimeFilter.update())
                    └── Strategy routing matrix (pair_config allow_* flags)
                            └── Strategy indicator check (z-score, momentum filter)
                                    └── RAG confidence scorer (ChromaDB)
                                            └── Position collision check (open positions mirror)
                                                    └── OrderRequest dispatch → ZMQ → EA
                                                                └── OrderResult fill confirmation → position state update

RecalibrationService (weekly timer)
    └── atomic apply_pending() at bar boundary
            └── OnlineRegimeFilter.reset() after swap

PiT discipline
    └── pit_read() for all feature construction in backtests
    └── PiTValidator AST scan on all new strategy Python files
    └── validate_pit_compliance() IC ratio test before promoting any new strategy to routing matrix

HMM-GARCH offline fit (on 4yr data)
    └── OnlineRegimeFilter initialization (requires fitted detector)
    └── RecalibrationService (needs fitted detector as baseline)

4yr backtest (vectorbt.pro) → Sharpe per pair per strategy
    └── pair_config.py routing matrix entries (allow_scalp, allow_momentum flags + size_mult)
    └── StrategyRouter reads pair_config at startup

7-day paper trade gate
    └── ZMQ bridge (live execution path)
    └── SQLite trade journal (fill confirmations logged)
    └── Backtest trade count expectation (from 4yr result)
```

---

## Feature Detail: Position Collision Handling

This is the most operationally critical edge case in the router. Three scenarios:

**Scenario 1: Same pair, same direction, different strategy**
Swing LONG GBPUSD (open, 120-bar hold) + Momentum LONG GBPUSD signal arrives.
Correct behavior: allow if position state allows stacking per size_mult; check total exposure does not exceed pair capital limit. Size_mult for momentum (0.4) + swing (1.0) = 1.4x total — acceptable within capital limits.
Implementation: router checks open position direction; if direction matches, calculate combined size_mult and gate against max_combined_mult per pair (recommend: 1.5x cap for T1 pairs).

**Scenario 2: Same pair, opposite direction, different strategy**
Swing LONG GBPUSD (open) + H1 scalp SHORT GBPUSD signal arrives.
Correct behavior: block the new SHORT signal entirely — do not dispatch. Net exposure cancels, commission is wasted.
Implementation: router checks position registry for (pair, direction); if existing position direction == opposite of new signal direction, return None from dispatch. This is non-negotiable.

**Scenario 3: Regime changes while position is open**
Regime was MEAN_REVERTING (swing active, position open), transitions to TRENDING.
Correct behavior: DO NOT force-close the open position on regime change. Let existing exits (ATR target, stop, timeout) run. Block new entries for the old strategy while regime is trending.
Implementation: regime gate applies only to new entries; existing positions are managed by exit rules set at entry time, not re-evaluated by regime at each bar.

---

## Feature Detail: Regime Classifier State Transitions

The V1 OnlineRegimeFilter uses the forward algorithm (causal) — correct for live use. Key behaviors to preserve:

**Cold start behavior:** At startup, filter initializes to HMMGARCHRegimeDetector.startprob_ — typically the stationary distribution from the training data. This means the first 5–10 bars after startup produce less reliable regime estimates. The 20-bar hysteresis provides natural protection during warmup.

**CRISIS state behavior:** In V1 REGIME_ACTIVATION, CRISIS maps to an empty engine list — no signals at all. This is the right default. In v2, CRISIS should mean: block all new entries; allow existing exits to run; do not publish any OrderRequest.

**Transition confidence thresholds (from V1):**
- TRENDING entry: 0.70
- MEAN_REVERTING entry: 0.65
- CRISIS entry: 0.60 (lower because speed of recognition matters more)
- Exit threshold: 0.30 (exit current regime if confidence falls below this)
These thresholds are validated in V1 and should not be changed without re-backtesting.

**Recalibration gate failures:** If RecalibrationService.recalibrate() fails Gate 1 (stationarity) or Gate 2 (state agreement < 90%), the active model is kept unchanged. The system continues on stale-but-stable parameters rather than installing a degraded model. Log the failure at WARNING level and schedule retry in 24h.

---

## Feature Detail: PiT Discipline Patterns

Three layers required; the V1 codebase implements all three and they must be ported:

**Layer 1: Data access (pit_read)**
All training data reads for HMM fitting, feature construction, and backtest replay must use pit_read(library, symbol, as_of_timestamp) which enforces an ArcticDB date_range filter. No direct DataFrame slicing against a stored history without a temporal cutoff.

**Layer 2: Feature shift enforcement (PiTValidator)**
The AST-based validator scans Python source for assignments that access price columns (close, high, low, open, returns, etc.) without a trailing .shift() call. This must be run as a pre-backtest check on all new strategy files (H1 scalp, momentum). The validator is already wired — the `validate_directory()` call needs to be added to the Makefile or CI step for v2 strategy files.

**Layer 3: IC ratio validation (validate_pit_compliance)**
After any new strategy backtest, run validate_pit_compliance(signal_df, price_df, threshold=1.5). If contemporaneous IC > 1.5 × forward IC, the signal has look-ahead bias and must not be promoted to the routing matrix. This is the final safety check before writing Sharpe numbers to pair_config.py.

**Critical v2 risk:** The HMM-GARCH model is trained on returns that will later be used in the live online filter. If any HMM training loop accidentally references future returns (e.g., iterating over the full DataFrame without a proper cutoff), the regime labels will leak. The RecalibrationService.recalibrate() call must receive only returns up to the recalibration trigger timestamp — it must not receive the full available history.

---

## Feature Detail: Paper Trade Validation Methodology

The 7-day paper trade gate is a binary go/no-go, not a performance evaluation. Its purpose is to verify that the execution pipeline works, not to prove the strategy is profitable in 7 days.

**What it measures:**
- Trade count on IC Markets demo account after 7 days ≥ 80% of expected backtest trade count for the same 7-day period
- Trade count ≤ 120% of expected (catches phantom duplicate signals from bridge bugs)
- Fill confirmations received for every dispatched OrderRequest (no silent drops)
- No disconnection events lasting > 60 seconds (heartbeat monitor)

**What it does not measure (explicitly):**
- P&L — 7 days is too short for statistical significance at this trade frequency
- Slippage vs backtest assumptions — important but separate metric, measured over 30+ days

**Expected trade count calculation:**
Use backtest_evaluate_all.py results for the same period by filtering the SQLite trade journal to the paper trade window dates. The tolerance is ±20%, meaning: if backtest shows 14 trades in 7 days for the enabled strategy set, accept 11–17 live trades.

**Failure modes that trigger a stop:**
1. Trade count < 80% expected: likely a ZMQ disconnection, close-bar detection bug, or regime stuck in CRISIS
2. Trade count > 120% expected: likely a deduplication failure, double-send bug in signal engine, or bar-close triggering multiple times
3. Any fill confirmation missing for a dispatched order: MQL5 EA execution path bug
4. EA CCircuitBreaker tripped within 7 days: position sizing calibration error

---

## MVP Recommendation

Prioritize in this order:

1. **ZMQ bridge** — nothing else is live without it; existing LinuxConsumer from V1 is the foundation; Windows publisher (MQL5 side) is the new work
2. **Close-bar detection + regime gate** — OnlineRegimeFilter porting from V1 with 20-bar hysteresis; this is the core of all dispatch logic
3. **StrategyRouter with routing matrix** — pair_config.py already has the matrix; router is the dispatch function: regime gate → allow_* flags → RAG score → direction + size_mult or None
4. **Position collision check** — opposite-direction block is table stakes before going live; must be in the router before first real trade
5. **PiT discipline enforcement** — validate all new backtest code before promoting Sharpe numbers to pair_config; AST scanner is already built
6. **7-day paper gate** — run before promoting to live capital; failure here blocks deployment

Defer until paper gate passes:
- HMM-GARCH recalibration timer (weekly recal) — V1 RecalibrationService works, but the weekly timer and drift alerting are operational overhead; configure recalibration to be manually triggered in v2.0 and automate in v2.1
- RAG scorer in dispatch path — +0.41 Sharpe is validated but ChromaDB adds latency; verify bridge latency budget allows it before wiring into the live path

---

## Phase-Specific Complexity Notes

| Feature | Complexity | Bottleneck |
|---------|------------|------------|
| ZMQ bridge (Python side) | Low — LinuxConsumer exists in V1 | MQL5 Windows publisher side; ZMQ for MQL5 requires specific DLL setup on Windows |
| ZMQ bridge (MQL5 EA side) | Medium | DLL compatibility, FillOrKill handling, reconnect logic in MQL5 |
| H1 scalp strategy backtest | Low — pattern identical to swing; pair_config already has results | 4yr data fetch if not already in arctic_data; warmup period for rolling indicators |
| Momentum strategy backtest | Low — same pattern; momentum.py features exist in V1 ml_price_momentum | Daily Z alignment check adds complexity vs pure H1 momentum |
| HMM-GARCH port from V1 | Low — all files exist; OnlineRegimeFilter, RecalibrationService, calibration YAML all portable | Integration with v2 signal engine's bar event loop; ensuring no import of V1-specific ArcticDB paths |
| PiT discipline manager port | Low — pit_manager.py and pit_validator.py are standalone | Running PiTValidator on V2 backtest scripts may surface violations to fix |
| StrategyRouter implementation | Medium — dispatch logic must be correct; position state registry requires thread-safe access | Position state sync between Python (registry) and MT5 (actual state); edge cases on fill failures |
| Live signal engine service | Medium | Process lifecycle management (startup, reconnect, graceful shutdown); close-bar detection accuracy across DST transitions |
| 7-day paper gate | Low — straightforward trade count comparison | Requires demo account live running for 7 days; timing constraint not a code complexity |

---

## Sources

- V1 codebase: `/home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V1/helix/src/` — RegimeOrchestrator, HMMGARCHRegimeDetector, OnlineRegimeFilter, RecalibrationService, LinuxConsumer, pit_manager, pit_validator, message_schemas, abstract
- V2 codebase: `/home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2/` — pair_config.py (evaluation matrix), backtest_hybrid.py (strategy independence pattern), CCircuitBreaker, CSignalManager
- Project context: `.planning/PROJECT.md` — constraints, key decisions, validated features
- Confidence: HIGH for all items — derived from actual implemented code and validated backtest results in this repository, not external sources
