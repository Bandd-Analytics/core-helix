"""
RAG Signal Filter — semantic retrieval for signal confidence scoring.

How it works:
  1. Every completed trade is stored as a ChromaDB document with its market
     context embedded as text (symbol, z-scores, session, vol regime, etc.)
  2. When a new signal fires, we embed the same context and retrieve the
     k most similar historical trades
  3. We return a confidence score (0–1) based on historical win rate of
     similar conditions, plus a size modifier the caller can apply

No API key required. Uses chromadb's default local embedding model.
"""
import json
import hashlib
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_rag"


def _make_doc_text(trade: dict) -> str:
    """Serialize a trade's market context into a searchable text document."""
    symbol        = trade.get("symbol", "UNKNOWN")
    strategy      = trade.get("type") or trade.get("strategy_type", "UNKNOWN")
    session       = trade.get("session", "UNKNOWN")
    daily_z       = trade.get("daily_z", 0.0) or 0.0
    h1_z          = trade.get("h1_z", 0.0) or 0.0
    vol_pct       = trade.get("vol_percentile", 50.0) or 50.0
    hour          = trade.get("hour_utc") or trade.get("entry_hour", 0)
    direction     = "LONG" if "LONG" in strategy else "SHORT"
    vol_regime    = "HIGH_VOL" if vol_pct > 70 else ("LOW_VOL" if vol_pct < 30 else "MED_VOL")
    z_magnitude   = "EXTREME" if abs(daily_z) > 2.5 else ("STRONG" if abs(daily_z) > 2.0 else "MODERATE")

    return (
        f"Symbol {symbol} strategy {strategy} direction {direction} "
        f"session {session} hour {hour} "
        f"daily_z {daily_z:.2f} h1_z {h1_z:.2f} "
        f"vol_regime {vol_regime} z_magnitude {z_magnitude}"
    )


def _make_metadata(trade: dict) -> dict:
    """Extract filterable metadata fields from a trade record."""
    pnl = trade.get("pnl_pct")
    return {
        "symbol":        str(trade.get("symbol", "")),
        "strategy_type": str(trade.get("type") or trade.get("strategy_type", "")),
        "session":       str(trade.get("session", "")),
        "won":           int(pnl > 0) if pnl is not None else 0,
        "pnl_pct":       float(pnl) if pnl is not None else 0.0,
        "daily_z":       float(trade.get("daily_z") or 0.0),
        "h1_z":          float(trade.get("h1_z") or 0.0),
        "vol_percentile": float(trade.get("vol_percentile") or 50.0),
    }


