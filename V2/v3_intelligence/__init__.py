"""
V3 Intelligence Layer — MarketMind continuous learning system.

Modules:
  trade_logger        — SQLite trade journal + append-only decision log
  pair_config         — per-pair strategy overrides with tiered sizing
  rag_signal_filter   — ChromaDB semantic retrieval for signal confidence scoring
  regime              — HMM-GARCH regime classifier subpackage (Phase 8)
  pit                 — point-in-time replay clock (Phase 8)
  router              — strategy router (Phase 9) — 4-gate dispatch chain
"""
from .trade_logger import TradeLogger
from .pair_config import PairConfig, PAIR_CONFIGS, get_pair_config
from .rag_signal_filter import RAGSignalFilter, CHROMA_AVAILABLE
from .regime import RegimeState, OnlineRegimeFilter
from .pit import PitClock, FutureBarReadError

# Phase 9 ROUT-01..04 router public API (CONTEXT D-12 / D-20).
from .router import (
    StrategyRouter,
    RouteDecision,
    Strategy,
    Direction,
    OpenPosition,
    PositionStore,
    InMemoryPositionStore,
    ZmqPositionStore,
)

__all__ = [
    "TradeLogger",
    "PairConfig",
    "PAIR_CONFIGS",
    "get_pair_config",
    "RAGSignalFilter",
    "CHROMA_AVAILABLE",
    "RegimeState",
    "OnlineRegimeFilter",
    "PitClock",
    "FutureBarReadError",
    # Phase 9
    "StrategyRouter",
    "RouteDecision",
    "Strategy",
    "Direction",
    "OpenPosition",
    "PositionStore",
    "InMemoryPositionStore",
    "ZmqPositionStore",
]
