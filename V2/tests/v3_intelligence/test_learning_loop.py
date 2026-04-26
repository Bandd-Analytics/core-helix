"""learning_loop.on_trade_close tests (INFRA-03 / D-10..D-13).

RED until Plan 04 lands V2/v3_intelligence/learning_loop.py.
Uses in_memory_logger + mock_chroma_collection from conftest_infra.py.
"""
from __future__ import annotations

import pytest


def test_on_trade_close_writes_sqlite(sample_trade, in_memory_logger,
                                        mock_chroma_collection) -> None:
    """D-10 (a): on_trade_close writes 1 row to SQLite trades."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag._col = mock_chroma_collection
    rag.index_trade.side_effect = lambda t: mock_chroma_collection.upsert(
        ids=[f"{t['symbol']}|{t['entry_date']}"],
        documents=["doc"], metadatas=[{}],
    )
    on_trade_close(sample_trade, logger=in_memory_logger, rag=rag)

    stats = in_memory_logger.get_stats(symbol=sample_trade["symbol"])
    assert stats["total_trades"] == 1


def test_on_trade_close_calls_rag_index(sample_trade, in_memory_logger,
                                          mock_chroma_collection) -> None:
    """D-10 (c) / D-13: on_trade_close invokes rag.index_trade exactly once."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag._col = mock_chroma_collection
    on_trade_close(sample_trade, logger=in_memory_logger, rag=rag)
    rag.index_trade.assert_called_once_with(sample_trade)


def test_on_trade_close_writes_decision_log_on_param_change(
    sample_trade, in_memory_logger, mock_chroma_collection
) -> None:
    """D-12: when strategy params change between two consecutive trades for the same
    (symbol, strategy), a decision_log row is written."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag._col = mock_chroma_collection

    t1 = dict(sample_trade)
    t1["params_json"] = '{"swing_z_threshold": 2.0, "swing_target_atr": 4.0}'
    on_trade_close(t1, logger=in_memory_logger, rag=rag)

    t2 = dict(sample_trade)
    t2["params_json"] = '{"swing_z_threshold": 2.5, "swing_target_atr": 4.0}'  # changed z
    on_trade_close(t2, logger=in_memory_logger, rag=rag)

    decisions = in_memory_logger.get_recent_decisions(20)
    assert any("swing_z_threshold" in d["parameter"] for d in decisions), \
        "Expected decision_log entry for swing_z_threshold change (D-12)"


def test_on_trade_close_no_decision_log_when_params_unchanged(
    sample_trade, in_memory_logger, mock_chroma_collection
) -> None:
    """D-12: when params identical to previous trade, no decision_log row written."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag._col = mock_chroma_collection

    t = dict(sample_trade)
    t["params_json"] = '{"swing_z_threshold": 2.0}'
    on_trade_close(t, logger=in_memory_logger, rag=rag)
    on_trade_close(t, logger=in_memory_logger, rag=rag)

    decisions = in_memory_logger.get_recent_decisions(20)
    assert len(decisions) == 0


def test_on_trade_close_chroma_idempotent_by_doc_id(
    sample_trade, in_memory_logger, mock_chroma_collection
) -> None:
    """RESEARCH Pitfall 4: deterministic doc_id ensures double-call has 1 ChromaDB doc, 2 SQLite rows."""
    from unittest.mock import MagicMock
    from v3_intelligence.learning_loop import on_trade_close

    rag = MagicMock()
    rag._col = mock_chroma_collection
    def _idx(t):
        # Deterministic doc_id includes symbol + entry_date + strategy
        doc_id = f"{t['symbol']}|{t.get('strategy', t.get('type'))}|{t['entry_date']}"
        mock_chroma_collection.upsert(ids=[doc_id], documents=["d"], metadatas=[{}])
    rag.index_trade.side_effect = _idx

    on_trade_close(sample_trade, logger=in_memory_logger, rag=rag)
    on_trade_close(sample_trade, logger=in_memory_logger, rag=rag)

    sqlite_count = in_memory_logger.get_stats(symbol=sample_trade["symbol"])["total_trades"]
    chroma_count = mock_chroma_collection.count()
    assert sqlite_count == 2  # SQLite has no de-dup
    assert chroma_count == 1  # ChromaDB upsert + deterministic doc_id deduplicates


def test_on_trade_close_uses_default_logger_when_not_injected(sample_trade, monkeypatch,
                                                                 tmp_path) -> None:
    """RESEARCH Pattern 3: default module-level logger is constructed lazily (production calls)."""
    monkeypatch.setattr("v3_intelligence.trade_logger.DB_PATH", tmp_path / "default.db")
    from v3_intelligence import learning_loop
    monkeypatch.setattr(learning_loop, "_DEFAULT_LOGGER", None)
    monkeypatch.setattr(learning_loop, "_DEFAULT_RAG", None)
    # rag still mocked to avoid real ChromaDB
    from unittest.mock import MagicMock
    fake_rag = MagicMock()
    monkeypatch.setattr(learning_loop, "_rag", lambda: fake_rag)
    learning_loop.on_trade_close(sample_trade)
    fake_rag.index_trade.assert_called_once()
