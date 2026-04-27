# SM_NewHUD

## Header

| Field | Value |
|-------|-------|
| Name | SM_NewHUD |
| Source filename | `!SM_NewHUD.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 100,652 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (may depend on sm_gmtoffset; may internally recompute or call iCustom on other SM indicators) |
| Confidence | Confidence: Low (internals); Medium (purpose and likely-displayed field set) |

**Confidence rationale:** SM_NewHUD is the most complex and uncertain indicator in the entire Phase 11 corpus. The 100,652-byte binary is approximately **6× larger than SM_TDI** (15,880 bytes) and ~18× larger than SM_IlsleyPsychLevels. This size is consistent with a Heads-Up Display that renders many simultaneous text fields, each with its own update logic, string-formatting code, and conditional color mapping. The purpose — a real-time multi-field dashboard displaying session, spread, ADR, TDI values, pivots, HOD/LOD, and market-maker cycle stage — is MEDIUM confidence, grounded in the MMM Book pp. 53-54 "Scanning View" (Intraday Directional Matrix) and the MMM Book p. 54 "Put the Chart Together" questionnaire that an MMM trader answers before each entry. The **internals** (exact field list, rendering implementation, parameter names, whether it calls iCustom vs. recomputes, whether it shows multi-pair data or account info) are LOW confidence — marked accordingly with `[INFER]` and `[INFER:guess]` throughout.

**Key size hypothesis:** 100KB could reflect: (a) rendering 10-15 distinct text fields with individual update logic, (b) embedded copies of TDI/ADR/Pivot calculation code rather than calling `iCustom` on those indicators, (c) multiple display modes (compact / full / scanning-matrix layout), (d) string-formatting machinery for labeled text rows, (e) multi-pair data fetching with symbol iteration. Any or all of these could explain the size.

**Primary source for purpose:** MMM Book p. 53 "Scanning View" — shows the Intraday Directional Matrix with Daily Colour, The Count (4H/H), The Range (M1-M3 / M2-M4). MMM Book p. 54 "Put the Chart Together" — the 12-question checklist an MMM trader runs before entering. Market Maker Cycle.jpg (in repo at `resource_pack/MMM/docs/Market Maker Cycle.jpg`) — the visual for the 3-day accumulation / move / distribution cycle that the HUD likely displays as a cycle-stage indicator.

---

## Purpose

SM_NewHUD is a **Heads-Up Display (HUD) dashboard** — a multi-information overlay that aggregates and displays trading-relevant data for the current chart in a structured text panel on the chart corner. It is purely informational (no signals, no drawing on the price chart) but functions as the primary at-a-glance reference for an MMM trader during an active session, consolidating data that would otherwise require switching between multiple chart windows or manually computing values.

The "New" in SM_NewHUD suggests it supersedes an earlier "SM_HUD" or similar dashboard. The 100KB binary size (by far the largest in the SM set) is consistent with an indicator that has gone through multiple feature additions, debug cycles, and formatting refinements over time.

**MMM Book pp. 53-54 provide the specification anchor.** The MMM Book p. 53 presents the "Scanning View" — an Intraday Directional Matrix that an MMM trader builds for each pair, capturing: **Daily Colour** (is today's daily candle currently green or red?), **The Count** (4H and H1 candle count since the daily open — how many candles into the day?), and **The Range** (which pivot mid-range the day is targeting: M1-M3 or M2-M4, depending on the prior daily candle color). A HUD that automates this matrix display — plus session timing, spread, ADR, and TDI confirmation values — is exactly what SM_NewHUD is designed to provide. MMM Book p. 54 "Put the Chart Together" questionnaire lists 12 data points traders must check before every entry: these map to the HUD fields.

**Market Maker Cycle context:** The Market Maker Cycle.jpg image (in repo) depicts the 3-day accumulation / directional-move / distribution pattern used in the BTMM methodology. If SM_NewHUD displays the current "day of cycle" (accumulation / move / distribution), it automates one of the most subjective MMM assessments. This field is `[INFER:guess]` — it may not exist, but its inclusion in a 100KB binary is plausible.

---

## Inputs / Parameters

The HUD's large binary size implies a substantial parameter set — likely one `Show*` toggle per display section plus configuration for each section. The following table is extensively [INFER].

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| HUDCorner | int | 0 (top-right) | 0–3 (MT4 CORNER_* enum: 0=top-right, 1=top-left, 2=bottom-left, 3=bottom-right) | Corner of chart where the HUD panel is anchored | [INFER] |
| FontFace | string | "Consolas" | any system font | Monospace font preferred for table-style alignment of numeric fields | [INFER] |
| FontSize | int | 10 | 6–24 | Font size in points | [INFER] |
| BackgroundColor | color | clrBlack | any | Background color of the HUD text panel | [INFER] |
| TextColor | color | clrWhite | any | Default text color for neutral fields | [INFER] |
| BullishColor | color | clrLimeGreen | any | Color applied to fields indicating bullish bias | [INFER] |
| BearishColor | color | clrTomato | any | Color applied to fields indicating bearish bias | [INFER] |
| ShowSession | bool | true | true / false | Display current session name (Asia / London / US / Gap) with countdown timer | [INFER] |
| ShowSpread | bool | true | true / false | Display current bid-ask spread in pips | [INFER] |
| ShowADR | bool | true | true / false | Display ADR value + current day's range + remaining range | [INFER] |
| ADRPeriod | int | 20 | 5–50 | Lookback period for ADR calculation | [INFER] — 20 is the MMM standard per SM_ADR_Marker.md |
| ShowTDI | bool | true | true / false | Display current TDI line values (Green, Red, Yellow RSI values) and directional bias | [INFER] |
| ShowPivots | bool | true | true / false | Display PP, R1, S1 and which zone the current price occupies | [INFER] |
| ShowHODLOD | bool | true | true / false | Display today's HOD, LOD, previous day's PHOD, PLOD, and intraday I-HOD / I-LOD | [INFER] |
| ShowDailyColour | bool | true | true / false | Display whether today's daily candle is currently green (bullish) or red (bearish) | [INFER] — maps to MMM Book p. 53 "Daily Colour" field |
| ShowMMCycle | bool | true | true / false | Display Market Maker Cycle stage (Accumulation / Move / Distribution) | [INFER] — maps to Market Maker Cycle.jpg 3-day pattern |
| ShowAccount | bool | false | true / false | Display account balance, equity, and floating P&L | [INFER:guess] — account data display is a secondary feature; may not exist |
| ShowMultiPair | bool | false | true / false | Display a summary table of configured pairs with directional bias | [INFER:guess] — multi-pair data in a 100KB binary is plausible but unconfirmed |
| PairList | string | "EURUSD,GBPUSD,USDJPY,AUDUSD" | comma-separated pairs | If ShowMultiPair=true, these pairs are scanned | [INFER:guess] |
| RefreshSeconds | int | 1 | 1–60 | Update cadence via `EventSetTimer` — how frequently the HUD fields refresh | [INFER] |
| ObjectPrefix | string | "smHUD_" | any valid string | Prefix for all OBJ_LABEL chart objects | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_NewHUD creates no indicator buffer arrays. It renders entirely through `OBJ_LABEL` chart objects (or possibly a single `OBJ_RECTANGLE_LABEL` with multi-line text) in the main chart window. No data is exposed to other indicators or EAs via `CopyBuffer`.

### Chart objects

Multiple `OBJ_LABEL` objects in the chart's main window (or a composite label rectangle), positioned at the `HUDCorner` anchor:
- One label per enabled display section (session, spread, ADR, TDI, pivots, HOD/LOD, daily colour, MM cycle)
- [INFER:guess] Multiple sub-labels per section for multi-line fields (e.g., HOD/LOD may span 2-3 lines)
- [INFER:guess] One optional `OBJ_RECTANGLE` serving as a black background panel behind all labels
- All objects named with `ObjectPrefix + field_name` (e.g., `"smHUD_session"`, `"smHUD_spread"`, `"smHUD_adr"`)

Approximate rendered appearance (all [INFER]):
```
┌─────────────────────────────────┐
│ Session: London  (closes 04:52) │
│ Spread:  0.8 pips               │
│ ADR:     88 pips | rem: 35 pips │
│ TDI:     G=58 R=55 Y=52 bullish │
│ PP: 1.0867  Zone: PP-R1         │
│ HOD: 1.0892  LOD: 1.0831        │
│ PHOD: 1.0900  PLOD: 1.0830      │
│ Daily: GREEN (bullish)           │
│ Cycle: Day 2 — Move phase        │
└─────────────────────────────────┘
```

### Alerts

[INFER] None. SM_NewHUD is a passive display dashboard. It does not fire alerts — the AlertZone and Alerting+TL indicators handle alerting. The HUD is a read-only informational overlay.

---

## Calculation logic

SM_NewHUD updates all display fields on a timer cadence (RefreshSeconds) and potentially on each tick for the most time-sensitive fields (spread, current price relative to zones).

1. **On `OnInit`:**
   - Create one `OBJ_LABEL` per enabled field at the `HUDCorner` position with vertical offset per row.
   - Call `EventSetTimer(RefreshSeconds)` to schedule periodic refreshes.
   - Compute an initial snapshot of all fields and populate the labels.

2. **On `OnTimer` (every RefreshSeconds):**

   **a. Session field (if ShowSession=true):**
   - Read `sm_GMTOffset` from `GlobalVariableGet("sm_GMTOffset")` [INFER] or compute from `TimeCurrent() - TimeGMT()`.
   - Classify current GMT time into: Asia (00:30-07:00 GMT), London (07:30-13:00 GMT), US (13:30-20:30 GMT), Gap (all other times).
   - Compute seconds to next session boundary.
   - Update label: `"Session: London  (closes in 04:52)"`.

   **b. Spread field (if ShowSpread=true):**
   - `spread_pips = (SymbolInfoDouble(symbol, SYMBOL_ASK) - SymbolInfoDouble(symbol, SYMBOL_BID)) / pip_unit()`.
   - Update label: `"Spread: 0.8 pips"`.

   **c. ADR field (if ShowADR=true):**
   - Compute ADR over `ADRPeriod` D1 bars: `sum(DailyHigh[i] - DailyLow[i]) / ADRPeriod` for i=1..ADRPeriod.
   - Compute today's range: `today_range = iHigh(PERIOD_D1, 0) - iLow(PERIOD_D1, 0)`.
   - Remaining = max(0, ADR - today_range).
   - Update label: `"ADR: 88 pips | today: 53 pips | rem: 35 pips"`.

   **d. TDI field (if ShowTDI=true):**
   - Compute (or read via iCustom from SM_TDI indicator) RSI_PL (Green), TSL (Red), MBL (Yellow) current values.
   - Classify bias: `if RSI_PL > TSL and RSI_PL > MBL: "bullish"` / `if RSI_PL < TSL and RSI_PL < MBL: "bearish"` / else `"neutral"`.
   - Update label with bias color: `"TDI: G=58 R=55 Y=52 (bullish)"` in BullishColor.

   **e. Pivots field (if ShowPivots=true):**
   - Compute daily pivots (PP, R1, S1) using previous day's H/L/C (same formula as SM_PivotPoints).
   - Classify current bid's zone: "below S1" / "S1-PP" / "PP-R1" / "R1-R2" / "above R2".
   - Update label: `"PP: 1.0867  Zone: PP-R1"`.

   **f. HOD/LOD field (if ShowHODLOD=true):**
   - Today HOD/LOD: `iHigh/iLow(PERIOD_D1, 0)`.
   - Previous day PHOD/PLOD: `iHigh/iLow(PERIOD_D1, 1)`.
   - Intraday I-HOD/I-LOD (Asian session): highest/lowest price from 00:30 GMT to 07:00 GMT today [INFER].
   - Update label: `"HOD: 1.0892  LOD: 1.0831 | PHOD: 1.0900  PLOD: 1.0830"`.

   **g. Daily Colour field (if ShowDailyColour=true):**
   - Compare `iOpen(PERIOD_D1, 0)` vs `current_bid`: if bid > open → GREEN; else → RED.
   - Update label with BullishColor or BearishColor: `"Daily: GREEN (bullish)"`.
   - Maps directly to MMM Book p. 53 "Daily Colour" field in the scanning matrix.

   **h. MM Cycle field (if ShowMMCycle=true) [INFER:guess]:**
   - Inferred from Market Maker Cycle.jpg 3-day pattern (Accumulation / Move / Distribution).
   - Day detection: `cycle_day = (TradingDaysSinceLastMajorLow % 3) + 1` [INFER:guess — highly speculative].
   - Or: cycle stage detected from TDI VB width (narrow = accumulation, expanding = move, retracting = distribution) [INFER:guess].
   - Update label: `"Cycle: Day 2 — Move"` [INFER:guess].

   **i. Account field (if ShowAccount=true) [INFER:guess]:**
   - `balance = AccountInfoDouble(ACCOUNT_BALANCE)`.
   - `equity = AccountInfoDouble(ACCOUNT_EQUITY)`.
   - `profit = AccountInfoDouble(ACCOUNT_PROFIT)`.
   - Update label: `"Bal: 1000.00 | Eq: 974.50 | P/L: -25.50"` (P/L in BearishColor if negative).

3. **On `OnTick`** (for sub-timer-cadence updates):
   - [INFER] Spread field may refresh on every tick rather than waiting for the timer (spread changes tick-by-tick and a 1-second refresh may show stale spread).
   - [INFER] Session countdown timer display may tick down in real-time if the indicator updates it on OnTick.

4. **On `OnChartEvent`** (CHARTEVENT_CHART_CHANGE) [INFER]:
   - Reposition all OBJ_LABEL objects after chart window resize or corner change via input dialog.

5. **On `OnDeinit`:** Delete all objects with prefix `ObjectPrefix` ("smHUD_").

**Bar-iteration model:** NOT every-tick for all fields. Timer-based refresh (RefreshSeconds=1) is the primary model. Spread and countdown may be tick-driven. ADR/TDI/Pivot computations are expensive and should NOT run every tick.

---

## Pseudocode

```
# SM_NewHUD — language-neutral imperative pseudocode
# Heads-Up Display dashboard for the MMM trading workflow
# Source: MMM Book pp. 53-54 (Scanning View + Put the Chart Together questionnaire)
#         Market Maker Cycle.jpg (3-day cycle stage display)
#         RESEARCH.md §2 Tier 2 — SM_NewHUD dossier

