# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** A validated daily Z-score mean-reversion signal (Sharpe 2.08) ready to move from Python backtest to live MT5 execution.
**Current focus:** Defining next milestone

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v2.0
Last activity: 2026-04-21 — Milestone v2.0 started (V3 Adaptive Strategy Dispatch System)

## Accumulated Context

- Daily swing strategy is the ONLY validated signal source; H1 scalp/momentum layers destroy alpha
- RAG filter (ChromaDB) boosts Sharpe from 1.67 → 2.08 — non-negotiable feature
- Hurst regime filter just added (latest commit) — not yet validated in live conditions
- BEC partial close shelved until win rate ≥ 40% (currently 35.4%)
- MT5 EA compiles but has NO live connection to Python signal engine
- The critical gap: execution plumbing (Python → MT5 bridge)
- USDJPY is the crown jewel (Sharpe 3.09, 44.4% win rate)
- IC Markets Raw Spread account is the target broker
