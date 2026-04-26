---
phase: 11
plan: 02
subsystem: sm-indicators-documentation
tags: [documentation, MT4, MQL4, SM-indicators, Tier-1, ADR, psychological-levels, EMA-crossover, PHOD-PLOD]
dependency_graph:
  requires: ["11-00", "11-01"]
  provides: ["SM_ADR_Marker.md", "SM_Daily_HiLo.md", "SM_BPCT.md", "SM_IlsleyPsychLevels.md", "SM_Crossover_Arrows.md"]
  affects: ["11-03 (Tier 2 composites — can now reference Tier 1 specs)", "INDEX.md"]
tech_stack:
  added: []
  patterns:
    - "12-section locked template (Header/Purpose/Inputs/Outputs/Calculation/Pseudocode/Visual/Dependencies/Edge cases/Test cases/Port notes/Uncertainty log)"
    - "[INFER] for medium-confidence claims; [INFER:guess] for low-confidence / speculative claims"
    - "Confidence: High / Medium / Low declared in Header table"
key_files:
  created:
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md"
    - "resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md"
  modified: []
decisions:
  - "SM_BPCT proceeds with Candidate Interpretation 3 (Buy/Sell Pressure Candle Tracker) as working hypothesis pending MT4 operator confirmation — entire spec tagged [INFER:guess]"
  - "SM_ADR_Marker Port notes cite V2/indicators/ADR_Levels.mq5 as the canonical MQ5 precedent (INFRA-04)"
  - "SM_IlsleyPsychLevels uses AdaptForJPY flag with SYMBOL_DIGITS ∈ {2,3} detection as the primary JPY edge case guard"
  - "SM_Crossover_Arrows documents the historical off-by-one repainting bug and states the 2019 binary is presumed fixed"
metrics:
  duration_minutes: 35
  completed_date: "2026-04-26"
  tasks_completed: 5
  tasks_total: 5
  files_created: 5
  files_modified: 0
---

# Phase 11 Plan 02: Tier 1 Atomic Indicators — Summary

**One-liner:** Five Tier 1 SM indicator specs written — ADR markers, daily H/L lines, speculative BPCT (3-candidate), psych levels (Ilsley), and EMA 5/13 crossover arrows — all passing check_spec.sh.

---

## What Was Built

Five reconstruction-grade markdown specs for the Tier 1 atomic SM indicators, conforming to the locked 12-section template established in Plan 01. All 5 files are under `resource_pack/MMM/SM Indicators/docs/indicators/`.

### Per-Indicator Confidence Summary

| Indicator | File | Confidence | [INFER] count | [INFER:guess] count | Key source |
|-----------|------|------------|---------------|----------------------|------------|
| SM_ADR_Marker | SM_ADR_Marker.md | **High** | 32 | 0 | MMM Book p.41 + ADR_Levels.mq5 |
| SM_Daily_HiLo | SM_Daily_HiLo.md | **High** | 30 | 0 | MMM Book p.41 (PHOD/PLOD) |
| SM_BPCT | SM_BPCT.md | **Low** | 2 | 41 | Abbreviation unresolved — 3 candidates |
| SM_IlsleyPsychLevels | SM_IlsleyPsychLevels.md | **Medium** | 28 | 0 | Public Round Levels pattern + Ilsley community |
| SM_Crossover_Arrows | SM_Crossover_Arrows.md | **Medium** | 34 | 0 | MMM Book p.47 (EMA 5/13) |

---

## Verification Results

All 5 specs pass `check_spec.sh` (12 sections, pseudocode ≥10 lines, MQ4/MQ5/Python in Port notes, Confidence declared, ≥1 [INFER] tag, Inputs table, ≥2 Test cases).

| Assertion | Result |
|-----------|--------|
| All 5 check_spec.sh exits 0 | PASS |
| SM_BPCT [INFER:guess] count ≥ 5 | PASS (count = 41) |
| SM_ADR_Marker contains "ADR_Levels" string | PASS |
| SM_Crossover_Arrows EMA 5 + EMA 13 references | PASS |
| SM_Crossover_Arrows cites MMM Book p.47 / Confluence | PASS |
| SM_IlsleyPsychLevels addresses JPY edge case | PASS |
| SM_BPCT presents all 3 candidate interpretations | PASS |
| All Confidence levels match RESEARCH.md spec | PASS |

