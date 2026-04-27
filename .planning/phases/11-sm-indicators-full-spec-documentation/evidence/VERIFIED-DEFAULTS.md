# Phase 11 — Verified Defaults from MT4 Inputs Dialog

**Captured:** 2026-04-27
**Source:** Operator screenshots (Google Drive folder `1Ot904w4UzsQMkoM33auodits5DtGl3qb`) of `!SM_*.ex4` indicators attached to a live MT4 chart, showing the "Inputs" tab of each indicator's properties dialog.
**Provider:** banddanalytics
**OCR'd by:** Claude (Drive MCP `read_file_content`)

This document records only the **observed parameter values from the live MT4 Inputs dialog**. It supersedes any `[INFER]` or `[INFER:guess]` tag in the corresponding Phase 11 spec where the same parameter is now confirmed. Charts (visual overlay screenshots) returned empty OCR for most images — visual fields are still inferred where stated below, but the Inputs-tab data is high confidence.

Indicators **NOT covered** by screenshots (no live data captured): sm_WorkTime, sm_WorkTime_no_autogmt, SM_Daily_HiLo, SM_IlsleyPsychLevels, SM_Crossover_Arrows, SM_PivotPoints, SM_AlertZone_1, SM_AlertZone_2, SM_Alerting+TL. Those specs retain their original `[INFER]` confidence levels.

---

## 1. SM_BPCT — Inputs Confirmed (was Confidence: Low)

**Indicator name in dialog:** `!SM_BPCT` (binary filename matches; the "BCPT" folder name in Google Drive is a typo). The acronym is **still unresolved** but the indicator's *function* is now confirmed:

