# Phase 9: Strategy Router - Research

**Researched:** 2026-04-28
**Domain:** Adaptive multi-strategy router (Python, dataclass-based dispatch, PiT-safe simulation)
**Confidence:** HIGH (all upstream APIs read directly from disk; one MEDIUM gap noted)

## Summary

`StrategyRouter` is a thin, stateful orchestration layer that composes four already-built upstream gates (regime, session, 4yr matrix, RAG) into a single typed `route(pair, ts, market_data) -> RouteDecision | None` call, with two cross-cutting policies layered on top: ROUT-02 swing-first priority and ROUT-03 same-pair direction conflict rejection. The phase ships almost no new mathematics — it is a contract phase. The only new computation is the ROUT-04 4yr portfolio simulator, which composes existing per-strategy backtest loops (`_run_scalp_loop`, `_run_momentum_loop`, `_backtest_swing_symbol`, `_backtest_m15_symbol`) under a single PitClock and a shared `InMemoryPositionStore`.

All four upstream gates are landed and tested. Phase 8 produced 5 detector JSONs (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP) and `OnlineRegimeFilter`/`load_detector` APIs. Phase 8.5 produced `is_tradeable_session()` and `is_blackout_window()` predicates. Phase 7 produced `pair_config.PAIR_CONFIGS` with per-strategy enable flags and embedded 4yr Sharpe numbers. `RAGSignalFilter.score_signal()` ships a fully-formed dict-returning API with per-pair-strategy-session-z queries.

**Primary recommendation:** Slice this phase as a 4-plan job — Wave 0 RED scaffold (P01) → router core + position store (P02) → detector inventory expansion to 8 pairs (P03) → 4yr simulation harness + ROUT-04 gate (P04). Lift two new abstractions only: `RouteDecision`/`OpenPosition` frozen dataclasses, and the `PositionStore` Protocol. Augment `OnlineRegimeFilter` with one additional method (`current_state_prob()`) that exposes the existing forward variable as a typed (state, confidence) pair without recomputation — this is the only gap between Phase 8's API and CONTEXT D-04's `regime_confidence` formula.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Router signature & return shape (D-01..D-04):**
- D-01: `route(pair: str, timestamp: datetime, market_data: BarSnapshot) -> RouteDecision | None`. `RouteDecision` is `@dataclass(frozen=True)` in `V2/v3_intelligence/router.py`. Fields: `strategy: Strategy` enum (M15_SCALP / H1_SCALP / H1_MOMENTUM / DAILY_SWING), `direction: Direction` enum (LONG / SHORT), `confidence: float` (0.0–1.0), `size_mult: float` (multiplier on pair_config base, capped at 1.0).
- D-02: `None` return collapses {regime-blocked, session-blocked, matrix-fail, RAG-below-threshold, direction-conflict, no-signal} to a single sentinel; structured `logging` at DEBUG with `gate_blocked` / `dispatched` records.
- D-03: `confidence` field = RAG score directly.
- D-04: `size_mult` = `pair_config[pair].position_size_mult * regime_confidence`, capped at 1.0; `regime_confidence` = HMM posterior of current state from `OnlineRegimeFilter.current_state_prob()`.

**Decision chain (D-05..D-08):**
- D-05: Gate order **Regime → Session → Matrix → RAG** (cheapest first).
- D-06: Short-circuit on first fail; one log record per blocked dispatch.
- D-07: Per-strategy iteration: Daily swing first, then H1 scalp, H1 momentum, M15 scalp.
- D-08: Tie-break on multiple intraday strategies = highest 4yr Sharpe from `pair_config.py`.

**Position state (D-09..D-12):**
- D-09: Injected `PositionStore` protocol with `open_positions(pair) -> list[OpenPosition]`. Two adapters: `InMemoryPositionStore` (backtest), `ZmqPositionStore` (live skeleton, Phase 10 wires).
- D-10: Direction conflict pair-level only (strategy-agnostic).
- D-11: Stateful instance, all deps injected at construction. No globals.
- D-12: Module location `V2/v3_intelligence/router.py`.

**4yr simulation (D-13..D-16):**
- D-13: Equal-per-dispatch capital allocation.
- D-14: 4yr-fit single-pass detectors (no walk-forward).
- D-15: Strict ROUT-03 reject (no replay queue).
- D-16: Sharpe baseline = aggregate router ≥ best single per-pair Sharpe + 0.2.

**Test scaffold & sim location (D-17..D-18):**
- D-17: Wave 0 RED scaffold lands first (mirrors Phase 7/8/8.4/8.5 P01 pattern); `V2/tests/v3_intelligence/test_router.py` with 8 RED tests.
- D-18: Sim at `V2/backtest/router_simulation.py` (NEW); `backtest_hybrid.py` untouched.

**Detector inventory (D-19):**
- D-19: Phase 8 has 5 detectors (USDJPY/GBPJPY/GBPAUD/GBPUSD/EURGBP); Phase 9 P03 adds GBPNZD/EURUSD/AUDNZD before ROUT-04.

**Phase 10 contract (D-20):**
- D-20: `LiveSignalEngine` instantiates `StrategyRouter` once at startup with detector JSONs + `RAGSignalFilter` + `ZmqPositionStore` + `pair_config`; on bar-close calls `router.route()`; if non-None packs into `OrderRequest`.

### Claude's Discretion

- Wave/plan ordering within these locked decisions (researcher recommends 4-plan slice; see §11)
- Router-internal logging schema (CONTEXT only specifies "gate_blocked" / "dispatched" record types); recommend stable JSON keys
- `OnlineRegimeFilter.current_state_prob()` shape — D-04 names it but doesn't specify return type. Recommend `tuple[RegimeState, float]` mirroring existing `update()` return contract
- Tie-break source — D-08 says "highest 4yr Sharpe from pair_config.py" but the Sharpes are in the docstring/notes prose, not as typed fields. Recommend lifting them to a typed dict (see §3 below)

### Deferred Ideas (OUT OF SCOPE)

- Sharpe-weighted or Kelly-fractional sizing (v3.0 EXPN-04)
- Walk-forward detector refits (v3.0 EXPN-03)
- Concurrent signal queueing
- Strategy-level direction conflict (kept pair-level)
- Live ZMQ position store implementation (Phase 10)
- Grafana router dashboard (v3.0 MONI-01)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUT-01 | `StrategyRouter.route(pair, ts, market_data) -> RouteDecision \| None` via 4-gate chain | §1 OnlineRegimeFilter API, §2 temporal_filters, §3 pair_config matrix, §4 RAGSignalFilter; all four gates already shipped |
| ROUT-02 | Swing-first priority — daily swing fires whenever conditions met; intraday strategies only when no swing position open | §6 PositionStore in-memory adapter; D-07 iteration order; per-pair check via `position_store.open_positions(pair)` filtered by `strategy == DAILY_SWING` |
| ROUT-03 | Reject if opposite-direction position open on same pair | §6 PositionStore + frozen `OpenPosition` dataclass; pair-level scope (D-10) |
| ROUT-04 | 4yr simulation: aggregate Sharpe ≥ max single Sharpe + 0.2 | §5 PiT simulation pattern, §6 trade_logger/learning_loop integration, §7 detector inventory expansion to 8 pairs |