state labels : map<string, label_object> = {}

function on_init():
    row = 0
    if ShowSession:    labels["session"]  = create_label("smHUD_session",  HUDCorner, row++)
    if ShowSpread:     labels["spread"]   = create_label("smHUD_spread",   HUDCorner, row++)
    if ShowADR:        labels["adr"]      = create_label("smHUD_adr",      HUDCorner, row++)
    if ShowTDI:        labels["tdi"]      = create_label("smHUD_tdi",      HUDCorner, row++)
    if ShowPivots:     labels["pivots"]   = create_label("smHUD_pivots",   HUDCorner, row++)
    if ShowHODLOD:     labels["hodlod"]   = create_label("smHUD_hodlod",   HUDCorner, row++)
    if ShowDailyColour:labels["daily"]    = create_label("smHUD_daily",    HUDCorner, row++)
    if ShowMMCycle:    labels["cycle"]    = create_label("smHUD_cycle",    HUDCorner, row++)
    if ShowAccount:    labels["account"]  = create_label("smHUD_account",  HUDCorner, row++)
    if ShowMultiPair:  labels["mpair"]    = create_label("smHUD_mpair",    HUDCorner, row++)
    set_timer(RefreshSeconds)
    refresh_all_fields()

function on_timer():
    refresh_all_fields()

