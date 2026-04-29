# SM_Alerting+TL

## Header

| Field | Value |
|-------|-------|
| Name | SM_Alerting+TL |
| Source filename | `!SM_Alerting+TL+v1.1.ex4` (version suffix `+v1.1` dropped per CONTEXT.md naming convention; the `+TL` component is preserved as a meaningful part of the indicator name) |
| Source platform | MT4 (MQL4) |
| Source binary size | 20,068 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (self-contained; depends on user-drawn OBJ_TREND objects, not other SM indicators) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The purpose — trendline-touch alerter that monitors user-drawn trendlines (`OBJ_TREND` objects) and fires alerts on touch or cross — is MEDIUM confidence. The `+TL` suffix unambiguously stands for "Trendline" and the `+v1.1` version implies a prior v1.0 without trendline monitoring (likely a simpler fixed-price alerter). The 20,068-byte size (~60% larger than AlertZone files at ~12KB) is consistent with the additional code needed to iterate `ObjectsTotal()` + `ObjectFind()` over all chart objects, compute slope/projection for each trendline, and manage per-trendline state for rate-limiting. The exact touch-tolerance algorithm and ancillary parameters are LOW confidence. Overall: **Confidence: Medium** for purpose, **Low** for touch-detection implementation details.

**Naming note:** The canonical output filename is `SM_Alerting+TL.md` — the `+TL` is part of the indicator identity. The `+v1.1` version suffix is dropped (per CONTEXT.md locked decisions: "only one canonical spec per indicator"). A prior `!SM_Alerting+v1.0.ex4` almost certainly existed without the `+TL` trendline-monitoring feature, containing only a simple price-level alerter.

---

## Purpose

SM_Alerting+TL monitors all user-drawn trendlines (`OBJ_TREND` objects) on the active chart and fires alerts when price **touches** or **crosses** any of them within a configurable tolerance. Unlike the AlertZone indicators (which monitor fixed horizontal price levels), Alerting+TL works on slanted trendlines whose projected price changes over time — requiring slope calculation and time-based extrapolation.

In the MMM workflow, trendlines are drawn manually by the trader to connect sequential HOD/LOD points, session-open-to-HOD lines, or S/R diagonal levels. When price returns to a trendline, it may represent a stop-hunt initiation zone (per "Anatomy of Stop Hunts" PDF in this repo) or a trend-continuation entry (price retests the dynamic support/resistance). SM_Alerting+TL removes the need for continuous chart monitoring — the indicator alerts when price reaches any live trendline, letting the trader assess the setup.

The `+v1.1` version suffix implies an earlier v1.0 indicator that provided only static price-level alerts (similar to AlertZone) without trendline monitoring. Version 1.1 extended the indicator to the more complex OBJ_TREND iteration pattern. The 20KB binary size (vs ~12KB for AlertZone) corroborates this: the additional ~8KB hosts the slope computation, per-trendline state map, and ObjectsTotal iteration code.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| AlertOnTouch | bool | true | true / false | Fire alert when price is within TouchPips of any trendline's projected value | [INFER] |
| AlertOnCross | bool | true | true / false | Fire alert when price crosses to the opposite side of a trendline | [INFER] |
| TouchPips | int | 2 | 1–50 | Tolerance for "touch" detection in pips — price within this distance of the projected trendline value is considered a touch | [INFER] — 2 pips is a tight default; could be 5 or 10 |
| RepeatAlertSeconds | int | 300 | 30–3600 | Minimum seconds between repeated alerts for the same trendline | [INFER] — per-trendline rate-limiting; same pattern as AlertZone |
| OnlyMonitorPrefix | string | "" | any valid string | If non-empty, only monitor OBJ_TREND objects whose name starts with this prefix — allows filtering a subset of trendlines | [INFER] |
| AlertSound | string | "alert.wav" | any valid filename | MT4 sound file played on alert | [INFER] |
| EmailAlert | bool | false | true / false | Also send email alert | [INFER] |
| PushAlert | bool | false | true / false | Also send push notification | [INFER] |
| DrawTouchMarker | bool | false | true / false | Draw a small marker (OBJ_ARROW) at the price and time of each touch event | [INFER] |
| TouchMarkerColor | color | clrYellow | any | Color of touch-point markers if DrawTouchMarker=true | [INFER] |
| MonitorRayOnly | bool | false | true / false | Only alert on trendlines that have `OBJPROP_RAY_RIGHT = true` (extended beyond their drawn endpoint) | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_Alerting+TL creates no indicator buffers; it reads existing chart objects (OBJ_TREND) and optionally creates marker objects.

