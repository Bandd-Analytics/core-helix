# Architecture Patterns

**Domain:** V3 Adaptive Strategy Dispatch System — Python signal intelligence wired into live MT5 execution
**Researched:** 2026-04-21
**Confidence:** HIGH — based on direct codebase inspection of all referenced source files

---

## System Overview

The V3 system adds four new Python components and modifies one existing MQL5 EA. The existing Python analysis stack (pair_config, rag_signal_filter, trade_logger) is reused without modification. The existing MT5 EA risk layer (CCircuitBreaker, CScalingManager, CLogger) is preserved intact as the last-gate execution guardian.

```
LINUX (Python)                                    WINDOWS (MT5)
─────────────────────────────────────────────     ───────────────────────────────────────
                                                  ┌─ OnTick() ──────────────────────────┐
  pair_config.py                                  │  MT5 price feed (ticks + bars)       │
  (routing matrix, allow_* flags)                 │        │                             │
       │                                          │        ▼                             │
       ▼                                          │  WindowsPublisher (ZMQ)             │
  V2/v3_intelligence/                             │  PUB tick  :5556                     │
  ├── regime.py  ←── ported from V1              │  PUB bar   :5557                     │
  │   HMMGARCHRegimeDetector                     │  PULL order:5558  ◄──────────────────┼──┐
  │   OnlineRegimeFilter (live)                  │  PUSH fill :5559  ──────────────────►│  │
  │                                              └─────────────────────────────────────┘  │
  ├── pit.py  ←── ported from V1                           │ (ZMQ over TCP/loopback)       │
  │   pit_read, validate_pit_compliance                    │                              │
  │   shift_features                                       ▼                              │
  │                                              V2/bridge/                               │
  └── strategy_router.py  (NEW)                 LinuxConsumer                            │
      StrategyRouter                             SUB tick  :5556                         │
      .route(symbol, regime, bar) →             SUB bar   :5557                         │
        (strategy_name, lot_mult)               PUSH order:5558 ──────────────────────────┘
                │                               PULL fill :5559
                │
                ▼
  V2/live/signal_engine.py  (NEW)
  LiveSignalEngine (async main loop)
  ├── on_bar(bar) → router.route() → RAG score → OrderRequest
  └── on_fill(result) → trade_logger.log_trade()
                │
                ▼
  V2/v3_intelligence/rag_signal_filter.py
  (UNCHANGED — scores signal before dispatch)
                │
                ▼
  V2/v3_intelligence/trade_logger.py
  (UNCHANGED — logs fills for future RAG indexing)

  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

WINDOWS (MT5 EA — modified)
  Modified V2/ea/MultiPairEA.mq5
  OnTimer():
    ├── Pull OrderRequest from ZMQ PULL socket
    │   (replaces internal CMeanRevSignal / CTrendSignal / CHybridSignal calls)
    │
    └── CCircuitBreaker.CheckAllLimits()  [UNCHANGED — last gate]
        └── IF PASS → CScalingManager.SubmitEntryWithRetry()
            └── CLogger.LogTrade()
```

---

## Component Inventory

### New Components

| File | Class | Status | Source |
|------|-------|--------|--------|
| `V2/bridge/linux_consumer.py` | `LinuxConsumer` | Port from V1 | `V1/helix/src/execution/bridge/linux_consumer.py` |
| `V2/bridge/windows_publisher.py` | `WindowsPublisher` | Port from V1 | `V1/helix/src/execution/bridge/windows_publisher.py` |
| `V2/bridge/message_schemas.py` | pack/unpack functions | Port from V1 | `V1/helix/src/execution/bridge/message_schemas.py` |
| `V2/bridge/abstract.py` | `Tick`, `Bar`, `OrderRequest`, `OrderResult`, `Side`, `OrderType` | Port from V1 | `V1/helix/src/execution/abstract.py` |
| `V2/v3_intelligence/regime.py` | `HMMGARCHRegimeDetector`, `OnlineRegimeFilter`, `RegimeState` | Port from V1 | `V1/helix/src/alpha/regime/` + `src/alpha/signal_types.py` |
| `V2/v3_intelligence/pit.py` | `pit_read`, `validate_pit_compliance`, `shift_features` | Port from V1 (simplified) | `V1/helix/src/data/pit_manager.py` |
| `V2/v3_intelligence/strategy_router.py` | `StrategyRouter` | New — no V1 equivalent | — |
| `V2/live/signal_engine.py` | `LiveSignalEngine` | New — no V1 equivalent | — |

