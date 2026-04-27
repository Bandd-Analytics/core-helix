# sm_WorkTime

## Header

| Field | Value |
|-------|-------|
| Name | sm_WorkTime |
| Source filename | `!sm_WorkTime.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 43,612 bytes |
| Binary date | Dec 15, 2011 |
| Tier | 0 — Helper (depends on sm_gmtoffset) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The session-window semantics of this indicator are HIGH confidence: MMM Book p. 8 defines the three session boundaries explicitly (Asia 00:30–07:00 GMT, London/Europe 07:30–13:00 GMT, US/New York 13:30–20:30 GMT) and MMM Book p. 40 ("Colour-Coded Sessions") directly describes the two-box overlay this indicator draws. The file's 43 KB size is consistent with substantial chart-drawing code (rectangle create/update/delete cycles across multiple sessions and history days). All parameter names, exact color defaults, object-naming conventions, and internal refresh cadence are `[INFER]` because the Dec 2011 binary cannot be decompiled.

---

## Purpose

`sm_WorkTime` is the session-window overlay indicator at the core of the MMM chart setup. It draws color-coded translucent rectangular boxes on the main price chart demarcating the three Steve Mauro MMM trading sessions: Asia (00:30–07:00 GMT), London/Europe (07:30–13:00 GMT), and US/New York (13:30–20:30 GMT), as defined in MMM Book p. 8. The boxes serve as a continuous visual reference for which session is currently active and for how many historical days back, letting the trader immediately identify session-based price behaviour — the Asian consolidation range (I-HOD / I-LOD), the London and NY breakout/reversal windows, and the inter-session gap periods. The indicator converts broker server time to GMT by reading the offset published by `sm_gmtoffset` (see Section 8, Dependencies), so that boxes remain accurately anchored to GMT session boundaries regardless of which broker server timezone the trader is using.

MMM Book p. 40 ("Colour-Coded Sessions") explicitly describes the visual output: "Two boxes can be drawn. The 1st is drawn around the Asian session and simply denotes the area of consolidation that is expected during this period. Quite often the ATR (Average True Range) of this period is considerably less than that of the other two sessions. The 2nd is a smaller box and highlights a time when there is a high probability of the midsession reversal (the New York Reversal). It starts at the beginning of the NY open and runs for about 3 hours." `sm_WorkTime` implements this two-box model for all three sessions, with the optional NY-reversal sub-box as an additional feature.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| AsiaStart | int (hours GMT) | 0 | 0–23 | Asia session start hour in GMT | High (MMM Book p. 8 — 00:30 means hour 0; minute offset is [INFER]) |
| AsiaEnd | int (hours GMT) | 7 | 0–23 | Asia session end hour in GMT | High (MMM Book p. 8) |
| LondonStart | int (hours GMT) | 7 | 0–23 | London/Europe session start hour | High (MMM Book p. 8; 07:30 minute offset is [INFER]) |
| LondonEnd | int (hours GMT) | 13 | 0–23 | London session end hour | High (MMM Book p. 8) |
| USStart | int (hours GMT) | 13 | 0–23 | US/New York session start hour | High (MMM Book p. 8; 13:30 minute offset is [INFER]) |
| USEnd | int (hours GMT) | 20 | 0–23 | US session end hour | High (MMM Book p. 8) |
| ShowAsia | bool | true | true / false | Toggle the Asia session rectangle | [INFER] |
| ShowLondon | bool | true | true / false | Toggle the London session rectangle | [INFER] |
| ShowUS | bool | true | true / false | Toggle the US session rectangle | [INFER] |
| AsiaColor | color | C'40,40,40' (dark gray) | any | Fill color for Asia session box | [INFER] |
| LondonColor | color | C'0,40,80' (dark blue) | any | Fill color for London session box | [INFER] |
| USColor | color | C'0,80,40' (dark green) | any | Fill color for US session box | [INFER] |
| HistoryDays | int | 5 | 1–30 | Number of past days for which to draw session boxes | [INFER] |
| UseGMTOffset | bool | true | true / false | Read GMT offset from sm_gmtoffset GlobalVariable to convert broker time → GMT | [INFER] |
| ShowNYReversal | bool | true | true / false | Draw the smaller NY-reversal sub-box (per MMM Book p. 40) starting at NY open and spanning ~3 h | [INFER] |
| ObjectPrefix | string | "smWT_" | any | Prefix string prepended to all chart object names created by this indicator | [INFER] |

---

## Outputs

### Indicator buffers

None. sm_WorkTime is a pure chart-drawing indicator; it declares no numeric indicator series. [INFER]

### Chart objects

One `OBJ_RECTANGLE` per visible session per displayed day:
- Up to `HistoryDays × 3` Asia/London/US rectangles (less if `ShowAsia / ShowLondon / ShowUS` are false).
- Optional `HistoryDays × 1` NY-reversal sub-rectangles (if `ShowNYReversal = true`), each spanning 13:30–16:30 GMT or approximately 3 h per MMM Book p. 40.
- Object names follow the pattern `ObjectPrefix + session_label + date_string` (e.g., `smWT_Asia_20250425`). [INFER on exact naming]
- All objects are deleted in `OnDeinit` via a prefix-based cleanup loop. [INFER]

### Alerts

None. sm_WorkTime is a visual-only helper. [INFER]

---

## Calculation logic

1. **OnInit — read GMT offset:**
   - If `UseGMTOffset == true` and GlobalVariable `sm_GMTOffset` exists: `broker_offset = GlobalVariableGet("sm_GMTOffset")`.
   - If the GlobalVariable does not exist (sm_gmtoffset not yet loaded): `broker_offset = 0`. Accept one cycle of inaccurate session boxes; boxes will correct on the next refresh after sm_gmtoffset initializes. [INFER — fallback behavior]
   - If `UseGMTOffset == false`: `broker_offset = 0`.

2. **Per-day rectangle computation:** For each day `d` in the range `[today - HistoryDays, today]`:
   a. Compute `day_anchor_utc` = midnight UTC for day `d` (Unix timestamp).
   b. For each session (`Asia`, `London`, `US`):
      - `session_start_utc = day_anchor_utc + session.start_hour * 3600 + session.start_min * 60`
      - `session_end_utc   = day_anchor_utc + session.end_hour   * 3600 + session.end_min   * 60`
      - Convert to broker time: `start_broker = session_start_utc + broker_offset * 3600`
      - Convert to broker time: `end_broker   = session_end_utc   + broker_offset * 3600`
   c. Locate the bar indices on the current chart whose timestamps bracket `start_broker` and `end_broker`.
   d. Create or update `OBJ_RECTANGLE` spanning `[start_broker, end_broker]` horizontally and `[chart_low, chart_high]` vertically, using the session's fill color and sending the object to the background (Z-order: behind price candles).

3. **NY Reversal sub-box (if `ShowNYReversal = true`):**
   For each day, draw a second, narrower rectangle over the US session window covering 13:30–16:30 GMT (broker-offset-adjusted), in a distinct color (e.g., translucent red/orange). [INFER on exact duration — MMM Book p. 40 says "about 3 hours"]

4. **Bar-iteration model:** The indicator refreshes on every new bar event (`OnCalculate` called when `rates_total` increases). On each refresh, all objects with `ObjectPrefix` are deleted and redrawn for the full `HistoryDays` window. This ensures that the right edge of rectangles stays current as price advances. [INFER — delete-and-redraw on every new bar is the standard MQL4 pattern for this class of indicator]

5. **OnDeinit:** Delete all objects whose names begin with `ObjectPrefix`. [INFER]

---

## Pseudocode

```
# sm_WorkTime — language-neutral imperative pseudocode
# All session times in GMT hours:minutes