### Chart objects

No persistent objects created by default. When `DrawTouchMarker = true`: small arrow-point objects (`OBJ_ARROW` or equivalent) are drawn at the price and time of each touch event, one per trendline per touch event. These are named using an auto-generated timestamp-based name (e.g., `"smTL_touch_HHMMSS"`) to avoid name collision.

### Alerts

- **Touch alert:** When `dist_pips ≤ TouchPips` for any OBJ_TREND object, `Alert()` fires with: "TL TOUCH [trendline_name] [symbol] @ [price]". Rate-limited per trendline by `RepeatAlertSeconds`.
- **Cross alert:** When price changes side relative to a trendline (projected_price changes from above-bid to below-bid or vice versa), `Alert()` fires with: "TL CROSS [trendline_name] [symbol] @ [price]". Also rate-limited.
- **Email / Push:** If EmailAlert=true / PushAlert=true, corresponding MT4 functions are also called on the same trigger condition.

---

## Calculation logic

The indicator operates on every tick (`OnTick` in MQL4 terminology for indicator-style tick callbacks, or the `OnCalculate` hook called on each new tick). The core loop iterates over all chart objects:

1. **On `OnInit`:** Initialize `last_alert_time` map (keyed by trendline object name). Initialize `prev_side` map (int: +1 / -1 / 0 keyed by trendline name) for cross-detection.

2. **On every tick:**

   a. **Iterate chart objects:** `total = ObjectsTotal(0)`. For `i` in `0 .. total-1`: `obj_name = ObjectName(0, i)`.

   b. **Filter to OBJ_TREND:** `if ObjectGetInteger(0, obj_name, OBJPROP_TYPE) != OBJ_TREND: continue`.

   c. **Apply name prefix filter:** `if OnlyMonitorPrefix != "" AND NOT starts_with(obj_name, OnlyMonitorPrefix): continue`.

   d. **Apply ray filter (if MonitorRayOnly=true):** `if NOT ObjectGetInteger(0, obj_name, OBJPROP_RAY_RIGHT): continue`.

   e. **Read trendline endpoints:**
      - `t1 = ObjectGetInteger(0, obj_name, OBJPROP_TIME, 0)` (first anchor time)
      - `p1 = ObjectGetDouble(0, obj_name, OBJPROP_PRICE, 0)` (first anchor price)
      - `t2 = ObjectGetInteger(0, obj_name, OBJPROP_TIME, 1)` (second anchor time)
      - `p2 = ObjectGetDouble(0, obj_name, OBJPROP_PRICE, 1)` (second anchor price)

   f. **Compute slope and projected price at current time:**
      - `if t2 == t1: continue` (vertical trendline — undefined slope; skip)
      - `slope = (p2 - p1) / (t2 - t1)` (price change per second of chart time)
      - `now = current_server_time()`
      - `projected = p1 + slope * (now - t1)`

   g. **Compute distance in pips:**
      - `dist_pips = abs(current_bid - projected) / pip_unit()`

   h. **Touch detection (`AlertOnTouch = true`):**
      - `if dist_pips <= TouchPips AND (now - last_alert_time[obj_name]) >= RepeatAlertSeconds`:
        - `fire_alert("TL TOUCH " + obj_name + " " + symbol + " @ " + format(current_bid))`
        - Update `last_alert_time[obj_name] = now`

   i. **Cross detection (`AlertOnCross = true`):**
      - `current_side = sign(current_bid - projected)` (+1 if bid above projected; -1 if below; 0 if exactly at)
      - `if obj_name in prev_side AND prev_side[obj_name] != 0 AND current_side != 0 AND current_side != prev_side[obj_name]`:
        - `fire_alert("TL CROSS " + obj_name + " " + symbol + " @ " + format(current_bid))`
        - Update `last_alert_time[obj_name] = now`
      - `prev_side[obj_name] = current_side`

   j. **Touch marker:** `if DrawTouchMarker AND dist_pips <= TouchPips`:
      - Create OBJ_ARROW at `(now, current_bid)` with color TouchMarkerColor.

3. **On `OnDeinit`:** Remove any touch-marker objects created by this indicator. The OBJ_TREND objects were drawn by the user — they are NOT removed.

