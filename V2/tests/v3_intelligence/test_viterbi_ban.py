"""REGM-04 Viterbi-ban grep gate (D-04, D-05).

This is the permanent CI guard for REGM-04: zero Viterbi calls in V2 backtest,
v3_intelligence, and live paths. RED until Plan 02/03/04 ensure the regime
port (and only the regime port) is committed without any Viterbi references.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]  # V2/
SCAN_DIRS = [
    REPO / "backtest",
    REPO / "v3_intelligence",
    REPO / "live",   # may not exist yet — handled below
]
PATTERNS = ["viterbi", "Viterbi", "predict_viterbi"]


def test_no_viterbi_imports_or_calls_in_v2() -> None:
    """REGM-04 / D-05: grep finds zero matches across SCAN_DIRS for PATTERNS.

    Excludes:
      - this test file itself (literal pattern strings live here)
      - .planning/ (planning docs are allowed to mention Viterbi)
      - tests/v3_intelligence/test_viterbi_ban.py (this file)
    """
    matches: list[str] = []
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for pattern in PATTERNS:
            # grep -rn -I (skip binary) --include='*.py'  pattern  dir
            result = subprocess.run(
                ["grep", "-rn", "-I", "--include=*.py", pattern, str(d)],
                capture_output=True, text=True,
            )
            for line in result.stdout.splitlines():
                # Allow this self-referential test file
                if "test_viterbi_ban.py" in line:
                    continue
                matches.append(line)
    assert matches == [], (
        "REGM-04 violated — Viterbi references found:\n"
        + "\n".join(matches)
    )


def test_no_viterbi_py_file_in_regime_subpackage() -> None:
    """D-04: V2/v3_intelligence/regime/viterbi.py MUST NOT exist."""
    p = REPO / "v3_intelligence" / "regime" / "viterbi.py"
    assert not p.exists(), f"D-04 violated — {p} exists"
