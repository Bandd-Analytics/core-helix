# Domain Pitfalls — V3 Adaptive Strategy Dispatch System

**Domain:** Adding ZMQ bridge + multi-strategy router + live MT5 execution to a validated Python signal engine
**Researched:** 2026-04-21
**Applies to:** Helix v2.0 milestone (V3 Adaptive Strategy Dispatch System)

---

## Scope Note

These pitfalls are specific to this codebase and this milestone. They assume the daily Z-score swing engine is validated (Sharpe 2.08, 539 trades, 35.4% win rate) and the MT5 EA compiles with CCircuitBreaker/CScalingManager/CLogger in place. The core risk is not building new features — it is silently invalidating the existing edge while doing so.

---

## Critical Pitfalls

Mistakes that cause silent edge destruction, data leakage, or live account blow-up.

---

### Pitfall C-1: ZMQ Message Schema Drift Between Python Publisher and MQL5 Consumer

**Phase:** ZMQ Bridge port (Phase 1)

**What goes wrong:**
The Python side publishes an OrderRequest as a JSON dict. The MQL5 EA parses it with string splitting or a hardcoded field-position assumption. When a new field is added to the Python schema (e.g., `strategy_type`, `regime_state`, `rag_score`) the MQL5 parser either silently reads the wrong field by position or drops the message entirely. No error is raised on either side. The EA continues executing on stale or misread data.

**Why it happens in this codebase:**
The V1 ZMQ stubs (`V1/helix/stubs/zmq_stubs.py`) define the wire API but there is no shared schema contract file. Python and MQL5 are developed on different OS (Linux vs Windows). Schema changes happen on the Python side and the MQL5 consumer is not updated in the same commit.

**Consequences:**
- Wrong lot size sent to CScalingManager (silent, no assertion fails)
- Wrong direction (long/short) if side field shifts position
- CCircuitBreaker never receives `strategy_type` so it cannot gate per-strategy — all strategies trip the same daily loss counter

**Prevention:**
1. Define a single canonical schema file: `v3_bridge/schema.py` with a frozen dataclass `OrderRequest` and a `to_json()` / `from_json()` method.
2. The MQL5 EA must parse by key name using a JSON parser (write a minimal `ParseJsonField(string json, string key)` helper), not by field position or `StringSplit`.
3. Add a schema version field: `{"schema_ver": 3, ...}`. The EA must reject and log any message where `schema_ver` does not match its compiled constant.
4. Write a Python round-trip test: serialize → deserialize → assert field equality for every field in `OrderRequest`.

**Detection:**
- EA `Print()` logs show order size 0.0 or direction=0 on valid signals
- Python side reports send success but MT5 has no new position

---

### Pitfall C-2: ZMQ DEALER/ROUTER Heartbeat Asymmetry on Windows Causes Silent Dead Bridge

**Phase:** ZMQ Bridge port (Phase 1)

**What goes wrong:**
Python runs on Linux with pyzmq. MT5 EA uses `ZeroMQ.mqh` (the community MQL5 ZMQ wrapper). The Python side sends heartbeats on a 1-second timer. The Windows ZMQ DLL (`libzmq.dll`) has a different default linger timeout and socket close behavior. When MT5 terminal is restarted or the EA is reloaded during optimization, the Windows socket does not cleanly close. The Python socket connects to a dead endpoint — `zmq_send` returns success (message queued internally) but nothing reaches the EA. No error is raised. The live service thinks it is connected; the EA is not receiving.

**Why it happens in this codebase:**
The V1 `ipc/__init__.py` is a stub (`# TODO: Phase 4`). There is no implemented heartbeat or reconnect logic to port from. The heartbeat must be built from scratch.

**Consequences:**
- Signal service runs, computes signals, publishes OrderRequests — zero executions on live account
- The 7-day demo gate passes vacuously (trade count = 0, which is within 20% of 0)
- Discovery only happens when you check the live account and see no trades