**Bar-iteration model:** Every-tick. Trendline alerts are time-critical (a touch may last only a few seconds on a volatile instrument). Cannot be bar-close-only. The per-object iteration loop adds overhead proportional to the number of objects on the chart — optimized by caching slope values and only recomputing when the trendline's anchor points change.

---

## Pseudocode

```
# SM_Alerting+TL — language-neutral imperative pseudocode
# Monitors OBJ_TREND objects and fires alerts on touch / cross
# Source: RESEARCH.md §2 Tier 2 dossier; OBJ_TREND iteration pattern

state last_alert_time : map<string, datetime> = {}
state prev_side       : map<string, int>      = {}
state slope_cache     : map<string, double>   = {}
state intercept_cache : map<string, double>   = {}

function on_init():
    # State maps initialized empty; populated on first tick per trendline
    pass

function on_tick():
    now     = current_server_time()
    bid     = current_bid()
    pip     = pip_unit()
    total   = chart_object_count()

    for i in 0..total - 1:
        obj_name = chart_object_name(i)
        if object_type(obj_name) != OBJ_TREND: continue
        if OnlyMonitorPrefix != "" and not obj_name.startswith(OnlyMonitorPrefix): continue
        if MonitorRayOnly and not object_ray_right(obj_name): continue

        t1 = object_anchor_time(obj_name, 0)
        p1 = object_anchor_price(obj_name, 0)
        t2 = object_anchor_time(obj_name, 1)
        p2 = object_anchor_price(obj_name, 1)

        if t2 == t1: continue       # vertical trendline — skip

        slope     = (p2 - p1) / (t2 - t1)
        projected = p1 + slope * (now - t1)
        dist_pips = abs(bid - projected) / pip

        if AlertOnTouch and dist_pips <= TouchPips:
            if now - last_alert_time.get(obj_name, 0) >= RepeatAlertSeconds:
                fire_alert("TL TOUCH " + obj_name + " @ " + format_price(bid))
                if EmailAlert:  send_email("SM Alerting+TL", "TOUCH " + obj_name)
                if PushAlert:   send_push("TL TOUCH " + obj_name)
                last_alert_time[obj_name] = now

        current_side = sign(bid - projected)   # +1, -1, or 0
        if AlertOnCross:
            if obj_name in prev_side and prev_side[obj_name] != 0 \
               and current_side != 0 and current_side != prev_side[obj_name]:
                fire_alert("TL CROSS " + obj_name + " @ " + format_price(bid))
                last_alert_time[obj_name] = now

        prev_side[obj_name] = current_side

        if DrawTouchMarker and dist_pips <= TouchPips:
            marker_name = "smTL_touch_" + format_timestamp(now) + "_" + obj_name[:8]
            create_arrow(marker_name, now, bid, TouchMarkerColor)

function on_deinit():
    delete_all_objects_with_prefix("smTL_touch_")
```

---

## Visual elements

**No persistent drawings on the price chart by this indicator** (beyond optional touch markers). The trendlines it monitors are user-drawn `OBJ_TREND` objects — SM_Alerting+TL does not modify or re-draw them.

When `DrawTouchMarker = true`: small yellow dot or arrow markers appear on the chart at each touch event's price and time. These are labeled with a timestamp-based name to prevent collision across multiple touch events and multiple trendlines.

The indicator's presence on the chart is otherwise invisible — no rectangle, no subwindow, no lines. It operates as a silent watcher.

---

## Dependencies

None on other SM indicators. SM_Alerting+TL relies entirely on:
1. The user having drawn at least one `OBJ_TREND` object on the chart (otherwise the iteration loop finds nothing to monitor — no alerts ever fire)
2. MT4's `ObjectsTotal()` and object property APIs (built-in)

No dependency on `sm_gmtoffset`, `sm_WorkTime`, or any Tier 0 / Tier 1 SM indicator.

---

## Edge cases

1. **No OBJ_TREND objects on chart:** The `ObjectsTotal()` loop finds no trendline objects. The indicator runs silently — no alerts, no errors. This is not a bug; the user simply has no trendlines drawn.

2. **Vertical trendline (`t1 == t2`):** The slope computation would divide by zero (`(p2-p1)/(0)`). The indicator skips this object explicitly. [INFER: skip is the expected behavior; some implementations instead define vertical lines as infinite slope and only alert if bid equals p1]

