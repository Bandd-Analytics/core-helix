# Phase 0 — Scope Lock: CONTEXT

**Phase:** V3 Intelligence Layer — Adaptive Strategy Dispatch System
**Status:** Scope Locked
**Date:** 2026-04-21
**Author:** Bandd Analytics (bandanalytics.ke@gmail.com)

---

## Phase Goal

Lock the architectural decisions needed before Phase 1 (codebase mapping) and Phase 2+ (implementation) can proceed. Produce a decisions artifact that downstream researcher and planner agents can consume without re-asking the user.

---

## Locked Decisions

### D-01 — IPC Method: ZMQ Primary + signals.json Failover

**Decision:** ZMQ bridge is the primary communication channel between Linux router and Windows MT5 EA. signals.json file bridge serves as failover if ZMQ becomes unavailable.

**Rationale:**
- ZMQ is battle-tested in V1 (helix/src/execution/bridge/): zero-copy, heartbeat-aware, typed MessagePack payloads
- Sub-50ms round-trip between Linux router and Windows MT5 host
- signals.json fallback provides robustness on ZMQ failure (network blip, bridge process crash)
- File bridge already exists as current V2 interim solution — retains it as safety

**Components (ported from V1):**
- `V1/helix/src/execution/bridge/windows_publisher.py` → adapt for V2 router publishing
- `V1/helix/src/execution/bridge/linux_consumer.py` → adapt for EA consumption pattern (mirror on MQL5 side)
- `V1/helix/src/execution/bridge/message_schemas.py` → reuse verbatim (Tick, Bar, OrderRequest, OrderResult)
- Ports: 5556 (ticks), 5557 (bars), 5558 (orders out), 5559 (results in)

**Failover trigger:** ZMQ heartbeat missing >30s → router switches publishing to signals.json.

---

### D-02 — Strategy Scope: Core 4 + Carry (5 Strategies)

**Decision:** Router dispatches 5 strategies across 8 pairs:

| Strategy | Timeframe | Status | Source |
|----------|-----------|--------|--------|
| Swing (mean-reversion) | 4H/Daily | Validated (Sharpe 1.67, +36.37%, 539 trades, 4yr) | V2 existing |
| H1 Scalp | 1H | Needs 4yr re-validation | V2 existing (730-day Sharpe only) |
| Momentum | 1H | Needs 4yr re-validation | V2 existing (730-day Sharpe only) |
| M15 Intraday | 15M | Validated (Sharpe 0.13 on 4yr) — live=False pending re-tune | V2 existing |
| Carry | Overnight (24H) | To be ported | V1/helix/src/alpha/carry/forex_carry.py |

**Rationale:**
- Carry adds uncorrelated overnight edge with minimal effort (~1 day backtest)
- V1 code is mature — minimal porting work
- Cointegration deferred to Phase 3+ (higher effort, lower marginal alpha)
- Scope keeps router complexity bounded for initial production release

**Deferred (for future phases):**
- Cointegration / stat-arb pairs (Johansen test exists in V1 — revisit after core 4 validation)
- HMM/GARCH regime filter (V1 exists — Phase 3+ enhancement)

---

### D-03 — Router Architecture: Tiered Defense-in-Depth

**Decision:** Router operates as three layers with graceful degradation plus cross-cutting alert layer.

**Layer Architecture:**

```
Tier 1 — Primary: Python Live Service
├── Subscribes to ZMQ tick/bar streams (5556, 5557)
├── Runs full router: 5 strategies, Hurst/OLS/SIGDET filters, RAG confidence scoring
├── Stateful: position tracking, pair regimes, correlation matrix, carry basket
├── Publishes OrderRequest via ZMQ (5558)
└── Sub-tick latency, streaming

Tier 2 — Fallback: Python Batch
├── Activates on ZMQ heartbeat timeout (>30s)
├── Runs on M15 bar close (stateless, polling mode)
├── Writes signals.json; EA polls file
├── Shares router codebase with Tier 1 (toggle: streaming vs batch mode)
└── Less intelligent but aware of all 5 strategies

Tier 3 — Safety Net: MQL5 Embedded
├── Activates on signals.json stale >10min OR Python process dead
├── Hardcoded pair→strategy mapping from static CSV (exported from pair_config.py)
├── No Hurst/OLS/SIGDET — minimal filters only (SR levels, ATR guards)
├── Existing CircuitBreaker remains active in all tiers
└── Deliberately dumb: just prevents orphaned positions, trades baseline strategy per pair
```

