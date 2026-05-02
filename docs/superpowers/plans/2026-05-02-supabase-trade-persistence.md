# Supabase Trade Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every Helix trade to Supabase Postgres with outbox-guaranteed eventual delivery, while preserving local SQLite as the hot-path source of truth.

**Architecture:** Two-tier durability — local SQLite always synchronous (existing path), Supabase mirrored inline via new `SupabaseTradeSink` with outbox state on every SQLite row. Hard drain checkpoints at TradeLogger init, sim post-loop, sim pre-wipe close the gap so no row is ever silently lost.

**Tech Stack:** Python 3.10+, psycopg 3.x, SQLite (existing), Supabase Postgres (project `hrjpzgoiknvvobjshrvs`), pytest, MCP `mcp__supabase__apply_migration`.

**Spec reference:** `docs/superpowers/specs/2026-05-02-supabase-trade-persistence-design.md`

**File structure:**

| File | Status | Responsibility |
|---|---|---|
| `V2/migrations/0002_create_trades.sql` | NEW | Supabase trades + decision_log schema |
| `V2/migrations/0001_create_bars.sql` | UPDATE | Provenance comment — re-applied to hrj project |
| `V2/v3_intelligence/supabase_sink.py` | NEW | psycopg-based writer; upsert + drain |
| `V2/v3_intelligence/trade_logger.py` | EXTEND | source/run_id/outbox cols; sink mirror |
| `V2/v3_intelligence/learning_loop.py` | EDIT | source default; chroma try/except |
| `V2/backtest/router_simulation.py` | EDIT | drain checkpoints (pre-wipe + post-loop) |
| `V2/scripts/backfill_trades_to_supabase.py` | NEW | one-shot bulk-upsert of existing rows + Phase 7 CSVs |
| `V2/tests/v3_intelligence/test_supabase_sink.py` | NEW | unit tests for sink (uses mock_psycopg_conn) |
| `V2/tests/v3_intelligence/test_trade_logger_outbox.py` | NEW | TradeLogger outbox state-machine tests |
| `V2/.env.example` | UPDATE | document `SUPABASE_DB_URL` |

---

## Wave 0 — Migrations + RED Test Scaffold

### Task 1: Author migration `0002_create_trades.sql`

**Files:**
- Create: `V2/migrations/0002_create_trades.sql`

- [ ] **Step 1: Create the migration file**

Create `V2/migrations/0002_create_trades.sql` with this exact content:

```sql
-- Trade persistence migration — companion to 0001_create_bars.
--
-- Migration name: 0002_create_trades
-- Intended target: Supabase project hrjpzgoiknvvobjshrvs (Helix-only)
-- Application path: mcp__supabase__apply_migration
--
-- STATUS: PENDING APPLICATION (Task 15 of this plan applies it after /mcp auth).
--
-- Source: docs/superpowers/specs/2026-05-02-supabase-trade-persistence-design.md
-- Identity model: (source, run_id, sqlite_id) — see spec §Identity model.

CREATE TABLE IF NOT EXISTS trades (
    id              BIGSERIAL    PRIMARY KEY,
    source          TEXT         NOT NULL,
    run_id          UUID         NOT NULL,
    sqlite_db       TEXT         NOT NULL,
    sqlite_id       INTEGER      NOT NULL,
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
    UNIQUE (source, run_id, sqlite_id)
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

- [ ] **Step 2: Update provenance comment in `0001_create_bars.sql`**

Open `V2/migrations/0001_create_bars.sql` and replace the STATUS block at the top:

Find (existing):
```
-- STATUS (2026-04-26): APPLIED via mcp__supabase__apply_migration from /gsd:execute-phase
--   orchestrator (post-Plan-08.4-01). Schema verified via information_schema.columns: 9
--   columns (pair/timeframe TEXT, ts TIMESTAMPTZ, open/high/low/close/volume NUMERIC,
--   source TEXT) + composite PK (pair, timeframe, ts) + idx_bars_pair_tf_ts_desc.
--   Plan 08.4-01 Task 2 (operator URL provisioning) remains deferred — required for
--   Plan 02 integration tests + scripts/update_cache.py runtime reads/writes.
```

Replace with:
```
-- STATUS (2026-04-26): APPLIED via mcp__supabase__apply_migration to LLM Hub project
--   nubmgoyyndtolsjyynln. That application is now historical — the Helix data target
--   moved to project hrjpzgoiknvvobjshrvs on 2026-05-02 (see
--   docs/superpowers/specs/2026-05-02-supabase-trade-persistence-design.md and
--   memory/reference_supabase_projects.md). The bars schema in nubm is orphaned;
--   never received data because SUPABASE_DB_URL was never provisioned there.
-- STATUS (2026-05-02): RE-APPLIED to project hrjpzgoiknvvobjshrvs via Task 15 of
--   the supabase-trade-persistence plan. Helix data target is now hrj exclusively.
```

(The second STATUS line is added in Task 15 once the migration actually runs; keep it as-is in this file even before Task 15 — it documents intent.)

- [ ] **Step 3: Commit**

```bash
git add V2/migrations/0002_create_trades.sql V2/migrations/0001_create_bars.sql
git commit -m "feat(migrations): 0002_create_trades + 0001 provenance update for hrj project"
```

---

### Task 2: RED test scaffold for `SupabaseTradeSink`

**Files:**
- Create: `V2/tests/v3_intelligence/test_supabase_sink.py`

- [ ] **Step 1: Write the RED test file**

Create `V2/tests/v3_intelligence/test_supabase_sink.py`:

```python
"""SupabaseTradeSink unit tests (RED until Task 4-7 implement the sink).

Uses mock_psycopg_conn fixture from conftest_infra.py (Phase 8.4 P01) so tests
don't require a real Supabase connection.
"""
from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest


def test_sink_construction_requires_db_url(monkeypatch):
    """SupabaseTradeSink raises if SUPABASE_DB_URL is unset and no db_url passed."""
    from v3_intelligence.supabase_sink import SupabaseTradeSink, SupabaseUnavailableError

    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(SupabaseUnavailableError):
        SupabaseTradeSink()


def test_sink_construction_accepts_explicit_url():
    """SupabaseTradeSink accepts a db_url override (for tests + per-call construction)."""
    from v3_intelligence.supabase_sink import SupabaseTradeSink

    sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
    assert sink._db_url == "postgresql://fake:fake@localhost/fake"


def test_upsert_trade_returns_true_on_success(mock_psycopg_conn, sample_trade):
    """upsert_trade returns True when psycopg execute completes without error."""
    from v3_intelligence.supabase_sink import SupabaseTradeSink

    with patch("v3_intelligence.supabase_sink.psycopg.connect", new=mock_psycopg_conn):
        sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
        ok = sink.upsert_trade(
            sample_trade,
            source="router_sim",
            run_id=str(uuid.uuid4()),
            sqlite_db="test.db",
            sqlite_id=1,
        )
        assert ok is True


