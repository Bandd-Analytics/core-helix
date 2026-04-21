# Architecture

**Analysis Date:** 2026-04-21

## Pattern Overview

**Overall:** Hybrid Python-MQL5 tiered trading system with graceful degradation. Current state (V2) is dual-strategy independent backtester with modular signal filtering. Planned V3 adds a three-tier router: Python live service (Tier 1) → Python batch fallback (Tier 2) → MQL5 safety net (Tier 3), with ZMQ/signals.json IPC.

**Key Characteristics:**
- **Language split:** Alpha engine on Python (Linux), execution EA on MQL5 (Windows MT5)
- **Strategy independence:** Each pair can run multiple strategies simultaneously with no shared position state
- **Stateless → Stateful progression:** V2 backtester is stateless; V3 router maintains pair regimes, correlation matrix, carry basket
- **Multi-timeframe signals:** Daily Z-scores gate H1/M15 entries; session filters apply (London/NY only for certain strategies)
- **Pure-numpy indicators:** All signal computation uses numpy (Hurst, OLS Z-score, SIGDET) — no external TA libraries
- **Semantic confidence scoring:** RAG layer (ChromaDB) retrieves historical trade contexts to assign confidence/size modifiers to new signals

---

## Layers

**Python Backtest Engine (Current V2):**
- Purpose: Offline strategy validation, parameter optimization, baseline performance metrics
- Location: `backtest/backtest_hybrid.py` (entry point), `backtest/backtest_all_timeframes.py`, `backtest/backtest_evaluate_all.py`
- Contains: Multi-timeframe data loading, signal generation, position tracking, trade logging
- Depends on: Historical CSV data (`data/`), signal filters (`backtest/signal_filters.py`), pair config (`v3_intelligence/pair_config.py`)
- Used by: Validation workflows, performance analysis, parameter tuning

**Signal Filters Layer:**
- Purpose: Compute Z-scores, Hurst exponent, volatility percentiles, ADX changepoints
- Location: `backtest/signal_filters.py`
- Contains: `rolling_hurst()`, `rolling_ols_zscore()`, `sigdet_zscore()`, volatility percentile, ADX/changepoint
- Depends on: pandas, numpy only
- Used by: Backtest engine for entry/exit decisions; planned for Tier 1 router

**Pair Configuration Layer:**
- Purpose: Central source of truth for per-symbol strategy mapping, sizing, thresholds
- Location: `v3_intelligence/pair_config.py`
- Contains: Dataclass `PairConfig` with strategy flags, Z-score thresholds, ATR multipliers, size multipliers per strategy
- Depends on: None (pure dataclass)
- Used by: Backtest engine, Tier 3 safety net (exports static CSV), planned V3 router (reads at startup)

**RAG Signal Filter (V3 Preparation):**
- Purpose: Semantic retrieval of similar historical trades to score confidence in new signals
- Location: `v3_intelligence/rag_signal_filter.py`
- Contains: ChromaDB interface, trade embedding, similarity search, confidence + size modifier scoring
- Depends on: chromadb (optional), trade logs
- Used by: Backtest engine (optional), planned Tier 1 router (primary decision layer)

**Trade Logging / Decision Log:**
- Purpose: Persistent SQLite journal of all trades + market context; decision audit trail
- Location: `v3_intelligence/trade_logger.py`
- Contains: `TradeLogger` class managing two tables: `trades` (every executed trade) and `decision_log` (parameter changes)
- Depends on: sqlite3, pathlib
- Used by: Backtest engine (logs all trades), RAG filter (reads for embedding), post-analysis

**MQL5 EA Architecture (Current V2):**
- Purpose: Live execution, real-time position management, risk gates on MT5 platform
- Location: `ea/MultiPairEA.mq5` (orchestrator), `ea/include/` (15 modular .mqh classes)
- Contains: Risk manager (circuit breaker, drawdown limits), position manager, signal generators (mean-rev, trend, hybrid), logging
- Depends on: MT5 Standard Library (Trade, Arrays), custom signal modules
- Used by: MT5 terminal (OnInit/OnTick entry points)

---

## Data Flow

**Current V2 Backtest Loop:**

