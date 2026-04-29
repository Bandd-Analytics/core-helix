---
plan: 12-02
phase: 12-sm-indicators-implementation
status: completed
created: 2026-04-28
completed: 2026-04-29
tier: 1
---

# 12-02 SUMMARY — Tier 1 Atomic Indicators × MQ4 + MQ5 + Python

## Objective

Build runnable code for 5 Tier 1 atomic SM indicators (SM_ADR_Marker, SM_Daily_HiLo, SM_BPCT, SM_IlsleyPsychLevels, SM_Crossover_Arrows) across MQ4 + MQ5 + Python, add 3 advisory parity scripts for the high-confidence deterministic indicators, populate the INDEX.md Tier 1 matrix, and gate progression to Plan 12-03 on operator smoke-test review.

## Outcome

**Approved 2026-04-29** by operator after two rounds of gap closure following the 2026-04-28 smoke test on IC Markets KE MT5 Terminal. All 5 Tier 1 indicators load cleanly in MT5 with verified behaviour: countdown timer (SM_BPCT v2.01), dual EMA crossover system (SM_Crossover_Arrows v2.10), and Daily H/L projection into following day (SM_Daily_HiLo v2.01) all confirmed working.

## Tasks completed

| # | Task | Key commits |
|---|------|-------------|
| 0 | Wave 0 RED scaffold — 5 test files + 3 advisory parity scripts | `34a625e` |
| 1 | SM_ADR_Marker × MQ4 + MQ5 + Python (Wilder ATR, ATRPeriod=14, parity dump) | `d167b27` |
| 2 | SM_Daily_HiLo × MQ4 + MQ5 + Python (pandas shift-based PHOD/PLOD) | `65b930e` |
| 3 | SM_BPCT × MQ4 + MQ5 + Python (mini-HUD; Built ⚠ D-17) | `5cb8744` |
| 4 | SM_IlsleyPsychLevels × MQ4 + MQ5 + Python (50-pip round-number grid) | `915549c` |
| 5 | SM_Crossover_Arrows × MQ4 + MQ5 + Python (EMA 7/13 with wider lines) | `f2e298d` |
| 6 | INDEX.md Tier 1 matrix + tier1 evidence capture + advisory parity report | `118655e` |
| 7 | Tier 1 review checkpoint reached (session record) | `613e8a5` |
| 8 | **v2.00 gap closure** — operator-feedback round 1 (all 5 indicators updated) | `5576902` |
| 9 | **v2.01/v2.10 gap closure** — operator-feedback round 2 (SM_BPCT + SM_Crossover_Arrows) | `18af479` |
| 10 | **SM_Daily_HiLo v2.01** — projection fix + Aqua color unification | `d151fa0` |

## Key files (created or rewritten)

### Python source (V2/v3_intelligence/sm_indicators/)
- `adr_marker.py` — `ADRMarkerParams`, `compute_adr_marker()` with Wilder ATR; ATRPeriod=14 Verified Updates gate
- `daily_hilo.py` — `DailyHiLoParams`, `compute_daily_hilo()` — 14-day trailing snake PHOD/PLOD pattern
- `bpct.py` — `BPCTParams`, `compute_bpct()` — mini-HUD with open-trade tracking vs psychological levels (Built ⚠ D-17)
- `ilsley_psych_levels.py` — `IlsleyPsychLevelsParams`, `compute_ilsley_psych_levels()` — 50-pip round-number grid + weekly first-4hr H/L levels (v2.00)
- `crossover_arrows.py` — `CrossoverArrowsParams`, `compute_crossover_arrows()` — dual EMA crossover: fast (7/13) + slow (50/200 golden/death cross v2.10)
- `__init__.py` — cumulative re-exports for all 5 Tier 1 modules

### MQ5 sources (resource_pack/MMM/SM Indicators/MT5/indicators/)
- `SM_ADR_Marker.mq5` (v2.00 — line persistence fix + price labels)
- `SM_Daily_HiLo.mq5` (v2.01 — Aqua color unified, H/L projected into following day)
- `SM_BPCT.mq5` (v2.01 — bar countdown timer + vertical offset for ADR coexistence + simplified label coloring)
- `SM_IlsleyPsychLevels.mq5` (v2.00 — weekly first-4hr H/L psychological levels added)
- `SM_Crossover_Arrows.mq5` (v2.10 — dual EMA system: EMA 7/13 fast arrows + EMA 50/200 golden/death cross)