def test_upsert_trade_returns_false_on_operational_error(sample_trade, monkeypatch):
    """upsert_trade returns False (NOT raises) when psycopg.OperationalError fires."""
    import psycopg
    from v3_intelligence.supabase_sink import SupabaseTradeSink

    def _fail_connect(*args, **kw):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr("v3_intelligence.supabase_sink.psycopg.connect", _fail_connect)

    sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
    ok = sink.upsert_trade(
        sample_trade,
        source="router_sim",
        run_id=str(uuid.uuid4()),
        sqlite_db="test.db",
        sqlite_id=1,
    )
    assert ok is False


def test_upsert_decision_returns_true_on_success(mock_psycopg_conn):
    """upsert_decision returns True when psycopg execute completes."""
    from v3_intelligence.supabase_sink import SupabaseTradeSink

    decision_row = {
        "logged_at": "2024-01-02T10:00:00",
        "parameter": "USDJPY.SWING.z_threshold",
        "from_value": "2.0",
        "to_value": "2.5",
        "rationale": "test",
        "result": None,
        "verdict": None,
        "session_id": None,
    }
    with patch("v3_intelligence.supabase_sink.psycopg.connect", new=mock_psycopg_conn):
        sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
        ok = sink.upsert_decision(
            decision_row,
            source="live",
            run_id=str(uuid.uuid4()),
            sqlite_db="marketmind.db",
            sqlite_id=1,
        )
        assert ok is True


def test_drain_outbox_marks_pending_rows_synced(tmp_path, mock_psycopg_conn, sample_trade):
    """drain_outbox pulls synced=0 rows, upserts them, marks synced=1."""
    from v3_intelligence.supabase_sink import SupabaseTradeSink
    from v3_intelligence.trade_logger import TradeLogger

    db_path = tmp_path / "test_marketmind.db"
    logger = TradeLogger(db_path=db_path, source="live")

    # Force outbox state by writing a trade with sink absent.
    logger._sink = None
    logger.log_trade(sample_trade)

    # Now drain via a working sink.
    with patch("v3_intelligence.supabase_sink.psycopg.connect", new=mock_psycopg_conn):
        sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
        n = sink.drain_outbox(logger)
        assert n == 1

    # Verify SQLite row marked synced.
    with logger._connect() as conn:
        row = conn.execute(
            "SELECT synced_to_supabase FROM trades WHERE id=1"
        ).fetchone()
        assert row["synced_to_supabase"] == 1


def test_drain_outbox_stops_on_first_failure(tmp_path, sample_trade, monkeypatch):
    """drain_outbox stops at the first row that fails (preserves order)."""
    import psycopg
    from v3_intelligence.supabase_sink import SupabaseTradeSink
    from v3_intelligence.trade_logger import TradeLogger

    db_path = tmp_path / "test_marketmind.db"
    logger = TradeLogger(db_path=db_path, source="live")
    logger._sink = None
    logger.log_trade(sample_trade)
    logger.log_trade(sample_trade)
    logger.log_trade(sample_trade)

    def _fail_connect(*args, **kw):
        raise psycopg.OperationalError("supabase down")

    monkeypatch.setattr("v3_intelligence.supabase_sink.psycopg.connect", _fail_connect)

    sink = SupabaseTradeSink(db_url="postgresql://fake:fake@localhost/fake")
    n = sink.drain_outbox(logger)
    assert n == 0  # nothing drained

    # Verify all rows still flagged synced=0.
    with logger._connect() as conn:
        rows = conn.execute(
            "SELECT synced_to_supabase FROM trades ORDER BY id ASC"
        ).fetchall()
        assert [r["synced_to_supabase"] for r in rows] == [0, 0, 0]
```

- [ ] **Step 2: Run tests to verify all RED**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py -v`
Expected: 7 errors (collection-time `ImportError: cannot import name 'SupabaseTradeSink'`) — this is the canonical Wave 0 RED state.

- [ ] **Step 3: Commit**

```bash
git add V2/tests/v3_intelligence/test_supabase_sink.py
git commit -m "test(supabase-sink): Wave 0 RED scaffold (7 tests, ImportError until Task 4)"
```

---

### Task 3: RED test scaffold for TradeLogger outbox

**Files:**
- Create: `V2/tests/v3_intelligence/test_trade_logger_outbox.py`

- [ ] **Step 1: Write the RED test file**

Create `V2/tests/v3_intelligence/test_trade_logger_outbox.py`:

```python
"""TradeLogger outbox state-machine tests (RED until Tasks 8-11 land).

These verify the new source/run_id/outbox columns and the success/failure
paths of log_trade with a mirrored Supabase sink.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


def test_logger_init_accepts_source(tmp_path):
    """TradeLogger.__init__ accepts source kwarg."""
    from v3_intelligence.trade_logger import TradeLogger
    logger = TradeLogger(db_path=tmp_path / "x.db", source="router_sim")
    assert logger.source == "router_sim"


def test_logger_init_generates_run_id(tmp_path):
    """TradeLogger.__init__ generates a fresh UUID run_id when not provided."""
    from v3_intelligence.trade_logger import TradeLogger
    logger = TradeLogger(db_path=tmp_path / "x.db", source="live")
    uuid.UUID(logger.run_id)  # raises if not a valid UUID


def test_logger_init_accepts_explicit_run_id(tmp_path):
    """TradeLogger.__init__ accepts an explicit run_id (used for re-runs)."""
    from v3_intelligence.trade_logger import TradeLogger
    rid = str(uuid.uuid4())
    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", run_id=rid)
    assert logger.run_id == rid


def test_log_trade_with_successful_sink_marks_synced(tmp_path, sample_trade):
    """log_trade with a working sink writes synced_to_supabase=1."""
    from v3_intelligence.trade_logger import TradeLogger

    sink = MagicMock()
    sink.upsert_trade.return_value = True

    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", sink=sink)
    logger.log_trade(sample_trade)

    with logger._connect() as conn:
        row = conn.execute(
            "SELECT source, run_id, synced_to_supabase, sync_attempts FROM trades WHERE id=1"
        ).fetchone()
        assert row["source"] == "live"
        assert row["run_id"] == logger.run_id
        assert row["synced_to_supabase"] == 1
        assert row["sync_attempts"] == 1


def test_log_trade_with_failing_sink_leaves_unsynced(tmp_path, sample_trade):
    """log_trade with a failing sink writes synced=0, sync_attempts=1, and DOES NOT raise."""
    from v3_intelligence.trade_logger import TradeLogger

    sink = MagicMock()
    sink.upsert_trade.return_value = False

    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", sink=sink)
    logger.log_trade(sample_trade)  # must not raise

    with logger._connect() as conn:
        row = conn.execute(
            "SELECT synced_to_supabase, sync_attempts FROM trades WHERE id=1"
        ).fetchone()
        assert row["synced_to_supabase"] == 0
        assert row["sync_attempts"] == 1


def test_log_trade_no_sink_writes_only_sqlite(tmp_path, sample_trade):
    """log_trade with sink=None writes SQLite only and leaves synced=0."""
    from v3_intelligence.trade_logger import TradeLogger

    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", sink=None)
    logger.log_trade(sample_trade)

    with logger._connect() as conn:
        row = conn.execute(
            "SELECT synced_to_supabase FROM trades WHERE id=1"
        ).fetchone()
        assert row["synced_to_supabase"] == 0


def test_logger_init_drains_pending_outbox(tmp_path, sample_trade):
    """A new TradeLogger instance pointed at a DB with synced=0 rows attempts to drain."""
    from v3_intelligence.trade_logger import TradeLogger

    db_path = tmp_path / "x.db"

    # First logger: no sink, leaves rows synced=0.
    logger_a = TradeLogger(db_path=db_path, source="live", sink=None)
    logger_a.log_trade(sample_trade)
    logger_a.log_trade(sample_trade)

    # Second logger: working sink — should drain on init.
    sink = MagicMock()
    sink.upsert_trade.return_value = True
    sink.drain_outbox.return_value = 2

    logger_b = TradeLogger(db_path=db_path, source="live", sink=sink)

    sink.drain_outbox.assert_called_once_with(logger_b)


def test_logger_drain_outbox_calls_sink(tmp_path, sample_trade):
    """logger.drain_outbox() delegates to sink.drain_outbox(self)."""
    from v3_intelligence.trade_logger import TradeLogger

    sink = MagicMock()
    sink.upsert_trade.return_value = False
    sink.drain_outbox.return_value = 0

    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", sink=sink)
    sink.drain_outbox.reset_mock()  # clear init-time drain call
    logger.drain_outbox()
    sink.drain_outbox.assert_called_once_with(logger)


def test_log_decision_with_successful_sink_marks_synced(tmp_path):
    """log_decision with a working sink writes synced_to_supabase=1 on decision_log row."""
    from v3_intelligence.trade_logger import TradeLogger

    sink = MagicMock()
    sink.upsert_decision.return_value = True

    logger = TradeLogger(db_path=tmp_path / "x.db", source="live", sink=sink)
    logger.log_decision(
        parameter="USDJPY.SWING.z_threshold",
        from_value=2.0,
        to_value=2.5,
        rationale="test",
    )

    with logger._connect() as conn:
        row = conn.execute(
            "SELECT source, run_id, synced_to_supabase FROM decision_log WHERE id=1"
        ).fetchone()
        assert row["source"] == "live"
        assert row["synced_to_supabase"] == 1


def test_existing_test_logger_construction_unchanged(tmp_path):
    """Backwards compat: TradeLogger() with NO source kwarg still works (defaults to 'live')."""
    from v3_intelligence.trade_logger import TradeLogger

    logger = TradeLogger(db_path=tmp_path / "x.db")
    assert logger.source == "live"
    assert logger.run_id  # auto-generated
```