```
1. Data Loading:
   - fetch_data.py → Dukascopy bi5 tick files (LZMA) → resampled to M15/H1/Daily CSV
   - Stored in data/ with naming convention: {SYM}_{TIMEFRAME}.csv or {SYM}_{TIMEFRAME}_{DAYS}d.csv
   - Examples: USDJPY_H1_730d.csv (2yr H1), GBPUSD_M15.csv (full history M15)

2. Entry Point (backtest_hybrid.py main):
   - Load pair config (pair_config.py)
   - For each symbol, load DAILY/H1/M15 CSV files
   - Initialize RAG filter (optional, if ChromaDB available)
   - Initialize trade logger

3. Signal Generation (per strategy):
   SWING (daily mean-reversion):
     - Daily Z-score on 20-bar rolling window
     - Hurst filter (optional, H > 0.55 blocks entry)
     - Changepoint detection (ADX regime)
     - Signal fires: |daily_Z| > 2.0, aligned session window
     - Exit: 4× H1_ATR target, 1.5× H1_ATR stop, 120-bar timeout

   M15 SCALP (5-hour mean-reversion):
     - M15 Z-score on 20-bar window, London/NY session only
     - Must align with or be neutral to daily Z direction
     - Signal fires: |M15_Z| > 2.0
     - Exit: 2.5× M15_ATR target, 1.5× M15_ATR stop, 12-bar timeout (3 hrs)

   H1 SCALP (London/NY session):
     - H1 Z-score on 20-bar window, session filter (7-11 UTC or 13-17 UTC)
     - Exit: 2× H1_ATR target, 0.75× H1_ATR stop, 4-bar timeout (~4 hrs)

   MOMENTUM (H1 trend):
     - H1 Z-score with daily Z alignment gate
     - Lower threshold (1.5 instead of 2.0) for faster entries
     - Exit: 1× H1_ATR target, 0.5× H1_ATR stop, 2-bar timeout

4. Position Tracking (in-memory per strategy):
   - Entry: store entry_price, entry_bar, entry_date, ATR, daily_Z, session context
   - On each bar: check exit conditions (target/stop/timeout)
   - Record: trade dict with symbol, strategy, entry/exit date/price, PnL%, bars_held, session, exit_reason
   - Log to TradeLogger.log_trade() → SQLite trades table

5. Reporting:
   - Aggregate by strategy + symbol
   - Compute metrics: Sharpe, win%, max DD, profit factor
   - Write to backtest/results/{report_name}.csv
   - Optional: write formatted report to backtest/analysis/{date}_{strategy}_{symbol}.txt
```

**Planned V3 Live Data Flow (Decision D-01, D-03):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ MT5 Live Feed (IC Markets Raw 1:100 leverage)                       │
│ - Tick stream (bid/ask)                                             │
│ - Bar close events (M15, H1, Daily)                                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ├─→ (Tier 1: Python Live Service)
                         │   ├─ ZMQ subscriber (5556 ticks, 5557 bars)
                         │   ├─ Stateful position tracker, pair regimes, correlation matrix
                         │   ├─ Router: run all 5 strategies, apply Hurst/OLS/SIGDET/RAG filters
                         │   ├─ Compute OrderRequest (symbol, direction, size, SL, TP)
                         │   └─ ZMQ publisher (5558 OrderRequest, 5559 OrderResult)
                         │
                         ├─→ (Tier 2: Python Batch - on ZMQ heartbeat timeout >30s)
                         │   ├─ Stateless polling mode (runs on M15 bar close)
                         │   ├─ Writes signals.json (shared codebase with Tier 1)
                         │   └─ EA polls file (≤10s stale tolerance)
                         │
                         └─→ (Tier 3: MQL5 Safety Net - signals.json stale >10min)
                             ├─ Hardcoded pair→strategy mapping (static CSV export)
                             ├─ Minimal filters: SR levels, ATR guards only
                             ├─ CircuitBreaker, CorrelationMonitor stay active
                             └─ Deliberately dumb: just prevents orphaned positions

