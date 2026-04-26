"""V2/scripts/backfill_rag.py one-shot backfill tests (INFRA-03 / D-14).

@pytest.mark.slow — runs scripts.backfill_rag against an isolated SQLite + temp Chroma.
RED until Plan 04 lands the script.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


def test_backfill_rag_count_matches_sqlite(in_memory_logger, sample_trade, tmp_path) -> None:
    """D-14: after backfill, ChromaDB collection count == SQLite trades count."""
    # Seed SQLite with N trades
    n = 5
    for i in range(n):
        t = dict(sample_trade)
        t["entry_date"] = f"2024-01-0{i+1} 10:00"
        in_memory_logger.log_trade(t)

    from scripts.backfill_rag import run_backfill
    chroma_path = tmp_path / "chroma_test"
    counted = run_backfill(db_path=in_memory_logger.db_path,
                            chroma_path=chroma_path,
                            collection="trade_memory_test")
    assert counted == n


def test_backfill_rag_idempotent_second_run(in_memory_logger, sample_trade, tmp_path) -> None:
    """D-14: second run inserts 0 new docs (deterministic doc_id)."""
    in_memory_logger.log_trade(sample_trade)
    from scripts.backfill_rag import run_backfill
    chroma_path = tmp_path / "chroma_test"
    n1 = run_backfill(db_path=in_memory_logger.db_path,
                       chroma_path=chroma_path,
                       collection="trade_memory_test")
    n2 = run_backfill(db_path=in_memory_logger.db_path,
                       chroma_path=chroma_path,
                       collection="trade_memory_test")
    assert n1 == 1
    assert n2 == 1  # Same trades — upsert == 1 doc total
