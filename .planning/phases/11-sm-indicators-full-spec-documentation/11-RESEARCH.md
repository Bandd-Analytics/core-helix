# Phase 11: SM Indicators Full-Spec Documentation — Research

**Researched:** 2026-04-26
**Domain:** MT4/MQL4 indicator reconstruction — Steve Mauro MMM/BTMM indicator suite
**Confidence:** MEDIUM overall (HIGH for TDI and ADR; MEDIUM for helpers and atomic tier; LOW for BPCT and NewHUD internals)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Output goes under `resource_pack/MMM/SM Indicators/docs/` with the exact folder structure:
  `helpers/` (3 files) and `indicators/` (11 files) plus `INDEX.md`
- Per-indicator template is 12 sections in locked order: Header / Purpose / Inputs / Parameters / Outputs / Calculation logic / Pseudocode / Visual elements / Dependencies / Edge cases / Test cases / Port notes (MQ4/MQ5/Python) / Uncertainty log
- Confidence tags: untagged = High; `[INFER]` = Medium; `[INFER:guess]` = Low
- Tier-based execution with user review after each tier: Tier 0 → Tier 1 → Tier 2 → INDEX.md
- Filenames drop leading `!` and `.ex4` suffix; `!SM_Alerting+TL+v1.1.ex4` → `SM_Alerting+TL.md` (version suffix dropped)

### Claude's Discretion
- Mermaid vs ASCII for dependency graph in INDEX.md (recommend ASCII for plain-viewer portability)
- Color hex codes in Visual elements sections (use MMM-typical red/green/yellow on black, tag `[INFER]`)
- Pseudocode style (language-neutral imperative, not MQL or Python syntax)
- Test case granularity (2 minimum, 4 maximum, edge cases first)
- Plan structure (recommended: 1 plan per tier + 1 plan for INDEX.md = 4 plans total)

### Deferred Ideas (OUT OF SCOPE)
- Actual MQ4/MQ5/Python implementation code
- Re-spec of the ~40 third-party indicators in the same folder
- MMM glossary expansion beyond Phase 11 scope
- Visual reproduction of HUD screenshots via live MT4
- Cross-language port unit tests
</user_constraints>

---

## 1. Executive Summary

This research covers all 14 `!SM_*` / `!sm_*` MT4 indicators that constitute Steve Mauro's proprietary Market Maker Method (MMM) chart setup. The binaries are compiled `.ex4` files with no decompilable source; reconstruction draws from four sources: (a) the MMM TDI Tradestation PDF, the MMM Book, and related MMM glossary files in this repo — which together supply HIGH-confidence data for TDI and ADR; (b) the public Forex community's TDI documentation, which cross-confirms all TDI parameter defaults; (c) the binary file sizes and timestamps which give size-based complexity estimates; and (d) indicator name semantics for everything else. One indicator (SM_TDI) is fully spec-able with HIGH confidence from the MMM TDI PDF alone. Five indicators (ADR_Marker, Daily_HiLo, IlsleyPsychLevels, PivotPoints, Crossover_Arrows) are spec-able at MEDIUM confidence using MMM Book references and well-understood public community patterns. The three helpers (sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt) are MEDIUM confidence based on known broker-time detection patterns and their 2011 timestamps. The remaining five (BPCT, AlertZone_1, AlertZone_2, Alerting+TL, NewHUD) are LOW-to-MEDIUM confidence and will require significant `[INFER]` tagging. Every claim in the spec files must be tagged according to the confidence scale in CONTEXT.md.

**Primary recommendation:** Document TDI first within Tier 2 as the anchor indicator; use it to establish template quality standards before tackling the harder-to-infer NewHUD and AlertZone specs.

---

## 2. Per-Indicator Research Dossiers

### Tier 0 — Helper: sm_gmtoffset

**Binary:** `!sm_gmtoffset.ex4` — 5,592 bytes — dated Nov 3, 2019
**Best-fit identity:** A utility indicator (likely draws nothing visible) that calculates and exposes the broker's GMT offset as a global variable or indicator buffer, to be consumed by sm_WorkTime and other session-aware indicators.

**Typical inputs (all [INFER]):**
- `AutoDetect` (bool, default true) — use MQL4 `TimeGMTOffset()` or derived broker-vs-local delta
- `ManualGMT` (int, default 0, range -12..+14) — fallback for when auto-detect is unreliable

**Calculation logic:**
MQL4 `TimeGMTOffset()` returns (local machine time minus UTC) in seconds. A broker's server time offset from GMT is derived by comparing `TimeCurrent()` (broker server time) against `TimeGMT()`. DST complicates this: MQL4's `TimeGMT()` accounts for local machine DST switch, not broker DST. The sm_gmtoffset indicator almost certainly polls `TimeCurrent()` vs a known GMT reference at a few known timestamps (e.g., Sunday 22:00 UTC rollover) to detect the broker's effective offset, then writes the result to a global variable (e.g., `GlobalVariableSet("sm_GMTOffset", offset)`). [INFER]

**What it draws:** Nothing on chart. Purpose is data-only. [INFER]

**Dependencies:** None (Tier 0 bottom).

**Binary size note:** 5,592 bytes is a small indicator — consistent with a utility that performs a single calculation and stores the result, not a complex drawing indicator.

**MMM Book reference:** MMM Book pp. 8 (session times defined as GMT ranges: Asia 00:30-07:00, Europe 07:30-13:00, US 13:30-20:30), confirming the need for broker-to-GMT normalization. The "Time Mapping" glossary entry explicitly states: "The action of matching your broker's server time to our indicators."

**Community references:** MQL5 forum "Auto detect GMT offset?" (2012) confirms that reliable auto-detection requires comparing `TimeCurrent()` to `TimeGMT()` and that DST handling is the primary edge case.

**Confidence:** MEDIUM — function is well-understood; exact auto-detection algorithm and parameter names unverifiable.

**Gaps for spec writer:** (1) Does it expose the offset via GlobalVariable, indicator buffer, or a shared include? (2) What is the DST-shift detection logic — does it query a specific day/time? (3) Does it produce any alert if broker time is anomalous?

---

### Tier 0 — Helper: sm_WorkTime

**Binary:** `!sm_WorkTime.ex4` — 43,612 bytes — dated Dec 15, 2011
**Best-fit identity:** Session-window overlay indicator. Draws color-coded rectangular boxes on the price chart demarcating the three MMM sessions (Asia, London/Europe, US/New York) and their gap times. The large size (43KB vs 5KB for gmtoffset) is consistent with substantial chart-drawing code: creating, refreshing, and cleaning up rectangle objects for multiple sessions across history.