┌────────────────────────────────────────────────────────────────────┐
│ Alert / Observability Layer (cross-cutting)                         │
│ - CLogger severity: INFO / WARN / CRITICAL                          │
│ - Tier transitions logged                                           │
│ - Heartbeat timeouts, stale signals, disagreements all logged       │
│ - Optional: Telegram webhook for CRITICAL events                    │
└────────────────────────────────────────────────────────────────────┘
```

**State Management:**

- **Backtest Engine:** State is local to each `HybridMultiTimeframeBacktest` instance; cleared on each run
- **V3 Router Tier 1 (planned):** Persists across bars — position tracking, pair correlation matrix, carry basket values, regime classifier state
- **V3 Router Tier 2 (planned):** Stateless; re-initializes on each M15 bar close
- **MQL5 EA:** Persists across ticks — open positions in MT5 trade pool, circuit breaker state, correlation monitor state

---

## Key Abstractions

**PairConfig (Configuration):**
- Purpose: Per-symbol strategy routing and parameterization
- Location: `v3_intelligence/pair_config.py`
- Pattern: Dataclass with strategy flags (`allow_swing`, `allow_m15_scalp`, etc.), Z-score thresholds, ATR multipliers, size multipliers
- Example usage: `cfg = get_pair_config("USDJPY")` → fetch strategy enabled/disabled flags and sizing
- Extensible: Each strategy can have independent thresholds per pair (future: add momentum_daily_z_threshold overrides)

**HybridMultiTimeframeBacktest (Engine):**
- Purpose: Orchestrate multi-strategy, multi-symbol, multi-timeframe backtests
- Location: `backtest/backtest_hybrid.py`
- Pattern: Monolithic class with strategy methods (`_backtest_swing_symbol`, `_backtest_m15_symbol`, etc.), signal helpers, RAG integration
- Key methods:
  - `z_score_signal(close, period=20)` → rolling Z-score
  - `adaptive_atr(high, low, close)` → volatility-adjusted ATR
  - `vol_percentile(atr)` → recent vol vs rolling window
  - `regime_changepoint(adx)` → trend/range regime detector
  - `_rag_size_modifier(symbol, strategy_type, session, ...)` → confidence-based sizing
- Entry point: `backtest()` method (called from main or scripts)

**Signal Filters (Pure Numpy):**
- Purpose: Stateless computation of alpha signals
- Location: `backtest/signal_filters.py`
- Abstractions:
  - `rolling_hurst(close, window=100)` → Hurst exponent (H < 0.45 = mean-reverting, H > 0.55 = trending)
  - `rolling_ols_zscore(close, window=20)` → trend-adjusted Z-score (vs rolling mean)
  - `sigdet_zscore(close, lag, influence, factor)` → adaptive Z-score (peak detector inspired)
  - All return pandas Series matching input index, NaN-padded for lookback period
- Reusability: Used in backtest engine; planned for direct import in V3 router

**RAGSignalFilter (Semantic Scoring):**
- Purpose: Score signal confidence based on historical trade similarity
- Location: `v3_intelligence/rag_signal_filter.py`
- Pattern: ChromaDB-backed retrieval (optional, graceful fallback if chromadb unavailable)
- Key method: `score_signal(symbol, strategy_type, session, daily_z, h1_z, vol_percentile, hour_utc)`
  - Returns: `{"action": "SKIP"|"TAKE"|"REDUCE", "confidence": 0–1, "size_modifier": 0–1}`
- Embedding context: "{symbol} {strategy} {direction} {session} {hour} {daily_z} {h1_z} {vol_regime} {z_magnitude}"
- Distance metric: similarity to top-k (default 10) historical trades

**CircuitBreaker (Risk Gate):**
- Purpose: Multi-layer risk management (daily loss, weekly loss, max drawdown)
- Location: `ea/include/CCircuitBreaker.mqh`
- Pattern: MQL5 class inheriting from `CCorrelationMonitor`
- State: `SCircuitBreakerState` with activation time, 48-hour resumption window
- Check points: Daily close, weekly close, continuous drawdown monitoring
- Action: Halts EA if any limit breached; logs reason; schedules automatic resumption after 48h

**PositionManager (Position Tracking):**
- Purpose: Real-time tracking of open positions on MT5
- Location: `ea/include/CPositionManager.mqh`
- Pattern: MQL5 class inheriting from `CPositionSizer`; maintains array of `SOpenPosition` structs
- Key methods: `UpdateAllPositions()`, `GetTotalOpenRisk()`, `GetSymbolExposure(symbol)`, `CountPositionsByDirection(symbol, dir)`
- Uses: `CTrade` class from MT5 Standard Library for order execution

---

## Entry Points

**Python Backtest Runners:**

1. **`backtest/backtest_hybrid.py` (main):**
   - Purpose: Run dual-strategy hybrid backtest (Swing + M15 Scalp)
   - Invocation: `python backtest_hybrid.py`
   - Output: Writes to `backtest/results/` and optional `backtest/analysis/`
   - What it does:
     - Loads all 8 pairs' DAILY/H1/M15 data from `data/` directory
     - Initializes `HybridMultiTimeframeBacktest` with RAG/logging enabled
     - Loops over each pair, calls `_backtest_swing_symbol()` and `_backtest_m15_symbol()`
     - Aggregates trades, computes Sharpe/metrics, writes CSV report

2. **`backtest/backtest_evaluate_all.py`:**
   - Purpose: Comprehensive matrix of all pairs × all strategies with independent evaluation
   - Invocation: `python backtest_evaluate_all.py [--swing|--m15|--intraday]`
   - Output: Ranked comparison matrix showing Sharpe per pair-strategy combination
   - Used for: Parameter optimization and strategy selection

3. **`backtest/backtest_all_timeframes.py`:**
   - Purpose: Alternative backtest runner (likely legacy or multi-TF specific)
   - Location: `backtest/backtest_all_timeframes.py`

**Data Utilities:**

4. **`scripts/fetch_data.py`:**
   - Purpose: Automated Dukascopy historical data download and CSV conversion
   - Invocation: `python fetch_data.py [--since 2020] [--sym GBPUSD] [--tf M15] [--workers 30]`
   - Output: Writes `{SYM}_{TIMEFRAME}.csv` to `data/` directory
   - Why: Provides authoritative historical data (same as live MT5 feed venue)

5. **`scripts/download_history.py`, `download_intraday_data.py`, `download_new_pairs.py`, `get_forex_daily.py`:**
   - Purpose: Various data fetching strategies (yfinance, other sources)
   - Typically used for M15/H1 if Dukascopy unavailable or for rapid testing

**MQL5 EA:**

6. **`ea/MultiPairEA.mq5`:**
   - Purpose: Live trading orchestrator on MT5 platform
   - Entry points (MQL5 event handlers):
     - `OnInit()`: Initialize risk manager, logger, signal generators, pair configs
     - `OnTick()`: Per-tick event loop — update positions, check circuit breaker, evaluate new signals
     - `OnDeinit()`: Cleanup
   - Architecture: Instantiates one `CCircuitBreaker`, one `CScalingManager`, 5 symbol-specific signal generators, 15 helper classes
   - Future (V3): Will consume ZMQ messages (Tier 1) or poll signals.json (Tier 2/3 fallback)

---

## Error Handling

**Strategy:** Multi-layer defense with explicit logging at each failure point.

**Patterns:**

1. **Data Loading Failures:**
   - Pattern: Check file existence before `pd.read_csv()`, return None or empty DataFrame if missing
   - Example: `_load_h1()` in `backtest_hybrid.py` checks 4 possible filename patterns
   - Recovery: Skip strategy if data unavailable; log warning

2. **Signal Computation NaN Handling:**
   - Pattern: Fill NaN with 0 (neutral) or previous value (for rolling stats)
   - Example: Hurst exponent returns NaN for first 100 bars; used as 0 (neutral filter)
   - Recovery: Trade proceeds with neutral signal; next bar recomputes

3. **Z-score / ATR Edge Cases:**
   - Pattern: Clip to avoid division by zero; use adaptive ATR (vol-adjusted) to handle low-vol regimes
   - Example: If std → 0, Z-score formula handled by pandas rolling().std() default behavior
   - Recovery: Trades execute with sensible defaults

4. **Position Tracking Gaps:**
   - Pattern: Log all position state changes; use `entry_bar` index to detect orphaned positions
   - Example: If position dict becomes stale, timeout logic (`bars > max_bars`) closes it
   - Recovery: Trade closed at exit_price, recorded with reason="timeout"

5. **Circuit Breaker (EA):**
   - Pattern: Check risk limits at multiple points (daily close, on every trade)
   - Example: `CheckAllLimits()` in `CCircuitBreaker` triggers `ActivateCircuitBreaker()` if any limit hit
   - Recovery: EA stops trading; logs `CRITICAL` alert; schedules auto-resumption in 48h

6. **RAG Filter Failures:**
   - Pattern: Graceful fallback if ChromaDB unavailable
   - Example: `CHROMA_AVAILABLE` flag; if false, RAG scoring skipped, size_modifier defaults to 1.0
   - Recovery: Trade proceeds without semantic confidence adjustment

---

## Cross-Cutting Concerns

**Logging:**
- **Python:** TradeLogger (SQLite) + print/logging to console
  - Trades logged to `data/marketmind.db` with full context (Z-scores, session, hour, vol_pct)
  - Decision log captures parameter changes + rationale
- **MQL5:** CLogger class
  - Severity levels: INFO, WARN, CRITICAL
  - Writes to MT5 Journal and optional MarketMind_Journal file
  - Tier transitions (Python live → batch → MQL5 safety) logged at CRITICAL level

**Validation:**
- **Entry-side:** Z-score threshold checks, session filters, daily Z alignment gates
- **Risk-side:** Circuit breaker (daily/weekly loss, max DD), correlation monitor, position sizing via Kelly fraction
- **Exit-side:** ATR-based targets/stops, bar timeout, profit/loss thresholds

**Authentication:**
- **Data sources:** Dukascopy (public, no API key). MT5 API (handled by Windows MT5 terminal, no explicit auth)
- **IPC (future V3):** ZMQ uses firewall restrictions (localhost or restricted network) — no crypto handshake
- **Signals.json fallback:** File-based, no authentication (assumes secure environment)

**Configuration & Environment:**
- **Pair config:** `v3_intelligence/pair_config.py` module (not a .env file)
- **Data dir:** Hardcoded `Path(__file__).parent / "data"` in backtest engine
- **Reports dir:** Auto-created under `Path(__file__).parent.parent / "reports"`
- **MT5 account:** IC Markets Raw, 1:100 leverage (specified in pair configs, enforced in CCircuitBreaker)

---

## Boundary: Python ↔ MQL5

**Current V2 Interface:**
- File-based bridge: `signals.json` (manually created or by external script)
- EA reads JSON at specified poll interval; extracts symbol, direction, size, SL, TP
- Drawback: High latency (~10s minimum), poll-based (not event-driven)

**Planned V3 Interface (Decision D-01):**
- **Primary:** ZMQ bridge (ported from V1)
  - Tier 1 router publishes `OrderRequest` messages (5558)
  - EA subscribes; executes immediately on receipt (<50ms latency)
  - Message schema: typed MessagePack with symbol, direction, size, entry_price, stop_loss, take_profit
- **Failover:** signals.json (same as V2)
  - Tier 2 router activates if ZMQ heartbeat missing >30s
  - EA falls back to polling signals.json every ~10s
  - Safety: Tier 3 embedded strategy activates if signals.json stale >10min
- **Stateless MQL5 model (V3 requirement):**
  - EA does NOT compute alpha signals
  - EA does NOT maintain regime state
  - EA only manages position lifecycle and risk gates
  - All intelligence stays on Linux router (Tier 1/2)

---

## V3 Intelligence Layer Scope (from Phase 0 CONTEXT)

**Strategies (locked decision D-02):**
1. Swing (mean-reversion, 4H/Daily) — validated ✓
2. H1 Scalp (London/NY session) — needs 4yr re-validation
3. Momentum (H1 trend with daily Z gate) — needs 4yr re-validation
4. M15 Intraday (5-hour mean-reversion) — validated (Sharpe 0.13) but pending re-tune
5. Carry (overnight, 24H) — to be ported from V1

**Router layers (locked decision D-03):**
- Tier 1: Python live (ZMQ streaming, stateful, full intelligence)
- Tier 2: Python batch (M15 bar close polling, signals.json output)
- Tier 3: MQL5 safety net (hardcoded pair→strategy mapping, minimal filters)

**Validation bar (locked decision D-04):**
- Already-validated (Swing, M15): paper forward 3mo ticks, live Sharpe within 40% of backtest
- New strategies: 2yr train (2022–2024), 2yr OOS held-out (2025–2026)
- Kill switch: 30-day rolling Sharpe < 0.3 → auto-disable strategy-pair

---

*Architecture analysis: 2026-04-21*
