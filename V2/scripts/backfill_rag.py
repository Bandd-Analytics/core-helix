"""V2/scripts/backfill_rag.py — One-shot RAG backfill (INFRA-03 / D-14).

Reads V2/data/marketmind.db `trades` table + embeds each row into ChromaDB
collection 'trade_memory' (D-13). Idempotent via deterministic doc_id (RESEARCH
Pitfall 4 formula: md5(symbol|strategy|entry_date|trade_id)).

Usage:
    cd V2 && python -m scripts.backfill_rag
    cd V2 && python -m scripts.backfill_rag --collection trade_memory_test --db-path /tmp/test.db

Returns the number of trades processed (printed to stdout, returned by
``run_backfill`` for programmatic callers).
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

from v3_intelligence.rag_signal_filter import (
    RAGSignalFilter, CHROMA_AVAILABLE, _make_doc_text, _make_metadata,
)
from v3_intelligence.trade_logger import DB_PATH as DEFAULT_DB_PATH


def _doc_id(trade: dict) -> str:
    """Deterministic doc_id — survives re-runs (RESEARCH Pitfall 4).

    Includes SQLite trade.id (AUTOINCREMENT, unique) so distinct rows with
    identical (symbol, strategy, entry_date) still get distinct ids; identical
    rows (same id) re-collapse to the same doc on second run.
    """
    symbol = trade.get("symbol", "")
    strategy = trade.get("strategy_type") or trade.get("type") or ""
    entry_date = trade.get("entry_date", "")
    trade_id = trade.get("id", "")
    key = f"{symbol}|{strategy}|{entry_date}|{trade_id}"
    return hashlib.md5(key.encode()).hexdigest()


def run_backfill(
    db_path: Optional[Path] = None,
    chroma_path: Optional[Path] = None,
    collection: str = "trade_memory",
) -> int:
    """Read trades from SQLite + upsert each into ChromaDB. Idempotent.

    Args:
        db_path: marketmind.db path (default: V2/data/marketmind.db)
        chroma_path: ChromaDB persistence dir (default: V2/data/chroma_rag)
        collection: ChromaDB collection name (default: 'trade_memory' per D-13)

    Returns:
        Number of trade rows read from SQLite. After a successful run this
        equals the ChromaDB collection count (idempotent re-runs collapse to
        the same final count).
    """
    if not CHROMA_AVAILABLE:
        raise ImportError("chromadb is required: pip install chromadb")

    db = db_path or DEFAULT_DB_PATH
    if not Path(db).exists():
        print(f"  WARN: {db} does not exist — nothing to backfill")
        return 0

    rag = (RAGSignalFilter(chroma_path=chroma_path, collection=collection)
           if chroma_path else RAGSignalFilter(collection=collection))

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM trades").fetchall()

    n_processed = 0
    for row in rows:
        trade = dict(row)
        # Some legacy rows have only `strategy_type`; helpers use trade['type']
        # as primary key, so backfill the alias.
        if "type" not in trade and "strategy_type" in trade:
            trade["type"] = trade["strategy_type"]
        doc_id = _doc_id(trade)
        rag._col.upsert(
            ids=[doc_id],
            documents=[_make_doc_text(trade)],
            metadatas=[_make_metadata(trade)],
        )
        n_processed += 1

    print(f"  Backfilled {n_processed} trades to ChromaDB collection "
          f"'{collection}' (idempotent — re-runs are safe)")
    return n_processed


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="backfill_rag",
        description="Phase 8.4 INFRA-03 / D-14 — one-shot RAG backfill from SQLite.",
    )
    ap.add_argument("--db-path", default=None, help="marketmind.db path")
    ap.add_argument("--chroma-path", default=None, help="ChromaDB dir")
    ap.add_argument("--collection", default="trade_memory")
    args = ap.parse_args()

    n = run_backfill(
        db_path=Path(args.db_path) if args.db_path else None,
        chroma_path=Path(args.chroma_path) if args.chroma_path else None,
        collection=args.collection,
    )
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