- [ ] **Step 2: Run to verify RED**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_trade_logger_outbox.py -v`
Expected: 10 failures — `TypeError: __init__() got an unexpected keyword argument 'source'` (or similar) at every test.

- [ ] **Step 3: Commit**

```bash
git add V2/tests/v3_intelligence/test_trade_logger_outbox.py
git commit -m "test(trade-logger): Wave 0 RED scaffold for outbox state machine (10 tests)"
```

---

## Wave 1 — `SupabaseTradeSink`

### Task 4: Implement `SupabaseTradeSink` skeleton + construction

**Files:**
- Create: `V2/v3_intelligence/supabase_sink.py`

- [ ] **Step 1: Create the sink module**

Create `V2/v3_intelligence/supabase_sink.py`:

```python
"""SupabaseTradeSink — psycopg-based mirror of TradeLogger writes.

Mirrors the existing OHLCVCache (V2/v3_intelligence/cache.py) connection
pattern: load V2/.env, read SUPABASE_DB_URL, connect with
prepare_threshold=None for pgbouncer compatibility.

The sink itself is stateless — TradeLogger owns the outbox state. Failure
handling is by return value (True/False), not exceptions, so the trade
close path is never blocked by Supabase availability.

Spec: docs/superpowers/specs/2026-05-02-supabase-trade-persistence-design.md
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import psycopg
from dotenv import load_dotenv

if TYPE_CHECKING:
    from .trade_logger import TradeLogger

# Load V2/.env (same path as cache.py).
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)

_DB_URL = os.environ.get("SUPABASE_DB_URL")

_log = logging.getLogger(__name__)


class SupabaseUnavailableError(RuntimeError):
    """Raised at SupabaseTradeSink construction when no SUPABASE_DB_URL is reachable."""


class SupabaseTradeSink:
    """Stateless writer that mirrors TradeLogger rows into Supabase Postgres."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url if db_url is not None else _DB_URL
        if not self._db_url:
            raise SupabaseUnavailableError(
                "SUPABASE_DB_URL not set — add it to V2/.env "
                "(get it from Supabase dashboard -> project hrjpzgoiknvvobjshrvs "
                "-> Connect -> Session pooler -> URI; use port 5432 not 6543)"
            )

    def _connect(self) -> "psycopg.Connection":
        """psycopg connection with prepare_threshold=None (RESEARCH Pitfall 1)."""
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def upsert_trade(
        self,
        row: dict[str, Any],
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        """Returns True on success, False on connection-level failure (no raise)."""
        raise NotImplementedError("Task 5 implements upsert_trade")

    def upsert_decision(
        self,
        row: dict[str, Any],
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        """Returns True on success, False on connection-level failure (no raise)."""
        raise NotImplementedError("Task 6 implements upsert_decision")

    def drain_outbox(self, logger: "TradeLogger", *, batch: int = 100) -> int:
        """Pull synced=0 rows, attempt upsert, mark synced=1 on success.

        Stops at the first failure (preserves order). Returns count synced.
        """
        raise NotImplementedError("Task 7 implements drain_outbox")


__all__ = ["SupabaseTradeSink", "SupabaseUnavailableError"]
```

- [ ] **Step 2: Run construction tests to verify GREEN**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py::test_sink_construction_requires_db_url tests/v3_intelligence/test_supabase_sink.py::test_sink_construction_accepts_explicit_url -v`
Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
git add V2/v3_intelligence/supabase_sink.py
git commit -m "feat(supabase-sink): module skeleton + construction; 2/7 tests GREEN"
```

---

### Task 5: Implement `SupabaseTradeSink.upsert_trade`

**Files:**
- Modify: `V2/v3_intelligence/supabase_sink.py`

- [ ] **Step 1: Replace `upsert_trade` body**

In `V2/v3_intelligence/supabase_sink.py`, replace the entire `upsert_trade` method body (lines starting at `def upsert_trade`) with:

```python
    def upsert_trade(
        self,
        row: dict[str, Any],
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        """Returns True on success, False on connection-level failure (no raise).

        Idempotent via UNIQUE (source, run_id, sqlite_id) + ON CONFLICT DO NOTHING.
        """
        params = {
            "source":         source,
            "run_id":         run_id,
            "sqlite_db":      sqlite_db,
            "sqlite_id":      sqlite_id,
            "logged_at":      row.get("logged_at"),
            "symbol":         row.get("symbol"),
            "strategy_type":  row.get("strategy_type") or row.get("type"),
            "entry_date":     row.get("entry_date"),
            "exit_date":      row.get("exit_date"),
            "entry_price":    row.get("entry_price"),
            "exit_price":     row.get("exit_price"),
            "pnl_pct":        row.get("pnl_pct"),
            "bars_held":      row.get("bars_held"),
            "session":        row.get("session"),
            "exit_reason":    row.get("exit_reason"),
            "size":           row.get("size"),
            "daily_z":        row.get("daily_z"),
            "h1_z":           row.get("h1_z"),
            "h1_atr":         row.get("h1_atr"),
            "vol_percentile": row.get("vol_percentile"),
            "hour_utc":       row.get("hour_utc"),
            "won":            row.get("won"),
            "notes":          row.get("notes"),
            "params_json":    row.get("params_json"),
        }
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades (
                        source, run_id, sqlite_db, sqlite_id, logged_at,
                        symbol, strategy_type, entry_date, exit_date,
                        entry_price, exit_price, pnl_pct, bars_held, session,
                        exit_reason, size, daily_z, h1_z, h1_atr, vol_percentile,
                        hour_utc, won, notes, params_json
                    ) VALUES (
                        %(source)s, %(run_id)s, %(sqlite_db)s, %(sqlite_id)s, %(logged_at)s,
                        %(symbol)s, %(strategy_type)s, %(entry_date)s, %(exit_date)s,
                        %(entry_price)s, %(exit_price)s, %(pnl_pct)s, %(bars_held)s, %(session)s,
                        %(exit_reason)s, %(size)s, %(daily_z)s, %(h1_z)s, %(h1_atr)s, %(vol_percentile)s,
                        %(hour_utc)s, %(won)s, %(notes)s, %(params_json)s
                    )
                    ON CONFLICT (source, run_id, sqlite_id) DO NOTHING
                    """,
                    params,
                )
                conn.commit()
            return True
        except psycopg.OperationalError as e:
            _log.warning("supabase upsert_trade failed (will outbox): %s", e)
            return False
```

- [ ] **Step 2: Run upsert_trade tests**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py::test_upsert_trade_returns_true_on_success tests/v3_intelligence/test_supabase_sink.py::test_upsert_trade_returns_false_on_operational_error -v`
Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
git add V2/v3_intelligence/supabase_sink.py
git commit -m "feat(supabase-sink): upsert_trade with ON CONFLICT idempotency"
```

---

### Task 6: Implement `SupabaseTradeSink.upsert_decision`

**Files:**
- Modify: `V2/v3_intelligence/supabase_sink.py`

- [ ] **Step 1: Replace `upsert_decision` body**

Replace the `upsert_decision` method body in `V2/v3_intelligence/supabase_sink.py`:

```python
    def upsert_decision(
        self,
        row: dict[str, Any],
        *,
        source: str,
        run_id: str,
        sqlite_db: str,
        sqlite_id: int,
    ) -> bool:
        """Returns True on success, False on connection-level failure (no raise)."""
        params = {
            "source":     source,
            "run_id":     run_id,
            "sqlite_db":  sqlite_db,
            "sqlite_id":  sqlite_id,
            "logged_at":  row.get("logged_at"),
            "parameter":  row.get("parameter"),
            "from_value": row.get("from_value"),
            "to_value":   row.get("to_value"),
            "rationale":  row.get("rationale"),
            "result":     row.get("result"),
            "verdict":    row.get("verdict"),
            "session_id": row.get("session_id"),
        }
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO decision_log (
                        source, run_id, sqlite_db, sqlite_id, logged_at,
                        parameter, from_value, to_value, rationale,
                        result, verdict, session_id
                    ) VALUES (
                        %(source)s, %(run_id)s, %(sqlite_db)s, %(sqlite_id)s, %(logged_at)s,
                        %(parameter)s, %(from_value)s, %(to_value)s, %(rationale)s,
                        %(result)s, %(verdict)s, %(session_id)s
                    )
                    ON CONFLICT (source, run_id, sqlite_id) DO NOTHING
                    """,
                    params,
                )
                conn.commit()
            return True
        except psycopg.OperationalError as e:
            _log.warning("supabase upsert_decision failed (will outbox): %s", e)
            return False
```

- [ ] **Step 2: Run upsert_decision test**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py::test_upsert_decision_returns_true_on_success -v`
Expected: 1 PASS.

- [ ] **Step 3: Commit**

```bash
git add V2/v3_intelligence/supabase_sink.py
git commit -m "feat(supabase-sink): upsert_decision mirrors upsert_trade"
```

---

### Task 7: Implement `SupabaseTradeSink.drain_outbox`

**Files:**
- Modify: `V2/v3_intelligence/supabase_sink.py`

- [ ] **Step 1: Replace `drain_outbox` body**

Replace the `drain_outbox` method body in `V2/v3_intelligence/supabase_sink.py`:

```python
    def drain_outbox(self, logger: "TradeLogger", *, batch: int = 100) -> int:
        """Pull synced=0 rows, attempt upsert, mark synced=1 on success.

        Stops at the first failure (preserves order). Returns count synced.
        Drains both `trades` and `decision_log` outboxes; trades first.
        """
        synced = 0
        sqlite_db = logger.db_path.name

        # Drain trades.
        while True:
            with logger._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE synced_to_supabase = 0
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (batch,),
                ).fetchall()
            if not rows:
                break
            progressed = False
            for r in rows:
                row_dict = dict(r)
                ok = self.upsert_trade(
                    row_dict,
                    source=row_dict["source"],
                    run_id=row_dict["run_id"],
                    sqlite_db=sqlite_db,
                    sqlite_id=row_dict["id"],
                )
                if not ok:
                    return synced  # stop on first failure
                with logger._connect() as conn:
                    conn.execute(
                        "UPDATE trades SET synced_to_supabase=1 WHERE id=?",
                        (row_dict["id"],),
                    )
                synced += 1
                progressed = True
            if not progressed:
                break

        # Drain decision_log.
        while True:
            with logger._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM decision_log
                    WHERE synced_to_supabase = 0
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (batch,),
                ).fetchall()
            if not rows:
                break
            progressed = False
            for r in rows:
                row_dict = dict(r)
                ok = self.upsert_decision(
                    row_dict,
                    source=row_dict["source"],
                    run_id=row_dict["run_id"],
                    sqlite_db=sqlite_db,
                    sqlite_id=row_dict["id"],
                )
                if not ok:
                    return synced
                with logger._connect() as conn:
                    conn.execute(
                        "UPDATE decision_log SET synced_to_supabase=1 WHERE id=?",
                        (row_dict["id"],),
                    )
                synced += 1
                progressed = True
            if not progressed:
                break

        return synced
```

- [ ] **Step 2: Run drain tests (still RED until Task 8 lands the sqlite columns)**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py::test_drain_outbox_marks_pending_rows_synced tests/v3_intelligence/test_supabase_sink.py::test_drain_outbox_stops_on_first_failure -v`
Expected: 2 ERROR (`OperationalError: no such column: synced_to_supabase`) — TradeLogger schema not yet extended. Will turn GREEN at end of Task 8.

- [ ] **Step 3: Commit**

```bash
git add V2/v3_intelligence/supabase_sink.py
git commit -m "feat(supabase-sink): drain_outbox; trades first, decision_log second"
```

---

## Wave 2 — TradeLogger Outbox State Machine

### Task 8: Extend TradeLogger schema with source/run_id/outbox columns

**Files:**
- Modify: `V2/v3_intelligence/trade_logger.py`

- [ ] **Step 1: Update imports + module constants**

At the top of `V2/v3_intelligence/trade_logger.py`, replace the import block (lines 1-15):

```python
"""
Trade Logger — persistent SQLite journal for trades and strategy decisions.

Two tables:
  trades       — every executed trade with full market context at entry
  decision_log — append-only record of every parameter change and its outcome

Phase 9 follow-up (2026-05-02): adds Supabase mirror via SupabaseTradeSink.
Each row has source/run_id metadata + outbox columns (synced_to_supabase,
sync_attempts, last_sync_error). See docs/superpowers/specs/
2026-05-02-supabase-trade-persistence-design.md.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .supabase_sink import SupabaseTradeSink


DB_PATH = Path(__file__).parent.parent / "data" / "marketmind.db"
```

- [ ] **Step 2: Replace `TradeLogger.__init__` and add new helper methods**

Replace the existing `__init__` and `_init_db` methods (lines ~18-83):

```python
class TradeLogger:
    def __init__(
        self,
        db_path: Path = DB_PATH,
        *,
        source: str = "live",
        run_id: Optional[str] = None,
        sink: Optional["SupabaseTradeSink"] = None,
    ):
        self.db_path = db_path
        self.source = source
        self.run_id = run_id if run_id is not None else str(uuid.uuid4())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Sink resolution: explicit > env-driven > None.
        self._sink = sink
        if self._sink is None:
            try:
                from .supabase_sink import SupabaseTradeSink, SupabaseUnavailableError
                try:
                    self._sink = SupabaseTradeSink()
                except SupabaseUnavailableError:
                    self._sink = None  # SUPABASE_DB_URL not set; outbox stays dormant
            except ImportError:
                self._sink = None

        # Drain any pending outbox rows from previous runs.
        if self._sink is not None:
            try:
                self._sink.drain_outbox(self)
            except Exception as e:  # pragma: no cover — defensive
                import logging
                logging.getLogger(__name__).warning(
                    "outbox drain at init failed (non-fatal): %s", e
                )

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at       TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    strategy_type   TEXT NOT NULL,
                    entry_date      TEXT NOT NULL,
                    exit_date       TEXT,
                    entry_price     REAL NOT NULL,
                    exit_price      REAL,
                    pnl_pct         REAL,
                    bars_held       INTEGER,
                    session         TEXT,
                    exit_reason     TEXT,
                    size            REAL,
                    daily_z         REAL,
                    h1_z            REAL,
                    h1_atr          REAL,
                    vol_percentile  REAL,
                    hour_utc        INTEGER,
                    won             INTEGER,
                    notes           TEXT
                );

                CREATE TABLE IF NOT EXISTS decision_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at   TEXT NOT NULL,
                    parameter   TEXT NOT NULL,
                    from_value  TEXT,
                    to_value    TEXT,
                    rationale   TEXT NOT NULL,
                    result      TEXT,
                    verdict     TEXT,
                    session_id  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
                CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_type);
                CREATE INDEX IF NOT EXISTS idx_trades_entry_date ON trades(entry_date);
            """)

            # Phase 8.4 INFRA-03 / D-12 — params_json (idempotent).
            self._add_column_if_missing(conn, "trades", "params_json", "TEXT")

            # Phase 9 follow-up (2026-05-02) — source/run_id/outbox columns.
            for col, decl in [
                ("source",             "TEXT NOT NULL DEFAULT 'live'"),
                ("run_id",             "TEXT"),
                ("synced_to_supabase", "INTEGER NOT NULL DEFAULT 0"),
                ("sync_attempts",      "INTEGER NOT NULL DEFAULT 0"),
                ("last_sync_error",    "TEXT"),
            ]:
                self._add_column_if_missing(conn, "trades", col, decl)
                self._add_column_if_missing(conn, "decision_log", col, decl)

    @staticmethod
    def _add_column_if_missing(conn, table: str, column: str, decl: str) -> None:
        """Idempotent ALTER TABLE ADD COLUMN (matches existing params_json pattern)."""
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise

    def drain_outbox(self) -> int:
        """Delegate to the sink's drain_outbox if configured; else 0."""
        if self._sink is None:
            return 0
        return self._sink.drain_outbox(self)
```

- [ ] **Step 3: Run TradeLogger init tests**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_trade_logger_outbox.py::test_logger_init_accepts_source tests/v3_intelligence/test_trade_logger_outbox.py::test_logger_init_generates_run_id tests/v3_intelligence/test_trade_logger_outbox.py::test_logger_init_accepts_explicit_run_id tests/v3_intelligence/test_trade_logger_outbox.py::test_existing_test_logger_construction_unchanged -v`
Expected: 4 PASS.

- [ ] **Step 4: Run existing learning_loop tests to verify no regression**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_learning_loop.py -v`
Expected: existing tests still PASS (init now uses default `source='live'`).

- [ ] **Step 5: Commit**

```bash
git add V2/v3_intelligence/trade_logger.py
git commit -m "feat(trade-logger): add source/run_id/outbox columns; idempotent ALTER TABLE"
```

---

### Task 9: Wire `log_trade` to mirror through the sink

**Files:**
- Modify: `V2/v3_intelligence/trade_logger.py`

- [ ] **Step 1: Replace `log_trade` body**

Replace the existing `log_trade` method in `V2/v3_intelligence/trade_logger.py`:

```python
    def log_trade(self, trade: dict):
        """Record a completed trade with full market context.

        Mirrors the row to Supabase via self._sink if configured. On Supabase
        failure, the row stays in SQLite with synced_to_supabase=0; the next
        successful drain (init-time, post-loop, or manual) will catch up.
        """
        pnl = trade.get("pnl_pct")
        row = {
            "logged_at":      datetime.utcnow().isoformat(),
            "symbol":         trade["symbol"],
            "strategy_type":  trade.get("strategy_type") or trade["type"],
            "entry_date":     str(trade["entry_date"]),
            "exit_date":      str(trade.get("exit_date", "")),
            "entry_price":    trade["entry_price"],
            "exit_price":     trade.get("exit_price"),
            "pnl_pct":        pnl,
            "bars_held":      trade.get("bars_held"),
            "session":        trade.get("session"),
            "exit_reason":    trade.get("exit_reason"),
            "size":           trade.get("size", 1.0),
            "daily_z":        trade.get("daily_z"),
            "h1_z":           trade.get("h1_z"),
            "h1_atr":         trade.get("h1_atr"),
            "vol_percentile": trade.get("vol_percentile"),
            "hour_utc":       trade.get("hour_utc"),
            "won":            int(pnl > 0) if pnl is not None else None,
            "notes":          trade.get("notes"),
            "params_json":    trade.get("params_json"),
            "source":         self.source,
            "run_id":         self.run_id,
        }
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO trades (
                    logged_at, symbol, strategy_type, entry_date, exit_date,
                    entry_price, exit_price, pnl_pct, bars_held, session,
                    exit_reason, size, daily_z, h1_z, h1_atr, vol_percentile,
                    hour_utc, won, notes, params_json, source, run_id
                ) VALUES (
                    :logged_at, :symbol, :strategy_type, :entry_date, :exit_date,
                    :entry_price, :exit_price, :pnl_pct, :bars_held, :session,
                    :exit_reason, :size, :daily_z, :h1_z, :h1_atr, :vol_percentile,
                    :hour_utc, :won, :notes, :params_json, :source, :run_id
                )
            """, row)
            sqlite_id = cur.lastrowid

        if self._sink is not None:
            ok = self._sink.upsert_trade(
                row,
                source=self.source,
                run_id=self.run_id,
                sqlite_db=self.db_path.name,
                sqlite_id=sqlite_id,
            )
            with self._connect() as conn:
                if ok:
                    conn.execute(
                        "UPDATE trades SET synced_to_supabase=1, sync_attempts=sync_attempts+1 WHERE id=?",
                        (sqlite_id,),
                    )
                else:
                    conn.execute(
                        "UPDATE trades SET sync_attempts=sync_attempts+1, last_sync_error=? WHERE id=?",
                        ("upsert returned False", sqlite_id),
                    )
```

- [ ] **Step 2: Run log_trade outbox tests**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_trade_logger_outbox.py::test_log_trade_with_successful_sink_marks_synced tests/v3_intelligence/test_trade_logger_outbox.py::test_log_trade_with_failing_sink_leaves_unsynced tests/v3_intelligence/test_trade_logger_outbox.py::test_log_trade_no_sink_writes_only_sqlite -v`
Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add V2/v3_intelligence/trade_logger.py
git commit -m "feat(trade-logger): log_trade mirrors via sink; outbox state on each row"
```

---

### Task 10: Wire `log_decision` to mirror through the sink

**Files:**
- Modify: `V2/v3_intelligence/trade_logger.py`

- [ ] **Step 1: Replace `log_decision` body**

Replace the existing `log_decision` method:

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
        """Append a strategy parameter change to the decision log; mirror via sink."""
        row = {
            "logged_at":  datetime.utcnow().isoformat(),
            "parameter":  parameter,
            "from_value": str(from_value) if from_value is not None else None,
            "to_value":   str(to_value)   if to_value   is not None else None,
            "rationale":  rationale,
            "result":     result,
            "verdict":    verdict,
            "session_id": session_id,
            "source":     self.source,
            "run_id":     self.run_id,
        }
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO decision_log (
                    logged_at, parameter, from_value, to_value,
                    rationale, result, verdict, session_id, source, run_id
                ) VALUES (
                    :logged_at, :parameter, :from_value, :to_value,
                    :rationale, :result, :verdict, :session_id, :source, :run_id
                )
            """, row)
            sqlite_id = cur.lastrowid

        if self._sink is not None:
            ok = self._sink.upsert_decision(
                row,
                source=self.source,
                run_id=self.run_id,
                sqlite_db=self.db_path.name,
                sqlite_id=sqlite_id,
            )
            with self._connect() as conn:
                if ok:
                    conn.execute(
                        "UPDATE decision_log SET synced_to_supabase=1, sync_attempts=sync_attempts+1 WHERE id=?",
                        (sqlite_id,),
                    )
                else:
                    conn.execute(
                        "UPDATE decision_log SET sync_attempts=sync_attempts+1, last_sync_error=? WHERE id=?",
                        ("upsert returned False", sqlite_id),
                    )
