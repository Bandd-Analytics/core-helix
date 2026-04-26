# SM_AlertZone_1

## Header

| Field | Value |
|-------|-------|
| Name | SM_AlertZone_1 |
| Source filename | `!SM_AlertZone_1.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 12,562 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (self-contained; no SM dependencies) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The general purpose — a price-level alert zone indicator that draws a rectangular zone and fires alerts when price enters/exits — is a well-understood pattern in MT4 (MEDIUM confidence). The MMM context (Strike Zone / Blue Box / Trading Zone) maps plausibly to this indicator class. However, the key open question is **what distinguishes AlertZone_1 from AlertZone_2**: the two binaries differ by only 148 bytes (`!SM_AlertZone_1.ex4` = 12,562 bytes; `!SM_AlertZone_2.ex4` = 12,710 bytes), which strongly suggests the same algorithm compiled with different default values — NOT different algorithms. Whether "variant 1" is the lower zone (long setups) or simply the first instance of the same indicator configured arbitrarily is unknown. All behavioral claims are [INFER]. Overall: **Confidence: Medium**.

---

## Purpose

SM_AlertZone_1 draws a rectangular zone on the price chart between two user-defined price levels and fires alerts when price enters or exits that zone. It is the primary tool for implementing the MMM "Strike Zone" (also called "Trading Zone" or "Blue Box") concept: an area near a key structural level (HOD, LOD, S1, ADR-low) where market makers are expected to accumulate positions before a directional move.

The MMM Glossary defines a **Trading Zone** / **Strike Zone** as an area "within 15-20 pips of HOD/LOD where setups occur" — price frequently spends time in this zone before the market-maker move initiates. The MMM Book p. 55 (Look for Strike Zones, item 4): "Is there a significant pivot point near this price?" reinforces that zones are defined relative to structural levels. SM_AlertZone_1 provides the alerting mechanism so a trader does not have to watch the chart continuously — the indicator watches the zone and fires when price enters.

**Relationship to AlertZone_2:** SM_AlertZone_1 and SM_AlertZone_2 share an almost-identical binary (148-byte file size delta). This spec documents AlertZone_1 as the **lower zone variant** — intended for use near LOD / S1 / ADR-low where LONG setups are anticipated. AlertZone_2 is documented separately as the upper zone variant for SHORT setups. However, the naming convention could equally mean the two indicators are loaded together as a pair (one lower, one upper) with user-configurable price inputs in both cases. The algorithmic distinction, if any, is [INFER].

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| ZoneHigh | double | 0.0 | any valid price | Upper price boundary of the alert zone | [INFER] — default 0.0 means user must manually set before the zone is active |
| ZoneLow | double | 0.0 | any valid price | Lower price boundary of the alert zone | [INFER] — default 0.0 |
| ZoneColor | color | clrSteelBlue | any | Fill color for the zone rectangle | [INFER] — steel blue / translucent as a "calm" lower-zone color |
| ZoneAlpha | int | 30 | 0–100 | Transparency of the zone fill (0=opaque, 100=invisible) | [INFER] |
| AlertOnEnter | bool | true | true / false | Fire alert when price first enters the zone (crosses into [ZoneLow, ZoneHigh]) | [INFER] |
| AlertOnExit | bool | false | true / false | Fire alert when price first exits the zone | [INFER] — exit alerting typically off by default |
| AlertSound | string | "alert.wav" | any valid filename | MT4 sound file played on alert | [INFER] |
| RepeatAlertSeconds | int | 300 | 30–3600 | Minimum seconds between repeated alerts on the same zone condition | [INFER] |
| EmailAlert | bool | false | true / false | Also send alert via configured email (SendMail) | [INFER] |
| PushAlert | bool | false | true / false | Also send push notification (SendNotification) | [INFER] |
| ObjectPrefix | string | "smAZ1_" | any valid string | Prefix for all chart objects created by this indicator; used for bulk-delete on deinit | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_AlertZone_1 uses `ObjectCreate` directly and exposes no indicator buffer arrays. Other indicators or EAs cannot access the zone boundaries via `CopyBuffer`.

### Chart objects

One `OBJ_RECTANGLE` spanning the full visible time range horizontally (or extended right with ray) and vertically between `ZoneLow` and `ZoneHigh`:
- Object name: `smAZ1_rect`
- Fill color: ZoneColor with ZoneAlpha transparency
- Z-order: background (below candlesticks)

[INFER] Optionally, two `OBJ_HLINE` at ZoneHigh and ZoneLow to mark the zone boundaries as crisp lines when the rectangle fill is too transparent to see clearly.

When `ZoneHigh = 0.0` AND `ZoneLow = 0.0`: no chart objects are created; `Comment()` is printed instructing the user to configure the inputs.

### Alerts

- **Enter alert:** When price transitions from outside the zone to inside the zone, `Alert()` fires with a message: "AZ1 ENTER [symbol] [price]". If EmailAlert=true: `SendMail()` also fires. If PushAlert=true: `SendNotification()` fires.
- **Exit alert:** When price transitions from inside the zone to outside, and `AlertOnExit=true`, a parallel alert fires: "AZ1 EXIT [symbol] [price]".
- **Rate limiting:** Both alert types are rate-limited by `RepeatAlertSeconds`. If the alert fires at time T, no further alerts of the same type fire until T + RepeatAlertSeconds — preventing alert floods from micro-oscillation at the zone boundary.

---

## Calculation logic

1. **On `OnInit`:**
   - Validate inputs: if `ZoneHigh ≤ ZoneLow` or both = 0.0, display a `Comment()` warning and skip drawing.
   - If valid: create `OBJ_RECTANGLE` between `[ZoneLow, ZoneHigh]` spanning chart time range. Set fill color and transparency.
   - Initialize `was_in_zone = false`; `last_alert_time = 0`.

2. **On every tick (`OnTick`):**
   - Read `current_price = Bid`.
   - Compute `is_in_zone = (current_price >= ZoneLow AND current_price <= ZoneHigh)`.
   - **Enter transition:** `is_in_zone = true AND was_in_zone = false`:
     - If `AlertOnEnter AND (CurrentTime - last_alert_time) >= RepeatAlertSeconds`:
       - `Alert("AZ1 ENTER " + Symbol + " @ " + DoubleToString(current_price, Digits))`
       - If EmailAlert: `SendMail("SM AlertZone_1", "ENTER " + Symbol)`
       - If PushAlert: `SendNotification("AZ1 ENTER " + Symbol)`
       - `last_alert_time = CurrentTime`
   - **Exit transition:** `is_in_zone = false AND was_in_zone = true`:
     - If `AlertOnExit AND (CurrentTime - last_alert_time) >= RepeatAlertSeconds`:
       - `Alert("AZ1 EXIT " + Symbol + " @ " + DoubleToString(current_price, Digits))`
       - `last_alert_time = CurrentTime`
   - Set `was_in_zone = is_in_zone`.

3. **Refresh of rectangle time anchors:** [INFER] The OBJ_RECTANGLE's right-time anchor may be extended on each `OnCalculate` call to follow the current bar's right edge, keeping the zone rectangle visible as the chart scrolls.

4. **On `OnDeinit`:** Delete all objects with prefix `smAZ1_`.

**Bar-iteration model:** Every-tick. The zone alert is time-critical — a price crossing the zone boundary mid-bar should fire immediately, not wait for bar close. Therefore `OnTick` (not `OnCalculate`) drives alert logic.

---

## Pseudocode

```
# SM_AlertZone_1 — language-neutral imperative pseudocode
# Purpose: price-level alert zone, variant 1 (lower zone / long-setup [INFER])
# Source: MMM Strike Zone concept (MMM Book p. 55 / MMM Glossary "Trading Zone")