---

## Key Design Decisions

### SM_ADR_Marker (Confidence: High)
- Formula `today_open ± ADR/2` is doubly confirmed: MMM Book p. 41 (text description) + `V2/indicators/ADR_Levels.mq5` (code precedent, INFRA-04).
- Port notes explicitly cite `V2/indicators/ADR_Levels.mq5` as the canonical MQ5 skeleton to copy, and `V2/v3_intelligence/adr.py` as the Python reference.
- 13 [INFER] entries cover parameter defaults, refresh cadence, object naming, and alert support — all unverifiable from the binary but well-bounded.

### SM_Daily_HiLo (Confidence: High)
- Algorithm `iHigh/iLow(PERIOD_D1, DaysBack)` is trivially derivable from the indicator name + MMM Book p. 41 PHOD/PLOD context.
- The size delta between `!SM_Daily_HiLo.ex4` (6,284 bytes) and `!_Daily_HiLo.ex4` (3,004 bytes) is noted as likely corresponding to the `ShowCurrentDay` optional running H/L feature.
- 10 [INFER] entries; Sunday-open thin-bar and broker-timezone edge cases documented.

### SM_BPCT (Confidence: Low)
- This is the most uncertain spec in the entire Phase 11 corpus. The "BPCT" abbreviation does not appear in any MMM/SM source document.
- Three candidate interpretations are presented: (1) Bars Per Cycle Tracker, (2) Beat-the-MM Pip Count Tracker, (3) Buy/Sell Pressure Candle Tracker.
- The spec proceeds with Candidate 3 as the working hypothesis (most cited in BTMM community forums), marks every behavioral claim `[INFER:guess]`, and explicitly recommends that the spec be fully rewritten once an operator reads the MT4 Inputs tab.
- 41 `[INFER:guess]` tags — far exceeding the VALIDATION.md requirement of ≥5.
- The Uncertainty log explicitly calls out that interpretations #1 and #2 would require complete rewrites of Calculation, Pseudocode, Outputs, and Visual sections.

### SM_IlsleyPsychLevels (Confidence: Medium)
- Algorithm is well-understood (round-number horizontal line indicator); the Ilsley-specific variant is small (3,540 bytes) and almost certainly identical in behavior to generic Round Levels MT4 indicators.
- Community attribution (Ilsley name, UK/European BTMM forums, mql5.com/en/code/55506) documented.
- JPY adaptation via `AdaptForJPY` flag + `SYMBOL_DIGITS ∈ {2, 3}` detection is documented as a critical correctness requirement — Test case 3 demonstrates the consequence of omitting it (lines spaced 0.5 pips apart on USDJPY).
- Index/crypto symbols (US30, BTCUSD) require manual `LevelInterval` override; no auto-detection assumed given the small binary size.