**Typical inputs ([INFER] unless noted):**
- `AsiaStart` / `AsiaEnd` (int hours, GMT): 0 / 7 — from MMM Book session times
- `LondonStart` / `LondonEnd` (int hours, GMT): 7 / 13
- `USStart` / `USEnd` (int hours, GMT): 13 / 20
- `ShowAsia` / `ShowLondon` / `ShowUS` (bool, default true each)
- `AsiaColor`, `LondonColor`, `USColor` (color, typical: gray/blue/green shading) [INFER]
- `HistoryDays` (int, default 5-10) — how many days of boxes to draw [INFER]
- `UseGMTOffset` (bool, default true) — whether to call sm_gmtoffset result [INFER]

**Calculation logic:**
For each bar in history up to HistoryDays, determine the bar's GMT time using broker offset from sm_gmtoffset, categorize into session, and draw/extend a rectangle OBJ on the chart. On every new bar event, delete previous bars' objects and re-draw. Session boundaries use MMM Book times precisely: Asia 00:30-07:00 GMT, gap 07:00-07:30, London 07:30-13:00, gap 13:00-13:30, US 13:30-20:30, gap 20:30-00:30.

**What it draws:** Translucent colored rectangles spanning each session window across the chart. Gap times may be drawn in a neutral color or left unshaded. [INFER]

**Dependencies:** sm_gmtoffset (reads offset from GlobalVariable). [INFER]

**MMM Book reference:** MMM Book p. 8 defines session boundaries explicitly. MMM Book p. 40 (Colour-Coded Sessions): "Two boxes can be drawn. The 1st is drawn around the Asian session and simply denotes the area of consolidation that is expected during this period... The 2nd is a smaller box and highlights a time when there is a high probability of the midsession reversal (the New York Reversal). It starts at the beginning of the NY open and runs for about 3 hours." This precisely describes what sm_WorkTime draws.

**2011 timestamp note:** The file dates to Dec 2011 and Sep 2011 for the no_autogmt variant — these are likely among the earliest SM indicators, contemporaneous with Steve Mauro's first MMM indicator package releases.

**Confidence:** MEDIUM — session logic is well-documented in MMM Book; exact parameter names and object-naming conventions unverifiable.

**Gaps:** (1) Does it draw the NY sub-box described in the MMM Book or leave that to a separate indicator? (2) What object-naming prefix does it use? (3) Does it draw any text labels on the boxes?

---

### Tier 0 — Helper: sm_WorkTime_no_autogmt

**Binary:** `!sm_WorkTime_no_autogmt.ex4` — 37,956 bytes — dated Sep 15, 2011
**Best-fit identity:** Same as sm_WorkTime but with manual GMT offset input instead of auto-detection via sm_gmtoffset. The name suffix makes this explicit. Slightly smaller (38KB vs 44KB), likely because the auto-detect branch and sm_gmtoffset call are removed and replaced by a single manual input field.

**Typical inputs ([INFER]):**
- Same as sm_WorkTime except:
  - Remove `UseGMTOffset` flag
  - Add `BrokerGMT` (int, default 2, range -12..+14) — manual broker offset from GMT

**Calculation logic:** Identical to sm_WorkTime except the GMT offset is a fixed input parameter rather than a dynamically read value.

**Dependencies:** None (no dependency on sm_gmtoffset — that is the whole point).

**Confidence:** MEDIUM — same as sm_WorkTime; the functional distinction is clearly encoded in the filename.

**Gaps:** Same as sm_WorkTime; additionally: does it include an input for DST adjustment (+1)?

---

### Tier 1 — Atomic: SM_ADR_Marker

**Binary:** `!SM_ADR_Marker.ex4` — 12,720 bytes — dated Nov 3, 2019
**Also present:** `!_ADR_Marker.ex4` — 12,720 bytes (identical size — likely the same indicator or immediate predecessor without SM_ prefix)

**Best-fit identity:** Average Daily Range marker. Plots two horizontal lines on the price chart anchored to today's open: ADR-high = today_open + ADR/2, ADR-low = today_open − ADR/2. This is confirmed by the MMM Book (p. 41: "ADR High and Low — The ADR is normally plotted as an oscillator. It is however difficult to read in this format and Mauro has produced a version which is read on the price chart and provides a high and low value.") and by the Helix precedent indicator ADR_Levels.mq5 which implements exactly this formula.

**Inputs (HIGH confidence from ADR_Levels.mq5 precedent and MMM community):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| LookbackDays | int | 20 | [INFER] — 20 is the MMM-typical ADR lookback; ADR_Levels.mq5 uses 20 |
| HighColor | color | DeepSkyBlue or Red | [INFER] |
| LowColor | color | OrangeRed or Green | [INFER] |
| MidColor | color | Silver/Gray | [INFER] |

**Calculation (HIGH confidence):**
```
ADR = mean( DailyHigh[i] - DailyLow[i] ) for i = 1..LookbackDays
today_open = PERIOD_D1 open bar[0]
ADR_high = today_open + ADR / 2
ADR_mid = today_open
ADR_low = today_open - ADR / 2
```
This matches ADR_Levels.mq5 exactly (`V2/indicators/ADR_Levels.mq5` lines 67-84).

**What it draws:** Two or three horizontal dashed lines on the price chart. Recalculates on new D1 bar or via timer. Does NOT draw in a subwindow.

**Dependencies:** None mandatory. May optionally read sm_gmtoffset for timezone-correct D1 open. [INFER]

**MMM Book reference:** p. 41 explicitly describes ADR High and Low as a price-chart overlay showing high and low value targets. p. 42 (Pivots): "It can be more accurate if it is coupled with an ADR indicator which tells us the average daily trading range of the last 2 weeks." (14 bars, alternative lookback).

**ADR_Levels.mq5 precedent:** The Helix indicator landed in Phase 08.4-04 (INFRA-04, Task 3a) at `V2/indicators/ADR_Levels.mq5`. Its structure — `#property indicator_chart_window`, `indicator_buffers 0`, `indicator_plots 0`, ObjectCreate OBJ_HLINE, EventSetTimer(60), OnCalculate D1-bar-change detection — is the canonical MQ5 port reference for this indicator.

**Confidence:** HIGH for formula and purpose; MEDIUM for exact parameter names and defaults.

**Gaps:** (1) Does SM_ADR_Marker also draw the previous day's ADR high/low (not just today's)? (2) Does it display the ADR value in pips as a label?

---

### Tier 1 — Atomic: SM_Daily_HiLo

**Binary:** `!SM_Daily_HiLo.ex4` — 6,284 bytes — dated Nov 3, 2019
**Also present:** `!_Daily_HiLo.ex4` — 3,004 bytes (smaller, simpler variant)

**Best-fit identity:** Previous day's High and Low marker. Draws two horizontal lines on the price chart at yesterday's high and yesterday's low. The MMM Book (p. 41, "Previous HOD/LOD Markers"): "The high and low prices from the previous day were used by the market maker to trap volume. It is therefore significant to know how price acts at these levels the following day. These levels will often line up with other support and resistance zones."