CONST: SESSIONS = [
    { name: "Asia",   start: (0, 30),  end: (7,  0),  color: DARK_GRAY  },
    { name: "London", start: (7, 30),  end: (13, 0),  color: DARK_BLUE  },
    { name: "US",     start: (13, 30), end: (20, 30), color: DARK_GREEN }
]
CONST: NY_REV = { start: (13, 30), end: (16, 30), color: DARK_RED_TRANSLUCENT }

GLOBAL: broker_offset = 0

function on_init():
    if UseGMTOffset:
        if global_variable_exists("sm_GMTOffset"):
            broker_offset = read_global_variable("sm_GMTOffset")
        else:
            broker_offset = 0   # fallback; will correct on next refresh
    else:
        broker_offset = 0


function on_new_bar():
    delete_all_objects_with_prefix(ObjectPrefix)

    today_midnight_utc = floor(current_utc_time() / 86400) * 86400

    for day_idx from -HistoryDays to 0 inclusive:
        day_anchor = today_midnight_utc + day_idx * 86400

        for session in SESSIONS:
            if not session_enabled(session.name):
                continue

            start_utc = day_anchor + session.start.hours * 3600 + session.start.mins * 60
            end_utc   = day_anchor + session.end.hours   * 3600 + session.end.mins   * 60

            start_broker = start_utc + broker_offset * 3600
            end_broker   = end_utc   + broker_offset * 3600

            obj_name = ObjectPrefix + session.name + "_" + format_date(day_anchor)
            draw_rectangle(
                name        = obj_name,
                time_left   = start_broker,
                price_top   = chart_high(),
                time_right  = end_broker,
                price_bottom= chart_low(),
                fill_color  = session.color,
                alpha       = 0.15,
                z_order     = SEND_TO_BACK
            )

        if ShowNYReversal:
            ny_start_utc = day_anchor + NY_REV.start.hours * 3600 + NY_REV.start.mins * 60
            ny_end_utc   = day_anchor + NY_REV.end.hours   * 3600 + NY_REV.end.mins   * 60
            draw_rectangle(
                name        = ObjectPrefix + "NYRev_" + format_date(day_anchor),
                time_left   = ny_start_utc + broker_offset * 3600,
                price_top   = chart_high(),
                time_right  = ny_end_utc   + broker_offset * 3600,
                price_bottom= chart_low(),
                fill_color  = NY_REV.color,
                alpha       = 0.20,
                z_order     = SEND_TO_BACK
            )


