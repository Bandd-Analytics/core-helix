# Technology Stack

**Analysis Date:** 2026-04-21

## Languages

**Primary:**
- **Python 3.x** - Backtesting engine, data processing, RAG intelligence layer, configuration management
- **MQL5** - MetaTrader 5 Expert Advisor (EA) and custom indicators for live/demo trading

## Runtime

**Environment:**
- Python 3.x (CPython)
- MetaTrader 5 (MT5) terminal + MQL5 compiler

**Package Manager:**
- pip (Python)
- MQL5 standard library (for MT5)

## Frameworks

**Core Trading:**
- **MetaTrader5 (Python API)** - Live/demo account control, position management
  - Import: `import MetaTrader5 as mt5` (see `scripts/download_new_pairs.py`, line 1)
  - Used for: Order execution, account state queries, symbol data retrieval

**Backtesting:**
- **VectorBT Pro** - Vectorized backtesting framework (vendored in `vectorbtpro/`)
  - Location: `/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/vectorbtpro/`
  - Status: External cloned library (see `vectorbtpro/setup.py`)
  - Purpose: Portfolio optimization, signal analysis, performance metrics
  - Note: Not analyzed in detail per exclusion directive

**Data Processing:**
- **Pandas** - OHLCV data manipulation, trade analysis
  - Used in: `backtest/backtest_hybrid.py` (line 26), `backtest/backtest_strategy.py` (line 1)
  - Purpose: DataFrame operations for timeseries, trade logging

- **NumPy** - Vectorized numerical computation
  - Used in: `backtest/backtest_hybrid.py` (line 27), signal calculations

**RAG / Knowledge Layer:**
- **ChromaDB** - Vector database for semantic trade history retrieval
  - Import: `import chromadb` (see `v3_intelligence/rag_signal_filter.py`, line 21)
  - Embedding: `from chromadb.utils import embedding_functions` (line 22)
  - Purpose: Store + retrieve similar historical trades for signal confidence scoring
  - Config path: `CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_rag"` (line 28)
  - Feature: Cosine-distance similarity with weighted win rate scoring

**Data Fetching:**
- **aiohttp** - Async HTTP client for Dukascopy data downloads
  - Used in: `scripts/fetch_data.py` (line 37)
  - Purpose: Parallel download of historical forex tick data from Dukascopy free feed

- **yfinance** - Yahoo Finance API wrapper
  - Import: `import yfinance as yf` (reference in grep output)
  - Purpose: Alternative forex/equity data source (limited forex coverage)

**Databases:**
- **SQLite3** - Persistent trade journal + decision log
  - Import: `import sqlite3` (see `v3_intelligence/trade_logger.py`, line 8)
  - DB path: `data/marketmind.db`
  - Tables: `trades` (full trade history with context), `decision_log` (parameter changes)
  - Schema: See `TradeLogger._init_db()` in `v3_intelligence/trade_logger.py` (lines 29-72)

## Key Dependencies

**Critical:**
- `pandas` [latest] - Time series analysis, OHLCV data structure
- `numpy` [latest] - Numerical computation, rolling statistics (ATR, Z-score, ADX)
- `chromadb` [latest] - Vector embeddings, semantic search for RAG trades
- `MetaTrader5` [latest] - MT5 account connectivity, live order execution
- `aiohttp` [latest] - Async HTTP for parallel data downloads

**Infrastructure:**
- `sqlite3` [stdlib] - Trade journal persistence
- `lzma` [stdlib] - Dukascopy bi5 tick file decompression (see `scripts/fetch_data.py`, line 31)
- `struct` [stdlib] - Binary parsing of Dukascopy tick records (line 75)
- `asyncio` [stdlib] - Async I/O orchestration for data fetching

**Utilities:**
- `pathlib` [stdlib] - Cross-platform file path handling
- `dataclasses` [stdlib] - Configuration objects (e.g., `PairConfig` in `v3_intelligence/pair_config.py`, line 34)
- `hashlib` [stdlib] - Trade ID generation in RAG indexing (see `rag_signal_filter.py`, line 15)
- `json` [stdlib] - Decision log serialization
- `datetime/timezone` [stdlib] - Timestamp handling (especially UTC for backtests)

**Build/Development:**
- MQL5 compiler (included in MT5 terminal)
- Python 3.x standard toolchain (venv recommended)

## Configuration

**Environment:**
- No `.env` file detected in repository
- Configuration via Python dataclasses: `PairConfig` (per-pair strategy tuning)
- MT5 inputs defined as `input` directives in EA files (e.g., `MultiPairEA.mq5`, lines 20-27)

**Configuration Files:**
- `v3_intelligence/pair_config.py` - Per-pair strategy parameters (tier, size multipliers, thresholds)
  - Example: `USDJPY: tier=1, swing_size_mult=1.0, allow_m15_scalp=True`
- `backtest/backtest_hybrid.py` - Strategy thresholds hardcoded in class methods (lines 40-62)
- `ea/include/SymbolConfig.mqh` - MT5 symbol configuration structs (referenced but not analyzed)

**Strategy Configuration Model:**
```python
# From v3_intelligence/pair_config.py
@dataclass
class PairConfig:
    symbol: str
    tier: int
    swing_size_mult: float = 1.0
    swing_z_threshold: float = 2.0
    swing_target_atr: float = 4.0
    # ... 25+ total configuration fields per pair
```

## Build & Deployment

**Live/Demo Trading:**
- MT5 terminal must be open with IC Markets Raw Spread account
- Python script attaches to running MT5 via MetaTrader5 API
- EA compiled from MQL5 source in MT5 IDE (F5 key)
- Indicators compiled separately and copied to MT5 Indicators folder

**Backtesting:**
- Python scripts read CSV data files from `data/` directory
- Output: Text reports in `reports/` + trade records to `data/marketmind.db`
- VectorBT Pro framework orchestrates portfolio simulation

**Data Pipeline:**
1. `scripts/fetch_data.py` → Downloads from Dukascopy (bi5 format) → Decompresses with lzma
2. Converts ticks to OHLCV (M15, H1, Daily) → Saves as CSV to `data/`
3. `backtest/backtest_hybrid.py` loads CSV files → Runs dual strategy backtest → Logs results to SQLite

## Platform Requirements

**Development:**
- Windows/Linux/macOS with Python 3.8+
- MetaTrader 5 terminal (Windows or Wine)
- 2+ GB RAM for full 5-year forex dataset
- Network access to Dukascopy datafeed (free, no auth required)

**Production (Live Trading):**
- Windows machine (MT5 runs natively on Windows)
- IC Markets Raw Spread account ($1,000+ minimum equity)
- Stable internet connection (1:100 leverage = $10 risk per 1% trade)
- MT5 terminal left running 24/5 (forex market hours)

**Data Storage:**
- CSV files: ~20-30 MB per pair (730-day H1 history)
- SQLite DB: ~3-4 MB (marketmind.db with 1000+ trades logged)
- ChromaDB vector index: ~10-50 MB (grows with trade history)

---

*Stack analysis: 2026-04-21*
