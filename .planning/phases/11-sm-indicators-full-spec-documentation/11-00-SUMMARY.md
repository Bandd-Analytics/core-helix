---
phase: 11-sm-indicators-full-spec-documentation
plan: "00"
subsystem: infra
tags: [bash, grep, awk, documentation, validation, sm-indicators, mmm]

requires: []
provides:
  - "check_spec.sh: per-spec 12-section conformance audit (8 checks per 11-VALIDATION.md Wave 0 Req #1)"
  - "check_all.sh: full 15-file suite runner with dep-graph cross-check"
  - "check_index.sh: INDEX.md 4-check audit"
  - "resource_pack/MMM/SM Indicators/docs/{helpers,indicators}/ directory tree (with .gitkeep)"
affects:
  - "11-01-PLAN.md (Tier 0 helpers) — each task's <verify> calls check_spec.sh"
  - "11-02-PLAN.md (Tier 1 atomic indicators)"
  - "11-03-PLAN.md (Tier 2 composite indicators)"
  - "11-04-PLAN.md (INDEX.md) — calls check_index.sh and check_all.sh"

tech-stack:
  added: []
  patterns:
    - "bash strict mode (set -euo pipefail) for all audit scripts"
    - "awk-based section extraction (find heading, accumulate until next H2) for section-scoped grep"
    - "15-file manifest array in check_all.sh — drives both existence and per-spec audit loops"

key-files:
  created:
    - ".planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh"
    - ".planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_index.sh"
    - ".planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh"
    - "resource_pack/MMM/SM Indicators/docs/.gitkeep"
    - "resource_pack/MMM/SM Indicators/docs/helpers/.gitkeep"
    - "resource_pack/MMM/SM Indicators/docs/indicators/.gitkeep"
  modified: []

key-decisions:
  - "Port notes awk stops at H2 only (not H3) — Port notes itself has H3 sub-headings (MQ4/MQ5/Python paragraphs); stopping at H3 would exit before capturing those tokens"
  - "Inputs/Test-cases section extraction also stops at H2 only — same reasoning; sections may have H3 sub-structure"
  - "check_all.sh files_passing check uses files_expected-1 (14 specs, not 15) — INDEX.md is audited by check_index.sh separately and not passed through check_spec.sh"
  - "check_all.sh does NOT abort on missing files — prints INFO and continues so it is usable mid-phase before all tiers are complete"

patterns-established:
  - "Section extraction pattern: awk '/heading/ {in_section=1; next} in_section && /^## / {exit} in_section {print}' — use this in Plans 01-04 for any section-scoped grep"
  - "Smoke-test new scripts with /tmp/ fixtures before committing; delete fixtures before commit"

requirements-completed: []

duration: 5min
cost: "-"
completed: 2026-04-26
---

# Phase 11 Plan 00: Validation Infrastructure Summary

**Bash grep-audit scaffold (3 executable scripts + docs/ directory tree) enabling automated conformance gating for all 15 SM indicator specs across Plans 01-04**

## Performance

- **Duration:** ~5 min
- **API Cost:** -
- **Started:** 2026-04-26T15:32:43Z
- **Completed:** 2026-04-26T15:37:14Z
- **Tasks:** 2 of 2
- **Files created:** 6

## Accomplishments

- Created `resource_pack/MMM/SM Indicators/docs/{helpers,indicators}/` directory tree (3 `.gitkeep` files) so Plans 01-03 have a concrete output destination on disk
- Implemented `check_spec.sh` with all 8 conformance checks from 11-VALIDATION.md Wave 0 Requirement #1; smoke-tested: incomplete fake spec → exit 1 (18 issues), complete fake spec → exit 0
- Implemented `check_index.sh` with 4 INDEX.md checks (Overview heading, dep-graph block, 14 spec links, MMM glossary cross-ref)
- Implemented `check_all.sh` suite runner: enumerates all 15 expected files, invokes check_spec.sh per spec, invokes check_index.sh, runs dep-graph cross-check for sm_gmtoffset/sm_WorkTime mention vs Dependencies section; exits 1 with clean summary when no specs present (correct Wave 0 behavior)

## check_spec.sh: 8 Checks Implemented

| # | Check | Key grep/awk term(s) |
|---|-------|----------------------|
| 1 | File exists | `test -f "$1"` |
| 2 | All 12 H2/H3 sections present | `Header`, `Purpose`, `Inputs`, `Outputs`, `Calculation`, `Pseudocode`, `Visual`, `Dependencies`, `Edge cases`, `Test cases`, `Port notes`, `Uncertainty` |
| 3 | Confidence declared in Header | `Confidence: High`, `Confidence: Medium`, `Confidence: Low` |
| 4 | At least one [INFER] tag | `[INFER]` or `[INFER:guess]` |
| 5 | Pseudocode block >= 10 lines | awk finds first fenced block after Pseudocode heading, counts interior lines |
| 6 | Inputs section has markdown table | `\|` line between Inputs heading and next H2 |
| 7 | Test cases >= 2 entries | `^[0-9]+\.` or `^[*-] ` between Test cases heading and next H2 |
| 8 | Port notes mentions MQ4, MQ5, Python | `MQ4`, `MQ5`, `Python` in lines between Port notes heading and next H2 |

**Important design note:** Checks 7 and 8 (Port notes, Inputs, Test cases) stop at the next `## ` (H2) heading, NOT at `### ` (H3). This is deliberate: Port notes itself uses H3 sub-headings (`### MQ4 to MQ5 Deltas`, `### Python Port`, `### Backtester Integration`) and stopping at H3 would exit before capturing those token references.

