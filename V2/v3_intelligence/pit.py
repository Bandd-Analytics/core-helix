"""Point-in-time replay clock — runtime no-future-read enforcement (REGM-03).

Lightweight pandas-native context manager. No ArcticDB dependency. Compares
read timestamps against an as-of cutoff and raises FutureBarReadError on any
access where the read timestamp exceeds the cutoff.

Per CONTEXT.md decisions:
  D-06: replay-clock context manager, pandas-native, no ArcticDB.
  D-07: opt-in via decorator on backtest method (existing loops untouched).
  D-08: timestamp-based check (`bar.ts > as_of_ts`), not index-based.
  D-09: mandatory test — out-of-order read raises FutureBarReadError.
  D-25: PitClock.UNBOUNDED sentinel disables enforcement (offline-fit usage).
"""
from __future__ import annotations

from typing import Any, Callable, ClassVar, Optional

import pandas as pd


class FutureBarReadError(Exception):
    """Raised when a PiT-gated read exceeds the as-of timestamp."""


class PitClock:
    """Replay clock. Wrap a backtest loop body to enforce no-future reads."""

    # Sentinel: shared instance with as_of=None — enforcement disabled.
    UNBOUNDED: ClassVar["PitClock"]  # set after class def below

    def __init__(self, as_of_ts: Optional[pd.Timestamp]) -> None:
        # None marks the UNBOUNDED sentinel; callers should prefer the constant.
        self._as_of: Optional[pd.Timestamp] = as_of_ts
        self._active: bool = False

    def __enter__(self) -> "PitClock":
        self._active = True
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        self._active = False

    def advance(self, new_ts: pd.Timestamp) -> None:
        """Move the cutoff forward inside the loop body.

        Must be monotone: new_ts >= self._as_of. The UNBOUNDED sentinel
        accepts any value (no rewind check).
        """
        if self._as_of is not None and new_ts < self._as_of:
            raise ValueError(
                f"PitClock cannot rewind ({new_ts} < {self._as_of})"
            )
        self._as_of = new_ts

    def read(
        self,
        df: pd.DataFrame,
        sym: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return rows of df whose index is <= self._as_of.

        Behaviour:
          - UNBOUNDED sentinel (as_of=None): returns df verbatim.
          - df.index.max() <= as_of: returns df verbatim.
          - df extends past cutoff: returns the truncated view (rows <= as_of).
          - df fully past cutoff: raises FutureBarReadError.
        """
        if self._as_of is None:  # UNBOUNDED
            return df
        if len(df) == 0:
            raise FutureBarReadError(
                "Empty DataFrame passed to PitClock.read"
                + (f" for {sym}" if sym else "")
            )
        if df.index.max() <= self._as_of:
            return df
        truncated = df.loc[df.index <= self._as_of]
        if truncated.empty:
            raise FutureBarReadError(
                f"No bars at or before {self._as_of}"
                + (f" for {sym}" if sym else "")
            )
        return truncated

    def assert_no_future(
        self,
        ts: pd.Timestamp,
        sym: Optional[str] = None,
    ) -> None:
        """Explicit guard: raise FutureBarReadError if ts > self._as_of.

        UNBOUNDED sentinel never raises (D-25).
        """
        if self._as_of is None:
            return
        if ts > self._as_of:
            raise FutureBarReadError(
                f"Read at {ts} exceeds clock {self._as_of}"
                + (f" for {sym}" if sym else "")
            )


# Sentinel construction — single shared instance with as_of=None (D-25).
PitClock.UNBOUNDED = PitClock(None)


def pit_gated(method: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: backtest method receives a PitClock kw or default UNBOUNDED.

    Phase 9 router opt-in pattern (D-07). Existing backtest loops in Phase 7
    do NOT use this decorator and are unmodified — UNBOUNDED only kicks in
    when callers do not pass `clock=`.
    """
    def wrapper(
        self: Any,
        *args: Any,
        clock: Optional[PitClock] = None,
        **kwargs: Any,
    ) -> Any:
        if clock is None:
            clock = PitClock.UNBOUNDED
        return method(self, *args, clock=clock, **kwargs)

    wrapper.__name__ = getattr(method, "__name__", "wrapper")
    wrapper.__doc__ = method.__doc__
    return wrapper


__all__ = ["PitClock", "FutureBarReadError", "pit_gated"]
