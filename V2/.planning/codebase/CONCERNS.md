# Codebase Concerns

**Analysis Date:** 2026-04-21

## Critical Validation Gaps

### Strategy-Specific In-Sample Overfitting & Collapse Risk

**M15 Strategy Sharpe Collapse (60-day → 4-year):**
- Issue: M15 intraday scalp measured Sharpe 2.09 on 60-day window (yfinance); collapsed to 0.13 on 4-year backtest
- Files: `backtest/backtest_hybrid.py` (lines 297–400), `backtest/backtest_evaluate_all.py` (lines 50–60)
- Impact: Strategy flagged `allow_m15_scalp=False` in `v3_intelligence/pair_config.py` (line 105) but code paths still present; live deployment would execute invalid strategy
- Root cause: Severe lookback bias in parameter tuning; 60-day window too short to capture regime shifts, volatility clusters, session seasonality
- Fix approach:
  1. Validate M15 on **full 4-year dataset** (not just 60 days) before any live trading
  2. Implement rolling forward-test: train on 2022-2024, test on 2025-2026 in-sample (no optimization on 2025-2026)
  3. Require 3 months paper trading with live ticks before re-enabling
  4. Add automated kill switch: 30-day rolling Sharpe < 0.3 → disable strategy-pair (Phase 0 CONTEXT.md D-04)

**H1 Scalp & Momentum — Unvalidated on 4-Year Data:**
- Issue: Both strategies only tested on 730-day (H1 data available in backtest/data/) windows; never run against full 4-year backtest
- Files: `backtest/backtest_evaluate_all.py` (lines 62–84 for evaluation configs), `backtest/backtest_hybrid.py` (not implemented — H1 scalp/momentum absent from class)
- Impact: Expected to collapse like M15 when exposed to unseen regime types (2022 crisis, 2024 volatility spike, 2025 carry unwinding)
- Severity: **HIGH** — blocks Phase 0 D-04 validation gate
- Fix approach:
  1. Extend H1 backtest data fetching to full 4-year in `scripts/fetch_data.py` (currently 730d only)
  2. Implement H1 scalp/momentum strategies in `backtest_hybrid.py` (currently missing — only Swing + M15 implemented)
  3. Re-run `backtest_evaluate_all.py` on 4-year window
  4. Document all parameter tuning windows to prevent selection bias (Phase 0 D-04 mandates 2022-2024 train, 2025-2026 OOS)

**GBPJPY M15 Disabled But Code Path Remains:**
- Issue: `pair_config.py` line 105 explicitly disables `allow_m15_scalp=False` (note: "all Z thresholds tested, structurally negative") yet `backtest_hybrid.py` lines 60–61 still includes GBPJPY in `m15_symbols` list
- Files: `v3_intelligence/pair_config.py`, `backtest/backtest_hybrid.py`
- Impact: If config check fails or is bypassed, M15 scalp would execute on GBPJPY despite known structural unprofitability
- Fix approach: Remove GBPJPY from `m15_symbols` list and add runtime assertion to verify pair_config disable flag

---

## Fragile Inter-Process Communication Bridge

### Signals.json File-Based Bridge (Current Interim Solution)

**Race Condition Risk:**
- Issue: No locking mechanism documented for signals.json; multiple processes (Python router, EA polling, backtest harness) may read/write simultaneously
- Files: Referenced in Phase 0 CONTEXT.md (D-01) but implementation not visible in V2 codebase
- Impact: Stale signals (EA reads half-written file), signal loss (overwrite before EA reads), corruption (simultaneous writes)
- Severity: **HIGH** — Tier 2 failover bridge must be rock-solid if Tier 1 (ZMQ) fails
- Observations:
  - No signals.json found in current codebase (`grep -rn "signals.json"` returns empty)
  - Bridge implementation deferred to Phase 1 (not yet ported from V1)
  - Phase 0 D-01 specifies ZMQ as primary with signals.json failover but failover code not present