state was_in_zone     = false
state last_alert_time = 0

function on_init():
    if ZoneHigh == 0 and ZoneLow == 0:
        comment("AlertZone_1: set ZoneHigh and ZoneLow inputs to activate")
        return
    if ZoneHigh <= ZoneLow:
        comment("AlertZone_1: ZoneHigh must be > ZoneLow")
        return
    create_rectangle(ObjectPrefix + "rect",
                     time_from=chart_start_time(), time_to=chart_end_time_extended(),
                     price_low=ZoneLow, price_high=ZoneHigh,
                     color=ZoneColor, alpha=ZoneAlpha, z_order=BACK)

function on_tick():
    current_price = current_bid()
    is_in_zone    = (current_price >= ZoneLow and current_price <= ZoneHigh)
    now           = current_server_time()

    if is_in_zone and not was_in_zone and AlertOnEnter:
        if now - last_alert_time >= RepeatAlertSeconds:
            alert("AZ1 ENTER " + symbol() + " @ " + format_price(current_price))
            if EmailAlert:  send_email("SM AlertZone_1", "ENTER " + symbol())
            if PushAlert:   send_push("AZ1 ENTER " + symbol())
            last_alert_time = now

    elif not is_in_zone and was_in_zone and AlertOnExit:
        if now - last_alert_time >= RepeatAlertSeconds:
            alert("AZ1 EXIT " + symbol() + " @ " + format_price(current_price))
            last_alert_time = now

    was_in_zone = is_in_zone

