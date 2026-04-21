# MarketMind — Helix

## Current Milestone: v2.0 — V3 Adaptive Strategy Dispatch System

**Goal:** Wire Python signal intelligence into live MT5 execution via a ZMQ bridge and an adaptive strategy router that dispatches per-pair per-bar to the best validated strategy based on regime + 4yr performance matrix.

**Target features:**
- ZMQ bridge (Python↔MT5, <10ms round-trip, heartbeat)
- H1 scalp + Momentum strategies validated on 4yr data → routing matrix
- HMM-GARCH regime classifier + PiT discipline (ported from V1)
- StrategyRouter (regime gate + 4yr matrix + RAG confidence → best pick)
- Live signal engine service + MT5 EA OrderRequest execution
- 7-day IC Markets demo paper trade as live gate

## What This Is

MarketMind is a multi-pair algorithmic trading system for MetaTrader 5 targeting small accounts ($1,000). It uses a daily Z-score mean-reversion signal, filtered by a Hurst regime detector and a RAG-based semantic confidence scorer, to trade 5 forex pairs (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP). The Python signal engine is fully validated via vectorbt.pro backtesting; the MT5 EA exists but is not yet connected to live execution.

## Core Value

A statistically validated daily Z-score mean-reversion signal that generates consistent alpha (Sharpe 2.08, +42.84% over 730 days) across 5 forex pairs — ready to move from Python backtest to live MT5 execution.

## Requirements

### Validated

- ✓ Daily Z-score mean-reversion signal engine (20-period MA, |Z| > 2.0 threshold) — v1.0
- ✓ ADX change-point filter (blocks entries during trending regimes) — v1.0
- ✓ RAG signal filter (ChromaDB semantic memory, confidence scoring, +0.41 Sharpe lift) — v1.0
- ✓ Hurst regime filter (H < 0.45 → mean-reverting; H > 0.55 → block entry) — v1.0
- ✓ Signal filters module (rolling_hurst, rolling_ols_zscore, sigdet_zscore) — v1.0
- ✓ Multi-pair tiered configuration (USDJPY T1, GBPJPY T1, GBPAUD T1, GBPUSD T1, EURGBP T2) — v1.0
- ✓ Per-strategy ATR-based exits (4× target, 1.5× stop, 120-bar timeout) — v1.0
- ✓ Python backtesting framework with vectorbt.pro — v1.0
- ✓ SQLite trade journal with full trade context logging — v1.0
- ✓ MT5 EA skeleton (compiles, includes all MQL5 managers) — v1.0
- ✓ Walk-forward validated backtest (539 trades, 35.4% win, Sharpe 1.67 base / 2.08 with RAG) — v1.0

### Active

<!-- v2.0 scope: V3 Adaptive Strategy Dispatch System -->

- [ ] ZMQ bridge ported from V1 — Python↔MT5 tick/order round-trip, heartbeat, <10ms local latency
- [ ] H1 scalp strategy backtested over 4yr data across all active pairs — produces routing matrix entry
- [ ] Momentum strategy backtested over 4yr data across all active pairs — produces routing matrix entry
- [ ] HMM-GARCH regime classifier ported from V1 with PiT discipline — zero future-bar leakage
- [ ] StrategyRouter dispatches per-pair per-bar to best strategy based on regime + 4yr matrix + RAG
- [ ] Live signal engine service (Python) consumes MT5 ticks, calls router, publishes OrderRequest
- [ ] MT5 EA reads OrderRequest from ZMQ, validates via CCircuitBreaker, executes
- [ ] 7-day IC Markets demo paper trade matches router backtest trade count within 20%

### Out of Scope

- BEC partial close (50% exit at 2× ATR) — win rate must reach ≥40% first; mechanism is sound but inverts asymmetry at current 35% win rate
- H1 scalp and intraday momentum as *combined concurrent layers* — confirmed to destroy daily alpha when run simultaneously on same capital; now in scope as *separately dispatched strategies* in the adaptive router (v2.0)
- M15 scalp as combined strategy — works in isolation (Sharpe 3.65 for GBPNZD) but cannot run concurrently with daily swing on same capital base without conflict
- Mobile app / web dashboard — not needed for MT5-based live trading
- Multi-account / portfolio management — out of scope for single $1,000 account target

## Context

- **Tech stack**: Python 3.x, vectorbt.pro 2026.3.1, ChromaDB (local), NumPy/Pandas, MQL5 (MetaTrader 5)
- **Target broker**: IC Markets Raw Spread Account (0.02–0.82 pip spreads, $3.50/lot/side commission, ~35ms execution)
- **Backtest window**: 730-day H1 data per pair (2 years), 2024–2026
- **Data pipeline**: Custom scripts for fetching OHLCV (fetch_data.py, download_history.py, download_intraday_data.py)
- **The execution gap**: Python signal engine produces validated entries, MT5 EA exists but no bridge between them — this is the next critical milestone

## Constraints

- **Capital**: $1,000 account — position sizing must prevent any single trade exceeding defined drawdown limits (<15% max DD)
- **Broker**: IC Markets MT5 Raw Spread — EA must use FillOrKill/IOC and respect minimum lot sizes
- **Win rate**: Daily swing holds at 35.4% — partial close features require ≥40% to be viable
- **Execution**: MT5 does not natively call Python; bridge requires ZeroMQ, REST API, or file-polling mechanism

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Daily-only swing as core signal | H1 scalp/momentum tested and confirmed to destroy alpha; daily Z-score is the only edge | ✓ Good |
| RAG semantic filter via ChromaDB | No API key required; local embedding; +0.41 Sharpe lift proven in backtest | ✓ Good |
| Hurst regime filter to gate entries | Prevents entries in trending regimes where mean-reversion fails | — Pending validation in live |
| 4× ATR target, 1.5× ATR stop | 2.67:1 R/R offsets 35% win rate for positive expectancy | ✓ Good |
| Shelve BEC partial close | Win rate (35%) too low; partial close inverts P&L asymmetry | ✓ Good |
| 5-pair portfolio, 3 disabled | EURUSD, AUDNZD, GBPJPY negative swing Sharpe — disabled for swing | ✓ Good |
| ZMQ bridge for Python↔MT5 IPC | Sub-10ms latency, ported from V1, tested architecture. File-polling rejected (1s latency, lock risk); named pipes rejected (Windows-only, no Linux dev) | — Pending |
| Adaptive router over single-strategy | Router selects best per-pair-per-bar strategy — H1 scalp/momentum valid as isolated dispatched strategies, not concurrent layers | — Pending |
| 4yr validation window for routing matrix | Replaces 730-day numbers in pair_config.py with statistically stronger evidence | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-21 after milestone v2.0 start — V3 Adaptive Strategy Dispatch System*
