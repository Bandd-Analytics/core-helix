# Supabase Trade Persistence with Outbox-Guaranteed Sync

**Date:** 2026-05-02
**Status:** Approved
**Owner:** Helix v2.0 Phase 9 (router) + Phase 10 (live execution) carry-over
**Target Supabase project:** `hrjpzgoiknvvobjshrvs` (Helix-only)

## Goal

Persist every Helix trade — live, router-sim, Phase 7 backtest, future contexts — to Supabase Postgres with a guarantee no row is silently lost, while preserving the existing local SQLite trade journal as the hot-path source of truth and keeping the RAG learning loop continuously fed from one unified corpus.

## Non-goals

- Replacing local SQLite with Supabase as the primary store.
- Synchronous block-and-retry on Supabase outages (would freeze sims and live trades).
- Changes to ChromaDB / RAG embedding schema or `rag_signal_filter.py`.
- Mirroring Phase 7 CSV-only backtests in real-time (handled by one-shot backfill).

## Architecture

### Two-tier durability

- **Tier 1 (hot, synchronous):** Local SQLite `trades` + `decision_log`. Existing `TradeLogger` path — never blocked, never fails on Supabase availability.
- **Tier 2 (durable, eventual):** Supabase `trades` + `decision_log`. Mirrored inline; outbox covers transient failures.

### Write flow (steady state)

1. Caller invokes `on_trade_close(trade)` (existing API, unchanged).
2. `TradeLogger.log_trade(trade)`:
   - SQLite `INSERT INTO trades` with `synced_to_supabase=0, sync_attempts=0`.
   - Attempt `SupabaseTradeSink.upsert_trade(...)` inline (sub-50ms when Supabase reachable).
   - On success: `UPDATE trades SET synced_to_supabase=1`. Done.
   - On failure: bump `sync_attempts`, write `last_sync_error`, leave `synced=0`. **No exception raised.** Caller continues.
3. `_maybe_log_param_diff` and `rag.index_trade` proceed normally (unchanged from current `learning_loop.on_trade_close`).

### Hard drain checkpoints

The outbox is what makes "guaranteed" actually guaranteed. Drain runs at every operation that could discard SQLite state:

- **`TradeLogger.__init__`:** drain on construction (catches restart-after-outage path).
- **`run_router_simulation()` post-loop:** drain before writing the JSON gate report — the gate result fires only when sim trades are durable to Supabase.
- **`run_router_simulation()` pre-`sim_db_path.unlink()`:** drain before any DB wipe — no row ever wiped while still in outbox.
- **CLI `--drain` flag** on `backfill_trades_to_supabase.py` for manual invocation.
- **EA graceful shutdown (Phase 10):** drain before exit (deferred to Phase 10 plan).

### Guarantee model

- When `log_trade` returns: row is durable to local SQLite (existing guarantee).
- When the outbox is empty: every row in SQLite is in Supabase. The UNIQUE constraint makes drain idempotent — running it twice never duplicates.
- A drain checkpoint runs before any operation that could discard SQLite state.
- **Therefore: no trade is ever silently lost from Supabase.** Worst case = a network outage delays Supabase visibility until the next reachable moment, but no data is dropped.

### Failure isolation

- Supabase down → SQLite still works, outbox grows, drain catches up later.
- `SUPABASE_DB_URL` unset → `SupabaseTradeSink` construction logs a single WARNING on first attempt; subsequent writes go straight to outbox state; drain becomes a no-op until env is set. (Same pattern as Phase 8.4 `cache.py`.)
- Sim crashes mid-run → SQLite has all closed trades; outbox flagged; next process drains.

## Schema

### Supabase migration `V2/migrations/0002_create_trades.sql`

