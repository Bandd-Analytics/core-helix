# Testing Patterns

**Analysis Date:** 2026-04-21

## Current State: Research-Grade (No Test Framework)

**Status:** Unit test directory exists but is empty. No pytest, unittest, or coverage infrastructure.

```
tests/
├── unit_tests/          # Empty directory — no test files
└── validation_spreadsheets/
```

**No CI/CD:** No GitHub Actions, pre-commit hooks, or automated test runners detected.

---

## Test Infrastructure

**Framework:** None (no test runner configured)
- No `pytest.ini`, `setup.cfg`, or `pyproject.toml` with test config
- No `unittest` test suites
- No test runner commands documented

**Assertion Library:** Not applicable (no tests written)

**Coverage:** Not measured or enforced

---

## Backtest Validation as Test Proxy

**What exists instead of unit tests:**
- `backtest_hybrid.py` (775 lines) — complete dual-strategy backtest engine
- `backtest_evaluate_all.py` (527 lines) — comprehensive evaluation matrix
- Data-driven validation via metrics calculation

**How it works:**

1. **Load historical data** → OHLC CSV files in `data/` directory (H1, daily, M15)
2. **Run backtest with injected configs** → Override `pair_config.py` in-memory
3. **Calculate performance metrics** → Sharpe, win rate, P&L, max loss
4. **Compare across all pairs × all strategies** → Matrix of results
5. **Filter by verdict** → Only enable pairs/strategies above profitability threshold

Example from `backtest_evaluate_all.py`:
```python
def metrics(df):
    """Calculate performance metrics from trade DataFrame."""
    if len(df) == 0:
        return {"trades": 0, "sharpe": 0, "win_rate": 0, "avg_pnl": 0}
    wins = (df['pnl_pct'] > 0).sum()
    sharpe = df['pnl_pnl'].mean() / df['pnl_pct'].std() * np.sqrt(252) if df['pnl_pct'].std() > 0 else 0
    return {
        "trades": len(df),
        "sharpe": sharpe,
        "win_rate": wins / len(df),
        "avg_pnl": df['pnl_pct'].mean(),
    }
```

**Trade logging as validation:**
- Every backtest trade logged to SQLite via `TradeLogger`
- Enables post-analysis and audit trail
- `trade_logger.print_summary()` outputs performance per symbol/strategy

Example:
```python
logger = TradeLogger()
logger.log_trades_bulk(trades_df)
logger.print_summary()
# Output:
# ======================================================================
# TRADE JOURNAL SUMMARY
# ======================================================================
# USDJPY   | Trades:  124 | Win%:  38.7% | P&L:  +36.37%
```

---

## Data & Fixtures

**Test data location:** `data/` directory
- CSV files: `SYMBOL_H1_2015-2026.csv`, `SYMBOL_DAILY_2015-2026.csv`, `SYMBOL_M15_2015-2026.csv`
- Format: OHLC + timestamp, loaded via `pd.read_csv()`
- Coverage: 11-year history (2015-2026) for EURUSD, USDJPY, AUDNZD, EURGBP, GBPJPY

**Configuration fixtures:**
- `v3_intelligence/pair_config.py` defines `PAIR_CONFIGS` dict with 8 pairs
- `_DEFAULT_CONFIG` fallback for unknown symbols
- Configs include thresholds, ATR multipliers, session windows

Example fixture from `pair_config.py`:
```python
PAIR_CONFIGS: dict[str, PairConfig] = {
    "USDJPY": PairConfig(
        symbol="USDJPY", tier=1,
        swing_size_mult=1.0,
        swing_z_threshold=2.0,
        swing_target_atr=4.0,
        swing_stop_atr=1.5,
        swing_max_bars=120,
        allow_swing=True,
        allow_scalp=False,
        allow_momentum=False,
        allow_m15_scalp=True,
        m15_size_mult=0.5,
        notes="Swing Sh 3.09 (best pair)...",
    ),
    # ... 7 more pairs
}
```

**RAG (Retrieval-Augmented Generation) index as test data:**
- ChromaDB vector index in `data/chroma_rag/`
- Persists historical trade embeddings
- Callable by test scenarios: `rag = RAGSignalFilter(); score = rag.score_signal(...)`
- Generated during backtest via `rag.index_trades(trades_df)`