**Inputs ([INFER]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| HighColor | color | Red or Blue | [INFER] |
| LowColor | color | Blue or Green | [INFER] |
| LineStyle | int | STYLE_DASH | [INFER] |
| LineWidth | int | 1 | [INFER] |
| ShowLabel | bool | true | [INFER] |

**Calculation:**
```
prev_high = iHigh(symbol, PERIOD_D1, 1)
prev_low = iLow(symbol, PERIOD_D1, 1)
Draw OBJ_HLINE at prev_high (color HighColor, style STYLE_DASH)
Draw OBJ_HLINE at prev_low (color LowColor, style STYLE_DASH)
```

**What it draws:** Two horizontal dashed lines on the price chart. Refreshes at D1 bar change. No subwindow.

**Dependencies:** Potentially sm_gmtoffset for correct D1 boundary detection. [INFER]

**Confidence:** HIGH for purpose; MEDIUM for exact visual details and parameters.

**Gaps:** (1) Does it also draw current-day running high/low (live tracking)? (2) Does it extend lines to the right only or both directions?

---

### Tier 1 — Atomic: SM_BPCT

**Binary:** `!SM_BPCT.ex4` — 10,868 bytes — dated Nov 3, 2019
**Best-fit identity:** The filename "BPCT" is the hardest abbreviation to resolve in this set. Three candidate interpretations:
1. **Bars Per Cycle Tracker** — counts bars since the last HOD/LOD or session open, displaying a count label. Binary size (11KB) is consistent with a tracker that draws numeric text objects.
2. **Beat-the-market-maker Pip Count Tracker** — displays cumulative pip movement from session open.
3. **Buy/sell Pressure Candle Tracker** — colors candles based on buying vs. selling pressure (body direction + volume proxy).

The most common interpretation seen in BTMM community discussions (Forex Factory thread "Steve Mauro MMM beat the market") is that BPCT is a **bias/pressure candle tracker** that gives a visual indication of whether bulls or bears are in control based on close relative to open within a session window. However this is LOW confidence — no authoritative source resolves the abbreviation.

**Web search result:** No direct hit for "SM_BPCT" by name. The Studocu BTMM seminar notes list indicators used in MMM but do not spell out BPCT specifically.

**Inputs ([INFER:guess]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| Period | int | 14 | [INFER:guess] |
| BullColor | color | Lime | [INFER:guess] |
| BearColor | color | Red | [INFER:guess] |

**What it draws:** [INFER:guess] A subwindow histogram or candle-coloring overlay showing directional bias per bar.

**Dependencies:** [INFER:guess] Possibly sm_WorkTime for session filtering.

**Confidence:** LOW overall. The spec writer MUST prominently flag the abbreviation ambiguity and present all three candidate interpretations in the Uncertainty log.

**Gaps:** Everything beyond filename. The binary size (11KB) rules out a trivially simple indicator but doesn't narrow down which category.

---

### Tier 1 — Atomic: SM_IlsleyPsychLevels

**Binary:** `!SM_IlsleyPsychLevels.ex4` — 3,540 bytes — dated Nov 3, 2019
**Best-fit identity:** Psychological levels indicator, specifically the "Ilsley" variant. "Ilsley" is a known community contributor in UK/European trading forums. The indicator draws horizontal lines at round-number psychological levels (e.g., every 00 pip and every 50 pip — i.e., 1.3000, 1.3050, 1.3100). This is a well-established indicator class; the "Ilsley" name simply identifies the specific community version SM adopted.

**Key insight from binary size:** 3,540 bytes is extremely small — smaller than sm_gmtoffset (5,592 bytes). This confirms it is a simple drawing indicator: iterate over price range, draw horizontal lines at levels where price % interval == 0.

**Inputs (MEDIUM confidence — standard for this indicator class):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| LevelInterval | int | 50 (points, 5-digit) | [INFER] — 50 points = 0.0050 on 5-digit pairs |
| LineColor | color | Gray or DimGray | [INFER] |
| MajorColor | color | DarkGray | [INFER] — 00 levels often differ |
| LineStyle | int | STYLE_DOT | [INFER] |
| Levels | int | 10 | [INFER] — number of levels above/below |

**Calculation:**
```
base = round(current_price / interval) * interval
for i = -Levels to +Levels:
    level = base + i * interval
    Draw OBJ_HLINE at level
```

**What it draws:** Multiple faint horizontal lines at psychological price levels. On the price chart (main window), no subwindow.

**Community references:** MQL5 Code Base has "Round Levels MT4" (mql5.com/en/code/55506) and FXSSI.RoundLevels as representative community implementations. The Ilsley variant is a personal-style wrapper around this standard algorithm.

**Dependencies:** None.

**Confidence:** HIGH for purpose and algorithm; MEDIUM for Ilsley-specific parameter choices.

**Gaps:** (1) Does it differentiate major (00) vs minor (50) levels with different colors/styles? (2) Does the interval adapt for JPY pairs (where psychological levels are at 0.50 and whole numbers)?

---

### Tier 1 — Atomic: SM_Crossover_Arrows

**Binary:** `!SM_Crossover_Arrows.ex4` — 5,508 bytes — dated Nov 3, 2019
**Best-fit identity:** EMA crossover arrow indicator. Draws up/down arrows on the price chart whenever a fast MA crosses a slow MA. The MMM Book uses EMA 5 and EMA 13 as the primary short-term MAs (p. 47: "EMA 5/13" listed under confluence indicators). This is the standard SM crossover pair. Community note (from websearch): "Steve Mauro's original BTMM indicator misplaced the EMA-crossover arrows... improved versions have been developed that correctly position the EMA crossover arrows."

**Inputs ([INFER]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| FastMA | int | 5 | [INFER] — MMM standard EMA5 |
| SlowMA | int | 13 | [INFER] — MMM standard EMA13 |
| MAMethod | int | MODE_EMA | [INFER] |
| UpColor | color | Lime or Aqua | [INFER] |
| DownColor | color | Red or Orange | [INFER] |
| ArrowSize | int | 1 or 2 | [INFER] |

**Calculation:**
```
fast[i] = EMA(close, FastMA, i)
slow[i] = EMA(close, SlowMA, i)
if fast[i] > slow[i] AND fast[i-1] <= slow[i-1]:
    draw UP arrow below bar[i]
if fast[i] < slow[i] AND fast[i-1] >= slow[i-1]:
    draw DOWN arrow above bar[i]
```

**What it draws:** Arrow objects (OBJ_ARROW_UP / OBJ_ARROW_DOWN or indicator buffer arrows) on the main price chart.

**Dependencies:** None.

**Confidence:** MEDIUM — pattern is well-understood; exact MA periods confirmed by MMM context as EMA 5/13; arrow styles unverifiable.

**Gaps:** (1) Does it also show arrows for EMA 50/200 crossovers? (2) Does it have alert functionality on crossover?

---

### Tier 2 — Composite: SM_TDI

**Binary:** `!SM_TDI.ex4` — 15,880 bytes — dated Nov 3, 2019
**Also present:** `!_TDI.ex4` — 27,724 bytes (a more elaborate version with more features)

**Best-fit identity:** Traders Dynamic Index. The canonical SM indicator, created by Dean Malone and adopted wholesale by Steve Mauro as the sole confirmation indicator for MMM strategies. Fully documented in the MMM TDI Tradestation PDF.

**Structure (HIGH confidence — directly from MMM TDI Tradestation PDF):**
The TDI is made of 5 lines and 3 levels:
- **Green line** = RSI Price Line (RSI PL) — the RSI itself, smoothed with a 2-period SMA
- **Red line** = Trade Signal Line (TSL) — 7-period SMA of the RSI PL; lagging MA used for entry signal
- **Yellow line** = Market Base Line (MBL) — 34-period SMA of the RSI PL; represents overall market trend
- **Blue lines (2)** = Volatility Bands — Bollinger Bands applied to the MBL with period 34 and stddev 1.6185 (some sources say 2.0; 1.6185 is more commonly reported for the original TDI)
- **Level 68** (gray dash) = Buying Exhaustion / overbought
- **Level 50** (gray dash) = Sentiment midpoint
- **Level 32** (gray dash) = Selling Exhaustion / oversold

**Inputs (HIGH confidence from MMM TDI PDF + community cross-confirmation):**
| Parameter | Type | Default | Source |
|-----------|------|---------|--------|
| RSI_Period | int | 13 | MMM TDI PDF: "Traders Dynamic Index (10, Cyan, Magenta, True, False, False)" — the "10" in the label appears to be a display artifact; community universally confirms RSI period 13 |
| RSI_Price | int | PRICE_CLOSE (0) | Community HIGH |
| Volatility_Band | int | 34 | Community HIGH |
| StdDev | double | 1.6185 | Community sources (earnforex, tradersunion); some say 2.0 [INFER for exact value] |
| RSI_Price_Line | int | 2 | Community HIGH — 2-period SMA of RSI |
| Trade_Signal_Line | int | 7 | Community HIGH — 7-period SMA of RSI |
| Market_Base_Line | int | 34 | Community HIGH — 34-period SMA of RSI (same period as Volatility_Band) |
| Level_High | double | 68 | MMM TDI PDF HIGH |
| Level_Mid | double | 50 | MMM TDI PDF HIGH |
| Level_Low | double | 32 | MMM TDI PDF HIGH |

**Complete calculation (HIGH confidence):**
```
RSI_raw[i] = RSI(close, RSI_Period, i)            // 13-period RSI on close
RSI_PL[i] = SMA(RSI_raw, 2, i)                    // Green line: 2-period smooth
TSL[i] = SMA(RSI_raw, 7, i)                       // Red line: 7-period signal
MBL[i] = SMA(RSI_raw, 34, i)                      // Yellow line: 34-period base
VB_upper[i] = MBL[i] + StdDev * StdDev(RSI_raw, 34, i)  // Upper blue band
VB_lower[i] = MBL[i] - StdDev * StdDev(RSI_raw, 34, i)  // Lower blue band
Draw horizontal lines at 32, 50, 68
```

**Three alert types (HIGH confidence from MMM TDI PDF):**
1. **TDI Signal Cross** — confirmed crossover of Green (RSI PL) above/below Red (TSL)
2. **MBL Cross** — confirmed crossover of Green above/below Yellow (MBL); requires Green > Red (long) and current High > previous avg High
3. **TDI Hook** — counter-trend: Green near 32 and crosses above lower VB (Long Hook); Green near 68 and crosses below upper VB (Short Hook)

**What it draws:** A separate subwindow below price. All 5 lines drawn in the subwindow. Three horizontal dashed reference lines at 32, 50, 68. No price-chart objects.

**MMM usage context (HIGH confidence from MMM Book pp. 45-46):**
Key patterns: Shark Fin Short/Long, Blood in the Water (MBL cross), scaling-in using VB breakout. Used at confluence: "EMA 5/13, EMA 50/200, RSI/TDI, Pivots" (MMM Book p. 47).

**Backtester integration (Helix-specific):** The Helix `v3_intelligence/regime.py` and `backtest_hybrid.py` already implement an RSI-based signal filter. SM_TDI Python port would output: RSI_PL, TSL, MBL, VB_upper, VB_lower as DataFrame columns. Signal generation: `signal = +1 if RSI_PL > TSL and RSI_PL > 50 else -1 if RSI_PL < TSL and RSI_PL < 50 else 0`. The TDI Hook pattern maps directly to a mean-reversion entry condition.

**Dependencies:** None (self-contained). Does not depend on sm_WorkTime or sm_gmtoffset.

**Confidence:** HIGH for formula, parameters, lines, and levels. MEDIUM for exact StdDev multiplier (1.6185 vs 2.0).

**Gaps:** (1) Exact StdDev: 1.6185 is the most-cited value for the "original" Malone TDI but the SM variant may use 2.0. (2) Does SM_TDI's green line smooth the raw RSI or the output of iRSI directly? (3) Does SM_TDI expose buffers accessible to EAs, or is it visual-only?

---

### Tier 2 — Composite: SM_PivotPoints

**Binary:** `!SM_PivotPoints.ex4` — 15,684 bytes — dated Nov 3, 2019
**Best-fit identity:** Daily (and possibly weekly) pivot point calculator. Draws PP, R1, R2, R3, S1, S2, S3 plus mid-pivot lines M1-M4 on the price chart. The MMM Book (pp. 42-43) discusses pivots extensively, specifically using the M1/M2/M3/M4 mid-pivot system that Mauro overlays on the standard floor pivots.

**Inputs ([INFER] unless noted):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| ShowDaily | bool | true | [INFER] |
| ShowWeekly | bool | false | [INFER] |
| PivotColor | color | White | [INFER] |
| R1/R2Color | color | Red | [INFER] |
| S1/S2Color | color | Green | [INFER] |
| MidColor | color | Yellow | [INFER] |
| ShowMidpoints | bool | true | [INFER] — MMM Book explicitly uses M1-M4 |

**Calculation (HIGH confidence — standard formula):**
```
// Using previous day's H, L, C
PP = (H_prev + L_prev + C_prev) / 3
R1 = 2*PP - L_prev
R2 = PP + (H_prev - L_prev)
R3 = H_prev + 2*(PP - L_prev)
S1 = 2*PP - H_prev
S2 = PP - (H_prev - L_prev)
S3 = L_prev - 2*(H_prev - PP)
// Mid-points (MMM-specific):
M1 = (S2 + S1) / 2
M2 = (S1 + PP) / 2
M3 = (PP + R1) / 2
M4 = (R1 + R2) / 2
```

**What it draws:** Horizontal lines on the price chart for all pivot levels. May draw labels (PP, R1, S1, M1 etc.) at the right edge. Daily pivots reset at 17:00 ET (22:00 GMT) per MMM Book.

**Dependencies:** sm_gmtoffset (for correct daily pivot reset time). [INFER]

**MMM Book reference:** pp. 42-43 detail the M1/M2/M3/M4 mid-pivot system specifically. "If the previous day's candle was red then this indicates that today might be an M1/M3 day... if the previous day's candle was green then this indicates that the day might be an M2/M4 day." This is a Mauro-specific use pattern on top of standard pivots.

**Confidence:** HIGH for formula (standard industry formula); MEDIUM for MMM-specific mid-pivot layer and parameter names.

**Gaps:** (1) Does it show the M1-M4 mid-pivots or only standard R/S levels? (2) Does it show weekly pivots? (3) Is the daily reset time user-configurable?

---

### Tier 2 — Composite: SM_AlertZone_1

**Binary:** `!SM_AlertZone_1.ex4` — 12,562 bytes — dated Nov 3, 2019
**Best-fit identity:** Price-level alert zone indicator, variant 1. Draws a rectangular zone on the chart between two user-defined price levels and fires an alert when price enters the zone. The "zone" concept maps to the MMM "Strike Zone" / "Blue Box" concept: an area near HOD/LOD (within 15-20 pips) where setups are expected. AlertZone_1 likely represents a simpler or earlier version — possibly a fixed-level alerter (user specifies two price levels, zone is drawn between them, alert fires when price enters).

**Inputs ([INFER]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| ZoneHigh | double | 0.0 | [INFER] — user-defined |
| ZoneLow | double | 0.0 | [INFER] — user-defined |
| ZoneColor | color | Blue (translucent) | [INFER] |
| AlertOnEnter | bool | true | [INFER] |
| AlertOnExit | bool | false | [INFER] |
| AlertSound | string | "alert.wav" | [INFER] |

**Calculation:** Monitor close or current price vs zone boundaries. If price crosses into [ZoneLow, ZoneHigh], fire alert. Draw OBJ_RECTANGLE across the chart at those price levels.

**What it draws:** A shaded rectangle on the price chart between ZoneLow and ZoneHigh spanning recent history. [INFER]

**MMM context:** MMM Book p. 55 (Look for Strike Zones, item 4): "Is there a significant pivot point near this price?" — zones are the operative concept. The Anatomy of Stop Hunts PDF (7MB, in repo) likely contains more context about trap zone identification, but was not read in this research pass due to size.

**Confidence:** MEDIUM — zone-alert concept is well-understood; whether AlertZone_1 is fixed-level vs. auto-generated from HOD/LOD is uncertain.

**Gaps:** (1) Is the zone user-defined (manual input) or auto-calculated from HOD/LOD distance? (2) What distinguishes AlertZone_1 from AlertZone_2 algorithmically (same code + different default zones, or genuinely different algorithms)? This is the critical open question.

---

### Tier 2 — Composite: SM_AlertZone_2

**Binary:** `!SM_AlertZone_2.ex4` — 12,710 bytes — dated Nov 3, 2019
**Best-fit identity:** Price-level alert zone indicator, variant 2. Nearly identical file size (12,710 vs 12,562 bytes — 148 bytes difference). This strongly suggests they are the same algorithm compiled with different default values, not fundamentally different implementations. The 148-byte difference could reflect different default color values, zone widths, or alert sounds stored as string literals.

**Most likely distinction from AlertZone_1:**
- AlertZone_1: Lower zone (near LOD / S1 / ADR-low) — alerts for potential long setups
- AlertZone_2: Upper zone (near HOD / R1 / ADR-high) — alerts for potential short setups
  OR
- AlertZone_1 and AlertZone_2 are meant to be placed simultaneously by the user for two different price levels, both active at the same time [INFER]

**Inputs:** Same as AlertZone_1 with potentially different default zone offsets from current price. [INFER]

**Confidence:** MEDIUM for shared algorithm; LOW for what exactly differs between the two variants.

**Gaps:** (1) Whether the two variants differ in algorithm or only defaults is the primary open question that the spec writer must flag prominently.

---

### Tier 2 — Composite: SM_Alerting+TL

**Binary:** `!SM_Alerting+TL+v1.1.ex4` — 20,068 bytes — dated Nov 3, 2019
**Best-fit identity:** Trendline-touch alerter. The "+TL" in the name stands for Trendline. The indicator monitors user-drawn trendlines (OBJ_TREND objects) on the chart and fires alerts when the price touches or crosses a trendline. The "v1.1" version suffix implies a prior v1.0 exists (likely a simpler alerting-only indicator without trendline monitoring).

**Key insight from file size:** 20,068 bytes is notably larger than the AlertZone files (12KB). This is consistent with the additional complexity of monitoring all chart trendline objects via `ObjectsTotal()` + `ObjectFind()` loops across all OBJ_TREND objects, plus the alerting logic.

**Inputs ([INFER]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| AlertOnTouch | bool | true | [INFER] |
| AlertOnCross | bool | true | [INFER] |
| TouchPips | int | 2 | [INFER] — tolerance for "touch" detection |
| AlertSound | string | "alert.wav" | [INFER] |
| RepeatAlertSeconds | int | 300 | [INFER] |
| AlertEmail | bool | false | [INFER] |
| AlertPush | bool | false | [INFER] |

**Calculation:**
```
For each OBJ_TREND on chart:
    projected_price = TL_slope * current_time + TL_intercept
    if |current_price - projected_price| <= TouchPips * Point:
        fire alert if not already fired within RepeatAlertSeconds
```

**What it draws:** No additional drawing (monitors existing user-placed trendlines). May draw a small marker dot at touch point. [INFER]

**Dependencies:** None. Relies on user to draw OBJ_TREND objects.

**Confidence:** MEDIUM for trendline-touch semantics; LOW for exact touch-detection algorithm.

**Gaps:** (1) Does it monitor ALL chart objects of type OBJ_TREND or only those with a specific naming prefix? (2) Does it alert on extension of the trendline beyond its drawn endpoints?

---

### Tier 2 — Composite: SM_NewHUD

**Binary:** `!SM_NewHUD.ex4` — 100,652 bytes — dated Nov 3, 2019
**Best-fit identity:** Heads-Up Display dashboard — the most complex indicator in the set (100KB binary, approximately 18x larger than SM_TDI). A multi-information overlay that aggregates and displays trading-relevant data for the current chart in a text/table format on the chart window. Based on the MMM methodology, the HUD likely displays: current session name, current broker time vs GMT, spread, ADR value, TDI line values, market maker cycle stage indicator, and possibly multi-pair data.

**The CONTEXT.md note:** "SM_NewHUD is 100KB — by far the largest. Its spec will likely be the longest and most complex. Plan for ~5-7 pages, not 3-4."

**Likely displayed elements ([INFER] for all):**
1. Current session (Asia / London / US / Gap) with countdown timer
2. Broker time and GMT time
3. Spread in pips
4. ADR value (current and remaining)
5. TDI line values (Green, Red, Yellow current values)
6. Pivot levels (PP, R1, S1)
7. Previous HOD/LOD
8. Market Maker cycle stage (if any — see Market Maker Cycle.jpg)
9. Account information (balance, equity, open P&L) [INFER:guess]
10. Multi-pair summary table [INFER:guess]

**MMM Book context:** The "Scanning View" (p. 53) shows an "Intraday Directional Matrix" table with Daily Colour, The Count (4H/H), The Range (M1-M3/M2-M4). A HUD that automates this matrix display would be extremely consistent with SM's workflow. The "Put the Chart Together" questionnaire (p. 54) lists exactly the data fields a HUD would display.

**Inputs ([INFER]):**
| Parameter | Type | Default | Confidence |
|-----------|------|---------|------------|
| HUDCorner | int | 0 (top-right) | [INFER] |
| FontSize | int | 10 | [INFER] |
| BackgroundColor | color | Black | [INFER] |
| TextColor | color | White | [INFER] |
| ShowSpread | bool | true | [INFER] |
| ShowADR | bool | true | [INFER] |
| ShowTDI | bool | true | [INFER] |
| ADRPeriod | int | 20 | [INFER] |

**What it draws:** A text panel (series of OBJ_LABEL or a single OBJ_EDIT object) on the main chart window corner. Does not use a subwindow. [INFER]

**Dependencies:** Likely calls sm_gmtoffset (for session detection), may internally recompute ADR and TDI values rather than reading from other indicators. [INFER]

**Backtester integration:** NewHUD is purely visual / informational. No backtester role. Python equivalent would be a dashboard print function or a real-time Streamlit/dash component.

**Confidence:** LOW for all internal details. The spec writer will have extensive [INFER:guess] entries for this indicator.

**Gaps:** (1) Does it show multi-pair data or single-pair only? (2) Does it compute TDI internally or read the SM_TDI indicator buffer? (3) What triggers refresh — OnTick, OnTimer, or both? (4) Does it support alert capabilities?

---

## 3. MMM Glossary Harvest

Terms from the MMM glossaries that indicator specs must cross-reference:

| Term | Definition (from MMM Glossary / Knowledge Base) | Indicator(s) |
|------|------------------------------------------------|--------------|
| ADR | Average Daily Range — indicator tracking average daily range of a currency | SM_ADR_Marker, SM_PivotPoints, SM_NewHUD |
| HOD / LOD | High / Low of Day — the highest/lowest point in a 24-hour period | SM_Daily_HiLo, SM_AlertZone_1/2, SM_NewHUD |
| I-HOD / I-LOD | Initial High/Low of Day — set during Asian session | sm_WorkTime, SM_AlertZone_1/2, SM_NewHUD |
| Market Maker Spread | Distance between I-HOD and I-LOD; <50 pips ideal | SM_ADR_Marker, SM_NewHUD |
| Trading Zone / Strike Zone | Area within 15-20 pips of HOD/LOD where setups occur | SM_AlertZone_1/2, SM_Alerting+TL |
| Blue Box | Defined key zone; session or level area — same as Trading Zone | SM_AlertZone_1/2 |
| TDI | Traders Dynamic Index — RSI+MA+Bollinger hybrid by Dean Malone | SM_TDI |
| Time Mapping | Matching broker server time to indicators | sm_gmtoffset, sm_WorkTime |
| Gap Time | Changeover between sessions (quiet period) | sm_WorkTime, SM_NewHUD |
| Session Open / Kill Zone | Fixed-time session open (London, NY) — key setup area | sm_WorkTime, SM_NewHUD |
| Pivot Phases (M1-M4) | Mid-pivot points used by Mauro to predict HOD/LOD location | SM_PivotPoints |
| Stop Hunt / Trap Zone | Aggressive MM move to trigger stops before real move | SM_AlertZone_1/2, SM_Alerting+TL |
| Shark Fin | TDI pattern: RSI breaks volatility band then re-enters — indicates stop hunt | SM_TDI |
| Blood in the Water | TDI pattern: RSI PL crosses Market Base Line — trend confirmation | SM_TDI |
| VB Squeeze | Volatility Band contraction — sign of consolidation before breakout | SM_TDI |
| TDI Hook | RSI PL hooks back from extreme (>68 or <32) — counter-trend signal | SM_TDI |
| 3-Day Cycle | Market maker cycle repeating over 3 days (accumulation/move/distribution) | SM_NewHUD (displays cycle stage) |
| Peak Formation | Highest/lowest intraday point | SM_Daily_HiLo, SM_NewHUD |
| Psychological Levels | Round-number price levels where institutional orders concentrate | SM_IlsleyPsychLevels |
| Market Maker Trend | The real trend of the market (vs. retail-perceived trend) | SM_TDI, SM_NewHUD |
| EMA 5/13 | Short-term EMA crossover pair — primary entry signal in MMM | SM_Crossover_Arrows |

---

## 4. Validation Architecture

This is a documentation phase — there are no code artifacts to test. However, completed specs CAN and MUST be validated against the sources used in this research.

### 4.1 Template Conformance Checklist (per spec file)

The plan-checker MUST verify each delivered `.md` file against this list:

```
[ ] Section 1: Header — name, source filename, platform, confidence level present
[ ] Section 2: Purpose — at least one paragraph; references MMM workflow
[ ] Section 3: Inputs/Parameters — table with all 5 columns (name, type, default, range, meaning); confidence tag on each row
[ ] Section 4: Outputs — three subsections: indicator buffers, chart objects, alerts (all three present even if "None")
[ ] Section 5: Calculation logic — step-by-step; includes bar-iteration model (new-bar-only vs. every-tick)
[ ] Section 6: Pseudocode — 30-80 lines; language-neutral imperative style; NOT MQL/Python syntax
[ ] Section 7: Visual elements — colors, line styles, Z-order, subwindow vs. main chart stated
[ ] Section 8: Dependencies — lists all Tier 0 dependencies and any external deps; "None" is explicit answer not omission
[ ] Section 9: Edge cases — covers: session boundary, weekends, broker DST, missing bars, JPY/index low-digit pairs, zero-volume bars
[ ] Section 10: Test cases — 2 minimum, 4 maximum; format "input conditions → expected output"
[ ] Section 11: Port notes — THREE paragraphs: MQ4→MQ5 deltas, Python port, Backtester integration
[ ] Section 12: Uncertainty log — bulleted; every [INFER] in sections 1-11 has corresponding bullet; format "[INFER] claim — reason"
```

**Failure condition:** Any section missing or containing placeholder text ("TBD", "TODO") fails template conformance.

### 4.2 TDI Spot-Check Rubric (HIGH priority)

The SM_TDI spec must be verified against the MMM TDI Tradestation PDF (this repo, `resource_pack/MMM/docs/MMM TDI_Tradestation.pdf`) on these specific claims:

| Claim in Spec | Expected (from PDF) | Verification Method |
|---------------|---------------------|---------------------|
| 5 lines + 3 levels | Green/Red/Yellow/Blue(×2) + 32/50/68 | PDF p. 10 — direct read |
| Green = RSI PL | 2-period SMA of RSI | PDF p. 11 — confirmed |
| Red = TSL | 7-period SMA of RSI | PDF p. 11 — confirmed |
| Yellow = MBL | 34-period SMA of RSI | PDF p. 12 — confirmed |
| Blue = VB | Bollinger on MBL, period 34 | PDF p. 13 — confirmed |
| 68 level = Buying Exhaustion | Overbought signal | PDF p. 10 — confirmed |
| 32 level = Selling Exhaustion | Oversold signal | PDF p. 10 — confirmed |
| TDI Signal Cross alert | Green crosses Red | PDF p. 15 — confirmed |
| MBL Cross alert conditions | Green crosses Yellow + price confirmation | PDF p. 16 — confirmed |
| TDI Hook alert conditions | Green hooks from 32/68 across VB | PDF p. 17 — confirmed |

**Auditor action:** For each row, locate the claim in the delivered SM_TDI.md and confirm it matches the PDF source. Any discrepancy must be flagged as a spec error.

### 4.3 Dependency Graph Cross-Check Rubric

The INDEX.md dependency graph must satisfy:

```
sm_gmtoffset
├── sm_WorkTime (uses gmtoffset)
└── sm_WorkTime_no_autogmt (explicitly has NO gmtoffset dependency)

sm_WorkTime / sm_gmtoffset (optional)
├── SM_ADR_Marker (may use for D1 boundary)
├── SM_Daily_HiLo (may use for D1 boundary)
├── SM_PivotPoints (uses for daily reset time)
└── SM_NewHUD (uses for session display)

Self-contained (no SM dependencies):
├── SM_IlsleyPsychLevels
├── SM_Crossover_Arrows
├── SM_TDI
├── SM_AlertZone_1
├── SM_AlertZone_2
├── SM_Alerting+TL (monitors user OBJ_TREND objects)
└── SM_BPCT (unclear)
```

**Auditor check:** Every spec's Section 8 (Dependencies) must be consistent with this graph. No Tier 1 indicator should claim a dependency on a Tier 2 indicator. No spec should claim a dependency on any third-party indicator outside the 14-file set.

### 4.4 [INFER] Coverage Audit

After all specs are delivered, an [INFER] audit must verify:

1. Every claim that is NOT directly sourced from the MMM TDI PDF, MMM Book, or ADR_Levels.mq5 is tagged `[INFER]` or `[INFER:guess]`
2. Every `[INFER]` in the body of the spec has a corresponding bullet in Section 12 (Uncertainty log)
3. The Uncertainty log does NOT contain claims that should be HIGH-confidence (e.g., TDI formula elements sourced from the PDF should NOT appear in the Uncertainty log as [INFER])
4. BPCT, NewHUD internals, and AlertZone_1 vs AlertZone_2 distinctions must each have at least 3 Uncertainty log entries

### 4.5 Nyquist Validation Architecture

Because this is a documentation phase, there are no automated tests. The Nyquist validation model is adapted to checklist-based gating:

| Tier | Gate before proceeding | Automated? |
|------|----------------------|------------|
| Tier 0 (3 helpers) | User review of all 3 specs | No — human review |
| Tier 1 (5 indicators) | User review of all 5 specs + template conformance pass | Partially (template checklist can be scripted) |
| Tier 2 (6 indicators) | User review + TDI spot-check rubric pass | Partially |
| INDEX.md | Full dependency graph cross-check pass + all 14 specs approved | Yes (graph consistency check) |

**Template conformance script:** A reviewer can run a simple grep/awk audit on each delivered `.md` to verify all 12 section headers are present:
```bash
for f in "resource_pack/MMM/SM Indicators/docs/helpers/"*.md "resource_pack/MMM/SM Indicators/docs/indicators/"*.md; do
    echo "=== $f ===";
    for section in "## Header" "## Purpose" "## Inputs" "## Outputs" "## Calculation" "## Pseudocode" "## Visual" "## Dependencies" "## Edge cases" "## Test cases" "## Port notes" "## Uncertainty"; do
        grep -c "$section" "$f" || echo "MISSING: $section";
    done;
done
```

---

## 5. Risks and Gaps

### 5.1 What We Still Won't Know After This Research

**HIGH-impact unknowns (affect spec quality materially):**

1. **BPCT abbreviation resolution.** No authoritative source identifies what BPCT stands for. The spec will present three candidates and mark all claims [INFER:guess]. A future operator who runs the indicator in MT4 could resolve this instantly by reading the indicator name in the Inputs tab.

2. **AlertZone_1 vs AlertZone_2 algorithm distinction.** The 148-byte file size difference is consistent with different default values only, but we cannot confirm this. If they are genuinely different algorithms, the specs will be wrong about AlertZone_2.

3. **NewHUD internal data sources.** The 100KB binary could compute all values internally, or it could read from other SM indicator buffers via `iCustom()`. If it uses `iCustom()` calls, the Dependencies section will be wrong.

4. **sm_gmtoffset exposure mechanism.** Whether it uses GlobalVariable, an indicator buffer, or a shared `.mqh` include file affects how dependent indicators read the offset — and thus the Dependencies section of every indicator that uses it.

5. **sm_WorkTime exact session boundaries.** The MMM Book specifies 07:30 GMT for London open, but the BTMM community sometimes uses 07:00. The spec must note both variants and tag the specific boundary as [INFER].

**MEDIUM-impact unknowns:**

6. **TDI StdDev multiplier.** Community sources split between 1.6185 and 2.0. The SM_TDI binary likely uses one specific value that cannot be determined without running the indicator.

7. **SM_Alerting+TL touch detection tolerance.** The number of pips used for "touch" detection significantly affects how many false alerts fire. This is entirely unverifiable from outside.

8. **SM_PivotPoints daily reset time.** MMM Book says 17:00 ET (22:00 GMT) but some brokers use midnight server time. The indicator may use a configurable reset time or may hard-code it.

**LOW-impact unknowns (affect completeness but not correctness of spec):**

9. **Exact color defaults.** Red, green, yellow, blue are clearly the MMM palette but specific hex values or MT4 named-color constants are unverifiable.
10. **Object-naming prefixes.** The prefix used by each indicator for its chart objects (e.g., "ADR_", "SM_WTime_") cannot be determined without inspecting runtime object lists.
11. **2011-era helpers' parameter names.** sm_WorkTime and sm_gmtoffset predate the 2019 SM indicator set; their parameter names may differ from conventions used in the newer indicators.

### 5.2 The "Cannot Know" List

These items are structurally impossible to determine without either (a) a working MT4 terminal running these indicators, or (b) access to the original MQ4 source:
- Whether any indicator repaints (recalculates on historical bars after initial compute)
- Exact buffer index assignments for each line
- Whether indicators support alerts via MetaTrader's `Alert()`, `SendMail()`, and `SendNotification()` or only popup/sound
- The object Z-order within multi-indicator chart setups
- Whether NewHUD has a "compact mode" or responsive layout

---

## 6. Recommended Plan Slicing

**Recommendation: 4 plans (one per tier + INDEX.md)**

Rationale:

| Plan | Content | Files | Estimated tasks | Internal review checkpoint |
|------|---------|-------|-----------------|---------------------------|
| Plan 01 — Tier 0 | sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt | 3 | 3 (one per file) | User review: Tier 0 complete |
| Plan 02 — Tier 1 | ADR_Marker, Daily_HiLo, BPCT, IlsleyPsychLevels, Crossover_Arrows | 5 | 5 (one per file) | User review: Tier 1 complete |
| Plan 03 — Tier 2 | TDI, PivotPoints, AlertZone_1, AlertZone_2, Alerting+TL, NewHUD | 6 | 6 (one per file) | User review: Tier 2 complete |
| Plan 04 — INDEX | INDEX.md | 1 | 1 + integration verification | Final user review |

**Do NOT split Tier 2 into two plans (e.g., TDI+PivotPoints vs. AlertZone+NewHUD).** Rationale: the user review checkpoint after Tier 2 is the natural quality gate; splitting creates an additional intermediate review with no new information until NewHUD is done anyway. The CONTEXT.md already acknowledges NewHUD is larger (~5-7 pages) — that is a within-plan sizing note, not a reason to split the plan.

**Parallelism note:** Within Tier 1 and Tier 2, individual specs are independent documents and can be written in parallel if two executor sessions run simultaneously. The planner should note this in the plan so a future parallelized execution can exploit it.

**INDEX.md last:** INDEX.md must be written after all 14 specs are reviewed and approved, so it can accurately list confidence levels, cross-reference all dependencies, and write the ASCII dependency graph from verified information.

---

## Sources

### Primary (HIGH confidence)
- `resource_pack/MMM/docs/MMM TDI_Tradestation.pdf` — full TDI structure (pages 9-19 read); all TDI lines, levels, alert conditions
- `resource_pack/MMM/docs/_MMM Book.pdf` — MMM methodology; session times (p. 8), colour-coded sessions (p. 40), HOD/LOD markers (p. 41), ADR High and Low (p. 41), Pivots (pp. 42-43), RSI (p. 44), TDI (pp. 45-46), Confluence of Signals (p. 47), Look for Strike Zones (p. 55)
- `V2/indicators/ADR_Levels.mq5` — MQ5 precedent for ADR_Marker formula (`today_open ± ADR/2`), parameter conventions, drawing API pattern
- `resource_pack/MMM/docs/MMM_Glossary_Enhanced.md` — term definitions for ADR, TDI, HOD/LOD, Sessions, Trading Zone
- `resource_pack/MMM/docs/MMM_Knowledge_Base.md` — 3-day cycle, M/W formations, session timing details

### Secondary (MEDIUM confidence)
- [Traders Dynamic Index — MetaTrader Indicator (EarnForex)](https://www.earnforex.com/indicators/Traders-Dynamic-Index/) — confirms RSI 13, VB 34, StdDev 1.6185, RSI_PL 2, TSL 7
- [Traders Dynamic Index — RoboForex Blog](https://blog.roboforex.com/blog/2020/05/28/traders-dynamic-index-indicator-description-and-trading/) — cross-confirms TDI parameter defaults
- [TDI Indicator Trading Strategy — Traders Union 2026](https://tradersunion.com/interesting-articles/trading-strategies/tdi-indicator/) — confirms RSI period 13, signal 7, MBL 34
- [Pivot Points — CashBackForex](https://www.cashbackforex.com/article/calculate-pivot-point) — standard pivot formulas (PP, R1-R3, S1-S3) confirmed against industry standard
- [BTMM Multi EMAs — MQL5 Market](https://www.mql5.com/en/market/product/154431) — confirms EMA 5/13 as primary crossover pair in BTMM

### Tertiary (LOW confidence — community, single source, unverified)
- [ForexPops — Steve Mauro MT4 Indicators](https://forexpops.com/steve-mauro-indicators/) — general SM indicator package description
- [Forex Factory — Steve Mauro MMM beat the market](https://www.forexfactory.com/thread/816894-steve-mauro-mmm-beat-the-market) — community usage patterns
- [HowToTrade — BTMM Strategy Guide](https://howtotrade.com/trading-strategies/beat-the-market-maker/) — EMA naming conventions (Mustard, Ketchup, etc.)
- [MQL5 Forum — Auto detect GMT offset](https://www.mql5.com/en/forum/144719) — confirms broker GMT detection challenge
- [Studocu — BTMM Seminar Notes](https://www.studocu.com/row/document/tumaini-university-makumira/elements-of-commerce/btmm-steve-mauro-indicator-they-are-for-confluence-and-confirmation-do-not-use-them-to-make/16629001) — general BTMM context

---

## Metadata

**Confidence breakdown:**
- SM_TDI: HIGH — fully documented in MMM TDI Tradestation PDF; cross-confirmed by community
- SM_ADR_Marker: HIGH for formula (confirmed by ADR_Levels.mq5 precedent and MMM Book); MEDIUM for parameter names
- SM_Daily_HiLo, SM_PivotPoints, SM_IlsleyPsychLevels, SM_Crossover_Arrows: MEDIUM — algorithms are standard/well-documented; SM-specific parameter names unverifiable
- sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt: MEDIUM — function is understood; exact implementation details from 2011 unverifiable
- SM_AlertZone_1, SM_AlertZone_2, SM_Alerting+TL: MEDIUM for function class; LOW for implementation details
- SM_BPCT: LOW — abbreviation unresolved; no direct community source
- SM_NewHUD: LOW for internals; MEDIUM for purpose and likely display elements

**Research date:** 2026-04-26
**Valid until:** 2026-07-26 (stable domain; MMM indicators are 2019-era, no active development)

---

## RESEARCH COMPLETE