---

## 1. Phase 8 OnlineRegimeFilter API surface

Source: [V2/v3_intelligence/regime/online_filter.py](../../../V2/v3_intelligence/regime/online_filter.py)

### Construction signature (line 50)

```python
def __init__(self, detector: HMMGARCHRegimeDetector) -> None
```
- Takes a fitted `HMMGARCHRegimeDetector`; raises `RuntimeError` if not `is_fitted`.
- Initialises forward variable α from `detector.startprob_` and per-state σ² from `detector.garch_params[*].unconditional_variance`.

### Public API the router calls

| Method/property | Signature | Use in router |
|---|---|---|
| `update(return_value: float) -> tuple[RegimeState, float]` | line 75 | Called by router on every bar with the bar's log return; returns `(current_regime, confidence)` |
| `state_probs` (property) | line 142, returns `np.ndarray` shape `(n_states,)` | Returns the full posterior over `[TRENDING, MEAN_REVERTING, CRISIS]` (variance-rank ordered per REGM-02). `confidence` field of `RouteDecision` derives from this. |
| `reset() -> None` | line 134 | Re-init filter; not called in the steady-state router loop, but useful in simulator setup |

### CRITICAL gap — `current_state_prob()` does NOT exist (MEDIUM confidence)

CONTEXT D-04 specifies:
> `regime_confidence` is the HMM posterior probability of the current state from `OnlineRegimeFilter.current_state_prob()`.

**This method does not exist on the class today.** The information is fully available via `state_probs` (the `_alpha` array) plus the `(regime, confidence)` tuple returned by the most-recent `update()` call, but no convenience accessor wraps "give me the posterior of the *current* (argmax) state without re-updating."

**Two options for Phase 9:**

1. **Add `current_state_prob() -> tuple[RegimeState, float]` to `OnlineRegimeFilter`** (recommended — single 5-line addition):
   ```python
   def current_state_prob(self) -> tuple[RegimeState, float]:
       """Return current (argmax_state, posterior) without advancing the filter."""
       best_state = int(np.argmax(self._alpha))
       return RegimeState(best_state), float(self._alpha[best_state])
   ```
   Mirrors the return shape of `update()` exactly. No new fields; reads existing `_alpha`.

2. **Inline the equivalent in router code** using `state_probs` — but this puts argmax logic in the router, duplicating what `update()` already computes internally and breaking the encapsulation boundary that Phase 8 was careful to draw.

Recommend Option 1. Touchpoint: `online_filter.py` lines 142–145 already expose `state_probs`; `current_state_prob()` slots in directly above or below.

### How the router consumes the regime gate

The router cannot blindly call `update()` from `route()` because that mutates filter state and the simulator's PiT loop must control bar advancement deterministically. **Pattern:**

```python
# In simulator: advance the per-pair filter once per bar
regime_state, regime_conf = filters[pair].update(log_return_t)

# Then in router.route(...): just READ the current state
state, prob = filters[pair].current_state_prob()
if state == RegimeState.CRISIS:
    return None  # gate 1 fail (or a configurable allow-list per CONTEXT)
```

CONTEXT D-04 says `size_mult = pair_config[pair].position_size_mult * regime_confidence`. Note: `PairConfig` does NOT have a field named `position_size_mult` — it has per-strategy sizing (`swing_size_mult`, `scalp_size_mult`, `momentum_size_mult`, `m15_size_mult`). The router must pick the per-strategy field that matches the dispatched strategy. This is a **CONTEXT-prose imprecision** the planner needs to resolve into a typed lookup; see §3.

### Memory footprint

Each detector JSON is 66 lines (~2 KB). Each in-memory `OnlineRegimeFilter` carries: `_alpha` (3 floats), `_sigma2` (3 floats), the underlying `HMMGARCHRegimeDetector` (3×4 GARCH params + 3×3 transition matrix + 3 startprob = ~30 floats). Per-pair overhead is well under 1 KB. **8 pairs × 1 KB = trivial; the live engine starts up in milliseconds.**

---

## 2. Phase 8.5 temporal_filters surface

Source: [V2/v3_intelligence/temporal_filters.py](../../../V2/v3_intelligence/temporal_filters.py)

### Public predicates (lines 79, 111)

```python
def is_tradeable_session(
    pair: str,
    strategy: str,
    timeframe: str,
    ts: datetime,
) -> bool

def is_blackout_window(ts: datetime) -> bool
```

### Argument contracts

| Param | Type | Convention | Router behaviour |
|---|---|---|---|
| `pair` | `str` | 6-char ticker, e.g. `"USDJPY"` | Pass `pair` argument verbatim |
| `strategy` | `str` | Plan 05 emits names matching `pair_config` enable flag stems: `"swing"`, `"scalp"`, `"momentum"`, `"m15_scalp"` (lowercase strings, NOT enum values) | Router maps `Strategy` enum → string before calling. **Important** — confirm exact strings Plan 05 uses; current `session_config.py` is a SEED with empty `SESSION_RULES`, so the contract is documented but not yet exercised on real keys. |
| `timeframe` | `str` | Per CONTEXT D-06 / matches Phase 8.4 cache convention: `"M15"`, `"H1"`, `"H4"`, `"DAILY"` | Router passes per-strategy timeframe: SWING=DAILY, H1_SCALP=H1, H1_MOMENTUM=H1, M15_SCALP=M15 |
| `ts` | `datetime` (UTC) | `_pair_currencies` and pattern matchers all assume UTC; tz-aware safer | Router receives `ts` from caller (simulator advances bar-by-bar; live engine reads from MT5 bar-close event) |

### Return semantics

- `is_tradeable_session()` returns `True` for the default case (no rule registered for that `(pair, strategy, timeframe)` triple). This is **important**: a missing key is permissive, not restrictive. Router treats `False` as a hard veto, `True` as "permit, but other gates may still reject."
- `is_blackout_window()` is a global ts-only filter (currency-agnostic). CONTEXT D-05 only lists Session as gate 2; the `is_blackout_window()` check is implicitly *inside* `is_tradeable_session()` via the `BLACKOUT_PATTERNS` loop (line 102–107 — patterns with `affects` matching pair currencies). The router does NOT need a separate gate call.

### Decision points the planner must resolve

1. **`SESSION_RULES` is currently empty** (seed). Phase 8.5 SESS-04 is "Complete (structural)" but the full-corpus phase-gate run requires `SUPABASE_DB_URL`. Until that runs, Plan 05's seeded `SESSION_RULES = {}` means `is_tradeable_session()` returns `True` for every input. The router's gate 2 will be a no-op against the seed config — but this is acceptable: the API contract is honored, and once `SUPABASE_DB_URL` lands and Phase 8.5 P03–P05 are re-run, `SESSION_RULES` populates and the gate goes live with no router changes needed.

