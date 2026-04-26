-- Phase 8.4 INFRA-01 / D-02 — bars table migration provenance
--
-- Migration name: 0001_create_bars
-- Intended target: Supabase project nubmgoyyndtolsjyynln (public schema)
-- Application path: mcp__supabase__apply_migration (MCP server in /home/user/Desktop/BA.ORG/.mcp.json)
--
-- STATUS (2026-04-26): APPLIED via mcp__supabase__apply_migration from /gsd:execute-phase
--   orchestrator (post-Plan-08.4-01). Schema verified via information_schema.columns: 9
--   columns (pair/timeframe TEXT, ts TIMESTAMPTZ, open/high/low/close/volume NUMERIC,
--   source TEXT) + composite PK (pair, timeframe, ts) + idx_bars_pair_tf_ts_desc.
--   Plan 08.4-01 Task 2 (operator URL provisioning) remains deferred — required for
--   Plan 02 integration tests + scripts/update_cache.py runtime reads/writes.
--
-- Operator follow-up to apply:
--   Option A (MCP):   spawn an executor with mcp__supabase__* tools attached, then run
--                     mcp__supabase__apply_migration(name="0001_create_bars", query=<below>)
--   Option B (psql):  load V2/.env (SUPABASE_DB_URL with port 5432 — Session pooler — per
--                     RESEARCH Pitfall 1), then `psql "$SUPABASE_DB_URL" -f V2/migrations/0001_create_bars.sql`
--   Option C (Python): `python -c "from dotenv import load_dotenv; load_dotenv('V2/.env'); ...
--                       psycopg.connect(os.environ['SUPABASE_DB_URL'], prepare_threshold=None)"
--                       and execute the SQL inline.
--
-- After application, the migration name '0001_create_bars' will be tracked in
-- supabase_migrations.schema_migrations (when applied via MCP or supabase CLI).
--
-- Source: 08.4-RESEARCH.md §"Code Examples" → "Postgres composite PK with idempotent migration"
-- Pinned by: 08.4-CONTEXT.md D-02 (single bars table; composite PK; NUMERIC for prices; source col)

CREATE TABLE IF NOT EXISTS bars (
    pair       TEXT        NOT NULL,
    timeframe  TEXT        NOT NULL,
    ts         TIMESTAMPTZ NOT NULL,
    open       NUMERIC(12, 5) NOT NULL,
    high       NUMERIC(12, 5) NOT NULL,
    low        NUMERIC(12, 5) NOT NULL,
    close      NUMERIC(12, 5) NOT NULL,
    volume     NUMERIC(20, 0)         ,
    source     TEXT        NOT NULL,
    PRIMARY KEY (pair, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_bars_pair_tf_ts_desc ON bars (pair, timeframe, ts DESC);

COMMENT ON TABLE bars IS 'OHLCV cache. Phase 8.4 INFRA-01. Source-of-truth for all backtests + Phase 9 router replay.';