- Fix approach:
  1. Use file locks (fcntl on Unix, msvcrt on Windows) for all signals.json read/write
  2. Implement atomic write: temp file → rename (prevents partial reads)
  3. Add signal timestamp + heartbeat to detect staleness (>10min → MQL5 Tier 3 activates)
  4. Log all IPC transitions (ZMQ → failover, failover → ZMQ) for observability
  5. Test failover path: kill Python ZMQ publisher mid-backtest, verify Tier 2 activation

**No Acknowledgment Protocol:**
- Issue: EA may read signal, execute trade, but router never knows if execution succeeded (one-way fire-and-forget)
- Files: Phase 0 D-01 design does not specify ACK/NACK mechanism
- Impact: Duplicate trades if signal resent on timeout; orphaned orders if EA crash; no feedback for router confidence scoring
- Fix approach:
  1. Add signals.json fields: `execution_ack` (timestamp when EA processed), `result` (success/fail reason)
  2. Router polls execution_ack with timeout; if missing >30s, log alert and escalate to Tier 2 batch mode
  3. Include in RAG decision logging (trade_logger.py) for learning loop

---

## Hurst Filter Ineffectiveness

**Hurst Exponent Not Blocking Entries as Intended:**
- Issue: `enable_hurst_filter=True` checks `hv > 0.55` to block entries (line 272 in backtest_hybrid.py), but Hurst computation window (80 bars daily = ~4 months) may be too long to catch quick regime changes
- Files: `backtest/signal_filters.py` (rolling_hurst implementation, lines 51–67), `backtest/backtest_hybrid.py` (lines 187–190, 272)
- Observations:
  - Hurst filter implemented in numpy (`signal_filters.py`), ported to MQL5 (`indicators/HurstExponent.mq5`)
  - Filter is optional (`enable_hurst_filter=False` default); not critical to core strategy
  - No validation of filter effectiveness: does it actually reduce losses in trending markets?
- Impact: **MEDIUM** — Optional filter; core strategy works without it, but false sense of regime protection if enabled
- Root cause: Hurst exponent inherently noisy on short windows; 80-bar window chosen empirically without backtested optimization
- Fix approach:
  1. Benchmark Hurst filter impact: run backtest with/without, measure drawdown reduction on trending pairs (GBPJPY, USDJPY)
  2. If impact < 5% reduction in max DD, mark as experimental; remove from production until validated
  3. Document window choice with statistical justification (current choice appears arbitrary)
  4. Consider alternative: ARCH/GARCH regime filter (V1 has implementation in helix/src/alpha/regime/hmm_garch.py, deferred to Phase 3)

---

## Data & Backtest Robustness Issues

### Insufficient Data Coverage for Intraday Strategies

**M15 & H1 Data Limited to 730 Days (2+ Year Window):**
- Issue: `backtest_hybrid.py` loads M15 from `data/{sym}_M15.csv` or `data/{sym}_M15_60d.csv` (line 165); H1 from `{sym}_H1_730d.csv` (line 158)
- Files: `backtest/backtest_hybrid.py` (lines 151–169), `scripts/fetch_data.py` (data fetcher)
- Impact:
  - Cannot validate long-term robustness of intraday strategies
  - M15 has only ~7,200 bars (15-min candles in 730 days); insufficient for robust parameter tuning or walk-forward testing
  - Carries bias: 2024-2026 sample may not represent 2022-2023 volatility/regime dynamics
- Severity: **HIGH** for unvalidated strategies (H1 Scalp, Momentum); **MEDIUM** for M15 (already flagged as needs re-validation)
- Root cause: Dukascopy M15/H1 fetching not yet ported from V1; currently using yfinance (limited depth) or manual download
- Fix approach:
  1. Port `V1/helix/src/data/dukascopy_fetcher.py` to V2 (Phase 0 inventory: priority P1, ~0.5d effort)
  2. Extend `scripts/fetch_data.py` to fetch 4-year M15/H1 via Dukascopy LZMA decoder
  3. Store as parquet (faster load) in data/ directory
  4. Validate data continuity: no gaps, no duplicate ticks, monotonic timestamps