**Alert / Observability Layer (cross-cutting):**
- CLogger severity levels: INFO / WARN / CRITICAL
- Alert() + Print() fires on any tier transition
- Heartbeat timeouts, stale signals, router disagreements all logged
- Optional: Telegram webhook for CRITICAL events (tier downgrade, kill switch trigger)

**Why tiered:**
- Never lose execution capability if any single layer fails
- Graceful degradation: smart → less smart → safe (never smart → dead)
- Alert fatigue managed — only tier transitions alert, not every heartbeat
- Testable: kill Python mid-backtest to verify Tier 2/3 activation

**V1 constraint honored:** Alpha engine runs on Linux; MQL5 stays thin (Tier 3 is explicitly simple, not a second brain).

---

### D-04 — Validation Bar: Medium (Targeted OOS)

**Decision:** Strategies face validation rigor appropriate to their current trust level.

**Acceptance Gate Spec:**

```
Already-Validated Strategies (Swing, M15):
├── In-sample: 4yr (2022-2026) Sharpe > 1.0, Win% > 45%, Max DD < 25%
└── Paper forward: 3 months live ticks
    ├── Live Sharpe within 40% of backtest Sharpe
    └── Slippage < 2x backtest assumption

New Strategies (H1 Scalp, Momentum, Carry):
├── In-sample: 2022-2024 (2yr train) — parameter tuning here
├── Out-of-sample: 2025-2026 (2yr held out)
│   ├── OOS Sharpe > 0.8
│   └── Win% within 15% of in-sample
└── Paper forward: 3 months live ticks (same criteria as above)

Kill Switch (all live strategies, continuous):
└── 30-day rolling Sharpe < 0.3 → auto-disable strategy-pair, alert user
```

**Rationale:**
- Paper forward test is the real OOS — live ticks catch execution/slippage that historical data cannot
- Simple 5-parameter strategies are less prone to overfitting than ML models; targeted OOS suffices
- Targeted rigor avoids redundancy: don't re-OOS strategies already proven on 4yr in-sample
- Monte Carlo on trade-order shuffling rejected as theatrical rigor — doesn't catch real failure modes

**Compute cost:** ~1-2 days wall time for full validation sweep (acceptable).

**What this prevents:** M15's 60-day→4yr collapse repeating on H1 Scalp / Momentum / Carry.

**What this does NOT catch:** Regime shifts to unseen conditions (no validation catches this — the kill switch + paper monitoring does).

---

### D-05 — Live Feed Source: MT5 Live + Dukascopy Historical

**Decision:** MT5 Python API is the authoritative live feed; Dukascopy bi5 files are the historical backtest source.

**Live feed:**
```
MT5 Windows host (IC Markets Raw account, 1:100 leverage)
  → MetaTrader5 Python API on Windows
  → ZMQ publisher (Tier 1) or signals.json writer (Tier 2)
  → Linux router
```

**Historical feed:**
```
Dukascopy bi5 cache (4yr, 8 pairs, M1 ticks)
  → V1/helix/src/data/dukascopy_fetcher.py (LZMA decoder, battle-tested)
  → Parquet conversion
  → V2 backtest engine
```

**Rationale:**
- MT5 feed = execution broker's feed → zero calibration drift between signal and fill
- Dukascopy = institutional-grade historical tick data, V1 fetcher already proven
- Free REST APIs (Polygon, Alpha Vantage) rejected: different tick definitions cause noise, severe rate limits, adds code paths without real safety

**Data integrity monitoring:**
- ZMQ heartbeat (5s interval) on live feed
- Tick timestamp monotonicity checks → alert on reordering
- Daily spread summary vs 30-day median → alert on anomaly

**Cost:** $0 (both free).

**Effort:** ~0.5 day to port V1 Dukascopy fetcher into V2 backtest loop.

---

## Code Context (Reusable Assets Inventory)

### V1 Components Slated for Port

| Component | V1 Path | V2 Destination | Priority | Effort |
|-----------|---------|----------------|----------|--------|
| ZMQ message schemas | helix/src/execution/bridge/message_schemas.py | V2/v3_intelligence/bridge/ | P0 | 0.5d |
| ZMQ Windows publisher | helix/src/execution/bridge/windows_publisher.py | V2/v3_intelligence/bridge/ | P0 | 1d |
| ZMQ Linux consumer | helix/src/execution/bridge/linux_consumer.py | V2/v3_intelligence/bridge/ | P0 | 0.5d |
| Dukascopy fetcher | helix/src/data/dukascopy_fetcher.py | V2/data/ | P1 | 0.5d |
| Carry signal logic | helix/src/alpha/carry/forex_carry.py | V2/backtest/strategies/ | P1 | 1d |
| PiT manager | helix/src/data/pit_manager.py | V2/backtest/ | P2 | 0.5d |