function on_tick():
    # Sub-timer refresh for time-sensitive fields
    if ShowSpread:
        spread = (ask() - bid()) / pip_unit()
        update_label("spread", "Spread: " + format_pips(spread) + " pips")

function refresh_all_fields():
    if ShowSession:
        gmt_off = global_var("sm_GMTOffset") or compute_gmt_offset()
        session, secs_remaining = classify_session(now_utc() + gmt_off)
        update_label("session", "Session: " + session + "  (closes " + hms(secs_remaining) + ")")

    if ShowADR:
        adr     = compute_adr(ADRPeriod)
        t_range = day_high() - day_low()
        remaining = max(0, adr - t_range)
        update_label("adr", "ADR: " + pips(adr) + " | today: " + pips(t_range) +
                     " | rem: " + pips(remaining))

    if ShowTDI:
        rsi_pl, tsl, mbl = compute_tdi_current()  # internal or via iCustom [INFER]
        if rsi_pl > tsl and rsi_pl > mbl:
            bias, col = "bullish", BullishColor
        elif rsi_pl < tsl and rsi_pl < mbl:
            bias, col = "bearish", BearishColor
        else:
            bias, col = "neutral", TextColor
        update_label("tdi",
            "TDI: G=" + fmt1(rsi_pl) + " R=" + fmt1(tsl) + " Y=" + fmt1(mbl) +
            " (" + bias + ")", color=col)

    if ShowPivots:
        pp, r1, s1 = compute_daily_pivots()
        zone = classify_price_zone(bid(), pp, r1, s1)
        update_label("pivots", "PP: " + fmt_price(pp) + "  Zone: " + zone)

    if ShowHODLOD:
        update_label("hodlod",
            "HOD: " + fmt_price(day_high()) + "  LOD: " + fmt_price(day_low()) +
            " | PHOD: " + fmt_price(prev_day_high()) + "  PLOD: " + fmt_price(prev_day_low()))

    if ShowDailyColour:
        d_open = daily_open()
        if bid() > d_open:
            update_label("daily", "Daily: GREEN (bullish)", color=BullishColor)
        else:
            update_label("daily", "Daily: RED  (bearish)", color=BearishColor)

    if ShowMMCycle:           # [INFER:guess]
        stage = detect_mmm_cycle_stage()   # returns "Day 1 — Accum" / "Day 2 — Move" / "Day 3 — Dist"
        update_label("cycle", "Cycle: " + stage)

    if ShowAccount:           # [INFER:guess]
        bal = account_balance(); eq = account_equity(); pl = account_profit()
        pl_col = BearishColor if pl < 0 else TextColor
        update_label("account",
            "Bal: " + fmt_money(bal) + " | Eq: " + fmt_money(eq) +
            " | P/L: " + fmt_money(pl), color=pl_col)