2. **Strategy string convention**: P02 of this phase needs a small Strategy-enum → session-string mapping. Recommend:
   ```python
   _STRATEGY_TO_SESSION_KEY = {
       Strategy.DAILY_SWING:   ("swing",     "DAILY"),
       Strategy.H1_SCALP:      ("scalp",     "H1"),
       Strategy.H1_MOMENTUM:   ("momentum",  "H1"),
       Strategy.M15_SCALP:     ("m15_scalp", "M15"),
   }
   ```

---

## 3. Phase 7 pair_config matrix shape + thresholds

Source: [V2/v3_intelligence/pair_config.py](../../../V2/v3_intelligence/pair_config.py)

### Actual shape

`PAIR_CONFIGS: dict[str, PairConfig]` — 8 keys, one per active pair. `PairConfig` is a `@dataclass` (NOT frozen — line 34) with these strategy-relevant fields:

| Field | Per strategy | Used by router |
|---|---|---|
| `allow_swing: bool` | swing | gate 3 enable check |
| `allow_scalp: bool` | H1 scalp | gate 3 enable check |
| `allow_momentum: bool` | H1 momentum | gate 3 enable check |
| `allow_m15_scalp: bool` | M15 scalp | gate 3 enable check |
| `swing_size_mult: float` | swing | size_mult numerator |
| `scalp_size_mult: float` | H1 scalp | size_mult numerator |
| `momentum_size_mult: float` | H1 momentum | size_mult numerator |
| `m15_size_mult: float` | M15 scalp | size_mult numerator |

### CRITICAL — 4yr Sharpe is NOT a typed field

The 4yr Sharpe numbers are **embedded in the `notes` prose strings AND in the `print_pair_summary` function's hardcoded `sharpes` dict (lines 213-222)**. There is no typed `sharpe_4yr` field on `PairConfig`.

The `sharpes` dict at line 213 IS canonical:

```python
sharpes = {
    'USDJPY': (3.09, -2.34, -1.61, 0.93),    # (swing, scalp, momentum, m15)
    'GBPJPY': (1.93,  0.85,  0.21, -0.02),
    'GBPAUD': (1.86, -0.61, -0.11, 1.08),
    'GBPUSD': (1.05, -0.15,  1.00, 2.60),
    'EURGBP': (0.45,  1.32,  1.57, 1.86),
    'GBPNZD': (-0.34, 0.66, -1.23, 3.65),    # (08.4-03 4yr correction: scalp 0.66)
    'EURUSD': (-0.20, -0.17, -1.03, 2.62),
    'AUDNZD': (-2.16, 1.63,  0.55, 2.19),
}
```

### Matrix threshold — `MIN_SHARPE`

CONTEXT D-05 says "matrix is `pair_config[pair][strategy].sharpe_4yr >= threshold`" — implying a numeric threshold. Phase 7 [V2/backtest/backtest_4yr_evaluate.py](../../../V2/backtest/backtest_4yr_evaluate.py) line 37 sets:

```python
SHARPE_THRESHOLD = 0.5    # D-10
MIN_TRADE_COUNT  = 30     # Open Questions #2
```

But `pair_config.allow_*` flags **already encode** this gate — they were flipped True/False after Phase 7 ran the 0.5 threshold check. **The router does NOT need to re-check Sharpe at runtime; checking `allow_*` flags is equivalent and simpler.**

### Gate 3 (Matrix) recommended implementation

```python
def _matrix_passes(self, pair: str, strategy: Strategy) -> bool:
    cfg = self.pair_config[pair]
    return {
        Strategy.DAILY_SWING: cfg.allow_swing,
        Strategy.H1_SCALP:    cfg.allow_scalp,
        Strategy.H1_MOMENTUM: cfg.allow_momentum,
        Strategy.M15_SCALP:   cfg.allow_m15_scalp,
    }[strategy]
```

### D-08 tie-break — recommendation

The planner should **lift the `print_pair_summary` `sharpes` dict to a module-level constant** so the router's tie-break (D-08) can reference it without parsing the docstring `notes`. Proposed:

```python
# pair_config.py — new module constant
SHARPE_4YR: dict[str, dict[str, float]] = {
    "USDJPY": {"swing": 3.09, "h1_scalp": -2.34, "h1_momentum": -1.61, "m15_scalp": 0.93},
    # ... etc
}
```

### Size multiplier fix (CONTEXT D-04 prose imprecision)

CONTEXT D-04 says `size_mult = pair_config[pair].position_size_mult * regime_confidence`. There is no `position_size_mult` field. The router must select the per-strategy field by dispatched strategy:

```python
_SIZE_MULT_FIELD = {
    Strategy.DAILY_SWING:  "swing_size_mult",
    Strategy.H1_SCALP:     "scalp_size_mult",
    Strategy.H1_MOMENTUM:  "momentum_size_mult",
    Strategy.M15_SCALP:    "m15_size_mult",
}
size_mult = min(1.0, getattr(cfg, _SIZE_MULT_FIELD[strategy]) * regime_confidence)
```

---

## 4. RAGSignalFilter.score_signal API + threshold convention

Source: [V2/v3_intelligence/rag_signal_filter.py](../../../V2/v3_intelligence/rag_signal_filter.py)

### Signature (line 122)

```python
def score_signal(
    self,
    symbol: str,
    strategy_type: str,        # "M15_SCALP_LONG" / "DAILY_SWING_SHORT" / etc.
    session: str,              # "LONDON" / "NY" / "OFF"
    daily_z: float,
    h1_z: float,
    vol_percentile: float,
    hour_utc: int,
    k: int = 15,
    min_samples: int = 5,
) -> dict:
```

### Return shape

```python
{
    "confidence":    float,    # 0.0–1.0 — historical win-rate of similar trades (the gate value)
    "sample_size":   int,      # how many similar trades found
    "avg_pnl":       float,
    "size_modifier": float,    # 0.5–1.2 — caller-applicable (router does NOT use this for size_mult per D-04)
    "action":        str,      # "TAKE" | "REDUCE" | "SKIP"
    "reason":        str,
}
```

### Threshold for "passes RAG gate"

The `action` field encodes the threshold logic Phase 7 backtest uses:

| Confidence | Action | Router behaviour |
|---|---|---|
| ≥ 0.38 | `TAKE` | gate 4 passes |
| ≥ 0.28 (and < 0.38) | `REDUCE` | gate 4 passes (CONTEXT does not split TAKE/REDUCE; D-03 says confidence is passed through verbatim) |
| < 0.28 | `SKIP` | gate 4 FAILS — return None |

**Cold-start path** (line 144): when `self._col.count() < min_samples` (5), returns `confidence=0.5, action="TAKE"` — meaning a fresh ChromaDB lets every signal through with 0.5 confidence. **This is acceptable for the live engine cold start but creates a confidence-inflation risk in the ROUT-04 simulation if the simulator runs against an empty Chroma collection.** Recommend: ROUT-04 simulator pre-warms Chroma with the first ~6 months of synthetic dispatches (or runs `learning_loop.on_trade_close()` as it goes — see §6).

### Recommended router gate 4 implementation

