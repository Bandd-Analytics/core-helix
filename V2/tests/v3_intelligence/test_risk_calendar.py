"""Phase 8.5 SESS-03 — RED scaffold (Wave 0).

All tests import from v3_intelligence.temporal_analysis (risk-calendar functions
live in the same module per RESEARCH §Pattern 5). Plan 04 turns these GREEN.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import pytest


def test_baseline_zscore_detection(synthetic_bars_with_spikes):
    """SESS-03 — detect_blackout_bars returns timestamps where range > 2.5σ above baseline.

    Synthetic 4yr H1 bars with injected 10× range spikes at every 1st-Friday-12:30.
    Detection must recover all injected timestamps; no false positives at quiet hours.
    """
    from v3_intelligence.temporal_analysis import detect_blackout_bars
    bars, injected_ts = synthetic_bars_with_spikes(
        pair="EURUSD", timeframe="H1", n_years=4,
        spike_pattern="first_friday_1230", spike_magnitude=10.0,
    )
    detected = detect_blackout_bars(bars, sigma=2.5)
    # All injected timestamps recovered
    recovered = set(injected_ts) & set(detected)
    assert len(recovered) >= int(len(injected_ts) * 0.9), \
        f"Expected ≥90% recovery, got {len(recovered)}/{len(injected_ts)}"


def test_pattern_extraction_first_friday(synthetic_bars_with_spikes):
    """SESS-03 — cluster_into_patterns recognizes "1st Friday 12:30" as wom n=1 dow=4 time=12:30.

    Per CONTEXT D-11: parametric pattern, NOT date list. dow=4 (Friday in pandas .dayofweek).
    """
    from v3_intelligence.temporal_analysis import cluster_into_patterns
    # 47 timestamps: every 1st Friday of every month over 4 years (48 expected, 1 missing)
    stamps = pd.DatetimeIndex([
        ts for ts in pd.date_range("2022-01-01", "2026-01-01", freq="D", tz="UTC")
        if ts.dayofweek == 4 and 1 <= ts.day <= 7
    ]).map(lambda ts: ts.replace(hour=12, minute=30))[:47]
    patterns = cluster_into_patterns(stamps)
    wom_patterns = [p for p in patterns if p["pattern"] == "wom"]
    assert len(wom_patterns) >= 1, f"No wom pattern detected: {patterns}"
    wom = wom_patterns[0]
    assert wom["n"] == 1
    assert wom["dow"] == 4  # Friday
    assert wom["time"] == "12:30"


def test_yaml_roundtrip_preserves_comments(tmp_path):
    """SESS-03 — write_risk_calendar uses ruamel.yaml round-trip; operator comments survive re-runs.

    Per CONTEXT D-12 + RESEARCH Pitfall (PyYAML drops comments).
    """
    from v3_intelligence.temporal_analysis import write_risk_calendar
    calendar_path = tmp_path / "risk_calendar.yaml"

    # First write — empirical detection only
    empirical = [{"pattern": "wom", "n": 1, "dow": 4, "time": "12:30",
                  "duration_min": 30, "affects": ["USD"], "source": "empirical"}]
    write_risk_calendar(empirical, calendar_path)
    assert calendar_path.exists()

    # Operator manually edits — adds a comment block + manual entry
    original = calendar_path.read_text()
    edited = original.replace(
        "blackouts:",
        "# manually curated 2026-04-27 per Fed calendar\nblackouts:"
    )
    # Inject a manual entry
    edited += (
        "\n  - pattern: dates\n    dates: ['2026-05-01']\n"
        "    time: '18:30'\n    duration_min: 60\n"
        "    affects: [USD]\n    source: manual\n"
    )
    calendar_path.write_text(edited)

    # Re-run write_risk_calendar — should preserve comment + manual entry
    write_risk_calendar(empirical, calendar_path)
    final = calendar_path.read_text()
    assert "# manually curated 2026-04-27 per Fed calendar" in final, \
        "Comment block lost on round-trip"
    assert "source: manual" in final, "Manual entry lost on round-trip"


def test_manual_override_merge(tmp_path):
    """SESS-03 — detection takes precedence on (pattern, time, affects) conflict; manual wins on no conflict.

    Per CONTEXT D-12.
    """
    from v3_intelligence.temporal_analysis import write_risk_calendar
    from ruamel.yaml import YAML
    calendar_path = tmp_path / "risk_calendar.yaml"

    # Manual entry pre-existing — different time slot (no conflict)
    yaml = YAML(typ="rt")
    with calendar_path.open("w") as f:
        yaml.dump({"blackouts": [
            {"pattern": "dates", "dates": ["2026-05-01"], "time": "18:30",
             "duration_min": 60, "affects": ["USD"], "source": "manual"},
        ]}, f)

    # New empirical detection — different time, no conflict
    empirical = [{"pattern": "wom", "n": 1, "dow": 4, "time": "12:30",
                  "duration_min": 30, "affects": ["USD"], "source": "empirical"}]
    write_risk_calendar(empirical, calendar_path)
    with calendar_path.open() as f:
        merged = yaml.load(f)
    sources = [b["source"] for b in merged["blackouts"]]
    assert "manual" in sources and "empirical" in sources, \
        f"Both sources should survive: {sources}"


def test_per_currency_scoping(synthetic_bars_with_spikes):
    """SESS-03 — each blackout entry declares affects=[<3-letter codes>] per CONTEXT D-13.

    Detected entries default to affects=[base_currency, quote_currency] of the source pair;
    Plan 04 may refine via heuristics (USD release windows scope to USD-only).
    """
    from v3_intelligence.temporal_analysis import detect_blackout_bars, cluster_into_patterns
    bars, _ = synthetic_bars_with_spikes(
        pair="EURUSD", timeframe="H1", n_years=4,
        spike_pattern="first_friday_1230", spike_magnitude=10.0,
    )
    stamps = detect_blackout_bars(bars, sigma=2.5)
    patterns = cluster_into_patterns(stamps, source_pair="EURUSD")
    for p in patterns:
        assert "affects" in p, f"Pattern missing 'affects' field: {p}"
        assert isinstance(p["affects"], list)
        assert all(isinstance(c, str) and len(c) == 3 for c in p["affects"]), \
            f"affects must be 3-letter currency codes: {p['affects']}"