function on_deinit():
    delete_all_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

Three translucent colored rectangles per session per displayed day, rendered on the **main price chart** (not in a subwindow). Each rectangle spans the full vertical range of the chart (from chart_low to chart_high) so that price candles render in front of the colored background:

- **Asia session:** dark gray fill [INFER on exact hex; `C'40,40,40'` is a representative value]. Represents the Asian consolidation range where I-HOD and I-LOD are set.
- **London/Europe session:** dark blue fill [INFER; `C'0,40,80'` representative]. The primary breakout window.
- **US/New York session:** dark green fill [INFER; `C'0,80,40'` representative]. Includes the NY open and any mid-session reversal.
- **NY Reversal sub-box (optional):** smaller translucent red or orange box overlaid on the first ~3 h of the US session (13:30–16:30 GMT) per MMM Book p. 40. [INFER on color]

Z-order: rectangles sent to background so that price candles, indicator lines, and user-drawn objects render above them. No text labels on the boxes by default. [INFER — some builds may draw a session label at the top edge of each box]

The indicator renders on all timeframes (M1 through MN); on very short timeframes (M1, M5) the rectangles will be very wide relative to visible bar count.

---

## Dependencies

`sm_gmtoffset` — when `UseGMTOffset = true`, sm_WorkTime reads the GlobalVariable `sm_GMTOffset` published by `sm_gmtoffset` to convert broker server time to GMT. If sm_gmtoffset is not loaded on the same chart, the fallback is `broker_offset = 0`, which means session boxes are anchored to broker time rather than GMT. [INFER on GlobalVariable name and fallback behavior]

No other SM helper dependencies. No external file I/O or timer events beyond bar callbacks. [INFER]

---

## Edge cases