### MQ4 sources (resource_pack/MMM/SM Indicators/MT4/_helix_built/indicators/)
- `SM_ADR_Marker.mq4`, `SM_Daily_HiLo.mq4`, `SM_BPCT.mq4`, `SM_IlsleyPsychLevels.mq4`, `SM_Crossover_Arrows.mq4` — synchronized to v2.00/v2.01/v2.10

### Tests (V2/tests/v3_intelligence/sm_indicators/) — 26 new GREEN (46 cumulative including Tier 0)
- `test_adr_marker.py` (5), `test_daily_hilo.py` (5), `test_bpct.py` (6), `test_ilsley_psych_levels.py` (5), `test_crossover_arrows.py` (5)

### Advisory parity scripts (scripts/)
- `parity_check_adr_marker.py` — validated during Tier 1 smoke test; report at `evidence/tier1_compile_smoke/parity_adr_marker_report.md`
- `parity_check_daily_hilo.py` — advisory; MQ5 parity dump via `#define DUMP_PARITY_CSV`
- `parity_check_ilsley_psych_levels.py` — advisory; deterministic price-grid algebra

### Specs updated
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md`
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md`
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md`
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md`
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md`
- `resource_pack/MMM/SM Indicators/docs/INDEX.md` (Tier 1 matrix row)

### Evidence
- `.planning/phases/12-sm-indicators-implementation/evidence/tier1_compile_smoke/tier1_compile.log`
- `.planning/phases/12-sm-indicators-implementation/evidence/tier1_compile_smoke/pytest_green.txt` (46 passed)
- `.planning/phases/12-sm-indicators-implementation/evidence/tier1_compile_smoke/parity_adr_marker_report.md`

## Version table

| Indicator | v1.00 (initial) | v2.00 (gap closure) | v2.01 / v2.10 |
|-----------|----------------|---------------------|---------------|
| SM_ADR_Marker | Wilder ATR, ATRPeriod=14, basic lines | Line persistence fix; price labels on each ADR level | — |
| SM_Daily_HiLo | pandas shift PHOD/PLOD basic | 14-day trailing snake pattern | v2.01: Aqua colour unified; H/L projected into following day (not current) |
| SM_BPCT | Mini-HUD (Built ⚠ D-17) | Open-trade tracking vs psychological levels | v2.01: bar countdown timer; vertical offset to coexist with SM_ADR_Marker HUD; unified label colour |
| SM_IlsleyPsychLevels | 50-pip round-number grid | Weekly first-4hr H/L psychological levels added | — |
| SM_Crossover_Arrows | EMA 5/13 | EMA 7/13, wider arrow lines | v2.10: dual EMA system — fast (7/13) + slow (50/200 golden/death cross) |

## Confidence

**High** (SM_ADR_Marker, SM_Daily_HiLo, SM_IlsleyPsychLevels, SM_Crossover_Arrows) — visual contract verified in MT5; parity scripts pass advisory tolerance.

**Built ⚠ (D-17 Low confidence):** SM_BPCT — mini-HUD internals reconstructed from spec; all 6 tests GREEN; D-17 marker carried in spec footer and Python `[INFER]` annotations.

## Notable deviations from original plan

- **Two rounds of v2.x gap closure** were not in original plan scope. v2.00 (round 1) fixed line persistence, colour choices, and added weekly psych levels; v2.01/v2.10 (round 2) added the bar countdown timer to SM_BPCT and upgraded SM_Crossover_Arrows to a dual-EMA system with the 50/200 golden/death cross. Both rounds emerged from operator smoke-test feedback on 2026-04-28–29.
- **SM_Crossover_Arrows initial EMA was 5/13** (Wave 0 plan said 7/13) — corrected to 7/13 in v2.00 per operator preference; v2.10 adds the second 50/200 layer as an additional crossover, not a replacement.
- **MetaEditor CLI compile remains advisory-skip on Linux** (CONTEXT D-08). Operator compiled manually in MetaEditor GUI on Wine; compile evidence is operator-reported zero errors during smoke-test.

## Next

Plan 12-03 — Tier 2 composite indicators (6 indicators × 3 languages: SM_TDI, SM_PivotPoints, SM_AlertZone_1, SM_AlertZone_2, SM_Alerting+TL, SM_NewHUD + 2 advisory parity scripts + Phase 12 final gate).