**Prevention:**
1. Implement explicit heartbeat: Python sends `{"type": "heartbeat", "ts": <unix_ms>}` every 500ms on a separate PUB socket. EA subscriber checks that last heartbeat age < 2000ms before executing any trade.
2. EA must log `BRIDGE_DISCONNECTED` and refuse all `OrderRequest` processing when heartbeat times out.
3. Python side must implement reconnect logic: if no ACK received for 3 consecutive sends, `socket.close()` and `socket.connect()` again.
4. Set `ZMQ_LINGER=0` explicitly on all sockets before close: `socket.setsockopt(zmq.LINGER, 0)`. This prevents the Windows linger hang.
5. Test the bridge by killing and restarting the MT5 EA while Python is running. Confirm Python detects disconnection within 2 seconds.

**Detection:**
- Python heartbeat send count increases but EA heartbeat receive count (logged via `Print`) does not
- `socket.poll(timeout=500)` returns 0 consistently

---

### Pitfall C-3: Look-Ahead Bias via searchsorted Date Merge in H1 Scalp / Momentum Backtest

**Phase:** H1 scalp + Momentum 4yr backtest validation (Phase 2)

**What goes wrong:**
The current `backtest_hybrid.py` merges daily Z-score context onto H1 bars using `np.searchsorted(daily_d, h1_d, side='right') - 1`. This is correct for the daily swing strategy because the daily bar closes before H1 bars open the next day. However, when adding an H1 scalp or momentum strategy where the signal is computed on H1 data and the entry fires at `h1.iloc[i]` (the close price of bar `i`), the ATR and Z-score computed at bar `i` already include bar `i`'s close. Entry at `iloc[i]` means you are trading on a bar you have already seen close — this is valid for next-bar entry but the current loop enters at `px = row['Close']` which is the close of the signal bar itself, not the open of the next bar.

**Why it happens in this codebase:**
`backtest_hybrid.py` lines 219 and 346: `px = row['Close']`. This is the close of bar `i`. The signal (z_score, atr) is computed on bar `i`'s close. Entry price = close of bar `i`. In backtesting this is perfect execution at the exact signal bar close — impossible in live trading where you only see the close after the bar completes. The result is an optimistic entry price on every trade.

**Consequences:**
- H1 scalp Sharpe inflated by ~0.2–0.4 (tight 2× ATR target means entry price error of half a pip matters)
- Routing matrix built on inflated Sharpe numbers dispatches scalp strategy too aggressively
- Live performance of scalp strategy is worse than expected, causing draw-down before the 7-day gate catches it

**Prevention:**
1. For H1 scalp and momentum strategies, change entry price to `h1.iloc[i+1]['Open']` (next bar open) and set the entry signal on bar `i`.
2. Wrap with bounds check: `if i + 1 >= len(h1): continue`.
3. Compute a "signal bar vs entry bar" latency test: run both entry-at-close and entry-at-next-open versions and report the Sharpe difference. If difference > 0.3, the edge is sensitive to execution timing.
4. The V1 `PiTValidator` in `V1/helix/src/quality/pit_validator.py` catches `df['close']` without `.shift(1)` in assignments — run it against the new H1 strategy files before committing results to the routing matrix.

**Detection:**
- Backtest Sharpe drops by more than 15% when switching from close-of-signal-bar to open-of-next-bar entry
- H1 scalp live trades miss targets by consistent small margins (entry price is consistently worse than backtest assumed)

---

### Pitfall C-4: HMM-GARCH State Label Permutation Destroys Regime → Strategy Mapping

**Phase:** HMM-GARCH port + PiT discipline manager (Phase 3)

