"""V2/v3_intelligence/regime/ — HMM-GARCH regime classifier subpackage (Phase 8).

Port of V1/helix/src/alpha/regime/ with two surgical changes per CONTEXT.md:
  - D-04: Viterbi banished — no viterbi.py, no predict_viterbi method.
  - D-22/D-23: RegimeState enum lives at types.py (only enum ported from V1
    signal_types.py).

Public surface (consumed by Phase 9 router and Phase 10 live):
  - RegimeState
  - HMMGARCHRegimeDetector       (Plan 02 — Task 3)
  - OnlineRegimeFilter           (Plan 03)
  - bars_to_log_returns          (Plan 02 — Task 2)
  - save_detector / load_detector (Plan 03)
"""
from __future__ import annotations

from .types import RegimeState

__all__ = ["RegimeState"]
