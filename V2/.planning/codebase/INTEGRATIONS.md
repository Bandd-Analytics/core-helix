# External Integrations

**Analysis Date:** 2026-04-21

## APIs & External Services

**MetaTrader 5 (IC Markets):**
- Service: MetaTrader 5 terminal + IC Markets Raw Spread account
- What it's used for: Live/demo trading execution, position management, account equity queries
  - SDK/Client: `MetaTrader5` Python package (`import MetaTrader5 as mt5`)
  - Auth: IC Markets login credentials (configured in MT5 account settings)
  - API: `mt5.open_buy()`, `mt5.open_sell()`, `mt5.positions_get()`, `mt5.symbol_info()`
  - Referenced: `scripts/download_new_pairs.py`, entry points use MT5 API to sync account state

**Dukascopy Historical Data Feed:**
- Service: Free public HTTP datafeed (no authentication required)
- What it's used for: Historical forex tick data (OHLCV candles for backtesting)
  - Data format: bi5 (LZMA-compressed binary tick records)
  - URL pattern: `https://datafeed.dukascopy.com/datafeed/{SYM}/{YEAR}/{MONTH:02d}/{DAY:02d}/{HOUR:02d}h_ticks.bi5`
  - Client: `aiohttp.ClientSession` async HTTP downloader
  - Implementation: `scripts/fetch_data.py` (lines 48-152)
  - Symbol coverage: 8 pairs (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP, GBPNZD, EURUSD, AUDNZD)
  - Data retention: Full history from 2015-2026 available (fetched incrementally)
  - Price scaling: JPY pairs ÷1000, others ÷100000

**Yahoo Finance (Secondary):**
- Service: yfinance API (limited forex coverage)
- What it's used for: Fallback forex data source (lower priority than Dukascopy)
- SDK/Client: `yfinance` Python package (`import yfinance as yf`)
- Auth: None required
- Note: Limited to major pairs, lower granularity than Dukascopy

## Data Storage

**Databases:**

**SQLite3 (`data/marketmind.db`):**
- Purpose: Persistent trade journal + decision log
- Connection: `sqlite3.connect(str(self.db_path))` (see `v3_intelligence/trade_logger.py`, line 25)
- Tables:
  - `trades` - Every executed trade with full market context
    - Columns: id, logged_at, symbol, strategy_type, entry_date, exit_date, entry_price, exit_price, pnl_pct, bars_held, session, exit_reason, size, daily_z, h1_z, h1_atr, vol_percentile, hour_utc, won, notes
    - Indexes: idx_trades_symbol, idx_trades_strategy, idx_trades_entry_date
    - Purpose: RAG signal filtering (historical win rate lookup), performance analysis
  
  - `decision_log` - Append-only record of parameter changes
    - Columns: id, logged_at, parameter, from_value, to_value, rationale, result, verdict, session_id
    - Purpose: Strategy evolution tracking, A/B testing audit trail

**ChromaDB Vector Store (`data/chroma_rag/`):**
- Purpose: Semantic similarity search for trade context
- Embedding function: DefaultEmbeddingFunction (chromadb built-in)
- Collection: `trades`
- Distance metric: Cosine distance
- Indexing: Trade context embedded as text (symbol, strategy, z-score, session, vol regime)
- Query usage: `rag_signal_filter.py` → `score_signal()` (lines 122-212)
  - Returns: confidence (0-1), sample_size, avg_pnl, size_modifier, action (TAKE/REDUCE/SKIP)
  - Cache: Query results cached in `_rag_cache` dict to avoid redundant lookups (line 144)
- Initialize: `RAGSignalFilter(chroma_path=CHROMA_PATH, collection="trades")` (line 83)

**File Storage:**

**CSV Data Files (`data/*.csv`):**
- Format: OHLCV (datetime, Open, High, Low, Close, Volume)
- Naming: `{SYMBOL}_{TIMEFRAME}.csv`
  - Examples: `USDJPY_H1.csv`, `AUDNZD_M15.csv`, `EURGBP_DAILY.csv`
- Retention: 730-day (≈2 year) rolling window for H1, 60-day for M15, full 2015-2026 for daily
- Encoding: CSV with ISO 8601 timestamps (UTC)
- Size: ~30 MB per pair per timeframe
- Loading: `backtest_hybrid.py` loads via `pd.read_csv()` with index parsing

**Tick Data Archive (`data/chroma_rag/`):**
- Dukascopy bi5 files downloaded but not persisted (decompressed on-the-fly in memory)
- Rationale: Tick data recreated from Dukascopy each run (no local tick cache)

## Caching & In-Memory State

**Python RAG Cache:**
- Location: `backtest_hybrid.py._rag_cache` (line 68)
- Structure: Dict[(symbol, strategy_type, session, z_bucket, h1_bucket, vol_bucket, hr_bucket)] → size_modifier
- Purpose: Avoid redundant RAG queries during backtest iterations
- Lifecycle: Per-backtest-run (cleared on each instantiation)