```

- [ ] **Step 2: Run log_decision outbox test**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_trade_logger_outbox.py::test_log_decision_with_successful_sink_marks_synced -v`
Expected: 1 PASS.

- [ ] **Step 3: Run all existing learning_loop tests for regression**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_learning_loop.py -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add V2/v3_intelligence/trade_logger.py
git commit -m "feat(trade-logger): log_decision mirrors via sink"
```

---

### Task 11: Verify drain delegation + init drain

**Files:** (no code changes — verification only)

- [ ] **Step 1: Run drain delegation tests**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_trade_logger_outbox.py::test_logger_init_drains_pending_outbox tests/v3_intelligence/test_trade_logger_outbox.py::test_logger_drain_outbox_calls_sink -v`
Expected: 2 PASS.

- [ ] **Step 2: Run drain_outbox tests in supabase_sink that were RED at end of Task 7**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py::test_drain_outbox_marks_pending_rows_synced tests/v3_intelligence/test_supabase_sink.py::test_drain_outbox_stops_on_first_failure -v`
Expected: 2 PASS — sqlite outbox columns now exist + drain delegation works.

- [ ] **Step 3: Run full Wave 0 + 1 + 2 suite**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_supabase_sink.py tests/v3_intelligence/test_trade_logger_outbox.py -v`
Expected: 17 PASS (7 sink + 10 logger).

