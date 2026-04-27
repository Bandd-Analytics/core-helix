# sm_WorkTime_no_autogmt

## Header

| Field | Value |
|-------|-------|
| Name | sm_WorkTime_no_autogmt |
| Source filename | `!sm_WorkTime_no_autogmt.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 37,956 bytes |
| Binary date | Sep 15, 2011 |
| Tier | 0 — Helper (no sm_gmtoffset dependency by design) |
| Confidence | Confidence: Medium |

**Confidence rationale:** Same as `sm_WorkTime` — session semantics HIGH confidence from MMM Book p. 8 / p. 40; exact parameter names, color defaults, object-naming conventions all `[INFER]`. Additional note: this variant predates `sm_WorkTime` by approximately 3 months (Sep 2011 vs Dec 2011), suggesting that the manual-GMT variant was the original and the auto-detect variant was added later. The 5,656-byte size difference between the two binaries (37,956 vs 43,612) is consistent with the auto-detect branch and GlobalVariable read being the only structural additions in the newer `sm_WorkTime`. [INFER — size-delta reasoning]

---

## Purpose

`sm_WorkTime_no_autogmt` draws the same color-coded translucent session-window rectangles on the price chart as `sm_WorkTime` (Asia 00:30–07:00 GMT, London/Europe 07:30–13:00 GMT, US/New York 13:30–20:30 GMT — MMM Book p. 8), but obtains the broker GMT offset from a **manual input parameter** (`BrokerGMT`) rather than from the GlobalVariable published by `sm_gmtoffset`. The "_no_autogmt" suffix is the complete functional description: this variant has no dependency on sm_gmtoffset by design.

Use this variant when: (a) the broker's DST schedule is non-standard and sm_gmtoffset auto-detection is unreliable, (b) the user prefers explicit control over the offset with no automatic adjustment, or (c) the user does not want to load sm_gmtoffset on the chart at all. The trade-off is that after a DST switch the user must manually update the `BrokerGMT` parameter (unless `BrokerDSTAdjust = true` is set) to keep session boxes accurate. All other visual and functional behaviour is identical to `sm_WorkTime`.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| BrokerGMT | int | 2 | -12 .. +14 | Broker server's GMT offset in whole hours — manually set by the user | [INFER] |
| BrokerDSTAdjust | bool | false | true / false | When true, add +1 h to BrokerGMT automatically during the Northern Hemisphere DST window (approx. late March – late October) | [INFER] |
| AsiaStart | int (hours GMT) | 0 | 0–23 | Asia session start hour in GMT | High (MMM Book p. 8) |
| AsiaEnd | int (hours GMT) | 7 | 0–23 | Asia session end hour in GMT | High (MMM Book p. 8) |
| LondonStart | int (hours GMT) | 7 | 0–23 | London/Europe session start hour | High (MMM Book p. 8) |
| LondonEnd | int (hours GMT) | 13 | 0–23 | London session end hour | High (MMM Book p. 8) |
| USStart | int (hours GMT) | 13 | 0–23 | US/New York session start hour | High (MMM Book p. 8) |
| USEnd | int (hours GMT) | 20 | 0–23 | US session end hour | High (MMM Book p. 8) |
| ShowAsia | bool | true | true / false | Toggle the Asia session rectangle | [INFER] |
| ShowLondon | bool | true | true / false | Toggle the London session rectangle | [INFER] |
| ShowUS | bool | true | true / false | Toggle the US session rectangle | [INFER] |
| AsiaColor | color | C'40,40,40' (dark gray) | any | Fill color for Asia session box | [INFER] |
| LondonColor | color | C'0,40,80' (dark blue) | any | Fill color for London session box | [INFER] |
| USColor | color | C'0,80,40' (dark green) | any | Fill color for US session box | [INFER] |
| HistoryDays | int | 5 | 1–30 | Number of past days for which to draw session boxes | [INFER] |
| ShowNYReversal | bool | true | true / false | Draw the smaller NY-reversal sub-box per MMM Book p. 40 | [INFER] |
| ObjectPrefix | string | "smWT_" | any | Prefix string prepended to all chart object names | [INFER] |

**Note:** `UseGMTOffset` is intentionally absent from this variant — that boolean was the flag in `sm_WorkTime` to enable/disable the GlobalVariable read. Here the offset is always sourced from `BrokerGMT`.

---

## Outputs

### Indicator buffers

None. Same as sm_WorkTime — pure chart-drawing indicator with no numeric series. [INFER]

### Chart objects

Identical to sm_WorkTime: one `OBJ_RECTANGLE` per visible session per displayed day:
- Up to `HistoryDays × 3` Asia/London/US rectangles.
- Optional `HistoryDays × 1` NY-reversal sub-rectangles (13:30–16:30 GMT, ~3 h, per MMM Book p. 40) if `ShowNYReversal = true`.
- Object name pattern: `ObjectPrefix + session_label + "_" + date_string`. [INFER]
- All objects deleted in `OnDeinit`. [INFER]

### Alerts

None. [INFER]

---

## Calculation logic

Identical to `sm_WorkTime` except for step 1 (offset acquisition):

1. **OnInit — set offset from input:**
   ```
   broker_offset = BrokerGMT
   if BrokerDSTAdjust and is_northern_hemisphere_dst_active():
       broker_offset = broker_offset + 1
   ```
   No GlobalVariable read. No dependency on sm_gmtoffset. The first-tick race condition that affects sm_WorkTime does not apply here.

2. **Per-day rectangle computation:** Identical to sm_WorkTime steps 2–3. For each day `d` in `[today - HistoryDays, today]`, for each session (`Asia`, `London`, `US`), compute UTC start/end from session boundary constants + 30-min offsets (00:30 / 07:30 / 13:30), add `broker_offset * 3600` to convert to broker time, then draw/update the `OBJ_RECTANGLE`.

3. **NY Reversal sub-box (if `ShowNYReversal = true`):** Identical to sm_WorkTime — draw a second narrower rectangle 13:30–16:30 GMT (broker-offset-adjusted) per MMM Book p. 40.

4. **Bar-iteration model:** Same as sm_WorkTime — delete-and-redraw all `ObjectPrefix`-prefixed objects on every new bar event. [INFER]

5. **OnDeinit:** Delete all objects with `ObjectPrefix`. [INFER]

---

## Pseudocode

```
# sm_WorkTime_no_autogmt — language-neutral imperative pseudocode
# Only difference from sm_WorkTime: broker_offset source is input, not GlobalVariable

