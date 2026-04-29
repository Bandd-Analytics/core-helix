# SM Indicators — Reconstruction Spec Index

A reconstruction-grade reference for the 14 `!SM_*` / `!sm_*` MT4 indicators that constitute Steve Mauro's Market Maker Method (MMM) chart setup.

The source `.ex4` binaries are compiled MQL4 and **cannot be decompiled**. Every spec is a best-effort reconstruction from: (1) the indicator filename, (2) MMM/SM community knowledge, (3) the MMM reference docs on disk in `resource_pack/MMM/docs/`, and (4) public references where the indicator name maps to a known community version. Confidence is uneven — SM_TDI is **High** (multiple MMM PDFs supply all parameters); SM_BPCT is **Low** (abbreviation unresolved). This INDEX plus 14 indicator specs equals **15 markdown files total** (3 helpers + 11 main indicators).

---

## Overview

Steve Mauro's Market Maker Method (MMM) is a UK-rooted FX-trading methodology centred on session-based price action (Asia / London / US), market-maker manipulation cycles, and a TDI-confirmed entry framework. The method maps broker server time to GMT session windows, tracks the prior day's high/low and ADR markers as key levels, uses the Traders Dynamic Index as the sole confirmation indicator, and interprets pivot mid-points (M1-M4) to predict where the daily high or low will form.

The 14 indicators in this folder automate the MMM scanning view described in the MMM Book pp. 53-54. They collectively handle: broker-time normalisation (sm_gmtoffset, sm_WorkTime), session-window boxes (sm_WorkTime variants), Average Daily Range markers (SM_ADR_Marker), daily high/low lines (SM_Daily_HiLo), psychological levels (SM_IlsleyPsychLevels), EMA crossover arrows (SM_Crossover_Arrows), the TDI confirmation subwindow (SM_TDI), daily pivots with M1-M4 mid-pivots (SM_PivotPoints), price-zone alerters (SM_AlertZone_1/2), trendline-touch alerter (SM_Alerting+TL), and a heads-up display dashboard (SM_NewHUD) that ties the scanning matrix together.

---

## How to use this folder

- **For a future implementer (MQ4 / MQ5 / Python port):** Start with the relevant indicator's spec, read sections 5 (Calculation logic) + 6 (Pseudocode) + 11 (Port notes). Use the Tier 0 helpers (sm_gmtoffset, sm_WorkTime) as foundations **before** implementing indicators that depend on them.
- **For a trader trying to understand what these indicators do:** Read sections 2 (Purpose) + 7 (Visual elements) + 10 (Test cases). Skip Pseudocode and Port notes.
- **For an MT4 operator who can run the indicators live:** Every `[INFER]` and `[INFER:guess]` tag in section 12 (Uncertainty log) is a candidate verification point. Run the indicator, read the parameter dialog, and update the spec.
- **Confidence levels:** Untagged claim = **High** (sourced from MMM docs or well-confirmed community sources); `[INFER]` = **Medium** (typical SM convention, unverified for this exact build); `[INFER:guess]` = **Low** (pure inference with no direct source).

---

## Dependency graph

