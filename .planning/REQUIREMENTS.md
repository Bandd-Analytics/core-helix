# Requirements: MarketMind Helix

**Defined:** 2026-04-22
**Core Value:** A statistically validated daily Z-score mean-reversion signal that generates consistent alpha — extended to an adaptive multi-strategy router dispatching live to MT5

## v2.0 Requirements

Requirements for V3 Adaptive Strategy Dispatch System.

### Bridge

- [x] **BRDG-01**: Versioned msgpack schema contract file defines Tick, Bar, OrderRequest, Fill, Heartbeat types before any bridge code is written
- [x] **BRDG-02**: ZMQ bridge has heartbeat + auto-reconnect (built from scratch — V1 IPC module is a stub with no heartbeat)
- [ ] **BRDG-03**: mql-zmq DLL compatibility confirmed on IC Markets MT5 terminal (go/no-go spike before EA work begins)
- [x] **BRDG-04**: MT5 EA publishes completed bars per pair with timeframe tag; Python reacts on bar close (no polling)

### Backtest Validation

- [x] **BKTS-01**: backtest_hybrid.py uses next-bar-open entry for all strategy loops (not signal-bar close — fixes Sharpe inflation of 0.2–0.4)
- [x] **BKTS-02**: H1 scalp strategy backtested on full 4yr data across all active pairs → routing matrix entry in pair_config.py
- [x] **BKTS-03**: Momentum strategy backtested on full 4yr data across all active pairs → routing matrix entry in pair_config.py
- [x] **BKTS-04**: pit_validator.py wired as pass/fail gate — no new Sharpe number enters pair_config.py without PiT compliance

### Regime + PiT

- [x] **REGM-01**: HMM-GARCH classifier ported from V1 to V2/v3_intelligence/regime.py with offline fit + online update split
- [x] **REGM-02**: HMM state labels pinned by variance rank at fit time (prevents permutation when re-fitting on new dataset)
- [x] **REGM-03**: PiT manager ported from V1 to V2/v3_intelligence/pit.py with no future-bar read enforced
- [x] **REGM-04**: OnlineRegimeFilter is the only regime series source in backtest and live paths — Viterbi banned from both

### Router

- [ ] **ROUT-01**: StrategyRouter.route(pair, timestamp, market_data) → {strategy, direction, confidence, size_mult} or None, using regime gate → matrix check → RAG score
- [ ] **ROUT-02**: Router implements swing-first priority — daily swing fires whenever conditions met; intraday strategies only when no swing position open on that pair
- [ ] **ROUT-03**: Router rejects any strategy if an opposite-direction position is already open on the same pair
- [ ] **ROUT-04**: Router 4yr simulation: aggregate portfolio Sharpe ≥ max individual strategy Sharpe + 0.2

### Live Execution

- [ ] **LIVE-01**: LiveSignalEngine Python service subscribes to MT5 bars, detects close, calls router, publishes OrderRequest over ZMQ
- [ ] **LIVE-02**: MT5 EA reads OrderRequest from ZMQ PULL socket and executes via CCircuitBreaker (risk layer unchanged)
- [ ] **LIVE-03**: CCircuitBreaker equity baseline uses AccountInfoDouble(ACCOUNT_EQUITY) on OnInit — hard-coded 1000.0 removed
- [ ] **LIVE-04**: 7-day IC Markets demo paper trade: live trade count within ±20% of router backtest expectation = go/no-go gate

## Future Requirements

Deferred to v3.0+. Not in current roadmap.

### Strategy Expansion

- **EXPN-01**: Carry strategy ported from V1/helix/src/alpha/carry/ and validated on 4yr data
- **EXPN-02**: Cointegration pairs strategy ported from V1/helix/src/alpha/cointegration/ and validated on 4yr data
- **EXPN-03**: Walk-forward regime model retraining on rolling 2yr window (quarterly cadence)
- **EXPN-04**: pair_config.py monthly re-ranking based on rolling Sharpe

### Monitoring

- **MONI-01**: Live dashboard (V2/live/dashboard/) — trade log, regime state, router decisions
- **MONI-02**: Alerting on bridge heartbeat loss or circuit breaker trip

## Out of Scope

| Feature | Reason |
|---------|--------|
| H1 scalp + momentum as concurrent layers with daily swing | Validated to destroy daily alpha when run simultaneously on same capital — only dispatched separately via router |
| BEC partial close | Win rate (35.4%) too low; inverts P&L asymmetry — revisit if win rate reaches ≥40% |
| Mobile app / web dashboard | Not needed for MT5-based live trading |
| Multi-account / portfolio management | Out of scope for single $1,000 account target |
| OAuth / authentication layer | Not applicable — local system |
| Polygon or Dukascopy feed backup | MT5 terminal is the sole live feed source for v2.0 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BRDG-01 | Phase 6 | Complete |
| BRDG-02 | Phase 6 | Complete |
| BRDG-03 | Phase 6 | Pending |
| BRDG-04 | Phase 6 | Complete |
| BKTS-01 | Phase 7 | Complete |
| BKTS-02 | Phase 7 | Complete |
| BKTS-03 | Phase 7 | Complete |
| BKTS-04 | Phase 7 | Complete |
| REGM-01 | Phase 8 | Complete |
| REGM-02 | Phase 8 | Complete |
| REGM-03 | Phase 8 | Complete |
| REGM-04 | Phase 8 | Complete |
| ROUT-01 | Phase 9 | Pending |
| ROUT-02 | Phase 9 | Pending |
| ROUT-03 | Phase 9 | Pending |
| ROUT-04 | Phase 9 | Pending |
| LIVE-01 | Phase 10 | Pending |
| LIVE-02 | Phase 10 | Pending |
| LIVE-03 | Phase 10 | Pending |
| LIVE-04 | Phase 10 | Pending |

**Coverage:**
- v2.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 — Traceability populated after roadmap creation*