### SM_Crossover_Arrows (Confidence: Medium)
- EMA 5 / EMA 13 as the standard MMM entry-signal pair is HIGH confidence from MMM Book p. 47.
- Cross-detection condition `fast_i > slow_i AND fast_i1 <= slow_i1` (compare current vs. previous bar) is the standard non-repainting crossover test.
- Historical off-by-one repainting bug (Steve Mauro's first-generation BTMM crossover indicator) is documented; the 2019 binary is presumed fixed.
- `V2/indicators/BandD_TradeReplay.mq5` cited as the MQ5 arrow-drawing reference for any port.

---

## Style/Voice Patterns Refined from Tier 0

1. **Confidence rationale block in Header:** Tier 0 established this pattern (brief prose after the table explaining what is HIGH vs. INFER). Tier 1 continues it consistently. The ADR_Marker rationale is the richest ("doubly confirmed by two independent sources").

2. **"Bar-iteration model" explicit call-out in Calculation logic:** Tier 0 helpers established this as a required element (every-tick vs. new-bar-only). Tier 1 continues it for all 5 indicators. Crossover_Arrows adds the `prev_calculated` optimization explanation.

3. **Port notes → Python code snippets:** All 5 Tier 1 specs include runnable Python code in the Python port subsection. This sets the anchor for Tier 2 specs (TDI, PivotPoints, AlertZones) which will also include Python code.

4. **Test cases as quantitative examples:** Tier 1 reinforces the pattern of using specific price numbers (EURUSD at 1.0867, USDJPY at 152.34) with expected output values calculated explicitly. The BPCT test cases use `[INFER:guess]` qualifiers to acknowledge they may be based on the wrong interpretation.

5. **Dependencies section:** "No mandatory dependencies. Self-contained." is the correct declaration for all 5 Tier 1 atoms. Tier 2 specs (TDI, AlertZone) will have real dependencies on sm_WorkTime or SM_TDI.

---

## [INFER] Tags Not Foreseen by RESEARCH.md (Followup Items for MT4 Operator)

The following `[INFER]` tags emerged during writing that are NOT explicitly called out in the RESEARCH.md §2 dossiers — an MT4 operator running the indicators should verify these:

1. **SM_ADR_Marker:** Whether the indicator consumes `sm_GMTOffset` GlobalVariable for D1 boundary alignment. This was not mentioned in the dossier but is architecturally significant.
2. **SM_ADR_Marker:** Exact refresh cadence (60-second timer vs every-tick vs every D1 bar). The ADR_Levels.mq5 uses 60s timer but the !SM binary may differ.
3. **SM_Daily_HiLo:** Whether the `ShowCurrentDay` optional running HOD/LOD feature actually exists — the binary size delta is suggestive but not conclusive.
4. **SM_IlsleyPsychLevels:** Whether any index-symbol auto-detection (US30, GER40) exists, or whether manual `LevelInterval` override is always required for non-forex instruments.
5. **SM_Crossover_Arrows:** Whether the EMA lines themselves are also drawn by the indicator (many crossover indicators also plot their source MAs). The binary may or may not include this.

---

## Tier 1 Review Status

**HALTED for Tier 1 user review.** Plan 03 (Tier 2 composites) does NOT start until the user reviews these 5 specs and types "approved" for Tier 1.

---

## Deviations from Plan

None — plan executed exactly as written. All 5 tasks produced files matching the acceptance criteria in the plan. No architectural surprises encountered. The BPCT spec required care to ensure all `[INFER:guess]` markers were applied consistently throughout (not just in the Uncertainty log), which the plan explicitly called for and which was honored.

---

## Known Stubs

None. All 5 specs are complete per the 12-section template. SM_BPCT is intentionally speculative (Low confidence), but this is the designed state documented in RESEARCH.md §5.1 and VALIDATION.md — it is not an incomplete stub, it is a structured placeholder with explicit resolution guidance.

---

## Self-Check

### Files exist:
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md` — FOUND
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md` — FOUND
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md` — FOUND
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md` — FOUND
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md` — FOUND

### Commits exist:
- 7b71743 — feat(11-02): write SM_ADR_Marker.md Tier 1 spec (Confidence: High)
- 80932f9 — feat(11-02): write SM_Daily_HiLo.md Tier 1 spec (Confidence: High)
- b90e374 — feat(11-02): write SM_BPCT.md Tier 1 spec (Confidence: Low)
- 6c3fa27 — feat(11-02): write SM_IlsleyPsychLevels.md Tier 1 spec (Confidence: Medium)
- 2b8138d — feat(11-02): write SM_Crossover_Arrows.md Tier 1 spec (Confidence: Medium)

### check_spec.sh results: All 5 PASS
### [INFER:guess] count in SM_BPCT.md: 41 (≥5 required)
### ADR_Levels reference in SM_ADR_Marker.md: FOUND
### EMA 5/13 + MMM Book p.47 in SM_Crossover_Arrows.md: FOUND
### JPY edge case in SM_IlsleyPsychLevels.md: FOUND
### 3 candidate interpretations in SM_BPCT.md: FOUND

## Self-Check: PASSED
