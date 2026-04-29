"""SM_Crossover_Arrows Python port — Phase 12 Plan 02 / D-07, D-10, D-11.

Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md

Version: 2.10

Two independent EMA crossover systems:

System 1 — Short-term (fast=7, slow=13, operator-tuned 2026-04-28):
    EMA 7/13 crossover. Original MMM Book p. 47 reference is EMA 5/13;
    operator's working setup runs the slightly slower 7-period fast EMA to
    filter intra-bar noise.
    Output columns: ema_fast, ema_slow, buy_signal, sell_signal.

System 2 — Long-term (long_fast=50, long_slow=200, v2.10 golden/death cross):
    EMA 50/200 crossover. Golden cross (50 crosses above 200) = buy.
    Death cross (50 crosses below 200) = sell.
    Output columns: ema_long_fast, ema_long_slow, golden_cross, death_cross.

Cross detection uses shift(1) guard on bar i vs bar i-1 to avoid
lookahead/repaint (Pitfall 5 — RESEARCH Anti-Patterns "Repainting on
bar[0] alerts").

Per D-11: function-first surface; D-10 >=1 GREEN pytest.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CrossoverArrowsParams:
    """Spec Section 3 inputs — both short-term and long-term systems.

    v2.00 default: EMA 7/13 (operator-tuned 2026-04-28). The original
    MMM Book p. 47 reference is EMA 5/13; the operator's working setup
    runs the slightly slower 7-period fast EMA to filter intra-bar noise.

    v2.10 adds: long_fast=50, long_slow=200 golden/death cross system.
    """

    fast: int = 7    # v2.00 operator-tuned 2026-04-28 (was 5 per MMM Book p. 47)
    slow: int = 13   # MMM Book p. 47
    long_fast: int = 50    # v2.10 golden/death cross fast EMA
    long_slow: int = 200   # v2.10 golden/death cross slow EMA
    enable_long_cross: bool = True  # v2.10 toggle for long-term system


def compute_crossover_arrows(
    df: pd.DataFrame,
    params: CrossoverArrowsParams = CrossoverArrowsParams(),
) -> pd.DataFrame:
    """SM_Crossover_Arrows — dual EMA crossover detection (v2.10).

    Per spec Section 5. Cross detected at bar i vs bar i-1 transitions
    only — no lookahead (Pitfall 5).

    Args:
        df: OHLC DataFrame (Title-case Open/High/Low/Close).
        params: CrossoverArrowsParams. Defaults fast=7, slow=13,
                long_fast=50, long_slow=200, enable_long_cross=True.

    Returns:
        DataFrame with the input columns plus:

        System 1 — short-term (unchanged from v2.00):
            ema_fast      — EMA(fast) of Close
            ema_slow      — EMA(slow) of Close
            buy_signal    — bool: short-term bullish cross at bar i
            sell_signal   — bool: short-term bearish cross at bar i

        System 2 — long-term (v2.10):
            ema_long_fast — EMA(long_fast) of Close
            ema_long_slow — EMA(long_slow) of Close
            golden_cross  — bool: long_fast crossed above long_slow at bar i
            death_cross   — bool: long_fast crossed below long_slow at bar i

        Legacy column cross_signal ('BUY'/'SELL'/'NONE') is also retained
        for backward compatibility with existing callers.
    """
    out = df.copy()  # Pitfall 3 — never mutate caller

    # --- System 1: short-term EMA pair ---
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

    out["buy_signal"] = bull
    out["sell_signal"] = bear

    # Legacy cross_signal column (backward compat).
    out["cross_signal"] = "NONE"
    out.loc[bull, "cross_signal"] = "BUY"
    out.loc[bear, "cross_signal"] = "SELL"

    # --- System 2: long-term EMA pair (v2.10 golden/death cross) ---
    out["ema_long_fast"] = out["Close"].ewm(
        span=params.long_fast, adjust=False
    ).mean()
    out["ema_long_slow"] = out["Close"].ewm(
        span=params.long_slow, adjust=False
    ).mean()

    if params.enable_long_cross:
        golden = (out["ema_long_fast"] > out["ema_long_slow"]) & (
            out["ema_long_fast"].shift(1) <= out["ema_long_slow"].shift(1)
        )
        death = (out["ema_long_fast"] < out["ema_long_slow"]) & (
            out["ema_long_fast"].shift(1) >= out["ema_long_slow"].shift(1)
        )
    else:
        golden = pd.Series(False, index=out.index)
        death = pd.Series(False, index=out.index)

    out["golden_cross"] = golden
    out["death_cross"] = death

    return out


__all__ = ["CrossoverArrowsParams", "compute_crossover_arrows"]