---

## Backtest Test Patterns

**Strategy isolation:**
- Each strategy runs independently: SWING, M15_SCALP, H1_SCALP, MOMENTUM
- Config injections enable/disable features in-memory: no file modifications
- Example from `backtest_evaluate_all.py`:

```python
def _eval_cfg_swing(sym):
    """Force swing enabled, use default ATR/Z thresholds."""
    base = PAIR_CONFIGS.get(sym, PairConfig(symbol=sym, tier=2))
    return PairConfig(
        symbol=sym, tier=base.tier,
        swing_size_mult=1.0,
        swing_z_threshold=2.0,
        swing_target_atr=4.0, swing_stop_atr=1.5,
        swing_max_bars=120,
        allow_swing=True, allow_scalp=False, allow_momentum=False, allow_m15_scalp=False,
    )

class Evaluator(HybridMultiTimeframeBacktest):
    def run_swing_with_cfg(self, symbol, daily, h1, cfg):
        """Run swing backtest with injected config instead of pair_config.py."""
        # ... backtest logic with `cfg` parameter instead of global config
```

**Cross-timeframe validation:**
- H1 bars mapped to daily Z-scores for signal alignment
- Example from `backtest_hybrid.py`:

```python
daily_d = np.array([str(d)[:10] for d in daily.index])
h1_d    = np.array([str(d)[:10] for d in h1.index])
idx     = np.clip(np.searchsorted(daily_d, h1_d, side='right') - 1, 0, len(daily) - 1)
h1['daily_z']     = daily['z_score'].values[idx]
```

**Signal validation:**
- Z-score calculation: `(price - MA) / std`
- ATR-based exits: `target = ATR × multiplier`, `stop = ATR × stop_multiplier`
- Session filtering: `_session()` returns 'LONDON' or 'NY' based on hour

---

## What's NOT Tested

**Critical gaps:**

1. **Risk Management:**
   - Circuit breaker logic (`CCircuitBreaker.mqh`) never unit tested
   - Daily/weekly loss limits not validated
   - Position correlation checks not verified

2. **Indicator Calculations:**
   - `AdaptiveATR.mq5` — no validation of percentile rank calculations
   - `HurstExponent.mq5` — R/S analysis not tested
   - `MeanRevOscillator.mq5` — OLS regression accuracy not verified
   - `SessionFilter.mq5` — session hour classification untested

3. **Edge Cases:**
   - No tests for NaN handling in signal calculations
   - No validation of division-by-zero protection
   - No tests for data gaps or missing bars
   - No boundary testing for parameter limits

4. **Integration:**
   - `MultiPairEA.mq5` initialization logic untested
   - Signal generator coupling not validated
   - Position sizing with Kelly fraction not verified

5. **RAG Learning Loop:**
   - `RAGSignalFilter` index construction untested
   - Confidence scoring accuracy not validated
   - Size modifier calculations not verified

6. **Database Integrity:**
   - `TradeLogger` schema integrity not tested
   - Concurrent write safety not verified
   - Data recovery scenarios untested

---

## Backtest Script Patterns (as Closest to Tests)

**Run evaluation matrix:**
```bash
cd /home/user/Desktop/Bandd\ Analytics/BA\ PRJ\ -\ Helix/V2/backtest
python backtest_evaluate_all.py            # full matrix, all pairs all strategies
python backtest_evaluate_all.py --swing    # swing only
python backtest_evaluate_all.py --m15      # M15 only
python backtest_evaluate_all.py --intraday # scalp + momentum only
```

**Manual validation:**
```python
from v3_intelligence.trade_logger import TradeLogger
logger = TradeLogger()
stats = logger.get_stats(symbol="USDJPY")
print(f"Win rate: {stats['win_rate']*100:.1f}%")
```

**Signal filter testing:**
```python
from v3_intelligence.rag_signal_filter import RAGSignalFilter
rag = RAGSignalFilter()
score = rag.score_signal(
    symbol="EURUSD",
    strategy_type="M15_SCALP",
    session="LONDON",
    daily_z=2.1,
    h1_z=0.8,
    vol_percentile=75.0,
    hour_utc=8,
)
print(f"Confidence: {score['confidence']}, Action: {score['action']}")
```

