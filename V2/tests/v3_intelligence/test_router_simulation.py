"""Phase 9 ROUT-04 simulation gate (CONTEXT D-18).

All tests are RED at Wave 0 scaffold time:

    test_router_simulation_module_importable
        Fails immediately on import — backtest.router_simulation does not yet
        exist (Plan 04 creates V2/backtest/router_simulation.py with
        run_router_simulation()).

    test_aggregate_sharpe_beats_single_by_0_2 (slow marker)
        Depends on Plan 02 router + Plan 03 detectors (8/8) + Plan 04 sim.
        Asserts ROUT-04 gate: aggregate router Sharpe >= max single per-pair
        Sharpe + 0.2.

    test_sim_report_schema (slow marker)
        Asserts V2/reports/router_4yr_simulation.json has the 4 required keys
        per CONTEXT D-18 (aggregate_sharpe, best_single_sharpe,
        baseline_plus_0_2, gate_passed).

Run with:
    cd V2 && python -m pytest tests/v3_intelligence/test_router_simulation.py -v -m slow
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_router_simulation_module_importable():
    """Plan 04 must create V2/backtest/router_simulation.py with
    run_router_simulation().
    """
    # Import inside the test body (not at module top) so collection succeeds
    # cleanly today even though the module does not yet exist.
    from backtest.router_simulation import run_router_simulation  # noqa: F401
    assert callable(run_router_simulation)


@pytest.mark.slow
def test_aggregate_sharpe_beats_single_by_0_2():
    """ROUT-04 gate: aggregate router Sharpe >= max(best per-pair single) + 0.2."""
    from backtest.router_simulation import run_router_simulation
    report = run_router_simulation()
    assert report["gate_passed"] is True, (
        f"ROUT-04 FAILED: "
        f"aggregate={report.get('aggregate_sharpe')}, "
        f"baseline={report.get('best_single_sharpe')}, "
        f"need={report.get('baseline_plus_0_2')}"
    )


@pytest.mark.slow
def test_sim_report_schema():
    """V2/reports/router_4yr_simulation.json must contain ROUT-04 gate keys
    per CONTEXT D-18.
    """
    from backtest.router_simulation import run_router_simulation
    run_router_simulation()  # populates the report on disk
    # tests/v3_intelligence/__file__ -> tests/v3_intelligence -> tests -> V2 -> reports
    report_path = Path(__file__).resolve().parents[2] / "reports" / "router_4yr_simulation.json"
    assert report_path.exists(), (
        f"{report_path} not produced by run_router_simulation()"
    )
    report = json.loads(report_path.read_text())
    for key in ("aggregate_sharpe", "best_single_sharpe", "baseline_plus_0_2", "gate_passed"):
        assert key in report, (
            f"missing key {key!r} in {report_path}: keys={list(report.keys())}"
        )