class RAGSignalFilter:
    """
    Semantic signal confidence scorer using ChromaDB.

    Usage:
        rag = RAGSignalFilter()
        rag.index_trades(trades_df)          # after each backtest run
        score = rag.score_signal(signal)      # before taking a trade
        if score["confidence"] > 0.4:
            # take trade at score["size_modifier"] * base_size
    """

    def __init__(self, chroma_path: Path = CHROMA_PATH, collection: str = "trade_memory"):
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is required: pip install chromadb")
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._col = self._client.get_or_create_collection(
            name=collection,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._col.count()

    def index_trade(self, trade: dict):
        """Add a single trade to the vector index."""
        doc_id = hashlib.md5(
            f"{trade.get('symbol')}{trade.get('entry_date')}{trade.get('type') or trade.get('strategy_type')}".encode()
        ).hexdigest()
        self._col.upsert(
            ids=[doc_id],
            documents=[_make_doc_text(trade)],
            metadatas=[_make_metadata(trade)],
        )

    def index_trades(self, trades_df, batch_size: int = 100):
        """Bulk-index a backtest results DataFrame."""
        records = trades_df.to_dict("records")
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            ids   = [
                hashlib.md5(
                    f"{r.get('symbol')}{r.get('entry_date')}{r.get('type')}".encode()
                ).hexdigest()
                for r in batch
            ]
            docs  = [_make_doc_text(r) for r in batch]
            metas = [_make_metadata(r) for r in batch]
            self._col.upsert(ids=ids, documents=docs, metadatas=metas)
        print(f"  RAG index: {self._col.count()} trades indexed")

    def score_signal(
        self,
        symbol: str,
        strategy_type: str,
        session: str,
        daily_z: float,
        h1_z: float,
        vol_percentile: float,
        hour_utc: int,
        k: int = 15,
        min_samples: int = 5,
    ) -> dict:
        """
        Score a new signal by retrieving k similar historical trades.

        Returns:
            confidence    — historical win rate among similar conditions (0–1)
            sample_size   — number of matching trades found
            avg_pnl       — average P&L of similar trades
            size_modifier — suggested size multiplier (0.5–1.2)
            action        — TAKE / REDUCE / SKIP recommendation
        """
        if self._col.count() < min_samples:
            return {
                "confidence": 0.5,
                "sample_size": 0,
                "avg_pnl": 0.0,
                "size_modifier": 1.0,
                "action": "TAKE",
                "reason": "Insufficient history — proceeding with default confidence",
            }

        direction = "LONG" if "LONG" in strategy_type else "SHORT"
        vol_regime = "HIGH_VOL" if vol_percentile > 70 else ("LOW_VOL" if vol_percentile < 30 else "MED_VOL")
        z_magnitude = "EXTREME" if abs(daily_z) > 2.5 else ("STRONG" if abs(daily_z) > 2.0 else "MODERATE")

        query_text = (
            f"Symbol {symbol} strategy {strategy_type} direction {direction} "
            f"session {session} hour {hour_utc} "
            f"daily_z {daily_z:.2f} h1_z {h1_z:.2f} "
            f"vol_regime {vol_regime} z_magnitude {z_magnitude}"
        )

        results = self._col.query(
            query_texts=[query_text],
            n_results=min(k, self._col.count()),
            include=["metadatas", "distances"],
        )

        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        if not metas:
            return {"confidence": 0.5, "sample_size": 0, "avg_pnl": 0.0,
                    "size_modifier": 1.0, "action": "TAKE", "reason": "No similar trades found"}

        # Weight by similarity (lower cosine distance = more similar)
        similarities = [max(0.0, 1.0 - d) for d in distances]
        total_weight = sum(similarities) or 1.0

        weighted_wins = sum(m["won"] * s for m, s in zip(metas, similarities))
        weighted_pnl  = sum(m["pnl_pct"] * s for m, s in zip(metas, similarities))

        confidence = weighted_wins / total_weight
        avg_pnl    = weighted_pnl / total_weight

        # Size modifier: scale up on high confidence, down on low
        if confidence >= 0.50:
            size_modifier = 1.0 + (confidence - 0.50) * 0.4  # up to 1.2x at 100% WR
        elif confidence >= 0.35:
            size_modifier = 1.0
        elif confidence >= 0.25:
            size_modifier = 0.7
        else:
            size_modifier = 0.5

        if confidence >= 0.38:
            action = "TAKE"
        elif confidence >= 0.28:
            action = "REDUCE"
        else:
            action = "SKIP"

        return {
            "confidence":    round(confidence, 3),
            "sample_size":   len(metas),
            "avg_pnl":       round(avg_pnl, 4),
            "size_modifier": round(size_modifier, 2),
            "action":        action,
            "reason":        f"{len(metas)} similar trades, {confidence*100:.0f}% win rate, avg P&L {avg_pnl*100:.3f}%",
        }

    def clear(self):
        """Wipe the index (use when re-running full backtest from scratch)."""
        self._client.delete_collection("trades")
        self._col = self._client.get_or_create_collection(
            name="trades",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )


if __name__ == "__main__":
    if not CHROMA_AVAILABLE:
        print("Install chromadb: pip install chromadb")
    else:
        rag = RAGSignalFilter()
        print(f"RAG index loaded: {rag.count} trades")