### Modified Components

| File | Change Required | Risk |
|------|----------------|------|
| `V2/ea/MultiPairEA.mq5` | Replace signal generation (CMeanRevSignal, CTrendSignal, CHybridSignal) with ZMQ PULL reader; add `#include <Zmq/Zmq.mqh>` | Medium — internal logic change but risk layer untouched |

### Unchanged Components

| File | Role |
|------|------|
| `V2/v3_intelligence/pair_config.py` | Read-only at runtime by StrategyRouter |
| `V2/v3_intelligence/rag_signal_filter.py` | Called by LiveSignalEngine before dispatch |
| `V2/v3_intelligence/trade_logger.py` | Called by LiveSignalEngine on fill receipt |
| `V2/ea/include/CCircuitBreaker.mqh` | Last-gate risk; never touched by router |
| `V2/ea/include/CScalingManager.mqh` | Lot-size and entry execution; never touched by router |
| `V2/ea/include/CLogger.mqh` | MT5-side trade journaling; unchanged |

---

## Data Flow: Per-Bar Signal Dispatch

```
H1 bar closes on MT5 (e.g. GBPUSD 08:00 UTC)
    │
    ▼
WindowsPublisher.publish_bar(bar)
    │  ZMQ PUB multipart [b"GBPUSD", msgpack(Bar)]
    ▼
LinuxConsumer.on_bar callback fires in LiveSignalEngine
    │
    ├─ 1. pair_config = get_pair_config("GBPUSD")
    │      Returns allow_swing=True, allow_momentum=True, etc.
    │
    ├─ 2. regime_filter.update(log_return) → (RegimeState.MEAN_REVERTING, 0.78)
    │      OnlineRegimeFilter — forward-only, no future-bar access
    │
    ├─ 3. strategy_router.route("GBPUSD", RegimeState.MEAN_REVERTING, bar, pair_config)
    │      Returns: strategy="swing", direction=+1, lot_mult=1.0
    │      Returns: None if no strategy qualifies
    │
    ├─ 4. rag.score_signal(symbol, strategy_type, session, daily_z, h1_z, vol_pct, hour_utc)
    │      Returns: {"action": "TAKE", "size_modifier": 1.1, "confidence": 0.54}
    │      If action == "SKIP": abort, no order sent
    │
    ├─ 5. Build OrderRequest(symbol, side, quantity=base_lot * lot_mult * size_modifier,
    │                         sl=entry - 1.5*atr, tp=entry + 4.0*atr)
    │
    └─ 6. LinuxConsumer.send_order(order)
           │  ZMQ PUSH msgpack(OrderRequest)
           ▼
       WindowsPublisher._order_loop() receives
           │
           ▼
       MultiPairEA.OnZmqOrder() (new handler in modified EA)
           │
           ├─ CCircuitBreaker.CheckAllLimits()  ← LAST GATE — no bypass allowed
           ├─ CCircuitBreaker.HasOpenPosition(symbol)  ← one-position-per-pair guard
           └─ CScalingManager.SubmitEntryWithRetry(entryReq, ticket)
               │
               └─ MT5 OrderSend()
```

---

## Data Flow: Fill Acknowledgment

```
MT5 OrderSend() succeeds → ticket assigned
    │
    ▼
WindowsPublisher.send_order_result(OrderResult)
    │  ZMQ PUSH msgpack(OrderResult)
    ▼
LinuxConsumer PULL socket receives
    │
    ▼
LiveSignalEngine.on_fill(result)
    ├─ trade_logger.log_trade(context)   ← persists to SQLite
    └─ rag.index_trade(trade_dict)       ← updates ChromaDB vector index
```

---

## Component Boundaries

### StrategyRouter

The router is the core new intelligence. It reads `pair_config.py` as a **static routing matrix** — it does not write to it.