**What goes wrong:**
HMM state labels are permuted by the EM initialization seed. The V1 `HMMGARCHRegimeDetector` in `hmm_garch.py` sorts states by ascending unconditional variance (State 0 = lowest vol = Trending, State 1 = Mean-Reverting, State 2 = Crisis). This sorting is deterministic for a given dataset. When the model is **re-fitted on the V2 4yr dataset** (larger, different pairs, different date range), the variance ordering may differ from V1 assumptions. If the sort key produces a different assignment (e.g., MEAN_REVERTING is now State 0 instead of State 1), the `RegimeState` enum mapping in `signal_types.py` is wrong for this dataset without any error being raised.

**Why it happens in this codebase:**
The V1 `RegimeOrchestrator` uses `REGIME_ACTIVATION[self._current_regime]` to dispatch engines. The enum values are integers (0, 1, 2). If the HMM fit assigns integer 0 to Mean-Reverting (lowest vol in this dataset) but the enum defines `RegimeState(0) = TRENDING`, the router dispatches trend-following strategies during mean-reversion regimes. The validated daily swing edge is disabled when it should fire.

**Consequences:**
- Daily Z-score swing strategy blocked in mean-reversion regimes (exactly when it should trade)
- H1 scalp dispatched during trending regimes (where it was shown to destroy alpha in combined-layer testing)
- Sharpe collapses in live trading with no obvious diagnostic

**Prevention:**
1. After fitting on new data, print the unconditional variance per state and manually verify the ordering matches the intended semantic. Add an assertion: `assert garch_params[0].unconditional_variance < garch_params[1].unconditional_variance < garch_params[2].unconditional_variance`.
2. Validate regime labels against a known-regime reference period: pick 3 months of clear trending (e.g., USDJPY 2022 BoJ divergence) and 3 months of clear ranging. Run `predict_viterbi()` and check that the majority label matches expectation.
3. Log the regime label distribution in the 4yr backtest: if State 0 (TRENDING) accounts for < 20% of bars, something is wrong.
4. Keep the `RegimeState` enum integer values as documentation, not as logic. Use `.name` comparisons in dispatch logic, not integer comparisons.

**Detection:**
- `predict_viterbi()` on a known-trending period returns `RegimeState.MEAN_REVERTING` for majority of bars
- Routing matrix shows daily swing dispatched 0% of bars in the 4yr run

---

### Pitfall C-5: HMM Viterbi Uses Full-History Data — Backtest PiT Contamination

**Phase:** HMM-GARCH port + PiT discipline manager (Phase 3)

**What goes wrong:**
`predict_viterbi()` in `hmm_garch.py` runs the Viterbi algorithm over the entire return series passed to it. In a backtest, if you pass the full 4yr return series to `predict_viterbi()` and then use the resulting state sequence as a per-bar regime label, you have look-ahead bias: the regime label for bar `t` was computed using information from bars `t+1` through `t+N`. The H1 scalp and momentum strategies will appear to time regime transitions perfectly.

**Why it happens in this codebase:**
The V1 `OnlineRegimeFilter` correctly implements the forward algorithm (causal). But the V1 `HMMGARCHRegimeDetector.predict_viterbi()` is an offline method. The distinction is easy to miss when porting: a developer who sees `predict_viterbi()` and uses it to generate the regime column in the 4yr backtest dataframe will produce inflated results.

**Consequences:**
- Routing matrix built on Viterbi-labeled regimes shows 20–40% higher Sharpe than live performance
- H1 scalp looks validated but lives in a regime that is only identifiable in hindsight
- The 7-day paper trade gate will catch this but only after a week of trades

**Prevention:**
1. In the 4yr backtest, the regime column must be generated exclusively by `OnlineRegimeFilter.update()` called bar-by-bar in chronological order.
2. Add a test: run the same backtest with Viterbi labels vs online filter labels. If Sharpe differs by > 0.3, the online filter version is the ground truth. Reject the Viterbi version.
3. The V1 `validate_pit_compliance()` function in `pit_manager.py` tests IC ratio (contemporaneous IC vs forward IC). Run it against the regime signal column.
4. Create a helper `regime_series_from_online_filter(returns: pd.Series, detector) -> pd.Series` that enforces causal-only regime generation and call it exclusively in backtest code.