CONST: SESSIONS = [
    { name: "Asia",   start: (0, 30),  end: (7,  0),  color: DARK_GRAY  },
    { name: "London", start: (7, 30),  end: (13, 0),  color: DARK_BLUE  },
    { name: "US",     start: (13, 30), end: (20, 30), color: DARK_GREEN }
]
CONST: NY_REV = { start: (13, 30), end: (16, 30), color: DARK_RED_TRANSLUCENT }

GLOBAL: broker_offset = 0

function on_init():
    # No GlobalVariable read — use input parameter directly
    broker_offset = BrokerGMT
    if BrokerDSTAdjust and is_northern_hemisphere_dst_active():
        broker_offset = broker_offset + 1


function is_northern_hemisphere_dst_active():
    # Heuristic: rough Northern Hemisphere DST window
    month = current_month()
    return (month >= 3 and month <= 10)


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
                name         = obj_name,
                time_left    = start_broker,
                price_top    = chart_high(),
                time_right   = end_broker,
                price_bottom = chart_low(),
                fill_color   = session.color,
                alpha        = 0.15,
                z_order      = SEND_TO_BACK
            )

        if ShowNYReversal:
            ny_start = day_anchor + NY_REV.start.hours * 3600 + NY_REV.start.mins * 60
            ny_end   = day_anchor + NY_REV.end.hours   * 3600 + NY_REV.end.mins   * 60
            draw_rectangle(
                name         = ObjectPrefix + "NYRev_" + format_date(day_anchor),
                time_left    = ny_start + broker_offset * 3600,
                price_top    = chart_high(),
                time_right   = ny_end   + broker_offset * 3600,
                price_bottom = chart_low(),
                fill_color   = NY_REV.color,
                alpha        = 0.20,
                z_order      = SEND_TO_BACK
            )