3. **Trendline drawn entirely in the past (non-ray, `t2 < now`):** If `MonitorRayOnly = false` (default), the indicator still extrapolates the trendline to `now` using `p1 + slope * (now - t1)`. This may produce a projected price far outside the chart's current visible range if the trendline's slope is steep. [INFER] A better behavior would be to skip trendlines whose `t2 < now AND OBJPROP_RAY_RIGHT = false`; but default behavior cannot be confirmed without running the indicator.

4. **User dragging a trendline while the indicator is running:** MT4 fires tick events while the user moves trendline anchor points. During the drag, `ObjectGetDouble` returns intermediate anchor positions. This may cause spurious touch/cross alerts mid-drag. Rate-limiting (`RepeatAlertSeconds`) reduces the impact but does not eliminate it.

5. **Large number of trendlines (>20 objects on chart):** The `ObjectsTotal()` loop runs on every tick. With 20+ trendlines and high-frequency symbols (e.g., GBPUSD during London open, ~5-10 ticks/second), the loop runs 100-200 iterations per second. At 20 trendlines this is manageable. At 100+ chart objects (common on cluttered analysis charts), CPU overhead may become visible. `OnlyMonitorPrefix` is the mitigation.

6. **JPY / index / crypto symbols (non-standard pip size):** `pip_unit()` must use `SYMBOL_DIGITS` to compute the correct pip size. For USDJPY (3 digits), 1 pip = 0.01; for EURUSD (5 digits), 1 pip = 0.0001. TouchPips=2 means 2 pips in the symbol's pip convention — the comparison `dist_pips <= TouchPips` is pip-neutral only if `pip_unit()` adapts correctly. [INFER] whether the indicator auto-detects or requires manual adjustment for non-standard symbols.

7. **Trendline deleted while indicator running:** The `prev_side` and `last_alert_time` maps retain a stale entry keyed on the deleted object's name. This is a minor memory leak (one map entry per deleted trendline). Not a correctness bug — the stale entry is never triggered because `ObjectGetInteger(type)` returns an error for a non-existent object, causing the iteration to skip it. [INFER]

---

## Test cases

1. **Ascending trendline touch (EURUSD H1):**
   - Setup: User draws a trendline from 2026-04-20 09:00 GMT (price 1.0820) to 2026-04-25 09:00 GMT (price 1.0880). Slope = (1.0880-1.0820)/(5 days × 86400s) = 0.0060/432000 ≈ 1.39e-8 price/second.
   - At 2026-04-26 12:00 GMT (elapsed = 6 days + 3h = 543600s from anchor): projected = 1.0820 + 1.39e-8 × 543600 = **1.0820 + 0.00755 ≈ 1.0896**.
   - Current bid = 1.0894. Dist_pips = |1.0894 - 1.0896| / 0.0001 = **2 pips** = TouchPips.
   - Expected: Alert fires — "TL TOUCH [trendline_name] EURUSD @ 1.08940".

2. **Trendline cross (same trendline, subsequent tick):**
   - Bid rallies from 1.0894 to 1.0899 (above projected 1.0896).
   - `prev_side = -1` (bid was below projected); `current_side = +1` (bid now above projected).
   - Expected: Cross alert fires — "TL CROSS [trendline_name] EURUSD @ 1.08990". Subsequent ticks at 1.0898 (still above) do NOT re-fire.

3. **OnlyMonitorPrefix filter (5 trendlines, filter to 2):**
   - Chart has: "TL_long_1", "TL_long_2", "UserDraw_1", "AnotherLine", "Fib_236".
   - `OnlyMonitorPrefix = "TL_"`.
   - Expected: Only "TL_long_1" and "TL_long_2" are checked on each tick. "UserDraw_1", "AnotherLine", "Fib_236" are skipped. Zero alerts from the unmonitored trendlines even if price touches them.

---

## Port notes

### MQ4 to MQ5 deltas

The OBJ_TREND-related APIs are identical between MQ4 and MQ5:
- `ObjectsTotal(chart_id)`, `ObjectName(chart_id, index)`, `ObjectGetInteger(chart_id, name, property)`, `ObjectGetDouble(chart_id, name, property, index)` — same signatures in both languages.
- The main MQ5 difference: `chart_id` parameter is required (pass `0` for the current chart). In MQ4, chart_id is omitted in many function calls.
- `Alert()`, `SendMail()`, `SendNotification()` — identical signatures.
- `OnCalculate` vs `OnTick`: In MQ5 indicators, every-tick behavior is driven by `OnCalculate` being called on each new tick (when `#property indicator_buffers 0` and no buffers are set, the function still fires on every tick). The MQ5 port preserves the every-tick behavior.