```python
def _rag_score(self, pair, strategy, ts, market_data) -> float:
    direction = "LONG" if market_data.h1_z < 0 else "SHORT"
    rag_strategy_type = f"{strategy.name}_{direction}"  # "M15_SCALP_LONG"
    result = self.rag.score_signal(
        symbol=pair,
        strategy_type=rag_strategy_type,
        session=_session(ts.hour),                  # reuse backtest_hybrid._session
        daily_z=market_data.daily_z,
        h1_z=market_data.h1_z,
        vol_percentile=market_data.vol_percentile,
        hour_utc=ts.hour,
    )
    return result["confidence"] if result["action"] != "SKIP" else 0.0
```

### `BarSnapshot` shape

CONTEXT D-01 names the `market_data` parameter `BarSnapshot` but no such type exists yet. RAGSignalFilter wants `daily_z`, `h1_z`, `vol_percentile`, `hour_utc`, plus the bar `Close` for log-return into `OnlineRegimeFilter.update()`. Recommend a minimal frozen dataclass:

```python
@dataclass(frozen=True)
class BarSnapshot:
    pair:           str
    timestamp:      datetime
    close:          float
    log_return:     float        # for OnlineRegimeFilter.update()
    daily_z:        float
    h1_z:           float
    vol_percentile: float
```

The simulator builds these per bar from the cached H1/M15/Daily DataFrames; the live engine builds these from the ZMQ bar-close event + cache lookback.

---

## 5. PiT simulation pattern (precedents)

Source citations:
- [V2/backtest/backtest_hybrid.py](../../../V2/backtest/backtest_hybrid.py) — per-pair-per-strategy backtest harness
- [V2/backtest/backtest_4yr_evaluate.py](../../../V2/backtest/backtest_4yr_evaluate.py) — 4yr Sharpe runner (the closest precedent)
- [V2/backtest/pit_validator.py](../../../V2/backtest/pit_validator.py) — AST-based PiT compliance checker
- [V2/v3_intelligence/pit.py](../../../V2/v3_intelligence/pit.py) — `PitClock` + `pit_active()`

### The Phase 7 4yr loop pattern (`backtest_4yr_evaluate.py`)

The harness loads each pair's `_H1_4yr.csv` once into a DataFrame, computes ALL indicator columns vectorized **before** the loop, then iterates `for i in range(100, len(h1) - 1)` — starting at bar 100 to give indicators their warmup. Every iteration:

```python
row      = h1.iloc[i]
next_row = h1.iloc[i + 1]   # BKTS-01 next-bar-open fill
ts       = h1.index[i]
# ... read row['Close'], row['z_score'], row['atr'] ...
# entry_px = next_row['Open']  ← THIS is the BKTS-01 fix
```

Vectorised pre-loop indicator computation does NOT violate PiT — the `pit_validator.py` AST checker explicitly whitelists `df['atr'] = self.adaptive_atr(df['High'], df['Low'], df['Close'])` (line 231 `_is_indicator_computation`). The validator catches in-loop bias only.

### How the router simulator must wrap PiT

```python
# V2/backtest/router_simulation.py (NEW per D-18)
from v3_intelligence.pit import PitClock
from v3_intelligence.regime import load_detector, OnlineRegimeFilter

# Pre-load ALL detectors once
filters = {
    pair: OnlineRegimeFilter(load_detector(f"V2/data/regime/{pair}_detector.json"))
    for pair in PAIR_CONFIGS  # 8 pairs after P03
}

# Pre-load ALL 4yr H1 CSVs once
h1_data = {pair: pd.read_csv(f"V2/data/{pair}_H1_4yr.csv", index_col=0, parse_dates=True)
           for pair in PAIR_CONFIGS}

# Iterate the unified time index
all_timestamps = sorted(set().union(*[df.index for df in h1_data.values()]))

router  = StrategyRouter(filters, rag, position_store, PAIR_CONFIGS)
sim_log = []
end_ts  = pd.Timestamp(all_timestamps[-1])

with PitClock(end_ts) as clock:        # PiT wrap — Phase 8 D-25 honored
    for ts in all_timestamps:
        clock.advance(pd.Timestamp(ts))
        for pair, df in h1_data.items():
            if ts not in df.index:
                continue
            # Advance the per-pair regime filter (mutating call)
            log_return = compute_log_return(df, ts)
            filters[pair].update(log_return)
            # Build snapshot, dispatch
            snapshot = build_snapshot(pair, ts, df)
            decision = router.route(pair, ts, snapshot)
            if decision is not None:
                sim_log.append((ts, pair, decision))
                position_store.open(pair, decision, ts)
            # Apply exits (target/stop/timeout) for any open positions on this pair
            position_store.tick_exits(pair, ts, df.loc[ts])
```

### Critical — auto-pull is REFUSED inside PitClock

[cache.py line 99](../../../V2/v3_intelligence/cache.py) checks `is_pit_active()` and raises `FutureBarReadError` instead of calling `_auto_pull` when inside a PitClock with-block. **The simulator MUST pre-warm the cache before entering PiT** (or, simpler: read directly from the CSVs, as `backtest_4yr_evaluate.py` does). CONTEXT instructs: "router does NOT call cache directly" — caller (simulator/LiveSignalEngine) provides the snapshot, so this constraint is naturally satisfied.

### `PitClock.advance()` is monotone

Line 75–85 of `pit.py`: `advance(new_ts)` raises `ValueError` if `new_ts < self._as_of`. The simulator's bar iterator must be sorted. CSV indices are already monotone time-ordered; no extra sort needed if iterating one CSV at a time, but the cross-pair unified iteration above MUST sort the union of timestamps.

### `pit_validator.py` gate (BKTS-04) for the new sim file

CONTEXT does NOT require this, but Phase 7 BKTS-04 established the pattern: any new file under `V2/backtest/` must pass `python -m backtest.pit_validator V2/backtest/router_simulation.py`. The validator whitelists `next_row['Open']` and indicator-arg patterns, so as long as the simulator follows the `backtest_4yr_evaluate.py` shape (next-bar-open fill, vectorised pre-loop indicators), it will pass.

---

## 6. trade_logger + learning_loop integration points

Source citations:
- [V2/v3_intelligence/learning_loop.py](../../../V2/v3_intelligence/learning_loop.py) line 54 — `on_trade_close(trade, *, logger=None, rag=None)`
- [V2/v3_intelligence/trade_logger.py](../../../V2/v3_intelligence/trade_logger.py) line 86 — `log_trade(trade)`
- [V2/backtest/backtest_hybrid.py](../../../V2/backtest/backtest_hybrid.py) lines 264–275 — swing exit calls `on_trade_close(rec)`; line 419 — m15 exit also

### The trade dict contract

Lines 11–17 of `learning_loop.py` document the required keys:

```
Required: symbol, type|strategy_type, entry_date, exit_date, entry_price,
          exit_price, pnl_pct, bars_held, exit_reason, session, hour_utc
Optional: direction, daily_z, h1_z, h1_atr, vol_percentile, size, regime, notes
For decision_log diff: params_json (JSON-string)
```

### Three things `on_trade_close` does synchronously (lines 65–80)

1. `logger.log_trade(trade)` — appends to SQLite `trades` table
2. `_maybe_log_param_diff(trade, log)` — writes `decision_log` row if `params_json` differs from previous trade for same `(symbol, strategy_type)`
3. `rag.index_trade(trade)` — upserts ChromaDB `trade_memory` collection