```python
class StrategyRouter:
    """
    Inputs:
      - symbol: str
      - regime: RegimeState  (TRENDING=0, MEAN_REVERTING=1, CRISIS=2)
      - bar: Bar  (OHLCV, used for z-score computation)
      - pair_config: PairConfig  (allow_* flags, size multipliers, thresholds)
      - lookback_bars: list[Bar]  (rolling window for indicator computation)

    Output:
      RouteDecision(
          strategy: Literal["swing", "h1_scalp", "momentum", "m15_scalp"] | None,
          direction: int,    # +1 long / -1 short / 0 no trade
          lot_mult: float,   # from pair_config.[strategy]_size_mult
          z_score: float,
          atr: float,
          sl_price: float,
          tp_price: float,
          rationale: str,
      )

    Routing logic:
      1. If regime == CRISIS: return None (no trade in any regime crisis)
      2. Filter to allow_*=True strategies for this pair
      3. For each enabled strategy, compute signal (z-score vs threshold)
      4. If regime == TRENDING: prefer momentum/m15_scalp over swing/h1_scalp
      5. If regime == MEAN_REVERTING: prefer swing/h1_scalp over momentum
      6. Return highest-conviction qualifying strategy, or None
    """
```

**Critical boundary:** The router never sees the EA's CCircuitBreaker state. It dispatches OrderRequests unconditionally when its signal fires. The EA circuit breaker is the only entity that can veto execution. This is intentional — the router decides WHAT to trade; the EA decides WHETHER to execute.

### pair_config.py Interface

The router reads `pair_config.py` in two modes:

**Mode 1 — Gate check (per-bar, O(1)):**
```python
cfg = get_pair_config(symbol)
if not cfg.allow_swing:
    skip
```

**Mode 2 — Parameter read (on signal, O(1)):**
```python
z_threshold = cfg.swing_z_threshold   # 2.0
lot_mult = cfg.swing_size_mult        # 1.0
atr_target = cfg.swing_target_atr     # 4.0
atr_stop = cfg.swing_stop_atr         # 1.5
```

`pair_config.py` is **never modified at runtime**. It is a static, file-deployed configuration updated only after re-running the backtest evaluation matrix. This is intentional — it prevents the live system from self-modifying its routing matrix.

### V2/v3_intelligence/pit.py (Ported, Simplified)

The V1 `pit_manager.py` depends on ArcticDB (`arcticdb` library), which is a heavy dependency not needed in V2. The V2 port retains only:

- `validate_pit_compliance(signal_df, price_df)` — used during backtest validation of new strategies before they enter the routing matrix
- `shift_features(df, columns, periods=1)` — used in backtest preprocessing

The `pit_read()` function (ArcticDB-dependent) is **dropped** from the V2 port. V2 uses pandas CSV/parquet from `V2/data/` directly. This is appropriate for the scale of this system.

### V2/v3_intelligence/regime.py (Ported)

The port bundles four V1 modules into one file:

| V1 source | V2 destination |
|-----------|---------------|
| `src/alpha/regime/hmm_garch.py` | `HMMGARCHRegimeDetector` class |
| `src/alpha/regime/online_filter.py` | `OnlineRegimeFilter` class |
| `src/alpha/regime/emissions.py` | `GARCHParams`, `garch_emission_prob` (inline) |
| `src/alpha/regime/viterbi.py` | `viterbi_decode` (inline, used for offline backtest only) |
| `src/alpha/signal_types.py` | `RegimeState` enum |

The V1 import path `from src.alpha.regime...` must be rewritten to relative imports within `V2/v3_intelligence/`.

**Model storage:** The fitted `HMMGARCHRegimeDetector` must be serialized between restarts. Use `joblib.dump` / `joblib.load` to `V2/data/regime_models/{symbol}_hmm_garch.pkl`. One model file per symbol. The `OnlineRegimeFilter` is reconstructed from the loaded detector at startup; its running state (`_alpha`, `_sigma2`) cannot be persisted across restarts — warm it up with the last 500 bars of H1 returns at startup.

```python
# Startup warm-up pattern (in LiveSignalEngine.init_pair):
detector = joblib.load(f"V2/data/regime_models/{symbol}_hmm_garch.pkl")
online_filter = OnlineRegimeFilter(detector)
for r in last_500_bar_returns:
    online_filter.update(r)   # burn-in to meaningful state
```