- **GMT offset GlobalVariable not yet published:** sm_WorkTime loads before sm_gmtoffset has initialized — `broker_offset` defaults to 0; boxes are visually incorrect by `abs(broker_offset)` hours for one bar cycle. Corrects on the next new-bar refresh once sm_gmtoffset has published its GlobalVariable. Operator should load sm_gmtoffset before sm_WorkTime to minimize this window.
- **DST switch mid-week:** The broker's GMT offset changes. sm_WorkTime reads the updated GlobalVariable on its next new-bar refresh; boxes shift accordingly from that bar onward. There is no mid-bar correction.
- **Daylight savings asymmetry:** The broker may observe DST on different calendar dates than the GMT/UTC reference (e.g., US broker switching on US DST date, 2 weeks before European DST). During the asymmetry window, sm_WorkTime boxes are off by 1 h even though sm_gmtoffset has correctly reported the raw broker offset. The `DSTAdjust` input in sm_gmtoffset is the mitigation; no direct handling in sm_WorkTime itself. [INFER]
- **Weekends:** No price bars exist for Saturday and Sunday. Session rectangles for Saturday/Sunday are drawn (spanning the gap) but no candles render inside them. This is cosmetically harmless.
- **Custom timeframe (M1, M5):** Rectangles are anchored to bar timestamps, not bar indices. On M1, each session rectangle spans hundreds of bars; the `delete_all_objects_with_prefix` call followed by redraw on every new bar is CPU-intensive. [INFER — performance issue on very short TFs]
- **Chart symbol change (ChartSetSymbol):** `OnInit` is called again; offset is re-read and boxes are redrawn for the new symbol. This is the standard MQL4 reinitialization pattern.
- **JPY pairs and indices:** Session box logic is purely time-based; it does not depend on the symbol's digit precision. No special handling needed.
- **Zero-volume bars:** sm_WorkTime does not read volume; zero-volume bars are treated like any other bar for session-box placement purposes.

---

## Test cases

1. **IC Markets EU broker (GMT+2 winter), EUR/USD H1 chart, current day is a Wednesday:** With `HistoryDays = 5`, sm_WorkTime should draw 5 days × 3 sessions = 15 rectangles (plus optionally 5 NY-reversal sub-boxes if `ShowNYReversal = true`). The Asia rectangle for today should span broker times **02:30–09:00** (= 00:30–07:00 GMT + 2 h offset). The London rectangle should span **09:30–15:00** broker time. The US rectangle should span **15:30–22:30** broker time.

2. **Same broker after European spring DST switch (broker moves to GMT+3):** Asia rectangle for today should span broker times **03:30–10:00** (= 00:30–07:00 GMT + 3 h). The box appears shifted 1 h later in broker time compared to winter. Session boxes correctly follow the GMT anchor even as broker clock shifts.

3. **UseGMTOffset = false, broker running on GMT+3:** Asia box is drawn at **00:30–07:00 in broker time** rather than at 03:30–10:00. The session boxes are visually wrong — 3 h earlier than the true GMT sessions — demonstrating why `UseGMTOffset = true` (dependent on sm_gmtoffset) is the correct configuration for non-GMT brokers.

---

## Port notes

### MQ4 to MQ5 deltas

The `OBJ_RECTANGLE` drawing API is syntactically identical between MQL4 and MQL5, but `ObjectCreate()` in MQL5 takes `chart_id` (pass 0 for the current chart) as the first argument. `ObjectSetInteger()` / `ObjectSetDouble()` for fill color, transparency, and Z-order are identical. `OnCalculate()` signature changes: MQL5 requires the full `(rates_total, prev_calculated, time[], open[], high[], low[], close[], tick_volume[], volume[], spread[])` form. Since sm_WorkTime never reads price buffer arrays (only chart_high/chart_low for rectangle bounds, obtained via `ChartGetDouble`), the `OnCalculate` body is minimal. `GlobalVariableGet` for reading sm_gmtoffset's output is identical in both languages. An MQL5 port can optionally use `EventSetTimer(1)` + `OnTimer()` to refresh rectangles on a 1-second cadence rather than waiting for new-bar events, which is useful on long timeframes (H4, Daily) where new bars are infrequent.

### Python port

sm_WorkTime is a pure plotting helper with no analytical output. In a Python/Helix context, the equivalent is a `plot_session_boxes(ax, dates, broker_offset, sessions)` function that calls `matplotlib.axes.Axes.axvspan(xmin, xmax, alpha=0.15, color=...)` for each session window on a price chart, or a `plotly` `add_vrect` call. The session detection logic — `is_in_session(timestamp_utc, session_name, broker_offset)` — is **factored out separately** from the plotting code, because the same logic is reused in Helix's `temporal_filters.py` (Phase 8.5 scope) for the `is_tradeable_session(pair, strategy, ts)` predicate. Inputs become a config dict (`session_config.py`) consumed by both the plotter and the session filter; the `broker_offset` value comes from the Python equivalent of sm_gmtoffset (a `detect_broker_offset()` utility, or simply 0 in backtesting mode).