The function takes optional injected `logger` and `rag` params (line 56–58) so the router simulator can pass mocks (or pass a different SQLite DB to keep simulation runs isolated from live `marketmind.db`).

### Router simulator integration pattern

Recommend the simulator's exit-handler emit trade dicts in the same shape `backtest_hybrid.py` uses (lines 244–263 for swing, lines 389–408 for m15) — including the `params_json` snapshot (lines 268–273). This preserves the RAG learning loop **during** the 4yr simulation, so by the time the simulator finishes, ChromaDB has 4 years of dispatched-trade history to score against. **Without this, the RAG gate is cold-start (returns 0.5 confidence) for the entire run.**

```python
# In V2/backtest/router_simulation.py
def _close_position(self, position, exit_ts, exit_px, exit_reason):
    rec = {
        "symbol":        position.pair,
        "type":          f"{position.strategy.name}_{position.direction.name}",
        "strategy_type": position.strategy.name,
        "direction":     position.direction.name,
        "entry_date":    position.opened_at,
        "exit_date":     exit_ts,
        "entry_price":   position.entry_px,
        "exit_price":    exit_px,
        "pnl_pct":       (exit_px - position.entry_px) / position.entry_px * (1 if position.direction == Direction.LONG else -1),
        "bars_held":     ...,
        "session":       _session(exit_ts.hour),
        "hour_utc":      position.opened_at.hour,
        "exit_reason":   exit_reason,
        "size":          position.size_mult,
        "daily_z":       position.daily_z_at_entry,
        "h1_z":          position.h1_z_at_entry,
        "vol_percentile": position.vol_pct_at_entry,
        "params_json":   json.dumps({"size_mult": position.size_mult, "confidence": position.confidence}),
    }
    on_trade_close(rec)
    self.trades.append(rec)
```

### Optional — isolate sim DB from live DB

`TradeLogger.__init__` accepts `db_path` (line 19). Recommend the simulator construct a fresh logger:

```python
sim_db = Path("V2/reports/router_simulation_trades.db")
sim_db.unlink(missing_ok=True)
sim_logger = TradeLogger(db_path=sim_db)
on_trade_close(rec, logger=sim_logger)  # don't pollute marketmind.db
```

Same for RAG: `RAGSignalFilter(collection="router_sim_trades")` to keep the simulation's ChromaDB upserts in a separate collection. Or accept that the sim writes to the production collection — Phase 8.4 INFRA-03 already wired backtest_hybrid to `trade_memory`, and ChromaDB upserts are idempotent on `doc_id`. **Recommend: separate collection** so the live engine's confidence numbers don't get inflated by simulation history.

---

## 7. Detector inventory expansion strategy

Source: [V2/scripts/fit_regime_detectors.py](../../../V2/scripts/fit_regime_detectors.py)

### Current state on disk

```
V2/data/regime/
  USDJPY_detector.json    (66 lines, ~2 KB, fitted 2026-04-25, v1_parity_tested=true)
  GBPJPY_detector.json
  GBPAUD_detector.json
  GBPUSD_detector.json
  EURGBP_detector.json
```

### What Phase 9 must add (D-19)

```
V2/data/regime/
  GBPNZD_detector.json    (NEW)
  EURUSD_detector.json    (NEW)
  AUDNZD_detector.json    (NEW)
```

### Required source data

| Pair | 4yr H1 CSV | Status |
|---|---|---|
| GBPNZD | `V2/data/GBPNZD_H1_4yr.csv` | EXISTS (Phase 8.4 INFRA-02) |
| EURUSD | `V2/data/EURUSD_H1_4yr.csv` | EXISTS (verified) |
| AUDNZD | `V2/data/AUDNZD_H1_4yr.csv` | EXISTS (verified) |

All three CSVs share the same `Datetime,Open,High,Low,Close,Volume` schema as the Phase 8 5-pair set.

### Script extension required (Plan 03 work)

`fit_regime_detectors.py` line 38 hardcodes:

```python
ACTIVE_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP"]   # D-10
```

Plan 03 must:
1. Extend `ACTIVE_PAIRS` to all 8 pairs (or read from `pair_config.PAIR_CONFIGS.keys()` — pitfall §8 says do not hardcode)
2. Run `python -m scripts.fit_regime_detectors --pair all` (idempotent — skips existing 5 unless `--force`)
3. Verify each new JSON has `variance_ordering.unconditional_variances` monotonically increasing (REGM-02 visible)
4. Stamp `v1_parity_tested=False` initially (line 75); **Phase 9 does NOT need to gate-flip this to True** — the @pytest.mark.slow parity tests in [test_regime_parity.py](../../../V2/tests/v3_intelligence/test_regime_parity.py) only assert vs. the 5 Phase 8 pairs that have V1 baseline data. The 3 new pairs have NO V1 baseline (V1 was 5-pair scope), so `v1_parity_tested=False` is the honest provenance — and ROUT-04 doesn't require it.

### Memory & time impact

Per Phase 8 P04 metric line: each detector fits in ~2.5 minutes on ~17k bars. 3 new detectors = ~7.5 minutes wall-clock. Memory < 5 MB. Negligible.

---

## 8. Anti-patterns + pitfalls (call out to planner)