## check_index.sh: 4 Checks Implemented

| # | Check | Logic |
|---|-------|-------|
| 1 | Overview heading present | grep for `## Overview`, `## Introduction`, or `## How to use this folder` |
| 2 | Dependency graph block | grep for `` ```mermaid `` OR fenced block within 100 lines of graph/Dependency heading |
| 3 | All 14 spec files linked | grep for each of 14 filenames (3 helpers + 11 indicators) in INDEX.md |
| 4 | MMM glossary cross-refs | grep for `resource_pack/MMM/docs/` OR `MMM_Glossary` OR `MMM Book` |

## check_all.sh: 15-File Manifest

```
resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md
resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md
resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md
resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md
resource_pack/MMM/SM Indicators/docs/INDEX.md         ← audited by check_index.sh
```

## Sample Failure Output (smoke test — incomplete fake spec)

```
FAIL: /tmp/fake_spec_incomplete.md (18 issues)
  - MISSING SECTION: Inputs
  - MISSING SECTION: Outputs
  - MISSING SECTION: Calculation
  - MISSING SECTION: Pseudocode
  - MISSING SECTION: Visual
  - MISSING SECTION: Dependencies
  - MISSING SECTION: Edge cases
  - MISSING SECTION: Test cases
  - MISSING SECTION: Port notes
  - MISSING SECTION: Uncertainty
  - MISSING: Confidence declaration (need 'Confidence: High', ...)
  - MISSING: at least one [INFER] tag — every spec has at least one inference
  - PSEUDOCODE TOO SHORT: found 0 lines (need >= 10)
  - MISSING: Inputs section must contain a markdown table
  - INSUFFICIENT TEST CASES: found 0 (need >= 2)
  - PORT NOTES MISSING: MQ4
  - PORT NOTES MISSING: MQ5
  - PORT NOTES MISSING: Python
```

## Task Commits

1. **Task 1: docs/ output tree + check_spec.sh** - `15009c7` (chore)
2. **Task 2: check_index.sh + check_all.sh** - `2ce34f8` (chore)

## Files Created

- `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh` — 8-check per-spec conformance audit
- `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_index.sh` — 4-check INDEX.md audit
- `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh` — 15-file suite runner
- `resource_pack/MMM/SM Indicators/docs/.gitkeep` — root docs dir placeholder
- `resource_pack/MMM/SM Indicators/docs/helpers/.gitkeep` — helpers tier placeholder
- `resource_pack/MMM/SM Indicators/docs/indicators/.gitkeep` — indicators tier placeholder

## Reminder for Plan 01 Executor

Every spec-writing task's `<verify><automated>` block should call:

```bash
bash .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh \
  "resource_pack/MMM/SM Indicators/docs/helpers/<spec_name>.md"
```

After all files in a tier are written, run:

```bash
bash .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh
```

The suite will print how many files are present vs. expected, and list any conformance failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Port notes awk extraction stopped too early at H3 sub-headings**
- **Found during:** Task 1 smoke-test (complete fake spec)
- **Issue:** The original awk for Checks 6, 7, 8 used `^(## |### )` as the section-exit trigger. Because Port notes has H3 sub-headings (`### MQ4 to MQ5 Deltas`, etc.), awk exited immediately after seeing the first H3, before extracting any body text. Same issue for Inputs/Test cases if those sections use H3 subsections.
- **Fix:** Changed exit trigger to `^## ` only (H2 only), allowing H3 sub-headings within the section body to be captured.
- **Files modified:** `scripts/check_spec.sh`
- **Verification:** Complete fake spec with `### MQ4 to MQ5 Deltas` sub-heading now correctly passes Check 8 (exit 0).
- **Committed in:** 15009c7 (Task 1 commit, fix applied before commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug found during smoke test, fixed inline before commit)
**Impact on plan:** Fix essential for correctness. No scope creep.

## Issues Encountered

None — plan executed cleanly after the inline awk fix during smoke-testing.

## Next Phase Readiness

- All 3 audit scripts are callable from project root
- `resource_pack/MMM/SM Indicators/docs/helpers/` and `indicators/` directories exist for Plan 01-03 spec files
- Plans 01-04 can include `bash .planning/phases/11-.../scripts/check_spec.sh "<file>"` directly in their `<verify><automated>` blocks without any further setup

---
*Phase: 11-sm-indicators-full-spec-documentation*
*Completed: 2026-04-26*

## Self-Check

### Files exist:

- [x] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh` — FOUND
- [x] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_index.sh` — FOUND
- [x] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh` — FOUND
- [x] `resource_pack/MMM/SM Indicators/docs/.gitkeep` — FOUND
- [x] `resource_pack/MMM/SM Indicators/docs/helpers/.gitkeep` — FOUND
- [x] `resource_pack/MMM/SM Indicators/docs/indicators/.gitkeep` — FOUND

### Commits exist:

- [x] `15009c7` — chore(11-00): create docs/ output tree + check_spec.sh per-spec audit
- [x] `2ce34f8` — chore(11-00): add check_index.sh + check_all.sh suite runner

### Automated verify block from plan:

- [x] `test -x check_spec.sh` — PASS
- [x] `test -d docs/helpers` — PASS
- [x] `test -d docs/indicators` — PASS
- [x] `bash -n check_spec.sh` — PASS
- [x] `test -x check_index.sh` — PASS
- [x] `test -x check_all.sh` — PASS
- [x] `bash -n check_index.sh` — PASS
- [x] `bash -n check_all.sh` — PASS
- [x] `bash check_all.sh` exits 1 with "Files present: 0" — PASS (correct failure on missing files)

## Self-Check: PASSED