---

## Recommended Test Framework (for Implementation)

**Structure to adopt:**
```
tests/
├── unit_tests/
│   ├── test_pair_config.py          # Config validation and defaults
│   ├── test_rag_signal_filter.py    # Confidence scoring logic
│   ├── test_trade_logger.py         # Database operations
│   └── test_signal_filters.py       # Z-score, ATR, Hurst calculations
├── integration_tests/
│   ├── test_backtest_hybrid.py      # Full dual-strategy run
│   ├── test_strategy_independence.py # Swing vs M15 isolation
│   └── test_cross_timeframe_alignment.py # Daily→H1 mapping
├── conftest.py                      # Shared fixtures (data, configs)
└── fixtures/
    ├── sample_data.csv              # Small OHLC dataset for fast tests
    └── sample_trades.json           # Trade results for RAG indexing
```

**Recommended tools:**
- **pytest** (>= 7.0) — Test runner and assertions
- **pytest-cov** — Coverage reporting
- **hypothesis** — Property-based testing for edge cases
- **pandas-testing** — DataFrame assertion utilities

**Example test patterns to implement:**

```python
# tests/unit_tests/test_pair_config.py
import pytest
from v3_intelligence.pair_config import get_pair_config, PAIR_CONFIGS

def test_get_pair_config_returns_known_symbol():
    cfg = get_pair_config("USDJPY")
    assert cfg.symbol == "USDJPY"
    assert cfg.tier == 1
    assert cfg.allow_swing is True

def test_get_pair_config_fallback_for_unknown():
    cfg = get_pair_config("UNKNOWN")
    assert cfg.symbol == "DEFAULT"
    assert cfg.tier == 2

@pytest.mark.parametrize("symbol,expected_tier", [
    ("USDJPY", 1),
    ("EURGBP", 2),
    ("GBPNZD", 2),
])
def test_pair_tiers(symbol, expected_tier):
    cfg = PAIR_CONFIGS[symbol]
    assert cfg.tier == expected_tier
```

**Coverage targets (to reach V1 standard of 80%+):**
- Signal calculations: 100% (Hurst, Z-score, ATR)
- Risk checks: 100% (daily/weekly limits, correlation)
- Trade logging: 95% (normal path + error handling)
- RAG indexing: 85% (happy path + edge cases)
- Backtest runners: 60% (complex state machines, harder to test)

---

## Current Coverage Status

**Measured:** 0% (no test suite)

**Implicit validation via backtests:**
- 11 years of OHLC data (11,000+ daily bars, 100,000+ H1 bars per pair)
- 539 trades in validated V2 baseline (best config)
- Sharpe 1.67, +36.37% P&L — signals and risk management validated in-market

**What this means:**
- Production code is battle-tested but not unit-tested
- Changes to signal logic require full backtest re-evaluation
- No regression detection for code changes
- Risk manager has not been tested in isolation

---

## Test Execution Gaps

**CI/CD:** Not present
- No `.github/workflows/` directory
- No pre-commit hooks (`.pre-commit-config.yaml` missing)
- No linting configs (`.flake8`, `.mypy.ini` missing)

**Local test command:**
- No `pytest` command available
- No `make test` target
- No `tox.ini` for environment-specific testing

**Coverage measurement:**
- No coverage reports generated
- No threshold enforcement
- No coverage artifacts in CI

---

## MQL5 Testing Strategy (Production EA)

**MultiPairEA.mq5 validation:**
- No unit tests (not possible in MQL5 without external framework)
- Manual backtesting in MT5 Terminal (visual inspection)
- Journal logging via `CLogger` for trade audit trail

**Indicator testing:**
- MT5 indicator windows show visual confirmation
- No automated validation of indicator output
- Historical backtesting is manual

**Risk manager validation:**
- Circuit breaker tested via account equity tracking
- Position sizing validated against P&L history
- No standalone tests for `CCircuitBreaker` class

---

*Testing analysis: 2026-04-21*