| # | Pitfall | Source | Impact if violated |
|---|---|---|---|
| 1 | **Auto-pull inside PitClock** — `OHLCVCache.get_bars()` raises `FutureBarReadError` if cache miss occurs inside `with PitClock(...)`. The simulator must pre-warm the cache (or read CSVs directly). | [cache.py:99](../../../V2/v3_intelligence/cache.py); Phase 8.4 D-04 | ROUT-04 simulation crashes mid-run; future-bar leak if accidentally bypassed |
| 2 | **Viterbi anywhere** — `predict_viterbi` removed from regime/types and online_filter; `test_viterbi_ban.py` AST-scans for re-introduction. | [REGM-04](../../../V2/tests/v3_intelligence/test_viterbi_ban.py); Phase 8 D-04 | Phase gate fails — REGM-04 ban grep blocks any commit |
| 3 | **Hardcoded active-pairs list** — `fit_regime_detectors.py` line 38 hardcodes 5 pairs (Phase 8 era); `backtest_hybrid.py:60` hardcodes 8 (drifts independently). Plan 03 must source from `pair_config.PAIR_CONFIGS.keys()`, not a literal list. | CONTEXT D-19 + auto-memory `feedback_8pairs_multi_timeframe.md` | Detector inventory drifts; future pair additions require multi-file edits |
| 4 | **M15 swing strategy** — Only 4 strategies dispatch (M15_SCALP / H1_SCALP / H1_MOMENTUM / DAILY_SWING). Do NOT introduce M15_SWING. `pair_config` enable flags are the closed set. | CONTEXT explicit | Schema drift; tests that mock 4 enum values break |
| 5 | **Skip wave-0 RED scaffold** — Phase 7/8/8.4/8.5 all started with a RED-tests-first plan. Checker/verifier tooling expects this. | CONTEXT D-17; Phase 8.4-01 / 8.5-01 / 11-01 / 12-01 metric rows | Plan checker blocks; verifier rejects Phase 9 without RED → GREEN trace |
| 6 | **Mutating regime filter inside `route()`** — `OnlineRegimeFilter.update()` mutates `_alpha` and `_sigma2`. If `route()` calls `update()`, the simulator loses control of bar advancement. The simulator must call `update()` exactly once per bar BEFORE calling `route()`; `route()` reads via `current_state_prob()` only. | online_filter.py:75 (mutating) vs. line 142 (read-only) | ROUT-04 produces wrong Sharpe; double-advance breaks state |
| 7 | **PiT validator failures on the new simulation file** — any in-loop `row['Close']` read assigning to a variable named `entry_*` triggers a violation. Use `next_row['Open']` for entries; `px = row['Close']` for exits is whitelisted. | [pit_validator.py:192](../../../V2/backtest/pit_validator.py) `_is_exit_price_assignment` | New file blocked from BKTS-04 gate; Sharpe inflation 0.2–0.4 if accepted |
| 8 | **Cold-start RAG inflation** — `score_signal()` returns `confidence=0.5, action="TAKE"` for first 5 bars. Simulator on empty Chroma will pass every signal at 0.5 — gate 4 becomes a no-op for the warmup window. | rag_signal_filter.py:144 | ROUT-04 Sharpe biased upward in early window unless RAG is pre-warmed via `learning_loop.on_trade_close()` |
| 9 | **`PairConfig` is NOT frozen** — line 34 lacks `frozen=True`. Multi-threaded router-shared instances could be mutated. Live engine assumption: `pair_config` is read-only after construction; document this contract. | pair_config.py:34 | Defensive: `RouteDecision` must be frozen (CONTEXT D-01) but PairConfig stays mutable for legacy compat — do NOT freeze it in this phase, just contract-document |
| 10 | **`PitClock` and threading** — `_PIT_THREAD_DEPTH` is `threading.local()`. If the simulator ever spawns workers, each worker has its own depth counter and `pit_active()` returns False there. CONTEXT D-13 says equal-per-dispatch on a single timeline — recommend single-threaded simulator. | pit.py:25 | Future parallelization regression-risk; not a Phase 9 blocker |
| 11 | **`SESSION_RULES` is currently empty (seed)** — `is_tradeable_session` returns True for every input until SUPABASE_DB_URL is provisioned and Phase 8.5 P03–P05 run on full corpus. Phase 9 router must work correctly against the empty seed (no errors) — but the gate is a no-op until real rules land. | session_config.py seed; STATE.md Phase 8.4 follow-up #1 | If router asserts non-empty SESSION_RULES, it deadlocks the whole engine until SUPABASE_DB_URL lands |
| 12 | **`current_state_prob()` does not exist on `OnlineRegimeFilter`** — CONTEXT D-04 references it but it's not in [online_filter.py](../../../V2/v3_intelligence/regime/online_filter.py). Plan 02 must add it (5-line read-only method) OR Plan 02 reads `state_probs` directly. Recommend the former for API symmetry. | online_filter.py — method absent | If router calls a missing method, AttributeError crashes the live engine on the first bar |

---

## 9. RouteDecision → OrderRequest mapping (Phase 10 forward-compat)

Source: [V2/bridge/types.py](../../../V2/bridge/types.py) (`OrderRequest`); [V2/bridge/schemas.py](../../../V2/bridge/schemas.py) (`pack_order_request`)

### `OrderRequest` shape (types.py:51–60)

```python
@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol:     str
    side:       Side                    # BUY=1 / SELL=-1 enum
    quantity:   float
    order_type: OrderType = OrderType.MARKET   # MARKET / LIMIT / STOP
    price:      float | None = None
    sl:         float | None = None
    tp:         float | None = None
    comment:    str = ""
```

### `RouteDecision` (CONTEXT D-01) field mapping

| RouteDecision field | OrderRequest field(s) | Mapping logic |
|---|---|---|
| `pair: str` (implicit from route() arg) | `symbol` | direct copy |
| `direction: Direction` enum | `side` | `Direction.LONG → Side.BUY`, `Direction.SHORT → Side.SELL` |
| `size_mult: float` | `quantity` | `quantity = base_lot_size(account_equity) * size_mult` — Phase 10 owns the `base_lot_size` formula |
| `confidence: float` | `comment` | embed in comment string for forensic logging, e.g. `f"strat={s.name} conf={c:.2f}"` (must fit in MT5's 31-char comment limit) |
| `strategy: Strategy` enum | `comment` (also) | needed by EA's CCircuitBreaker for magic-number routing |
| (no field — derived) | `order_type` | always `OrderType.MARKET` for v2.0 (no limit orders) |
| (no field — derived) | `price` | `None` for market orders |
| (no field — derived) | `sl` | derived by Phase 10 from `pair_config[pair].swing_stop_atr * atr_at_entry` (or scalp/momentum/m15 variant per strategy) |
| (no field — derived) | `tp` | derived by Phase 10 from `*_target_atr * atr_at_entry` |

### Forward-compat checks for Phase 9 design

1. **Strategy enum must round-trip cleanly.** EA's CCircuitBreaker (Phase 10) needs a stable string representation. Recommend `Strategy(enum.Enum)` with string values:
   ```python
   class Strategy(enum.Enum):
       DAILY_SWING  = "DAILY_SWING"
       H1_SCALP     = "H1_SCALP"
       H1_MOMENTUM  = "H1_MOMENTUM"
       M15_SCALP    = "M15_SCALP"
   ```
   So `decision.strategy.value` is a string the EA can parse from the comment field.

2. **Direction enum aligns with Side enum at runtime, not at type level.** Different files (router.py vs bridge/types.py) own them — that's correct (router doesn't depend on bridge). The Phase 10 mapping function lives in `LiveSignalEngine` and translates explicitly.

3. **`size_mult` is dimensionless ∈ [0, 1].** Phase 10 multiplies by base lot size. The router does NOT need to know the account equity. Phase 9 ships `size_mult` as a pure multiplier; CONTEXT D-04 caps at 1.0 — guarantees Phase 10 never has to clamp.

4. **No price field.** Market orders only; entry price is what MT5 fills at. Phase 9 simulator approximates via next-bar-open per BKTS-01 fix.

### One field worth adding to `RouteDecision` for Phase 10 forward-compat

`atr_at_entry: float` — the ATR value the router observed. Phase 10 needs this to compute SL/TP. CONTEXT D-01 omits it. Without it, Phase 10's mapping function must re-compute ATR from the bar — duplicates work and could drift. Recommend Plan 02 adds `atr_at_entry: float` to `RouteDecision` even though CONTEXT didn't list it explicitly; it's read directly from `BarSnapshot`.