```sql
-- Phase 9 follow-up — Supabase Trade Persistence (companion to 0001_create_bars)
-- Target Supabase project: hrjpzgoiknvvobjshrvs (Helix-only)
-- Application path: mcp__supabase__apply_migration

CREATE TABLE IF NOT EXISTS trades (
    id              BIGSERIAL    PRIMARY KEY,    -- Supabase-side autoincrement
    source          TEXT         NOT NULL,       -- 'live' | 'router_sim' | 'phase7_backtest' | 'temporal_analysis'
    run_id          UUID         NOT NULL,       -- groups trades from one process; live = process-start UUID
    sqlite_db       TEXT         NOT NULL,       -- 'marketmind.db' | 'router_simulation_trades.db' | ...
    sqlite_id       INTEGER      NOT NULL,       -- back-reference to local SQLite row
    logged_at       TIMESTAMPTZ  NOT NULL,
    symbol          TEXT         NOT NULL,
    strategy_type   TEXT         NOT NULL,
    entry_date      TIMESTAMPTZ  NOT NULL,
    exit_date       TIMESTAMPTZ          ,
    entry_price     NUMERIC(12, 5) NOT NULL,
    exit_price      NUMERIC(12, 5)         ,
    pnl_pct         NUMERIC                ,
    bars_held       INTEGER                ,
    session         TEXT                   ,
    exit_reason     TEXT                   ,
    size            NUMERIC                ,
    daily_z         NUMERIC                ,
    h1_z            NUMERIC                ,
    h1_atr          NUMERIC                ,
    vol_percentile  NUMERIC                ,
    hour_utc        SMALLINT               ,
    won             SMALLINT               ,
    notes           TEXT                   ,
    params_json     JSONB                  ,
    UNIQUE (source, run_id, sqlite_id)           -- idempotent upsert key
);

CREATE INDEX IF NOT EXISTS idx_trades_source_run     ON trades(source, run_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_strat   ON trades(symbol, strategy_type);
CREATE INDEX IF NOT EXISTS idx_trades_entry_date     ON trades(entry_date);

CREATE TABLE IF NOT EXISTS decision_log (
    id          BIGSERIAL    PRIMARY KEY,
    source      TEXT         NOT NULL,
    run_id      UUID         NOT NULL,
    sqlite_db   TEXT         NOT NULL,
    sqlite_id   INTEGER      NOT NULL,
    logged_at   TIMESTAMPTZ  NOT NULL,
    parameter   TEXT         NOT NULL,
    from_value  TEXT                 ,
    to_value    TEXT                 ,
    rationale   TEXT         NOT NULL,
    result      TEXT                 ,
    verdict     TEXT                 ,
    session_id  TEXT                 ,
    UNIQUE (source, run_id, sqlite_id)
);

CREATE INDEX IF NOT EXISTS idx_decision_source_param ON decision_log(source, parameter);
```

### Local SQLite extension (idempotent ALTER TABLE in `_init_db`)

`trades` adds:
- `source` TEXT — set at TradeLogger init
- `run_id` TEXT — UUID4 (process-scoped); always non-null
- `synced_to_supabase` INTEGER DEFAULT 0
- `sync_attempts` INTEGER DEFAULT 0
- `last_sync_error` TEXT

`decision_log` adds the same five columns.

All ALTER TABLEs wrapped in `try/except sqlite3.OperationalError` for `duplicate column name` (matches existing `params_json` pattern at `trade_logger.py:79-83`).

### Identity model

A trade's globally-unique identity is `(source, run_id, sqlite_id)`:

- `source` discriminates context — set on `TradeLogger.__init__`.
- `run_id` is a per-process UUID — every TradeLogger instance gets a fresh UUID at construction, including live processes. This makes wipe-and-rerun safe: re-running the same sim into the same wiped sim DB reuses sqlite_ids 1..N, but the new run_id keeps them distinguishable in Supabase.
- `sqlite_id` is the SQLite autoincrement PK on the local row.

## Components

### File map

| File | Status | Purpose |
|---|---|---|
| `V2/v3_intelligence/supabase_sink.py` | NEW | psycopg-based writer; `SupabaseTradeSink.upsert_trade/upsert_decision/drain_outbox` |
| `V2/v3_intelligence/trade_logger.py` | EXTEND | accepts `source` + `run_id`; mirrors writes; outbox state on each row |
| `V2/v3_intelligence/learning_loop.py` | EDIT | `_logger()` gets `source='live'` default; `on_trade_close` API unchanged; wrap `embed_target.index_trade(trade)` in try/except so chroma failures don't crash the trade-close path |
| `V2/backtest/router_simulation.py` | EDIT | TradeLogger constructed with `source='router_sim'` + per-run UUID; pre-wipe + post-loop drain checkpoints |
| `V2/migrations/0001_create_bars.sql` | PROVENANCE UPDATE | note re-application to hrj project |
| `V2/migrations/0002_create_trades.sql` | NEW | trades + decision_log tables |
| `V2/scripts/backfill_trades_to_supabase.py` | NEW | one-shot bulk-upsert of existing rows + Phase 7 CSVs |
| `V2/tests/v3_intelligence/test_supabase_sink.py` | NEW | unit + slow-integration tests |
| `V2/tests/v3_intelligence/test_trade_logger_outbox.py` | NEW | TradeLogger outbox state machine tests |
| `V2/.env.example` | UPDATE | document `SUPABASE_DB_URL` for hrj project |

### Component contracts

#### `SupabaseTradeSink`

```python
class SupabaseTradeSink:
    def __init__(self, db_url: str | None = None): ...
        # Reads SUPABASE_DB_URL env if db_url is None.
        # Raises SupabaseUnavailableError on construction iff env unset AND db_url None.
        # Mirrors cache.py psycopg connection style: prepare_threshold=None for pgbouncer.

    def upsert_trade(
        self,
        row: dict,
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        ...
        # Returns True on success.
        # Returns False on psycopg.OperationalError (network/timeout/auth failures).
        # Raises on programmer error (bad SQL / schema mismatch).
        # Idempotent via UNIQUE (source, run_id, sqlite_id) + ON CONFLICT DO NOTHING.

    def upsert_decision(
        self,
        row: dict,
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        ...

    def drain_outbox(
        self,
        logger: "TradeLogger",
        *,
        batch: int = 100,
    ) -> int:
        ...
        # Pulls all WHERE synced_to_supabase=0 ORDER BY id ASC LIMIT batch.
        # Per row: attempt upsert; on success mark synced=1; on failure stop drain
        # (Supabase still down). Returns count synced.
```