### Backtester integration

sm_WorkTime is **purely visual** and has no backtester role — the session boxes inform the human trader visually but are not consumed by any backtesting logic. However, the session-boundary times embedded in this indicator (00:30 / 07:00 / 07:30 / 13:00 / 13:30 / 20:30 GMT) are precisely the values that Helix's Phase 8.5 temporal analysis (`session_config.py`, `temporal_filters.py`) will codify as the canonical MMM session schedule. When porting sm_WorkTime session parameters to Python for backtesting purposes, factor the session-classification function out of the plotting layer and wire it into `is_tradeable_session(pair, strategy, ts)` per the Phase 8.5 ROADMAP entry (SC4). This avoids duplicating session boundary constants across the codebase.

---

## Uncertainty log

- [INFER] Session minute offsets: the integer-hour inputs (AsiaStart=0, LondonStart=7, USStart=13) do not capture the 30-minute offsets (00:30, 07:30, 13:30) from MMM Book p. 8. The actual inputs may use separate `AsiaStartMin` / `AsiaEndMin` parameters, or hard-code the 30-min offset internally, or round to the nearest hour for simplicity
- [INFER] Parameter name `AsiaStart` / `AsiaEnd` / `LondonStart` etc. — common naming convention; actual names in 2011-era MQL4 code could be `Asian_Start`, `AsiaSt`, or entirely different
- [INFER] ShowAsia / ShowLondon / ShowUS toggle parameters — may be combined into a single `ShowSessions` bitmask, or each session may always be shown with no toggle
- [INFER] Default colors `C'40,40,40'`, `C'0,40,80'`, `C'0,80,40'` — representative MMM-palette dark tones; exact RGB values unknown
- [INFER] HistoryDays default of 5 — common choice for a working week; could be 3, 7, or 10
- [INFER] ShowNYReversal parameter — MMM Book p. 40 describes the NY-reversal box, but it may be a permanently drawn element rather than a user toggle
- [INFER] ObjectPrefix "smWT_" — plausible SM convention; exact prefix unknown
- [INFER] GlobalVariable name read as "sm_GMTOffset" — must match the name written by sm_gmtoffset; if sm_gmtoffset uses a different name string, the link breaks
- [INFER] delete-and-redraw on every new bar — an alternative is to create objects once in OnInit and then only update their X-axis endpoints on new bars; the former is simpler and more common in 2011-era indicators
- [INFER] NY-reversal sub-box spanning 13:30–16:30 GMT (3 h) — MMM Book p. 40 says "about 3 hours" without specifying end time exactly
- [INFER] Z-order send-to-back via `ObjectSetInteger(0, name, OBJPROP_BACK, true)` — standard MQL4 pattern for background rectangles; the indicator may also adjust the OBJPROP_FILL property for transparency
- [INFER] No text labels on boxes by default — some variants of this indicator draw "ASIA", "LONDON", "NY" labels at the top edge; presence and format unknown

---

## Implementation status (Phase 12)

| Target | Status | File | Commit | Date |
|--------|--------|------|--------|------|
| MQ4 | Built ✅ | `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_WorkTime.mq4` | `<TBD>` | 2026-04-XX |
| MQ5 | Built ✅ | `resource_pack/MMM/SM Indicators/MT5/helpers/sm_WorkTime.mq5` | `<TBD>` | 2026-04-XX |
| Python | Built ✅ | `V2/v3_intelligence/sm_indicators/helpers/sm_worktime.py` | `<TBD>` | 2026-04-XX |

Tests: `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_worktime.py` (6 tests GREEN)
Confidence: Medium (matches Phase 11 spec).
Notes: depends on `sm_gmtoffset` (Python `compute_sm_gmtoffset`; MQ5/MQ4 GlobalVariable `sm_GMTOffset`). Session boundaries follow MMM Book p. 8 (00:30 / 07:30 / 13:30 GMT) and p. 40 NY-reversal sub-box (13:30–16:30 GMT, ~3 h).