---

## ZMQ Message Schemas (from V1 bridge, confirmed)

All messages use **MessagePack** serialization via `msgpack` library. Timestamps as int64 nanoseconds since epoch.

### Tick message (MT5 → Python, PUB :5556)
```
Frame 1: b"SYMBOL"          (UTF-8 topic prefix for ZMQ filtering)
Frame 2: msgpack({
    "ts":  int64,            # nanoseconds since epoch
    "sym": str,              # e.g. "GBPUSD"
    "bid": float,
    "ask": float,
    "bv":  float,            # bid volume (proxy only)
    "av":  float,            # ask volume (proxy only)
    "src": str               # feed identifier
})
```

### Bar message (MT5 → Python, PUB :5557)
```
Frame 1: b"SYMBOL"
Frame 2: msgpack({
    "ts":  int64,            # bar open time, nanoseconds
    "sym": str,
    "o":   float,
    "h":   float,
    "l":   float,
    "c":   float,
    "v":   float,            # tick volume
    "sp":  float             # representative spread
})
```

### Heartbeat (MT5 → Python, sent on PUB :5556 every 5 seconds)
```
Single frame: msgpack({"type": "heartbeat", "ts": int64})
```
Single frame (no topic prefix) — LinuxConsumer detects by frame count: 1 frame = heartbeat, 2 frames = tick/bar.

### OrderRequest (Python → MT5, PUSH :5558)
```
Single frame: msgpack({
    "sym":  str,             # "GBPUSD"
    "side": int,             # Side.BUY=1 / Side.SELL=-1
    "qty":  float,           # lots
    "ot":   str,             # "market" / "limit" / "stop"
    "px":   float | None,    # limit/stop price
    "sl":   float | None,    # stop-loss price (absolute, not pips)
    "tp":   float | None,    # take-profit price (absolute, not pips)
    "cmt":  str              # e.g. "swing|MEAN_REV|z=2.31|rag=0.54"
})
```

### OrderResult / Fill (MT5 → Python, PUSH :5559)
```
Single frame: msgpack({
    "oid":  str,             # broker order ticket as string
    "fp":   float,           # fill price
    "fq":   float,           # fill quantity
    "slip": float,           # price deviation from requested
    "comm": float,           # commission charged
    "ok":   bool,            # True if filled
    "err":  str              # rejection reason if ok=False
})
```

### Comment field convention (OrderRequest.cmt)
The `cmt` field is the primary audit trail. Use pipe-delimited format:
```
"{strategy}|{regime}|z={z_score:.2f}|rag={confidence:.2f}|sz={size_modifier:.2f}"
```
Example: `"swing|MEAN_REV|z=2.31|rag=0.54|sz=1.10"`

This comment propagates to `CLogger.LogTrade()` on the MT5 side and to `trade_logger.log_trade()` on the Python side, giving full traceability without a separate correlation ID.

---

## Close-Bar Detection Across Pairs and Timezones

**The problem:** H1 bars close at different wall-clock times across brokers and pairs. MT5 uses broker server time (IC Markets = UTC+3 EEST / UTC+2 EET seasonally). The Python side must not act on in-progress bars.

**The V1 solution (confirmed in `linux_consumer.py`):** The WindowsPublisher sends a Bar message only when MT5's `iTime(symbol, PERIOD_H1, 0)` changes — i.e., at the exact moment a new H1 bar opens, publishing the just-completed bar. The EA already uses this pattern via `lastBarTime[pairIndex]`.

**V2 implementation rule:** The LiveSignalEngine does NOT implement independent bar detection. It relies entirely on the Bar messages pushed by the EA. A Bar message arriving on port 5557 means: "this bar is closed, act on it." This delegates close-bar detection to MT5's own iTime mechanism, which is authoritative.

```python
# LiveSignalEngine.on_bar() — correct pattern
async def on_bar(self, bar: Bar) -> None:
    # bar.timestamp is the OPEN time of the COMPLETED bar
    # MT5 only sends this message after iTime changes
    # No additional close-bar guard needed on the Python side
    await self._dispatch(bar)
```

