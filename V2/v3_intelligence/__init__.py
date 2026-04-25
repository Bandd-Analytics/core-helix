"""
V3 Intelligence Layer — MarketMind continuous learning system.

Modules:
  trade_logger        — SQLite trade journal + append-only decision log
  pair_config         — per-pair strategy overrides with tiered sizing
  rag_signal_filter   — ChromaDB semantic retrieval for signal confidence scoring
  regime              — HMM-GARCH regime classifier subpackage (Phase 8)
"""
from .trade_logger import TradeLogger
from .pair_config import PairConfig, PAIR_CONFIGS, get_pair_config
from .rag_signal_filter import RAGSignalFilter, CHROMA_AVAILABLE
from .regime import RegimeState  # re-export for ergonomics (D-22)

__all__ = [
    "TradeLogger",
    "PairConfig",
    "PAIR_CONFIGS",
    "get_pair_config",
    "RAGSignalFilter",
    "CHROMA_AVAILABLE",
    "RegimeState",
]
