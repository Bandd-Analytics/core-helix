"""End-of-trade hook closing the RAG learning loop (INFRA-03 / D-10..D-14).

Single entry point: on_trade_close(trade: dict). Synchronously:
  1. logger.log_trade(trade)            — SQLite trades table (D-10 a)
  2. _maybe_log_param_diff(trade, log)  — decision_log diff if params_json changed (D-12)
  3. rag.index_trade(trade)             — ChromaDB trade_memory upsert (D-10 c, D-13)

Phase 8 D-29: rag_signal_filter.py is preserved — this module only adds a glue
layer (no edits to embed logic / score_signal / _make_doc_text / _make_metadata).

Trade dict shape (matches V2/backtest/backtest_hybrid.py rec — lines 240-261):
  Required: symbol, type|strategy_type, entry_date, exit_date, entry_price,
            exit_price, pnl_pct, bars_held, exit_reason, session, hour_utc
  Optional: direction, daily_z, h1_z, h1_atr, vol_percentile, size, regime, notes
  D-12 for diff: params_json (JSON-string of {z_threshold, target_atr, stop_atr,
                                              size_mult, ...})
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .trade_logger import TradeLogger

try:
    from .rag_signal_filter import RAGSignalFilter, CHROMA_AVAILABLE
except ImportError:  # pragma: no cover — only triggers if chromadb is missing
    CHROMA_AVAILABLE = False  # type: ignore[assignment]
    RAGSignalFilter = None  # type: ignore[misc,assignment]


_DEFAULT_LOGGER: Optional[TradeLogger] = None
_DEFAULT_RAG: Optional["RAGSignalFilter"] = None


def _logger() -> TradeLogger:
    """Lazy-init module-level TradeLogger (RESEARCH Pattern 3)."""
    global _DEFAULT_LOGGER
    if _DEFAULT_LOGGER is None:
        _DEFAULT_LOGGER = TradeLogger()
    return _DEFAULT_LOGGER


def _rag() -> Optional["RAGSignalFilter"]:
    """Lazy-init module-level RAGSignalFilter on collection 'trade_memory' (D-13)."""
    if not CHROMA_AVAILABLE or RAGSignalFilter is None:
        return None
    global _DEFAULT_RAG
    if _DEFAULT_RAG is None:
        _DEFAULT_RAG = RAGSignalFilter(collection="trade_memory")  # D-13
    return _DEFAULT_RAG


def on_trade_close(
    trade: dict[str, Any],
    *,
    logger: Optional[TradeLogger] = None,
    rag: Optional["RAGSignalFilter"] = None,
) -> None:
    """Synchronous end-of-trade hook (D-10).

    Optional logger/rag params let tests inject mocks; production callers just
    pass `trade` and let module-level defaults handle SQLite + Chroma.

    Order:
      (1) SQLite log_trade  -> appends row to `trades` (D-10 a)
      (2) decision_log diff -> appends to `decision_log` ONLY when params changed
                               vs. the previous trade for same (symbol, strategy)
                               (D-12). Reads back from SQLite OFFSET 1 to skip
                               the row we just wrote.
      (3) RAG index_trade   -> ChromaDB upsert (D-10 c, D-13). Idempotent via
                               deterministic doc_id when caller uses the
                               RESEARCH Pitfall 4 formula.
    """
    log = logger or _logger()
    log.log_trade(trade)
    _maybe_log_param_diff(trade, log)
    embed_target = rag if rag is not None else _rag()
    if embed_target is not None:
        embed_target.index_trade(trade)


def _maybe_log_param_diff(trade: dict[str, Any], log: TradeLogger) -> None:
    """D-12 / RESEARCH open Q2 implementation.

    Compares trade['params_json'] to the previous trade's params_json for the
    same (symbol, strategy_type). For each changed key, writes a decision_log
    row.

    No-op when:
      - trade has no params_json key (e.g., backfill from legacy rows)
      - no previous trade exists for this (symbol, strategy)
      - params_json is identical to the previous trade's
    """
    cur_params = trade.get("params_json")
    if cur_params is None:
        return

    symbol = trade.get("symbol")
    strategy = trade.get("strategy_type") or trade.get("type")
    if not symbol or not strategy:
        return

    # Find previous trade for same (symbol, strategy) — exclude the row we just
    # wrote via OFFSET 1.
    # TECH DEBT: uses TradeLogger._connect (private). Replace with public
    # `get_last_params_for(symbol, strategy)` helper if Phase 9/10 evolves
    # connection management.
    with log._connect() as conn:
        prev_row = conn.execute(
            """
            SELECT params_json FROM trades
            WHERE symbol = ? AND strategy_type = ? AND params_json IS NOT NULL
            ORDER BY id DESC LIMIT 1 OFFSET 1
            """,
            (symbol, strategy),
        ).fetchone()
    if prev_row is None or prev_row["params_json"] is None:
        return

    try:
        cur = json.loads(cur_params) if isinstance(cur_params, str) else cur_params
        prev = json.loads(prev_row["params_json"])
    except (json.JSONDecodeError, TypeError):
        return

    if not isinstance(cur, dict) or not isinstance(prev, dict):
        return

    for key in cur:
        if key in prev and cur[key] != prev[key]:
            log.log_decision(
                parameter=f"{symbol}.{strategy}.{key}",
                from_value=prev[key],
                to_value=cur[key],
                rationale=f"Auto-detected change at trade {trade.get('entry_date')}",
            )


__all__ = ["on_trade_close"]
