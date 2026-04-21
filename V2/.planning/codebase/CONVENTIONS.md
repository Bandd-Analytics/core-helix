# Coding Conventions

**Analysis Date:** 2026-04-21

## Python Naming Patterns

**Files:**
- Lowercase snake_case: `backtest_hybrid.py`, `rag_signal_filter.py`, `trade_logger.py`
- Scripts use underscores for multi-word: `download_history.py`, `download_intraday_data.py`

**Functions:**
- Lowercase snake_case throughout
- Private helper functions prefixed with `_`: `_make_doc_text()`, `_make_metadata()`, `_session()`, `_eval_cfg_swing()`
- Public methods: `get_pair_config()`, `index_trade()`, `score_signal()`, `log_trade()`, `get_stats()`

**Classes:**
- PascalCase for all classes: `RAGSignalFilter`, `TradeLogger`, `HybridMultiTimeframeBacktest`, `Evaluator`, `MarketMindBacktest`
- Dataclasses: `PairConfig` (defined in `v3_intelligence/pair_config.py`)

**Variables:**
- Lowercase snake_case: `position_size`, `risk_per_trade`, `daily_z`, `h1_z`, `vol_percentile`, `entry_price`, `exit_price`
- Constants in UPPERCASE: `PAIR_CONFIGS`, `CHROMA_AVAILABLE`, `CHROMA_PATH`, `DATA_DIR`, `ALL_PAIRS`, `ACTIVE_PAIRS`
- Session constants as frozensets: `_LONDON_HOURS`, `_NY_HOURS`

**Type Hints:**
- Used sparingly but present for public APIs
- Dataclass field annotations are comprehensive: `symbol: str`, `tier: int`, `swing_size_mult: float`, `allow_swing: bool`
- Function signatures include return types: `def get_pair_config(symbol: str) -> PairConfig:`
- Optional types from `typing`: `Optional[str]`, `Optional[dict]`
- Generic dict type hints: `dict` without strict typing (no `Dict[str, PairConfig]` syntax, but `dict[str, PairConfig]` in type hints)

Example from `rag_signal_filter.py`:
```python
def _make_doc_text(trade: dict) -> str:
    """Serialize a trade's market context into a searchable text document."""
    ...

def score_signal(
    self,
    symbol: str,
    strategy_type: str,
    session: str,
    daily_z: float,
    h1_z: float,
    vol_percentile: float,
    hour_utc: int,
    k: int = 15,
    min_samples: int = 5,
) -> dict:
```

## Docstring Patterns

**Module-level docstrings:**
- Comprehensive docstrings at module top explaining purpose, usage, architecture
- Example from `backtest_hybrid.py`:
```python
"""
MarketMind V2 — Dual-Strategy Backtest Engine

Two INDEPENDENT strategies with separate position tracking and reporting:

  Strategy 1: DAILY SWING (H1 execution)
    - Signal: daily Z-score mean reversion (|Z| > 2.0)
    - Exits:  4.0× H1_ATR target, 1.5× H1_ATR stop, 120-bar timeout
    ...
"""
```

**Class docstrings:**
- Google-style docstrings with Usage section
- Example from `RAGSignalFilter`:
```python
class RAGSignalFilter:
    """
    Semantic signal confidence scorer using ChromaDB.

    Usage:
        rag = RAGSignalFilter()
        rag.index_trades(trades_df)          # after each backtest run
        score = rag.score_signal(signal)      # before taking a trade
    """
```

**Function docstrings:**
- One-line summary followed by parameter documentation
- Example from `trade_logger.py`:
```python
def log_decision(
    self,
    parameter: str,
    from_value,
    to_value,
    rationale: str,
    result: Optional[str] = None,
    verdict: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Append a strategy parameter change to the decision log."""
```

**Missing docstrings:**
- Backtest runners (`backtest_strategy.py`, `backtest_all_timeframes.py`) lack comprehensive docstrings
- No function-level docstrings in signal indicator functions

## Code Organization

**Imports:**
- Standard library first: `import sys`, `import io`, `import pandas as pd`, `import numpy as np`
- Third-party in order: pandas, numpy, pathlib, datetime, chromadb
- Internal imports with relative paths: `from v3_intelligence.trade_logger import TradeLogger`
- Conditional imports with try/except for optional dependencies:
```python
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
```

**Module structure:**
- Configuration/dataclasses at top: `pair_config.py` has `@dataclass PairConfig` followed by `PAIR_CONFIGS` dict
- Helper functions before main classes
- Main classes fully implemented before usage

## Error Handling

**Patterns:**
- Graceful degradation with optional dependencies: chromadb wrapped in try/except
- `CHROMA_AVAILABLE` flag controls feature availability
- Raises ImportError if required dependency missing: `raise ImportError("chromadb is required: pip install chromadb")`
- No explicit error logging; relies on Python exceptions

Example from `rag_signal_filter.py`:
```python
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class RAGSignalFilter:
    def __init__(self, chroma_path: Path = CHROMA_PATH, collection: str = "trades"):
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is required: pip install chromadb")
```

## Logging & Output

**No logging framework:**
- Uses raw `print()` statements for output
- Formatted with f-strings: `print(f"{sym:8} {'T'+str(cfg.tier):5} {sw:7} ...")`
- Summary tables use separator lines: `print("="*120)`, `print("-"*120)`

**Trade Logger:**
- SQLite-based persistence in `trade_logger.py`
- `log_trade()` records completed trades to database
- `log_decision()` appends strategy parameter changes
- `print_summary()` outputs formatted tables