```
Tier 0 — Helpers
----------------
sm_gmtoffset                          [no deps — Tier 0 bottom]
    ├── sm_WorkTime                   [reads sm_GMTOffset GlobalVariable set by sm_gmtoffset]
    └── sm_WorkTime_no_autogmt        [explicitly NO sm_gmtoffset dep — manual BrokerGMT input]


Tier 1 — Atomic Indicators  (no SM deps beyond optional Tier 0)
---------------------------------------------------------------
sm_gmtoffset (optional — D1-boundary alignment) [INFER]:
    ├── SM_ADR_Marker                 [may read sm_GMTOffset for today_open D1 boundary]
    └── SM_Daily_HiLo                 [may read sm_GMTOffset for D1 boundary detection]

Self-contained (no SM deps):
    ├── SM_IlsleyPsychLevels          [round-number psych levels — no session awareness]
    ├── SM_Crossover_Arrows           [EMA 5/13 crossover — self-contained]
    └── SM_BPCT                       [abbreviation UNRESOLVED — LOW confidence]
                                       [may or may not consume sm_WorkTime; see Uncertainty log]


Tier 2 — Composite Indicators
------------------------------
sm_gmtoffset (optional / required) [INFER]:
    ├── SM_PivotPoints                [uses for daily-reset GMT alignment]
    └── SM_NewHUD                     [uses for session display and broker-time normalisation]

Self-contained (no confirmed SM deps):
    ├── SM_TDI                        [the load-bearing MMM confirmation indicator — self-contained]
    ├── SM_AlertZone_1                [lower price-zone alerter (long setups)]
    ├── SM_AlertZone_2                [upper price-zone alerter (short setups);
    │                                  same algorithm as AlertZone_1, different defaults — [INFER]]
    └── SM_Alerting+TL                [monitors user-drawn OBJ_TREND objects — no SM deps]


Notes:
• SM_NewHUD is a HUD dashboard. It DISPLAYS data that may originate from SM_TDI,
  SM_ADR_Marker, SM_PivotPoints, and SM_Daily_HiLo. Whether it computes these values
  internally or calls iCustom() on the dedicated indicators is [INFER] — see SM_NewHUD
  spec §8 Dependencies. The 100KB binary size makes self-contained computation plausible.
• SM_BPCT's position in this graph cannot be determined — it may be self-contained, or
  it may consume sm_WorkTime for session filtering. The spec presents three candidate
  interpretations; all are tagged [INFER:guess].
• SM_ADR_Marker and SM_Daily_HiLo have NO mandatory SM dependencies. The sm_gmtoffset
  dependency is optional — both can function using the platform's built-in D1 bar
  boundary. The dependency is noted as [INFER].
• sm_WorkTime_no_autogmt explicitly has NO dependency on sm_gmtoffset by design — it
  accepts a manual BrokerGMT integer input. This is the key architectural distinction
  between the two WorkTime variants.
```

---

## Specs

| # | Tier | Spec | Confidence | Source binary | Brief purpose |
|---|------|------|------------|---------------|---------------|
| 1 | 0 | [sm_gmtoffset](./helpers/sm_gmtoffset.md) | Medium | `!sm_gmtoffset.ex4` | Detect broker GMT offset; publish via GlobalVariable `sm_GMTOffset` |
| 2 | 0 | [sm_WorkTime](./helpers/sm_WorkTime.md) | Medium | `!sm_WorkTime.ex4` | Session-window box overlay (Asia/London/US) using auto-GMT from sm_gmtoffset |
| 3 | 0 | [sm_WorkTime_no_autogmt](./helpers/sm_WorkTime_no_autogmt.md) | Medium | `!sm_WorkTime_no_autogmt.ex4` | Session-window boxes using manual BrokerGMT input (no sm_gmtoffset dep) |
| 4 | 1 | [SM_ADR_Marker](./indicators/SM_ADR_Marker.md) | High | `!SM_ADR_Marker.ex4` | ADR markers: `today_open ± ADR/2` (20-day lookback) |
| 5 | 1 | [SM_Daily_HiLo](./indicators/SM_Daily_HiLo.md) | High | `!SM_Daily_HiLo.ex4` | Previous day High/Low horizontal lines (PHOD/PLOD) |
| 6 | 1 | [SM_BPCT](./indicators/SM_BPCT.md) | Low | `!SM_BPCT.ex4` | Abbreviation UNRESOLVED — best-guess: Buy/Sell Pressure Candle Tracker (3 candidate interpretations in spec) |
| 7 | 1 | [SM_IlsleyPsychLevels](./indicators/SM_IlsleyPsychLevels.md) | Medium | `!SM_IlsleyPsychLevels.ex4` | Round-number psychological levels (00/50 pip intervals) |
| 8 | 1 | [SM_Crossover_Arrows](./indicators/SM_Crossover_Arrows.md) | Medium | `!SM_Crossover_Arrows.ex4` | EMA 5/13 crossover arrows (MMM primary entry-signal pair) |
| 9 | 2 | [SM_TDI](./indicators/SM_TDI.md) | High | `!SM_TDI.ex4` | Traders Dynamic Index — RSI(13) + Bollinger Bands + MAs; the MMM signature confirmation indicator |
| 10 | 2 | [SM_PivotPoints](./indicators/SM_PivotPoints.md) | High | `!SM_PivotPoints.ex4` | Daily pivots (PP/R1-R3/S1-S3) + MMM-specific M1-M4 mid-pivots |
| 11 | 2 | [SM_AlertZone_1](./indicators/SM_AlertZone_1.md) | Medium | `!SM_AlertZone_1.ex4` | Lower price-zone alerter (long setup entry zone) |
| 12 | 2 | [SM_AlertZone_2](./indicators/SM_AlertZone_2.md) | Medium | `!SM_AlertZone_2.ex4` | Upper price-zone alerter (short setup entry zone; same algorithm as AlertZone_1, different defaults) |
| 13 | 2 | [SM_Alerting+TL](./indicators/SM_Alerting+TL.md) | Medium | `!SM_Alerting+TL+v1.1.ex4` | Trendline-touch alerter — monitors all OBJ_TREND objects on chart |
| 14 | 2 | [SM_NewHUD](./indicators/SM_NewHUD.md) | Low | `!SM_NewHUD.ex4` | Heads-up display dashboard (100KB binary; aggregates ~10 MMM scanning fields) |