**Detection:**
- Backtest Sharpe for H1 scalp drops significantly when regime is generated with `OnlineRegimeFilter` vs `predict_viterbi`
- Contemporaneous IC of regime signal exceeds forward IC by 1.5× (the `validate_pit_compliance()` threshold)

---

### Pitfall C-6: Strategy Router Collapses Daily Swing Edge by Treating It as One Option Among Many

**Phase:** StrategyRouter build (Phase 4)

**What goes wrong:**
The StrategyRouter receives regime + routing matrix + RAG confidence and dispatches a single strategy. If the router is implemented as argmax(Sharpe_per_strategy), it will dispatch H1 scalp or momentum on days when the daily swing Z-score is also above threshold. This creates the same alpha-destruction that was documented in V1: intraday strategies running on days with open daily swing positions consume the same ATR-defined risk budget and increase correlated drawdown.

**Why it happens in this codebase:**
The `PairConfig` dataclass has `allow_swing`, `allow_scalp`, `allow_momentum` as independent boolean flags. If the router treats these as a pick-one dispatch table, it will override the pair config's intent. The existing validated result (Sharpe 2.08) was produced with swing as the only active strategy on USDJPY, GBPJPY, GBPAUD.

**Consequences:**
- For USDJPY (best swing pair, Sh 3.09): router dispatches H1 scalp (Sh -2.34) on trending days → live account loss
- The daily swing edge is preserved in backtest (separate position tracking) but destroyed in live (shared capital account)
- This is the exact failure mode that was documented in the milestone context: "H1 scalp + Momentum tested COMBINED with daily swing → destroyed alpha"

**Prevention:**
1. The router must implement a priority hierarchy, not a single selection: (a) if daily swing condition is met AND pair `allow_swing=True` → always dispatch swing; (b) only dispatch scalp/momentum when daily swing is NOT in position for that pair.
2. Add a position state check: router must query the CCircuitBreaker/CPositionManager before dispatching any intraday strategy for a pair that has an open swing position.
3. The routing matrix scores (Sharpe by strategy) are a dispatch filter, not a replacement for the hierarchy. A strategy with Sharpe 1.5 that fires when no swing position exists is better than dispatching it over an open Sharpe 3.09 swing trade.
4. Write a router invariant test: given a simulated open swing position on USDJPY, assert that `router.dispatch(symbol="USDJPY", ...)` returns `NONE` for scalp and momentum strategies.

**Detection:**
- 4yr router backtest shows more than one concurrent position per pair on the same timeframe
- Total position count per pair exceeds the `allow_*` flags in `PairConfig`

---

### Pitfall C-7: CCircuitBreaker Equity Baseline Is Set at EA Init — Multi-Strategy Dispatch Resets It

**Phase:** Live service + MT5 EA modification (Phase 5)

**What goes wrong:**
`CCircuitBreaker.InitCircuitBreaker(InpInitialEquity, limits)` sets the equity baseline at EA startup. The circuit breaker computes daily/weekly loss as a percentage of this fixed baseline. In V3, the EA now receives `OrderRequest` messages for multiple strategies (swing, scalp, momentum) on multiple pairs. If the EA is reloaded (common during MT5 terminal updates or broker session resets), `InpInitialEquity` resets to the hard-coded input parameter (1000.0 in the current EA) regardless of current account equity. A live account at $1,100 now has a circuit breaker calibrated to $1,000 — which means the daily loss limit fires 10% too early.

**Why it happens in this codebase:**
`MultiPairEA.mq5` line 21: `input double InpInitialEquity = 1000.0`. This is a static input. On EA reload it will revert to 1000.0 unless the trader manually updates it. With multiple concurrent strategies, equity fluctuates more rapidly than single-strategy trading.

