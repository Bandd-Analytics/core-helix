---
phase: 12
slug: sm-indicators-implementation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `12-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already installed in V2 environment) |
| **Config file** | `V2/pyproject.toml` (existing) — pytest config under `[tool.pytest.ini_options]` |
| **Quick run command** | `cd V2 && pytest -v tests/v3_intelligence/sm_indicators/test_<name>.py` |
| **Full suite command** | `cd V2 && pytest -v tests/v3_intelligence/sm_indicators/` |
| **Estimated runtime** | < 30 seconds for full suite (no slow integration tests; all use synthetic or pre-loaded CSV fixtures) |
| **MQ4/MQ5 compile gate** | `bash scripts/compile_mq.sh <src>` — exits 0 on "0 errors, 0 warnings" + `.ex*` mtime check |

---

## Sampling Rate

- **After every task commit:** `pytest -v V2/tests/v3_intelligence/sm_indicators/test_<name>.py && bash scripts/compile_mq.sh <mq5> && bash scripts/compile_mq.sh <mq4>` (≤ 5 seconds per-task)
- **After every plan wave (= per tier):** Full Phase 12 pytest suite + all-tier compile gate: `pytest -v V2/tests/v3_intelligence/sm_indicators/ && bash scripts/compile_mq_all_tier.sh <tier>` (≤ 30 seconds)
- **Before `/gsd:verify-work 12`:** Full suite GREEN + tier-3 review approved + advisory parity reports captured
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Phase 12 has no formal REQ-IDs. Success criteria derive from CONTEXT.md decisions D-08 (MQ4 compile+load), D-09 (MQ5 compile+load), D-10 (Python pytest GREEN), and the 14 spec files.

| Task ID | Plan | Wave | Indicator (Tier) | Test Type | Automated Command | File Exists | Status |
|---------|------|------|------------------|-----------|-------------------|-------------|--------|
| 12-01-T0a | 01 | 1 | sm_gmtoffset (T0) | Python unit | `pytest -v V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_gmtoffset.py` | ❌ W0 | ⬜ pending |
| 12-01-T0a | 01 | 1 | sm_gmtoffset (T0) | MQ5 compile | `bash scripts/compile_mq.sh resource_pack/MMM/SM\ Indicators/MT5/helpers/sm_gmtoffset.mq5` | ❌ W0 | ⬜ pending |
| 12-01-T0a | 01 | 1 | sm_gmtoffset (T0) | MQ4 compile | `bash scripts/compile_mq.sh "resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_gmtoffset.mq4"` | ❌ W0 | ⬜ pending |
| 12-01-T0b | 01 | 1 | sm_WorkTime (T0) | Python unit | `pytest -v .../helpers/test_sm_worktime.py` | ❌ W0 | ⬜ pending |
| 12-01-T0b | 01 | 1 | sm_WorkTime (T0) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-01-T0b | 01 | 1 | sm_WorkTime (T0) | Smoke chart load | operator (manual) | manual | ⬜ pending |
| 12-01-T0c | 01 | 1 | sm_WorkTime_no_autogmt (T0) | Python unit | `pytest -v .../helpers/test_sm_worktime_no_autogmt.py` | ❌ W0 | ⬜ pending |
| 12-01-T0c | 01 | 1 | sm_WorkTime_no_autogmt (T0) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-02-T1a | 02 | 1 | SM_ADR_Marker (T1) | Python unit | `pytest -v .../test_adr_marker.py` | ❌ W0 | ⬜ pending |
| 12-02-T1a | 02 | 1 | SM_ADR_Marker (T1) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-02-T1a | 02 | 1 | SM_ADR_Marker (T1) | Advisory parity | `python scripts/parity_check_adr_marker.py` | ❌ W0 | ⬜ pending |
| 12-02-T1b | 02 | 1 | SM_Daily_HiLo (T1) | Python unit | `pytest -v .../test_daily_hilo.py` | ❌ W0 | ⬜ pending |
| 12-02-T1b | 02 | 1 | SM_Daily_HiLo (T1) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-02-T1b | 02 | 1 | SM_Daily_HiLo (T1) | Advisory parity | `python scripts/parity_check_daily_hilo.py` | ❌ W0 | ⬜ pending |
| 12-02-T1c | 02 | 1 | SM_BPCT (T1, ⚠) | Python unit (shape) | `pytest -v .../test_bpct.py` | ❌ W0 | ⬜ pending |
| 12-02-T1c | 02 | 1 | SM_BPCT (T1, ⚠) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-02-T1d | 02 | 1 | SM_IlsleyPsychLevels (T1) | Python unit | `pytest -v .../test_ilsley_psych_levels.py` | ❌ W0 | ⬜ pending |
| 12-02-T1d | 02 | 1 | SM_IlsleyPsychLevels (T1) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-02-T1d | 02 | 1 | SM_IlsleyPsychLevels (T1) | Advisory parity | `python scripts/parity_check_ilsley_psych_levels.py` | ❌ W0 | ⬜ pending |
| 12-02-T1e | 02 | 1 | SM_Crossover_Arrows (T1) | Python unit | `pytest -v .../test_crossover_arrows.py` | ❌ W0 | ⬜ pending |
| 12-02-T1e | 02 | 1 | SM_Crossover_Arrows (T1) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2a | 03 | 1 | SM_TDI (T2) | Python unit (5 cases) | `pytest -v .../test_tdi.py` | ❌ W0 | ⬜ pending |
| 12-03-T2a | 03 | 1 | SM_TDI (T2) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2a | 03 | 1 | SM_TDI (T2) | Advisory parity | `python scripts/parity_check_tdi.py` | ❌ W0 | ⬜ pending |
| 12-03-T2b | 03 | 1 | SM_PivotPoints (T2) | Python unit | `pytest -v .../test_pivot_points.py` | ❌ W0 | ⬜ pending |
| 12-03-T2b | 03 | 1 | SM_PivotPoints (T2) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2b | 03 | 1 | SM_PivotPoints (T2) | Advisory parity | `python scripts/parity_check_pivot_points.py` | ❌ W0 | ⬜ pending |
| 12-03-T2c | 03 | 1 | SM_AlertZone_1 (T2) | Python unit | `pytest -v .../test_alert_zone_1.py` | ❌ W0 | ⬜ pending |
| 12-03-T2c | 03 | 1 | SM_AlertZone_1 (T2) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2d | 03 | 1 | SM_AlertZone_2 (T2) | Python unit | `pytest -v .../test_alert_zone_2.py` | ❌ W0 | ⬜ pending |
| 12-03-T2d | 03 | 1 | SM_AlertZone_2 (T2) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2e | 03 | 1 | SM_Alerting+TL (T2) | Python unit | `pytest -v .../test_alerting_tl.py` | ❌ W0 | ⬜ pending |
| 12-03-T2e | 03 | 1 | SM_Alerting+TL (T2) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |
| 12-03-T2f | 03 | 1 | SM_NewHUD (T2, ⚠) | Python unit (shape) | `pytest -v .../test_new_hud.py` | ❌ W0 | ⬜ pending |
| 12-03-T2f | 03 | 1 | SM_NewHUD (T2, ⚠) | MQ4/MQ5 compile | `bash scripts/compile_mq.sh <mq4|mq5>` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Wave 0 gaps are scaffolded by each plan's first task — see "Wave 0 Requirements" below.*

---

## Wave 0 Requirements

Each plan begins with its own Wave 0 RED scaffold (RED-test files + compile script + package skeletons). This matches the Phase 8 / Phase 8.4 / Phase 11 wave-model cadence rather than a single Phase-12-wide Wave 0.

**Plan 12-01 Wave 0 (Tier 0 helpers — 3 specs):**

- [ ] `V2/tests/v3_intelligence/sm_indicators/__init__.py` — new test package
- [ ] `V2/tests/v3_intelligence/sm_indicators/conftest.py` — OHLCV fixtures (`ohlcv_eurusd_h1`, `ohlcv_usdjpy_h1`, `ohlcv_gbpnzd_h1`, `synthetic_ohlc_uptrend`, `synthetic_doji`)
- [ ] `V2/tests/v3_intelligence/sm_indicators/helpers/__init__.py` + `helpers/test_*.py` — 3 RED test files (sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt)
- [ ] `V2/v3_intelligence/sm_indicators/__init__.py` + `helpers/__init__.py` — empty packages so RED imports resolve
- [ ] `scripts/compile_mq.sh` — Wine MetaEditor wrapper with `/log:` parse + `.ex*` mtime check
- [ ] `scripts/compile_mq_all_tier.sh` — wraps `compile_mq.sh` across an entire tier's MQ4 + MQ5 sources
- [ ] `.gitignore` addition: `*.ex5`, `*.ex4`, plus `!resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/*.ex4` exception (preserves Phase 11 originals)
- [ ] `resource_pack/MMM/SM Indicators/MT4/_helix_built/README.md` — explains "these are reconstructions of !SM_*.ex4 originals from docs/ specs"
- [ ] Verify operator MT4 install path (D-08 smoke load) — Plan 12-01 Task 1 step; defer if absent (per RESEARCH.md Open Question #2)

**Plan 12-02 Wave 0 (Tier 1 atomic — 5 specs):**

- [ ] `V2/tests/v3_intelligence/sm_indicators/test_<name>.py` × 5 — RED test files (adr_marker, daily_hilo, bpct, ilsley_psych_levels, crossover_arrows)
- [ ] `scripts/parity_check_adr_marker.py` — first parity check; validates 1e-4 tolerance achievability before applying same approach to TDI/Pivots (per RESEARCH.md Open Question #3)
- [ ] `scripts/parity_check_<name>.py` × 2 more — daily_hilo, ilsley_psych_levels (high-confidence atomic indicators)

**Plan 12-03 Wave 0 (Tier 2 composite — 6 specs):**

- [ ] `V2/tests/v3_intelligence/sm_indicators/test_<name>.py` × 6 — RED test files (tdi, pivot_points, alert_zone_1, alert_zone_2, alerting_tl, new_hud)
- [ ] `scripts/parity_check_tdi.py`, `scripts/parity_check_pivot_points.py` — last 2 advisory parity scripts (high-confidence composites)

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| MQ4 indicator loads on chart in MT4 (Wine) without runtime error | D-08 | Spawned executor cannot drive Wine GUI (Phase 8.4 P04 SUMMARY documented this) | Operator: open Wine MT4 → File → Open Data Folder → MQL4/Indicators → drag-drop or Refresh → drag indicator to a chart → confirm no Experts-tab errors. Capture PNG into `evidence/tier{N}_compile_smoke/`. |
| MQ5 indicator loads on chart in IC Markets KE MT5 (Wine) without runtime error | D-09 | Same Wine-GUI constraint | Operator: open IC Markets KE MT5 → MQL5/Indicators → drag indicator to chart → confirm Experts log silent. Capture PNG into evidence dir. Files copied to `~/.mt5/.../IC Markets KE MT5 Terminal/MQL5/Indicators/` per Phase 8.4 P04 precedent. |
| Advisory parity: MQ5 buffer matches Python compute() within tolerance (1e-4 prices, 1e-6 ratios) | D-15 | Manual MQ5 strategy-tester run with `#define DUMP_PARITY_CSV` to emit `MQL5/Files/parity_<name>.csv`; then python diff script | Operator: 1) compile MQ5 with `DUMP_PARITY_CSV` flag, 2) run on EURUSD H1 fixture range in strategy tester, 3) collect `MQL5/Files/parity_<name>.csv`, 4) `python scripts/parity_check_<name>.py` reports max-abs-diff. **Captured as evidence, not a blocker.** |
| Spec footer "Implementation status (Phase 12)" appended to each spec | D-13 | Mechanical edit per task; verifiable via `grep "Implementation status (Phase 12)"` | Automated grep gate per task acceptance criteria. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify command or are flagged Manual-Only above
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify (Python pytest + MQ compile cover every task)
- [ ] Wave 0 covers all MISSING references in the per-task verification map (3 plans, RED scaffolds plus compile scripts plus parity scripts)
- [ ] No watch-mode flags (`pytest --watch` not used; per-task command is one-shot)
- [ ] Feedback latency < 30s (verified — full suite < 30s per RESEARCH.md)
- [ ] Manual-only items (D-08/D-09 chart-load, D-15 advisory parity) explicitly listed and not blocking tier review per CONTEXT.md (D-15 advisory)
- [ ] `nyquist_compliant: true` set in frontmatter once Wave 0 of all 3 plans is built and the per-task map shows automated commands resolving to existing files

**Approval:** pending
