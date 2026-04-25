"""Regime state enum (D-22, D-23 — only RegimeState ported from the V1 signal_types module)."""
from __future__ import annotations

import enum


class RegimeState(enum.IntEnum):
    """HMM regime states, ordered by ascending unconditional variance.

    Values are pinned by variance rank at fit time (REGM-02), so the integer
    value carries semantic meaning across re-fits:

      TRENDING       = 0  -> lowest unconditional variance
      MEAN_REVERTING = 1  -> middle
      CRISIS         = 2  -> highest
    """

    TRENDING = 0
    MEAN_REVERTING = 1
    CRISIS = 2


__all__ = ["RegimeState"]