function on_deinit():
    delete_all_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

Identical to `sm_WorkTime`. Three translucent colored rectangles per session per displayed day on the **main price chart** (not a subwindow):

- **Asia session:** dark gray fill. [INFER on exact hex]
- **London/Europe session:** dark blue fill. [INFER]
- **US/New York session:** dark green fill. [INFER]
- **NY Reversal sub-box (optional):** translucent red/orange, 13:30–16:30 GMT, per MMM Book p. 40. [INFER on color]

Z-order: sent to background; candles render above boxes. No text labels by default. [INFER] Renders on all timeframes.

---

## Dependencies

None — this variant has no dependency on sm_gmtoffset by design. The broker GMT offset is taken directly from the `BrokerGMT` input parameter rather than from any GlobalVariable published at runtime. This is the explicit purpose of the "_no_autogmt" suffix.

No other SM helper dependencies. No external file I/O, no GlobalVariable reads. [INFER]

---

## Edge cases

- **User must manually adjust `BrokerGMT` after a broker DST switch when `BrokerDSTAdjust = false` (the default):** Unlike `sm_WorkTime`, which refreshes from sm_gmtoffset on the next bar and automatically picks up the new offset, this variant retains the value set at load time. After a DST switch, session boxes will be off by 1 h until the user changes `BrokerGMT` and reloads the indicator. Setting `BrokerDSTAdjust = true` partially mitigates this but relies on a calendar-based heuristic rather than actual broker behavior.
- **First-tick race condition does NOT apply:** Unlike sm_WorkTime, there is no GlobalVariable dependency that might not yet be populated. The offset is available immediately from the input parameter on `OnInit`.
- **Weekends:** Same as sm_WorkTime — rectangles are drawn over the weekend gap; cosmetically harmless.
- **Custom timeframes:** Same CPU-load consideration as sm_WorkTime on very short timeframes (M1, M5).
- **Broker offset change (server relocation):** Requires manual update of `BrokerGMT` and chart reload.
- **JPY pairs, indices, zero-volume bars:** Same handling as sm_WorkTime — purely time-based logic; symbol digit precision and volume are irrelevant.
- **BrokerDSTAdjust heuristic inaccuracy:** The month-range heuristic (March–October) is a Northern Hemisphere approximation. Brokers following US DST rules (which differ by ~2 weeks from European DST) may cause a 1-week window of inaccuracy around each DST transition.

---

## Test cases

1. **IC Markets EU broker, BrokerGMT = 2 (winter), EUR/USD H1:** sm_WorkTime_no_autogmt draws boxes at the same positions as sm_WorkTime configured against the same broker with sm_gmtoffset running. Asia = 02:30–09:00 broker, London = 09:30–15:00 broker, US = 15:30–22:30 broker. **Verifies behavioral parity with auto-GMT variant.**

2. **Same broker after DST switch, BrokerDSTAdjust = true:** `broker_offset = BrokerGMT + 1 = 3`. Boxes shift by +1 h in broker time: Asia = 03:30–10:00, London = 10:30–16:00, US = 16:30–23:30. Session boxes correctly follow GMT anchor even after DST.

3. **Same broker after DST switch, BrokerDSTAdjust = false (default):** `broker_offset` remains `2`. Boxes still draw at the winter positions (02:30–09:00 for Asia, etc.) — now 1 h off from true GMT sessions. This demonstrates why the auto-GMT variant (`sm_WorkTime`) is generally preferred: the user must manually update `BrokerGMT` to `3` and reload the indicator to correct the boxes.

---

## Port notes

### MQ4 to MQ5 deltas

Identical to `sm_WorkTime` except for the removal of one `GlobalVariableGet` call in `OnInit`. All drawing API differences (chart_id in `ObjectCreate`, `OnCalculate` signature, `EventSetTimer` option for timer-based refresh) are exactly the same as the `sm_WorkTime` MQ5 port. The only unique MQ5 consideration is that `GlobalVariableSet` is never called here, so there is no need to check for the GlobalVariable API.

### Python port