### Look-Ahead Bias Not Explicitly Mitigated

**Close-Based Indicators Computed Before Trade Entry:**
- Issue: Indicators like Z-score are computed on rolling windows that include the current bar's close before entry decision; unclear if backtest correctly prevents future information leakage
- Files: `backtest/backtest_hybrid.py` (lines 84–87 z_score_signal, 94–109 compute_adx, 213+ entry logic)
- Observations:
  - `z_score_signal` uses `close.rolling().mean()` and `.std()` — standard pandas rolling includes current bar
  - Entry checks at line 268+ use daily/h1 data from current bar, then enters at "row['Close']"
  - No explicit comment about timestamp/causality
- Impact: **MEDIUM** — strategy likely correct (rolling window is computed before entry), but lack of explicit guardrails creates maintenance risk
- Fix approach:
  1. Add assertion: entry bars must be at least 20+ bars after data warmup (rolling window length)
  2. Document entry timing clearly: "Entry decision made on bar N close; fill price is bar N+1 open (next bar)"
  3. Add test: re-run 10-trade sample by hand, verify no future data used
  4. Separate "signal bar" (N) from "entry bar" (N+1) in code to eliminate ambiguity

### Data Continuity Not Validated

**No Checks for Missing Bars, Duplicates, or Timezone Issues:**
- Files: `backtest/backtest_hybrid.py` (data loading, lines 151–169), no validation step
- Impact: Gaps in H1 data (2am-6am no liquidity on some pairs) could inflate Sharpe via reduced denominator; duplicates break ATR calculation
- Fix approach:
  1. Add data validation step after load: check monotonic timestamps, count gaps, report missing bars per session
  2. Add timezone safety check for M15/daily merge (line 203–208 uses string slicing; fragile if data sources differ)
  3. Store data with explicit timezone (UTC); error if missing

---

## Code Quality & Maintenance Concerns

### High Volume of Print Statements (Debug Code Mixed with Production)

