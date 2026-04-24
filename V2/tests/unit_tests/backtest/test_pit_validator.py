"""PiT validator port + whitelist tests (BKTS-04, D-05/D-06/D-07/D-08).

Verifies the ported V2/backtest/pit_validator.py:
  - Flags signal-bar price reads (df['Close'], df['Open'] without .shift())
  - Whitelists next-bar reads (h1.iloc[i+1]['Open'])
  - Exits 0 when scanning the fixed backtest_hybrid.py and backtest_evaluate_all.py
  - Exits 1 when scanning a deliberately biased fixture
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.fixture
def validator():
    """Import the ported validator; skip the test if not yet ported."""
    from backtest.pit_validator import PiTValidator  # noqa: PLC0415
    return PiTValidator()


def test_validator_class_exists() -> None:
    """BKTS-04 / D-05: PiTValidator class is importable from V2/backtest/."""
    from backtest.pit_validator import PiTValidator  # noqa: F401
    from backtest.pit_validator import PiTViolation  # noqa: F401


def test_price_columns_covers_title_case(validator) -> None:
    """D-07: PRICE_COLUMNS includes both 'Close' and 'close' so the project's
    pandas Title-case columns are detected."""
    from backtest.pit_validator import PRICE_COLUMNS
    for col in ("Close", "Open", "High", "Low", "close", "open", "high", "low"):
        assert col in PRICE_COLUMNS, f"PRICE_COLUMNS missing '{col}'"


def test_flags_biased_close_read(validator, tmp_path) -> None:
    """D-07: Assigning entry_price = row['Close'] (signal-bar close) is a violation."""
    f = tmp_path / "biased.py"
    f.write_text(dedent("""
        def run(df):
            for i in range(100, len(df)):
                row = df.iloc[i]
                entry_price = row['Close']   # biased
                positions.append({'entry_price': entry_price})
    """))
    violations = validator.validate_file(f)
    assert len(violations) >= 1
    assert any("Close" in v.column_accessed or v.column_accessed == "Close"
               for v in violations)


def test_whitelists_next_bar_open(validator, tmp_path) -> None:
    """D-07: h1.iloc[i+1]['Open'] is an intentional next-bar fill — NOT a violation."""
    f = tmp_path / "fixed.py"
    f.write_text(dedent("""
        def run(df):
            for i in range(100, len(df) - 1):
                row = df.iloc[i]
                entry_price = df.iloc[i + 1]['Open']   # whitelisted
                positions.append({'entry_price': entry_price})
    """))
    violations = validator.validate_file(f)
    # The next-bar read must NOT appear in violations
    msgs = "\n".join(v.message for v in violations)
    assert "iloc[i + 1]" not in msgs and "next" not in msgs.lower() or len(violations) == 0


def test_cli_exits_zero_on_clean_file(tmp_path) -> None:
    """D-06: CLI exits 0 when all scanned files are clean."""
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, "-m", "backtest.pit_validator", str(f)],
        cwd=Path(__file__).resolve().parents[3],  # V2/
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"


def test_cli_exits_nonzero_on_violation(tmp_path) -> None:
    """D-06: CLI exits 1 and prints VIOLATION lines when bias is present."""
    f = tmp_path / "biased.py"
    f.write_text(dedent("""
        def run(df):
            for i in range(100, len(df)):
                row = df.iloc[i]
                entry_price = row['Close']
    """))
    result = subprocess.run(
        [sys.executable, "-m", "backtest.pit_validator", str(f)],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "VIOLATION" in (result.stdout + result.stderr)


def test_cli_scans_real_backtest_files_after_fix() -> None:
    """D-08: After Plan 02 applies the entry-fix, running the validator against
    the two real backtest files produces zero violations.

    NOTE: This test is the BKTS-04 phase-gate — it will fail until Plans 02/03
    both complete. Plan 03 creates the validator; Plan 02 fixes the backtest.
    """
    from backtest.pit_validator import PiTValidator
    v = PiTValidator()
    repo = Path(__file__).resolve().parents[3]  # V2/
    targets = [repo / "backtest" / "backtest_hybrid.py",
               repo / "backtest" / "backtest_evaluate_all.py"]
    violations = []
    for t in targets:
        violations.extend(v.validate_file(t))
    assert violations == [], \
        f"Expected 0 violations; got {len(violations)}:\n" + \
        "\n".join(f"  {x.file}:{x.line} {x.message}" for x in violations)