---

## MMM glossary cross-references

### MMM source documents

The following source documents are in `resource_pack/MMM/docs/`. Paths are relative from this INDEX.md (at `resource_pack/MMM/SM Indicators/docs/INDEX.md`):

- [_MMM Book.pdf](../../docs/_MMM%20Book.pdf) — **Primary methodology reference.** Session times (p. 8), colour-coded sessions (p. 40), PHOD/PLOD markers (p. 41), ADR High/Low (p. 41), pivot system (pp. 42-43), RSI (p. 44), TDI patterns (pp. 45-46), confluence signals (p. 47), Strike Zones (p. 55), Scanning View / Intraday Directional Matrix (pp. 53-54).
- [MMM TDI_Tradestation.pdf](../../docs/MMM%20TDI_Tradestation.pdf) — **Load-bearing reference for SM_TDI.** Supplies all five line definitions, all parameter values (RSI period 13, VB period 34, StdDev 1.6185, RSI_PL 2, TSL 7, MBL 34), all three alert types, and the 32/50/68 reference levels. The only document that makes SM_TDI a High-confidence spec.
- [MMM TOP 5 TDI Strategies.pdf](../../docs/MMM%20TOP%205%20TDI%20Strategies.pdf) — TDI usage patterns and entry frameworks; cross-reference for SM_TDI test cases.
- [TDI indicator for Mobile.pdf](../../docs/TDI%20indicator%20for%20Mobile.pdf) — Visual TDI reference; useful for confirming line colours and subwindow layout.
- [MMM_Glossary_Enhanced.md](../../docs/MMM_Glossary_Enhanced.md) — Markdown-enhanced MMM glossary with definitions for ADR, HOD/LOD, I-HOD/I-LOD, TDI, Time Mapping, Strike Zone, Pivot Phases, Stop Hunt, and related terms. Primary source for the Glossary Hooks table below.
- [MMM_Knowledge_Base.md](../../docs/MMM_Knowledge_Base.md) — Curated MMM concepts: 3-day cycle, M/W formations, session timing details, session open "kill zone" definition.
- [Anatomy of Stop Hunts ( Trap Moves).pdf](../../docs/Anatomy%20of%20Stop%20Hunts%20%28%20Trap%20Moves%29.pdf) — Context for SM_AlertZone_1/2 and SM_Alerting+TL; explains the market-maker stop-hunt mechanic that AlertZones are designed to warn about.
- [Market Maker Cycle.jpg](../../docs/Market%20Maker%20Cycle.jpg) — Visual reference for the 3-day accumulation / move / distribution cycle that SM_NewHUD likely displays as a cycle-stage indicator.
- [MMM FX MINDSHIFT - MVP.pdf](../../docs/MMM%20FX%20MINDSHIFT%20-%20MVP.pdf) — MMM mindset and process material; background context for the broader SM methodology.