### Python port

In live trading: trendlines must be sourced externally (MT5 EA that dumps `ObjectsTotal` to a ZMQ socket or SQLite file; Python subscribes to this feed). For each `(t1, p1, t2, p2)` tuple:

```python
def projected_price(t1, p1, t2, p2, now):
    if t2 == t1:
        return None  # vertical trendline
    slope = (p2 - p1) / (t2 - t1).total_seconds()
    return p1 + slope * (now - t1).total_seconds()

for tl in active_trendlines:
    proj = projected_price(*tl, now=current_time)
    if proj and abs(bid - proj) / pip_size <= TOUCH_PIPS:
        emit_touch_event(tl)
```

For backtesting: pre-define trendlines as `(t1, p1, t2, p2)` tuples; iterate over OHLC bars checking for projected-price crossings.

### Backtester integration

Trendlines are typically discretionary inputs — they require human judgment to draw. Programmatic trendline generation (e.g., swing-high/swing-low chain detection) would be needed to use SM_Alerting+TL equivalently in `backtest_hybrid.py`. Helix's current backtester does NOT consume user trendlines; the SM_Alerting+TL functional equivalent in a programmatic context would be a `dynamic_level_alert()` function that accepts slope and intercept parameters derived from algorithmic swing detection (Phase 9 StrategyRouter candidate). This indicator has **no direct backtester role** in the current Helix v2.0 architecture but represents the discretionary trendline-watching workflow that the Phase 9 router aims to formalize.

---

## Uncertainty log

- [INFER] TouchPips default 2 — a 2-pip tolerance is tight for H4/Daily charts where trendlines may be imprecise; could be 5, 10, or user-configurable with a larger default
- [INFER] AlertOnTouch and AlertOnCross both true by default — entering the zone and crossing it are the two primary events; could be that only one is enabled by default
- [INFER] OnlyMonitorPrefix default empty string (monitor all OBJ_TREND objects) — a non-empty default (e.g., "TL_") would require the user to name trendlines with a specific prefix, which is restrictive; empty is the more user-friendly default
- [INFER] Whether the indicator respects OBJPROP_RAY_RIGHT and skips non-ray trendlines past their drawn endpoint — `MonitorRayOnly` parameter is inferred; the actual behavior may always extrapolate or may always respect the ray property
- [INFER] DrawTouchMarker default false — visual clutter on active touch is a side effect users may not want by default; false is the safer default
- [INFER] Whether pip_unit() auto-adapts for JPY/index symbols (SYMBOL_DIGITS detection) — incorrect pip sizing would make TouchPips=2 produce very different behavior on USDJPY vs EURUSD
- [INFER] Earlier v1.0 (without `+TL` suffix) likely existed as a simpler price-level alerter without OBJ_TREND iteration — the `+v1.1` version suffix implies this history
- [INFER] Whether alerts fire per-trendline or as a single batch when multiple trendlines are touched simultaneously
- [INFER] Memory handling for `prev_side` and `last_alert_time` maps when trendlines are deleted — stale entries may accumulate without cleanup
- [INFER] Whether the indicator alerts on trendlines drawn by the user vs. trendlines drawn by other indicators (all OBJ_TREND objects regardless of creator would match the `ObjectsTotal` loop)

---

## Implementation status (Phase 12)

| Target | Status | Build date | Notes |
|--------|--------|------------|-------|
| MQ5 | Built ✅ | 2026-04-29 | `resource_pack/MMM/SM Indicators/MT5/indicators/SM_Alerting+TL.mq5`; iterates OBJ_TREND objects; linear projection; 1s timer; per-TL one-shot guard |
| MQ4 | Built ✅ | 2026-04-29 | `resource_pack/MMM/SM Indicators/MT4/_helix_built/indicators/SM_Alerting+TL.mq4`; MQL4 idioms; ObjectType/ObjectGet* |
| Python | Built ✅ | 2026-04-29 | `V2/v3_intelligence/sm_indicators/alerting_tl.py`; `compute_alerting_tl(df, trendlines=[(t1,p1,t2,p2),...])`; linear interpolation; 3/3 pytest GREEN |

**Confidence:** Medium — trendline-touch-alerter pattern well-understood; linear interpolation projection canonical; all parameter defaults [INFER].
Python port: no live OBJ_TREND access; caller supplies trendlines as explicit tuples.