## Authentication & Identity

**Auth Provider:**
- IC Markets: Username/password configured in MT5 account settings (not in code)
- Dukascopy: No authentication (public HTTP endpoints)
- yfinance: No authentication

**Secrets Location:**
- `.env` file: Not detected (no environment variable config)
- MT5 credentials: Stored in MT5 terminal profile (outside codebase)
- Approach: Manual MT5 login before running live trading scripts

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, or external error service)
- Approach: Console logging + SQLite decision log for parameter changes
- MT5 Journal: Built-in MT5 terminal journal captures EA execution logs

**Logs:**
- **MT5 Journal Tab**: Captures OnInit(), OnTimer(), order execution errors (internal to MT5)
- **CSV Trade Journal**: `MarketMind_Journal_YYYY-MM-DD.csv` written by EA (see `ea/include/CLogger.mqh`)
  - Path: MT5 terminal data folder
  - Columns: datetime, symbol, type, entry_price, exit_price, pnl, bars_held, reason
- **Python Backtest Reports**: Text files in `reports/` directory
  - Example: `reports/daily_swing_strategy_2026-04-21_12-31-55.txt`
  - Content: Trade summary, Sharpe ratio, max drawdown, win rate, trade-by-trade log

**Console Output:**
- Backtests print Sharpe ratio, max DD, win rate to stdout
- Python scripts log to terminal (no file output except CSV results)

## CI/CD & Deployment

**Hosting:**
- None (local Windows machine required for MT5)
- IC Markets account hosts live positions (no separate infrastructure)

**CI Pipeline:**
- None detected
- Manual workflow: User runs `python backtest_hybrid.py --swing` → reviews reports → deploys EA to MT5

**Deployment Steps:**
1. Compile MQL5 indicators in MT5 IDE (F5 key) → `%AppData%/MetaQuotes/Terminal/[TerminalID]/MQL5/Indicators/`
2. Copy EA + include files to EA folder → Compile EA
3. Attach EA to EURUSD H1 chart → Configure input parameters → Enable AutoTrading

## Environment Configuration

**Required Env Vars:**
- None (configuration hardcoded in Python dataclasses)
- MT5 credentials stored in MT5 profile (not in code)

**Optional Env Vars:**
- `PYTHONPATH`: May need adjustment if running from outside project root

**Key Configuration Parameters (hardcoded):**
```python
# backtest_hybrid.py
LONDON_HOURS = frozenset(range(7, 12))    # UTC session window
NY_HOURS = frozenset(range(13, 18))
enable_rag = True                          # Enable RAG signal filtering
enable_logging = True                      # Enable SQLite logging
enable_changepoint = True                  # Enable regime detection
enable_hurst_filter = False                # Disabled by default
```

```python
# pair_config.py (per-pair overrides)
PAIR_CONFIGS = {
    "USDJPY": PairConfig(
        tier=1,
        swing_size_mult=1.0,
        allow_m15_scalp=True,
        m15_z_threshold=2.0,
        m15_size_mult=0.5,
    ),
    # ... 7 more pairs
}
```

## Webhooks & Callbacks

**Incoming:**
- None (EA is passive, responds to 1-second timer in MT5)

**Outgoing:**
- None (no external event notifications)
- Logging is write-only: SQLite trades table, CSV journal file

## Data Flow & Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKTEST PIPELINE                         │
└─────────────────────────────────────────────────────────────┘

Dukascopy HTTP Feed
       ↓
scripts/fetch_data.py (async download + lzma decompress)
       ↓
data/{SYM}_H1.csv, data/{SYM}_M15.csv
       ↓
backtest/backtest_hybrid.py (load CSV, run dual strategy)
       ↓
       ├→ TradeLogger.log_trade() → data/marketmind.db (trades table)
       ├→ RAGSignalFilter.index_trades() → data/chroma_rag/ (vector index)
       └→ Text reports → reports/*.txt
       
┌─────────────────────────────────────────────────────────────┐
│                     LIVE TRADING PIPELINE                    │
└─────────────────────────────────────────────────────────────┘

MT5 Terminal (IC Markets account)
       ↓
MultiPairEA.mq5 (OnTimer event every 1 second)
       ├→ Load indicator values via iCustom()
       ├→ Generate signal scores
       └→ Submit orders via CTrade
       ↓
CLogger.mqh (write CSV journal)
       ↓
MarketMind_Journal_YYYY-MM-DD.csv
       
(Optional: Python script reads marketmind.db for RAG initialization)
```

## Integration Status & Maturity

| Component | Status | Notes |
|-----------|--------|-------|
| Dukascopy data feed | Stable | Free, no auth, robust error handling |
| MT5 API | Stable | Live trading tested on IC Markets Raw |
| ChromaDB vector store | Beta | Used for signal confidence, cache optimization ongoing |
| SQLite trade journal | Stable | Core audit trail for backtest analysis |
| yfinance (fallback) | Available | Not actively used (Dukascopy preferred) |

---

*Integration audit: 2026-04-21*