### V2 Existing Assets

| Component | Path | Role in V3 |
|-----------|------|------------|
| Signal filters (numpy) | V2/backtest/signal_filters.py | Hurst, OLS Z-score, SIGDET — router uses for gating |
| Hybrid backtest engine | V2/backtest/backtest_hybrid.py | Extend to run all 5 strategies |
| Pair config | V2/v3_intelligence/pair_config.py | Router source of truth for pair↔strategy mapping |
| RAG signal filter | V2/v3_intelligence/rag_signal_filter.py | Tier 1 confidence scoring layer |
| Multi-pair EA | V2/ea/MultiPairEA.mq5 | Host for Tier 3 safety net; consumes ZMQ / signals.json |
| EA risk modules | V2/ea/include/ (15 modular .mqh) | CircuitBreaker, CorrelationMonitor, PositionManager — stay active |

### Deferred / Future Phase Assets

| Component | V1 Path | Reason Deferred |
|-----------|---------|-----------------|
| HMM/GARCH regime filter | helix/src/alpha/regime/hmm_garch.py | Phase 3+ enhancement after core 5 validated |
| Online regime filter | helix/src/alpha/regime/online_filter.py | Paired with HMM/GARCH port |
| Cointegration (Johansen) | helix/src/alpha/cointegration/johansen.py | Deferred per D-02 scope decision |

---

## Scope Guardrails (Non-Negotiable)

- **No new strategies beyond Core 4 + Carry** this phase. Cointegration is Phase 3+.
- **Alpha engine on Linux only** — MQL5 Tier 3 stays minimal (hardcoded pair→strategy, no indicators).
- **No free REST API integration** — MT5 + Dukascopy are sufficient.
- **No OOS rigor beyond targeted spec** — paper forward test is the real OOS.
- **Strategy-pair combos enter live only after full acceptance gate passed.**

## Deferred Ideas (for Future Phases)

- Cointegration stat-arb pairs (captured; revisit after Phase 3)
- HMM/GARCH regime classifier (captured; Phase 3+ enhancement)
- Telegram webhook for CRITICAL alerts (captured; nice-to-have)
- Monte Carlo stress testing (rejected as theatrical for this strategy complexity)
- Polygon/Alpha Vantage redundancy feed (rejected as cargo-cult)

---

## Open Questions for Downstream Agents

**For Phase 1 Researcher (codebase mapping):**
- Confirm V1 ZMQ bridge still runs on current Python version (3.11+)
- Inventory all V2 backtest entry points and their strategy coverage gaps
- Map MQL5 EA's current strategy dispatch logic — how much refactoring for Tier 3?

**For Phase 2 Planner (implementation):**
- Sequence decision: port ZMQ first, or re-validate H1/Momentum/Carry first?
  - Recommendation: parallel tracks — ZMQ infra is independent of strategy validation
- Paper forward test infrastructure: use MT5 demo account or IC Markets demo?

---

## Decision Summary Table

| ID | Area | Decision | Status |
|----|------|----------|--------|
| D-01 | IPC Method | ZMQ primary + signals.json failover | LOCKED |
| D-02 | Strategy Scope | Core 4 + Carry (5 strategies) | LOCKED |
| D-03 | Router Architecture | Tiered (Python live / Python batch / MQL5 safety) + Alerts | LOCKED |
| D-04 | Validation Bar | Medium — targeted OOS for unvalidated strategies | LOCKED |
| D-05 | Live Feed | MT5 live + Dukascopy historical | LOCKED |

---

## Next Steps

1. **Phase 1 — Map Codebase** (`/gsd:map-codebase`)
   - Inventory V1 portable components in detail
   - Confirm V2 integration points
   - Identify blockers in current V2 backtest engine

2. **Phase 2 — Roadmap Creation** (`/gsd:new-milestone` or planner)
   - Break V3 Intelligence Layer into 4-5 implementation phases
   - Sequence: Infra (ZMQ) → Validation (4yr re-test) → Router (Tier 1-2-3) → Go-live (paper forward)

3. **Phase 2+ — Implementation Cycles** (`/gsd:plan-phase` → `/gsd:execute-phase`)
   - One phase per major component (ZMQ port, strategy validation, router build, EA integration)

---

*End of Phase 0 CONTEXT. Downstream agents: treat decisions D-01 through D-05 as locked constraints. Redirect any scope-expansion questions back to the user, not to re-litigation of these decisions.*
