"""ROUT-04 simulation CLI driver (CONTEXT D-18 / Phase 9 P04).

Usage:
    cd V2 && python -m scripts.run_router_simulation
    cd V2 && python -m scripts.run_router_simulation --report-path /tmp/sim.json
    cd V2 && python -m scripts.run_router_simulation --rag-collection custom_sim
    cd V2 && python -m scripts.run_router_simulation --no-rag-learning  # debugging

Exits 0 if gate_passed=true; exits 1 otherwise (Phase 7 BKTS-04 gate-as-CLI pattern).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="JSON output path (default: V2/reports/router_4yr_simulation.json)",
    )
    parser.add_argument(
        "--sim-db",
        type=Path,
        default=None,
        help="Sim-only SQLite DB path (default: V2/reports/router_simulation_trades.db)",
    )
    parser.add_argument(
        "--rag-collection",
        default="router_sim_trades",
        help=(
            "ChromaDB collection for sim trades "
            "(default: router_sim_trades — kept separate from production)"
        ),
    )
    parser.add_argument(
        "--no-rag-learning",
        action="store_true",
        help="Disable on_trade_close RAG indexing (debugging — gate 4 stays cold-start)",
    )
    parser.add_argument(
        "--max-ts",
        default=None,
        help=(
            "Optional ISO-8601 timestamp to truncate sim window to (for wall-time-bounded "
            "evaluation). When omitted, runs the full 4yr corpus."
        ),
    )
    args = parser.parse_args(argv)

    # Lazy import — slow heavy imports only after argparse succeeds (matches
    # V2/scripts/run_temporal_analysis.py precedent).
    from backtest.router_simulation import run_router_simulation
    import pandas as pd

    max_ts = pd.Timestamp(args.max_ts) if args.max_ts is not None else None

    report = run_router_simulation(
        report_path=args.report_path,
        sim_db_path=args.sim_db,
        rag_collection=args.rag_collection,
        warm_rag=not args.no_rag_learning,
        max_ts=max_ts,
    )

    print("\n" + "=" * 70)
    print("ROUT-04 4yr Simulation Report")
    print("=" * 70)
    print(json.dumps(report, indent=2, default=str))
    print("=" * 70)
    if report["gate_passed"]:
        print(
            f"GATE PASSED: aggregate_sharpe={report['aggregate_sharpe']:.4f} "
            f">= baseline_plus_0_2={report['baseline_plus_0_2']:.4f}"
        )
        return 0
    print(
        f"GATE FAILED: aggregate_sharpe={report['aggregate_sharpe']:.4f} "
        f"< baseline_plus_0_2={report['baseline_plus_0_2']:.4f} "
        f"(best_single_sharpe={report['best_single_sharpe']:.4f})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
