# Milestones

## v1.0 — Validated Signal Engine (Completed: 2026-04-21)

**Goal:** Build and validate the core trading signal pipeline in Python — from raw OHLCV data to backtested, regime-filtered, RAG-enhanced trade signals with a working MT5 EA skeleton.

**Shipped:**
- Daily Z-score mean-reversion signal engine across 5 forex pairs
- ADX change-point regime filter
- Hurst exponent regime filter (H < 0.45 → mean-reverting gate)
- RAG signal filter (ChromaDB semantic memory, confidence scoring)
- Signal filters module (rolling_hurst, rolling_ols_zscore, sigdet_zscore)
- Multi-pair tiered configuration with per-pair ATR-based exits
- Python backtesting framework (vectorbt.pro)
- SQLite trade journal with full context logging
- MT5 EA skeleton (compiles)
- Walk-forward validated results: Sharpe 2.08, +42.84% P&L, 513 trades

**Last phase:** 5 (inferred from development history)
