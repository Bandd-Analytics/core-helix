-- Phase 8.4 INFRA-01 / D-02 — bars table migration provenance
--
-- Migration name: 0001_create_bars
-- Intended target: Supabase project nubmgoyyndtolsjyynln (public schema)
-- Application path: mcp__supabase__apply_migration (MCP server in /home/user/Desktop/BA.ORG/.mcp.json)
--
-- STATUS (2026-04-25): NOT YET APPLIED.
-- Plan 08.4-01 Task 2 was deferred by operator (SUPABASE_DB_URL not provisioned).
-- Plan 08.4-01 Task 3 was executed without an MCP-capable agent (mcp__supabase__* tools
--   were not injected into the resumed executor context). The DDL below is the verbatim
--   payload that mcp__supabase__apply_migration should send when re-run by an MCP-enabled
--   agent or applied directly via psql once SUPABASE_DB_URL is provisioned.
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