**Extensive stdout in Backtest Loop:**
- Issue: `backtest_hybrid.py` lines 445–564 contain dozens of `print()` statements for progress reporting
- Also in: `pair_config.py` (208–230), `trade_logger.py` (205–232), `rag_signal_filter.py` (120, 226, 229), `backtest_all_timeframes.py` (139–240), `backtest_strategy.py` (153–202)
- Impact: **LOW** — functional but unprofessional; pollutes logs, makes scripting harder, no structured logging
- Fix approach:
  1. Replace all `print()` with logging module (Python logging)
  2. Add log level control: DEBUG for bar-by-bar, INFO for summary, WARN for errors
  3. Route to file + stdout conditionally
  4. Remove progress bars from backtest (they're slow and pointless in batch mode)

### Complex Monolithic Backtest Engine

**`backtest_hybrid.py` is 775 Lines, Implements 2 Strategies:**
- Issue: Single class mixes data loading, signal generation, position tracking, exit logic, RAG integration, logging, and reporting
- Files: `backtest/backtest_hybrid.py` (entire file)
- Impact: **MEDIUM** — difficult to test individual strategies independently, hard to add H1 Scalp/Momentum without duplication
- Fix approach:
  1. Refactor: extract each strategy into a `Strategy` base class with subclasses (`SwingStrategy`, `M15Strategy`, etc.)
  2. Move position tracking to a shared `Portfolio` class
  3. Move backtest loop to a generic `BacktestEngine` that accepts strategy instances
  4. Result: ~200-line engine + ~150-line per strategy (cleaner, testable, reusable)

### Pair Configuration Hardcoded in Code

**`pair_config.py` Defines All Strategy-Pair Combinations:**
- Issue: If tier assignments or strategy enablement changes, code must be edited and recommitted (not data-driven)
- Files: `v3_intelligence/pair_config.py` (defines PAIR_CONFIGS dict, used by `backtest_hybrid.py`, EA, router)
- Impact: **MEDIUM** — acceptable for current scope but brittle for Phase 3+ multi-strategy expansion
- Fix approach:
  1. Move PAIR_CONFIGS to CSV (pair_strategy_mapping.csv) with columns: Pair, Strategy, Tier, AllowFlag, Parameters
  2. Load at runtime: `get_pair_config(symbol)` reads CSV instead of hardcoded dict
  3. Phase 0 D-03 already mentions "exported from pair_config.py" → CSV for EA to read; implement bi-directionally

---

## Windows-Only Constraint Risk

**MT5 Python API Requires Windows Host:**
- Issue: Live feed and EA execution rely on MetaTrader5 Python API, which only runs on Windows (no native Linux/Mac MT5)
- Files: Phase 0 CONTEXT.md D-05, implicit in architecture (MT5 on Windows, router on Linux)
- Impact: **MEDIUM** — infra constraint, not code bug, but creates single-point-of-failure: if Windows host crashes, ZMQ feed dies
- Mitigation already in place:
  - Phase 0 D-03 specifies Tier 2 (batch mode) and Tier 3 (embedded EA) fallbacks
  - Tier 3 remains active even if Linux router + Windows MT5 both fail
- Fix approach:
  1. Document Windows host resilience: use Windows Server or Hyper-V VM with daily snapshot backups
  2. Test failover: unplug Windows host, verify EA continues on embedded hardcoded strategy
  3. Monitor MT5 Python bridge health: heartbeat check every 5s, alert on miss
  4. No code change needed if failover tiers are verified to work

---

## Experimental/Unimplemented Features

### H1 Scalp & Momentum Strategies Missing from Backtest Engine

**Strategies Defined in `backtest_evaluate_all.py` but Not in `backtest_hybrid.py`:**
- Issue: `backtest_evaluate_all.py` defines `_eval_cfg_scalp()` (line 62) and `_eval_cfg_momentum()` (line 74) and attempts to run them via `Evaluator` class
- But `HybridMultiTimeframeBacktest` base class only implements `_backtest_swing_symbol()` and `_backtest_m15_symbol()` (lines 175, 297)
- There is NO `_backtest_scalp_symbol()` or `_backtest_momentum_symbol()` method
- Files: `backtest/backtest_hybrid.py`, `backtest/backtest_evaluate_all.py` (lines 62–84, 92+)
- Impact: **HIGH** — if scalp/momentum eval runs, it will fail with AttributeError or return empty DataFrames
- Severity: Blocks full evaluation matrix that Phase 0 D-02 requires
- Fix approach:
  1. Implement `_backtest_scalp_symbol()` method in `HybridMultiTimeframeBacktest`
  2. Implement `_backtest_momentum_symbol()` method
  3. Update `Evaluator.run_scalp_with_cfg()` and `Evaluator.run_momentum_with_cfg()` to call new methods
  4. Validate via `backtest_evaluate_all.py --scalp --momentum`

### RAG Index Warmup Not Robust

**RAG Disabled Until >30 Trades Collected:**
- Issue: RAG filter in `backtest_hybrid.py` line 130 returns `1.0` (no size modification) until `self.rag.count < 30`
- Files: `backtest/backtest_hybrid.py` (line 130), `v3_intelligence/rag_signal_filter.py` (lines 67–89)
- Impact: **LOW** — warmup is acceptable; just means first 30 trades execute at full size
- Concern: RAG implementation is V3 feature (not core to V2 validation); if ChromaDB unavailable, falls back to `rag = None`
- Fix approach:
  1. Make RAG truly optional: wrap in try/except, log warning if unavailable, continue without it
  2. Add metrics: track RAG skip reasons (not available, cold start, low count) in trade journal
  3. Document in README: "RAG learning loop activates after 30 trades; first month trades execute at base sizing"

---

## Test Coverage Gaps

### No Unit Tests for Core Strategies

**`tests/unit_tests/` Directory Empty:**
- Files: `tests/unit_tests/` (empty)
- Impact: **HIGH** — cannot regression-test strategy changes, risk silent bugs
- Affected areas:
  - Signal generation (Z-score, Hurst, ADX) — no unit tests
  - Position entry/exit logic — no unit tests
  - Risk management thresholds — no unit tests
  - Data loading & timezone handling — no unit tests
- Fix approach:
  1. Create `tests/unit_tests/test_signal_filters.py` — test rolling_hurst, rolling_ols_zscore, sigdet_zscore
  2. Create `tests/unit_tests/test_backtest_engine.py` — fixture data + verify entry/exit logic
  3. Create `tests/unit_tests/test_pair_config.py` — verify config overrides work
  4. Add pytest + CI integration
  5. Target: ≥80% coverage on core backtest, signal_filters, pair_config modules

### Validation Spreadsheets Not Integrated

**`tests/validation_spreadsheets/` Exists but Not Linked to Code:**
- Files: `tests/validation_spreadsheets/` (likely contains manual Excel checks)
- Impact: Manual validation is good but brittle; drift if code changes
- Fix approach:
  1. Export validation data as pytest fixtures (read Excel, generate test cases)
  2. Run spreadsheet validation as part of CI
  3. Document expected values from spreadsheets in test comments

---

## Security Observations

### No Secrets Management Detected

**Observation:** `.env` files not found; API keys/credentials not visible in source code (good!)
- No concerns identified in this category; MT5 credentials are external (broker account)
- Dukascopy free feed requires no auth
- ZMQ bridge can optionally use TLS (not implemented, Phase 1 enhancement)

### Logging May Expose Sensitive Trade Data

**Issue:** Trade logger (`v3_intelligence/trade_logger.py`) logs all trades to CSV (symbol, entry price, exit price, PnL)
- Files: `v3_intelligence/trade_logger.py` (lines 72+), logs to `.json` files in `data/` directory
- Impact: **LOW** — trade data itself is not secret, but if data/ directory is leaked, profit/loss info is exposed
- Fix approach:
  1. Add permissions check: ensure `data/` and `reports/` are readable by process only (0600)
  2. Document: "Trade journals contain real P&L; do not commit to git or share publicly"

---

## Performance Concerns

### Potential Inefficiencies in Backtest Engine

**Repeated Data Copying in Loop:**
- Issue: `backtest_hybrid.py` line 181–182 and 297–298 call `.copy()` on large dataframes every time a pair is backtested
- Files: `backtest/backtest_hybrid.py` (lines 181–182, 297–298)
- Impact: **LOW** — backtest is not a bottleneck; runs once per day max; copy is safe and correct
- Fix approach: Not necessary; current approach is memory-safe and clear

**RAG Embedding Calls May Be Slow:**
- Issue: RAG filter calls ChromaDB embedding function for every signal (lines 139–142 in backtest_hybrid.py)
- Files: `v3_intelligence/rag_signal_filter.py` (embedding function used in score_signal)
- Impact: **LOW** in backtest (batched); **MEDIUM** in live (per-signal latency)
- Observations: Default embedding function is fast (sentence-transformers on CPU), but adds ~50-100ms per query
- Fix approach:
  1. Cache embeddings for recent signals (LRU cache, size 100)
  2. Batch embed signals if router processes multiple pairs in parallel
  3. Profile live router: measure embedding latency, ensure <200ms per signal for sub-tick execution

---

## Known Issues & Deferred Work

### M15 Strategy Disabled Pending Re-Tuning

**Status:** Live=False (cannot trade)
- Reason: Sharpe collapse from 2.09 (60d) to 0.13 (4yr)
- File: `v3_intelligence/pair_config.py` (line 105 for GBPJPY)
- Blocker: Requires 4-year backtest validation + 3-month paper trading
- Owner: Phase 1 research team

### H1 Scalp & Momentum Not Implemented in Backtest

**Status:** Strategies defined but not coded
- Reason: Backtest engine only supports Swing + M15; scalp/momentum logic never ported
- Files: `backtest/backtest_hybrid.py` (missing methods), `backtest_evaluate_all.py` (broken eval paths)
- Blocker: Prevents Phase 0 D-04 validation gate
- Effort: 2–3 days to implement both strategies + validation
- Owner: Phase 2 implementation team

### Hurst Filter Effectiveness Unproven

**Status:** Optional, disabled by default
- Reason: Hurst exponent may be too noisy; window choice (80 bars) not validated
- Files: `backtest/signal_filters.py`, `backtest/backtest_hybrid.py` line 64
- Blocker: None; optional feature, core strategy works without it
- Action: Benchmark on Phase 2; consider removing if <5% impact
- Owner: Phase 3+ regime filter enhancement

### V1 Portable Components Not Yet Ported

**Status:** Identified but not migrated to V2
- Phase 0 CONTEXT.md Table (lines 185–193) lists porting priorities
- Blocking Phase 1:
  - ZMQ bridge (`helix/src/execution/bridge/`) → needed for D-01 Tier 1
  - Dukascopy fetcher (`helix/src/data/dukascopy_fetcher.py`) → needed for 4-year validation data
- Deferred to Phase 3+:
  - HMM/GARCH regime filter, Cointegration/stat-arb, Online regime filter
- Owner: Phase 1 planning + Phase 2+ execution

---

## Severity Summary

| Severity | Count | Examples |
|----------|-------|----------|
| **HIGH** | 4 | M15 collapse + unvalidated H1/Momentum, fragile signals.json IPC, H1 Scalp/Momentum missing from backtest, insufficient intraday data |
| **MEDIUM** | 7 | Hurst filter unproven, complex monolithic engine, hardcoded pair configs, Windows-only MT5, look-ahead bias not mitigated, RAG index coldstart, data continuity not validated |
| **LOW** | 5 | Print statement clutter, performance non-issues, logging may expose trade data, test coverage gaps, RAG latency in live |

---

## Action Items for Phase 1 (Researcher)

1. **Confirm validation blockers:** Verify M15 4-year collapse metrics, estimate H1/Momentum collapse risk
2. **Inventory V1 portable code:** Locate ZMQ bridge and Dukascopy fetcher, assess porting effort
3. **Map MQL5 EA strategy dispatch:** How much refactoring for Tier 3 hardcoded routing?
4. **Data coverage audit:** Measure M15/H1 data gaps, recommend historical data source (Dukascopy or alternative)

## Action Items for Phase 2 (Planner)

1. **Sequence ZMQ port vs strategy re-validation:** (Recommendation: parallel tracks)
2. **Break backtest refactoring:** Design `Strategy` base class, extract methods
3. **Plan H1 Scalp/Momentum implementation:** Add missing backtest methods, integrate with evaluation matrix
4. **Plan Dukascopy integration:** Extend data fetcher to 4-year depth, validate continuity

## Action Items for Ongoing Maintenance

1. **Add logging:** Replace print() with logging module
2. **Add unit tests:** Target 80% coverage on core modules
3. **Monitor live strategy health:** Implement 30-day rolling Sharpe kill switch (Phase 0 D-04)
4. **Document entry timing:** Clarify bar N vs bar N+1 causality in all strategy docstrings

---

*Concerns audit: 2026-04-21. This document reflects analysis of V2 backtest engine, EA, and V3 intelligence layer as of Phase 0 CONTEXT lock.*
