---
phase: 11-sm-indicators-full-spec-documentation
plan: "04"
subsystem: documentation
tags: [documentation, MT4, MQL4, SM-indicators, MMM, INDEX, cross-reference, dependency-graph, glossary]

dependency_graph:
  requires:
    - "11-00 (check_index.sh + check_all.sh + check_spec.sh scripts)"
    - "11-01 (Tier 0 helper specs: sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt)"
    - "11-02 (Tier 1 atomic specs: SM_ADR_Marker, SM_Daily_HiLo, SM_BPCT, SM_IlsleyPsychLevels, SM_Crossover_Arrows)"
    - "11-03 (Tier 2 composite specs: SM_TDI, SM_PivotPoints, SM_AlertZone_1/2, SM_Alerting+TL, SM_NewHUD)"
  provides:
    - "INDEX.md: Phase 11 docs entry point — overview, ASCII dep graph, all 14 spec links, MMM glossary cross-refs, 18-term glossary hooks, confidence summary, 8-item MT4 operator verification list"
  affects:
    - "Phase 9 (Strategy Router): SM indicator specs are the reference for MMM-based signal integration into Helix backtest"
    - "Future spec revision phase: 8 open questions documented for MT4 operator follow-up session"

tech-stack:
  added: []
  patterns:
    - "ASCII dependency graph (Tier 0/1/2 with confirmed and [INFER] edges) — NOT mermaid, per CONTEXT.md Claude's Discretion"
    - "Spec catalog as markdown table: 14 rows, relative-path links, Confidence column consistent with each spec's Header declaration"
    - "Glossary hooks table: MMM terms → implementing indicators, bridging from MMM theory to SM toolset"
    - "Audience-segmented How to use section: implementer / trader / MT4 operator paths"

key-files:
  created:
    - "resource_pack/MMM/SM Indicators/docs/INDEX.md"
  modified: []

key-decisions:
  - "ASCII dependency graph chosen over mermaid per CONTEXT.md Claude's Discretion for plain-viewer portability"
  - "SM_NewHUD dep graph node shows iCustom vs internal computation as [INFER] — the 100KB size is consistent with self-contained computation but cannot be confirmed without MT4 decompile access"
  - "sm_WorkTime_no_autogmt explicitly annotated in dep graph as having NO sm_gmtoffset dep — this is the key architectural distinction between the two WorkTime variants"
  - "SM_ADR_Marker and SM_Daily_HiLo D1-boundary dep on sm_gmtoffset marked as optional [INFER] — no mandatory dependency; both can function using the platform's built-in D1 bar boundary"
  - "check_all.sh dep-graph warnings (2) are pre-existing from Plan 01 — false positives from sm_gmtoffset.md and sm_WorkTime_no_autogmt.md mentioning sm_WorkTime in comparison context, not as a runtime dependency; not introduced by Plan 04"

requirements-completed: []

duration: "~3 min"
cost: "-"
completed: 2026-04-27
---

# Phase 11 Plan 04: INDEX.md Cross-Reference Document — Summary

**INDEX.md written as the Phase 11 docs entry point: ASCII dependency graph, 14 spec links, 9 MMM source doc references, 18 glossary-term-to-indicator mappings, 4-High/8-Medium/2-Low confidence summary, and 8-item MT4 operator verification list — check_index.sh PASS, all 15 files present.**

---

## Performance

- **Duration:** ~3 min
- **API Cost:** -
- **Started:** 2026-04-27T03:55:49Z
- **Completed:** 2026-04-27T03:59:37Z
- **Tasks:** 1 of 1
- **Files created:** 1

---

## Accomplishments

- Wrote `resource_pack/MMM/SM Indicators/docs/INDEX.md` (209 lines): the cross-reference entry point for the 15-file SM Indicators doc set. Sections written in plan-specified order: Title/intro → Overview → How to use → Dependency graph (ASCII) → Specs catalog table → MMM glossary cross-references → Confidence summary → Open questions for MT4 operator → Phase metadata footer.

- **ASCII dependency graph** (59 lines including notes) renders the full Tier 0/1/2 architecture with confirmed and `[INFER]` edges. Correctly reflects the canonical RESEARCH.md §4.3 graph: sm_gmtoffset as bottom-of-stack; sm_WorkTime depending on it; sm_WorkTime_no_autogmt explicitly having NO dep; SM_TDI/AlertZone/Alerting+TL self-contained; SM_PivotPoints and SM_NewHUD with optional sm_gmtoffset dep.

