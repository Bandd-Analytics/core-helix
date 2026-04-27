"""SEED session_config — overwritten by run_temporal_analysis.py phase-gate run.

Phase 8.5 SESS-04 — initial state before full-corpus run.
Re-generate via: cd V2 && python -m scripts.run_temporal_analysis

Schema (per CONTEXT D-08, Plan 05):
- GENERATED_AT (str): ISO timestamp of last regeneration
- SOURCE_HASH (str): sha256[:16] of source CSVs + risk_calendar.yaml
- SESSION_RULES (dict): {(pair, strategy, timeframe): {blacklisted_hours, blacklisted_dows, tradeable_sessions}}
- BLACKOUT_PATTERNS (list): parametric recurring blackout windows (wom/dow/mom/yearly/dates)
"""
from __future__ import annotations

GENERATED_AT: str = "2026-04-27T00:00:00Z"
SOURCE_HASH: str = "seed-empty"

SESSION_RULES: dict[tuple[str, str, str], dict] = {}
BLACKOUT_PATTERNS: list[dict] = []
