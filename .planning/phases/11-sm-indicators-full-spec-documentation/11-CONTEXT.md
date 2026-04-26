# Phase 11: SM Indicators full-spec documentation — Context

**Gathered:** 2026-04-26
**Status:** Ready for planning
**Source:** Brainstorming session 2026-04-26 (design approved by user before invoking `/gsd:plan-phase 11`)

<domain>
## Phase Boundary

Produce reconstruction-grade documentation for **all 14 `!SM_*` / `!sm_*` MT4 indicators** found in `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/`. The `.ex4` source binaries are compiled MQL4 and **cannot be decompiled** — every spec is a best-effort reconstruction from:

1. The indicator filename (e.g., `!SM_ADR_Marker.ex4` → Average Daily Range Marker)
2. SM/MMM (Steve Mauro Market Maker Method) community knowledge
3. The MMM reference docs already on disk in `resource_pack/MMM/docs/` (MMM Book PDF, MMM Glossary, MMM Knowledge Base, MMM TDI Tradestation, MMM TOP 5 TDI Strategies, TDI indicator for Mobile, Anatomy of Stop Hunts, Market Maker Cycle image, MMM FX MINDSHIFT MVP)
4. Public references where the indicator name maps to a known community version (e.g., Ilsley Psych Levels, ZUP, Heiken Ashi, generic TDI)
5. Inference where 1–4 are insufficient — every inferred claim **MUST** be tagged `[INFER]`

**The phase delivers documentation only.** No `.mq4`, `.mq5`, or Python implementation code is produced in this phase. The goal is to enable a future implementer to reconstruct any of these 14 indicators in MQ4, MQ5, or Python without access to the original source.

**In scope:** 14 indicator specs + 1 INDEX = **15 markdown files** total.
**Out of scope:** the other ~40 third-party indicators in the same folder (DY-WK-MN-YR LINES, ECR Cross, MA Alert, MM4XSF_TDI, ZUP, etc.) — those start with names other than `!SM_` / `!sm_`.

</domain>

<decisions>
## Implementation Decisions

### Output Location (Locked)
- All output goes under `resource_pack/MMM/SM Indicators/docs/`
- Structure:
  ```
  resource_pack/MMM/SM Indicators/docs/
  ├── INDEX.md                            # written LAST
  ├── helpers/
  │   ├── sm_gmtoffset.md
  │   ├── sm_WorkTime.md
  │   └── sm_WorkTime_no_autogmt.md
  └── indicators/
      ├── SM_ADR_Marker.md
      ├── SM_Alerting+TL.md
      ├── SM_AlertZone_1.md
      ├── SM_AlertZone_2.md
      ├── SM_BPCT.md
      ├── SM_Crossover_Arrows.md
      ├── SM_Daily_HiLo.md
      ├── SM_IlsleyPsychLevels.md
      ├── SM_NewHUD.md
      ├── SM_PivotPoints.md
      └── SM_TDI.md
  ```
- Filenames preserve original casing/punctuation where meaningful but drop the leading `!` and the `.ex4` suffix (filesystem-friendly). For `!SM_Alerting+TL+v1.1.ex4` the `+v1.1` version suffix is dropped — only one canonical spec per indicator.

### Per-Indicator Template (Locked, 12 sections)
Every spec under `helpers/` and `indicators/` MUST contain these sections in this order:

1. **Header** — name, source filename (`.ex4`), source platform (MT4), confidence level (High / Medium / Low — based on how much can be inferred from MMM docs vs pure name-guessing)
2. **Purpose** — one paragraph: what it shows on the chart and why it matters in MMM/SM workflow
3. **Inputs / Parameters** — table of: parameter name, type, default value, valid range, meaning. Mark each row's confidence (e.g., "default 20" `[INFER]` vs "GMT offset hours" `[High]`)
4. **Outputs** — three subsections: indicator buffers (numeric series exposed to other indicators / EAs), chart objects (lines, zones, arrows, labels), alerts (popup / sound / email / push)
5. **Calculation logic** — step-by-step algorithm including the bar-iteration model (every-tick vs new-bar-only) and any timeframe-specific behavior
6. **Pseudocode** — language-neutral, ~30–80 lines
7. **Visual elements** — what's drawn, default colors, line/arrow styles, Z-order / draw layer (price chart vs subwindow)
8. **Dependencies** — other SM helpers it relies on (typically `sm_gmtoffset` for broker-time normalization or `sm_WorkTime` for session windows). External dependencies (e.g., timer events, file I/O) listed explicitly.
9. **Edge cases** — session boundaries, weekends, broker DST shifts, missing bars, broker-time-vs-GMT offset handling, low-digit symbols (JPY pairs, indices), zero-volume bars
10. **Test cases** — 2–4 concrete input→expected-output examples (e.g., "EURUSD H1 on 2025-04-25, ADR(20)=88 pips → marker at HighOfDay+44 pips and LowOfDay−44 pips"). Use real MMM-typical defaults.
11. **Port notes** — three target-specific paragraphs:
    - **MQ4 → MQ5 deltas:** OnInit signature, indicator handle vs buffer, `iCustom` vs `iIndicator`, `OnCalculate` parameters, drawing API differences
    - **Python port:** vectorized pandas approach vs per-bar iteration, no chart objects → output as DataFrame columns + lightweight matplotlib/plotly plot helpers, alert handling becomes log/event emission
    - **Backtester integration:** how this indicator's output would feed Helix's `backtest_hybrid` (if applicable — e.g., NewHUD is purely visual and has no backtester role; TDI directly feeds strategy signals)