- **Spec catalog table**: 14 rows linking all specs via `./helpers/` and `./indicators/` relative paths. Confidence column verified against each spec's actual Header declaration (all 14 match). Source binary filenames included for direct cross-reference to the MT4 binary folder.

- **MMM source documents section**: 9 docs linked with relative paths from INDEX.md to `../../docs/` — covers the MMM Book, both TDI PDFs, Glossary Enhanced, Knowledge Base, Anatomy of Stop Hunts, Market Maker Cycle, and MMM FX MINDSHIFT.

- **Glossary hooks table**: 18 MMM terms (ADR, HOD/LOD, I-HOD/I-LOD, Time Mapping, Gap Time, Strike Zone, Stop Hunt, Pivot Phases M1-M4, TDI, Shark Fin, Blood in the Water, VB Squeeze, TDI Hook, 3-Day Cycle, Psychological Levels, EMA 5/13, Market Maker Spread, Peak Formation) each mapped to implementing indicator(s) with relative links.

- **Confidence summary**: High (4) / Medium (8) / Low (2) breakdown with detailed rationale per group and a count table.

- **Open questions**: 8 operator verification items documented with precise action steps (BPCT abbreviation, TDI StdDev, AlertZone distinction, NewHUD field set, NewHUD data source test, session minute offsets, sm_gmtoffset publication mechanism, default colors/object prefixes).

---

## Verification Results

### check_index.sh

```
PASS: INDEX
```

### check_all.sh

```
Files expected: 15
Files present:  15
Files passing:  14
INDEX status:   PASS
Dep-graph warnings: 2
```

Exit code: 1 (due to 2 pre-existing dep-graph warnings from Plan 01 — see Deviations section below)

### check_index.sh acceptance criteria

| Check | Result |
|-------|--------|
| `## Overview` heading present | PASS |
| ASCII dep graph fenced block present within 100 lines of "Dependency" heading | PASS |
| All 14 spec filenames present in INDEX.md | PASS (33 relative-path links total) |
| MMM glossary cross-ref present (`resource_pack/MMM/docs/` referenced) | PASS |
| `mermaid` keyword count | 0 (PASS) |

### Additional spot checks

| Assertion | Result |
|-----------|--------|
| 15 .md files present in docs/ | PASS (wc -l = 15) |
| Relative links count ≥ 14 | PASS (33 links) |
| SM_TDI RSI period 13 in spec | PASS |
| SM_BPCT [INFER:guess] count ≥ 5 | PASS (41) |
| SM_ADR_Marker references ADR_Levels | PASS |
| All 14 Confidence columns match spec Header | PASS (all 14) |
| No `mermaid` in INDEX.md | PASS (count = 0) |

### Per-spec confidence consistency

