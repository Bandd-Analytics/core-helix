---
phase: 11-sm-indicators-full-spec-documentation
plan: "03"
subsystem: documentation
tags: [documentation, MT4, MQL4, SM-indicators, Tier-2, TDI, pivots, alert-zones, HUD, spec-writing]
dependency_graph:
  requires: ["11-00", "11-01", "11-02"]
  provides:
    - "SM_TDI.md: reconstruction-grade HIGH-confidence TDI spec from MMM TDI Tradestation PDF"
    - "SM_PivotPoints.md: daily pivot calculator with MMM-specific M1-M4 mid-pivots"
    - "SM_AlertZone_1.md: lower price-zone alerter for long setups"
    - "SM_AlertZone_2.md: upper price-zone alerter for short setups"
    - "SM_Alerting+TL.md: trendline-touch alerter via OBJ_TREND iteration"
    - "SM_NewHUD.md: heads-up display dashboard — the most complex SM indicator (100KB binary)"
  affects:
    - "11-04 (INDEX.md) — Tier 2 specs complete the 14-spec corpus; INDEX.md can now cross-link all specs"
tech_stack:
  added: []
  patterns:
    - "12-section locked template (Header/Purpose/Inputs/Outputs/Calculation/Pseudocode/Visual/Dependencies/Edge cases/Test cases/Port notes/Uncertainty log)"
    - "[INFER] for medium-confidence claims; [INFER:guess] for low-confidence / speculative claims"
    - "Confidence: High / Medium / Low declared in Header table"
    - "Per-trendline state machine pattern (last_alert_time + prev_side maps) for SM_Alerting+TL"
    - "Timer-based multi-field refresh pattern for SM_NewHUD (OnTimer every RefreshSeconds)"
key_files:
  created:
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md"
  modified: []
decisions:
  - "SM_TDI StdDev multiplier documented as 1.6185 [INFER] vs 2.0 — 1.6185 is the most-cited value for the original Malone TDI; MT4 operator confirmation required"
  - "SM_AlertZone_1 vs SM_AlertZone_2 hypothesis: same algorithm compiled with different defaults (color, sound) — 148-byte size delta is consistent with default-only difference, not separate algorithms"
  - "SM_NewHUD internals: iCustom vs internal-recompute documented as the single most important unknown; 100KB binary size makes self-contained computation more plausible"
  - "SM_Alerting+TL filename preserves +TL suffix verbatim; +v1.1 version suffix dropped per CONTEXT.md naming decision"
  - "SM_NewHUD fields anchored to MMM Book pp.53-54 Scanning View + Market Maker Cycle.jpg — 10 display sections documented as likely HUD fields"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-26"
  tasks_completed: 6
  tasks_total: 6
  files_created: 6
  files_modified: 0
---

# Phase 11 Plan 03: Tier 2 Composite Indicators — Summary

**One-liner:** Six Tier 2 SM indicator specs completed — TDI (RSI-13/levels-32-50-68/three-alerts), PivotPoints (M1-M4 mid-pivots), AlertZone pair (148-byte same-algorithm hypothesis), Alerting+TL (OBJ_TREND slope/projection), NewHUD (428 lines / 10-field dashboard) — all passing check_spec.sh.

---

## What Was Built

Six reconstruction-grade markdown specs for the Tier 2 composite SM indicators. All 14 SM indicator specs are now complete (3 helpers + 5 Tier 1 + 6 Tier 2 = 14 files). check_all.sh confirms 14/15 files present (INDEX.md intentionally absent — written in Plan 04).

### Per-Indicator Summary

| Indicator | File | Confidence | Lines | [INFER] count | [INFER:guess] count | Key source |
|-----------|------|------------|-------|---------------|---------------------|------------|
| SM_TDI | SM_TDI.md | **High** | 343 | 10 | 0 | MMM TDI Tradestation PDF + community cross-confirmation |
| SM_PivotPoints | SM_PivotPoints.md | **High** | 315 | 11 | 0 | Standard pivot formula + MMM Book pp.42-43 (M1-M4) |
| SM_AlertZone_1 | SM_AlertZone_1.md | **Medium** | 241 | 10 | 0 | MMM Strike Zone concept (MMM Book p.55 / Glossary) |
| SM_AlertZone_2 | SM_AlertZone_2.md | **Medium** | 245 | 8 | 0 | AlertZone_1 sibling; 148-byte delta documented |
| SM_Alerting+TL | SM_Alerting+TL.md | **Medium** | 288 | 10 | 0 | RESEARCH.md §2 Tier 2 TL dossier; OBJ_TREND iteration |
| SM_NewHUD | SM_NewHUD.md | **Low** | 428 | 13 | 4 | MMM Book pp.53-54 + Market Maker Cycle.jpg |