Example from `trade_logger.py`:
```python
def print_summary(self):
    """Print a full performance summary to stdout."""
    print("\n" + "="*70)
    print("TRADE JOURNAL SUMMARY")
    print("="*70)
    for sym in symbols:
        s = self.get_stats(symbol=sym)
        if s:
            print(f"{sym:8} | Trades: {s['total_trades']:4} | "
                  f"Win%: {s['win_rate']*100:5.1f}% | "
                  f"P&L: {s['total_pnl_pct']*100:7.2f}%")
```

## Comments & Inline Documentation

**Section separators:**
- Visual ASCII dividers for logical sections: `# ─────────────────────────────────────────────────────────────────────────────`
- Comment blocks describe algorithm intent
- Inline comments explain constants and thresholds

Example from `signal_filters.py`:
```python
# ─────────────────────────────────────────────────────────────────────────────
# Hurst Exponent  (variance-scaling method)
#
# H < 0.45 → mean-reverting regime    (good for our Z-score entries)
# H ~ 0.50 → random walk              (neutral)
# H > 0.55 → trending regime          (block mean-reversion entries)
#
# Method: for increasing aggregation lags, variance of log-returns scales as
#   Var(τ) ∝ τ^(2H)  →  H = slope / 2  from log-log OLS fit
# ─────────────────────────────────────────────────────────────────────────────
```

**Configuration comments:**
- Extensive inline comments for pair configs explaining Sharpe ratios and thresholds
- Comments explain why strategies are enabled/disabled

Example from `pair_config.py`:
```python
# ── USDJPY: Elite swing pair. M15 marginal but positive. ─────────────────
"USDJPY": PairConfig(
    symbol="USDJPY", tier=1,
    swing_size_mult=1.0,
    allow_swing=True,
    allow_scalp=False,           # H1 scalp Sh -2.34 — strongly negative
    allow_momentum=False,        # Momentum Sh -1.61 — negative
    allow_m15_scalp=True,        # M15 Sh 0.93 — marginal positive
    ...
    notes="Swing Sh 3.09 (best pair). M15 Sh 0.93 (marginal, 0.5x size). H1 scalp/momentum both negative.",
),
```

## MQL5 Naming Conventions

**Files:**
- PascalCase with .mq5 extension: `MultiPairEA.mq5`, `AdaptiveATR.mq5`, `CCircuitBreaker.mqh`

**Classes:**
- C prefix required: `CCircuitBreaker`, `CSignalManager`, `CMeanRevSignal`, `CTrendSignal`, `CHybridSignal`, `CScalingManager`, `CLogger`
- Uppercase first letter: `CCorrelationMonitor`, `CPositionSizer`, `CRiskManager`

**Structs:**
- S prefix for struct types: `SCircuitBreakerState`, `SSymbolConfig`, `SRiskLimits`

**Functions & Methods:**
- PascalCase: `InitCircuitBreaker()`, `CheckAllLimits()`, `IsDailyLimitBreached()`, `GetCircuitBreakerState()`
- Boolean getter methods: `IsDrawdownLimitBreached()`, `IsCircuitBreakerActive()`
- Status checks with `Get` prefix: `GetCircuitBreakerReason()`

**Variables & Properties:**
- camelCase for local variables (in MQL context)
- prefix-based scoping: `inpLimits` (parameters), `cbState` (private members)
- include guards use full path: `#ifndef CCIRCUIT_BREAKER_H` / `#define CCIRCUIT_BREAKER_H`

Example from `CCircuitBreaker.mqh`:
```mql5
struct SCircuitBreakerState
{
   bool     isDailyLimitHit;
   bool     isWeeklyLimitHit;
   bool     isDrawdownLimitHit;
   bool     isCircuitBreakerActive;
};

class CCircuitBreaker : public CCorrelationMonitor
{
private:
   SCircuitBreakerState cbState;
   int       CIRCUIT_BREAKER_HOURS;
   bool      isLoggingEnabled;

public:
   bool      InitCircuitBreaker(double initialEquity, SRiskLimits &inpLimits);
   bool      CheckAllLimits();
   bool      GetCircuitBreakerState() { return cbState; }
};
```

**MQL5 Include Pattern:**
- Header includes: `#include <Trade/Trade.mqh>` (standard library)
- Custom includes: `#include "include/SymbolConfig.mqh"` (relative to EA directory)

## Module Design

**Barrel files:**
- `v3_intelligence/__init__.py` imports and re-exports main classes: `TradeLogger`, `RAGSignalFilter`, `PairConfig`

**Dataclass-driven config:**
- `pair_config.py` uses `@dataclass` for strategy configuration with sensible defaults
- Factory function: `get_pair_config(symbol: str) -> PairConfig` with fallback to defaults

**Database-backed state:**
- `trade_logger.py` manages SQLite persistence with context manager pattern
- `_connect()` method returns connection, schema initialized in `_init_db()`

**Optional feature flags:**
- RAG indexing opt-in: `enable_rag=True` parameter in `HybridMultiTimeframeBacktest`
- Conditional imports prevent hard failures on missing dependencies

## Code Quality Gaps

**Type hint coverage:**
- Only 30-40% of function parameters have type hints (gap in backtest_*.py files)
- Dict types lack generics (uses `dict` not `Dict[str, float]`)

**Error handling:**
- Minimal try/except (only for imports)
- No validation of config values or data ranges
- No exception chaining or context preservation

**Missing docstrings:**
- Backtest runner functions lack documentation
- Indicator calculation functions unexplained
- Helper functions in signal_filters.py undocumented

---

*Convention analysis: 2026-04-21*
