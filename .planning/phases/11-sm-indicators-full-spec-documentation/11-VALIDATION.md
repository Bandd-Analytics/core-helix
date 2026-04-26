---
phase: 11
slug: sm-indicators-full-spec-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **This is a documentation phase.** "Tests" are markdown-conformance checks, grep-based audits, and structured human review — not pytest/jest. Each finished spec is the unit under validation. The `## Validation Architecture` section in 11-RESEARCH.md (sections 4.1–4.5) is the source of truth for the audit rubrics referenced here.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash + grep + manual review (no test framework) |
| **Config file** | none — checks are inline shell commands |
| **Quick run command** | `bash .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh <spec_file>` (created in Wave 0) |
| **Full suite command** | `bash .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh` |
| **Estimated runtime** | ~3 seconds (grep over 15 markdown files) |

---

## Sampling Rate

- **After every task commit (one spec written):** Run `check_spec.sh <spec_file>` — verifies the 12 required sections + at least one `[INFER]` or `High` confidence marker + valid cross-references
- **After every plan wave (one tier complete):** Run `check_all.sh` — full audit across all completed specs + dependency graph cross-check + tier-completeness verification
- **Before `/gsd:verify-work`:** All 15 files exist, full suite green, human review accepted per tier
- **Max feedback latency:** ~3 seconds (grep is fast)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-00-01 | 00 | 0 | infra | wave-0 | `test -f .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh && test -x .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh` | ❌ W0 | ⬜ pending |
| 11-00-02 | 00 | 0 | infra | wave-0 | `test -f .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh && test -x .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh` | ❌ W0 | ⬜ pending |
| 11-01-01 | 01 | 1 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md"` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md"` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md"` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md"` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 2 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md"` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 2 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md"` | ❌ W0 | ⬜ pending |
| 11-02-04 | 02 | 2 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md"` | ❌ W0 | ⬜ pending |
| 11-02-05 | 02 | 2 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md"` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md"` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md"` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md"` | ❌ W0 | ⬜ pending |
| 11-03-04 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md"` | ❌ W0 | ⬜ pending |
| 11-03-05 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md"` | ❌ W0 | ⬜ pending |
| 11-03-06 | 03 | 3 | doc | spec-conformance | `bash .../scripts/check_spec.sh "resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md"` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 4 | doc | index-cross-ref | `bash .../scripts/check_index.sh "resource_pack/MMM/SM Indicators/docs/INDEX.md"` | ❌ W0 | ⬜ pending |
| 11-04-02 | 04 | 4 | doc | dep-graph | `bash .../scripts/check_all.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note on plan numbering:** Plan 00 is Wave 0 (validation infra). Plans 01–04 are content plans (one per tier + INDEX). Final task IDs are assigned by the planner; the planner MAY adjust above mapping but must preserve the wave/tier structure.

---

## Wave 0 Requirements

- [ ] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_spec.sh` — per-spec conformance audit. Verifies:
  1. Frontmatter or H1 with indicator name
  2. All 12 required H2/H3 sections present (Header, Purpose, Inputs, Outputs, Calculation logic, Pseudocode, Visual elements, Dependencies, Edge cases, Test cases, Port notes, Uncertainty log)
  3. Confidence indicator declared in Header (one of: `Confidence: High`, `Confidence: Medium`, `Confidence: Low`)
  4. At least 1 `[INFER]` tag in Uncertainty log (every spec has at least one inference, given source binaries are not decompilable)
  5. Pseudocode block present (fenced code block ≥ 10 lines)
  6. Inputs section contains a markdown table
  7. At least 2 entries in "Test cases" section (numbered or bulleted)
  8. "Port notes" section explicitly mentions MQ4, MQ5, and Python (grep all three terms)

- [ ] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh` — full-suite audit. Wraps check_spec.sh over all 14 spec files + index audit + dependency-graph cross-check. Verifies:
  1. All 15 files exist at expected paths
  2. Each spec passes check_spec.sh
  3. INDEX.md exists and lists all 14 indicators in its dependency graph
  4. No spec's "Dependencies" section references a helper file that doesn't exist
  5. Tier 2 specs that mention `sm_gmtoffset` or `sm_WorkTime` have those listed in their Dependencies section (cross-check between body text and Dependencies subsection)

- [ ] `.planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_index.sh` — INDEX.md audit. Verifies:
  1. INDEX.md contains an "## Overview" or equivalent intro section
  2. INDEX.md contains a dependency graph (ASCII or mermaid block)
  3. INDEX.md links to all 14 spec files via relative paths
  4. INDEX.md lists or links to MMM glossary docs in `resource_pack/MMM/docs/`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tier 0 review | doc | Subjective accuracy of helper semantics — is the gmtoffset auto-detect logic plausible? | After Tier 0 plan completes: user reads all 3 helper specs and confirms each is reconstruction-grade (could a future implementer build it from this?). User responds "approved" or describes issues. |
| Tier 1 review | doc | Subjective: are the 5 atomic indicator specs accurate enough that a future MQ5/Python port would behave like the original? | After Tier 1 plan completes: same protocol — user reads 5 specs, approves or describes issues. |
| Tier 2 review | doc | TDI spec accuracy against MMM TDI Tradestation PDF; NewHUD plausibility | After Tier 2 plan completes: user reads 6 specs, with extra attention to TDI (cross-check against MMM TDI PDF parameters per Validation Architecture §4.2) and NewHUD (the longest, most-inferred spec). |
| INDEX review | doc | Dependency graph accuracy + glossary cross-refs | After Plan 04: user reads INDEX.md, confirms graph matches actual dependencies declared in the 14 specs. |
| BPCT confidence flag | doc | BPCT abbreviation is unresolved per RESEARCH §5.1 — every claim must be `[INFER:guess]`-tagged | grep `[INFER:guess]` SM_BPCT.md && expect ≥ 5 occurrences (entire spec is speculation) |

---

## Validation Sign-Off

- [ ] All tasks have automated grep-conformance check OR Wave 0 dependency
- [ ] Sampling continuity: every spec gets check_spec.sh run after its commit (no 3 consecutive specs without automated verify)
- [ ] Wave 0 ships 3 audit scripts (check_spec.sh, check_all.sh, check_index.sh) before Tier 0 starts
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s (grep is fast; full audit covers all 15 files in seconds)
- [ ] `nyquist_compliant: true` set in frontmatter once all 4 plans pass and all 4 manual reviews are "approved"

**Approval:** pending