**Timezone normalization:** All timestamps in the bridge are int64 nanoseconds since epoch (UTC). The `bar.timestamp` is the bar open time in broker time converted to UTC nanoseconds by the EA before publishing. The Python side works entirely in UTC — no timezone conversion needed.

**Multi-pair bar coincidence:** Multiple pairs may send bars within milliseconds of each other at the top of each hour. The `LinuxConsumer` event loop processes one bar at a time (sequential async dispatch). For H1 strategies where per-bar latency is measured in minutes, this is not an issue. The `asyncio.Poller(timeout=100ms)` loop in `LinuxConsumer._receive_loop()` handles all arrivals within a single poll cycle.

**M15 scalp complication:** M15 bars close 4x per hour. The same `on_bar` callback handles both H1 and M15 bars. The router must gate by timeframe:

```python
# In LiveSignalEngine.on_bar():
bar_timeframe = infer_timeframe(bar)   # inspect bar.timestamp modulo 900s vs 3600s
if bar_timeframe == "H1":
    strategies_to_check = ["swing", "h1_scalp", "momentum"]
elif bar_timeframe == "M15":
    strategies_to_check = ["m15_scalp"]
```

The EA must publish separate Bar messages per timeframe, and the broker's symbol must be subscribed on both timeframes (subscribe to `b"GBPUSD_H1"` and `b"GBPUSD_M15"` as topic prefixes). Alternatively, publish timeframe as part of the `cmt` field and infer from timestamp interval — the latter is more robust.

---

## Build Order

The four new components have strict dependency ordering. Build in this sequence:

### Stage 1: Bridge (dependency-free foundation)
**Files:** `V2/bridge/__init__.py`, `V2/bridge/abstract.py`, `V2/bridge/message_schemas.py`, `V2/bridge/linux_consumer.py`, `V2/bridge/windows_publisher.py`

**Why first:** Every other new component depends on `OrderRequest`, `Bar`, `Tick`, and `LinuxConsumer`. These are pure ports — no new logic, just import-path rewriting.

**Porting steps:**
1. Copy V1 files, strip `from src.execution.abstract import` → `from V2.bridge.abstract import`
2. Remove `from src.execution.bridge.message_schemas import` → `from V2.bridge.message_schemas import`
3. Adjust `WindowsPublisher._order_loop()` to expose a callback for the EA-side MQL5 ZMQ library
4. Validate with a loopback test: Python PUSH → Python PULL, round-trip msgpack encode/decode

**Deliverable:** `V2/bridge/` passes a 100-round-trip loopback test at <10ms per round trip on localhost.

### Stage 2: Regime (depends on bridge abstract types only)
**Files:** `V2/v3_intelligence/regime.py`, `V2/v3_intelligence/pit.py`

**Why second:** The router needs `RegimeState` from regime.py. Regime fitting requires historical returns data from CSVs in `V2/data/` (no bridge dependency). PiT is a pure utility with no dependencies.

**Porting steps:**
1. Consolidate V1 `alpha/regime/` + `alpha/signal_types.py` into single `regime.py`
2. Rewrite imports to be self-contained (no `from src.*`)
3. Strip ArcticDB dependency from pit.py (replace `pit_read` with pandas CSV reader)
4. Write offline fitting script `V2/scripts/fit_regime_models.py` that:
   - Loads H1 data from `V2/data/` for each active pair
   - Fits `HMMGARCHRegimeDetector` on full history
   - Saves to `V2/data/regime_models/{symbol}_hmm_garch.pkl`
5. Validate: confirm `RegimeState` enum and `OnlineRegimeFilter.update()` run without errors

**Deliverable:** Regime models fitted and saved for all 8 pairs. `OnlineRegimeFilter` warm-up test passes.

### Stage 3: StrategyRouter (depends on regime.py, pair_config.py)
**Files:** `V2/v3_intelligence/strategy_router.py`

**Why third:** Router is the integration point. It requires `RegimeState` (from Stage 2) and reads `pair_config.py` (already exists). No bridge dependency — can be tested purely with synthetic bars.

