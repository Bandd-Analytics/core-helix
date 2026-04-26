---
phase: 11-sm-indicators-full-spec-documentation
plan: "01"
subsystem: documentation
tags: [mql4, mmm, sm-indicators, session-helpers, gmt-offset, spec-writing, tier-0]

requires:
  - "11-00 (check_spec.sh + docs/ directory tree)"

provides:
  - "sm_gmtoffset.md: reconstruction-grade spec for the GMT-offset utility used by all session-aware indicators"
  - "sm_WorkTime.md: spec for the auto-GMT session-window box overlay (Asia/London/US)"
  - "sm_WorkTime_no_autogmt.md: manual-GMT variant — same as sm_WorkTime but with manual BrokerGMT input"

affects:
  - "11-02-PLAN.md (Tier 1 atomic indicators): sm_WorkTime.md and sm_gmtoffset.md are now citable as dependency targets in Section 8 of Tier 1 specs"

tech-stack:
  added: []
  patterns:
    - "12-section markdown spec template (Header / Purpose / Inputs table / Outputs 3-subsection / Calculation / Pseudocode / Visual / Dependencies / Edge cases / Test cases / Port notes / Uncertainty log)"
    - "Confidence tagging: untagged = High, [INFER] = Medium, [INFER:guess] = Low"
    - "Language-neutral imperative pseudocode style (not MQL or Python syntax)"
    - "Port notes as three distinct H3 sub-sections: MQ4 to MQ5 deltas / Python port / Backtester integration"
    - "Uncertainty log as bulleted list with [INFER] claim — reason format, one bullet per inference"

key-files:
  created:
    - "resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md"
    - "resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md"
    - "resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md"
  modified: []

key-decisions:
  - "Integer-only GMT offset model documented as known limitation — half-hour offsets (India IST UTC+5:30, Iran IRST UTC+3:30) unsupported; most Forex brokers run on whole-hour offsets so this is acceptable"
  - "Dependencies section for sm_WorkTime_no_autogmt reads 'None — this variant has no dependency on sm_gmtoffset by design' (sm_gmtoffset named in the None declaration, not as a runtime dep)"
  - "Session minute offsets (00:30 / 07:30 / 13:30) documented as [INFER] — the integer-hour input parameters may or may not capture the 30-min precision; this is a residual gap for Tier 1 review to flag"
  - "sm_WorkTime_no_autogmt BrokerDSTAdjust default = false — older 2011-era indicators typically expected manual adjustment; [INFER] but consistent with the binary predating sm_WorkTime"
  - "Backtester integration note is consistent across all 3 specs: sm_gmtoffset is a no-op in backtest (UTC timestamps already); sm_WorkTime / sm_WorkTime_no_autogmt are purely visual but their session-boundary constants feed temporal_filters.py"

requirements-completed: []

duration: "~6 min"
cost: "-"
completed: 2026-04-26
---

# Phase 11 Plan 01: Tier 0 Helper Specs Summary

**Three reconstruction-grade markdown specs for the Tier 0 SM helper indicators (sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt), each passing check_spec.sh and declaring Confidence: Medium**

---

## Performance

- **Duration:** ~6 min
- **API Cost:** -
- **Started:** 2026-04-26T15:57:11Z
- **Completed:** 2026-04-26T16:03:27Z
- **Tasks:** 3 of 3
- **Files created:** 3 spec files

---

## Accomplishments

- Wrote `sm_gmtoffset.md` (192 lines): 12-section spec for the GMT-offset detection utility. Purpose cites MMM Glossary "Time Mapping" + MMM Book p. 8 session times. Inputs table with 4 parameters (all [INFER]: AutoDetect / ManualGMT / DSTAdjust / GlobalVarName). Calculation logic covers TimeCurrent()-TimeGMT() delta approach + DST heuristic + hourly refresh. 12 [INFER] bullets in Uncertainty log. Backtester note: no-op in UTC-timestamped backtest mode.

- Wrote `sm_WorkTime.md` (247 lines): 12-section spec for the auto-GMT session-window box overlay. Purpose cites MMM Book p. 8 (three session times) and directly quotes MMM Book p. 40 ("Colour-Coded Sessions" — two boxes, NY-reversal 3h sub-box). Inputs table with 16 parameters. Dependencies section explicitly names sm_gmtoffset with GlobalVariable link. 50-line pseudocode. 12 [INFER] bullets (≥ 8 required). 3 test cases demonstrate winter/summer parity and why UseGMTOffset=false is dangerous.