### Glossary hooks — terms to indicators

Terms from the MMM Glossary Enhanced and MMM Knowledge Base, mapped to the indicators that implement or display them:

| Term | Definition | Indicator(s) |
|------|-----------|-------------|
| ADR | Average Daily Range — mean of `DailyHigh - DailyLow` over a lookback window (typically 20 days); measures how far price moves in a typical day | [SM_ADR_Marker](./indicators/SM_ADR_Marker.md), [SM_PivotPoints](./indicators/SM_PivotPoints.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| HOD / LOD | High/Low of Day — the highest and lowest price reached in the current 24-hour period | [SM_Daily_HiLo](./indicators/SM_Daily_HiLo.md), [SM_AlertZone_1](./indicators/SM_AlertZone_1.md), [SM_AlertZone_2](./indicators/SM_AlertZone_2.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| I-HOD / I-LOD | Initial High/Low of Day — the high and low set during the Asian session before London opens; the market maker's initial reference range | [sm_WorkTime](./helpers/sm_WorkTime.md), [SM_AlertZone_1](./indicators/SM_AlertZone_1.md), [SM_AlertZone_2](./indicators/SM_AlertZone_2.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| Market Maker Spread | Distance between I-HOD and I-LOD; ideally < 50 pips for a valid MMM setup | [SM_ADR_Marker](./indicators/SM_ADR_Marker.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| Time Mapping | The action of matching broker server time to session indicator times | [sm_gmtoffset](./helpers/sm_gmtoffset.md), [sm_WorkTime](./helpers/sm_WorkTime.md) |
| Gap Time | The changeover period between sessions (e.g., 07:00-07:30 GMT between Asia close and London open) | [sm_WorkTime](./helpers/sm_WorkTime.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| Session Open / Kill Zone | The first 1-3 hours of a session open (London 07:30, NY 13:30 GMT); highest-probability entry window | [sm_WorkTime](./helpers/sm_WorkTime.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |
| Strike Zone / Blue Box | Price area within ~15-20 pips of the HOD/LOD where MMM setups trigger; equivalent to "Trading Zone" | [SM_AlertZone_1](./indicators/SM_AlertZone_1.md), [SM_AlertZone_2](./indicators/SM_AlertZone_2.md), [SM_Alerting+TL](./indicators/SM_Alerting+TL.md) |
| Stop Hunt / Trap Zone | Aggressive market-maker move designed to trigger retail stop-loss orders before the real directional move | [SM_AlertZone_1](./indicators/SM_AlertZone_1.md), [SM_AlertZone_2](./indicators/SM_AlertZone_2.md), [SM_Alerting+TL](./indicators/SM_Alerting+TL.md) |
| Pivot Phases (M1-M4) | MMM mid-pivot system: M1=(S2+S1)/2, M2=(S1+PP)/2, M3=(PP+R1)/2, M4=(R1+R2)/2; used to predict where the daily HOD/LOD will form based on prior candle colour | [SM_PivotPoints](./indicators/SM_PivotPoints.md) |
| TDI | Traders Dynamic Index — RSI+Bollinger Bands+MA hybrid by Dean Malone; the MMM signature confirmation indicator | [SM_TDI](./indicators/SM_TDI.md) |
| Shark Fin | TDI pattern: RSI PL (green line) spikes above 68 or below 32 then re-enters the volatility band — indicates a stop hunt | [SM_TDI](./indicators/SM_TDI.md) |
| Blood in the Water | TDI pattern: RSI PL crosses the Market Base Line (yellow) with price confirmation — trend continuation entry signal | [SM_TDI](./indicators/SM_TDI.md) |
| VB Squeeze | TDI Volatility Band contraction — sign of consolidation before a breakout; precedes high-probability entries | [SM_TDI](./indicators/SM_TDI.md) |
| TDI Hook | Counter-trend signal: RSI PL hooks back from an extreme (>68 or <32) across the volatility band boundary | [SM_TDI](./indicators/SM_TDI.md) |
| 3-Day Cycle | Market maker cycle repeating over 3 days: accumulation / directional move / distribution | [SM_NewHUD](./indicators/SM_NewHUD.md) |
| Psychological Levels | Round-number price levels (e.g., 1.3000, 1.3050) where institutional orders concentrate | [SM_IlsleyPsychLevels](./indicators/SM_IlsleyPsychLevels.md) |
| EMA 5/13 | The primary short-term EMA crossover pair in MMM; crossing generates initial entry signals (confirmed by MMM Book p. 47) | [SM_Crossover_Arrows](./indicators/SM_Crossover_Arrows.md) |
| Peak Formation | The highest or lowest intraday point; key reference for HOD/LOD tracking | [SM_Daily_HiLo](./indicators/SM_Daily_HiLo.md), [SM_NewHUD](./indicators/SM_NewHUD.md) |

---

## Confidence summary

### High confidence — trustable for direct port

These specs are grounded in primary MMM source documents or confirmed community precedents. An implementer can port directly using the spec without significant uncertainty:

- **SM_TDI** — All five line definitions, all parameter values (RSI period 13, VB period 34, StdDev 1.6185, RSI_PL 2, TSL 7, MBL 34), and all three alert types are directly sourced from the MMM TDI Tradestation PDF. Cross-confirmed by multiple community sources. Only MEDIUM item: exact StdDev multiplier (1.6185 vs 2.0) — verify in MT4 Inputs tab.
- **SM_ADR_Marker** — Formula `today_open ± ADR/2` doubly confirmed: MMM Book p. 41 + `V2/indicators/ADR_Levels.mq5` (INFRA-04 precedent). ADR_Levels.mq5 is the canonical MQ5 skeleton.
- **SM_Daily_HiLo** — Purpose confirmed by MMM Book p. 41 (PHOD/PLOD markers); algorithm `iHigh/iLow(PERIOD_D1, 1)` is directly derivable from indicator name + purpose.
- **SM_PivotPoints** — Standard floor-pivot formula (PP/R1-R3/S1-S3) is HIGH confidence; MMM-specific M1-M4 mid-pivot system confirmed by MMM Book pp. 42-43. Note: daily reset time and M1-M4 implementation are MEDIUM confidence.

### Medium confidence — port with caveats; verify parameter defaults in MT4

These specs have well-understood purpose and algorithm but unverified parameter names, defaults, or implementation specifics:

- **sm_gmtoffset** — Function is well-understood (TimeCurrent() − TimeGMT() delta approach + GlobalVariable `sm_GMTOffset`); exact parameter names and DST-detection algorithm unverified for this specific 2019 binary.
- **sm_WorkTime** — Session logic confirmed by MMM Book p. 8 (session times) + p. 40 (colour-coded boxes); parameter names and ObjectPrefix naming convention are `[INFER]`.
- **sm_WorkTime_no_autogmt** — Functional identity to sm_WorkTime minus auto-GMT is clearly encoded in the filename; BrokerGMT default value and BrokerDSTAdjust parameter existence are `[INFER]`.
- **SM_IlsleyPsychLevels** — Round-number level algorithm is HIGH confidence (industry-standard pattern); Ilsley-specific parameter choices and JPY-adaptation behaviour are `[INFER]`.
- **SM_Crossover_Arrows** — EMA 5/13 confirmed by MMM Book p. 47; arrow style, MA line display, and alert behaviour are `[INFER]`.
- **SM_AlertZone_1** — Zone-alert concept confirmed by MMM Book p. 55 + MMM Glossary (Strike Zone); whether zone is user-defined or auto-calculated from HOD/LOD is `[INFER]`.
- **SM_AlertZone_2** — 148-byte file size delta from AlertZone_1 is the primary evidence for the same-algorithm / different-defaults hypothesis; the exact difference is `[INFER]`.
- **SM_Alerting+TL** — Trendline-touch alerter semantics are clear from the filename; touch-detection tolerance (TouchPips) and iteration scope are `[INFER]`.

### Low confidence — rewrite recommended after MT4 inspection

These specs contain extensive `[INFER:guess]` tags. A spec revision is expected after an operator runs the indicator in MT4 and reads the parameter dialog or observes chart behaviour:

- **SM_BPCT** — The "BPCT" abbreviation is unresolved. The entire spec is a best-effort reconstruction from three candidate interpretations: (1) Bars Per Cycle Tracker, (2) Beat-the-MM Pip Count Tracker, (3) Buy/Sell Pressure Candle Tracker. Candidate 3 is used as the working hypothesis. 41 `[INFER:guess]` tags — every behavioural claim is speculative.
- **SM_NewHUD** — Purpose is understood (MMM scanning-view aggregator per pp. 53-54); internals are LOW confidence: exact field list, calculation source (internal vs iCustom), refresh logic, multi-pair support, and rendering layout are all `[INFER]` or `[INFER:guess]`.

**Confidence by count:**

| Level | Count | Indicators |
|-------|-------|------------|
| High | 4 | SM_TDI, SM_ADR_Marker, SM_Daily_HiLo, SM_PivotPoints |
| Medium | 8 | sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt, SM_IlsleyPsychLevels, SM_Crossover_Arrows, SM_AlertZone_1, SM_AlertZone_2, SM_Alerting+TL |
| Low | 2 | SM_BPCT, SM_NewHUD |

---

## Open questions for future MT4 operator

The following items can each be resolved in seconds by an operator who can run the indicator in MT4 and read the parameter dialog or observe chart behaviour. None are phase blockers, but each resolution improves the relevant spec from `[INFER]` to confirmed:

- **SM_BPCT abbreviation:** Run the indicator; read the indicator name in the MT4 Inputs tab. Pick from: {Bars Per Cycle Tracker, Beat-the-MM Pip Count Tracker, Buy/Sell Pressure Candle Tracker} OR document the actual abbreviation. This unlocks a full spec rewrite of the BPCT spec.
- **SM_TDI StdDev multiplier:** Run SM_TDI → read the "StdDev" parameter default in the Inputs tab. The spec documents 1.6185 as the most-cited community value; it could be 2.0 in the SM variant.
- **SM_AlertZone_1 vs SM_AlertZone_2 distinction:** Load both on the same chart → compare parameter dialogs. The 148-byte binary delta corresponds to one or two specific parameter differences (color constant / sound filename / object prefix). Document the exact difference.
- **SM_NewHUD field set:** Run SM_NewHUD on a EURUSD H1 chart → capture a screenshot of the HUD at session boundary and at active-session midpoint. Document the exact field list, ordering, and any conditional rendering. Compare against the 10-section list in the SM_NewHUD spec.
- **SM_NewHUD data source (iCustom vs internal):** Load SM_TDI and SM_NewHUD together. Remove SM_TDI. If the TDI field in the HUD goes blank → HUD uses `iCustom`. If values continue → HUD computes internally. This resolves the most important architectural unknown in the entire corpus.
- **sm_WorkTime session minute offsets:** Confirm whether the Asia/London/US start parameters accept minutes-since-midnight (allowing 00:30, 07:30, 13:30) or integer hours only (0, 7, 13). Read the parameter dialog for `AsiaStart`, `LondonStart`, `USStart`.
- **sm_gmtoffset publication mechanism:** Confirm whether the indicator writes to GlobalVariable (expected: `sm_GMTOffset`), an indicator buffer, or a shared `.mqh` include. This affects how every downstream indicator reads the offset.
- **Default colors and object prefixes:** For any indicator, capturing the MT4 Inputs tab at load time reveals all parameter defaults. The object prefix used by each indicator (e.g., "smWT_", "ADR_", "SM_PVT_") is visible in the MT4 Objects List.

---

## Phase metadata

- **Phase:** 11-sm-indicators-full-spec-documentation
- **Created:** 2026-04-27
- **Source binaries:** `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/!{SM_*,sm_*}.ex4` (14 files)
- **Spec template:** 12-section locked (Header / Purpose / Inputs / Outputs / Calculation logic / Pseudocode / Visual elements / Dependencies / Edge cases / Test cases / Port notes / Uncertainty log) — see [11-CONTEXT.md](../../../../.planning/phases/11-sm-indicators-full-spec-documentation/11-CONTEXT.md) §Per-Indicator Template
- **Validation rubric:** see [11-VALIDATION.md](../../../../.planning/phases/11-sm-indicators-full-spec-documentation/11-VALIDATION.md)
- **Reconstruction methodology:** The `.ex4` binaries are compiled MQL4 and are not decompilable with any public tool. All specs are best-effort reconstructions from indicator names, MMM source docs, community knowledge, and binary size analysis. Every claim not directly sourced from a primary document is tagged `[INFER]` (medium confidence) or `[INFER:guess]` (low confidence). These tags are the primary review targets for any operator who gains MT4 access to the live indicator suite.

---

## Implementation matrix (Phase 12)

Per D-14, this section is updated at the end of each Phase 12 tier with
the per-spec implementation status. Each row's "Status" cell summarizes
the per-target footer added to the linked spec.

### Tier 0 — helpers (Plan 12-01)

| # | Spec | MQ4 | MQ5 | Python | Version | Confidence | Footer link |
|---|------|-----|-----|--------|---------|------------|-------------|
| 1 | [sm_gmtoffset](./helpers/sm_gmtoffset.md) | ✅ | ✅ | ✅ | v2.00 (MQ4/MQ5) / v1.00 (Py) | High | [#implementation-status-phase-12](./helpers/sm_gmtoffset.md#implementation-status-phase-12) |
| 2 | [sm_WorkTime](./helpers/sm_WorkTime.md) | ✅ | ✅ | ✅ | v2.00 | High | [#implementation-status-phase-12](./helpers/sm_WorkTime.md#implementation-status-phase-12) |
| 3 | [sm_WorkTime_no_autogmt](./helpers/sm_WorkTime_no_autogmt.md) | ✅ | ✅ | ✅ | v2.00 | High | [#implementation-status-phase-12](./helpers/sm_WorkTime_no_autogmt.md#implementation-status-phase-12) |

Tier 0 review: approved 2026-04-28 (operator). v2.00 visual contract verified against `V2/indicators/BandD_WorktimeRibbon.mq5` reference (operator smoke-test 2026-04-28). See per-spec "v2.00 changes" section for the full delta from the 2011-era binary spec.

### Tier 1 — atomic indicators (Plan 12-02)

| # | Spec | MQ4 | MQ5 | Python | Confidence | Footer link |
|---|------|-----|-----|--------|------------|-------------|
| 4 | [SM_ADR_Marker](./indicators/SM_ADR_Marker.md) | ✅ | ✅ | ✅ | High | [#implementation-status-phase-12](./indicators/SM_ADR_Marker.md#implementation-status-phase-12) |
| 5 | [SM_Daily_HiLo](./indicators/SM_Daily_HiLo.md) | ✅ | ✅ | ✅ | High | [#implementation-status-phase-12](./indicators/SM_Daily_HiLo.md#implementation-status-phase-12) |
| 6 | [SM_BPCT](./indicators/SM_BPCT.md) | ⚠ | ⚠ | ⚠ | Low (D-17) | [#implementation-status-phase-12](./indicators/SM_BPCT.md#implementation-status-phase-12) |
| 7 | [SM_IlsleyPsychLevels](./indicators/SM_IlsleyPsychLevels.md) | ✅ | ✅ | ✅ | Medium | [#implementation-status-phase-12](./indicators/SM_IlsleyPsychLevels.md#implementation-status-phase-12) |
| 8 | [SM_Crossover_Arrows](./indicators/SM_Crossover_Arrows.md) | ✅ | ✅ | ✅ | Medium | [#implementation-status-phase-12](./indicators/SM_Crossover_Arrows.md#implementation-status-phase-12) |

Tier 1 review: approved YYYY-MM-DD (operator).

### Tier 2 — composite indicators (Plan 12-03)

| # | Spec | MQ4 | MQ5 | Python | Confidence | Footer link |
|---|------|-----|-----|--------|------------|-------------|
| 9 | [SM_TDI](./indicators/SM_TDI.md) | ✅ | ✅ | ✅ | High | [#implementation-status-phase-12](./indicators/SM_TDI.md#implementation-status-phase-12) |
| 10 | [SM_PivotPoints](./indicators/SM_PivotPoints.md) | ✅ | ✅ | ✅ | High | [#implementation-status-phase-12](./indicators/SM_PivotPoints.md#implementation-status-phase-12) |
| 11 | [SM_AlertZone_1](./indicators/SM_AlertZone_1.md) | ✅ | ✅ | ✅ | Medium | [#implementation-status-phase-12](./indicators/SM_AlertZone_1.md#implementation-status-phase-12) |
| 12 | [SM_AlertZone_2](./indicators/SM_AlertZone_2.md) | ✅ | ✅ | ✅ | Medium | [#implementation-status-phase-12](./indicators/SM_AlertZone_2.md#implementation-status-phase-12) |
| 13 | [SM_Alerting+TL](./indicators/SM_Alerting+TL.md) | ✅ | ✅ | ✅ | Medium | [#implementation-status-phase-12](./indicators/SM_Alerting+TL.md#implementation-status-phase-12) |
| 14 | [SM_NewHUD](./indicators/SM_NewHUD.md) | ⚠ | ⚠ | ⚠ | Low (D-17) | [#implementation-status-phase-12](./indicators/SM_NewHUD.md#implementation-status-phase-12) |

Tier 2 review: approved YYYY-MM-DD (operator).

### Phase 12 summary

- **14 indicators** built across **MQ4 + MQ5 + Python** (3 helpers + 5 atomic + 6 composite)
- **Compile-clean:** all 28 MQ source files (14 .mq4 + 14 .mq5) pass `0 errors, 0 warnings` under Wine MetaEditor
- **Pytest:** all 14 indicators have ≥1 GREEN test; SM_TDI has ≥5 cases per spec Section 10
- **Verified Updates honored:** SM_TDI RSI=21 + Shark_Fin 63/37; SM_ADR_Marker ATRPeriod=14; SM_BPCT mini-HUD; SM_NewHUD 18-field set + HYADR + Av_N EMAs (1, 4, 13, 26, 52)
- **Built ⚠ (D-17 Low confidence):** SM_BPCT, SM_NewHUD
- **Advisory parity (D-15):** scripts available for SM_ADR_Marker, SM_Daily_HiLo, SM_IlsleyPsychLevels, SM_TDI, SM_PivotPoints (5 of 7 high-confidence deterministic indicators). The remaining 2 (sm_gmtoffset, sm_WorkTime) are deferred — their return-value contract is too simple to merit a CSV diff (sm_gmtoffset returns a single int hours offset; sm_WorkTime returns a session-window boolean), and Python↔MQ parity for them is enforced structurally by the unit tests.
- **AlertZone shared module:** SM_AlertZone_1 and SM_AlertZone_2 share `compute_alert_zone()` in Python per RESEARCH Open Question #5 (148-byte binary delta = same algorithm, different defaults)

Status legend: ✅ Built (high/medium confidence) · ⚠ Built (low confidence per D-17) · ❌ Skipped (not applicable per D-18)
