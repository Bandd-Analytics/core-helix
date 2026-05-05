"""RED tests for V2/scripts/pull_live_trades.py — live MT5 -> TradeLogger ingestion.

Covers:
  Schema    — `broker_position_id` column on trades + idempotent migration
  Logger    — log_trade_if_new(trade) returns False on duplicate, True on insert
  Parser    — parse_strategy_from_comment maps EA tags / falls back to MANUAL_*
  Pairing   — pair_deals_to_trades collapses (open, close) deal pairs into trade rows
  File-drop — load_inbox_deals reads V2/data/live/inbox/*.json
  Since arg — parse_since handles 'today', 'auto' (empty / populated journal), ISO date
  Heartbeat — record_heartbeat appends a decision_log row
  Ingest    — end-to-end: deals -> ingest -> rows in trades + duplicate runs are no-ops
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Schema migration tests
# ─────────────────────────────────────────────────────────────────────────────


def test_broker_position_id_column_exists(tmp_path) -> None:
    """trades table has a broker_position_id TEXT column after fresh init."""
    from v3_intelligence.trade_logger import TradeLogger
    db = tmp_path / "schema.db"
    _ = TradeLogger(db_path=db)
    with sqlite3.connect(db) as raw:
        cols = {row[1] for row in raw.execute("PRAGMA table_info(trades)").fetchall()}
    assert "broker_position_id" in cols, (
        f"trades.broker_position_id missing — got columns {sorted(cols)!r}"
    )


def test_broker_position_id_unique_index_exists(tmp_path) -> None:
    """A UNIQUE index on broker_position_id is created (partial: WHERE NOT NULL).

    The index is what makes log_trade_if_new able to use INSERT OR IGNORE
    semantics safely; without it duplicates would slip through.
    """
    from v3_intelligence.trade_logger import TradeLogger
    db = tmp_path / "index.db"
    _ = TradeLogger(db_path=db)
    with sqlite3.connect(db) as raw:
        idx_rows = raw.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='trades'"
        ).fetchall()
    names = [r[0] for r in idx_rows]
    assert any("broker_position_id" in n for n in names), (
        f"No index on broker_position_id — got {names!r}"
    )


def test_migration_idempotent_on_existing_db(tmp_path) -> None:
    """Re-initializing TradeLogger on an existing DB does not raise.

    Mirrors the params_json idempotent-ALTER pattern at trade_logger.py:117.
    """
    from v3_intelligence.trade_logger import TradeLogger
    db = tmp_path / "idem.db"
    _ = TradeLogger(db_path=db)        # first init creates schema
    _ = TradeLogger(db_path=db)        # second init must NOT raise


# ─────────────────────────────────────────────────────────────────────────────
# log_trade_if_new tests
# ─────────────────────────────────────────────────────────────────────────────


def test_log_trade_if_new_inserts_when_unseen(in_memory_logger, sample_trade) -> None:
    """First call with a fresh broker_position_id inserts and returns True."""
    trade = dict(sample_trade)
    trade["broker_position_id"] = "777001"
    inserted = in_memory_logger.log_trade_if_new(trade)
    assert inserted is True, "Expected True on first insert"
    with in_memory_logger._connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE broker_position_id = ?", ("777001",)
        ).fetchone()[0]
    assert n == 1, f"Expected exactly 1 row for ticket 777001, got {n}"


def test_log_trade_if_new_skips_duplicate(in_memory_logger, sample_trade) -> None:
    """Second call with the same broker_position_id returns False, no extra row."""
    trade = dict(sample_trade)
    trade["broker_position_id"] = "777002"
    assert in_memory_logger.log_trade_if_new(trade) is True
    again = in_memory_logger.log_trade_if_new(trade)
    assert again is False, "Expected False on duplicate broker_position_id"
    with in_memory_logger._connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE broker_position_id = ?", ("777002",)
        ).fetchone()[0]
    assert n == 1, f"Duplicate broker_position_id created {n} rows; should be 1"


# ─────────────────────────────────────────────────────────────────────────────
# parse_strategy_from_comment tests
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_strategy_recognized_router_tag() -> None:
    """Recognized router tags pass through verbatim."""
    from scripts.pull_live_trades import parse_strategy_from_comment
    for tag in (
        "DAILY_SWING_LONG", "DAILY_SWING_SHORT",
        "H1_SCALP_LONG", "H1_SCALP_SHORT",
        "M15_SCALP_LONG", "M15_SCALP_SHORT",
        "H1_MOMENTUM_LONG", "H1_MOMENTUM_SHORT",
    ):
        assert parse_strategy_from_comment(tag, deal_type="buy") == tag, (
            f"Recognized tag {tag!r} must round-trip"
        )


def test_parse_strategy_unknown_comment_long() -> None:
    """Empty / unrecognized comment + buy deal -> MANUAL_LONG."""
    from scripts.pull_live_trades import parse_strategy_from_comment
    assert parse_strategy_from_comment("", deal_type="buy") == "MANUAL_LONG"
    assert parse_strategy_from_comment("yolo", deal_type="buy") == "MANUAL_LONG"


def test_parse_strategy_unknown_comment_short() -> None:
    """Empty / unrecognized comment + sell deal -> MANUAL_SHORT."""
    from scripts.pull_live_trades import parse_strategy_from_comment
    assert parse_strategy_from_comment("", deal_type="sell") == "MANUAL_SHORT"
    assert parse_strategy_from_comment("hand-placed", deal_type="sell") == "MANUAL_SHORT"


# ─────────────────────────────────────────────────────────────────────────────
# pair_deals_to_trades tests
# ─────────────────────────────────────────────────────────────────────────────


def _deal(position_id, ticket, deal_type, price, time, symbol="EURUSD",
          volume=0.01, comment="", profit=0.0):
    return {
        "position_id": position_id,
        "ticket": ticket,
        "type": deal_type,            # "buy" | "sell"
        "symbol": symbol,
        "volume": volume,
        "price": price,
        "time": time,                 # ISO-8601 string
        "comment": comment,
        "profit": profit,
    }


def test_pair_deals_long_position() -> None:
    """A buy-then-sell pair on one position_id collapses to one LONG trade row.

    pnl_pct must be (exit - entry) / entry (positive when sell > buy).
    """
    from scripts.pull_live_trades import pair_deals_to_trades
    deals = [
        _deal(101, 1, "buy",  1.10000, "2026-05-05T08:00:00+00:00",
              comment="MANUAL", profit=0.0),
        _deal(101, 2, "sell", 1.10550, "2026-05-05T11:30:00+00:00",
              comment="MANUAL", profit=0.55),
    ]
    trades = pair_deals_to_trades(deals)
    assert len(trades) == 1, f"Expected 1 paired trade, got {len(trades)}"
    t = trades[0]
    assert t["broker_position_id"] == "101"
    assert t["symbol"] == "EURUSD"
    assert t["type"] == "MANUAL_LONG"
    assert t["entry_price"] == pytest.approx(1.10000)
    assert t["exit_price"] == pytest.approx(1.10550)
    assert t["pnl_pct"] == pytest.approx((1.10550 - 1.10000) / 1.10000, rel=1e-6)


def test_pair_deals_short_position() -> None:
    """A sell-then-buy pair collapses to one SHORT trade row.

    pnl_pct for shorts is (entry - exit) / entry (positive when buy < sell).
    """
    from scripts.pull_live_trades import pair_deals_to_trades
    deals = [
        _deal(202, 10, "sell", 150.500, "2026-05-05T08:00:00+00:00",
              symbol="USDJPY", comment="", profit=0.0),
        _deal(202, 11, "buy",  149.900, "2026-05-05T13:00:00+00:00",
              symbol="USDJPY", comment="", profit=0.60),
    ]
    trades = pair_deals_to_trades(deals)
    assert len(trades) == 1
    t = trades[0]
    assert t["type"] == "MANUAL_SHORT"
    assert t["entry_price"] == pytest.approx(150.500)
    assert t["exit_price"] == pytest.approx(149.900)
    assert t["pnl_pct"] == pytest.approx((150.500 - 149.900) / 150.500, rel=1e-6)


def test_pair_deals_open_position_skipped() -> None:
    """A position with only one deal (still open) is NOT yielded."""
    from scripts.pull_live_trades import pair_deals_to_trades
    deals = [
        _deal(303, 20, "buy", 1.30000, "2026-05-05T09:00:00+00:00"),
    ]
    trades = pair_deals_to_trades(deals)
    assert trades == [], "Open positions must not appear in journal output"


# ─────────────────────────────────────────────────────────────────────────────
# load_inbox_deals tests
# ─────────────────────────────────────────────────────────────────────────────


def test_load_inbox_reads_all_json(tmp_path) -> None:
    """Multiple .json files under inbox/ are concatenated."""
    from scripts.pull_live_trades import load_inbox_deals
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "2026-05-05_morning.json").write_text(json.dumps([
        _deal(1, 100, "buy",  1.1, "2026-05-05T08:00:00+00:00"),
        _deal(1, 101, "sell", 1.2, "2026-05-05T09:00:00+00:00"),
    ]))
    (inbox / "2026-05-05_afternoon.json").write_text(json.dumps([
        _deal(2, 200, "sell", 1.5, "2026-05-05T13:00:00+00:00"),
    ]))
    deals = load_inbox_deals(inbox)
    assert len(deals) == 3, f"Expected 3 deals across 2 files, got {len(deals)}"


def test_load_inbox_missing_dir_returns_empty(tmp_path) -> None:
    """Inbox dir absent -> empty list, no error (puller may run before any drops)."""
    from scripts.pull_live_trades import load_inbox_deals
    deals = load_inbox_deals(tmp_path / "no_such_inbox")
    assert deals == []


# ─────────────────────────────────────────────────────────────────────────────
# parse_since tests
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_since_today_returns_midnight_utc() -> None:
    from scripts.pull_live_trades import parse_since
    now = datetime(2026, 5, 5, 14, 23, 17, tzinfo=timezone.utc)
    got = parse_since("today", logger=None, now=now)
    assert got == datetime(2026, 5, 5, 0, 0, 0, tzinfo=timezone.utc)


def test_parse_since_iso_date_passthrough() -> None:
    from scripts.pull_live_trades import parse_since
    got = parse_since("2026-04-30", logger=None, now=None)
    assert got == datetime(2026, 4, 30, 0, 0, 0, tzinfo=timezone.utc)


def test_parse_since_auto_empty_logger_falls_back_30d(in_memory_logger) -> None:
    """auto + empty journal -> 30 days before `now`."""
    from scripts.pull_live_trades import parse_since
    now = datetime(2026, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
    got = parse_since("auto", logger=in_memory_logger, now=now)
    assert got == now - timedelta(days=30)


# ─────────────────────────────────────────────────────────────────────────────
# heartbeat + end-to-end ingest tests
# ─────────────────────────────────────────────────────────────────────────────


def test_record_heartbeat_writes_decision_log(in_memory_logger) -> None:
    """record_heartbeat appends a row with parameter='heartbeat:pull_live_trades'."""
    from scripts.pull_live_trades import record_heartbeat
    record_heartbeat(in_memory_logger, source="inbox",
                     summary={"inserted": 2, "skipped": 1})
    rows = in_memory_logger.get_recent_decisions(5)
    assert any(r["parameter"] == "heartbeat:pull_live_trades" for r in rows), (
        f"No heartbeat row in decision_log; got {[r['parameter'] for r in rows]}"
    )


def test_ingest_idempotent_over_two_runs(in_memory_logger) -> None:
    """Running ingest twice with the same deals inserts once, dupes counted second run."""
    from scripts.pull_live_trades import ingest_deals
    deals = [
        _deal(901, 1000, "buy",  1.10000, "2026-05-05T08:00:00+00:00",
              comment="H1_SCALP_LONG"),
        _deal(901, 1001, "sell", 1.10100, "2026-05-05T09:00:00+00:00",
              comment="H1_SCALP_LONG"),
    ]
    first = ingest_deals(deals, logger=in_memory_logger)
    second = ingest_deals(deals, logger=in_memory_logger)

    assert first["inserted"] == 1, f"First run should insert 1, got {first}"
    assert first["skipped"] == 0
    assert second["inserted"] == 0, f"Second run should insert 0, got {second}"
    assert second["skipped"] == 1, f"Second run should skip 1 dup, got {second}"

    with in_memory_logger._connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE broker_position_id = '901'"
        ).fetchone()[0]
    assert n == 1, f"After 2 idempotent runs there must be 1 row for position 901, got {n}"


def test_ingest_uses_recognized_strategy_from_comment(in_memory_logger) -> None:
    """End-to-end: comment 'H1_SCALP_LONG' lands in strategy_type column."""
    from scripts.pull_live_trades import ingest_deals
    deals = [
        _deal(902, 2000, "buy",  1.20000, "2026-05-05T08:00:00+00:00",
              comment="H1_SCALP_LONG"),
        _deal(902, 2001, "sell", 1.20300, "2026-05-05T10:00:00+00:00",
              comment="H1_SCALP_LONG"),
    ]
    ingest_deals(deals, logger=in_memory_logger)
    with in_memory_logger._connect() as conn:
        row = conn.execute(
            "SELECT strategy_type FROM trades WHERE broker_position_id = '902'"
        ).fetchone()
    assert row is not None, "Trade not inserted"
    assert row["strategy_type"] == "H1_SCALP_LONG"