12. **Uncertainty log** — bulleted list of every assumption made. Format: `[INFER] <claim> — <reason>`. Examples: `[INFER] Default ADR period is 20 — typical SM convention but unverifiable without source`

### Documentation Order (Locked)
Document in dependency order so primaries can reference helpers without forward refs:

- **Tier 0 — Helpers (3 files):**
  1. `sm_gmtoffset` — GMT offset detection (likely auto-detect via DST + broker server time)
  2. `sm_WorkTime` — session window definition, uses gmtoffset
  3. `sm_WorkTime_no_autogmt` — variant of WorkTime without auto-GMT (manual offset)

- **Tier 1 — Atomic indicators (5 files, no SM dependencies beyond Tier 0):**
  4. `SM_ADR_Marker` — Average Daily Range markers (high+ADR/2, low−ADR/2)
  5. `SM_Daily_HiLo` — daily high/low lines
  6. `SM_BPCT` — likely "Beat-Per-Candle Tracker" or "Bars Per Cycle Tracker" (resolve in research)
  7. `SM_IlsleyPsychLevels` — psychological levels at round numbers (00, 50)
  8. `SM_Crossover_Arrows` — generic MA crossover arrows

- **Tier 2 — Composite indicators (6 files, may depend on Tier 1 or call multiple helpers):**
  9. `SM_TDI` — Traders Dynamic Index (RSI + Bollinger Bands + MA), MMM's signature indicator
  10. `SM_PivotPoints` — daily/weekly pivot calculations (PP, R1-R3, S1-S3)
  11. `SM_AlertZone_1` — price-level alert zone (variant 1)
  12. `SM_AlertZone_2` — price-level alert zone (variant 2 — differs how?)
  13. `SM_Alerting+TL` — trendline-touch alerter
  14. `SM_NewHUD` — heads-up display dashboard (large, ~100KB binary — most complex)

- **INDEX.md (written LAST):** overview, ASCII dependency graph, glossary cross-refs to MMM docs, "How to use this folder" preface

### Review Cadence (Locked)
After **each tier completes** (Tier 0 → user review → Tier 1 → user review → Tier 2 → user review → INDEX.md), the user reviews and approves before the next tier starts. This keeps quality high and lets the user catch systemic template/format issues early before they propagate to all 14 files.

### Uncertainty Marking (Locked)
- High-confidence claims (e.g., "TDI uses RSI period 13 — confirmed in MMM TDI Tradestation PDF") have **no tag**.
- Medium-confidence claims (typical SM convention but unverifiable for this exact build) tagged **`[INFER]`**.
- Low-confidence claims (pure name-guessing, no community/doc support) tagged **`[INFER:guess]`**.

### Claude's Discretion
- Whether to use Mermaid or ASCII for the dependency graph in INDEX.md → choose whichever renders cleanly in plain markdown viewers (recommend ASCII for portability)
- Color hex codes in "Visual elements" sections → use commonly-seen MMM defaults (red/green/yellow on black) where the source is silent; tag `[INFER]`
- Pseudocode style → language-neutral imperative pseudocode (NOT MQL or Python syntax) so it's equally easy to port to all three targets
- How granular each "Test case" is → 2 cases minimum, 4 maximum, prioritizing edge cases over happy path
- Plan structure (1 plan per tier vs other slicing) → **recommended:** 1 plan per tier + 1 plan for INDEX.md = 4 plans, since each tier has internal review checkpoint and parallel-friendly file boundaries

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, plan-checker, executor) MUST read these before doing their work.**