**BPCT is a mini-HUD / status panel** displayed in a chart corner. It shows real-time price, spread, and HOD/LOD distance, with alerts when price approaches HOD/LOD. (Best-fit interpretation: **B**id-**P**rice-**C**hart-**T**racker, **B**reakout-**P**oint-**C**ondition-**T**racker, or similar. RESEARCH §2 BPCT's three candidates remain plausible but the HUD-style nature points to a "Tracker" semantic.)

| Input | Default | Type | Confirmed |
|-------|---------|------|-----------|
| Corner_of_Chart | RIGHT_TOP | enum | ✓ |
| Show_Price | true | bool | ✓ |
| Show_Xtra_Details | true | bool | ✓ |
| Show_Smaller_Size | true | bool | ✓ |
| Show_Trade_Pips | true | bool | ✓ |
| Shift_UP_DN | 0 | int | ✓ |
| Adjust_Side_to_side | 0 | int | ✓ |
| Comment | (empty) | string | ✓ |
| Label_color | White | color | ✓ |
| Spread_color | Gold | color | ✓ |
| Price_Up_color | Lime | color | ✓ |
| PriceDn_color | Crimson | color | ✓ |
| Price_At_Extreme_color | Dark Green | color | ✓ |
| Distance_From_Extreme | 12.0 | double | ✓ |
| HOD_LOD_Alert | false | bool | ✓ |
| Pips_To_HOD_LOD_For_Alert | 5.0 | double | ✓ |

**Confidence elevation:** SM_BPCT.md should drop most `[INFER:guess]` tags on input names and defaults. Algorithm internals (how the rolling HOD/LOD is computed) remain `[INFER]` — only Inputs are confirmed. Confidence can move from **Low → Medium**.

---

## 2. SM_TDI — Inputs Confirmed (was Confidence: High)

**CRITICAL CORRECTION: `RSI_Period = 21`, not 13.** This contradicts the MMM TDI Tradestation PDF default. The Phase 11 spec's "RSI=13" claim was wrong for this specific implementation.

| Input | Default | Type | Confirmed | Notes |
|-------|---------|------|-----------|-------|
| RSI_Period | **21** | int | ✓ | **Spec said 13 — corrected** |
| RSI_Price | 0 | int | ✓ | (0 = close, MQL `PRICE_CLOSE`) |
| Volatility_Band | 34 | int | ✓ | Bollinger period |
| RSI_Price_Line | 2 | int | ✓ | RSI_PL (Green) — 2-period SMA |
| RSI_Price_Type | 0 | int | ✓ | (0 = SMA) |
| Trade_Signal_Line | 7 | int | ✓ | TSL (Red) — 7-period SMA |
| Trade_Signal_Type | 0 | int | ✓ | (0 = SMA) |
| Shark_Fin_Alert | false | bool | ✓ |  |
| Shark_Fin_Upper_Level | 63.0 | double | ✓ | **NOT 68 — corrected** |
| Shark_Fin_Lower_Level | 37.0 | double | ✓ | **NOT 32 — corrected** |
| Squeeze_Alert | false | bool | ✓ |  |
| Squeeze_Entry_Alert | false | bool | ✓ |  |
| VB_High_Value | 45.0 | double | ✓ | New parameter not in spec |
| VB_Low_Value | 55.0 | double | ✓ | New parameter not in spec |
| Pop_Up_Alert | false | bool | ✓ |  |
| Draw_MBL_Slope | false | bool | ✓ | MBL slope visualization toggle |
| Sensitivity | 0.0001 | double | ✓ | Probably alert-trigger epsilon |

**Levels tab confirmed:** Fixed minimum = 19.2182, Fixed maximum = 77.5613 (so the y-axis spans roughly the typical RSI range but slightly truncated, not 0-100).

**Bollinger StdDev multiplier:** NOT visible in Inputs tab — likely hard-coded internally. The MMM TDI Tradestation PDF cites 1.6185, but this build may differ. Remains `[INFER]`.

**Confidence elevation:** SM_TDI.md inputs section should be fully rewritten with these confirmed values. Confidence stays **High** but the spec needs material correction.

---

## 3. SM_ADR_Marker — Inputs Confirmed (was Confidence: High formula / Medium params)

**CORRECTION: `ATRPeriod = 14`, not 20.** Phase 11 spec's "ADR(20)" assumption was wrong. Default is the standard ATR period (14), not the longer 20 day period.

| Input | Default | Type | Confirmed | Notes |
|-------|---------|------|-----------|-------|
| TimeZoneOfData | 0 | int | ✓ | Hours |
| TimeZoneOfSession | 0 | int | ✓ | Hours |
| ATRPeriod | **14** | int | ✓ | **Spec said 20 — corrected** |
| UseManualADR | false | bool | ✓ |  |
| ManualADRValuePips | 0 | int | ✓ | Used only if UseManualADR=true |
| LineStyle | 2 | int | ✓ | (MQL STYLE_DOT) |
| LineThickness1 | 1 | int | ✓ |  |
| LineColor1 | Orange | color | ✓ | First line (likely upper marker) |
| LineThickness2 | 2 | int | ✓ |  |
| LineColor2 | Red | color | ✓ | Second line (likely lower marker or full-ADR) |
| BarForLabels | -10 | int | ✓ | Negative = label offset to right of last bar |
| DebugLogger | false | bool | ✓ |  |
| showtext | false | bool | ✓ | Toggle for label text display |

**Confidence:** Stays **High**. Inputs section needs correction (ATR=14, plus the manual-override + timezone + label-offset inputs that weren't in our spec).

---

## 4. SM_NewHUD — Field Set Confirmed (was Confidence: Low for internals)

**18+ visible HUD fields confirmed** from the chart-overlay screenshot. Phase 11 spec listed 10; the actual is more. New ADR variants beyond what we spec'd: **HYADR** (Half-Yearly ADR) — not in our list.

### Confirmed visible fields (chart overlay)

| Field | Description | Phase 11 spec? |
|-------|-------------|----------------|
| ASK / BID | Current bid/ask quote | Implicit (Spread) |
| spread (in pips) | E.g., "1.8" | ✓ |
| HOD + distance from current | E.g., "HOD 2.31540: 25" | ✓ |
| LOD + distance from current | E.g., "LOD 2.30885: 41" | ✓ |
| TDR | Today's Daily Range | ✓ as ADR |
| YDR | Yesterday's Daily Range | ✗ NEW |
| WADR | Weekly ADR | ✗ NEW |
| MADR | Monthly ADR | ✗ NEW |
| HYADR | **Half-Yearly ADR** | ✗ NEW |
| PTO | Price-To-Open (distance) | ✗ NEW |
| WH + distance | Week High | ✗ NEW |
| WL + distance | Week Low | ✗ NEW |
| WR | Weekly Range | ✗ NEW |
| MWR | Monthly Weekly Range avg | ✗ NEW |
| 3MWR | 3-Month Weekly Range avg | ✗ NEW |
| 6MWR | 6-Month Weekly Range avg | ✗ NEW |
| 3xADR | 3x ADR multiple alert | ✗ NEW |
| Candle Time | countdown to next candle | ✓ |

### Confirmed inputs (from params 1 + params 2 screenshots)

**HUD settings:**
- Code_Version: 1
- MaxSpread: 1.75
- Range_Today_Text / Range_Yest_Text / Range_Week_Text: TDR / YDR / WR (the labels shown on the HUD)
- FontSize: 9, FontColor: White
- Symbol_FontColor: Black, Symbol_Font_Size: 14
- PriceColor: Black
- Font_SizeADR3: 9, FontColorADR3: Yellow
- Show_4Digit_Price: false (so 5-digit pricing default)
- ColorLast_Digit: false, LastDigitColor: 90,90,90 (RGB gray)

**HiLo alert thresholds:**
- HiLoAlert_Distance1: 10 pips (warn)
- HiLoAlert_Distance2: 20 pips (alert)
- HOD/LOD AlertClr: Dark Green; NearClr: LawnGreen

**Week HiLo alert thresholds:**
- Week_HiLo_Alert_Distance3: 25 pips
- Week_HiLo_Alert_Distance4: 50 pips

**ADR alert:**
- adrAlert_Distance: 10
- 3 sets of color pairs: wadr (weekly), madr (monthly), hyadr (half-yearly) — each with AlertColorHi/Lo + ExceedColorHi/Lo

**Background settings:**
- UseDark_Background: false
- BackgroundColor: Gray
- BackgroundSize: 120
- XL_Background_for_News: true
- Overview_Mode: false
- Trade_Track_Mode: false

**Average periods (Av_N):**
- y: 18, y_distance: 0
- Av_1: 0, Av_2: 1, Av_3: 4, Av_4: 13, Av_5: ?, Av_6: 26 (and 52 visible at end)
- These are **likely EMA periods** displayed on the HUD (Fibonacci-like: 1, 4, 13, 26, 52)

**Confidence elevation:** SM_NewHUD.md should be substantially expanded — field list goes from 10 to 18+, add HYADR, add the rolling-Av_N section, add the alert distance scheme. Confidence moves from **Low → Medium** for inputs but stays **Low** for true internals (the iCustom calls + decision logic).

---

## 5. !_boxes — Tangentially captured (NOT one of our 14 specs)

The "gmtoffset" Drive folder also contained screenshots of the `!_boxes.ex4` indicator (third-party, not in our 14). Captured here for completeness — `!_boxes` references `!sm_WorkTime v2.0` in its Version field, **confirming** that `_boxes` depends on `sm_WorkTime`. This validates the dependency graph in INDEX.md (sm_WorkTime is the foundational session-times helper that other indicators consume).

`!_boxes` is a session-overlay drawer (Asian box, NY box, London Shadow box, NY Shadow box, Stop Hunt box, EMA-50/200/800 alerts). Not in the Phase 11 spec scope, so not documented further.

---

## 6. Open questions still unresolved

| Question | Status |
|----------|--------|
| BPCT abbreviation expansion | Still `[INFER:guess]` — function confirmed (mini-HUD), but the actual spelled-out form is not visible in any captured dialog. SM_BPCT.md keeps abbreviation candidates. |
| TDI Bollinger StdDev (1.6185 vs 2.0) | Not in Inputs tab — likely hardcoded. Stays `[INFER]`. |
| AlertZone_1 vs _2 difference | Not screenshotted — still untested. `[INFER]` retained. |
| sm_gmtoffset publish mechanism (GlobalVariable vs include) | Not screenshotted — chart overlay returned empty OCR. `[INFER]` retained. |
| Helper: sm_WorkTime / sm_WorkTime_no_autogmt | Not screenshotted directly (the "gmtoffset" folder showed `!_boxes` instead). `[INFER]` retained. |
| SM_NewHUD `iCustom` calls | Not visible from Inputs/chart screenshots alone. Would need MetaEditor "Indicators Used" inspection. `[INFER]` retained. |

---

## 7. Spec update plan

The following specs need targeted edits to incorporate this evidence:

1. **SM_BPCT.md** — rewrite Inputs section with the 16 confirmed parameters. Drop ~30 of the 41 `[INFER:guess]` tags (algorithm internals stay tagged). Confidence: Low → Medium.
2. **SM_TDI.md** — RSI_Period: 13 → 21. Add Shark_Fin / Squeeze / VB / Sensitivity inputs. Update test cases that referenced RSI=13.
3. **SM_ADR_Marker.md** — ATRPeriod: 20 → 14. Add TimeZone + Manual override + label-offset inputs.
4. **SM_NewHUD.md** — expand field set from 10 to 18, add HYADR, add Av_N averages, add alert-distance inputs section, add background settings.

Each updated spec must re-pass `bash check_spec.sh <path>` (12-section conformance preserved).

Each updated spec gets a "Verified 2026-04-27" note in the Header citing this evidence file path.