**Consequences:**
- Circuit breaker trips at wrong equity level after account growth
- After a string of wins, a normal losing day triggers the circuit breaker prematurely
- Or worse: after account loss to $900, the circuit breaker threshold is now loose relative to actual equity

**Prevention:**
1. On `OnInit()`, replace `InpInitialEquity` with `AccountInfoDouble(ACCOUNT_EQUITY)` as the baseline — always use current equity, not a static parameter.
2. Persist the baseline to a global variable file (`GlobalVariableSet("helix_equity_baseline", equity)`) so it survives EA reloads.
3. Read the persisted baseline on `OnInit()`: if `GlobalVariableCheck("helix_equity_baseline")` returns true, use the stored value; otherwise use current equity and store it.
4. For multi-strategy: the circuit breaker must track daily loss per-strategy (using the `magic` number field in `OrderRequest`) not only as portfolio-level loss. A bad scalp day should not block swing trades.

**Detection:**
- EA logs show `CIRCUIT BREAKER ACTIVATED` immediately after a reload with no recent losses
- `GetDailyLossPercent()` returns a non-zero value on a fresh session

---

## Moderate Pitfalls

### Pitfall M-1: Daily Z-Score Merge Carries Stale Same-Day Values Into H1 Scalp Entry Decisions

**Phase:** H1 scalp backtest (Phase 2)

**What goes wrong:**
`backtest_hybrid.py` uses `np.searchsorted(daily_d, h1_d, side='right') - 1` to map daily Z-score onto each H1 bar. `side='right'` means that H1 bars on the same calendar date as the daily bar close get the daily Z-score from that close. For the swing strategy this is acceptable (daily bar closes at 17:00 NY, H1 entries happen next day). For H1 scalp strategies that can fire from 00:00 UTC, this assigns the previous day's daily Z-score to the first bar of a new day — which is correct. But on days where the daily bar is computed from H1 data that runs through 23:59, the first H1 bar of the SAME day has no valid daily Z-score yet. The `side='right'` gives it the previous day's close.

For swing this is intentional and validated. For H1 scalp, if the strategy uses the daily Z direction filter (dz alignment), a stale Z-score from the previous day's close may misalign the direction filter for the first several hours of the new day.

**Prevention:**
Add a session-time guard: H1 scalp entries before 07:00 UTC (before London open) use the previous day's daily Z — document this explicitly. Verify that excluding pre-07:00 H1 scalp entries does not materially change the routing matrix Sharpe.

---

### Pitfall M-2: RAG ChromaDB Index Contains Only Swing Trades — Inflates Scalp Confidence Scores

**Phase:** StrategyRouter + RAG integration (Phase 4)

**What goes wrong:**
The existing ChromaDB index (`RAGSignalFilter`) was seeded with 539 daily swing trades. The `score_signal()` method performs semantic similarity search against this history. When the router queries RAG confidence for an H1 scalp entry, it retrieves nearest-neighbor swing trades (different strategy type, different bars_held, different session profile) and scores them. The returned `size_modifier` is calibrated on swing trade outcomes, not scalp outcomes.

**Why it happens in this codebase:**
`rag_signal_filter.py` accepts `strategy_type` as a query field but the existing index only has `'DAILY_SWING_LONG'` and `'DAILY_SWING_SHORT'` entries. The ChromaDB `where` filter for `strategy_type` will return empty results for scalp queries, causing the RAG module to fall back to the default `size_modifier=1.0` — or, if no `where` filter is applied, it will incorrectly match swing trades.

**Prevention:**
1. Verify the RAG query includes a `where={"strategy_type": strategy_type}` filter.
2. For H1 scalp and momentum strategies, disable RAG scoring until 50+ trades are indexed for each strategy type. Use `size_modifier=1.0` (neutral) until the index is warm.
3. After the 4yr backtest is complete, seed the ChromaDB index with H1 scalp and momentum trades separately before running the router in live mode.

---

