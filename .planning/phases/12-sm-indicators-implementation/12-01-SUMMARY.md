---
plan: 12-01
phase: 12-sm-indicators-implementation
status: completed
created: 2026-04-27
completed: 2026-04-28
tier: 0
---

# 12-01 SUMMARY — Tier 0 SM Indicators Helpers + Phase Scaffold

## Objective

Build runnable code for the 3 Tier 0 helper indicators (`sm_gmtoffset`, `sm_WorkTime`, `sm_WorkTime_no_autogmt`) in MQ4 + MQ5 + Python, set up the Phase-12-wide compile/test scaffold, and gate progression to Plan 12-02 on operator review of Tier 0 compile + smoke evidence.

## Outcome

**Approved 2026-04-28** by operator after smoke-load on IC Markets KE MT5 Terminal. Tier 0 helpers are visually contracted to `V2/indicators/BandD_WorktimeRibbon.mq5` and produce session-H/L-bounded boxes with changeover gap windows for stop-hunt / reversal observation.

## Tasks completed

| # | Task | Commit |
|---|------|--------|
| 0 | Wave 0 RED scaffold (compile scripts, gitignore, package skeleton, conftest, RED tests) | `ea0c54d` |
| 1 | sm_gmtoffset × MQ4 + MQ5 + Python (5 tests GREEN) | `2439e3a` |
| 2 | sm_WorkTime × MQ4 + MQ5 + Python (6 tests GREEN) | `57deeab` |
| 3 | sm_WorkTime_no_autogmt × MQ4 + MQ5 + Python (4 tests GREEN, no-sm_gmtoffset gate PASS) | `b9c684c` |
| 4 | INDEX.md Implementation matrix + Tier 0 evidence capture | `e3ecc4f` |
| 5 | Tier 0 review checkpoint — operator smoke-test surfaced gaps | `bdc8138` |
| 6 | **v2.00 gap closure** — BandD ribbon parity + sm_gmtoffset corner label | `5179fa1` |
| 7 | Approval-date substitution (placeholders → `2026-04-28`) | `0ac509c` |

## Key files (created or rewritten)

### Source code
- `V2/v3_intelligence/sm_indicators/__init__.py`, `helpers/__init__.py`
- `V2/v3_intelligence/sm_indicators/helpers/sm_gmtoffset.py`
- `V2/v3_intelligence/sm_indicators/helpers/sm_worktime.py` (v2.00)
- `V2/v3_intelligence/sm_indicators/helpers/sm_worktime_no_autogmt.py` (v2.00)
- `resource_pack/MMM/SM Indicators/MT5/helpers/sm_gmtoffset.mq5` (v2.00 — corner label)
- `resource_pack/MMM/SM Indicators/MT5/helpers/sm_WorkTime.mq5` (v2.00 — BandD parity)
- `resource_pack/MMM/SM Indicators/MT5/helpers/sm_WorkTime_no_autogmt.mq5` (v2.00 — BandD parity)
- `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_gmtoffset.mq4` (v2.00)
- `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_WorkTime.mq4` (v2.00)
- `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_WorkTime_no_autogmt.mq4` (v2.00)

### Phase scaffold
- `scripts/compile_mq.sh`, `scripts/compile_mq_all_tier.sh`
- `.gitignore` (compiled binaries `*.ex4` / `*.ex5`)
- `V2/tests/v3_intelligence/sm_indicators/conftest.py` (synthetic OHLCV fixtures)
- `resource_pack/MMM/SM Indicators/MT4/_helix_built/README.md`

### Tests (20 GREEN total — 15 v1 + 5 v2.00)
- `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_gmtoffset.py` (5)
- `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_worktime.py` (10)
- `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_worktime_no_autogmt.py` (5)

### Specs updated
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md`
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md`
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md`
- `resource_pack/MMM/SM Indicators/docs/INDEX.md`

### Evidence
- `.planning/phases/12-sm-indicators-implementation/evidence/tier0_compile_smoke/tier0_compile.log`
- `.planning/phases/12-sm-indicators-implementation/evidence/tier0_compile_smoke/pytest_green.txt`

## v2.00 visual contract (Phase 12 gap closure)

Operator smoke-test on 2026-04-28 surfaced two gaps in the as-implemented 2011-era spec:

1. `sm_gmtoffset`'s `Comment()` text gets buried by other indicators that also call `Comment()` — apparent invisibility.
2. `sm_WorkTime`'s dark full-chart-range bands diverge from the operator's working setup (`V2/indicators/BandD_WorktimeRibbon.mq5`).

v2.00 closes both gaps:

- **`sm_gmtoffset`** — Persistent `OBJ_LABEL` "sm_GMTOffset: +Xh" in upper-right corner (configurable corner / color / font / offsets)
- **`sm_WorkTime` + `sm_WorkTime_no_autogmt`** — BandD ribbon parity:
  - Box height = session H/L (`CopyRates` / `iHigh`+`iLow`)
  - Light colors (`clrLightBlue` Asia / `clrLightGray` London-Gap+London+NY-Gap / `clrBrown` NY)
  - 20% opacity via `ColorToARGB` (MQ5)
  - Changeover gap boxes (London 09:00→10:00, NY 15:00→16:00 — ±30m around session open)
  - Optional Asian Range (AR Line) — horizontal H/L extending past Asia close
  - Pip-range labels ("R=92.4")
  - HH:MM string inputs (broker time defaults)
  - Skip weekends, 500ms timer, per-chart prefix
- **Python** — `LONDON_GAP` and `NY_GAP` labels added to `session_label`; gap labels overwrite session labels at overlap; `show_gaps=True` is the new default. Optional `show_asia_range=True` attaches `asia_range_high/low/pips` columns.

D-19 architectural distinction preserved: `sm_WorkTime` reads `sm_GMTOffset` GlobalVariable (auto via `sm_gmtoffset`); `sm_WorkTime_no_autogmt` uses `InpBrokerGMT` manual input only.

## Confidence

**High** — visual contract verified against operator-confirmed reference (BandD_WorktimeRibbon screenshot 2026-04-28); D-19 architectural distinction grep-gated and passing; 20/20 helper tests GREEN; phase 8/8.4/8.5 fast suite shows no regression.

## Notable deviations from original plan

- **v2.00 visual rework was not in original plan scope** — it emerged as gap-closure during the Tier 0 review checkpoint when the operator smoke-loaded the v1.00 binaries against their working BandD reference. Captured as a single coherent commit (`5179fa1`) covering MQ4 + MQ5 + Python + tests + specs to keep all targets in sync.
- **MetaEditor CLI compile remains advisory-skip on Linux** (CONTEXT D-08). Operator compiled manually in MetaEditor GUI on Wine; compile evidence is the absence of error reports during smoke-test rather than CLI exit status.

## Next

Plan 12-02 — Tier 1 atomic indicators (5 indicators × 3 languages: SM_ADR_Marker, SM_Daily_HiLo, SM_BPCT, SM_IlsleyPsychLevels, SM_Crossover_Arrows + 3 advisory parity scripts).