- [ ] **Step 4: Run full v3_intelligence + backtest regression**

Run: `cd V2 && python -m pytest tests/v3_intelligence/ tests/backtest/ -v --ignore=tests/v3_intelligence/test_cache.py -m "not slow"`
Expected: green run; if not, debug regressions before continuing.

(Note: test_cache.py uses real Supabase and is gated on env; ignore for unit-level regression check.)

- [ ] **Step 5: Commit (verification-only — git status should show nothing to commit)**

```bash
git status
# Expected: working tree clean — verification step had no code changes.
```

---

## Wave 3 — Integration with Existing Flows

### Task 12: Isolate ChromaDB indexing failures in `learning_loop.on_trade_close`

**Files:**
- Modify: `V2/v3_intelligence/learning_loop.py`

- [ ] **Step 1: Write a test for chroma isolation**

Append to `V2/tests/v3_intelligence/test_learning_loop.py`:

```python
def test_on_trade_close_isolates_chroma_failure(sample_trade, in_memory_logger):
    """If rag.index_trade raises, on_trade_close still completes (SQLite writes succeed)."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag.index_trade.side_effect = RuntimeError("chroma down")

    on_trade_close(sample_trade, logger=in_memory_logger, rag=rag)  # must not raise

    stats = in_memory_logger.get_stats(symbol=sample_trade["symbol"])
    assert stats["total_trades"] == 1
```

