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

MarketMind is a multi-pair, multi-timeframe algorithmic trading system for MetaTrader 5 targeting small accounts ($1,000). It trades **8 forex pairs** — USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP, GBPNZD, EURUSD, AUDNZD — across **three timeframes** (M15 scalp, H1 scalp/momentum, Daily swing). Each pair × strategy × timeframe combination is independently validated; the live router dispatches per-bar to whichever combination is positive-Sharpe under the current regime and session window. The Python signal engine is fully validated via vectorbt.pro backtesting; the MT5 EA exists but is not yet connected to live execution.

The v2.0 milestone goal decomposes into **five axes**: identify *which pairs* to trade, *at what time/session*, *under what regime conditions*, *using which strategies*, while *mitigating risk* and staying consistent. Every active phase advances one or more of these axes — Phase 7 (pair × strategy), Phase 8 (regime), Phase 8.5 (time), Phase 9 (router that combines them all), Phase 10 (live).

## Core Value

A statistically validated multi-strategy alpha portfolio: daily Z-score swing (Sharpe 2.08, +42.84% over 730 days on 5 pairs), H1 scalp/momentum on validated pairs (Phase 7 4yr matrix), and M15 scalp on 7 of 8 pairs (Sharpe range 0.93–3.65) — adaptively dispatched per-pair-per-bar based on regime, session, and 4yr performance evidence, and ready to move from Python backtest to live MT5 execution.

## Requirements

### Validated

- ✓ Daily Z-score mean-reversion signal engine (20-period MA, |Z| > 2.0 threshold) — v1.0
- ✓ ADX change-point filter (blocks entries during trending regimes) — v1.0
- ✓ RAG signal filter (ChromaDB semantic memory, confidence scoring, +0.41 Sharpe lift) — v1.0
- ✓ Hurst regime filter (H < 0.45 → mean-reverting; H > 0.55 → block entry) — v1.0
- ✓ Signal filters module (rolling_hurst, rolling_ols_zscore, sigdet_zscore) — v1.0
- ✓ Multi-pair × multi-timeframe tiered configuration: 8 pairs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP T1–T2; GBPNZD/EURUSD/AUDNZD T2) × {M15 scalp, H1 scalp, H1 momentum, Daily swing}, per-strategy enable flags driven by 4yr/730d/60d Sharpe matrix in [pair_config.py](V2/v3_intelligence/pair_config.py) — v1.0 baseline, refined in Phase 7 4yr corrections
- ✓ Per-strategy ATR-based exits (4× target, 1.5× stop, 120-bar timeout) — v1.0
- ✓ Python backtesting framework with vectorbt.pro — v1.0
- ✓ SQLite trade journal with full trade context logging — v1.0
- ✓ MT5 EA skeleton (compiles, includes all MQL5 managers) — v1.0
- ✓ Walk-forward validated backtest (539 trades, 35.4% win, Sharpe 1.67 base / 2.08 with RAG) — v1.0

### Active

<!-- v2.0 scope: V3 Adaptive Strategy Dispatch System -->

- [x] ZMQ bridge ported from V1 — Python↔MT5 tick/order round-trip, heartbeat, <10ms local latency (Phase 6, 2026-04-24)
- [x] H1 scalp strategy backtested over 4yr data across all active pairs — produces routing matrix entry (Phase 7, 2026-04-25)
- [x] Momentum strategy backtested over 4yr data across all active pairs — produces routing matrix entry (Phase 7, 2026-04-25)
- [x] HMM-GARCH regime classifier ported from V1 with PiT discipline — zero future-bar leakage (Phase 8, 2026-04-25)
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
- **Backtest windows**: 4yr H1 (7 of 8 pairs — GBPNZD still on 730d, gap to close before Phase 8.5), 60d M15 (all 8 pairs — short window, DoY/DoM analysis statistically thin), 4yr Daily (all 8 pairs)
- **Data pipeline**: Custom scripts for fetching OHLCV (fetch_data.py, download_history.py, download_intraday_data.py); persistent cache strategy still ad-hoc (CSV-on-disk, no incremental delta fetch — gap flagged for Phase 8.5 prereq)
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
| 8-pair × multi-timeframe matrix (M15 + H1 + Daily) | Per-strategy independent enable flags in pair_config.py — swing on 5 pairs, M15 scalp on 7, H1 scalp/momentum on validated subsets; supersedes the prior "5-pair swing-only" framing | ✓ Good |
| ZMQ bridge for Python↔MT5 IPC | Sub-10ms latency, ported from V1, tested architecture. File-polling rejected (1s latency, lock risk); named pipes rejected (Windows-only, no Linux dev) | — Pending |
| Adaptive router over single-strategy | Router selects best per-pair-per-bar strategy — H1 scalp/momentum valid as isolated dispatched strategies, not concurrent layers | — Pending |
| 4yr validation window for routing matrix | Replaces 730-day numbers in pair_config.py with statistically stronger evidence | — Pending |

## Memory Architecture (Phase 8.4 D-20)

The project uses two complementary persistent memory layers, plus one separate RAG store for trade history:

| Layer | Role | Backing Store | Updated By |
|-------|------|---------------|------------|
| **claude-mem** (canonical conversation memory) | Cross-session conversation continuity, recent context, what was done last session | bun worker-service.cjs daemon | Auto — every Claude session |
| **mempalace** (structured-knowledge palace) | Project taxonomy: rooms × keywords × drawers; retrievable structured facts | `~/.mempalace/palace/` (user-global; per-project wing) | `mempalace init` once + `mempalace mine .` periodically |

The in-repo [`mempalace.yaml`](../mempalace.yaml) documents the room/keyword shape — it is a README-shaped descriptor for the palace, NOT a load-bearing config (the actual palace state lives in `~/.mempalace/palace/`). **DO NOT re-run `mempalace init` after editing `mempalace.yaml`** (RESEARCH Pitfall 7 — init overwrites the YAML).

Auto-memory entries also exist at `~/.claude/projects/-home-user-Desktop-BA-ORG-Bandd-Analytics-helix/memory/` (orthogonal to both — Claude internal session state).

**RAG learning memory** (separate concern from the two layers above): `V2/data/chroma_rag/trade_memory` collection — populated by `on_trade_close()` (D-10) and the one-shot [`scripts/backfill_rag.py`](../V2/scripts/backfill_rag.py) (D-14). Used by `RAGSignalFilter.score_signal()` for entry confidence in live + backtest paths.

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
*Last updated: 2026-04-25 after Phase 8 completion — HMM-GARCH regime classifier and PitClock manager ported with REGM-01/02/03/04 verified; Viterbi banished; 5 detector JSONs landed; D-16 parity GREEN at rtol=1e-6.*
*2026-04-25 (later): scope drift correction — restored 8-pair × multi-timeframe (M15/H1/Daily) framing as the project default; prior "5 pairs" wording was a stale v1.0-swing-era artifact contradicted by [pair_config.py](V2/v3_intelligence/pair_config.py).*