function on_deinit():
    kill_timer()
    delete_all_objects_with_prefix("smHUD_")
```

---

## Visual elements

**Main price chart (no subwindow).** The HUD renders as a structured text panel anchored to `HUDCorner` (default top-right):

**Layout (all [INFER]):**
- Black or near-black background rectangle (`OBJ_RECTANGLE_LABEL` or inferred via z-layered `OBJ_RECTANGLE`) [INFER]
- 8-10 text rows, one per enabled field
- Monospace font (Consolas or Courier New) for column alignment
- Variable text colors per field: neutral fields in white, bullish readings in lime-green, bearish readings in red/tomato

**Approximate dimensions:** 240-320 pixels wide, 150-200 pixels tall — sized to fit 10 rows at 10pt Consolas [INFER].

**Z-order:** Above all chart elements (candlesticks, lines, rectangles from other indicators). The HUD is always visible regardless of price-chart clutter.

**Color semantics:**
- Spread < 2 pips: TextColor (neutral)
- Spread ≥ 2 pips: [INFER] may show in BearishColor (high spread = caution)
- TDI bullish: BullishColor (lime green)
- TDI bearish: BearishColor (tomato/red)
- Daily colour green: BullishColor
- Daily colour red: BearishColor
- P/L negative: BearishColor; P/L positive: BullishColor [INFER:guess]

---

## Dependencies

- **sm_gmtoffset** (likely) — for classifying the current time into the correct MMM session (Asia/London/US/Gap). The HUD needs the broker's GMT offset to correctly determine "is it London session right now?" [INFER]
- **SM_TDI** (possible) — the HUD may read TDI buffer values via `iCustom("SM_TDI", symbol, period, buffer, shift)` if SM_TDI is loaded on the same chart, OR it may internally recompute the RSI/SMA/Bollinger calculations. The 100KB binary size makes self-contained computation more plausible (avoids a hard dependency) but does not confirm it. [INFER]
- **SM_ADR_Marker, SM_PivotPoints, SM_Daily_HiLo** (possible) — same question applies to each: read via iCustom vs. internal recompute. [INFER]

The dependency question — **iCustom vs. internal recompute** — is the single most important unknown about SM_NewHUD. If it uses iCustom, removing SM_TDI from the chart would break the HUD's TDI field. If it recomputes internally, SM_NewHUD is a monolithic self-contained dashboard.

---

## Edge cases

1. **sm_GMTOffset GlobalVariable not published when HUD initializes:** Session field shows "?" or defaults to "Unknown" until the GMT offset is available (which requires sm_gmtoffset to be loaded and have executed at least once). [INFER] A timeout or default-GMT fallback may be implemented.

2. **Insufficient bar history for ADR/TDI/Pivot calculation:** If the chart has fewer than `ADRPeriod + 34` bars (warmup for ADR + TDI's 34-period SMA), the corresponding fields display "N/A" or remain blank. [INFER]

3. **Symbol/timeframe change:** `OnInit` fires; all old labels (prefix-based) are deleted; labels are re-created for the new symbol; all fields are recomputed with the new symbol's data.

4. **Window resize / chart corner change via input dialog:** When the user changes `HUDCorner` via the indicator's input dialog, MT4 triggers an `OnInit` recompile. The new corner placement takes effect immediately; old objects are deleted via prefix-based cleanup. [INFER] `OnChartEvent(CHARTEVENT_CHART_CHANGE)` may also reposition labels on window resize without recompile.

5. **JPY / index symbols — pip formatting:** Every numeric field involving price or spread must use `SYMBOL_DIGITS` to compute pip size and format displayed values correctly. For USDJPY (3-digit), 1 pip = 0.01 — a spread of 0.01 is 1 pip. Incorrect pip detection would display "0.1 pips" instead of "1 pip" (10× error). The HUD must call `pip_unit()` per the current chart symbol for every numeric conversion.

6. **Multi-pair table (ShowMultiPair=true) with unavailable symbols:** If a symbol in `PairList` is not in Market Watch, `MarketInfo()` or `SymbolInfoDouble()` returns 0 or an error. The HUD must display "USDJPY: N/A" for that row rather than crashing or showing 0. [INFER:guess]

7. **Timer race condition with OnTick:** The spread field updated in `OnTick` and other fields updated in `OnTimer` may interleave. During a 1-second timer cycle with multiple tick events, the spread line might flicker between the timer-stale value and the tick-fresh value. [INFER] A mutex flag or double-buffer approach may be used.

8. **RefreshSeconds=1 with all fields enabled:** Each timer cycle computes ADR (reads ADRPeriod D1 bars), TDI (computes RSI + SMA chains), Pivots, HOD/LOD (reads D1 and possibly H1 bars), and optionally multi-pair data. On a slow machine with many symbols in Market Watch, this may cause visible lag. [INFER] Users on slow machines should increase RefreshSeconds to 5 or 10.

9. **MM Cycle stage detection (ShowMMCycle=true) — reliability warning [INFER:guess]:** The Market Maker Cycle.jpg 3-day pattern is a qualitative framework, not a deterministic algorithm. Any automated "Day 1/2/3" detection implemented in the HUD is necessarily heuristic and subject to false classification. The Uncertainty log prominently flags this.

---

## Test cases

1. **Full HUD render at Asia-to-London boundary (EURUSD H1):**
   - Time: 07:25:30 GMT (4 minutes 30 seconds before London open at 07:30 GMT)
   - Expected HUD fields (all [INFER] for formatting):
     - `"Session: Asia  (closes 00:04:30)"`
     - `"Spread: 0.7 pips"`
     - `"ADR: 88 pips | today: 25 pips | rem: 63 pips"`
     - `"TDI: G=52 R=51 Y=49 (neutral)"` (in TextColor=white, bias neutral)
     - `"PP: 1.0867  Zone: PP-R1"` (current bid in 1.0867-1.0904 range)
     - `"HOD: 1.0890  LOD: 1.0820 | PHOD: 1.0900  PLOD: 1.0830"`
     - `"Daily: GREEN (bullish)"` (current bid > daily open)
     - `"Cycle: Day 1 — Accumulation"` [INFER:guess]
   - Verify: At 07:30 GMT (next timer cycle), Session field transitions to `"Session: London  (closes 05:30:00)"`.

2. **Session transition — countdown resets:**
   - One second before 07:30 GMT: `"Session: Asia  (closes 00:00:01)"`.
   - At 07:30 GMT exactly (next timer cycle fires): `"Session: London  (closes 05:30:00)"`.
   - Verifies that session-boundary detection and countdown-reset logic function correctly.

3. **TDI bullish bias change with color update:**
   - London open momentum spike: RSI_PL rises from 49 to 54, crossing MBL (50) and TSL (51).
   - Before: TDI label reads `"TDI: G=49 R=51 Y=50 (bearish)"` in BearishColor.
   - After: TDI label updates to `"TDI: G=54 R=51 Y=50 (bullish)"` in BullishColor.
   - Verifies that conditional color coding switches on directional change.

4. **Account field with floating loss (ShowAccount=true) [INFER:guess]:**
   - `ACCOUNT_BALANCE = 1000.00`, `ACCOUNT_EQUITY = 974.50`, `ACCOUNT_PROFIT = -25.50`.
   - Expected: `"Bal: 1000.00 | Eq: 974.50 | P/L: -25.50"` with P/L value rendered in BearishColor (red).
   - Verifies conditional color: positive P/L → BullishColor; negative → BearishColor.

5. **Multi-pair fallback — symbol not in Market Watch [INFER:guess]:**
   - ShowMultiPair=true, PairList="EURUSD,GBPUSD,USDJPY". USDJPY is not in Market Watch.
   - Expected HUD multi-pair section:
     - `"EURUSD: ↑ G=56"  GBPUSD: ↓ G=44"  USDJPY: N/A"`
   - Verifies graceful degradation: the missing symbol does not crash the indicator or display a zero/garbage value.

6. **Chart corner change via input dialog:**
   - User changes `HUDCorner` from 0 (top-right) to 2 (bottom-left) in the indicator settings dialog.
   - MT4 triggers `OnInit` recompile.
   - Expected: All `smHUD_*` objects are deleted (OnDeinit cleanup), then recreated at the bottom-left corner (OnInit). The session countdown continues without interruption (timer restarts).

---

## Port notes

### MQ4 to MQ5 deltas

- `OBJ_LABEL` API identical: `ObjectCreate`, `ObjectSetString(OBJPROP_TEXT)`, `ObjectSetInteger(OBJPROP_COLOR)`, `ObjectSetInteger(OBJPROP_FONTSIZE)`.
- `EventSetTimer` / `OnTimer` identical.
- `AccountInfoDouble(ACCOUNT_BALANCE)` identical.
- `SymbolInfoDouble(symbol, SYMBOL_ASK/BID)` identical to MQ5; MQ4 uses `Ask`/`Bid` globals instead.
- `iCustom` for reading SM_TDI buffers: MQ4 `iCustom("SM_TDI", period, ..., buffer, shift)` → MQ5 handle pattern with `CopyBuffer`. If SM_NewHUD calls iCustom, the MQ5 port must replace those calls with the handle-based API.
- `ChartID()` required explicitly in MQ5 for all `ObjectCreate` / `ObjectGet*` / `ObjectSet*` calls.

### Python port

SM_NewHUD has **no backtester role** — it is a purely visual, live-data dashboard. A Python equivalent for live trading would be a **Streamlit or Dash dashboard** subscribing to the same data sources:
- Session classifier: `temporal_filters.py` (Phase 8.5) provides session boundaries
- ADR: `V2/v3_intelligence/adr.py` (referenced in SM_ADR_Marker.md)
- TDI: future `V2/v3_intelligence/tdi.py` (Phase 9 candidate)
- Pivots: one-line computation from daily OHLC
- HOD/LOD: from the OHLCV cache (Phase 8.4 INFRA-02)
- Account: MetaAPI or ZMQ bridge account info endpoint

A "backtest replay HUD" — showing what the HUD would have displayed at each historical timestamp during a simulation — would pull all fields from the V2 OHLCV cache and Phase 8 regime detector outputs. This is not currently implemented in Helix.

### Backtester integration

**SM_NewHUD does NOT integrate with `backtest_hybrid.py`** — it is purely visual and informational. However, the data sources SM_NewHUD aggregates are EXACTLY the same set that the Phase 9 StrategyRouter (per ROADMAP.md) will consume as gating inputs:

| HUD field | Phase 9 router equivalent |
|-----------|--------------------------|
| Session | `temporal_filters.py` session gate |
| ADR remaining | ADR-utilization threshold gate |
| TDI bias | TDI signal filter (Phase 9 candidate `tdi.py`) |
| Pivots zone | Spatial pivot-proximity gate |
| HOD/LOD | HOD/LOD distance gate |
| Daily colour | Daily-trend direction filter |
| MM Cycle stage | 3-day cycle phase gate (if implemented) |

SM_NewHUD is therefore a **human analog** of what the Phase 9 StrategyRouter does programmatically — the HUD enables a human to make the same gating decisions the router will automate. This makes SM_NewHUD's field list a useful design specification for the Phase 9 router's input feature set.

---

## Uncertainty log

- [INFER] All input parameter names, types, and defaults — none are verifiable from the binary alone; the 17-row Inputs table is a plausible hypothesis based on MMM Book pp. 53-54 fields
- [INFER] Whether the HUD computes ADR, TDI, Pivots, and HOD/LOD internally (most likely given 100KB binary — no iCustom overhead) or reads them via iCustom from separately loaded SM indicators
- [INFER] RefreshSeconds default 1 — every-second refresh is responsive but resource-intensive; could be 5 or 10; tick-driven alternatives are possible
- [INFER] Whether ShowMMCycle exists and correctly implements the Market Maker Cycle.jpg 3-day pattern — the cycle-stage classification is highly speculative; the HUD may not include this field at all
- [INFER:guess] ShowAccount and ShowMultiPair parameters may not exist — account info and multi-pair tables are secondary features inconsistent with a "per-chart indicator" philosophy; both are marked [INFER:guess]
- [INFER:guess] PairList parameter for multi-pair display — if multi-pair is absent, this parameter does not exist
- [INFER] Color-coded text (BullishColor / BearishColor) vs. static white — color-coding is common in professional HUDs but MT4's OBJ_LABEL color API is clunky for per-field dynamic colors; could default to static white with no color changes
- [INFER] Whether the HUD uses a single OBJ_RECTANGLE_LABEL with multi-line text or separate OBJ_LABEL per field — single label is simpler to position; per-field labels allow independent color control
- [INFER] FontFace default "Consolas" — Consolas is not available on all Windows installations; "Courier New" is the safe fallback; actual default unknown
- [INFER] Whether the indicator supports configurable display order or sections are hard-coded top-to-bottom by function
- [INFER] Whether intraday I-HOD / I-LOD (Asian session high/low specifically) is shown alongside the general HOD/LOD, or whether HOD/LOD is simply the daily running high/low
- [INFER] Whether the cycle-stage detection maps to the Market Maker Cycle.jpg image's 3-day accumulation/directional-move/distribution pattern (Day 1/2/3) or to a different cycle definition (e.g., intraday cycle: Asia/London/US)
- [INFER:guess] Whether the HUD supports a "compact mode" showing only 3-4 priority fields when the chart is narrow
- [INFER] Whether the spread display is instantaneous (bid-ask at current tick) or averaged over a rolling window (to smooth out micro-spike spreads at news events)
- [INFER] Whether session countdown displays hours:minutes:seconds (sub-second precision unnecessary for a 1-second timer) or minutes:seconds only

**Recommendation to future spec re-writer:** Once an operator runs SM_NewHUD in MT4 on any chart, the indicator's Inputs dialog will reveal the exact parameter list and defaults. A screenshot of the HUD at London-open and at session-gap (inter-session quiet period) — both captured with all fields visible — should replace the entirely inferred field list in this spec. Until then, this spec documents the best-reconstruction of what an MMM-workflow HUD would display, grounded in MMM Book pp. 53-54, the Market Maker Cycle.jpg image, and the documented field sets of similar community HUD indicators.

---

## Verified Updates (2026-04-27 from MT4 Inputs + chart overlay)

Operator-captured screenshots of `!SM_NewHUD.ex4` confirm **18+ visible HUD fields** (prior spec listed 10) and a substantial Inputs catalog. Notably, a **Half-Yearly ADR (HYADR)** field exists that was not anticipated in prior spec.

### Confirmed visible HUD fields

| Field | Description | Was in spec? |
|-------|-------------|--------------|
| ASK / BID | Live quote pair | implicit |
| spread (pips) | Live spread, e.g., "1.8" | ✓ |
| HOD + distance from current | E.g., "HOD 2.31540: 25" | ✓ |
| LOD + distance from current | E.g., "LOD 2.30885: 41" | ✓ |
| TDR | Today's Daily Range | ✓ as ADR |
| YDR | Yesterday's Daily Range | ✗ NEW |
| WADR | Weekly ADR | ✗ NEW |
| MADR | Monthly ADR | ✗ NEW |
| **HYADR** | **Half-Yearly ADR** | ✗ NEW |
| PTO | Price-To-Open distance | ✗ NEW |
| WH + distance | Week High + distance | ✗ NEW |
| WL + distance | Week Low + distance | ✗ NEW |
| WR | Weekly Range | ✗ NEW |
| MWR / 3MWR / 6MWR | Monthly + 3-Month + 6-Month Weekly Range averages | ✗ NEW |
| 3xADR | Triple-ADR multiple alert | ✗ NEW |
| Candle Time | Countdown to next candle | ✓ |

### Confirmed inputs (from params 1 + params 2 screenshots)

**Display:** Code_Version=1, MaxSpread=1.75, Range_Today_Text="TDR", Range_Yest_Text="YDR", Range_Week_Text="WR", FontSize=9, FontColor=White, Symbol_FontColor=Black, Symbol_Font_Size=14, PriceColor=Black, Font_SizeADR3=9, FontColorADR3=Yellow, Show_4Digit_Price=false, ColorLast_Digit=false, LastDigitColor=(90,90,90).

**HiLo alert thresholds:** HiLoAlert_Distance1=10 pips (warn), HiLoAlert_Distance2=20 pips (alert). Color pairs HOD/LOD AlertClr=Dark Green, NearClr=LawnGreen.

**Week HiLo alert thresholds:** Week_HiLo_Alert_Distance3=25, Week_HiLo_Alert_Distance4=50. WH/WL Alert/Near color pairs same scheme.

**ADR alert:** adrAlert_Distance=10. Three color-pair sets: wadr (weekly), madr (monthly), **hyadr (half-yearly)** — each with AlertColorHi/Lo + ExceedColorHi/Lo.

**Background settings:** UseDark_Background=false, BackgroundColor=Gray, BackgroundSize=120, XL_Background_for_News=true, Overview_Mode=false, Trade_Track_Mode=false.

**Average periods (Av_N):** y=18, y_distance=0, Av_1=0, Av_2=1, Av_3=4, Av_4=13, Av_5=?, Av_6=26, plus a trailing 52. **Likely EMA periods displayed on the HUD** in a Fibonacci-ish progression (1, 4, 13, 26, 52). NEW — not anticipated in prior spec.

### Implications

- HYADR section adds a half-yearly average daily range — needs a dedicated calculation block in Phase 12 implementation.
- Av_N periods imply NewHUD computes/displays multiple EMAs (likely closing-price EMA at periods 1/4/13/26/52). If true, this is a small additional indicator inside the HUD.
- The 18-field display means the HUD is denser than a standard mini-HUD — Phase 12 implementation must lay out 4-5 grouped clusters (price, daily ranges, weekly stats, alerts, candle timer) to fit cleanly.

See `.planning/phases/11-sm-indicators-full-spec-documentation/evidence/VERIFIED-DEFAULTS.md` §4 for the full audit.

**Confidence:** Inputs/visible-fields elevation **Low → Medium**. Internals (whether NewHUD calls other SM indicators via `iCustom` for TDI/Pivots/ADR data, or computes everything itself) **remain `[INFER]`** — needs MetaEditor inspection of the .ex4 source if recovered, or behavioral testing.