All 14 confirmed OK (INDEX confidence column matches each spec's `Confidence:` Header declaration):
- sm_gmtoffset: Medium ✓
- sm_WorkTime: Medium ✓
- sm_WorkTime_no_autogmt: Medium ✓
- SM_ADR_Marker: High ✓
- SM_Daily_HiLo: High ✓
- SM_BPCT: Low ✓
- SM_IlsleyPsychLevels: Medium ✓
- SM_Crossover_Arrows: Medium ✓
- SM_TDI: High ✓
- SM_PivotPoints: High ✓
- SM_AlertZone_1: Medium ✓
- SM_AlertZone_2: Medium ✓
- SM_Alerting+TL: Medium ✓
- SM_NewHUD: Low ✓

---

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | INDEX.md cross-reference entry point | `6edfd83` | `resource_pack/MMM/SM Indicators/docs/INDEX.md` |

---

## Deviations from Plan

### Pre-existing dep-graph warnings (not introduced by Plan 04)

**[Not a Plan 04 deviation — documented for completeness]**

`check_all.sh` exits 1 due to 2 dep-graph warnings inherited from Plan 01:
- `sm_gmtoffset.md` mentions `sm_WorkTime` in its body (explaining that sm_WorkTime consumes sm_gmtoffset) but sm_WorkTime is not listed in sm_gmtoffset's Dependencies section — correctly so, because sm_gmtoffset does NOT depend on sm_WorkTime; the dependency runs the other direction.
- `sm_WorkTime_no_autogmt.md` mentions `sm_WorkTime` throughout (it's the variant it compares against) but sm_WorkTime is not a runtime dependency.

These are false positives in the dep-graph checker (check_all.sh §Step 4): the script checks if a helper token appears in the spec body without also appearing in the Dependencies section, regardless of direction. Both cases are correctly written specs; the checker's heuristic doesn't distinguish "A mentions B because A explains B's dependency on A" from "A depends on B."

This was noted in 11-03-SUMMARY.md: "The pre-existing check_all.sh warnings (2 dependency-graph warnings about sm_gmtoffset.md and sm_WorkTime_no_autogmt.md) are from Plan 01 — not introduced by this plan." Per the phase notes in the execution context: "dep-graph warnings ≤ 5 (some warnings are acceptable per Plan 01 precedent)."

**No Plan 04 deviations.** INDEX.md was written exactly as specified in the plan's task action section.

---

## 7 Must-Haves Verified

| Must-Have | Status |
|-----------|--------|
| 1. 15 markdown files exist at locked paths | PASS (15 files present) |
| 2. Each of 14 specs passes check_spec.sh | PASS (14/14) |
| 3. INDEX.md exists with overview + dep graph + 14 spec links + MMM glossary cross-refs | PASS (check_index.sh PASS) |
| 4. Per-tier human review approved (Tier 0, 1, 2 user-approved per prior plans) | AWAITING FINAL INDEX REVIEW |
| 5. SM_TDI contains RSI period 13 + levels 32/50/68 | PASS |
| 6. SM_BPCT has ≥ 5 [INFER:guess] tags | PASS (41 tags) |
| 7. SM_ADR_Marker references ADR_Levels.mq5 in Port notes (MQ5) | PASS |

---

## Followups for Future MT4 Operator

These 8 items are carried forward as candidate verifications after an operator runs the SM indicators in a live MT4 terminal. None are phase blockers:

1. **SM_BPCT abbreviation:** Read MT4 Inputs tab → pick from 3 candidates or document actual name → full spec rewrite
2. **SM_TDI StdDev multiplier:** Read MT4 Inputs tab → confirm 1.6185 vs 2.0
3. **SM_AlertZone_1 vs SM_AlertZone_2:** Load both → compare Inputs tabs → document exact distinction
4. **SM_NewHUD field set:** Screenshot HUD at session boundary + midpoint → compare against 10-section spec list
5. **SM_NewHUD data source:** Remove SM_TDI while NewHUD is running → observe TDI field in HUD (blank = iCustom; continues = internal)
6. **sm_WorkTime session minute offsets:** Confirm whether inputs accept fractional hours or integer only
7. **sm_gmtoffset publication mechanism:** Confirm GlobalVariable name and mechanism
8. **Default colors / object prefixes:** Capture from MT4 Inputs tabs for any indicator

---

## Known Stubs

None. INDEX.md is complete and substantive. No placeholder text ("TBD", "TODO") used. Every section specified in the plan was written.

---

## Self-Check

### Files exist:

```bash
[ -f "/home/user/Desktop/BA.ORG/Bandd-Analytics/helix/resource_pack/MMM/SM Indicators/docs/INDEX.md" ] && echo "FOUND" || echo "MISSING"
```
Result: FOUND

### Commit exists:

```bash
git log --oneline --all | grep -q "6edfd83" && echo "FOUND" || echo "MISSING"
```
Result: FOUND — `6edfd83 feat(11-04): write INDEX.md cross-reference entry point for SM Indicators docs`

### Script results:

- [x] `check_index.sh INDEX.md` — PASS (exit 0)
- [x] `check_all.sh` — Files present: 15, Files passing: 14, INDEX status: PASS, Dep-graph warnings: 2 (pre-existing from Plan 01, not introduced by Plan 04)
- [x] 15 .md files in docs/ — PASS
- [x] All 14 Confidence columns consistent with spec Headers — PASS (all 14 OK)
- [x] No `mermaid` keyword in INDEX.md — PASS (count = 0)
- [x] `resource_pack/MMM/docs/` referenced in INDEX.md — PASS
- [x] SM_TDI RSI period 13 — PASS
- [x] SM_BPCT [INFER:guess] ≥ 5 — PASS (41)
- [x] SM_ADR_Marker references ADR_Levels — PASS

## Self-Check: PASSED

---

## Phase 11 Readiness

**Phase 11 is content-complete.** All 15 markdown files are written and passing their automated checks:
- 3 Tier 0 helper specs (Plans 01) — user-approved
- 5 Tier 1 atomic specs (Plan 02) — user-approved
- 6 Tier 2 composite specs (Plan 03) — user-approved
- 1 INDEX.md (Plan 04) — **AWAITING FINAL USER REVIEW**

**Phase 11 ready for final user review of INDEX.md and `/gsd:verify-work 11`.**

The orchestrator should run `/gsd:verify-work 11` after the user reviews INDEX.md and approves.