### Pitfall M-3: Windows pyzmq DLL Version Mismatch Between Python and libzmq.dll

**Phase:** ZMQ Bridge port (Phase 1)

**What goes wrong:**
The MT5 community ZeroMQ wrapper (`ZeroMQ.mqh` / `libzmq.dll`) bundles a specific version of libzmq (typically 4.2.x or 4.3.x). The Linux Python side uses `pyzmq` which links against the system libzmq. If the Linux pyzmq version uses ZMQ protocol 3.1 features not supported by the Windows DLL version, certain socket options (`ZMQ_IMMEDIATE`, `ZMQ_PROBE_ROUTER`) silently fail on Windows without error codes.

**Prevention:**
1. On the Python side, constrain: `import zmq; assert zmq.zmq_version_info() >= (4, 2, 0)`.
2. Avoid advanced socket options. The bridge only needs PUSH/PULL (orders) and PUB/SUB (heartbeat). Both are stable in all ZMQ 4.x versions.
3. Test the DLL version: the MT5 community wrapper typically ships `libzmq.dll` version 4.2.5. Pin pyzmq to a version that is API-compatible: `pyzmq>=22.0,<26.0`.

---

### Pitfall M-4: 4yr Backtest Sharpe Computed Per-Trade Not Annualized Correctly for H1 Timeframe

**Phase:** H1 scalp + Momentum 4yr validation (Phase 2)

**What goes wrong:**
The existing `_metrics()` method in `backtest_hybrid.py` computes Sharpe as `pnl.mean() / pnl.std() * np.sqrt(252)`. This annualization assumes daily frequency (252 trading days). H1 scalp trades typically close within 4 bars (4 hours). Using `sqrt(252)` for a strategy that fires 3–8 times per day inflates the Sharpe significantly relative to a daily strategy.

**Prevention:**
For H1 strategies, annualize using trade frequency: count average trades per year across the 4yr window and use `sqrt(trades_per_year)` not `sqrt(252)`. Alternatively, use the time-based annualization from vectorbt.pro which handles this correctly. Report both the per-trade Sharpe and the time-series Sharpe to catch the discrepancy.

---

### Pitfall M-5: MT5 IOC Fill — No Position Confirmation Before ZMQ ACK

**Phase:** Live service + MT5 EA modification (Phase 5)

**What goes wrong:**
The V1 `mt5_adapter.py` submits an `ORDER_FILLING_IOC` order and returns `OrderResult` based on `result.retcode == TRADE_RETCODE_DONE`. IOC fills are either filled immediately or cancelled. At IC Markets with ~35ms execution, the order can return `RETCODE_DONE` but the position may not yet appear in `positions_get()` if polled within the same millisecond. The Python side receives a success ACK and logs the trade as open. If the EA then receives a second `OrderRequest` for the same pair (e.g., from the scalp strategy) before the first position is visible to `positions_get()`, it will open a second position.

**Prevention:**
1. After `order_send()` returns `RETCODE_DONE`, poll `positions_get(symbol=symbol)` with a 50ms retry loop (max 3 retries) to confirm the position appears before publishing the ACK.
2. The EA must maintain an internal `pending_pairs` set: add `symbol` to the set when an `OrderRequest` is sent to broker, remove it when the position appears in `positions_get()`. Reject any `OrderRequest` for a symbol in `pending_pairs`.

---

## Minor Pitfalls

### Pitfall m-1: backtest_evaluate_all.py H1 Data Window Is 730 Days, Not 4 Years

**Phase:** H1 scalp + Momentum 4yr validation (Phase 2)

**What goes wrong:**
`pair_config.py` comment says "H1 scalp (730-day H1 window)". The 4yr backtest requirement in PROJECT.md says "4yr validation window". These are different. If the H1 data files are only 730 days (2 years), the routing matrix is built on 2yr data while the requirement says 4yr. The Sharpe numbers in the comment block of `pair_config.py` (e.g., AUDNZD H1 scalp Sh 1.63) are from the 730-day window and may not hold over 4 years.