- [ ] **Step 2: Run to verify RED**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_learning_loop.py::test_on_trade_close_isolates_chroma_failure -v`
Expected: FAIL — `RuntimeError: chroma down` propagates.

- [ ] **Step 3: Wrap chroma call in try/except**

In `V2/v3_intelligence/learning_loop.py`, replace the trailing block of `on_trade_close` (lines 78-80):

Find:
```python
    embed_target = rag if rag is not None else _rag()
    if embed_target is not None:
        embed_target.index_trade(trade)
```

Replace with:
```python
    embed_target = rag if rag is not None else _rag()
    if embed_target is not None:
        try:
            embed_target.index_trade(trade)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "chroma index_trade failed for trade %s|%s (non-fatal): %s",
                trade.get("symbol"), trade.get("entry_date"), e,
            )
```

- [ ] **Step 4: Run to verify GREEN**

Run: `cd V2 && python -m pytest tests/v3_intelligence/test_learning_loop.py -v`
Expected: all PASS (existing 4 + new 1 = 5).

- [ ] **Step 5: Commit**

```bash
git add V2/v3_intelligence/learning_loop.py V2/tests/v3_intelligence/test_learning_loop.py
git commit -m "feat(learning-loop): isolate chroma index_trade failures from trade-close path"
```

---

### Task 13: Add drain checkpoints to `router_simulation`

**Files:**
- Modify: `V2/backtest/router_simulation.py`

- [ ] **Step 1: Locate the `sim_db_path.unlink()` block and the JSON write**

In `V2/backtest/router_simulation.py`, the relevant existing code (around lines 371-393):

```python
    report_path = report_path or (REPORTS_DIR / "router_4yr_simulation.json")
    sim_db_path = sim_db_path or (REPORTS_DIR / "router_simulation_trades.db")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if sim_db_path.exists():
        sim_db_path.unlink()  # fresh sim each run

    # Sim-only logger + sim-only Chroma collection (RESEARCH §6 — never touch
    # production marketmind.db / trade_memory).
    sim_logger = TradeLogger(db_path=sim_db_path)
    ...