**Implementation guidance:**
- `StrategyRouter` holds one `OnlineRegimeFilter` per symbol (dict keyed by symbol string)
- On `route()` call, it advances the filter, checks pair_config allow_* flags, computes z-score against the appropriate threshold, and returns a `RouteDecision`
- Must NOT cache results between bars — each call is fresh
- Regime gate: `CRISIS` always returns `None` regardless of pair_config flags

**Deliverable:** Router unit tests covering all 8 pairs × all 4 strategies × all 3 regime states = expected allow/deny outcomes.

### Stage 4: Live Signal Engine + EA modification (depends on all above)
**Files:** `V2/live/signal_engine.py`, modified `V2/ea/MultiPairEA.mq5`

**Why last:** Requires bridge (Stage 1), regime (Stage 2), router (Stage 3). The EA modification is the highest-risk change — it touches production MT5 code.

**Python LiveSignalEngine implementation guidance:**
- `asyncio`-based event loop wrapping `LinuxConsumer`
- On startup: load regime models, warm up filters, subscribe to all active symbol topics
- `on_bar()` → router → RAG → build OrderRequest → send_order
- `on_fill()` → log_trade + index_trade
- Heartbeat stale guard: if `consumer.is_stale`, suppress all order sends and log a warning

**MQL5 EA modification guidance:**
- Remove `#include "include/CMeanRevSignal.mqh"`, `CTrendSignal.mqh"`, `CHybridSignal.mqh"` from OnTimer() signal processing path
- Add `#include <Zmq/Zmq.mqh>` (from MT5's MQL5/Include, install mql5-zmq library)
- Add `Context zmq_ctx; Socket zmq_pull(zmq_ctx, ZMQ_PULL);` initialized in `OnInit()`
- Replace `ProcessPair()`'s `signalGenerator.GenerateSignal(signal)` block with `zmq_pull.recv(orderBytes)` + `ParseOrderRequest(orderBytes, entryReq)`
- Keep `CCircuitBreaker.CheckAllLimits()` and `CScalingManager.SubmitEntryWithRetry()` exactly as-is — no changes to risk layer
- The `pairConfigs[]` array and `SSymbolConfig` are still needed for ATR calculation and CLogger; do not remove them

**Deliverable:** 7-day IC Markets demo paper trade run with trade count within 20% of router backtest expectation.

---

## Patterns to Follow

### Pattern 1: Router-as-Pure-Function
**What:** `StrategyRouter.route()` takes all inputs as arguments and returns a value. It holds no mutable state except the per-symbol `OnlineRegimeFilter` instances (necessary for the forward algorithm).
**When:** Every signal dispatch call.
**Why:** Allows deterministic replay of routing decisions from logged inputs for debugging.

### Pattern 2: EA as Dumb Executor
**What:** The modified EA does not interpret OrderRequest content — it validates risk limits and submits to MT5 verbatim.
**When:** Every ZMQ order received.
**Why:** Keeps signal intelligence entirely in Python where it can be tested, replayed, and updated without recompiling MQL5.

### Pattern 3: Comment-Based Audit Trail
**What:** The `OrderRequest.comment` field carries `"{strategy}|{regime}|z={z:.2f}|rag={r:.2f}|sz={s:.2f}"`.
**When:** Every order.
**Why:** Both MT5 CLogger and Python trade_logger capture this string. No separate correlation ID infrastructure needed.

### Pattern 4: Warm-Up Before Live
**What:** `OnlineRegimeFilter` is warmed up with the last 500 bars of H1 returns at service startup before any orders are sent.
**When:** LiveSignalEngine startup sequence.
**Why:** The forward algorithm's state (`_alpha`, `_sigma2`) is meaningless at initialization (startprob_ is a flat prior). Without warm-up, the first 50-100 bars of live trading would have garbage regime predictions.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Router Bypassing the EA's Risk Layer
**What:** Sending orders directly to MT5 via Python's `MetaTrader5` library, circumventing the EA.
**Why bad:** Destroys the circuit breaker guarantee. Daily loss limits, drawdown limits, and position count checks exist in CCircuitBreaker — if bypassed, a signal bug can blow the account.
**Instead:** Always route through ZMQ → EA → CCircuitBreaker. No exceptions.

### Anti-Pattern 2: Runtime pair_config.py Mutation
**What:** Modifying `allow_swing`, `swing_z_threshold`, or size multipliers at runtime based on live P&L feedback.
**Why bad:** Creates look-ahead bias in backtests (future-aware config), makes behavior non-reproducible, and risks compounding a bad signal during a drawdown period.
**Instead:** Update pair_config.py only after a full backtest evaluation run (`backtest_evaluate_all.py`) with new data. Deploy as a config file change, restart the live service.

### Anti-Pattern 3: Polling iTime from Python
**What:** Python calling MT5's Python API (`mt5.copy_rates_from_pos`) on a timer to detect bar closes.
**Why bad:** The MT5 Python API is Windows-only, introduces a polling latency (minimum ~1 second), and creates a race condition with the EA also managing bar state.
**Instead:** Let the EA detect bar closes via `iTime()` change detection (already implemented in `lastBarTime[]` array) and push Bar messages over ZMQ. Python reacts, not polls.

### Anti-Pattern 4: Fitting HMM-GARCH on a Rolling Sliding Window Per Bar
**What:** Re-fitting the full `HMMGARCHRegimeDetector` on every new bar in the live loop.
**Why bad:** `HMMGARCHRegimeDetector.fit()` takes seconds per symbol (Gaussian HMM EM algorithm + GARCH fitting). On 8 pairs × 1-second bar events = system collapses.
**Instead:** Fit offline weekly or on-demand. Use `OnlineRegimeFilter` for per-bar updates — it runs in microseconds per bar.

### Anti-Pattern 5: Storing Regime Model State in Memory Only
**What:** Fitting the `HMMGARCHRegimeDetector` once at startup and losing the fit on service restart.
**Why bad:** HMM convergence is stochastic (seed-dependent). Different restarts may produce different state orderings, making the router non-deterministic.
**Instead:** Serialize fitted models to `V2/data/regime_models/{symbol}_hmm_garch.pkl` immediately after fitting. Live service loads from disk; only re-fits when explicitly triggered.

---

## Coupling Risks

### Risk 1: EA MQL5 ZMQ Library Compatibility
**Description:** The MT5 EA needs a ZMQ binding for MQL5. The standard option is `mql5-zmq` (GitHub: dingmaotu/mql5-zmq). This library wraps libzmq.dll and must be present in `MT5/MQL5/Libraries/`. It is not part of the standard MT5 installation.
**Severity:** HIGH — blocks the entire bridge integration if the DLL is missing or version-mismatched.
**Mitigation:** Verify `mql5-zmq` compiles and connects on the IC Markets demo MT5 instance before writing any router logic. This is a go/no-go gate for Stage 4.

### Risk 2: pair_config.py as Shared Truth with Backtest
**Description:** `pair_config.py` is read by: (1) `StrategyRouter` at runtime, (2) `backtest_evaluate_all.py` during evaluation, (3) potentially by future analytics. It is a single file that both live and backtest components depend on.
**Severity:** MEDIUM — if pair_config is updated for live trading and the backtest is re-run, the new backtest uses updated params, creating a data point that appears to validate a param that was chosen with forward-looking knowledge.
**Mitigation:** Treat pair_config.py as a versioned config. When updating, create `pair_config_YYYYMMDD.py` as an archive before modifying. The decision_log table in `trade_logger` should record every pair_config change with rationale.

### Risk 3: OnlineRegimeFilter Warm-Up Drift
**Description:** When the live service restarts after a gap (e.g., weekend), the warm-up feed uses the last 500 bars from disk. If the bars on disk are stale (data pipeline not running), the filter warms up on old data and may misclassify regime on the first live bar.
**Severity:** MEDIUM — misclassified regime on first bar means wrong strategy dispatched, potentially wrong direction.
**Mitigation:** Warm-up script should fetch fresh bars from MT5 via ZMQ bar subscription, replaying them before enabling order dispatch. Add a `warmup_complete: bool` flag to LiveSignalEngine; suppress all order sends until warm-up is complete.

### Risk 4: Tick-Level Bar Aggregation Mismatch
**Description:** The EA sends bars on `iTime()` change (MT5 broker time). The Python side receives these and routes. If the EA has a bug where it sends a bar before the H1 bar closes (e.g., on server reconnect, it re-publishes the current incomplete bar), Python will act on a mid-bar signal.
**Severity:** MEDIUM — would generate signals on incomplete bars, violating PiT discipline.
**Mitigation:** Include `"complete": True` in the Bar message schema. EA sets `"complete": True` only when it detects `iTime()` change (bar rollover), never on tick updates. Python discards any bar where `complete != True`.

### Risk 5: RAG Cold-Start on Fresh Deployment
**Description:** `RAGSignalFilter` returns `{"action": "TAKE", "confidence": 0.5}` when `count < 5` (insufficient history). On a fresh deployment before 5 trades are indexed, all signals pass through at default confidence.
**Severity:** LOW — existing backtest has ~500 indexed trades already. Only a risk if ChromaDB is wiped.
**Mitigation:** Pre-populate ChromaDB from the backtest trades DataFrame on deployment using `rag.index_trades(trades_df)`. Document this as a required deployment step.

### Risk 6: Windows vs Linux Deployment Split
**Description:** `WindowsPublisher` runs on the Windows MT5 machine. `LinuxConsumer`, `StrategyRouter`, `LiveSignalEngine` run on Linux. Code that imports from both sides in the same process will fail.
**Severity:** LOW — already handled correctly in V1 by the split consumer/publisher architecture.
**Mitigation:** Enforce the split explicitly in the `V2/bridge/__init__.py` documentation. `LinuxConsumer` must never be imported on Windows; `WindowsPublisher` must never be imported on Linux (or import conditionally with platform check). For local dev/test, both can run on the same machine using `tcp://127.0.0.1` instead of the WireGuard VPN address.

---

## Scalability Considerations

This is a single-account system targeting $1,000 capital. Scalability here means operational reliability, not load capacity.

| Concern | Current Scale (8 pairs, 1 account) | Action Needed |
|---------|-------------------------------------|---------------|
| Bar processing latency | <1ms per bar (pure Python, no DB write on signal) | None |
| OrderRequest queue depth | 1 order per pair max (circuit breaker enforces) | None |
| Regime model refit frequency | Weekly offline | Schedule via cron; restart live service after |
| ChromaDB index size | ~500 trades, grows ~5/week | None for years |
| SQLite trade log | ~500 rows, grows ~5/week | None for years |
| ZMQ socket count | 4 sockets per bridge instance | None |

---

## Sources

- Direct inspection of `V1/helix/src/execution/bridge/linux_consumer.py` — ZMQ socket architecture, reconnect logic, stale detection
- Direct inspection of `V1/helix/src/execution/bridge/windows_publisher.py` — port bindings, heartbeat interval, order loop
- Direct inspection of `V1/helix/src/execution/bridge/message_schemas.py` — full msgpack schema for all 5 message types
- Direct inspection of `V1/helix/src/execution/abstract.py` — OrderRequest, OrderResult, Tick, Bar, Side, OrderType dataclasses
- Direct inspection of `V1/helix/src/alpha/regime/hmm_garch.py` — HMMGARCHRegimeDetector API, state ordering convention
- Direct inspection of `V1/helix/src/alpha/regime/online_filter.py` — OnlineRegimeFilter forward algorithm, warm-up behavior
- Direct inspection of `V1/helix/src/alpha/signal_types.py` — RegimeState enum values (TRENDING=0, MEAN_REVERTING=1, CRISIS=2)
- Direct inspection of `V1/helix/src/data/pit_manager.py` — PiT compliance implementation, ArcticDB dependency
- Direct inspection of `V2/v3_intelligence/pair_config.py` — PairConfig dataclass, all 8 pairs, allow_* flags, size multipliers
- Direct inspection of `V2/ea/MultiPairEA.mq5` — EA structure, CCircuitBreaker usage, lastBarTime[] bar detection, signal generator architecture
- Direct inspection of `V2/v3_intelligence/rag_signal_filter.py` — score_signal() interface, confidence thresholds, action values
- Direct inspection of `V2/v3_intelligence/trade_logger.py` — SQLite schema, log_trade() interface
- Confidence: HIGH — all claims derived from direct file inspection, not inference
