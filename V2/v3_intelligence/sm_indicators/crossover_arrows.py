"""SM_Crossover_Arrows Python port — Phase 12 Plan 02 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md

EMA 5/13 crossover detection (MMM Book p. 47). Cross detected at bar i
vs bar i-1 to avoid lookahead/repaint (Pitfall 5 — RESEARCH Anti-Patterns
"Repainting on bar[0] alerts").

Per D-11: function-first surface; D-10 ≥1 GREEN pytest.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CrossoverArrowsParams:
    """Spec Section 3 inputs.

    Defaults per MMM Book p. 47 (EMA 5/13 — the MMM-canonical short-term
    crossover pair).
    """

    fast: int = 5    # MMM Book p. 47
    slow: int = 13   # MMM Book p. 47


def compute_crossover_arrows(
    df: pd.DataFrame,
    params: CrossoverArrowsParams = CrossoverArrowsParams(),
) -> pd.DataFrame:
    """SM_Crossover_Arrows — EMA 5/13 cross detection.

    Per spec Section 5. Cross detected at bar i vs bar i-1 transitions
    only — no lookahead (Pitfall 5).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: CrossoverArrowsParams. Defaults fast=5, slow=13.

    Returns:
        DataFrame with the input columns plus:
            ema_fast      — EMA(fast) of Close
            ema_slow      — EMA(slow) of Close
            cross_signal  — 'BUY' on bullish cross at bar i, 'SELL' on
                            bearish cross at bar i, otherwise 'NONE'
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # adjust=False matches MT4/MT5 iMA(MODE_EMA) recursive smoothing.
    out["ema_fast"] = out["Close"].ewm(span=params.fast, adjust=False).mean()
    out["ema_slow"] = out["Close"].ewm(span=params.slow, adjust=False).mean()

    # bar i vs bar i-1 cross — NEVER bar 0 vs current tick (RESEARCH
    # Anti-Patterns "Repainting on bar[0] alerts").
    bull = (out["ema_fast"] > out["ema_slow"]) & (
        out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)
    )
    bear = (out["ema_fast"] < out["ema_slow"]) & (
        out["ema_fast"].shift(1) >= out["ema_slow"].shift(1)
    )

    out["cross_signal"] = "NONE"
    out.loc[bull, "cross_signal"] = "BUY"
    out.loc[bear, "cross_signal"] = "SELL"

    return out


__all__ = ["CrossoverArrowsParams", "compute_crossover_arrows"]