(Marked as "discretion" — not in CONTEXT D-01's explicit field list; raise with operator if uncertain.)

---

## 10. Validation Architecture (Nyquist 8-dimension breakdown)

`.planning/config.json` does NOT explicitly set `workflow.nyquist_validation`; under the spec's "absent = enabled" rule, this section IS required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in use across V2 since Phase 6) |
| Config file | `V2/pyproject.toml` (slow marker registered there per Phase 8 test_regime_parity precedent) |
| Quick run command | `cd V2 && pytest tests/v3_intelligence/test_router.py -x -q` |
| Full suite command | `cd V2 && pytest tests/ -q --deselect tests/v3_intelligence/test_regime_parity.py` (skip slow parity by default) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| ROUT-01 | `route()` returns `RouteDecision` with the typed shape | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_route_returns_typed_dataclass -x` | Wave 0 |
| ROUT-01 | Regime gate blocks (CRISIS state) | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_regime_gate_blocks -x` | Wave 0 |
| ROUT-01 | Session gate blocks (`is_tradeable_session=False`) | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_session_gate_blocks -x` | Wave 0 |
| ROUT-01 | Matrix gate blocks (`allow_X=False`) | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_matrix_gate_blocks -x` | Wave 0 |
| ROUT-01 | RAG gate blocks (action == SKIP / confidence < 0.28) | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_rag_gate_blocks -x` | Wave 0 |
| ROUT-01 | Valid dispatch (all 4 gates pass) | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_valid_dispatch -x` | Wave 0 |
| ROUT-02 | Daily swing dispatched preferentially over intraday | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_swing_first_priority -x` | Wave 0 |
| ROUT-02 | Intraday strategies skipped when swing position open on pair | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_intraday_skipped_when_swing_open -x` | Wave 0 |
| ROUT-03 | Opposite-direction position rejects new dispatch | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_direction_conflict_reject -x` | Wave 0 |
| ROUT-03 | Same-direction stacking permitted | unit | `pytest V2/tests/v3_intelligence/test_router.py::test_same_direction_stacking_allowed -x` | Wave 0 |
| ROUT-04 | 4yr simulation Sharpe gate passes | integration (slow) | `pytest V2/tests/v3_intelligence/test_router_integration.py::test_aggregate_sharpe_beats_single_by_0_2 -x --slow` | Wave 0 |
| ROUT-04 | Sim output JSON has required keys | integration | `pytest V2/tests/v3_intelligence/test_router_integration.py::test_sim_report_schema -x` | Wave 0 |
| Cross | PiT validator passes on `router_simulation.py` | smoke | `python -m backtest.pit_validator V2/backtest/router_simulation.py` | EXISTS |

### Sampling Rate

- **Per task commit:** `cd V2 && pytest tests/v3_intelligence/test_router.py -x -q` (~3 sec)
- **Per wave merge:** `cd V2 && pytest tests/ -q -k "not parity"` (~30 sec, deselects slow parity)
- **Phase gate:** Full suite GREEN + `python -m backtest.pit_validator V2/backtest/router_simulation.py` exits 0 + the slow integration test produces `V2/reports/router_4yr_simulation.json` with `gate_passed=true` before `/gsd:verify-work`

### Wave 0 Gaps

The following test files do not exist yet and must land in Plan 01 (Wave 0):

- [ ] `V2/tests/v3_intelligence/test_router.py` — 11 RED unit tests covering all ROUT-01/02/03 scenarios above
- [ ] `V2/tests/v3_intelligence/test_router_integration.py` — 2 RED slow tests gating ROUT-04 (marked `@pytest.mark.slow` — registered marker per `V2/pyproject.toml` precedent)
- [ ] `V2/tests/v3_intelligence/conftest.py` — extend with new fixtures: `mock_regime_filter`, `mock_session_filter`, `mock_rag`, `mock_position_store`, `synthetic_bar_snapshot`. Existing conftest already has `synthetic_three_regime_returns` and `v1_baseline` — keep those untouched.

### 8-Dimension Validation Breakdown

| Dim | Question | Phase 9 evidence |
|---|---|---|
| **Functional** | Does `route()` return `RouteDecision` for valid inputs and `None` for blocked? | `test_route_returns_typed_dataclass`, `test_valid_dispatch`, the 4 gate-block tests |
| **Behavioral** | Do swing-first and direction-conflict policies fire correctly across 100s of dispatch combinations? | `test_swing_first_priority`, `test_intraday_skipped_when_swing_open`, `test_direction_conflict_reject`, `test_same_direction_stacking_allowed` |
| **Performance** | Does `route()` complete in <10 ms (live latency budget)? | benchmark in `test_route_latency_under_10ms` (Wave 0 — measures Python wall-clock; RAG cosine query is the hot path) |
| **Security** | Are there any unsafe operations? Does the router log secrets? | None expected — pure dispatch logic, no I/O at route() time. Verifier checks logging schema redacts nothing leakable |
| **Reliability** | What happens when an upstream gate raises? | `test_route_propagates_regime_filter_exception`, `test_route_handles_empty_position_store` (Wave 0 RED) |
| **Maintainability** | Can a future engineer add a 5th strategy? | `Strategy` enum + per-strategy size-mult dict in pair_config — `test_add_strategy_only_touches_one_dict` (Wave 0 — documentation-style test) |
| **Observability** | Can ops see why a dispatch was blocked? | `test_logs_gate_blocked_with_reason`, `test_logs_dispatched_with_full_decision` (Wave 0 — assert log records via `caplog`) |
| **Compliance** | Does ROUT-04 simulation pass PiT validator? | `python -m backtest.pit_validator V2/backtest/router_simulation.py` returns exit 0 (Phase 7 BKTS-04 gate inherited) |

---

## 11. Recommended Plan Slicing — 4 plans

### Plan 01 (Wave 0): RED test scaffold + dataclass stubs

**Mirrors Phase 7-01, 8-01, 8.4-01, 8.5-01 patterns.**

Tasks (3):
1. Land 11 RED unit tests in `V2/tests/v3_intelligence/test_router.py` covering ROUT-01/02/03 scenarios (CONTEXT D-17 spec: 8 tests; recommend 11 to fully cover the 8-dim grid)
2. Land 2 RED slow integration tests in `V2/tests/v3_intelligence/test_router_integration.py` gating ROUT-04 (`@pytest.mark.slow`)
3. Stub `V2/v3_intelligence/router.py` with bare imports + `RouteDecision`/`OpenPosition`/`PositionStore`/`Strategy`/`Direction` symbols — enough to make tests collect cleanly. Implementation is empty (`raise NotImplementedError`) — RED.

Outcome: Tests collect, all RED. Phase 9 P02–P04 turn them GREEN.

### Plan 02: Router core + position store (ROUT-01/02/03)

Tasks (3–4):
1. Implement `RouteDecision` frozen dataclass + `Strategy`/`Direction` enums + `OpenPosition` frozen dataclass + `PositionStore` Protocol + `InMemoryPositionStore` adapter (turns `test_route_returns_typed_dataclass`, `test_direction_conflict_reject`, `test_same_direction_stacking_allowed` GREEN)
2. Implement 4-gate decision chain in `StrategyRouter.route()` (turns 4 gate-block tests + `test_valid_dispatch` GREEN). Add `OnlineRegimeFilter.current_state_prob()` 5-line method (Pitfall #12).
3. Implement swing-first iteration + tie-break (turns `test_swing_first_priority`, `test_intraday_skipped_when_swing_open` GREEN). Lift `SHARPE_4YR` constant in `pair_config.py` for tie-break (§3 recommendation)
4. Add structured logging + observability tests (turns `test_logs_gate_blocked_with_reason`, `test_logs_dispatched_with_full_decision` GREEN)

### Plan 03: Detector inventory expansion to 8 pairs (ROUT-04 prep)

Tasks (2):
1. Extend `V2/scripts/fit_regime_detectors.py` to source `ACTIVE_PAIRS` from `pair_config.PAIR_CONFIGS.keys()` (Pitfall #3); fit + persist GBPNZD/EURUSD/AUDNZD detector JSONs (commits 3 new JSON files into `V2/data/regime/`)
2. Run end-to-end smoke: `python -m scripts.fit_regime_detectors --pair all` produces 8 JSONs; verify `variance_ordering.unconditional_variances` monotonically increasing for each new pair

### Plan 04: 4yr simulation harness + ROUT-04 gate (the phase-gate plan)

Tasks (3–4):
1. Implement `V2/backtest/router_simulation.py` (NEW per CONTEXT D-18). Loads 8 detector JSONs, 8 H1 4yr CSVs, builds router, runs PiT-wrapped loop, dispatches via `router.route()`, calls `on_trade_close(rec, logger=sim_logger, rag=sim_rag)` on each simulated exit (separate sim DB + Chroma collection per §6 recommendation)
2. Compute aggregate Sharpe + best single per-pair Sharpe; emit `V2/reports/router_4yr_simulation.json` with `{aggregate_sharpe, best_single_sharpe, baseline_plus_0_2, gate_passed}` (CONTEXT D-18 spec)
3. Wire integration tests (turn `test_aggregate_sharpe_beats_single_by_0_2`, `test_sim_report_schema` GREEN); pass PiT validator on `router_simulation.py`
4. Phase gate: full suite GREEN + `gate_passed=true` in committed JSON report

### Cross-plan invariants

- Wave 0 RED scaffold MUST land before any GREEN plan starts (CONTEXT D-17, Pitfall #5)
- Each plan's tasks must have `<verify>` commands that point to real test paths on disk (Phase 8.4 P01 / 8.5 P01 metric: "Nyquist compliance: every implementation task has a `<verify>` command pointing to a real test file on disk")
- No plan modifies `V2/backtest/backtest_hybrid.py` (CONTEXT D-18)
- No plan touches MQL5 sources (Phase 10 owns)

---

## Sources

### Primary (HIGH confidence)

- [V2/v3_intelligence/regime/online_filter.py](../../../V2/v3_intelligence/regime/online_filter.py) — read in full; `update()` API + `state_probs` property documented; `current_state_prob()` confirmed absent
- [V2/v3_intelligence/regime/persistence.py](../../../V2/v3_intelligence/regime/persistence.py) — `save_detector` / `load_detector` schema + JSON contract
- [V2/v3_intelligence/regime/types.py](../../../V2/v3_intelligence/regime/types.py) — `RegimeState` enum (TRENDING=0, MEAN_REVERTING=1, CRISIS=2)
- [V2/v3_intelligence/temporal_filters.py](../../../V2/v3_intelligence/temporal_filters.py) — predicate signatures, default-permissive contract, blackout pattern resolution
- [V2/v3_intelligence/pair_config.py](../../../V2/v3_intelligence/pair_config.py) — full file read; PAIR_CONFIGS dict, allow_* flags, size_mult fields, the embedded `sharpes` dict at line 213
- [V2/v3_intelligence/rag_signal_filter.py](../../../V2/v3_intelligence/rag_signal_filter.py) — `score_signal()` signature, return shape, action thresholds, cold-start behaviour
- [V2/v3_intelligence/cache.py](../../../V2/v3_intelligence/cache.py) — `is_pit_active` refusal pattern at line 99
- [V2/v3_intelligence/pit.py](../../../V2/v3_intelligence/pit.py) — `PitClock` API, `pit_active()`, monotone `advance()`, threading.local depth counter
- [V2/v3_intelligence/learning_loop.py](../../../V2/v3_intelligence/learning_loop.py) — `on_trade_close` contract, optional injection, params_json diff logic
- [V2/v3_intelligence/trade_logger.py](../../../V2/v3_intelligence/trade_logger.py) — SQLite schema, `db_path` constructor injection
- [V2/backtest/pit_validator.py](../../../V2/backtest/pit_validator.py) — AST whitelist patterns (next-bar fill, indicator args, exit-price assignment)
- [V2/backtest/backtest_hybrid.py](../../../V2/backtest/backtest_hybrid.py) — swing + m15 backtest patterns, `on_trade_close` call sites, `_session()` helper
- [V2/backtest/backtest_4yr_evaluate.py](../../../V2/backtest/backtest_4yr_evaluate.py) — 4yr Sharpe runner pattern (closest precedent for ROUT-04 sim)
- [V2/scripts/fit_regime_detectors.py](../../../V2/scripts/fit_regime_detectors.py) — fitting CLI; ACTIVE_PAIRS hardcoded list to extend
- [V2/bridge/types.py](../../../V2/bridge/types.py) — `OrderRequest` field set
- [V2/data/regime/USDJPY_detector.json](../../../V2/data/regime/USDJPY_detector.json) — confirmed JSON schema on disk
- Phase planning artefacts read: [09-CONTEXT.md](09-CONTEXT.md), [REQUIREMENTS.md](../../REQUIREMENTS.md), [STATE.md](../../STATE.md), [ROADMAP.md](../../ROADMAP.md) lines 191–206

### Secondary (MEDIUM confidence)

- `SESSION_RULES` empty-seed status — read [V2/v3_intelligence/session_config.py](../../../V2/v3_intelligence/session_config.py) (seed file, GENERATED_AT 2026-04-27); cross-checked against STATE.md "Phase 8.5 SESS-04 full-corpus run requires SUPABASE_DB_URL — non-blocking carry-over"
- `pair_config` Sharpe numbers — only available in `notes` prose AND `print_pair_summary` `sharpes` dict (line 213). MEDIUM because there is no canonical typed source; planner needs to resolve
- `OnlineRegimeFilter.current_state_prob()` absence — confirmed by reading the entire `online_filter.py`. CONTEXT names the method but the file does not implement it. MEDIUM because it could in principle have been added in a commit not visible to research; confirmed via direct file read on 2026-04-28

### Tertiary (LOW confidence)

- None. All claims in this RESEARCH.md are sourced from files on disk read in full or in load-bearing sections.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is shipped and tested across Phase 6/7/8/8.4/8.5
- Architecture (4-gate chain, PositionStore protocol, simulator): HIGH — patterns established by precedent phases
- Pitfalls: HIGH — 12 pitfalls cited with file/line precision
- `current_state_prob()` gap: MEDIUM — confirmed absent on 2026-04-28; planner must add OR work around
- `pair_config.SHARPE_4YR` constant lift: MEDIUM — recommendation, not yet committed

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (30 days — codebase is stable; only risk is `SESSION_RULES` populating from a SUPABASE_DB_URL run, which would NOT invalidate any claim here — only narrows the gate-2 no-op window)

---

## RESEARCH COMPLETE