- Wrote `sm_WorkTime_no_autogmt.md` (244 lines): 12-section spec for the manual-GMT variant. Notes Sep 2011 binary predates Dec 2011 sm_WorkTime (original manual version → auto-detect added). Dependencies section: "None — this variant has no dependency on sm_gmtoffset by design." BrokerGMT (int, default 2) and BrokerDSTAdjust (bool, default false) replace UseGMTOffset. 48-line pseudocode (on_init replaces GlobalVar read with direct parameter read; on_new_bar identical to sm_WorkTime). 10 [INFER] bullets.

---

## Confidence breakdown written into each spec

| Spec | Overall Confidence | High-confidence claims | Medium/[INFER] claims |
|------|-------------------|----------------------|----------------------|
| sm_gmtoffset.md | Medium | Function purpose (MMM Glossary "Time Mapping"); detection approach via TimeCurrent()-TimeGMT() (MQL5 forum confirmed) | All parameter names; GlobalVariable as publication mechanism; refresh cadence; Comment() visual |
| sm_WorkTime.md | Medium | Session times 00:30/07:30/13:30 GMT (MMM Book p. 8); NY-reversal box ~3h (MMM Book p. 40); 43KB consistent with substantial drawing code | All parameter names and defaults; color values; ObjectPrefix; refresh model; NY-reversal exact time span |
| sm_WorkTime_no_autogmt.md | Medium | Functional identity to sm_WorkTime minus auto-GMT (encoded in filename + 5,656-byte size delta); Sep 2011 predates Dec 2011 | BrokerGMT default; BrokerDSTAdjust default; algorithmic equivalence to sm_WorkTime (cannot verify without decompilation) |

---

## Style and voice patterns established for Tier 1

These patterns were established in Plan 01 and serve as the style anchor for Plans 02 and 03:

1. **Header table format:** `| Field | Value |` two-column table with Name / Source filename / Source platform / Source binary size / Binary date / Tier / Confidence. Follow with a "Confidence rationale" paragraph explaining the high vs [INFER] split.

2. **Purpose depth:** 1–2 paragraphs. First paragraph: what the indicator does in plain English. Second (if applicable): direct MMM Book quote with page citation. All three Tier 0 specs include at least one direct MMM Book citation.

3. **Inputs table column order:** `Parameter | Type | Default | Valid range | Meaning | Confidence`. Confidence column contains either bare "High" text (citing source) or `[INFER]` / `[INFER:guess]`. Do not put the full `[INFER]` explanation in the table — save that for the Uncertainty log.

4. **Outputs three-subsection pattern:** Always write all three subsections (Indicator buffers / Chart objects / Alerts) even when the content is "None". Many specs will have mostly "None" entries; that is correct and expected.

5. **Calculation logic numbered steps:** Step 1 is always "OnInit — [what happens at load]". Last step is always "Bar-iteration model — [every tick? new bar? timer?]" followed by "OnDeinit — [cleanup]". This ordering makes it easy to compare across specs.

6. **Pseudocode style:** Language-neutral imperative with `function` declarations, no MQL/Python syntax. Use `CONST`, `GLOBAL`, and plain `=` assignment. Comments with `#`. Target 30–50 lines for drawing indicators, 20–30 for utility indicators.

7. **Port notes three H3 sub-headings:** Always `### MQ4 to MQ5 deltas` / `### Python port` / `### Backtester integration`. Backtester note should always say "purely visual / no backtester role" for drawing indicators, or "factored session-classification function feeds temporal_filters.py" where applicable.

8. **Uncertainty log format:** `- [INFER] <concise claim> — <reason for inference>`. One bullet per distinct inference in the body. Never duplicate claims. Avoid vague bullets like "parameters are uncertain" — be specific about each parameter name.

---

## [INFER] tags that emerged during writing not covered by RESEARCH.md

These are candidate follow-up items for an operator with a running MT4 terminal:

1. **sm_gmtoffset publication mechanism:** Whether it uses GlobalVariable (most plausible) vs indicator buffer vs shared `.mqh` include-file global. This affects how all downstream indicators read it.
2. **Session minute offsets in sm_WorkTime inputs:** The integer-hour parameters (AsiaStart=0, LondonStart=7, USStart=13) may or may not internally add the 30-minute offsets (00:30, 07:30, 13:30 from MMM Book p. 8). The actual input might be separate `*Min` parameters or hard-coded internally.
3. **sm_WorkTime_no_autogmt BrokerDSTAdjust parameter:** Whether this parameter even exists in the 2011 binary (it may have been added only in the newer sm_WorkTime or may not exist at all).
4. **ObjectPrefix string:** The actual MT4 runtime object list for a chart running sm_WorkTime would immediately reveal the prefix. This would confirm or deny the "smWT_" assumption.
5. **NY-reversal sub-box end time:** MMM Book p. 40 says "about 3 hours"; whether this is exactly 16:30 GMT or e.g. 17:00, 16:00, or dynamically computed from the US session end.
6. **DSTAdjust subtraction direction in sm_gmtoffset:** The current spec subtracts 1 from `raw_offset` when broker appears DST-shifted. The correct direction may be the opposite depending on whether the broker includes or excludes DST in its reported server time — this is the primary algorithmic uncertainty.

---

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | sm_gmtoffset.md spec | `bf265fd` | `resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md` |
| 2 | sm_WorkTime.md spec | `892d1ed` | `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md` |
| 3 | sm_WorkTime_no_autogmt.md spec | `97d406f` | `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md` |

---

## Deviations from Plan

None — all 3 tasks executed exactly as written. No bugs, no missing dependencies, no architectural changes required. The docs/ directory and helpers/ subdirectory already existed from Plan 00.

---

## Tier 0 Review Status

**AWAITING USER REVIEW** — per 11-VALIDATION.md Manual-Only Verifications and 11-01-PLAN.md `<verification>` section, Plan 02 does NOT start until the user reads all 3 helper specs and approves.

Review instructions per VALIDATION.md:
> "After Tier 0 plan completes: user reads all 3 helper specs and confirms each is reconstruction-grade (could a future implementer build it from this?). User responds 'approved' or describes issues."

Review focus areas:
- Is the sm_gmtoffset auto-detection algorithm (TimeCurrent - TimeGMT) plausible?
- Are the session times (00:30 / 07:30 / 13:30 GMT) correctly cited from MMM Book p. 8?
- Is the NYReversal sub-box description (MMM Book p. 40, ~3 hours) correctly rendered?
- Are the BrokerGMT defaults and DSTAdjust logic reasonable for a 2011-era indicator?

**Timestamp awaiting review:** 2026-04-26 — capture "Tier 0 approved" + any feedback here before Plan 02 starts.

---

## Known Stubs

None — all three specs contain substantive content. No placeholder text ("TBD", "TODO") appears in any spec. The [INFER] tags are by design (source binaries are non-decompilable), not stubs.

---

## Self-Check

### Files exist:

- [x] `resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md` — FOUND
- [x] `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md` — FOUND
- [x] `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md` — FOUND

### Commits exist:

- [x] `bf265fd` — feat(11-01): write sm_gmtoffset.md reconstruction-grade spec (Task 1)
- [x] `892d1ed` — feat(11-01): write sm_WorkTime.md reconstruction-grade spec (Task 2)
- [x] `97d406f` — feat(11-01): write sm_WorkTime_no_autogmt.md reconstruction-grade spec (Task 3)

### Automated verify blocks:

- [x] `check_spec.sh sm_gmtoffset.md` — PASS
- [x] `check_spec.sh sm_WorkTime.md` — PASS
- [x] `check_spec.sh sm_WorkTime_no_autogmt.md` — PASS
- [x] `sm_WorkTime.md Dependencies mentions sm_gmtoffset` — PASS
- [x] `sm_WorkTime_no_autogmt.md Dependencies reads "None"` — PASS
- [x] `BrokerGMT in sm_WorkTime_no_autogmt.md` — PASS (15 occurrences)
- [x] `sm_WorkTime referenced in sm_WorkTime_no_autogmt.md` — PASS (31 occurrences)
- [x] `All 3 specs declare Confidence: Medium` — PASS

## Self-Check: PASSED