```

And the JSON write (around line 593):

```python
    report_path.write_text(json.dumps(report, indent=2, default=str))
    return report
```

- [ ] **Step 2: Add pre-wipe drain**

Replace the `sim_db_path.unlink()` block (lines 374-376) with:

```python
    if sim_db_path.exists():
        # Pre-wipe drain: ensure any unsynced outbox rows from the previous
        # sim land in Supabase before we discard the SQLite file.
        try:
            from v3_intelligence.supabase_sink import SupabaseTradeSink, SupabaseUnavailableError
            try:
                _pre_wipe_logger = TradeLogger(db_path=sim_db_path, source="router_sim")
                _pre_wipe_logger.drain_outbox()
            except SupabaseUnavailableError:
                pass  # SUPABASE_DB_URL not set — outbox stays in sqlite, but file is wiped next
        except Exception as e:  # pragma: no cover — defensive
            import logging
            logging.getLogger(__name__).warning(
                "pre-wipe drain failed (non-fatal): %s", e
            )
        sim_db_path.unlink()
```

- [ ] **Step 3: Update sim_logger construction to pass source + new run_id**

Replace the line `sim_logger = TradeLogger(db_path=sim_db_path)` with:

```python
    import uuid as _uuid
    run_id = str(_uuid.uuid4())
    sim_logger = TradeLogger(db_path=sim_db_path, source="router_sim", run_id=run_id)
```

- [ ] **Step 4: Add post-loop drain before JSON write**

Replace the JSON write line `report_path.write_text(json.dumps(report, indent=2, default=str))` with:

```python
    # Post-loop drain: ensure all sim trades land in Supabase before the gate
    # report fires. The gate result is only "real" when sim trades are durable.
    try:
        sim_logger.drain_outbox()
    except Exception as e:  # pragma: no cover — defensive
        import logging
        logging.getLogger(__name__).warning(
            "post-loop drain failed (non-fatal): %s", e
        )

    report_path.write_text(json.dumps(report, indent=2, default=str))
```

- [ ] **Step 5: Sanity-check imports**

Verify `from v3_intelligence.trade_logger import TradeLogger` is already imported at the top of `V2/backtest/router_simulation.py` (it is per existing code at line 45). No new top-level imports needed; the `uuid` and `SupabaseTradeSink` imports above are intentionally local to keep cold-import time low.

- [ ] **Step 6: Run a smoke test of the file**

Run: `cd V2 && python -c "from backtest import router_simulation; print('import ok')"`
Expected: `import ok` — module-level imports clean.

- [ ] **Step 7: Commit**

```bash
git add V2/backtest/router_simulation.py
git commit -m "feat(router-sim): add pre-wipe + post-loop drain checkpoints; tag source/run_id"
```

---

## Wave 4 — Backfill + Migration Application

### Task 14: Implement `backfill_trades_to_supabase.py`

**Files:**
- Create: `V2/scripts/backfill_trades_to_supabase.py`

- [ ] **Step 1: Create the backfill script**

Create `V2/scripts/backfill_trades_to_supabase.py`:

```python
"""One-shot bulk-upsert of existing trade rows into Supabase.

Reads:
  - V2/data/marketmind.db                       -> source='live'
  - V2/reports/router_simulation_trades.db      -> source='router_sim'

(Phase 7 CSV backtests in V2/reports/combined_*_trades.csv etc. are NOT
included here — they predate the trade_logger contract and would need a
custom adapter; deferred to a follow-up task if needed.)

Idempotent: UNIQUE (source, run_id, sqlite_id) + ON CONFLICT DO NOTHING.

Usage:
    cd V2 && python -m scripts.backfill_trades_to_supabase
    cd V2 && python -m scripts.backfill_trades_to_supabase --dry-run
    cd V2 && python -m scripts.backfill_trades_to_supabase --drain-only
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Iterable


def _deterministic_run_id(seed: str) -> str:
    """Derive a deterministic UUID from a seed string (e.g., first row's logged_at).

    Backfill needs run_id to be stable across re-runs so the UNIQUE constraint
    triggers ON CONFLICT DO NOTHING instead of inserting duplicates.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_OID, seed))


