"""Phase 8.5 D-15 — thin CLI driver for temporal_analysis library.

Discovers active combos from PAIR_CONFIGS, anchors end_ts to min-of-maxes
across cache timeframes, wraps the entire batch run in a SINGLE PitClock
(RESEARCH Pitfall 5 — no nesting), writes per-combo CSVs to
.planning/phases/08.5-temporal-session-analysis/evidence/.

Plan 03 extends this driver to also render heatmaps;
Plan 04 adds risk-calendar emission via detect_and_write_risk_calendar;
Plan 05 adds session_config.py regeneration via regenerate_session_config.

Usage:
  cd V2 && python -m scripts.run_temporal_analysis            # full run
  cd V2 && python -m scripts.run_temporal_analysis --dry-run  # discover combos only
  cd V2 && python -m scripts.run_temporal_analysis --pair USDJPY  # single pair
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from v3_intelligence import temporal_analysis as ta
from v3_intelligence.pair_config import PAIR_CONFIGS
from v3_intelligence.pit import PitClock

EVIDENCE_DIR = (
    Path(__file__).resolve().parents[2]
    / ".planning" / "phases"
    / "08.5-temporal-session-analysis" / "evidence"
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run", action="store_true",
        help="Discover combos and report; do not load bars or write CSVs.",
    )
    p.add_argument(
        "--pair", default=None,
        help="Restrict to a single pair (e.g., USDJPY). Default: all 8.",
    )
    p.add_argument(
        "--out-dir", type=Path, default=EVIDENCE_DIR,
        help=f"Evidence output directory. Default: {EVIDENCE_DIR}",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Discover combos (RESEARCH Anti-Pattern: never hardcode the list)
    combos = ta.discover_active_combos(PAIR_CONFIGS)
    if args.pair:
        combos = [c for c in combos if c[0] == args.pair]
    print(f"[run_temporal_analysis] active combos: {len(combos)}")
    for pair, strat, tf in combos:
        print(f"  - {pair} / {strat} / {tf}")

    if args.dry_run:
        print("[run_temporal_analysis] dry-run complete — no analysis performed")
        return 0

    # Lazy-instantiate cache so dry-run path works without SUPABASE_DB_URL
    # (OHLCVCache constructor raises RuntimeError on missing env var).
    from v3_intelligence.cache import OHLCVCache
    cache = OHLCVCache()
    end_ts = ta.discover_end_ts(cache)
    print(f"[run_temporal_analysis] end_ts (PiT anchor) = {end_ts}")

    # Single PitClock wrap (Pitfall 5 — no nesting)
    with PitClock(end_ts):
        for pair, strategy, timeframe in combos:
            try:
                trades = ta.generate_trades(pair, strategy, timeframe, cache, end_ts)
                buckets = ta.bucket_trades(trades, timeframe)
                csv_path = ta.write_combo_csv(
                    buckets, pair, strategy, timeframe, out_dir
                )
                # SESS-02 (Plan 03): render heatmaps inside the same PitClock so
                # any incidental bar reads remain PiT-clamped. M15 emits hour+dow
                # only; H1/Daily additionally emit dom+doy (CONTEXT D-14).
                png_paths = ta.render_combo_heatmaps(
                    buckets, pair, strategy, timeframe, out_dir
                )
                print(
                    f"  [OK] {pair}/{strategy}/{timeframe} -> {csv_path.name} "
                    f"+ {len(png_paths)} PNGs ({len(trades)} trades)"
                )
            except Exception as e:
                print(
                    f"  [FAIL] {pair}/{strategy}/{timeframe}: "
                    f"{type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                # Don't stop the batch — record the failure and continue

        # SESS-03 (Plan 04): emit empirical risk calendar after per-combo work.
        # Pool detections across the unique pairs (single H1 pass per pair) so
        # patterns generalize beyond a single pair's view. Manual operator
        # entries from prior runs survive via write_risk_calendar's merge.
        try:
            unique_pairs = sorted({pair for pair, _, _ in combos})
            risk_path = out_dir / "risk_calendar.yaml"
            ta.detect_and_write_risk_calendar(
                cache=cache,
                pairs=unique_pairs,
                timeframe="H1",
                end_ts=end_ts,
                out_path=risk_path,
            )
            print(f"  [OK] risk_calendar.yaml -> {risk_path.name}")
        except Exception as e:
            print(
                f"  [FAIL] risk_calendar emission: {type(e).__name__}: {e}",
                file=sys.stderr,
            )

    # SESS-04 (Plan 05): regenerate session_config.py from evidence/. Sits
    # OUTSIDE the PitClock — it reads CSVs + YAML on disk, no bar reads.
    try:
        sc_target = (
            Path(__file__).resolve().parents[1]
            / "v3_intelligence" / "session_config.py"
        )
        ta.regenerate_session_config(
            evidence_dir=out_dir,
            target=sc_target,
            risk_calendar_path=out_dir / "risk_calendar.yaml",
        )
        print(f"  [OK] session_config.py regenerated -> {sc_target}")
    except Exception as e:
        print(
            f"  [FAIL] session_config regeneration: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