### MMM Source Material (in this repo)
- `resource_pack/MMM/docs/_MMM Book.pdf` — primary MMM theory reference (3 MB)
- `resource_pack/MMM/docs/MMM Glossary.pdf` — official term definitions (39 KB)
- `resource_pack/MMM/docs/MMM_Glossary_Enhanced.md` — markdown-enhanced glossary (17 KB)
- `resource_pack/MMM/docs/MMM_Knowledge_Base.md` — curated MMM concepts (11 KB)
- `resource_pack/MMM/docs/GLOSSARY_IMPROVEMENTS.md` — recent glossary refinements (7 KB)
- `resource_pack/MMM/docs/MMM TDI_Tradestation.pdf` — **critical for `SM_TDI.md`** (1.2 MB)
- `resource_pack/MMM/docs/MMM TOP 5 TDI Strategies.pdf` — TDI usage patterns (1.2 MB)
- `resource_pack/MMM/docs/TDI indicator for Mobile.pdf` — mobile/visual TDI reference (377 KB)
- `resource_pack/MMM/docs/Anatomy of Stop Hunts ( Trap Moves).pdf` — context for AlertZone / PivotPoint usage (7 MB)
- `resource_pack/MMM/docs/Market Maker Cycle.jpg` — visual reference for the market-maker cycle phases that NewHUD likely displays
- `resource_pack/MMM/docs/MMM FX MINDSHIFT - MVP.pdf` — MMM mindset/process material (18 MB)

### Source Binaries (read for filenames, not content)
- `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/!SM_*.ex4` (11 uppercase)
- `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/!sm_*.ex4` (3 lowercase helpers)

### Helix Project Context (for "Backtester integration" port-notes section)
- `.planning/PROJECT.md` — Helix v2.0 architecture (8 pairs × M15/H1/Daily, five-axis goal)
- `V2/v3_intelligence/pair_config.py` — canonical pair × timeframe matrix
- Recent INFRA-04 work: `BandD_TradeReplay.mq5`, `ADR_Levels.mq5` already landed in Phase 08.4-04 — these are the **precedent** for how SM indicators would integrate if ported to MQ5

### Output Location
- `resource_pack/MMM/SM Indicators/docs/` — does not exist yet, will be created by Tier 0 plan

</canonical_refs>

<specifics>
## Specific Ideas

- The `!sm_WorkTime.ex4` and `!sm_WorkTime_no_autogmt.ex4` files are large (43KB and 38KB) and date back to 2011 — they are likely the most-relied-on helpers. Treat their specs as foundational; subsequent specs reference them.
- `!SM_NewHUD.ex4` is **100KB** — by far the largest. Its spec will likely be the longest and most complex. Plan for ~5-7 pages, not 3-4.
- The numbered variants (`AlertZone_1` vs `AlertZone_2`, `Alerting+TL+v1.1` suggesting earlier `+v1.0`) suggest these are evolutionary versions. Spec the latest version; mention the earlier in the Uncertainty log if relevant.
- `SM_TDI` is the load-bearing indicator for MMM strategy generation — there are two dedicated MMM PDFs about it. Its spec should be the deepest, with at least 4 test cases drawn from "MMM TOP 5 TDI Strategies."
- Confidence will vary widely: TDI is high-confidence (multiple MMM PDFs); BPCT and IlsleyPsychLevels are medium (community references exist); helpers are medium-low (broker-time conversion is well-understood but exact behavior unverifiable). Each spec's Header section makes this explicit.

</specifics>

<deferred>
## Deferred Ideas

- **Actual `.mq4` / `.mq5` / Python implementation** — explicit out-of-scope for Phase 11. Reconstruction code is a future phase, opened only after these specs pass review.
- **Re-spec of the ~40 third-party indicators** in the same folder (DY-WK-MN-YR LINES, ECR Cross, MA Alert, MM4XSF_TDI, ZUP, Sessions(auto), THV3 SDX-TzPivots, etc.) — out of scope here; they are not `!SM_*` and most have publicly-available source elsewhere.
- **MMM glossary expansion** — if specs surface new terms not in `MMM_Glossary_Enhanced.md`, those go to a backlog item, not into this phase.
- **Visual reproduction of HUD screenshots** — verifying NewHUD spec against a live MT4 chart screenshot would close uncertainty but requires running MT4 (Wine or otherwise). Out of scope; flagged as a future verification task.
- **Cross-language port unit tests** — once MQ4/MQ5/Python implementations exist, parity tests across all three targets per indicator. Future phase only.

</deferred>

---

*Phase: 11-sm-indicators-full-spec-documentation*
*Context gathered: 2026-04-26 via brainstorming session (no separate `/gsd:discuss-phase` run — design was locked in conversation, then `/gsd:plan-phase 11` invoked directly)*
