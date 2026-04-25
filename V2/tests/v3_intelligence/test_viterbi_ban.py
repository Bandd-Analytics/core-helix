"""REGM-04 Viterbi-ban grep gate (D-04, D-05).

This is the permanent CI guard for REGM-04: zero functional Viterbi imports,
calls, or files in V2 backtest, v3_intelligence, and live paths.

Plan 04 refinement (per Plan 03 SUMMARY §"Next Plan Readiness"):
The test scans for FUNCTIONAL viterbi usage patterns (imports, calls,
attribute access, file existence) — not for the literal substring
"viterbi". Module/class docstrings in V2/v3_intelligence/regime/__init__.py
and V2/v3_intelligence/regime/hmm_garch.py legitimately mention "Viterbi"
to document that the V1 method/file was deliberately not ported (D-04).
Allowing those documentation mentions while still catching any actual
import/call is the correct enforcement (per Plan 03 SUMMARY's "Plan 04
must either refine the grep to skip docstrings/comments OR rephrase…"
guidance — option (a) chosen here).

The functional patterns covered:
  - import statements:  ``from .viterbi import …``  / ``import …viterbi``
  - module imports:     ``from X.viterbi import …``  / ``from X import viterbi``
  - method calls:       ``.predict_viterbi(``  /  ``viterbi_decode(``
  - attribute access:   ``.viterbi_…``  on detector / filter
  - file existence:     V2/v3_intelligence/regime/viterbi.py MUST NOT exist
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # V2/
SCAN_DIRS = [
    REPO / "backtest",
    REPO / "v3_intelligence",
    REPO / "live",   # may not exist yet — handled below
]

# Functional-only regex patterns (extended grep). Each pattern targets a
# real import / call / attribute usage, never a free-form mention.
FUNCTIONAL_PATTERNS = [
    # imports of any submodule literally named viterbi (case-insensitive on .Viterbi/.viterbi)
    r"from[[:space:]]+[._A-Za-z0-9]*\.[Vv]iterbi[[:space:]]+import",
    r"^[[:space:]]*import[[:space:]]+[._A-Za-z0-9]*\.[Vv]iterbi\b",
    r"from[[:space:]]+[._A-Za-z0-9]+[[:space:]]+import[[:space:]]+[Vv]iterbi\b",
    # function/method calls
    r"\bpredict_viterbi[[:space:]]*\(",
    r"\bviterbi_decode[[:space:]]*\(",
    # attribute / member access on an object (e.g. detector.predict_viterbi)
    r"\.predict_viterbi\b",
    r"\.viterbi_decode\b",
    # explicit assignment binding the name (rules out a re-introduced name)
    r"^[[:space:]]*predict_viterbi[[:space:]]*=",
    r"^[[:space:]]*viterbi_decode[[:space:]]*=",
]


def test_no_functional_viterbi_in_v2() -> None:
    """REGM-04 / D-05: zero functional Viterbi import/call/attr in V2 source.

    Permits docstring/comment mentions documenting the deliberate D-04
    omission (e.g. "predict_viterbi method removed"). Catches any real
    re-introduction of the symbol via import, call, or attribute access.

    Excludes:
      - this test file itself (literal pattern strings live here)
      - .planning/ (planning docs are allowed to mention Viterbi)
    """
    matches: list[str] = []
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for pattern in FUNCTIONAL_PATTERNS:
            # grep -rn -I -E (extended regex)  pattern  dir
            result = subprocess.run(
                ["grep", "-rn", "-I", "-E", "--include=*.py", pattern, str(d)],
                capture_output=True, text=True,
            )
            for line in result.stdout.splitlines():
                # Allow this self-referential test file
                if "test_viterbi_ban.py" in line:
                    continue
                matches.append(line)
    assert matches == [], (
        "REGM-04 violated — functional Viterbi import/call/attribute found:\n"
        + "\n".join(matches)
    )


def test_no_viterbi_py_file_in_regime_subpackage() -> None:
    """D-04: V2/v3_intelligence/regime/viterbi.py MUST NOT exist."""
    p = REPO / "v3_intelligence" / "regime" / "viterbi.py"
    assert not p.exists(), f"D-04 violated — {p} exists"


def test_no_viterbi_py_file_anywhere_in_scan_dirs() -> None:
    """D-04 (defense in depth): no *.py file in SCAN_DIRS named viterbi.py.

    Catches a viterbi.py reintroduced under a different package path
    (e.g. backtest/viterbi.py, v3_intelligence/utils/viterbi.py).
    Case-insensitive name match on the basename.
    """
    rx = re.compile(r"^[Vv]iterbi\.py$")
    offenders: list[str] = []
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for path in d.rglob("*.py"):
            if rx.match(path.name):
                offenders.append(str(path))
    assert offenders == [], (
        "D-04 violated — viterbi.py file(s) present in V2:\n"
        + "\n".join(offenders)
    )