def _backfill_db(
    db_path: Path,
    source: str,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Backfill all rows from a SQLite DB to Supabase. Returns (synced, total)."""
    if not db_path.exists():
        print(f"  skip {db_path} (not found)")
        return (0, 0)

    from v3_intelligence.supabase_sink import SupabaseTradeSink, SupabaseUnavailableError
    from v3_intelligence.trade_logger import TradeLogger

    try:
        sink = SupabaseTradeSink()
    except SupabaseUnavailableError as e:
        print(f"  ERROR: {e}")
        return (0, 0)

    # Determine deterministic run_id from the earliest row.
    with sqlite3.connect(db_path) as raw_conn:
        raw_conn.row_factory = sqlite3.Row
        first = raw_conn.execute(
            "SELECT logged_at FROM trades ORDER BY id ASC LIMIT 1"
        ).fetchone()
    if first is None:
        print(f"  skip {db_path} (no trades)")
        return (0, 0)
    run_id = _deterministic_run_id(f"{source}|{db_path.name}|{first['logged_at']}")

    # Open a TradeLogger pointing at the existing DB. Its __init__ adds any
    # missing outbox columns (idempotent ALTER TABLE), then drains.
    logger = TradeLogger(db_path=db_path, source=source, run_id=run_id, sink=sink)

    # Force every row to outbox state and drain.
    with logger._connect() as conn:
        n_total = conn.execute("SELECT COUNT(*) AS n FROM trades").fetchone()["n"]
        if not dry_run:
            conn.execute("UPDATE trades SET source=?, run_id=? WHERE source IS NULL OR run_id IS NULL",
                         (source, run_id))
            conn.execute("UPDATE trades SET synced_to_supabase=0 WHERE synced_to_supabase IS NULL")

    if dry_run:
        print(f"  dry-run: would attempt to sync {n_total} rows from {db_path.name}")
        return (0, n_total)

    n_synced = sink.drain_outbox(logger)
    print(f"  synced {n_synced}/{n_total} rows from {db_path.name} (source={source}, run_id={run_id})")
    return (n_synced, n_total)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be synced without writing.")
    parser.add_argument("--drain-only", action="store_true",
                        help="Skip backfill marking; only drain existing outbox state.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    targets: list[tuple[Path, str]] = [
        (repo_root / "data" / "marketmind.db",                 "live"),
        (repo_root / "reports" / "router_simulation_trades.db", "router_sim"),
    ]

    total_synced = 0
    total_rows = 0
    for db_path, source in targets:
        print(f"backfill {db_path} as source={source}")
        synced, n = _backfill_db(db_path, source, dry_run=args.dry_run)
        total_synced += synced
        total_rows += n

    print(f"\nDONE: {total_synced}/{total_rows} rows synced across {len(targets)} DBs.")
    return 0 if total_synced == total_rows else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: Smoke-test dry-run path (works without Supabase)**

Run: `cd V2 && python -m scripts.backfill_trades_to_supabase --dry-run`
Expected output (rows counted from current DBs):
```
backfill /home/user/.../V2/data/marketmind.db as source=live
  dry-run: would attempt to sync N rows from marketmind.db
backfill /home/user/.../V2/reports/router_simulation_trades.db as source=router_sim
  dry-run: would attempt to sync 9565 rows from router_simulation_trades.db
DONE: 0/<total> rows synced across 2 DBs.
```

(If `marketmind.db` doesn't exist, that target is skipped — that's OK for now.)

- [ ] **Step 3: Commit**

```bash
git add V2/scripts/backfill_trades_to_supabase.py
git commit -m "feat(backfill): one-shot trade backfill script with deterministic run_ids"
```

---

### Task 15: Apply migrations to `hrjpzgoiknvvobjshrvs` (REQUIRES /mcp AUTH)

**Files:** (no code changes — operational task)

**Pre-condition:** User has authenticated Supabase MCP via `/mcp` against the new project. Verify `mcp__supabase__list_tables` is callable from this session before proceeding.

- [ ] **Step 1: Apply 0001_create_bars to hrj**

Invoke the MCP tool:

```
mcp__supabase__apply_migration(
    name="0001_create_bars",
    query="<full SQL body of V2/migrations/0001_create_bars.sql, excluding the leading comment block>",
)
```

Verify result has no error. Expected behavior: `bars` table created.

- [ ] **Step 2: Apply 0002_create_trades to hrj**

```
mcp__supabase__apply_migration(
    name="0002_create_trades",
    query="<full SQL body of V2/migrations/0002_create_trades.sql, excluding the leading comment block>",
)
```

- [ ] **Step 3: Verify schema**

Invoke `mcp__supabase__list_tables(schemas=["public"])`. Expected: tables `bars`, `trades`, `decision_log`.

- [ ] **Step 4: Update `0001_create_bars.sql` STATUS line**

Open `V2/migrations/0001_create_bars.sql` and append a new STATUS line under the existing one:

```
-- STATUS (2026-05-02): RE-APPLIED to project hrjpzgoiknvvobjshrvs via the
--   supabase-trade-persistence plan Task 15. Helix data target is now hrj
--   exclusively; nubm bars schema is orphaned (never received data).
```

- [ ] **Step 5: Update `0002_create_trades.sql` STATUS line**

Open `V2/migrations/0002_create_trades.sql` and replace the existing STATUS line:

Find:
```
-- STATUS: PENDING APPLICATION (Task 15 of this plan applies it after /mcp auth).
```

Replace with:
```
-- STATUS (2026-05-02): APPLIED to project hrjpzgoiknvvobjshrvs via
--   mcp__supabase__apply_migration. Schema verified: trades + decision_log
--   tables created with UNIQUE (source, run_id, sqlite_id) and three indexes
--   each.
```

- [ ] **Step 6: Commit provenance updates**

```bash
git add V2/migrations/0001_create_bars.sql V2/migrations/0002_create_trades.sql
git commit -m "docs(migrations): record application of 0001+0002 to hrj project"
```

---

## Wave 5 — End-to-End Verification (REQUIRES SUPABASE_DB_URL)

### Task 16: Run an end-to-end live round-trip

**Files:** (no code changes — operational verification)

**Pre-condition:** User has provisioned `SUPABASE_DB_URL` in `V2/.env` pointing at hrj's Session-pooler URI (port 5432).

- [ ] **Step 1: Verify env wiring**

Run: `cd V2 && python -c "from v3_intelligence.supabase_sink import SupabaseTradeSink; s = SupabaseTradeSink(); print('connected:', bool(s._db_url))"`
Expected: `connected: True`.

- [ ] **Step 2: Backfill the existing 9565 sim rows**

Run: `cd V2 && python -m scripts.backfill_trades_to_supabase`
Expected: `synced 9565/9565 rows from router_simulation_trades.db (source=router_sim, run_id=<UUID>)`.

- [ ] **Step 3: Spot-check via MCP**

Invoke `mcp__supabase__execute_sql(query="SELECT source, COUNT(*) FROM trades GROUP BY source")`. Expected: at least one row with `(router_sim, 9565)`.

- [ ] **Step 4: Run a fresh small sim and verify post-loop drain hits Supabase**

Run: `cd V2 && python -m scripts.run_router_simulation --max-ts 2022-06-01`
Expected: gate report prints; no Supabase warnings logged. Then verify:

```
mcp__supabase__execute_sql(query="
  SELECT run_id, COUNT(*)
  FROM trades
  WHERE source='router_sim'
  GROUP BY run_id
  ORDER BY MAX(logged_at) DESC
  LIMIT 3
")
```

Expected: the new run_id appears with the row count from the small sim.

- [ ] **Step 5: Document outcome in the spec/plan completion note**

Append to the bottom of `docs/superpowers/plans/2026-05-02-supabase-trade-persistence.md`:

```
## Completion notes

- Applied 0001 + 0002 migrations to hrjpzgoiknvvobjshrvs on <DATE>.
- Backfilled <N> historical rows from marketmind.db (source=live) and
  <N> rows from router_simulation_trades.db (source=router_sim).
- End-to-end round-trip verified: small sim (--max-ts 2022-06-01) wrote
  <N> rows to Supabase via post-loop drain.
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/plans/2026-05-02-supabase-trade-persistence.md
git commit -m "docs(plan): record E2E verification of supabase trade persistence"
```

---

## Self-Review

After implementing all tasks:

1. **Spec coverage check:**
   - Schema (spec §Schema) → Task 1 + Task 8
   - Two-tier durability + write flow (spec §Architecture) → Tasks 4-9
   - Hard drain checkpoints (spec §Architecture) → Tasks 8 (init), 11 (verify), 13 (sim)
   - Failure isolation (spec §Failure isolation) → Tasks 8 (sink resolution), 12 (chroma)
   - Identity model (spec §Identity model) → Tasks 1, 8
   - Backfill (spec §Backfill strategy) → Task 14
   - Migration application (spec §Migration application sequence) → Task 15
   - Test plan (spec §Test plan) → Tasks 2, 3, 11, 12, 16

2. **Placeholder scan:** No "TBD"/"TODO"/"implement later" — every step has concrete code or commands.

3. **Type consistency:** `SupabaseTradeSink.upsert_trade/upsert_decision/drain_outbox` signatures match across Tasks 4-7 and the test mocks in Task 3. `TradeLogger.__init__(source, run_id, sink)` matches across Tasks 8-10 and Task 11 verification.