function on_deinit():
    delete_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

**Main price chart (no subwindow).** The zone appears as a translucent rectangular shaded region spanning the price chart horizontally at the user-configured price levels:

- **Fill:** Semi-transparent steel-blue rectangle [INFER: clrSteelBlue at ~30% opacity]. The transparency ensures candlesticks beneath the zone remain visible.
- **Border:** [INFER] No separate border line, or a thin steel-blue border at ZoneHigh and ZoneLow (matching OBJ_HLINE at both boundaries).
- **Z-order:** Background — below all candlesticks, arrows, and text labels.
- **Time span:** Extends from chart origin to the current visible right edge (or "ray right" if extended). [INFER] The rectangle time anchors may update on each bar to follow the chart scroll position.
- **No labels** on the zone rectangle by default. [INFER]

The rectangle remains on the chart until the indicator is removed (OnDeinit) or the user changes ZoneHigh/ZoneLow inputs (triggering OnInit reset).

---

## Dependencies

None. SM_AlertZone_1 is self-contained. It does not call `sm_gmtoffset`, `sm_WorkTime`, or any other SM indicator. Zone boundaries are user-defined price levels — no automatic calculation from session times or HOD/LOD.

---

## Edge cases

1. **ZoneHigh = ZoneLow = 0.0 (default unset state):** Indicator detects the 0/0 condition on `OnInit` and displays a `Comment()` prompt. No zone is drawn, no alerts fire. This prevents the indicator from cluttering the chart before the user configures it.

2. **ZoneHigh < ZoneLow (input error):** The indicator should detect this on `OnInit` and either swap the values silently or display an error comment. [INFER: behavior unverifiable]

3. **Bid spreads across zone boundary in a single tick (price gap):** If the Bid jumps from below ZoneLow to above ZoneHigh in one tick, the indicator sees: `was_in_zone = false`, `is_in_zone = true`, fires enter alert. Next tick Bid may still be inside the zone. No double-fire because `was_in_zone` was already set to true.

4. **Micro-oscillation at zone boundary (noise):** Price repeatedly crosses ZoneLow/ZoneHigh in rapid succession — e.g., on a thin-spread USDJPY at 05:00 GMT. `RepeatAlertSeconds` (default 300 seconds) ensures at most one alert per 5 minutes regardless of boundary-crossing frequency.

5. **AlertZone_1 and AlertZone_2 both loaded on the same chart:** Each indicator manages its own rectangle object (different `ObjectPrefix`). There is no conflict. If the zones overlap, both rectangles stack with combined visual fill.

6. **Symbol change:** `OnInit` fires; old rectangle (prefix-based) is deleted; new zone drawn at the same user-input price levels (which may not be meaningful for the new symbol — user must reconfigure inputs).

7. **Chart reopen (MT4 restart):** OBJ_RECTANGLE may persist in the chart's object list from a previous session. `OnInit` deletes all objects with the prefix before re-creating them.

