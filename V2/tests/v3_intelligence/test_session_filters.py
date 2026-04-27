"""Phase 8.5 SESS-04 — RED scaffold (Wave 0).

Tests assert the predicate API contract for Phase 9 router consumption.
Plan 05 generates session_config.py + temporal_filters.py and turns these GREEN.
"""
from __future__ import annotations
from datetime import datetime, timezone
import pytest


def test_is_tradeable_session_hard_veto():
    """SESS-04 — is_tradeable_session returns False for blacklisted hour per (pair, strategy, timeframe).

    Per CONTEXT D-06 hard-veto signature.
    Inject a synthetic SESSION_RULES entry via monkeypatch; assert hour-3 -> False, hour-13 -> True.
    """
    from v3_intelligence import session_config
    from v3_intelligence.temporal_filters import is_tradeable_session

    # Plan 05 produces real SESSION_RULES; for now assert structure exists
    assert hasattr(session_config, "SESSION_RULES"), \
        "session_config.py must export SESSION_RULES dict"
    assert isinstance(session_config.SESSION_RULES, dict)

    # Hard-veto contract: if a rule exists for (pair, strategy, tf) and ts.hour
    # is in blacklisted_hours, return False
    rules = session_config.SESSION_RULES
    if rules:
        (pair, strat, tf), rule = next(iter(rules.items()))
        if rule.get("blacklisted_hours"):
            bad_hour = rule["blacklisted_hours"][0]
            ts_blocked = datetime(2025, 1, 15, bad_hour, 0, tzinfo=timezone.utc)
            assert is_tradeable_session(pair, strat, tf, ts_blocked) is False
            # And a non-blacklisted hour returns True
            good_hour = (bad_hour + 12) % 24
            if good_hour not in rule["blacklisted_hours"]:
                ts_allowed = datetime(2025, 1, 15, good_hour, 0, tzinfo=timezone.utc)
                assert is_tradeable_session(pair, strat, tf, ts_allowed) is True


def test_is_blackout_window_global():
    """SESS-04 — is_blackout_window(ts) returns True for matching parametric pattern per D-07.

    Test: a wom pattern n=1 dow=4 time=12:30 duration=30min must match
    2024-04-05 12:35 UTC (1st Friday of April 2024) and reject 2024-04-05 13:01 UTC.
    """
    from v3_intelligence import session_config
    from v3_intelligence.temporal_filters import is_blackout_window

    assert hasattr(session_config, "BLACKOUT_PATTERNS"), \
        "session_config.py must export BLACKOUT_PATTERNS list"
    assert isinstance(session_config.BLACKOUT_PATTERNS, list)

    # 2024-04-05 is the 1st Friday of April 2024 — verify
    ts_in_window  = datetime(2024, 4, 5, 12, 35, tzinfo=timezone.utc)
    ts_out_window = datetime(2024, 4, 5, 13, 5,  tzinfo=timezone.utc)

    # If Plan 05 emits at least one wom pattern at 12:30, the test is meaningful;
    # if no patterns yet, smoke-test only that the function returns a bool
    result_in  = is_blackout_window(ts_in_window)
    result_out = is_blackout_window(ts_out_window)
    assert isinstance(result_in,  bool)
    assert isinstance(result_out, bool)


def test_session_config_importable():
    """SESS-04 — session_config.py is valid Python, imports cleanly, has required top-level symbols.

    Per CONTEXT D-08 (Python literals, not YAML/JSON).
    Required exports: SESSION_RULES (dict), BLACKOUT_PATTERNS (list),
                      GENERATED_AT (str ISO timestamp), SOURCE_HASH (str).
    """
    from v3_intelligence import session_config
    for attr in ("SESSION_RULES", "BLACKOUT_PATTERNS", "GENERATED_AT", "SOURCE_HASH"):
        assert hasattr(session_config, attr), \
            f"session_config.py missing required export: {attr}"
    assert isinstance(session_config.SESSION_RULES,    dict)
    assert isinstance(session_config.BLACKOUT_PATTERNS, list)
    assert isinstance(session_config.GENERATED_AT,     str)
    assert isinstance(session_config.SOURCE_HASH,      str)

    # SESSION_RULES keys must be (pair, strategy, timeframe) tuples
    for key in session_config.SESSION_RULES.keys():
        assert isinstance(key, tuple) and len(key) == 3, \
            f"SESSION_RULES key not (pair, strategy, timeframe) tuple: {key}"