Identical plotting code as `sm_WorkTime` — same `axvspan` or `add_vrect` calls, same color scheme. The only difference is that the offset comes from a config dict input (e.g., `config["broker_gmt_offset"] = 2`) rather than a runtime detection call. This is actually **simpler to port** than the auto-detect variant because there is no need to implement `detect_broker_offset()`. The factored-out `session_classification` function (for `temporal_filters.py`) is the same as for `sm_WorkTime`.

### Backtester integration

Identical to `sm_WorkTime` — purely visual, no backtester role. The same session-boundary constants (00:30 / 07:30 / 13:30 GMT) feed `temporal_filters.py`. In backtesting mode, broker offset is always 0 (UTC timestamps in all OHLCV CSVs) and no offset parameter is needed regardless of which variant was used in live MT4.

---

## Uncertainty log

- [INFER] Parameter name `BrokerGMT` — could be `GMTOffset`, `ManualGMT`, `BrokerOffset`, `FixedGMT`, or any similar label; chosen as the most semantically clear
- [INFER] Default value `BrokerGMT = 2` — representative of a common European-server broker default (IC Markets EU, Pepperstone EU); a UTC+3 default (African/Middle-Eastern servers) or UTC+0 default are equally plausible
- [INFER] Parameter name `BrokerDSTAdjust` — could be `ApplyDST`, `DSTAuto`, `DSTOffset`, or absent from this older variant entirely
- [INFER] Default value `BrokerDSTAdjust = false` — older 2011-era indicators commonly expected manual adjustment; defaulting to true is also plausible but less typical for that era
- [INFER] Algorithmic equivalence to sm_WorkTime — inferred from (a) identical filename modulo the "_no_autogmt" suffix, (b) the 5,656-byte size delta being consistent with the removal of only the auto-GMT branch and GlobalVariable read, and (c) the Sep 2011 vs Dec 2011 timestamp suggesting this was the source from which sm_WorkTime was derived by addition; we cannot verify the binaries differ ONLY in the GMT-source branch without decompilation
- [INFER] Session minute offsets (00:30 / 07:30 / 13:30) — same uncertainty as sm_WorkTime; the integer-hour inputs may not capture the 30-minute offsets
- [INFER] ShowAsia / ShowLondon / ShowUS toggles present in this variant — may have been added only in the newer sm_WorkTime; the 2011-era version may have always drawn all sessions
- [INFER] ObjectPrefix "smWT_" shared with sm_WorkTime — could differ; if both indicators are loaded simultaneously with the same prefix, object-name collisions would occur. A distinct prefix (e.g., "smWTna_") would be more robust
- [INFER] ShowNYReversal parameter presence in this older variant — MMM Book p. 40 documents the NY-reversal box but the Sep 2011 binary may predate that feature
- [INFER] BrokerDSTAdjust uses a Northern Hemisphere calendar heuristic — could instead use a fixed date table (last Sunday of March / October), or could be entirely absent (manual-only DST handling expected from the user)

---

## Implementation status (Phase 12)

| Target | Status | File | Commit | Date |
|--------|--------|------|--------|------|
| MQ4 | Built ✅ | `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_WorkTime_no_autogmt.mq4` | `<TBD>` | 2026-04-XX |
| MQ5 | Built ✅ | `resource_pack/MMM/SM Indicators/MT5/helpers/sm_WorkTime_no_autogmt.mq5` | `<TBD>` | 2026-04-XX |
| Python | Built ✅ | `V2/v3_intelligence/sm_indicators/helpers/sm_worktime_no_autogmt.py` | `<TBD>` | 2026-04-XX |

Tests: `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_worktime_no_autogmt.py` (4 tests GREEN)
Confidence: Medium (matches Phase 11 spec).
Notes: explicitly NO `sm_gmtoffset` dependency by design (D-19 architectural distinction). Verified by grep gate (`test_no_sm_gmtoffset_dependency`) on the Python module and absence of `GlobalVariableGet("sm_GMTOffset")` from the MQ5/MQ4 sources. Object prefix is `smWTnoauto_` to avoid collision with the auto-variant's `smWT_` prefix when both are loaded on the same chart.