#### `TradeLogger` (extended)

```python
class TradeLogger:
    def __init__(
        self,
        db_path: Path = DB_PATH,
        *,
        source: str = "live",
        run_id: str | None = None,        # auto-generated UUID4 if None
        sink: SupabaseTradeSink | None = None,  # auto-constructs if None and env set
    ): ...

    # Existing methods unchanged in signature; internals augmented:
    def log_trade(self, trade: dict): ...
        # 1. SQLite insert with source/run_id/synced=0.
        # 2. If sink available: attempt upsert; mark synced=1 on success, log error on failure.
        # 3. No exceptions raised on Supabase failure.

    def log_decision(self, ...): ...   # same pattern

    def drain_outbox(self) -> int: ...
        # Drains both trades and decision_log outboxes via the configured sink.
```

## Migration application sequence

Once user authenticates `/mcp` against the new project:

1. `mcp__supabase__apply_migration(name="0001_create_bars", query=<existing SQL>)` → applies bars schema to hrj
2. `mcp__supabase__apply_migration(name="0002_create_trades", query=<new SQL>)` → applies trades + decision_log
3. Verify via `mcp__supabase__list_tables` — expect `bars`, `trades`, `decision_log`
4. Update provenance comments in both `.sql` files to record hrj application

## Backfill strategy (one-shot, idempotent)

`V2/scripts/backfill_trades_to_supabase.py`:

- Reads every row from `V2/data/marketmind.db` `trades` + `decision_log` → upserts with `source='live'`, `run_id=<deterministic UUID derived from first row's logged_at>`.
- Reads every row from `V2/reports/router_simulation_trades.db` → `source='router_sim'`, `run_id=<deterministic UUID derived from first logged_at>`.
- Phase 7 CSV backtests (`V2/reports/combined_*_trades.csv`, `daily_swing_strategy_*_trades.csv`, etc.) → `source='phase7_backtest'`, `run_id` derived from filename timestamp.
- UNIQUE constraint makes the script safely re-runnable.
- After backfill: `synced_to_supabase=1` flagged on every SQLite row.

## Test plan

### Unit (no Supabase)

`test_supabase_sink.py`:
- `upsert_trade` builds correct SQL with all columns
- Returns False on `psycopg.OperationalError`
- Honors UNIQUE constraint (idempotent on re-call)

`test_trade_logger_outbox.py`:
- `log_trade` with successful sink → row has `synced_to_supabase=1`
- `log_trade` with failing sink → `synced=0`, `sync_attempts=1`, `last_sync_error` populated, **no exception raised**
- `drain_outbox` pulls only `synced=0` rows, marks success
- `drain_outbox` stops on first failure (preserves order)
- TradeLogger init drains pending rows
- `source` and `run_id` propagate to outbox metadata

### Integration (slow, gated on `SUPABASE_DB_URL`)

- Real Supabase write/read round-trip
- Backfill idempotency (run twice, same row count)

### Regression

- All existing `test_trade_logger.py` tests still pass (additive change)
- Existing `learning_loop` flow unchanged for callers that don't pass `source` (default to `'live'`)

## Risk register

| Risk | Mitigation |
|---|---|
| `SUPABASE_DB_URL` unset → all rows queue in outbox | TradeLogger logs a single WARNING on first attempt; drain becomes no-op; user provisions URL when ready |
| Sim wipes `router_simulation_trades.db` before drain | Hard checkpoint: `run_router_simulation` calls `logger.drain_outbox()` before `sim_db_path.unlink()` |
| Outbox grows unboundedly during long outage | Drain attempts on every TradeLogger init; 4yr sim worst case ~9.6K rows in outbox before drain — acceptable; `--drain-only` CLI flag for emergencies |
| psycopg connection pooling leaks | Mirror Phase 8.4 cache.py: `prepare_threshold=None`, fresh connection per write batch, context-managed |
| Learning loop's ChromaDB indexing failure crashes `on_trade_close` | Existing code does NOT isolate the chroma call. Add `try/except Exception` around `embed_target.index_trade(trade)` in `learning_loop.on_trade_close` as part of this work — log a WARNING with trade id but never raise. Aligns with user intent that the learning loop stays available even when one tier fails. |
| LLM Hub project (`nubmgoyyndtolsjyynln`) still has orphaned `bars` schema | Out of scope here; clean up at user's convenience — no data was ever written |

## Open dependencies

- User authenticates Supabase MCP via `/mcp` against `hrjpzgoiknvvobjshrvs`.
- User provisions `SUPABASE_DB_URL` in `V2/.env` (Settings → Database → Connection pooler → Session mode → port 5432).
- Both prerequisites are non-blocking for the implementation work; they gate only the integration tests and migration application.