**Prevention:**
Before running the 4yr backtest, verify that `{sym}_H1_730d.csv` files are extended to 4yr. If the data fetcher only downloads 730 days, update `download_history.py` to fetch 4yr of H1 data into a new `{sym}_H1_4yr.csv` file. Do not overwrite the validated 730-day files.

---

### Pitfall m-2: PiTValidator AST Check Does Not Catch numpy Indexing Patterns

**Phase:** HMM-GARCH port + PiT discipline (Phase 3)

**What goes wrong:**
The V1 `PiTValidator` scans for `df['close']`-style subscript access without `.shift()`. It does not catch `arr[i]` numpy array indexing patterns (which are used extensively in `signal_filters.py` and would appear in the HMM-GARCH port). A developer who writes the online forward filter using `returns[t]` indexing will not be flagged by the validator.

**Prevention:**
Supplement AST validation with the IC-based runtime check: `validate_pit_compliance()` from `pit_manager.py`. Run it on the regime signal series output of the ported `OnlineRegimeFilter` before committing the 4yr routing matrix numbers.

---

### Pitfall m-3: Timezone Ambiguity in Daily-to-H1 Date Merge After Data Source Change

**Phase:** H1 scalp + Momentum 4yr backtest (Phase 2)

**What goes wrong:**
The `_load_daily()` method reads CSV files with `parse_dates=True`. If the 4yr H1 data is fetched from a different source than the existing 730-day files (e.g., a new broker feed vs the existing download script), the timezone representation may differ: one is UTC-naive, the other is UTC-aware with `+00:00` suffix. `str(d)[:10]` date extraction still works, but the `searchsorted` alignment produces off-by-one errors at daylight saving time transitions (UK DST rollover in March/October shifts the H1 bars by 1 hour relative to daily bars).

**Prevention:**
Normalize all timestamps to UTC-naive at load time: `df.index = df.index.tz_localize(None)` if tz-aware, or `df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)` if mixed. Add a data loading test that verifies the first H1 bar of a day is at 00:00 UTC, not 01:00 UTC, for both summer and winter dates.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| ZMQ bridge port | Schema drift (C-1) and silent dead bridge (C-2) | Schema version field + heartbeat watchdog before any live test |
| H1 scalp 4yr backtest | Entry-at-signal-close bias (C-3) + wrong Sharpe annualization (M-4) | Switch to next-bar open entry; use trade-frequency annualization |
| HMM-GARCH port | State label permutation (C-4) and Viterbi PiT contamination (C-5) | Variance-order assertion + online filter enforced for backtest |
| StrategyRouter | Router override of swing priority (C-6) + stale RAG scores (M-2) | Priority hierarchy (swing > intraday) + position-state query |
| Live MT5 EA | Equity baseline reset (C-7) + IOC race condition (M-5) | Use live equity on init + position confirmation poll |

## Sources

- Direct code inspection: `V1/helix/src/alpha/regime/hmm_garch.py`, `online_filter.py`, `orchestrator.py`
- Direct code inspection: `V2/backtest/backtest_hybrid.py`, `signal_filters.py`, `pair_config.py`
- Direct code inspection: `V2/ea/MultiPairEA.mq5`, `CCircuitBreaker.mqh`
- Direct code inspection: `V1/helix/src/data/pit_manager.py`, `V1/helix/src/quality/pit_validator.py`
- Direct code inspection: `V1/helix/stubs/zmq_stubs.py`, `V1/helix/src/execution/mt5_adapter.py`
- Project context: `.planning/PROJECT.md` (milestone scope, validated metrics, key decisions)
- Confidence: HIGH for all C-class pitfalls (identified from direct code inspection of the exact code being ported); MEDIUM for M-class pitfalls (identified from code patterns and known ZMQ/pyzmq behavior)