---

## TDI Spot-Check Rubric (VALIDATION.md §4.2)

Verification against MMM TDI Tradestation PDF claims:

| Claim in Spec | Expected (from PDF) | Status |
|---------------|---------------------|--------|
| 5 lines + 3 levels | Green/Red/Yellow/Blue(×2) + 32/50/68 | PASS |
| Green = RSI PL | 2-period SMA of RSI | PASS |
| Red = TSL | 7-period SMA of RSI | PASS |
| Yellow = MBL | 34-period SMA of RSI | PASS |
| Blue = VB | Bollinger on MBL, period 34 | PASS |
| 68 level = Buying Exhaustion | Overbought signal | PASS |
| 32 level = Selling Exhaustion | Oversold signal | PASS |
| TDI Signal Cross alert | Green crosses Red | PASS |
| MBL Cross alert conditions | Green crosses Yellow + price confirmation | PASS |
| TDI Hook alert conditions | Green hooks from 32/68 across VB | PASS |

All 10 spot-check rows satisfied. SM_TDI.md cites "MMM TDI Tradestation PDF" directly in Purpose and parameter confidence notes. RSI Period 13 is confirmed by `grep -qE "RSI_Period.*13"`.

**Open item:** StdDev multiplier 1.6185 vs 2.0 — documented as [INFER]; an MT4 operator reading the parameter dialog resolves this immediately.

---

## NewHUD Page Count and Field Count

- **Line count:** 428 (target was ≥ 250; exceeds by 178 lines)
- **Enabled display sections:** 10 (`ShowSession`, `ShowSpread`, `ShowADR`, `ShowTDI`, `ShowPivots`, `ShowHODLOD`, `ShowDailyColour`, `ShowMMCycle`, `ShowAccount`, `ShowMultiPair`)
- **Inputs table rows:** 19 (exceeds the ≥15-row target)
- **Test cases:** 6 (exceeds ≥4 requirement)
- **Uncertainty log entries:** 15 (exceeds ≥10 requirement)
- **Pseudocode lines:** 45+ lines (well above 10-line minimum)
- **Confidence:** Low for internals; Medium for purpose and field list

**MMM Book anchoring:** The HUD field list is directly grounded in MMM Book p. 53 (Scanning View — Intraday Directional Matrix: Daily Colour, The Count, The Range) and MMM Book p. 54 (Put the Chart Together questionnaire — 12 fields). Market Maker Cycle.jpg cited as source for the ShowMMCycle field (3-day accumulation/move/distribution cycle stage indicator).

---

## AlertZone_1 vs AlertZone_2 — Algorithm vs Defaults

Both specs are self-consistent in documenting the **same-algorithm / different-defaults hypothesis**:

- Evidence: 148-byte file size delta (12,562 vs 12,710 bytes) — too small for a different algorithm; consistent with a different string literal (color constant name, sound filename, or object prefix)
- AlertZone_1: lower zone / long-setup variant (inferred from naming convention: "1" = first/lower)
- AlertZone_2: upper zone / short-setup variant (inferred: "2" = second/upper; ZoneColor default inferred as red/orange vs AlertZone_1's blue)
- Both specs acknowledge the ambiguity in their Uncertainty log: "Whether AlertZone_1 vs AlertZone_2 differ in algorithm or only in defaults — 148-byte file size delta is the sole objective evidence"
- Both specs demonstrate the symmetric use case: either indicator can be configured for either zone; the "1=lower / 2=upper" interpretation is convention, not a code constraint

The dual-zone test case in AlertZone_2.md explicitly shows both indicators loaded simultaneously with complementary zones.

---

## Operator Follow-Up Items (MT4 Terminal Required)

These uncertainties can be resolved immediately by an operator who can run the indicators in MT4 and read the parameter dialogs or observe chart behavior:

1. **SM_TDI StdDev multiplier:** Run SM_TDI on any chart → read the "StdDev" parameter default value in the Inputs tab. The spec documents 1.6185 as the inferred default; could be 2.0.
2. **SM_AlertZone_1 vs SM_AlertZone_2 distinction:** Run both indicators on the same chart → compare parameter dialogs. The 148-byte delta corresponds to one or two specific parameter differences (color / sound / prefix).
3. **SM_NewHUD field set:** Run SM_NewHUD on a EURUSD H1 chart → capture a screenshot. The full field list is immediately visible. Compare against the 10-section list in this spec.
4. **SM_Alerting+TL TouchPips default:** Run the indicator → read the default in the Inputs tab. The spec infers 2 pips; could be 5 or 10.
5. **SM_TDI buffer exposure:** Run SM_TDI on a chart; attempt to read buffer 0 via iCustom from an EA or a second indicator. If successful → SM_TDI exposes buffers. If not → visual-only.
6. **SM_NewHUD iCustom vs internal computation:** Load SM_TDI and SM_NewHUD on the same chart, then remove SM_TDI. If the TDI field in the HUD goes blank/N/A → HUD uses iCustom. If it continues showing values → HUD computes internally.

---

## Deviations from Plan

None — all 6 tasks executed exactly as written. The plan specifications for each indicator were detailed enough that no additional architectural decisions were needed during execution.

### Ancillary observations

- SM_NewHUD at 428 lines significantly exceeds the "5-7 pages" target from CONTEXT.md §Specifics — the 10-field scope and 15-entry Uncertainty log drove the length; this is appropriate given the Confidence: Low classification requiring extensive documentation of uncertainty.
- The pre-existing `check_all.sh` warnings (2 dependency-graph warnings about sm_gmtoffset.md and sm_WorkTime_no_autogmt.md) are from Plan 01 — not introduced by this plan.

---

## Verification Results

### check_spec.sh (6 Tier 2 specs)

| Spec | Exit code | Sections | Confidence | [INFER] | Pseudocode ≥10 lines | Inputs table | ≥2 test cases | MQ4/MQ5/Python |
|------|-----------|----------|------------|---------|---------------------|--------------|----------------|----------------|
| SM_TDI.md | 0 PASS | 12/12 | High | yes | yes | yes | yes (5 cases) | yes |
| SM_PivotPoints.md | 0 PASS | 12/12 | High | yes | yes | yes | yes (3 cases) | yes |
| SM_AlertZone_1.md | 0 PASS | 12/12 | Medium | yes | yes | yes | yes (3 cases) | yes |
| SM_AlertZone_2.md | 0 PASS | 12/12 | Medium | yes | yes | yes | yes (3 cases) | yes |
| SM_Alerting+TL.md | 0 PASS | 12/12 | Medium | yes | yes | yes | yes (3 cases) | yes |
| SM_NewHUD.md | 0 PASS | 12/12 | Low | yes | yes | yes | yes (6 cases) | yes |

### check_all.sh (all 14 specs)

- Files expected: 15 (14 specs + INDEX.md)
- Files present: 14 (INDEX.md intentionally absent — Plan 04)
- Files passing check_spec.sh: 14/14
- Dep-graph warnings: 2 (pre-existing from Plan 01; not introduced by this plan)

### Additional spot-checks

| Assertion | Command | Result |
|-----------|---------|--------|
| SM_TDI RSI period 13 | `grep -qE "RSI_Period.*13"` | PASS |
| SM_TDI level 32 | `grep -q "32"` | PASS |
| SM_TDI level 50 | `grep -q "50"` | PASS |
| SM_TDI level 68 | `grep -q "68"` | PASS |
| SM_PivotPoints M1-M4 | `grep -qE "M1|M2|M3|M4"` | PASS |
| SM_PivotPoints MMM Book pp.42-43 | `grep -qE "p\. ?42\|p\. ?43"` | PASS |
| SM_AlertZone_1 references AlertZone_2 | `grep -qi "AlertZone_2"` | PASS |
| SM_AlertZone_2 references AlertZone_1 | `grep -qi "AlertZone_1"` | PASS |
| SM_Alerting+TL OBJ_TREND reference | `grep -qiE "OBJ_TREND"` | PASS |
| SM_Alerting+TL slope formula | `grep -qiE "slope"` | PASS |
| SM_Alerting+TL filename uses +TL | `test -f "SM_Alerting+TL.md"` | PASS |
| SM_NewHUD line count ≥ 250 | `wc -l` = 428 | PASS |
| SM_NewHUD MMM Book p.53 reference | `grep -qiE "Scanning"` | PASS |
| SM_NewHUD Market Maker Cycle | `grep -qi "Market Maker Cycle"` | PASS |
| SM_BPCT unchanged | `git diff HEAD -- SM_BPCT.md` | PASS (untouched) |

---

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | SM_TDI.md reconstruction-grade spec | `a55857e` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md` |
| 2 | SM_PivotPoints.md reconstruction-grade spec | `83500bb` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md` |
| 3 | SM_AlertZone_1.md reconstruction-grade spec | `3e25634` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md` |
| 4 | SM_AlertZone_2.md reconstruction-grade spec | `3911fb2` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md` |
| 5 | SM_Alerting+TL.md reconstruction-grade spec | `279b3f3` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md` |
| 6 | SM_NewHUD.md reconstruction-grade spec | `5735229` | `resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md` |

---

## Known Stubs

None — all six specs contain substantive content. No placeholder text ("TBD", "TODO") appears in any spec. The extensive use of `[INFER]` and `[INFER:guess]` tags is by design (source binaries are non-decompilable), not stubs. Every tagged claim has a corresponding entry in the spec's Uncertainty log with a specific reason for the inference.

---

## Self-Check

### Files exist:

- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md` — FOUND (343 lines)
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md` — FOUND (315 lines)
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md` — FOUND (241 lines)
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md` — FOUND (245 lines)
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md` — FOUND (288 lines) with +TL preserved
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md` — FOUND (428 lines ≥ 250 target)

### Commits exist:

- [x] `a55857e` — feat(11-03): write SM_TDI.md reconstruction-grade spec (Task 1)
- [x] `83500bb` — feat(11-03): write SM_PivotPoints.md reconstruction-grade spec (Task 2)
- [x] `3e25634` — feat(11-03): write SM_AlertZone_1.md reconstruction-grade spec (Task 3)
- [x] `3911fb2` — feat(11-03): write SM_AlertZone_2.md reconstruction-grade spec (Task 4)
- [x] `279b3f3` — feat(11-03): write SM_Alerting+TL.md reconstruction-grade spec (Task 5)
- [x] `5735229` — feat(11-03): write SM_NewHUD.md reconstruction-grade spec (Task 6)

### Automated verify blocks:

- [x] `check_spec.sh SM_TDI.md` — PASS
- [x] `check_spec.sh SM_PivotPoints.md` — PASS
- [x] `check_spec.sh SM_AlertZone_1.md` — PASS
- [x] `check_spec.sh SM_AlertZone_2.md` — PASS
- [x] `check_spec.sh SM_Alerting+TL.md` — PASS
- [x] `check_spec.sh SM_NewHUD.md` — PASS
- [x] `check_all.sh` — 14/14 specs pass; INDEX.md intentionally absent (Plan 04)
- [x] SM_TDI RSI period 13 grep — PASS
- [x] SM_TDI levels 32/50/68 grep — PASS
- [x] SM_PivotPoints M1-M4 grep — PASS
- [x] SM_PivotPoints MMM Book pp.42-43 grep — PASS
- [x] SM_NewHUD line count ≥ 250 — PASS (428 lines)
- [x] SM_NewHUD Scanning View reference — PASS
- [x] SM_NewHUD Market Maker Cycle reference — PASS
- [x] All 6 specs declare correct Confidence level — PASS
- [x] SM_Alerting+TL.md preserves +TL in filename — PASS

## Self-Check: PASSED

---

## Tier 2 Review Status

**AWAITING USER REVIEW** — per 11-VALIDATION.md Manual-Only Verifications and 11-03-PLAN.md `<verification>` section: "HALT for Tier 2 user review." Plan 04 (INDEX.md) does NOT start until the user reads all 6 Tier 2 specs and approves.

**Priority review focus per VALIDATION.md §4.2:**
1. **SM_TDI.md** — cross-check the TDI spot-check rubric table above against the MMM TDI Tradestation PDF (all 10 rows should match the PDF)
2. **SM_NewHUD.md** — assess whether the 10-section field list is a plausible reconstruction of what a 100KB MMM HUD would display; note any obviously-wrong or obviously-missing fields
3. **SM_AlertZone_1 vs SM_AlertZone_2** — assess whether the 148-byte same-algorithm hypothesis is plausible; assess whether the lower-zone / upper-zone interpretation is reasonable
4. **SM_PivotPoints.md** — verify M1-M4 formulas match MMM Book pp.42-43 M1/M2/M3/M4 definitions
5. **SM_Alerting+TL.md** — assess whether the OBJ_TREND slope-projection approach is the correct algorithm for a trendline-touch alerter

**Operator follow-up opportunities:** The 6 items listed in "Operator Follow-Up Items" above can be resolved immediately by anyone with MT4 access to the SM indicator suite. None of them block Plan 04 (INDEX.md), but the resolutions should be incorporated into the specs before they are used as a reconstruction basis.