8. **JPY / index pairs:** `current_price` is a plain double comparison vs ZoneHigh/ZoneLow. No pip-unit conversion is needed for the zone detection itself (it's a raw price comparison). However, if the indicator displays the distance to zone boundary in pips (in a label or alert text), it must use `SYMBOL_DIGITS` to format correctly.

---

## Test cases

1. **Standard enter alert (EURUSD H1):**
   - Configuration: `ZoneLow = 1.0820`, `ZoneHigh = 1.0830`, `AlertOnEnter = true`, `AlertOnExit = false`.
   - Tick stream: price at 1.0842 (outside zone) → drops to 1.0826 (inside zone).
   - Expected: Alert fires — "AZ1 ENTER EURUSD @ 1.08260". Zone rectangle visible on chart in steel-blue between 1.0820 and 1.0830. No exit alert because AlertOnExit=false.
   - After alert: price rebounds to 1.0838 (exits zone). No alert because AlertOnExit=false.

2. **Exit alert enabled, rate-limited:**
   - Configuration: `AlertOnEnter = true`, `AlertOnExit = true`, `RepeatAlertSeconds = 60`.
   - Tick stream: price at 1.0840 → drops to 1.0825 (enter fires at T+0) → rises to 1.0835 (exit fires at T+5s) → drops again to 1.0824 (enter would fire but T+5 < T+0+60, so suppressed).
   - Expected: Only 2 alerts total in this 30-second window: the initial enter and the first exit. Third event (re-enter) is rate-limited.

3. **RepeatAlertSeconds=300, high-frequency zone oscillation:**
   - Tick stream: price oscillates across 1.0830 (ZoneHigh boundary) 5 times in 30 seconds.
   - Expected: Only 1 alert fires (the first enter event). Subsequent events are suppressed until 300 seconds elapse.

---

## Port notes

### MQ4 to MQ5 deltas

`OBJ_RECTANGLE`, `ObjectCreate`, `ObjectSetDouble` APIs are identical in MQ4 and MQ5. The main MQ5 difference: `ObjectCreate` requires `ChartID()` as the first argument (0 in current-chart context). `Alert()`, `SendMail()`, `SendNotification()` function signatures identical. The `OnTick` handler exists in both languages for indicators (though its use in indicators vs EAs differs — in MQ5 indicators it is `OnTick` as well, called by the terminal on each new tick). Tick-driven indicator logic is fully portable between MQ4 and MQ5.

### Python port

In a live trading context: subscribe to tick stream via broker API (OANDA / MetaAPI / ZMQ bridge from MT5); maintain a `was_in_zone` state variable; emit log/webhook event on zone transition. In backtest: scan bar OHLC — `is_in_zone = (bar.low <= ZoneHigh) and (bar.high >= ZoneLow)` (any part of the bar touches the zone).

```python
# Vectorized zone detection for backtesting
df['in_zone'] = (df['Low'] <= ZONE_HIGH) & (df['High'] >= ZONE_LOW)
df['zone_enter'] = df['in_zone'] & ~df['in_zone'].shift(1).fillna(False)
```

### Backtester integration

Alert zones are SPATIAL filters — price-level gates. In `backtest_hybrid.py`, a zone can implement a "setup confirmation" gate: a trade entry signal only activates if price is currently inside the defined zone. Helix's Phase 8.4 INFRA-03 RAG learning loop (`on_trade_close`) already records HOD/LOD at trade time — these values are the natural inputs for dynamically setting `ZoneLow` (near LOD) and `ZoneHigh` (LOD + 15 pips) per session, making the alert zone a programmatic rather than manual price specification.

---

## Uncertainty log

- [INFER] Default ZoneHigh = 0.0 / ZoneLow = 0.0 — the indicator likely requires user to set these manually before it draws anything; default 0/0 is the common "unset" convention
- [INFER] Whether AlertZone_1 differs from AlertZone_2 in algorithm or only in default values — the 148-byte file size delta (12,562 vs 12,710 bytes) is the only objective evidence; 148 bytes could be a different default color string literal, sound filename, or zone-offset constant
- [INFER] If they differ in defaults: AlertZone_1 = lower zone (long setups near LOD), AlertZone_2 = upper zone (short setups near HOD) — this is a naming convention inference only
- [INFER] Whether the two variants are intended to be loaded simultaneously (one per chart for the two zones) or used independently
- [INFER] ZoneColor default clrSteelBlue — a neutral/calming blue for the lower zone is plausible; could be any color
- [INFER] ZoneAlpha default 30 — some transparency so candlesticks beneath are visible; exact value unknown
- [INFER] AlertOnEnter = true / AlertOnExit = false — enter alerting is the primary use case; exit alerting is secondary and typically disabled by default
- [INFER] RepeatAlertSeconds default 300 (5 minutes) — a 5-minute cooldown is common in MT4 alert indicators
- [INFER] ObjectPrefix "smAZ1_" — conventional naming; actual prefix unknown
- [INFER] Whether the rectangle extends to the chart's right edge via "ray" vs fixed time anchors — "ray" extension is more practical for a zone that should remain visible as time advances
